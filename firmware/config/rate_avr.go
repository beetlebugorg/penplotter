//go:build avr

package config

// Values for the ATmega2560 (16 MHz, 8 KB RAM) on the stock CR-10 V3 mainboard.
// The step interrupt has 1600 clock cycles at 10 kHz. 10 kHz at 80 steps/mm
// gives 125 mm/s on one axis.
const (
	TickHz      = 10000 // step timer rate. One step per axis per tick at most.
	SegmentTick = 20    // ticks per segment (2 ms)
	MaxFeed     = 120   // mm/s, the planner clamps all moves to this speed
	PlannerSize = 8     // blocks in the look-ahead buffer
	SegQueue    = 16    // segments in the step queue. It must be a power of 2.
)
