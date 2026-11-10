package geom

import (
	"image"
	"image/color"
	"math"
	"math/rand"
	"testing"
)

func near(a, b Pt, tol float64) bool { return math.Hypot(a.X-b.X, a.Y-b.Y) <= tol }

func TestSolveExact(t *testing.T) {
	want := H{1.2, 0.1, 30, -0.05, 0.9, 12, 0.0004, -0.0002, 1}
	src := []Pt{{0, 0}, {300, 0}, {300, 400}, {0, 400}}
	var dst []Pt
	for _, p := range src {
		dst = append(dst, want.Apply(p))
	}
	h, err := Solve(src, dst)
	if err != nil {
		t.Fatal(err)
	}
	for _, p := range []Pt{{10, 20}, {150, 210}, {299, 5}} {
		if !near(h.Apply(p), want.Apply(p), 1e-6) {
			t.Fatalf("at %v: got %v want %v", p, h.Apply(p), want.Apply(p))
		}
	}
}

func TestSolveLeastSquaresAndInverse(t *testing.T) {
	want := H{0.8, -0.2, 640, 0.15, -0.7, 700, 0.0003, 0.0005, 1}
	r := rand.New(rand.NewSource(1))
	var src, dst []Pt
	for i := 0; i < 12; i++ {
		p := Pt{r.Float64() * 216, r.Float64() * 380}
		q := want.Apply(p)
		q.X += r.NormFloat64() * 0.3
		q.Y += r.NormFloat64() * 0.3
		src, dst = append(src, p), append(dst, q)
	}
	h, err := Solve(src, dst)
	if err != nil {
		t.Fatal(err)
	}
	if e := RMS(h, src, dst); e > 0.6 {
		t.Fatalf("rms %v", e)
	}
	inv, err := h.Inverse()
	if err != nil {
		t.Fatal(err)
	}
	p := Pt{100, 200}
	if !near(inv.Apply(h.Apply(p)), p, 1e-6) {
		t.Fatal("inverse round trip")
	}
}

func TestSolveDegenerate(t *testing.T) {
	src := []Pt{{0, 0}, {1, 1}, {2, 2}, {3, 3}}
	if _, err := Solve(src, src); err == nil {
		t.Fatal("want an error for collinear points")
	}
}

func TestWarpShift(t *testing.T) {
	src := image.NewRGBA(image.Rect(0, 0, 20, 20))
	src.SetRGBA(5, 7, color.RGBA{255, 0, 0, 255})
	// Output pixel (x, y) samples src at (x+3, y+4).
	out := Warp(src, H{1, 0, 3, 0, 1, 4, 0, 0, 1}, 10, 10, color.RGBA{})
	if c := out.RGBAAt(2, 3); c.R != 255 {
		t.Fatalf("got %v", c)
	}
	far := Warp(src, H{1, 0, 100, 0, 1, 0, 0, 0, 1}, 4, 4, color.RGBA{1, 2, 3, 255})
	if c := far.RGBAAt(1, 1); c != (color.RGBA{1, 2, 3, 255}) {
		t.Fatalf("background: %v", c)
	}
}

func TestLensRoundTrip(t *testing.T) {
	l := NewLens(1296, 972)
	l.K1 = -0.08
	for _, p := range []Pt{{10, 10}, {648, 486}, {1200, 900}} {
		if q := l.Distort(l.Undistort(p)); !near(q, p, 1e-6) {
			t.Fatalf("%v -> %v", p, q)
		}
	}
}

func TestFitK1(t *testing.T) {
	// A known camera: homography plus barrel distortion.
	truth := Camera{Lens: NewLens(1296, 972)}
	truth.Lens.K1 = -0.08
	truth.Hi = H{3.1, 0.4, 150, -0.2, -2.6, 900, 0.0002, 0.0011, 1}
	truth.H, _ = truth.Hi.Inverse()
	var px, mm []Pt
	for j := 0; j < 4; j++ {
		for i := 0; i < 4; i++ {
			m := Pt{10 + 196*float64(i)/3, 10 + 360*float64(j)/3}
			px, mm = append(px, truth.ToCamera(m)), append(mm, m)
		}
	}
	c0, e0, err := Fit(px, mm, 1296, 972, false)
	if err != nil {
		t.Fatal(err)
	}
	c1, e1, err := Fit(px, mm, 1296, 972, true)
	if err != nil {
		t.Fatal(err)
	}
	if e1 > 0.05 || e1 > e0/5 {
		t.Fatalf("k1 fit: rms %v (without k1 %v), k1 %v", e1, e0, c1.Lens.K1)
	}
	if math.Abs(c1.Lens.K1+0.08) > 0.01 {
		t.Fatalf("k1 %v", c1.Lens.K1)
	}
	_ = c0
}
