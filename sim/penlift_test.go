package sim

import (
	"os"
	"path/filepath"
	"testing"
)

// A small linkage: the tip meets the tab at 85 degrees, and the lift grows 1 mm for each degree.
// The tip slips off the tab at 150 degrees and stalls on the tab top at 140 degrees.
func testLink() *PenLink {
	t := make([]float64, 181)
	for i := range t {
		if i > 85 && i < 150 {
			t[i] = float64(i - 85)
		}
	}
	return &PenLink{Lift: t, Slip: 150, Stall: 140}
}

func TestLiftAt(t *testing.T) {
	l := testLink()
	cases := []struct{ deg, want float64 }{{0, 0}, {80, 0}, {85, 0}, {86.5, 1.5}, {130, 45}, {-5, 0}, {200, 0}}
	for _, c := range cases {
		if got := liftAt(l.Lift, c.deg); got != c.want {
			t.Errorf("liftAt(%g) = %g, want %g", c.deg, got, c.want)
		}
	}
}

func TestPenTouches(t *testing.T) {
	l := testLink()
	if !penTouches(l, 80, false, 130, 80) {
		t.Error("the pen must touch at the pen-down angle")
	}
	if penTouches(l, 130, false, 130, 80) {
		t.Error("the pen must be up at the pen-up angle")
	}
	if !penTouches(l, 170, false, 130, 80) {
		t.Error("the pen must touch when the horn tip is past the end of the tab")
	}
	if !penTouches(l, 140, true, 130, 80) {
		t.Error("the pen must touch when the horn rests on the top of the tab")
	}
	// No linkage: the old rule (90 % of the move).
	if penTouches(nil, 100, false, 130, 80) || !penTouches(nil, 84, false, 130, 80) {
		t.Error("the rule with no linkage is wrong")
	}
}

func TestHornStall(t *testing.T) {
	l := testLink()
	over := false
	if h := l.stop(130, &over, false); h != 130 || over {
		t.Fatalf("pen up: horn %g, over %v", h, over)
	}
	if l.stop(160, &over, false); !over {
		t.Fatal("above the slip angle the tip must be over the tab")
	}
	if h := l.stop(130, &over, false); h != 140 || !over {
		t.Errorf("back to pen up: horn %g, over %v; want a stall at 140", h, over)
	}
	if h := l.stop(130, &over, true); h != 130 || over {
		t.Errorf("after FreeHorn: horn %g, over %v", h, over)
	}
}

func TestLoadPenLink(t *testing.T) {
	dir := t.TempDir()
	p := filepath.Join(dir, "frame.json")
	if err := os.WriteFile(p, []byte(`{"units":"mm"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadPenLink(p); err == nil {
		t.Error("a frame.json with no pen_lift must give an error")
	}
	real := filepath.Join("..", "hardware", "stl", "frame.json")
	if _, err := os.Stat(real); err != nil {
		t.Skip("no hardware/stl/frame.json")
	}
	l, err := LoadPenLink(real)
	if err != nil {
		t.Skip(err) // an older frame.json
	}
	if liftAt(l.Lift, 80) > 0 {
		t.Errorf("at 80 deg (pen down) the lift is %g mm: the pen is not on the paper", liftAt(l.Lift, 80))
	}
	if liftAt(l.Lift, 130) < 5 {
		t.Errorf("at 130 deg (pen up) the lift is only %g mm", liftAt(l.Lift, 130))
	}
	if l.Slip <= 130 {
		t.Errorf("the tip slips off the tab at %g deg, below pen up", l.Slip)
	}
}
