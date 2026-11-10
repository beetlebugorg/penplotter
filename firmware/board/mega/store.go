//go:build atmega2560

package mega

import (
	"device/avr"
	"errors"
	"runtime/interrupt"

	"github.com/beetlebugorg/penplotter/firmware/settings"
)

// EEPROMStore keeps the settings in the 4 KB EEPROM of the ATmega2560, from address 0.
// A byte write takes 3.3 ms, so a full record takes about 3.4 s. The controller saves
// only when the machine is idle. The store writes only the bytes that changed.
type EEPROMStore struct{}

const eepromSize = 4096

func eepromWait() {
	for avr.EECR.Get()&avr.EECR_EEPE != 0 {
	}
}

func eepromRead(addr uint16) byte {
	eepromWait()
	avr.EEARH.Set(uint8(addr >> 8))
	avr.EEARL.Set(uint8(addr))
	avr.EECR.SetBits(avr.EECR_EERE)
	return avr.EEDR.Get()
}

func eepromWrite(addr uint16, v byte) {
	eepromWait()
	avr.EEARH.Set(uint8(addr >> 8))
	avr.EEARL.Set(uint8(addr))
	avr.EEDR.Set(v)
	// EEPE must follow EEMPE within 4 clock cycles. Two sbi instructions do that.
	// EECR is I/O address 0x1F. EEMPE is bit 2, EEPE is bit 1.
	m := interrupt.Disable()
	avr.Asm("sbi 0x1f, 2")
	avr.Asm("sbi 0x1f, 1")
	interrupt.Restore(m)
}

// Load implements settings.Store.
func (EEPROMStore) Load(b []byte) bool {
	if len(b) > eepromSize {
		return false
	}
	for i := range b {
		b[i] = eepromRead(uint16(i))
	}
	return true
}

// Save implements settings.Store.
func (EEPROMStore) Save(b []byte) error {
	if len(b) > eepromSize {
		return errors.New("no EEPROM space")
	}
	for i, v := range b {
		if eepromRead(uint16(i)) != v {
			eepromWrite(uint16(i), v)
		}
	}
	return nil
}

var _ settings.Store = EEPROMStore{}
