//go:build rp2040

// Command pico is the pen plotter firmware for a Raspberry Pi Pico.
//
//	tinygo build -target=pico -o build/plotter.uf2 ./firmware/cmd/pico
package main

import (
	"github.com/beetlebugorg/penplotter/firmware/board/pico"
	"github.com/beetlebugorg/penplotter/firmware/controller"
)

func main() {
	b := pico.New()
	c := controller.NewWith(b, b.Ex, controller.Options{Store: pico.FlashStore{}, Net: b.Network()})
	b.Start(c)
	for {
		c.Poll()
		b.Yield()
	}
}
