//go:build !avr

package config

// Values for a fast processor (the Pico and the simulator).
const (
	TickHz      = 40000 // step timer rate. One step per axis per tick at most.
	SegmentTick = 80    // ticks per segment (2 ms)
	MaxFeed     = 250   // mm/s, the planner clamps all moves to this speed
	PlannerSize = 32    // blocks in the look-ahead buffer
	SegQueue    = 64    // segments in the step queue. It must be a power of 2.
)
