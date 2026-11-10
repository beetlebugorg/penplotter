//go:build rp2040 && !cyw43439

package pico

import (
	"machine"

	"github.com/beetlebugorg/penplotter/firmware/controller"
)

// PinLED blinks while the main loop runs. The Pico W uses GPIO25 for the Wi-Fi chip,
// so only the Pico H build drives it.
const PinLED = machine.LED

// Network returns nil: the Pico H has no Wi-Fi.
func (b *Board) Network() controller.Network { return nil }

// Start starts the parts that need the controller. The Pico H has none.
func (b *Board) Start(c *controller.Controller) {}

// Yield lets other goroutines run. The Pico H has none.
func (b *Board) Yield() {}

func ledInit()       { PinLED.Configure(machine.PinConfig{Mode: machine.PinOutput}) }
func ledSet(on bool) { PinLED.Set(on) }
