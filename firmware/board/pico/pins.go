//go:build rp2040

// Package pico is the board code for a Raspberry Pi Pico.
// docs/wiring.md shows the same pin map with the wiring.
package pico

import "machine"

// Pin map.
const (
	PinXStep  = machine.GPIO2
	PinXDir   = machine.GPIO3
	PinYStep  = machine.GPIO4 // Y1, left side
	PinYDir   = machine.GPIO5
	PinEn     = machine.GPIO6  // all three drivers, active low
	PinY2Step = machine.GPIO10 // Y2, right side
	PinY2Dir  = machine.GPIO11

	PinXMin  = machine.GPIO7
	PinYMin  = machine.GPIO8 // Y1
	PinY2Min = machine.GPIO12

	PinServo = machine.GPIO9 // PWM slice 4, channel B

	PinBeeper  = machine.GPIO16 // through the 74AHCT125
	PinLCDCS   = machine.GPIO17 // ST7920 CS (RS), through the 74AHCT125
	PinLCDSCK  = machine.GPIO18 // SPI0 SCK -> ST7920 SCLK (E)
	PinLCDData = machine.GPIO19 // SPI0 TX  -> ST7920 SID (R/W)

	PinEncA   = machine.GPIO20
	PinEncB   = machine.GPIO21
	PinEncBtn = machine.GPIO22
)

// Pins reserved for the automatic pen changer (not used yet): a Z axis on a 4th
// TMC2209, a Z endstop, and a gripper servo. GP0 and GP1 stay free for a debug UART.
// GP23, GP24, GP25 and GP29 belong to the Wi-Fi chip on the Pico W: do not use them.
const (
	PinZStep   = machine.GPIO13
	PinZDir    = machine.GPIO14
	PinZMin    = machine.GPIO15
	PinGripper = machine.GPIO26 // PWM slice 5, channel A
	PinSpare1  = machine.GPIO27
	PinSpare2  = machine.GPIO28
)

// servoPWM is the PWM slice of PinServo.
var servoPWM = machine.PWM4
