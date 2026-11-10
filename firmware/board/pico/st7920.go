//go:build rp2040

package pico

import (
	"device/rp"
	"machine"

	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// ST7920 drives the 12864 LCD in serial mode on SPI0.
// CS is active high. Each byte goes as three SPI bytes:
// a sync byte (0xF8 for a command, 0xFA for data), the high nibble, and the low nibble.
type ST7920 struct {
	spi *machine.SPI
}

// The ST7920 needs about 72 us for each command or data byte.
const st7920Wait = 80

// NewST7920 sets up SPI0 and puts the LCD in graphic mode.
func NewST7920() *ST7920 {
	PinLCDCS.Configure(machine.PinConfig{Mode: machine.PinOutput})
	PinLCDCS.Low()
	machine.SPI0.Configure(machine.SPIConfig{
		Frequency: 1_000_000,
		Mode:      3,
		SCK:       PinLCDSCK,
		SDO:       PinLCDData,
		SDI:       machine.NoPin,
	})
	d := &ST7920{spi: machine.SPI0}
	waitUs(100_000) // power-on time of the LCD
	for _, c := range []byte{0x30, 0x30, 0x0C, 0x01, 0x06} {
		d.cmd(c)
	}
	waitUs(2000) // the clear command needs 1.6 ms
	d.cmd(0x34)  // extended instructions
	d.cmd(0x36)  // graphic display on
	return d
}

func waitUs(us uint32) {
	start := rp.TIMER.TIMERAWL.Get()
	for rp.TIMER.TIMERAWL.Get()-start < us {
	}
}

func (d *ST7920) send(sync, v byte) {
	buf := [3]byte{sync, v & 0xF0, v << 4}
	PinLCDCS.High()
	d.spi.Tx(buf[:], nil)
	PinLCDCS.Low()
	waitUs(st7920Wait)
}

func (d *ST7920) cmd(c byte)  { d.send(0xF8, c) }
func (d *ST7920) data(c byte) { d.send(0xFA, c) }

// Flush implements ui.Display. It sends one dirty row per call, so the main loop
// keeps the step queue full. One row takes about 1.5 ms.
func (d *ST7920) Flush(fb *ui.FB) {
	y, row, ok := fb.NextDirty()
	if !ok {
		return
	}
	// Rows 32..63 are the right half of the 256x32 graphic RAM.
	x := byte(0)
	if y >= 32 {
		y -= 32
		x = 8
	}
	d.cmd(0x80 | byte(y))
	d.cmd(0x80 | x)
	for _, b := range row {
		d.data(b)
	}
}
