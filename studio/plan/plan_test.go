package plan

import (
	"math"
	"strings"
	"testing"
)

func TestPlaceUprightAndRotation(t *testing.T) {
	// A 20 x 10 drawing. Its top left corner (0,0) goes to the back left of the item.
	it := Item{Lines: [][]Pt{{{0, 0}, {20, 10}}}, W: 20, H: 10, X: 100, Y: 50, Scale: 2}
	l := it.Place()[0]
	if l[0] != (Pt{80, 60}) || l[1] != (Pt{120, 40}) {
		t.Fatalf("%v", l)
	}
	it.Angle = 90
	l = it.Place()[0]
	if math.Abs(l[0].X-90) > 1e-9 || math.Abs(l[0].Y-30) > 1e-9 {
		t.Fatalf("rotated %v", l)
	}
}

func TestCheck(t *testing.T) {
	if err := Check([][]Pt{{{0, 0}, {216, 380}}}, 216, 380); err != nil {
		t.Fatal(err)
	}
	if err := Check([][]Pt{{{-1, 0}}}, 216, 380); err == nil {
		t.Fatal("want an error")
	}
}

func TestOrderShortensTravel(t *testing.T) {
	lines := [][]Pt{
		{{100, 0}, {110, 0}},
		{{0, 0}, {10, 0}},
		{{60, 0}, {50, 0}},
		{{20, 0}, {30, 0}},
	}
	o := Order(lines, Pt{})
	if TravelLength(o, Pt{}) > TravelLength(lines, Pt{})-1 {
		t.Fatalf("no gain: %v", o)
	}
	if o[0][0] != (Pt{0, 0}) || o[2][0] != (Pt{50, 0}) {
		t.Fatalf("order %v", o)
	}
}

func TestGCode(t *testing.T) {
	park := Pt{0, 380}
	g := GCode([][]Pt{{{1, 2}, {3, 4}}, {{3, 4}, {5, 6}}, {{10, 10}, {11, 10}}}, Options{Feed: 1200, Home: true, Park: &park})
	for _, want := range []string{"G21\nG90\nM5\nG28\n", "G0 X1 Y2\nM3\nG1 F1200\nG1 X3 Y4\nG1 X5 Y6\nM5\nG0 X10 Y10\n", "G0 X0 Y380\nM400\n"} {
		if !strings.Contains(g, want) {
			t.Fatalf("missing %q in\n%s", want, g)
		}
	}
	if strings.Count(g, "M3") != 2 {
		t.Fatalf("pen downs:\n%s", g)
	}
}

func TestGrid(t *testing.T) {
	if len(Grid(0, 216, 380, 10)) != 5 || len(Grid(4, 216, 380, 10)) != 16 {
		t.Fatal("grid size")
	}
	g := Grid(3, 200, 300, 10)
	if g[0] != (Pt{10, 10}) || g[8] != (Pt{190, 290}) {
		t.Fatalf("%v", g)
	}
}
