// Package svg reads the drawing of an SVG file as polylines in millimetres.
// It reads path, line, polyline, polygon, rect, circle and ellipse elements, groups with
// transforms, and the viewBox. It ignores fills, text and images.
package svg

import (
	"encoding/xml"
	"errors"
	"io"
	"math"
	"strconv"
	"strings"
)

// Pt is a point in millimetres. Y points down, as in SVG.
type Pt struct{ X, Y float64 }

// Polyline is one pen stroke.
type Polyline []Pt

// Drawing is the result of a parse.
type Drawing struct {
	Lines  []Polyline
	Colors []string // the stroke colour of each line, "#rrggbb" (the fill colour when there is no stroke)
	Layers []string // the Inkscape layer (or top-level group) label of each line, or ""
	Width  float64  // the document size in mm (from width/height or the viewBox)
	Height float64
}

// Options control the parse.
type Options struct {
	Tolerance float64 // the largest distance between a curve and its polyline, in mm (default 0.05)
	DPI       float64 // the size of a user unit with no unit (default 96 per inch)
}

// matrix is an affine transform [a c e; b d f].
type matrix [6]float64

var ident = matrix{1, 0, 0, 1, 0, 0}

func (m matrix) apply(p Pt) Pt {
	return Pt{m[0]*p.X + m[2]*p.Y + m[4], m[1]*p.X + m[3]*p.Y + m[5]}
}

// mul returns m·n: first n, then m.
func (m matrix) mul(n matrix) matrix {
	return matrix{
		m[0]*n[0] + m[2]*n[1], m[1]*n[0] + m[3]*n[1],
		m[0]*n[2] + m[2]*n[3], m[1]*n[2] + m[3]*n[3],
		m[0]*n[4] + m[2]*n[5] + m[4], m[1]*n[4] + m[3]*n[5] + m[5],
	}
}

// scale returns the mean scale of m (for the curve tolerance).
func (m matrix) scale() float64 {
	return math.Sqrt(math.Abs(m[0]*m[3] - m[1]*m[2]))
}

// Parse reads an SVG document.
func Parse(r io.Reader, opt Options) (*Drawing, error) {
	if opt.Tolerance <= 0 {
		opt.Tolerance = 0.05
	}
	if opt.DPI <= 0 {
		opt.DPI = 96
	}
	unit := 25.4 / opt.DPI
	dec := xml.NewDecoder(r)
	dec.Strict = false
	dec.AutoClose = xml.HTMLAutoClose
	dec.Entity = xml.HTMLEntity
	d := &Drawing{}
	var stack []matrix
	var pstack []paint
	pcur := paint{stroke: "", fill: "#000000"}
	depth := 0 // element depth below the svg root
	cur := ident
	root := true
	skip := 0 // depth inside defs, clipPath and similar elements
	for {
		tok, err := dec.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		switch t := tok.(type) {
		case xml.StartElement:
			stack = append(stack, cur)
			pstack = append(pstack, pcur)
			depth++
			name := t.Name.Local
			if skip > 0 || name == "defs" || name == "clipPath" || name == "mask" || name == "symbol" ||
				name == "marker" || name == "pattern" || name == "metadata" || name == "style" || name == "title" {
				skip++
				continue
			}
			a := attrs(t)
			if root && name == "svg" {
				root = false
				cur = svgRoot(a, unit, d)
			}
			if tr, ok := a["transform"]; ok {
				m, err := parseTransform(tr)
				if err != nil {
					return nil, err
				}
				cur = cur.mul(m)
			}
			if a["display"] == "none" || strings.Contains(strings.ReplaceAll(a["style"], " ", ""), "display:none") {
				skip++
				continue
			}
			pcur = inheritPaint(pcur, a)
			if name == "g" && (a["groupmode"] == "layer" || depth == 2) {
				if l := a["label"]; l != "" {
					pcur.layer = l
				} else if l := a["id"]; l != "" && a["groupmode"] == "layer" {
					pcur.layer = l
				}
			}
			tol := opt.Tolerance / math.Max(cur.scale(), 1e-9)
			var lines []Polyline
			switch name {
			case "path":
				lines, err = parsePath(a["d"], tol)
			case "line":
				lines = []Polyline{{{num(a["x1"]), num(a["y1"])}, {num(a["x2"]), num(a["y2"])}}}
			case "polyline", "polygon":
				pts := numbers(a["points"])
				var pl Polyline
				for i := 0; i+1 < len(pts); i += 2 {
					pl = append(pl, Pt{pts[i], pts[i+1]})
				}
				if name == "polygon" && len(pl) > 2 {
					pl = append(pl, pl[0])
				}
				if len(pl) > 1 {
					lines = []Polyline{pl}
				}
			case "rect":
				lines = rect(num(a["x"]), num(a["y"]), num(a["width"]), num(a["height"]), a["rx"], a["ry"], tol)
			case "circle":
				r := num(a["r"])
				lines = ellipse(num(a["cx"]), num(a["cy"]), r, r, tol)
			case "ellipse":
				lines = ellipse(num(a["cx"]), num(a["cy"]), num(a["rx"]), num(a["ry"]), tol)
			}
			if err != nil {
				return nil, err
			}
			col := pcur.stroke
			if col == "" || col == "none" {
				col = pcur.fill
			}
			if col == "" || col == "none" {
				col = "#000000"
			}
			for _, l := range lines {
				out := make(Polyline, len(l))
				for i, p := range l {
					out[i] = cur.apply(p)
				}
				d.Lines = append(d.Lines, out)
				d.Colors = append(d.Colors, col)
				d.Layers = append(d.Layers, pcur.layer)
			}
		case xml.EndElement:
			if len(stack) > 0 {
				cur = stack[len(stack)-1]
				stack = stack[:len(stack)-1]
			}
			if len(pstack) > 0 {
				pcur = pstack[len(pstack)-1]
				pstack = pstack[:len(pstack)-1]
			}
			depth--
			if skip > 0 {
				skip--
			}
		}
	}
	if root {
		return nil, errors.New("svg: no svg element")
	}
	return d, nil
}

func attrs(t xml.StartElement) map[string]string {
	a := map[string]string{}
	for _, x := range t.Attr {
		a[x.Name.Local] = strings.TrimSpace(x.Value)
	}
	// Presentation values in style="" (only display is used).
	for _, kv := range strings.Split(a["style"], ";") {
		if k, v, ok := strings.Cut(kv, ":"); ok && strings.TrimSpace(k) == "display" {
			a["display"] = strings.TrimSpace(v)
		}
	}
	return a
}

// length reads a length with a unit, in mm. unit is the size of a user unit in mm.
func length(s string, unit float64) (float64, bool) {
	s = strings.TrimSpace(s)
	if s == "" || strings.HasSuffix(s, "%") {
		return 0, false
	}
	units := map[string]float64{"mm": 1, "cm": 10, "in": 25.4, "pt": 25.4 / 72, "pc": 25.4 / 6, "px": unit, "q": 0.25}
	for u, f := range units {
		if strings.HasSuffix(strings.ToLower(s), u) {
			v, err := strconv.ParseFloat(strings.TrimSpace(s[:len(s)-len(u)]), 64)
			return v * f, err == nil
		}
	}
	v, err := strconv.ParseFloat(s, 64)
	return v * unit, err == nil
}

// svgRoot sets the size of the drawing and returns the transform from user units to mm.
func svgRoot(a map[string]string, unit float64, d *Drawing) matrix {
	w, okW := length(a["width"], unit)
	h, okH := length(a["height"], unit)
	vb := numbers(a["viewBox"])
	if len(vb) == 4 && vb[2] > 0 && vb[3] > 0 {
		if !okW && !okH {
			w, h = vb[2]*unit, vb[3]*unit
		} else if !okW {
			w = h * vb[2] / vb[3]
		} else if !okH {
			h = w * vb[3] / vb[2]
		}
		d.Width, d.Height = w, h
		sx, sy := w/vb[2], h/vb[3]
		// preserveAspectRatio: the default xMidYMid meet.
		s := math.Min(sx, sy)
		if strings.HasPrefix(strings.TrimSpace(a["preserveAspectRatio"]), "none") {
			return matrix{sx, 0, 0, sy, -vb[0] * sx, -vb[1] * sy}
		}
		tx := (w - vb[2]*s) / 2
		ty := (h - vb[3]*s) / 2
		return matrix{s, 0, 0, s, tx - vb[0]*s, ty - vb[1]*s}
	}
	d.Width, d.Height = w, h
	return matrix{unit, 0, 0, unit, 0, 0}
}

func num(s string) float64 {
	v, _ := strconv.ParseFloat(strings.TrimSpace(strings.TrimSuffix(strings.TrimSpace(s), "px")), 64)
	return v
}

// numbers reads a list of numbers separated by spaces or commas.
func numbers(s string) []float64 {
	sc := scanner{s: s}
	var out []float64
	for {
		v, ok := sc.number()
		if !ok {
			return out
		}
		out = append(out, v)
	}
}

func rect(x, y, w, h float64, rxs, rys string, tol float64) []Polyline {
	if w <= 0 || h <= 0 {
		return nil
	}
	rx, okx := strconv.ParseFloat(rxs, 64)
	ry, oky := strconv.ParseFloat(rys, 64)
	if okx != nil && oky == nil {
		rx = ry
	}
	if oky != nil && okx == nil {
		ry = rx
	}
	if okx != nil && oky != nil {
		rx, ry = 0, 0
	}
	rx, ry = math.Min(math.Max(rx, 0), w/2), math.Min(math.Max(ry, 0), h/2)
	if rx == 0 || ry == 0 {
		return []Polyline{{{x, y}, {x + w, y}, {x + w, y + h}, {x, y + h}, {x, y}}}
	}
	var pl Polyline
	corner := func(cx, cy, a0 float64) {
		n := arcSegments(math.Max(rx, ry), math.Pi/2, tol)
		for i := 0; i <= n; i++ {
			a := a0 + math.Pi/2*float64(i)/float64(n)
			pl = append(pl, Pt{cx + rx*math.Cos(a), cy + ry*math.Sin(a)})
		}
	}
	corner(x+w-rx, y+ry, -math.Pi/2)
	corner(x+w-rx, y+h-ry, 0)
	corner(x+rx, y+h-ry, math.Pi/2)
	corner(x+rx, y+ry, math.Pi)
	pl = append(pl, pl[0])
	return []Polyline{pl}
}

func ellipse(cx, cy, rx, ry, tol float64) []Polyline {
	if rx <= 0 || ry <= 0 {
		return nil
	}
	n := arcSegments(math.Max(rx, ry), 2*math.Pi, tol)
	pl := make(Polyline, 0, n+1)
	for i := 0; i <= n; i++ {
		a := 2 * math.Pi * float64(i) / float64(n)
		pl = append(pl, Pt{cx + rx*math.Cos(a), cy + ry*math.Sin(a)})
	}
	return []Polyline{pl}
}

// arcSegments returns the number of chords for an arc of radius r and angle sweep, so that
// each chord stays within tol of the arc.
func arcSegments(r, sweep, tol float64) int {
	if r <= tol {
		return 4
	}
	step := 2 * math.Acos(1-tol/r)
	n := int(math.Ceil(math.Abs(sweep) / step))
	return max(n, 4)
}

// paint is the inherited stroke and fill colour and the layer label.
type paint struct{ stroke, fill, layer string }

// inheritPaint applies the stroke and fill of an element (attributes, then the style
// attribute, which wins) to the inherited values.
func inheritPaint(p paint, a map[string]string) paint {
	set := func(key, v string) {
		v = strings.TrimSpace(v)
		if v == "" || v == "inherit" {
			return
		}
		c := ParseColor(v)
		if v == "none" {
			c = "none"
		}
		if c == "" {
			return
		}
		if key == "stroke" {
			p.stroke = c
		} else {
			p.fill = c
		}
	}
	set("stroke", a["stroke"])
	set("fill", a["fill"])
	for _, decl := range strings.Split(a["style"], ";") {
		k, v, ok := strings.Cut(decl, ":")
		if !ok {
			continue
		}
		switch strings.TrimSpace(k) {
		case "stroke":
			set("stroke", v)
		case "fill":
			set("fill", v)
		}
	}
	return p
}

var namedColors = map[string]string{
	"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "lime": "#00ff00",
	"blue": "#0000ff", "yellow": "#ffff00", "cyan": "#00ffff", "aqua": "#00ffff", "magenta": "#ff00ff",
	"fuchsia": "#ff00ff", "gray": "#808080", "grey": "#808080", "silver": "#c0c0c0", "maroon": "#800000",
	"olive": "#808000", "purple": "#800080", "teal": "#008080", "navy": "#000080", "orange": "#ffa500",
	"brown": "#a52a2a", "pink": "#ffc0cb", "gold": "#ffd700", "violet": "#ee82ee", "indigo": "#4b0082",
	"darkgreen": "#006400", "darkblue": "#00008b", "darkred": "#8b0000", "lightblue": "#add8e6",
	"skyblue": "#87ceeb", "turquoise": "#40e0d0", "crimson": "#dc143c", "coral": "#ff7f50",
}

// ParseColor reads a CSS colour: #rgb, #rrggbb, rgb(r, g, b) with numbers or percentages, or
// a common name. It returns "#rrggbb", or "" for a colour it does not know (for example a
// gradient reference).
func ParseColor(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	if c, ok := namedColors[s]; ok {
		return c
	}
	if strings.HasPrefix(s, "#") {
		h := s[1:]
		if len(h) == 3 {
			h = string([]byte{h[0], h[0], h[1], h[1], h[2], h[2]})
		}
		if len(h) == 6 {
			if _, err := strconv.ParseUint(h, 16, 32); err == nil {
				return "#" + h
			}
		}
		return ""
	}
	if strings.HasPrefix(s, "rgb(") && strings.HasSuffix(s, ")") {
		parts := strings.Split(s[4:len(s)-1], ",")
		if len(parts) != 3 {
			return ""
		}
		var v [3]int
		for i, p := range parts {
			p = strings.TrimSpace(p)
			if strings.HasSuffix(p, "%") {
				f, err := strconv.ParseFloat(strings.TrimSuffix(p, "%"), 64)
				if err != nil {
					return ""
				}
				v[i] = int(math.Round(f * 255 / 100))
			} else {
				f, err := strconv.ParseFloat(p, 64)
				if err != nil {
					return ""
				}
				v[i] = int(math.Round(f))
			}
			v[i] = max(0, min(255, v[i]))
		}
		return "#" + hex2(v[0]) + hex2(v[1]) + hex2(v[2])
	}
	return ""
}

func hex2(v int) string { return strconv.FormatInt(int64(256+v), 16)[1:] }
