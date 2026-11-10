package svg

import (
	"math"
	"strings"
	"testing"
)

func near(a, b, tol float64) bool { return math.Abs(a-b) <= tol }

func TestUnitsAndViewBox(t *testing.T) {
	d, err := Parse(strings.NewReader(`<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 200 100">
	<line x1="0" y1="0" x2="200" y2="100"/></svg>`), Options{})
	if err != nil {
		t.Fatal(err)
	}
	if d.Width != 100 || d.Height != 50 || len(d.Lines) != 1 {
		t.Fatalf("%+v", d)
	}
	e := d.Lines[0][1]
	if !near(e.X, 100, 1e-9) || !near(e.Y, 50, 1e-9) {
		t.Fatalf("end %v", e)
	}
}

func TestPxDefault(t *testing.T) {
	d, err := Parse(strings.NewReader(`<svg width="96" height="96"><rect x="0" y="0" width="96" height="96"/></svg>`), Options{})
	if err != nil {
		t.Fatal(err)
	}
	if !near(d.Width, 25.4, 1e-9) || !near(d.Lines[0][2].X, 25.4, 1e-9) {
		t.Fatalf("%+v", d)
	}
}

func TestPathCommands(t *testing.T) {
	// A square with relative commands, then H/V, then a closed shape.
	ls, err := parsePath("M10,10 h10 v10 H10 z m30,0 l5-5L50 10Z", 0.01)
	if err != nil {
		t.Fatal(err)
	}
	if len(ls) != 2 {
		t.Fatalf("got %d lines", len(ls))
	}
	if len(ls[0]) != 5 || ls[0][4] != (Pt{10, 10}) || ls[0][2] != (Pt{20, 20}) {
		t.Fatalf("first: %v", ls[0])
	}
	if ls[1][0] != (Pt{40, 10}) || ls[1][1] != (Pt{45, 5}) {
		t.Fatalf("second: %v", ls[1])
	}
}

func TestArcHalfCircle(t *testing.T) {
	// A half circle of radius 10 from (0,0) to (20,0), with packed flags.
	ls, err := parsePath("M0 0A10 10 0 0120 0", 0.01)
	if err != nil {
		t.Fatal(err)
	}
	for _, p := range ls[0] {
		if !near(math.Hypot(p.X-10, p.Y), 10, 0.02) {
			t.Fatalf("point %v is not on the circle", p)
		}
	}
	if e := ls[0][len(ls[0])-1]; e != (Pt{20, 0}) {
		t.Fatalf("end %v", e)
	}
	// Sweep 1 in SVG (y down) goes through negative y? It goes clockwise on screen: through y < 0.
	mid := ls[0][len(ls[0])/2]
	if mid.Y > -9 {
		t.Fatalf("mid %v: wrong side", mid)
	}
}

func TestCubicTolerance(t *testing.T) {
	ls, err := parsePath("M0,0 C0,10 10,10 10,0 S20,-10 20,0", 0.01)
	if err != nil {
		t.Fatal(err)
	}
	pl := ls[0]
	if len(pl) < 10 {
		t.Fatalf("too few points: %d", len(pl))
	}
	// The curve at t = 0.5 of the first segment is (5, 7.5).
	best := math.Inf(1)
	for _, p := range pl {
		best = math.Min(best, math.Hypot(p.X-5, p.Y-7.5))
	}
	if best > 0.2 {
		t.Fatalf("mid point far: %v", best)
	}
	if pl[len(pl)-1] != (Pt{20, 0}) {
		t.Fatal("end")
	}
}

func TestTransforms(t *testing.T) {
	d, err := Parse(strings.NewReader(`<svg width="100mm" height="100mm" viewBox="0 0 100 100">
	<g transform="translate(50,50) rotate(90)"><line x1="0" y1="0" x2="10" y2="0"/></g>
	<g transform="matrix(2 0 0 2 0 0)"><g transform="scale(0.5)"><circle cx="10" cy="10" r="5"/></g></g>
	<defs><line x1="0" y1="0" x2="1" y2="1"/></defs></svg>`), Options{})
	if err != nil {
		t.Fatal(err)
	}
	if len(d.Lines) != 2 {
		t.Fatalf("got %d lines", len(d.Lines))
	}
	e := d.Lines[0][1]
	if !near(e.X, 50, 1e-9) || !near(e.Y, 60, 1e-9) {
		t.Fatalf("rotated end %v", e)
	}
	for _, p := range d.Lines[1] {
		if !near(math.Hypot(p.X-10, p.Y-10), 5, 0.06) {
			t.Fatalf("circle point %v", p)
		}
	}
}

func TestNumbers(t *testing.T) {
	v := numbers("1.5.5-2e1,3E-1 .5")
	want := []float64{1.5, 0.5, -20, 0.3, 0.5}
	if len(v) != len(want) {
		t.Fatalf("%v", v)
	}
	for i := range v {
		if !near(v[i], want[i], 1e-12) {
			t.Fatalf("%v", v)
		}
	}
}

func TestColorsAndLayers(t *testing.T) {
	src := `<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
	 width="100mm" height="100mm" viewBox="0 0 100 100">
	 <g inkscape:groupmode="layer" inkscape:label="T2 red" stroke="red">
	   <line x1="0" y1="0" x2="10" y2="0"/>
	   <path d="M0 5 L10 5" style="stroke:#00f"/>
	 </g>
	 <g inkscape:groupmode="layer" inkscape:label="Pen 9">
	   <rect x="1" y="1" width="5" height="5" fill="rgb(0,128,0)" stroke="none"/>
	   <circle cx="50" cy="50" r="4" stroke="#AbC"/>
	 </g>
	</svg>`
	d, err := Parse(strings.NewReader(src), Options{})
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"#ff0000", "#0000ff", "#008000", "#aabbcc"}
	layers := []string{"T2 red", "T2 red", "Pen 9", "Pen 9"}
	if len(d.Colors) != 4 {
		t.Fatalf("colours %v", d.Colors)
	}
	for i := range want {
		if d.Colors[i] != want[i] || d.Layers[i] != layers[i] {
			t.Errorf("line %d: %s %q, want %s %q", i, d.Colors[i], d.Layers[i], want[i], layers[i])
		}
	}
	if ParseColor("rgb(100%, 0%, 50%)") != "#ff0080" || ParseColor("url(#g)") != "" {
		t.Error("ParseColor")
	}
}
