package svg

import (
	"fmt"
	"math"
	"strconv"
	"strings"
)

// scanner reads the numbers and the commands of path data.
type scanner struct {
	s string
	i int
}

func (sc *scanner) skipSep() {
	for sc.i < len(sc.s) {
		c := sc.s[sc.i]
		if c == ' ' || c == ',' || c == '\t' || c == '\n' || c == '\r' {
			sc.i++
			continue
		}
		return
	}
}

// number reads one number. "1.5.5" is two numbers, "-1-2" is two numbers.
func (sc *scanner) number() (float64, bool) {
	sc.skipSep()
	st := sc.i
	j := sc.i
	if j < len(sc.s) && (sc.s[j] == '+' || sc.s[j] == '-') {
		j++
	}
	digits, dot := false, false
	for j < len(sc.s) {
		c := sc.s[j]
		if c >= '0' && c <= '9' {
			digits = true
			j++
		} else if c == '.' && !dot {
			dot = true
			j++
		} else {
			break
		}
	}
	if !digits {
		return 0, false
	}
	if j < len(sc.s) && (sc.s[j] == 'e' || sc.s[j] == 'E') {
		k := j + 1
		if k < len(sc.s) && (sc.s[k] == '+' || sc.s[k] == '-') {
			k++
		}
		if k < len(sc.s) && sc.s[k] >= '0' && sc.s[k] <= '9' {
			for k < len(sc.s) && sc.s[k] >= '0' && sc.s[k] <= '9' {
				k++
			}
			j = k
		}
	}
	v, err := strconv.ParseFloat(sc.s[st:j], 64)
	if err != nil {
		return 0, false
	}
	sc.i = j
	return v, true
}

// flag reads an arc flag: a single 0 or 1, with no separator needed after it.
func (sc *scanner) flag() (bool, bool) {
	sc.skipSep()
	if sc.i < len(sc.s) && (sc.s[sc.i] == '0' || sc.s[sc.i] == '1') {
		v := sc.s[sc.i] == '1'
		sc.i++
		return v, true
	}
	return false, false
}

func (sc *scanner) command() (byte, bool) {
	sc.skipSep()
	if sc.i < len(sc.s) && strings.IndexByte("MmLlHhVvCcSsQqTtAaZz", sc.s[sc.i]) >= 0 {
		c := sc.s[sc.i]
		sc.i++
		return c, true
	}
	return 0, false
}

// parsePath turns path data into polylines. tol is the curve tolerance in user units.
func parsePath(d string, tol float64) ([]Polyline, error) {
	sc := scanner{s: d}
	var out []Polyline
	var cur Polyline
	var p, start, ctrl Pt
	var last byte
	flush := func() {
		if len(cur) > 1 {
			out = append(out, cur)
		}
		cur = nil
	}
	lineTo := func(q Pt) {
		if len(cur) == 0 {
			cur = Polyline{p}
		}
		cur = append(cur, q)
		p = q
	}
	cmd := byte(0)
	for {
		c, ok := sc.command()
		if ok {
			cmd = c
		} else {
			sc.skipSep()
			if sc.i >= len(sc.s) {
				break
			}
			if cmd == 0 {
				return nil, fmt.Errorf("svg: path data must start with a command: %q", d)
			}
			// An implicit repeat. After M the repeat is L.
			if cmd == 'M' {
				cmd = 'L'
			} else if cmd == 'm' {
				cmd = 'l'
			}
		}
		rel := cmd >= 'a'
		up := cmd &^ 0x20
		get := func() (float64, error) {
			v, ok := sc.number()
			if !ok {
				return 0, fmt.Errorf("svg: a number is missing after %c at %d", cmd, sc.i)
			}
			return v, nil
		}
		pt := func() (Pt, error) {
			x, err := get()
			if err != nil {
				return Pt{}, err
			}
			y, err := get()
			if err != nil {
				return Pt{}, err
			}
			if rel {
				return Pt{p.X + x, p.Y + y}, nil
			}
			return Pt{x, y}, nil
		}
		switch up {
		case 'Z':
			if len(cur) > 0 {
				lineTo(start)
			}
			flush()
			p = start
			last = 'Z'
			// Z takes no numbers: go to the next command.
			continue
		case 'M':
			q, err := pt()
			if err != nil {
				return nil, err
			}
			flush()
			p, start = q, q
		case 'L':
			q, err := pt()
			if err != nil {
				return nil, err
			}
			lineTo(q)
		case 'H':
			v, err := get()
			if err != nil {
				return nil, err
			}
			if rel {
				v += p.X
			}
			lineTo(Pt{v, p.Y})
		case 'V':
			v, err := get()
			if err != nil {
				return nil, err
			}
			if rel {
				v += p.Y
			}
			lineTo(Pt{p.X, v})
		case 'C', 'S':
			var c1 Pt
			if up == 'C' {
				q, err := pt()
				if err != nil {
					return nil, err
				}
				c1 = q
			} else {
				c1 = p
				if last == 'C' || last == 'S' {
					c1 = Pt{2*p.X - ctrl.X, 2*p.Y - ctrl.Y}
				}
			}
			c2, err := pt()
			if err != nil {
				return nil, err
			}
			q, err := pt()
			if err != nil {
				return nil, err
			}
			if len(cur) == 0 {
				cur = Polyline{p}
			}
			cur = cubic(cur, p, c1, c2, q, tol, 0)
			ctrl, p = c2, q
		case 'Q', 'T':
			var c1 Pt
			if up == 'Q' {
				q, err := pt()
				if err != nil {
					return nil, err
				}
				c1 = q
			} else {
				c1 = p
				if last == 'Q' || last == 'T' {
					c1 = Pt{2*p.X - ctrl.X, 2*p.Y - ctrl.Y}
				}
			}
			q, err := pt()
			if err != nil {
				return nil, err
			}
			if len(cur) == 0 {
				cur = Polyline{p}
			}
			// A quadratic is a cubic with these control points.
			a := Pt{p.X + 2.0/3*(c1.X-p.X), p.Y + 2.0/3*(c1.Y-p.Y)}
			b := Pt{q.X + 2.0/3*(c1.X-q.X), q.Y + 2.0/3*(c1.Y-q.Y)}
			cur = cubic(cur, p, a, b, q, tol, 0)
			ctrl, p = c1, q
		case 'A':
			rx, err := get()
			if err != nil {
				return nil, err
			}
			ry, err := get()
			if err != nil {
				return nil, err
			}
			rot, err := get()
			if err != nil {
				return nil, err
			}
			large, ok1 := sc.flag()
			sweep, ok2 := sc.flag()
			if !ok1 || !ok2 {
				return nil, fmt.Errorf("svg: bad arc flags at %d", sc.i)
			}
			q, err := pt()
			if err != nil {
				return nil, err
			}
			if len(cur) == 0 {
				cur = Polyline{p}
			}
			cur = arc(cur, p, q, rx, ry, rot, large, sweep, tol)
			p = q
		}
		last = up
	}
	flush()
	return out, nil
}

// cubic appends the points of a cubic Bézier (without p0) by recursive subdivision.
func cubic(pl Polyline, p0, p1, p2, p3 Pt, tol float64, depth int) Polyline {
	// Flatness: the distance of the control points from the chord.
	dx, dy := p3.X-p0.X, p3.Y-p0.Y
	d1 := math.Abs((p1.X-p3.X)*dy - (p1.Y-p3.Y)*dx)
	d2 := math.Abs((p2.X-p3.X)*dy - (p2.Y-p3.Y)*dx)
	l2 := dx*dx + dy*dy
	flat := false
	if l2 < 1e-18 {
		flat = math.Hypot(p1.X-p0.X, p1.Y-p0.Y)+math.Hypot(p2.X-p0.X, p2.Y-p0.Y) <= tol
	} else {
		flat = (d1+d2)*(d1+d2) <= 16*tol*tol*l2/9
	}
	if flat || depth > 16 {
		return append(pl, p3)
	}
	m := func(a, b Pt) Pt { return Pt{(a.X + b.X) / 2, (a.Y + b.Y) / 2} }
	p01, p12, p23 := m(p0, p1), m(p1, p2), m(p2, p3)
	p012, p123 := m(p01, p12), m(p12, p23)
	mid := m(p012, p123)
	pl = cubic(pl, p0, p01, p012, mid, tol, depth+1)
	return cubic(pl, mid, p123, p23, p3, tol, depth+1)
}

// arc appends an elliptical arc (SVG endpoint form, without p0).
func arc(pl Polyline, p0, p1 Pt, rx, ry, rotDeg float64, large, sweep bool, tol float64) Polyline {
	if p0 == p1 {
		return pl
	}
	rx, ry = math.Abs(rx), math.Abs(ry)
	if rx == 0 || ry == 0 {
		return append(pl, p1)
	}
	phi := rotDeg * math.Pi / 180
	cos, sin := math.Cos(phi), math.Sin(phi)
	dx, dy := (p0.X-p1.X)/2, (p0.Y-p1.Y)/2
	x1 := cos*dx + sin*dy
	y1 := -sin*dx + cos*dy
	// Scale up the radii if they are too small.
	if l := x1*x1/(rx*rx) + y1*y1/(ry*ry); l > 1 {
		s := math.Sqrt(l)
		rx, ry = rx*s, ry*s
	}
	num := rx*rx*ry*ry - rx*rx*y1*y1 - ry*ry*x1*x1
	den := rx*rx*y1*y1 + ry*ry*x1*x1
	co := 0.0
	if den > 0 && num > 0 {
		co = math.Sqrt(num / den)
	}
	if large == sweep {
		co = -co
	}
	cx1 := co * rx * y1 / ry
	cy1 := -co * ry * x1 / rx
	cx := cos*cx1 - sin*cy1 + (p0.X+p1.X)/2
	cy := sin*cx1 + cos*cy1 + (p0.Y+p1.Y)/2
	ang := func(ux, uy, vx, vy float64) float64 {
		return math.Atan2(ux*vy-uy*vx, ux*vx+uy*vy)
	}
	t1 := ang(1, 0, (x1-cx1)/rx, (y1-cy1)/ry)
	dt := ang((x1-cx1)/rx, (y1-cy1)/ry, (-x1-cx1)/rx, (-y1-cy1)/ry)
	if !sweep && dt > 0 {
		dt -= 2 * math.Pi
	} else if sweep && dt < 0 {
		dt += 2 * math.Pi
	}
	n := arcSegments(math.Max(rx, ry), dt, tol)
	for i := 1; i <= n; i++ {
		t := t1 + dt*float64(i)/float64(n)
		x, y := rx*math.Cos(t), ry*math.Sin(t)
		pl = append(pl, Pt{cos*x - sin*y + cx, sin*x + cos*y + cy})
	}
	pl[len(pl)-1] = p1
	return pl
}

// parseTransform reads a transform attribute.
func parseTransform(s string) (matrix, error) {
	m := ident
	s = strings.TrimSpace(s)
	for s != "" {
		open := strings.IndexByte(s, '(')
		cl := strings.IndexByte(s, ')')
		if open < 0 || cl < open {
			return ident, fmt.Errorf("svg: bad transform %q", s)
		}
		name := strings.TrimSpace(strings.Trim(s[:open], ", "))
		v := numbers(s[open+1 : cl])
		var t matrix
		switch name {
		case "matrix":
			if len(v) != 6 {
				return ident, fmt.Errorf("svg: matrix needs 6 numbers")
			}
			t = matrix{v[0], v[1], v[2], v[3], v[4], v[5]}
		case "translate":
			if len(v) == 1 {
				v = append(v, 0)
			}
			if len(v) < 2 {
				return ident, fmt.Errorf("svg: bad translate")
			}
			t = matrix{1, 0, 0, 1, v[0], v[1]}
		case "scale":
			if len(v) == 1 {
				v = append(v, v[0])
			}
			if len(v) < 2 {
				return ident, fmt.Errorf("svg: bad scale")
			}
			t = matrix{v[0], 0, 0, v[1], 0, 0}
		case "rotate":
			if len(v) == 0 {
				return ident, fmt.Errorf("svg: bad rotate")
			}
			a := v[0] * math.Pi / 180
			r := matrix{math.Cos(a), math.Sin(a), -math.Sin(a), math.Cos(a), 0, 0}
			if len(v) == 3 {
				t = matrix{1, 0, 0, 1, v[1], v[2]}.mul(r).mul(matrix{1, 0, 0, 1, -v[1], -v[2]})
			} else {
				t = r
			}
		case "skewX":
			if len(v) < 1 {
				return ident, fmt.Errorf("svg: bad skewX")
			}
			t = matrix{1, 0, math.Tan(v[0] * math.Pi / 180), 1, 0, 0}
		case "skewY":
			if len(v) < 1 {
				return ident, fmt.Errorf("svg: bad skewY")
			}
			t = matrix{1, math.Tan(v[0] * math.Pi / 180), 0, 1, 0, 0}
		default:
			return ident, fmt.Errorf("svg: unknown transform %q", name)
		}
		m = m.mul(t)
		s = strings.TrimSpace(strings.TrimLeft(s[cl+1:], ", "))
	}
	return m, nil
}
