package planner

import (
	"math"
	"testing"

	"github.com/beetlebugorg/penplotter/firmware/stepgen"
)

const (
	tickHz = 40000
	segT   = 80
	accel  = 1500
)

var spm = [2]float32{80, 80}

type run struct {
	pos    [2]int32
	speeds []float32 // mm/s of each move segment
	lens   []float32
	pens   int
}

// drain runs Prep and records the segments in place of the executor.
func drain(t *testing.T, p *Planner, r *Prep, q *stepgen.Queue, out *run) {
	t.Helper()
	var s stepgen.Segment
	for i := 0; i < 1_000_000; i++ {
		r.Fill()
		if !q.Pop(&s) {
			if p.Len() == 0 && !r.Busy() {
				return
			}
			continue
		}
		switch s.Kind {
		case stepgen.Move:
			var d [2]float32
			for a := 0; a < 2; a++ {
				n := int32(s.Steps[a])
				if s.Dir&(1<<a) != 0 {
					n = -n
				}
				out.pos[a] += n
				d[a] = float32(n) / spm[a]
				if s.Steps[a] > uint16(s.Ticks) {
					t.Fatalf("segment has more steps than ticks: %+v", s)
				}
			}
			l := float32(math.Hypot(float64(d[0]), float64(d[1])))
			out.speeds = append(out.speeds, l/(float32(s.Ticks)/tickHz))
			out.lens = append(out.lens, l)
		case stepgen.Pen:
			out.pens++
		}
	}
	t.Fatal("drain did not end")
}

func setup() (*Planner, *Prep, *stepgen.Queue) {
	p := &Planner{JunctionDev: 0.02}
	q := &stepgen.Queue{}
	r := &Prep{P: p, Q: q, TickHz: tickHz, SegTicks: segT, MinSpeed: 1}
	return p, r, q
}

func steps(x, y float32) [2]int32 { return [2]int32{int32(x * 80), int32(y * 80)} }

func TestSquareExactAndLimited(t *testing.T) {
	p, r, q := setup()
	var out run
	pts := [][2]float32{{50, 0}, {50, 50}, {0, 50}, {0, 0}, {33.3, 12.7}}
	for i, pt := range pts {
		for !p.AddMove(steps(pt[0], pt[1]), 100, accel, spm, uint32(i)) {
			t.Fatal("planner full")
		}
	}
	p.AddPen(40, 100, 9)
	drain(t, p, r, q, &out)
	if out.pos != steps(33.3, 12.7) {
		t.Errorf("end position %v, want %v", out.pos, steps(33.3, 12.7))
	}
	if out.pens != 1 {
		t.Errorf("pens = %d", out.pens)
	}
	for i, v := range out.speeds {
		if v > 100*1.03+2 {
			t.Fatalf("segment %d speed %.1f over nominal", i, v)
		}
	}
	// Speed change between full segments stays near accel*dt.
	dt := float32(segT) / tickHz
	for i := 1; i < len(out.speeds)-1; i++ {
		dv := out.speeds[i] - out.speeds[i-1]
		// One step per segment is 6.25 mm/s, so allow two steps of rounding.
		if float32(math.Abs(float64(dv))) > accel*dt*1.2+2*(1/spm[0])/dt {
			t.Fatalf("segment %d: speed jump %.2f mm/s: %v len %v", i, dv, out.speeds[i-3:i+2], out.lens[i-3:i+2])
		}
	}
	if last := out.speeds[len(out.speeds)-1]; last > 10 {
		t.Errorf("the machine does not stop at the end: %.1f mm/s %v %v", last, out.speeds[len(out.speeds)-6:], out.lens[len(out.lens)-6:])
	}
}

func TestStraightLineKeepsSpeed(t *testing.T) {
	p, _, _ := setup()
	for i := 1; i <= 5; i++ {
		p.AddMove(steps(float32(i*20), 0), 80, accel, spm, 0)
	}
	// The entry speed of the middle blocks is the nominal speed.
	if e := p.buf[p.idx(2)].Entry; e < 79 {
		t.Errorf("entry of block 2 = %.1f, want 80", e)
	}
	// A 90 degree corner is slow.
	p2, _, _ := setup()
	p2.AddMove(steps(20, 0), 80, accel, spm, 0)
	p2.AddMove(steps(20, 20), 80, accel, spm, 0)
	if e := p2.buf[p2.idx(1)].Entry; e > 15 || e < 1 {
		t.Errorf("corner speed = %.1f", e)
	}
}

func TestPenIsBarrier(t *testing.T) {
	p, _, _ := setup()
	p.AddMove(steps(20, 0), 80, accel, spm, 0)
	p.AddPen(40, 10, 0)
	p.AddMove(steps(40, 0), 80, accel, spm, 0)
	if p.buf[p.idx(2)].Entry != 0 {
		t.Error("move after the pen block does not start from rest")
	}
}
