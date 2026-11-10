//go:build !linux

package serial

import (
	"errors"
	"os"
)

// Open is only on Linux in this version.
func Open(path string) (*os.File, error) {
	return nil, errors.New("serial: only Linux is supported")
}
