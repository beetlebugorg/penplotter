// Package stepgen runs the motion segments at a fixed tick rate.
// The board calls Executor.Tick from the step timer interrupt.
// The code uses integer math only and does not allocate memory.
//
// The executor has three step channels: X, Y1 and Y2. The planner knows two
// axes (X and Y). In all Y moves, channel Y2 steps together with Y1.
// Only Home segments of Y and Trim segments move Y1 and Y2 apart.
package stepgen

import (
	"sync/atomic"

	"github.com/beetlebugorg/penplotter/firmware/config"
)

// QueueSize is the number of segments in the queue. It must be a power of 2.
const QueueSize = config.SegQueue

// Kind tells what a segment does.
type Kind uint8

// Segment kinds.
const (
	Move  Kind = iota // step the axes at a constant rate
	Pen               // set the servo angle, then wait Ticks
	Dwell             // wait Ticks
	Home              // step an axis until its endstop triggers. Y homes Y1 and Y2, each to its own switch.
	Trim              // step channel Y2 only (Steps[1] steps), to square the gantry
)

// Channels of the executor.
const (
	ChX   = 0
	ChY1  = 1
	ChY2  = 2
	NumCh = 3
)

// Segment is one unit of work for the executor.
type Segment struct {
	Kind  Kind
	Dir   uint8     // bit i set: axis i moves to the negative side. Bit 1 also sets the Y2 direction.
	Axis  uint8     // Home: the axis (0 = X, 1 = Y1 and Y2)
	Angle uint16    // Pen: the servo angle in degrees
	Steps [2]uint16 // Move: steps of each axis
	Ticks uint32    // Move: duration. Pen, Dwell: wait. Home: ticks per step.
	Max   uint32    // Home: the maximum number of steps
	Line  uint32    // the G-code line of this segment
}

// Queue is a single-producer, single-consumer ring of segments.
// The main loop pushes. The executor pops.
type Queue struct {
	buf        [QueueSize]Segment
	head, tail atomic.Uint32
}

// Len returns the number of queued segments.
func (q *Queue) Len() int { return int(q.head.Load() - q.tail.Load()) }

// Space returns the number of free places.
func (q *Queue) Space() int { return QueueSize - q.Len() }

// Push adds a segment. It returns false if the queue is full.
func (q *Queue) Push(s Segment) bool {
	h := q.head.Load()
	if h-q.tail.Load() >= QueueSize {
		return false
	}
	q.buf[h&(QueueSize-1)] = s
	q.head.Store(h + 1)
	return true
}

func (q *Queue) pop(s *Segment) bool {
	t := q.tail.Load()
	if t == q.head.Load() {
		return false
	}
	*s = q.buf[t&(QueueSize-1)]
	q.tail.Store(t + 1)
	return true
}

// Out is the result of one tick.
type Out struct {
	Step   uint8 // bit i set: pulse the step pin of channel i (X, Y1, Y2)
	Dir    uint8 // bit i set: channel i moves to the negative side
	DirSet bool  // write Dir to the direction pins before the step pulse
	Servo  int16 // new servo angle, or -1
}

// Executor runs the segments of its queue.
type Executor struct {
	Q Queue
	// Endstop reads the endstop of a channel (X, Y1, Y2).
	// The executor calls it from the tick during Home segments, and during Move
	// segments when HardLimits is true.
	Endstop func(ch int) bool
	// HardLimits stops all motion when a switch closes during a move toward it.
	// A switch that is closed when the move starts does not count, so a move to
	// the home position (where the switch is closed) works.
	HardLimits bool

	cur    Segment
	active bool
	t, n   uint32
	acc    [2]uint32
	pos    [NumCh]int32
	hits   uint8 // Home: channels that reached their switch
	armed  uint8 // Move: channels whose switch was open at the start

	pubPos   [NumCh]atomic.Int32
	line     atomic.Uint32
	busy     atomic.Bool
	abort    atomic.Bool
	homeHits atomic.Uint32
	limits   atomic.Uint32
	floor    [NumCh]atomic.Int32 // a switch that closes at or below this position does not count
	floorSet [NumCh]atomic.Bool
}

// Tick runs one step timer tick.
func (e *Executor) Tick() (o Out) {
	o.Servo = -1
	if e.abort.Load() {
		e.Q.tail.Store(e.Q.head.Load())
		e.active = false
		e.busy.Store(false)
		e.abort.Store(false)
		return
	}
	if !e.active {
		if e.Q.Len() == 0 {
			return
		}
		e.busy.Store(true)
		e.Q.pop(&e.cur)
		e.active = true
		e.t, e.n = 0, 0
		e.acc[0] = e.cur.Ticks / 2
		e.acc[1] = e.cur.Ticks / 2
		e.hits = 0
		e.line.Store(e.cur.Line)
		// Y2 follows the direction of Y1. A Trim segment sets the Y2 bit itself.
		if e.cur.Kind != Trim {
			e.cur.Dir = e.cur.Dir&^(1<<ChY2) | (e.cur.Dir>>ChY1&1)<<ChY2
		}
		o.Dir = e.cur.Dir
		o.DirSet = true
		if e.cur.Kind == Pen {
			o.Servo = int16(e.cur.Angle)
		}
		e.armed = 0
		if e.cur.Kind == Move && e.HardLimits && e.Endstop != nil {
			for ch := 0; ch < NumCh; ch++ {
				ax := ch
				if ax > 1 {
					ax = 1
				}
				if e.cur.Dir&(1<<ch) != 0 && e.cur.Steps[ax] > 0 && !e.Endstop(ch) {
					e.armed |= 1 << ch
				}
			}
		}
	}
	switch e.cur.Kind {
	case Move:
		if e.armed != 0 {
			for ch := 0; ch < NumCh; ch++ {
				if e.armed&(1<<ch) != 0 && e.Endstop(ch) &&
					!(e.floorSet[ch].Load() && e.pos[ch] <= e.floor[ch].Load()) {
					// A switch closed during a move toward it: drop all segments.
					e.limits.Store(e.limits.Load() | 1<<ch)
					e.Q.tail.Store(e.Q.head.Load())
					e.active = false
					e.busy.Store(false)
					return
				}
			}
		}
		for i := 0; i < 2; i++ {
			e.acc[i] += uint32(e.cur.Steps[i])
			if e.acc[i] >= e.cur.Ticks {
				e.acc[i] -= e.cur.Ticks
				o.Step |= e.step(i)
				if i == ChY1 {
					o.Step |= e.step(ChY2)
				}
			}
		}
		e.t++
		if e.t >= e.cur.Ticks {
			e.finish()
		}
	case Trim:
		e.acc[1] += uint32(e.cur.Steps[1])
		if e.acc[1] >= e.cur.Ticks {
			e.acc[1] -= e.cur.Ticks
			o.Step |= e.step(ChY2)
		}
		e.t++
		if e.t >= e.cur.Ticks {
			e.finish()
		}
	case Pen, Dwell:
		e.t++
		if e.t >= e.cur.Ticks {
			e.finish()
		}
	case Home:
		e.t++
		if e.t < e.cur.Ticks {
			break
		}
		e.t = 0
		chans := uint8(1 << ChX)
		if e.cur.Axis&1 == 1 {
			chans = 1<<ChY1 | 1<<ChY2
		}
		for ch := 0; ch < NumCh; ch++ {
			if chans&(1<<ch) == 0 || e.hits&(1<<ch) != 0 {
				continue
			}
			if e.Endstop != nil && e.Endstop(ch) {
				e.hits |= 1 << ch
			} else if e.n < e.cur.Max {
				o.Step |= e.step(ch)
			}
		}
		e.n++
		if e.hits == chans || e.n > e.cur.Max {
			e.homeHits.Store(uint32(e.hits))
			e.finish()
		}
	}
	return
}

// step counts one step of channel ch and returns its step bit.
func (e *Executor) step(ch int) uint8 {
	if e.cur.Dir&(1<<ch) != 0 {
		e.pos[ch]--
	} else {
		e.pos[ch]++
	}
	e.pubPos[ch].Store(e.pos[ch])
	return 1 << ch
}

func (e *Executor) finish() {
	e.active = false
	if e.Q.Len() == 0 {
		e.busy.Store(false)
	}
}

// Idle tells if the queue is empty and no segment runs.
func (e *Executor) Idle() bool {
	// Read the queue length first. The tick sets busy before it pops.
	return e.Q.Len() == 0 && !e.busy.Load()
}

// Pos returns the step position of a channel (X, Y1, Y2).
func (e *Executor) Pos(ch int) int32 { return e.pubPos[ch].Load() }

// SetPos sets the step position of a channel. Call it only when Idle is true.
func (e *Executor) SetPos(ch int, v int32) {
	e.pos[ch] = v
	e.pubPos[ch].Store(v)
}

// Line returns the G-code line of the last started segment.
func (e *Executor) Line() uint32 { return e.line.Load() }

// HomeHits returns the channels that reached their switch in the last Home segment.
// Bit i is channel i.
func (e *Executor) HomeHits() uint8 { return uint8(e.homeHits.Load()) }

// SetLimitFloor tells the hard limit check where the switch of a channel closes.
// After homing, the switch closes at position 0, so a move to 0 must not stop the
// machine. ok false removes the floor: any closing switch stops the machine.
func (e *Executor) SetLimitFloor(ch int, steps int32, ok bool) {
	e.floor[ch].Store(steps)
	e.floorSet[ch].Store(ok)
}

// LimitHits returns the channels whose switch stopped a move, and clears them.
func (e *Executor) LimitHits() uint8 { return uint8(e.limits.Swap(0)) }

// Abort asks the tick to drop all segments. AbortDone tells when the tick did it.
func (e *Executor) Abort() { e.abort.Store(true) }

// AbortDone tells if the last Abort is complete.
func (e *Executor) AbortDone() bool { return !e.abort.Load() }

// Pop removes the oldest segment. Tests use it in place of the executor.
func (q *Queue) Pop(s *Segment) bool { return q.pop(s) }
