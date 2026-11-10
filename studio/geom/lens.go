package geom

import (
	"errors"
	"math"
)

// Lens is a radial distortion model. Image points are normalised by S (half the image
// diagonal) about the centre (CX, CY). An ideal point is the observed point times
// (1 + K1 r² + K2 r⁴), where r is the normalised radius of the observed point.
// K1 < 0 corrects barrel distortion.
type Lens struct {
	CX, CY, S float64
	K1, K2    float64
}

// NewLens returns a lens with no distortion for a w x h image.
func NewLens(w, h int) Lens {
	return Lens{CX: float64(w) / 2, CY: float64(h) / 2, S: math.Hypot(float64(w), float64(h)) / 2}
}

// Undistort maps an observed image point to the ideal (pinhole) point.
func (l Lens) Undistort(p Pt) Pt {
	if l.K1 == 0 && l.K2 == 0 || l.S == 0 {
		return p
	}
	u, v := (p.X-l.CX)/l.S, (p.Y-l.CY)/l.S
	r2 := u*u + v*v
	f := 1 + l.K1*r2 + l.K2*r2*r2
	return Pt{l.CX + u*f*l.S, l.CY + v*f*l.S}
}

// Distort maps an ideal point to the observed image point (the inverse of Undistort).
func (l Lens) Distort(q Pt) Pt {
	if l.K1 == 0 && l.K2 == 0 || l.S == 0 {
		return q
	}
	qu, qv := (q.X-l.CX)/l.S, (q.Y-l.CY)/l.S
	u, v := qu, qv
	for i := 0; i < 20; i++ {
		r2 := u*u + v*v
		f := 1 + l.K1*r2 + l.K2*r2*r2
		if f <= 0 {
			break
		}
		u, v = qu/f, qv/f
	}
	return Pt{l.CX + u*l.S, l.CY + v*l.S}
}

// Camera maps camera pixels to machine millimetres: first the lens, then the homography.
type Camera struct {
	Lens Lens
	H    H // ideal camera pixels to machine mm
	Hi   H // machine mm to ideal camera pixels
}

// ToMachine maps an observed camera pixel to machine mm.
func (c Camera) ToMachine(p Pt) Pt { return c.H.Apply(c.Lens.Undistort(p)) }

// ToCamera maps machine mm to the observed camera pixel.
func (c Camera) ToCamera(m Pt) Pt { return c.Lens.Distort(c.Hi.Apply(m)) }

// Fit solves the camera from pairs of observed pixels and machine points. With fitK1 and 6 or
// more pairs, it also finds K1 (a 1-D search for the smallest error). It returns the camera and
// the RMS error in mm.
func Fit(px, mm []Pt, w, h int, fitK1 bool) (Camera, float64, error) {
	if len(px) != len(mm) || len(px) < 4 {
		return Camera{}, 0, errors.New("geom: need 4 or more point pairs")
	}
	try := func(k1 float64) (Camera, float64, error) {
		l := NewLens(w, h)
		l.K1 = k1
		ideal := make([]Pt, len(px))
		for i, p := range px {
			ideal[i] = l.Undistort(p)
		}
		hm, err := Solve(ideal, mm)
		if err != nil {
			return Camera{}, 0, err
		}
		hi, err := hm.Inverse()
		if err != nil {
			return Camera{}, 0, err
		}
		return Camera{Lens: l, H: hm, Hi: hi}, RMS(hm, ideal, mm), nil
	}
	if !fitK1 || len(px) < 6 {
		return try(0)
	}
	// Golden section search on K1 in [-0.5, 0.5]. The error is smooth near the answer.
	errAt := func(k float64) float64 {
		_, e, err := try(k)
		if err != nil {
			return math.Inf(1)
		}
		return e
	}
	// A coarse scan first: the error can have more than one dip far from zero.
	best, bestE := 0.0, errAt(0)
	for k := -0.5; k <= 0.5001; k += 0.05 {
		if e := errAt(k); e < bestE {
			best, bestE = k, e
		}
	}
	a, b := best-0.05, best+0.05
	g := (math.Sqrt(5) - 1) / 2
	c, d := b-g*(b-a), a+g*(b-a)
	fc, fd := errAt(c), errAt(d)
	for i := 0; i < 40; i++ {
		if fc < fd {
			b, d, fd = d, c, fc
			c = b - g*(b-a)
			fc = errAt(c)
		} else {
			a, c, fc = c, d, fd
			d = a + g*(b-a)
			fd = errAt(d)
		}
	}
	k := (a + b) / 2
	if errAt(k) > bestE {
		k = best
	}
	return try(k)
}
