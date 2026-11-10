// Package geom has the plane geometry of plotstudio: points, homographies, and image warps.
package geom

import (
	"errors"
	"math"
)

// Pt is a point in the plane.
type Pt struct{ X, Y float64 }

// H is a 3x3 homography, row-major. It maps (x, y, 1) to (u, v, w).
type H [9]float64

// Identity returns the identity homography.
func Identity() H { return H{1, 0, 0, 0, 1, 0, 0, 0, 1} }

// Apply maps p through h.
func (h H) Apply(p Pt) Pt {
	u := h[0]*p.X + h[1]*p.Y + h[2]
	v := h[3]*p.X + h[4]*p.Y + h[5]
	w := h[6]*p.X + h[7]*p.Y + h[8]
	if w == 0 {
		return Pt{math.Inf(1), math.Inf(1)}
	}
	return Pt{u / w, v / w}
}

// Mul returns a·b: first b, then a.
func Mul(a, b H) H {
	var r H
	for i := 0; i < 3; i++ {
		for j := 0; j < 3; j++ {
			r[i*3+j] = a[i*3]*b[j] + a[i*3+1]*b[3+j] + a[i*3+2]*b[6+j]
		}
	}
	return r
}

// Inverse returns the inverse of h.
func (h H) Inverse() (H, error) {
	a, b, c, d, e, f, g, k, l := h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], h[8]
	A := e*l - f*k
	B := -(d*l - f*g)
	C := d*k - e*g
	det := a*A + b*B + c*C
	if math.Abs(det) < 1e-15 {
		return H{}, errors.New("geom: the homography has no inverse")
	}
	inv := H{
		A, -(b*l - c*k), b*f - c*e,
		B, a*l - c*g, -(a*f - c*d),
		C, -(a*k - b*g), a*e - b*d,
	}
	for i := range inv {
		inv[i] /= det
	}
	return inv, nil
}

// Normalise scales h so that h[8] is 1 (if possible).
func (h H) Normalise() H {
	if h[8] == 0 {
		return h
	}
	s := h[8]
	for i := range h {
		h[i] /= s
	}
	return h
}

// normaliser returns the similarity that moves the centroid of pts to the origin and makes
// the mean distance from it sqrt(2) (Hartley normalisation).
func normaliser(pts []Pt) H {
	var cx, cy float64
	for _, p := range pts {
		cx += p.X
		cy += p.Y
	}
	n := float64(len(pts))
	cx /= n
	cy /= n
	var d float64
	for _, p := range pts {
		d += math.Hypot(p.X-cx, p.Y-cy)
	}
	d /= n
	s := 1.0
	if d > 0 {
		s = math.Sqrt2 / d
	}
	return H{s, 0, -s * cx, 0, s, -s * cy, 0, 0, 1}
}

// Solve finds the homography that maps src[i] to dst[i]. It needs 4 or more pairs. With more
// than 4 pairs it gives the least-squares solution (h33 = 1) on normalised points.
func Solve(src, dst []Pt) (H, error) {
	if len(src) != len(dst) || len(src) < 4 {
		return H{}, errors.New("geom: need 4 or more point pairs")
	}
	ts, td := normaliser(src), normaliser(dst)
	// Normal equations of the 2N x 8 system A·h = b.
	var ata [8][8]float64
	var atb [8]float64
	add := func(row [8]float64, b float64) {
		for i := 0; i < 8; i++ {
			for j := 0; j < 8; j++ {
				ata[i][j] += row[i] * row[j]
			}
			atb[i] += row[i] * b
		}
	}
	for i := range src {
		s, d := ts.Apply(src[i]), td.Apply(dst[i])
		x, y, u, v := s.X, s.Y, d.X, d.Y
		add([8]float64{x, y, 1, 0, 0, 0, -u * x, -u * y}, u)
		add([8]float64{0, 0, 0, x, y, 1, -v * x, -v * y}, v)
	}
	h8, err := solve8(ata, atb)
	if err != nil {
		return H{}, err
	}
	hn := H{h8[0], h8[1], h8[2], h8[3], h8[4], h8[5], h8[6], h8[7], 1}
	tdi, err := td.Inverse()
	if err != nil {
		return H{}, err
	}
	return Mul(tdi, Mul(hn, ts)).Normalise(), nil
}

// solve8 solves a·x = b by Gaussian elimination with partial pivoting.
func solve8(a [8][8]float64, b [8]float64) ([8]float64, error) {
	const n = 8
	for c := 0; c < n; c++ {
		p := c
		for r := c + 1; r < n; r++ {
			if math.Abs(a[r][c]) > math.Abs(a[p][c]) {
				p = r
			}
		}
		if math.Abs(a[p][c]) < 1e-12 {
			return [8]float64{}, errors.New("geom: the points are degenerate (three in one line?)")
		}
		a[c], a[p] = a[p], a[c]
		b[c], b[p] = b[p], b[c]
		for r := c + 1; r < n; r++ {
			f := a[r][c] / a[c][c]
			for k := c; k < n; k++ {
				a[r][k] -= f * a[c][k]
			}
			b[r] -= f * b[c]
		}
	}
	var x [8]float64
	for r := n - 1; r >= 0; r-- {
		s := b[r]
		for k := r + 1; k < n; k++ {
			s -= a[r][k] * x[k]
		}
		x[r] = s / a[r][r]
	}
	return x, nil
}

// RMS returns the root mean square distance between h(src[i]) and dst[i].
func RMS(h H, src, dst []Pt) float64 {
	if len(src) == 0 {
		return 0
	}
	var s float64
	for i := range src {
		p := h.Apply(src[i])
		s += (p.X-dst[i].X)*(p.X-dst[i].X) + (p.Y-dst[i].Y)*(p.Y-dst[i].Y)
	}
	return math.Sqrt(s / float64(len(src)))
}
