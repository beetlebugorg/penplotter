//go:build !linux

package camera

import "errors"

// Device is a V4L2 capture device.
type Device struct {
	Path  string   `json:"path"`
	Name  string   `json:"name"`
	Sizes []string `json:"sizes"`
}

// List returns no devices on this system.
func List() []Device { return nil }

// OpenV4L2 is only on Linux.
func OpenV4L2(path string) (Source, error) { return nil, errors.New("camera: V4L2 needs Linux") }
