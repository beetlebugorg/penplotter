package gcode

import "math"

// Arc splits a G2/G3 arc into points on the arc.
// The last point is exactly the end point.
type Arc struct {
	cx, cy   float64
	r        float64
	a0, step float64
	n, i     int
	ex, ey   float32
}

// NewArc makes an arc from start (sx, sy) to end (ex, ey).
// The center is the start plus (ci, cj). cw is true for G2.
// If r is not 0, the arc uses radius r (R word) and ignores ci, cj.
// maxSeg is the maximum line length and tol the maximum chord error, in mm.
func NewArc(sx, sy, ex, ey, ci, cj, r float32, cw bool, maxSeg, tol float32) (Arc, bool) {
	var a Arc
	a.ex, a.ey = ex, ey
	if r != 0 {
		// Center from the radius. A negative R selects the arc over 180 degrees.
		dx, dy := float64(ex-sx), float64(ey-sy)
		d := math.Hypot(dx, dy)
		rr := math.Abs(float64(r))
		if d == 0 || d > 2*rr+1e-6 {
			return a, false
		}
		h := math.Sqrt(math.Max(rr*rr-d*d/4, 0))
		mx, my := float64(sx)+dx/2, float64(sy)+dy/2
		// Unit normal to the left of the chord.
		nx, ny := -dy/d, dx/d
		side := 1.0
		if cw {
			side = -1
		}
		if r < 0 {
			side = -side
		}
		ci = float32(mx + side*h*nx - float64(sx))
		cj = float32(my + side*h*ny - float64(sy))
	}
	a.cx = float64(sx) + float64(ci)
	a.cy = float64(sy) + float64(cj)
	a.r = math.Hypot(float64(ci), float64(cj))
	if a.r == 0 {
		return a, false
	}
	a.a0 = math.Atan2(float64(sy)-a.cy, float64(sx)-a.cx)
	a1 := math.Atan2(float64(ey)-a.cy, float64(ex)-a.cx)
	sweep := a1 - a.a0
	if cw {
		if sweep >= -1e-9 {
			sweep -= 2 * math.Pi
		}
	} else if sweep <= 1e-9 {
		sweep += 2 * math.Pi
	}
	seg := float64(maxSeg)
	if t := float64(tol); t > 0 && t < a.r {
		chord := 2 * math.Sqrt(t*(2*a.r-t))
		if chord < seg {
			seg = chord
		}
	}
	n := int(math.Ceil(math.Abs(sweep) * a.r / seg))
	if n < 1 {
		n = 1
	}
	a.n = n
	a.step = sweep / float64(n)
	return a, true
}

// Next returns the next point. It returns false after the end point.
func (a *Arc) Next() (x, y float32, ok bool) {
	if a.i >= a.n {
		return 0, 0, false
	}
	a.i++
	if a.i == a.n {
		return a.ex, a.ey, true
	}
	t := a.a0 + a.step*float64(a.i)
	return float32(a.cx + a.r*math.Cos(t)), float32(a.cy + a.r*math.Sin(t)), true
}

// Left returns the number of points that remain.
func (a *Arc) Left() int { return a.n - a.i }
