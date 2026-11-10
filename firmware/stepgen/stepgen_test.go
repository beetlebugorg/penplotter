package stepgen

import "testing"

func TestMoveExactSteps(t *testing.T) {
	var e Executor
	e.Q.Push(Segment{Kind: Move, Steps: [2]uint16{37, 80}, Ticks: 80, Dir: 2})
	e.Q.Push(Segment{Kind: Move, Steps: [2]uint16{1, 0}, Ticks: 3})
	var n [2]int
	for i := 0; i < 200; i++ {
		o := e.Tick()
		for a := 0; a < 2; a++ {
			if o.Step&(1<<a) != 0 {
				n[a]++
			}
		}
	}
	if n != [2]int{38, 80} {
		t.Errorf("steps = %v", n)
	}
	if e.Pos(0) != 38 || e.Pos(1) != -80 || e.Pos(ChY2) != -80 {
		t.Errorf("pos = %d %d %d", e.Pos(0), e.Pos(1), e.Pos(ChY2))
	}
	if !e.Idle() {
		t.Error("not idle")
	}
}

func TestQueueWrap(t *testing.T) {
	var q Queue
	var s Segment
	for i := 0; i < 1000; i++ {
		if !q.Push(Segment{Line: uint32(i)}) {
			t.Fatal("push failed")
		}
		if !q.pop(&s) || s.Line != uint32(i) {
			t.Fatal("pop failed")
		}
	}
	for i := 0; i < QueueSize; i++ {
		q.Push(Segment{})
	}
	if q.Push(Segment{}) || q.Space() != 0 {
		t.Error("full queue accepts a push")
	}
}

func TestHomeStopsOnEndstop(t *testing.T) {
	var e Executor
	e.SetPos(0, 100)
	e.Endstop = func(ch int) bool { return e.pos[ch] <= 90 }
	e.Q.Push(Segment{Kind: Home, Axis: 0, Dir: 1, Ticks: 2, Max: 1000})
	for i := 0; i < 100 && !e.Idle(); i++ {
		e.Tick()
	}
	if e.HomeHits() != 1 || e.Pos(0) != 90 {
		t.Errorf("hits=%b pos=%d", e.HomeHits(), e.Pos(0))
	}
}

func TestDualYHomeSquares(t *testing.T) {
	var e Executor
	// Y2 starts 7 steps further from its switch than Y1.
	e.SetPos(ChY1, 20)
	e.SetPos(ChY2, 27)
	e.Endstop = func(ch int) bool { return e.pos[ch] <= 0 }
	e.Q.Push(Segment{Kind: Home, Axis: 1, Dir: 2, Ticks: 1, Max: 100})
	for i := 0; i < 200 && !e.Idle(); i++ {
		e.Tick()
	}
	if e.HomeHits() != 6 || e.Pos(ChY1) != 0 || e.Pos(ChY2) != 0 || e.Pos(ChX) != 0 {
		t.Errorf("hits=%b pos=%d %d %d", e.HomeHits(), e.Pos(0), e.Pos(1), e.Pos(2))
	}
	// Trim moves Y2 only.
	e.Q.Push(Segment{Kind: Trim, Steps: [2]uint16{0, 5}, Ticks: 10})
	for i := 0; i < 20; i++ {
		e.Tick()
	}
	if e.Pos(ChY1) != 0 || e.Pos(ChY2) != 5 {
		t.Errorf("trim: pos %d %d", e.Pos(ChY1), e.Pos(ChY2))
	}
	// A failed home reports the channel that did not reach its switch.
	e.Endstop = func(ch int) bool { return ch == ChY1 }
	e.Q.Push(Segment{Kind: Home, Axis: 1, Dir: 2, Ticks: 1, Max: 3})
	for i := 0; i < 20 && !e.Idle(); i++ {
		e.Tick()
	}
	if e.HomeHits() != 1<<ChY1 {
		t.Errorf("hits=%b", e.HomeHits())
	}
}

func TestPenAndAbort(t *testing.T) {
	var e Executor
	e.Q.Push(Segment{Kind: Pen, Angle: 42, Ticks: 5})
	if o := e.Tick(); o.Servo != 42 {
		t.Errorf("servo = %d", o.Servo)
	}
	e.Q.Push(Segment{Kind: Dwell, Ticks: 1000})
	e.Abort()
	e.Tick()
	if !e.Idle() || !e.AbortDone() {
		t.Error("abort did not clear the queue")
	}
}
