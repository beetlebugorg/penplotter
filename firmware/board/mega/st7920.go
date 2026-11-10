//go:build atmega2560

package mega

import "machine"

// ST7920 drives the 12864 LCD in serial mode. The pins are not on a hardware SPI port, so
// the driver sends the bits with the pins. CS is active high. Each byte goes as three bytes:
// a sync byte (0xF8 for a command, 0xFA for data), the high nibble, and the low nibble.
type ST7920 struct{}

// The ST7920 needs about 72 us for each command or data byte.
const st7920Wait = 80

// NewST7920 puts the LCD in text mode: 4 lines of 16 characters.
func NewST7920() *ST7920 {
	for _, p := range []machine.Pin{PinLCDCS, PinLCDSCK, PinLCDData} {
		p.Configure(machine.PinConfig{Mode: machine.PinOutput})
		p.Low()
	}
	d := &ST7920{}
	waitUs(100_000) // power-on time of the LCD
	for _, c := range []byte{0x30, 0x30, 0x0C, 0x01, 0x06} {
		d.cmd(c)
	}
	waitUs(2000) // the clear command needs 1.6 ms
	return d
}

// waitUs waits with a busy loop. One pass takes about 4 clock cycles (0.25 us).
//
//go:noinline
func waitUs(us uint32) {
	for n := us * 4; n > 0; n-- {
		machine.NoPin.Get() // a volatile access stops the compiler from removing the loop
	}
}

// shift sends one byte, most significant bit first. The LCD reads SID on the rising edge of SCLK.
func shift(v byte) {
	for i := 0; i < 8; i++ {
		PinLCDData.Set(v&0x80 != 0)
		PinLCDSCK.High()
		v <<= 1
		PinLCDSCK.Low()
	}
}

func (d *ST7920) send(sync, v byte) {
	PinLCDCS.High()
	shift(sync)
	shift(v & 0xF0)
	shift(v << 4)
	PinLCDCS.Low()
	waitUs(st7920Wait)
}

func (d *ST7920) cmd(c byte)  { d.send(0xF8, c) }
func (d *ST7920) data(c byte) { d.send(0xFA, c) }

// Text writes one line (0..3) of 16 characters. The LCD stays in text mode: its own
// character ROM draws the letters, so the board needs no frame buffer.
func (d *ST7920) Text(row int, s string) {
	addr := [4]byte{0x80, 0x90, 0x88, 0x98}
	d.cmd(addr[row&3])
	for i := 0; i < 16; i++ {
		ch := byte(' ')
		if i < len(s) {
			ch = s[i]
		}
		d.data(ch)
	}
}
