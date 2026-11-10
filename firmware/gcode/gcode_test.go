package gcode

import (
	"math"
	"testing"
)

func TestParse(t *testing.T) {
	var l Line
	if err := Parse([]byte("N10 g1x10.5 Y-3 (comment) F3000 ; tail"), &l); err != nil {
		t.Fatal(err)
	}
	want := []Word{{'G', 1}, {'X', 10.5}, {'Y', -3}, {'F', 3000}}
	if l.N != len(want) {
		t.Fatalf("got %d words, want %d", l.N, len(want))
	}
	for i, w := range want {
		if l.W[i] != w {
			t.Errorf("word %d: got %c%v, want %c%v", i, l.W[i].L, l.W[i].V, w.L, w.V)
		}
	}
	if v, ok := l.Get('Y'); !ok || v != -3 {
		t.Errorf("Get Y = %v %v", v, ok)
	}
	if err := Parse([]byte("G X1"), &l); err != ErrBadNumber {
		t.Errorf("missing number: got %v", err)
	}
	if err := Parse([]byte("G28 X Y"), &l); err != nil || l.N != 3 || !l.Has('Y') {
		t.Errorf("axis words without numbers: %v %d", err, l.N)
	}
	if err := Parse([]byte("G1 X-"), &l); err != ErrBadNumber {
		t.Errorf("sign only: got %v", err)
	}
	if err := Parse([]byte("G1 X.5 *42"), &l); err != nil || l.W[1].V != 0.5 {
		t.Errorf("checksum: %v %v", err, l.W[1])
	}
	if err := Parse([]byte("# 1"), &l); err != ErrBadLetter {
		t.Errorf("bad letter: got %v", err)
	}
}

func TestArcQuarter(t *testing.T) {
	// Counter-clockwise quarter circle around (0,0) with radius 10.
	a, ok := NewArc(10, 0, 0, 10, -10, 0, 0, false, 1, 0.01)
	if !ok {
		t.Fatal("arc rejected")
	}
	n := 0
	var x, y float32
	for {
		px, py, ok := a.Next()
		if !ok {
			break
		}
		x, y = px, py
		n++
		r := math.Hypot(float64(px), float64(py))
		if math.Abs(r-10) > 1e-3 {
			t.Fatalf("point %d off the circle: r=%v", n, r)
		}
		if px < -1e-3 || py < -1e-3 {
			t.Fatalf("point %d outside the first quadrant: %v %v", n, px, py)
		}
	}
	if x != 0 || y != 10 {
		t.Errorf("end = %v %v", x, y)
	}
	if n < 16 {
		t.Errorf("only %d points", n)
	}
}

func TestArcFullCircleAndRadius(t *testing.T) {
	// Full circle: start equals end.
	a, ok := NewArc(5, 0, 5, 0, -5, 0, 0, true, 1, 0.01)
	if !ok || a.Left() < 30 {
		t.Fatalf("full circle: ok=%v points=%d", ok, a.Left())
	}
	// Clockwise half circle with R.
	b, ok := NewArc(0, 0, 20, 0, 0, 0, 10, true, 1, 0.01)
	if !ok {
		t.Fatal("R arc rejected")
	}
	maxY := float32(-1)
	for {
		_, y, ok := b.Next()
		if !ok {
			break
		}
		if y > maxY {
			maxY = y
		}
	}
	if math.Abs(float64(maxY)-10) > 0.05 {
		t.Errorf("clockwise half circle from left to right goes over the top: max y %v", maxY)
	}
}
