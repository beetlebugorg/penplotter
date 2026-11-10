package sim

import (
	"image/color"
	"math"
	"testing"
)

func TestCameraProjectAndRender(t *testing.T) {
	m := New()
	c := NewCamera(m, CameraOptions{W: 324, H: 243})
	// The whole frame opening is in the picture.
	for _, p := range []vec3{{40, 20, 0}, {360, 20, 0}, {360, 500, 0}, {40, 500, 0}} {
		u, v, ok := c.Project(p, 324, 243)
		if !ok || u < 0 || v < 0 || u > 324 || v > 243 {
			t.Fatalf("%v is outside the picture: %v %v", p, u, v)
		}
	}
	img := c.Render(324, 243)
	// The centre of the paper is white or the document.
	pc := vec3{c.geo.homePen[0] + 113, c.geo.homePen[1] + 182, 0}
	u, v, _ := c.Project(pc, 324, 243)
	px := img.RGBAAt(int(u), int(v))
	if px.R < 200 || px.G < 200 {
		t.Fatalf("paper centre colour %v", px)
	}
	_ = color.RGBA{}
	// Distortion round trip.
	c.opt.K1 = -0.08
	a, b := c.distort(100, 80, 324, 243)
	x, y := c.undistort(a, b, 324, 243)
	if math.Abs(x-100) > 1e-6 || math.Abs(y-80) > 1e-6 {
		t.Fatalf("lens %v %v", x, y)
	}
}
