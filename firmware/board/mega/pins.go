//go:build atmega2560

// Package mega is the board code for the stock CR-10 V3 mainboard
// (Creality v2.5.2, ATmega2560, 16 MHz, 8 KB RAM, onboard drivers at 1/16 step).
// docs/guide/20-electronics-and-wiring.md shows the wiring.
//
// The plotter uses the driver sockets of the printer like this:
//
//	X  driver -> X motor   (head board, socket X)
//	Y  driver -> Y1 motor  (base board, socket Y)
//	Z  driver -> Y2 motor  (base board, socket Z1)
//	E  driver -> free (not used)
package mega

import "machine"

// Pin map. The port names are the ATmega2560 port pins.
const (
	PinXStep  = machine.PF0
	PinXDir   = machine.PF1
	PinXEn    = machine.PD7
	PinYStep  = machine.PF6 // Y1
	PinYDir   = machine.PF7
	PinYEn    = machine.PF2
	PinY2Step = machine.PL3 // Y2 on the Z driver
	PinY2Dir  = machine.PL1
	PinY2En   = machine.PK0

	PinXMin  = machine.PE5 // head board X-
	PinYMin  = machine.PJ1 // base board Y-
	PinY2Min = machine.PD3 // base board Z-

	// PinServo is the servo pin of the stock board (OC1A, Arduino D11). It reaches the
	// signal pin of the BL_T socket on the head board. The pen servo plugs into BL_T.
	PinServo = machine.PB5

	// PinHeater drives the MOSFET of the hotend heater (Arduino D10). The plotter does not use
	// it. The firmware holds it low, so the HEAT socket stays off.
	PinHeater = machine.PB4

	PinLCDCS   = machine.PH1 // ST7920 CS (RS)
	PinLCDSCK  = machine.PA1 // ST7920 SCLK (E)
	PinLCDData = machine.PH0 // ST7920 SID (R/W)
	PinEncA    = machine.PC4
	PinEncB    = machine.PC6
	PinEncBtn  = machine.PC2 // low when pressed
	PinBeeper  = machine.PC0 // Arduino D37. Check it on your board.
)

// Pins of the free E driver. The firmware holds this driver off.
const (
	PinEStep = machine.PA4
	PinEDir  = machine.PA6
	PinEEn   = machine.PA2
)
