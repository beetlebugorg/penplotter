// Package planner queues the moves and plans their speeds.
// It uses junction deviation for the corner speeds and trapezoid speed profiles.
// Prep cuts the planned blocks into constant-rate segments for the step executor.
package planner

import (
	"math"

	"github.com/beetlebugorg/penplotter/firmware/config"
)

// Size is the number of blocks in the look-ahead buffer.
const Size = config.PlannerSize

// Kind tells what a block does.
type Kind uint8

// Block kinds. Pen and Dwell blocks are barriers: the machine stops before them.
const (
	Move Kind = iota
	Pen
	Dwell
)

// Block is one queued action.
type Block struct {
	Kind     Kind
	Steps    [2]int32 // Move: signed steps of each axis
	Len      float32  // Move: length in mm
	Unit     [2]float32
	Nominal  float32 // mm/s
	Accel    float32 // mm/s²
	MaxEntry float32 // the highest entry speed that the corner permits
	Entry    float32 // the planned entry speed
	Angle    uint16  // Pen: servo angle
	Ticks    uint32  // Pen, Dwell: wait in ticks
	Line     uint32
}

// Planner is a ring buffer of blocks.
type Planner struct {
	buf    [Size]Block
	tail   int // the oldest block
	n      int
	locked bool // Prep runs the tail block. Its entry speed is fixed.

	// Pos is the step position at the end of the last queued block.
	Pos [2]int32
	// JunctionDev is the corner tolerance in mm.
	JunctionDev float32
}

func (p *Planner) idx(i int) int { return (p.tail + i) % Size }

// Len returns the number of queued blocks.
func (p *Planner) Len() int { return p.n }

// Space returns the number of free blocks.
func (p *Planner) Space() int { return Size - p.n }

// Clear removes all blocks.
func (p *Planner) Clear() { p.n, p.locked = 0, false }

func sqrt32(v float32) float32 {
	if v <= 0 {
		return 0
	}
	return float32(math.Sqrt(float64(v)))
}

// AddMove queues a straight move to the step position target.
// It returns false if the buffer is full. A move of zero steps returns true and queues nothing.
func (p *Planner) AddMove(target [2]int32, speed, accel float32, spm [2]float32, line uint32) bool {
	if p.n == Size {
		return false
	}
	var b Block
	b.Kind = Move
	b.Steps = [2]int32{target[0] - p.Pos[0], target[1] - p.Pos[1]}
	if b.Steps == [2]int32{} {
		return true
	}
	dx := float32(b.Steps[0]) / spm[0]
	dy := float32(b.Steps[1]) / spm[1]
	b.Len = sqrt32(dx*dx + dy*dy)
	b.Unit = [2]float32{dx / b.Len, dy / b.Len}
	b.Nominal = speed
	b.Accel = accel
	b.Line = line
	if p.n > 0 {
		prev := &p.buf[p.idx(p.n-1)]
		if prev.Kind == Move {
			b.MaxEntry = p.junction(prev, &b)
		}
	}
	p.buf[p.idx(p.n)] = b
	p.n++
	p.Pos = target
	p.recalc()
	return true
}

// junction returns the highest speed through the corner between a and b.
func (p *Planner) junction(a, b *Block) float32 {
	cos := -(a.Unit[0]*b.Unit[0] + a.Unit[1]*b.Unit[1])
	vmax := a.Nominal
	if b.Nominal < vmax {
		vmax = b.Nominal
	}
	switch {
	case cos > 0.999999:
		return 0 // full reversal
	case cos < -0.999999:
		return vmax // straight line
	}
	sinHalf := sqrt32((1 - cos) / 2)
	v := sqrt32(b.Accel * p.JunctionDev * sinHalf / (1 - sinHalf))
	if v > vmax {
		v = vmax
	}
	return v
}

// AddPen queues a servo move and a wait.
func (p *Planner) AddPen(angle uint16, ticks, line uint32) bool {
	return p.addBarrier(Block{Kind: Pen, Angle: angle, Ticks: ticks, Line: line})
}

// AddDwell queues a wait.
func (p *Planner) AddDwell(ticks, line uint32) bool {
	return p.addBarrier(Block{Kind: Dwell, Ticks: ticks, Line: line})
}

func (p *Planner) addBarrier(b Block) bool {
	if p.n == Size {
		return false
	}
	p.buf[p.idx(p.n)] = b
	p.n++
	p.recalc()
	return true
}

// recalc plans the entry speeds of all blocks that Prep did not start.
func (p *Planner) recalc() {
	first := 0
	if p.locked {
		first = 1
	}
	// Reverse pass: each block must be able to stop at the end of the buffer.
	next := float32(0)
	for i := p.n - 1; i >= first; i-- {
		b := &p.buf[p.idx(i)]
		if b.Kind != Move {
			b.Entry = 0
			next = 0
			continue
		}
		v := sqrt32(next*next + 2*b.Accel*b.Len)
		if v > b.MaxEntry {
			v = b.MaxEntry
		}
		b.Entry = v
		next = v
	}
	// Forward pass: each block must be able to reach its entry speed.
	for i := 1; i < p.n; i++ {
		a := &p.buf[p.idx(i-1)]
		b := &p.buf[p.idx(i)]
		if b.Kind != Move || a.Kind != Move {
			continue
		}
		v := sqrt32(a.Entry*a.Entry + 2*a.Accel*a.Len)
		if b.Entry > v {
			b.Entry = v
		}
	}
}

// peek returns the oldest block, or nil.
func (p *Planner) peek() *Block {
	if p.n == 0 {
		return nil
	}
	return &p.buf[p.tail]
}

// pop removes the oldest block.
func (p *Planner) pop() {
	if p.n == 0 {
		return
	}
	p.tail = (p.tail + 1) % Size
	p.n--
	p.locked = false
}

// exitSpeed returns the planned exit speed of the oldest block.
func (p *Planner) exitSpeed() float32 {
	if p.n < 2 {
		return 0
	}
	return p.buf[p.idx(1)].Entry
}
