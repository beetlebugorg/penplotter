//go:build atmega2560

// Command mega is the pen plotter firmware for the stock CR-10 V3 mainboard
// (Creality v2.5.2, ATmega2560). It has no Wi-Fi. It uses the small controller (package mini).
//
//	tinygo build -target=arduino-mega2560 -o build/plotter-mega.hex ./firmware/cmd/mega
//	tinygo flash -target=arduino-mega2560 -port /dev/ttyUSB0 ./firmware/cmd/mega
package main

import (
	"github.com/beetlebugorg/penplotter/firmware/board/mega"
	"github.com/beetlebugorg/penplotter/firmware/mini"
)

func main() {
	b := mega.New()
	c := mini.New(b, b.Ex, mega.EEPROMStore{})
	for {
		c.Poll()
	}
}
