//go:build rp2040

package pico

import (
	"errors"
	"machine"

	"github.com/beetlebugorg/penplotter/firmware/settings"
)

// FlashStore keeps the settings in the last erase block of the flash data area.
// A write erases the block (4 KB) and programs one record. The step interrupt
// cannot run during the write, so the controller saves only when the machine is idle.
type FlashStore struct{}

func (FlashStore) offset() int64 {
	return machine.Flash.Size() - machine.Flash.EraseBlockSize()
}

// Load implements settings.Store.
func (s FlashStore) Load(b []byte) bool {
	if machine.Flash.Size() < machine.Flash.EraseBlockSize() {
		return false
	}
	_, err := machine.Flash.ReadAt(b, s.offset())
	return err == nil
}

// Save implements settings.Store.
func (s FlashStore) Save(b []byte) error {
	if machine.Flash.Size() < machine.Flash.EraseBlockSize() || len(b) > int(machine.Flash.EraseBlockSize()) {
		return errors.New("no flash space")
	}
	blk := s.offset() / machine.Flash.EraseBlockSize()
	if err := machine.Flash.EraseBlocks(blk, 1); err != nil {
		return err
	}
	_, err := machine.Flash.WriteAt(b, s.offset())
	return err
}

var _ settings.Store = FlashStore{}
