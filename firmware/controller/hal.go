// Package controller runs the main loop of the plotter.
// It reads G-code, plans the moves, feeds the step executor and runs the UI.
// The same code runs on the Pico and in the simulator. Only the HAL changes.
package controller

import "github.com/beetlebugorg/penplotter/firmware/ui"

// HAL is the hardware of one board.
// The board also runs Executor.Tick from its step timer and sends the servo angles.
type HAL interface {
	// NowMicros returns a monotonic time in microseconds.
	NowMicros() uint64
	// SetMotors enables or disables the stepper drivers.
	SetMotors(on bool)
	// Endstop tells if the endstop of a channel (stepgen.ChX, ChY1, ChY2) is triggered.
	Endstop(ch int) bool
	// Encoder returns the knob detents since the last call. Positive is clockwise.
	Encoder() int
	// Button tells if the knob button is down now.
	Button() bool
	// Beep sounds the beeper for ms milliseconds.
	Beep(ms int)
	// ReadSerial returns the next byte from the host, if there is one.
	ReadSerial() (byte, bool)
	// WriteSerial sends text to the host.
	WriteSerial(s string)
	// Display returns the LCD backend.
	Display() ui.Display
	// Poll lets the board do its own periodic work.
	Poll()
}
