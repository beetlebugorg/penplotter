package serial

import (
	"fmt"
	"os"

	"golang.org/x/sys/unix"
)

// Open opens a tty device (for example /dev/ttyACM0 or a /dev/pts device of the simulator) in
// raw mode at 115200 baud. USB CDC devices ignore the baud rate.
func Open(path string) (*os.File, error) {
	fd, err := unix.Open(path, unix.O_RDWR|unix.O_NOCTTY|unix.O_CLOEXEC, 0)
	if err != nil {
		return nil, fmt.Errorf("serial: open %s: %w", path, err)
	}
	t, err := unix.IoctlGetTermios(fd, unix.TCGETS)
	if err != nil {
		unix.Close(fd)
		return nil, fmt.Errorf("serial: %s is not a tty: %w", path, err)
	}
	// cfmakeraw
	t.Iflag &^= unix.IGNBRK | unix.BRKINT | unix.PARMRK | unix.ISTRIP | unix.INLCR | unix.IGNCR | unix.ICRNL | unix.IXON
	t.Oflag &^= unix.OPOST
	t.Lflag &^= unix.ECHO | unix.ECHONL | unix.ICANON | unix.ISIG | unix.IEXTEN
	t.Cflag &^= unix.CSIZE | unix.PARENB | unix.CBAUD
	t.Cflag |= unix.CS8 | unix.CREAD | unix.CLOCAL | unix.B115200
	t.Ispeed, t.Ospeed = unix.B115200, unix.B115200
	t.Cc[unix.VMIN] = 1
	t.Cc[unix.VTIME] = 0
	if err := unix.IoctlSetTermios(fd, unix.TCSETS, t); err != nil {
		unix.Close(fd)
		return nil, fmt.Errorf("serial: set raw mode: %w", err)
	}
	return os.NewFile(uintptr(fd), path), nil
}
