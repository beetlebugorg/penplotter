package planner

import (
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
)

// Prep cuts the oldest block into segments of constant step rate.
type Prep struct {
	P        *Planner
	Q        *stepgen.Queue
	TickHz   uint32
	SegTicks uint32
	MinSpeed float32

	active bool
	s, v   float32
	done   [2]int32
}

// Busy tells if Prep works on a block.
func (r *Prep) Busy() bool { return r.active }

// Reset stops the current block. Call it after Planner.Clear.
func (r *Prep) Reset() { r.active, r.v = false, 0 }

func abs32(v int32) int32 {
	if v < 0 {
		return -v
	}
	return v
}

// Fill pushes segments until the queue is full or no block remains.
func (r *Prep) Fill() {
	for r.Q.Space() > 0 {
		b := r.P.peek()
		if b == nil {
			r.v = 0
			return
		}
		if !r.active {
			switch b.Kind {
			case Pen:
				r.Q.Push(stepgen.Segment{Kind: stepgen.Pen, Angle: b.Angle, Ticks: b.Ticks, Line: b.Line})
				r.P.pop()
				r.v = 0
				continue
			case Dwell:
				r.Q.Push(stepgen.Segment{Kind: stepgen.Dwell, Ticks: b.Ticks, Line: b.Line})
				r.P.pop()
				r.v = 0
				continue
			}
			r.active = true
			r.P.locked = true
			r.s = 0
			r.done = [2]int32{}
			if r.v > b.Entry {
				r.v = b.Entry
			}
		}
		r.segment(b)
	}
}

func (r *Prep) segment(b *Block) {
	dt := float32(r.SegTicks) / float32(r.TickHz)
	exit := r.P.exitSpeed()
	floor := exit
	if floor < r.MinSpeed {
		floor = r.MinSpeed
	}
	// Use the speed limit at the estimated end of this segment.
	rem := b.Len - r.s - r.v*dt
	if rem < 0 {
		rem = 0
	}
	vlim := sqrt32(exit*exit + 2*b.Accel*rem)
	if vlim > b.Nominal {
		vlim = b.Nominal
	}
	var vNew float32
	if r.v <= vlim {
		vNew = r.v + b.Accel*dt
		if vNew > vlim {
			vNew = vlim
		}
	} else {
		vNew = r.v - b.Accel*dt
		if vNew < floor {
			vNew = floor
		}
	}
	if vNew < r.MinSpeed {
		vNew = r.MinSpeed
	}
	ds := (r.v + vNew) / 2 * dt
	var seg stepgen.Segment
	seg.Kind = stepgen.Move
	seg.Line = b.Line
	ticks := r.SegTicks
	var target [2]int32
	last := r.s+ds >= b.Len-1e-4
	if last {
		target = b.Steps
		// The block ends at the exit speed, but never faster than vNew.
		vEnd := exit
		if vEnd < r.MinSpeed {
			vEnd = r.MinSpeed
		}
		if vEnd > vNew {
			vEnd = vNew
		}
		avg := (r.v + vEnd) / 2
		if avg < r.MinSpeed {
			avg = r.MinSpeed
		}
		rem := b.Len - r.s
		ticks = uint32(rem/avg*float32(r.TickHz) + 0.999)
		r.v = vEnd
	} else {
		r.s += ds
		f := r.s / b.Len
		for i := 0; i < 2; i++ {
			v := f * float32(b.Steps[i])
			if v < 0 {
				target[i] = int32(v - 0.5)
			} else {
				target[i] = int32(v + 0.5)
			}
		}
		r.v = vNew
	}
	for i := 0; i < 2; i++ {
		d := target[i] - r.done[i]
		if d < 0 {
			seg.Dir |= 1 << i
		}
		n := uint32(abs32(d))
		if n > ticks {
			ticks = n
		}
		seg.Steps[i] = uint16(n)
	}
	if ticks == 0 {
		ticks = 1
	}
	seg.Ticks = ticks
	r.done = target
	r.Q.Push(seg)
	if last {
		r.active = false
		r.P.pop()
	}
}
