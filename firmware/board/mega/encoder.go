//go:build atmega2560

package mega

import (
	"runtime/interrupt"

	"github.com/beetlebugorg/penplotter/firmware/config"
)

// Quadrature table: index is (old state << 2) | new state. A state is (A << 1) | B.
var quad = [16]int8{0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0}

var (
	encState uint8
	encCount int16
)

func encRead() uint8 {
	var s uint8
	if PinEncA.Get() {
		s |= 2
	}
	if PinEncB.Get() {
		s |= 1
	}
	return s
}

// encPoll runs in the step interrupt.
func encPoll() {
	s := encRead()
	encCount += int16(quad[encState<<2|s])
	encState = s
}

// encoderDetents returns the full detents since the last call and keeps the rest.
func encoderDetents() int {
	m := interrupt.Disable()
	d := encCount / config.EncoderPulsesPerDetent
	encCount -= d * config.EncoderPulsesPerDetent
	interrupt.Restore(m)
	return int(d)
}
