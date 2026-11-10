package sim

import (
	"bufio"
	"io"
	"os"
	"strings"
	"sync"

	"github.com/creack/pty"
	"golang.org/x/term"
)

// StartPTY makes a pseudo-terminal for a G-code sender, such as a print host or a script.
// It returns the device path, for example /dev/pts/7. If link is not empty, it also
// makes a symbolic link with that name to the device.
func (m *Machine) StartPTY(link string) (string, error) {
	ptmx, tty, err := pty.Open()
	if err != nil {
		return "", err
	}
	// Raw mode: no echo and no line changes. Keep tty open, so the device
	// stays when a sender closes it.
	if _, err := term.MakeRaw(int(tty.Fd())); err != nil {
		return "", err
	}
	name := tty.Name()
	m.ttys = append(m.ttys, tty, ptmx) // keep the files open; the runtime closes unreachable files
	if link != "" {
		os.Remove(link)
		if err := os.Symlink(name, link); err != nil {
			return name, err
		}
	}
	go m.serveLines(ptmx, ptmx)
	return name, nil
}

// serveLines connects a line link to the serial port. It sends each line and waits for
// its "ok". The lines that are not replies (for example "start") also go to the link.
func (m *Machine) serveLines(r io.Reader, w io.Writer) {
	var wmu sync.Mutex
	write := func(line string) {
		wmu.Lock()
		w.Write([]byte(line + "\n"))
		wmu.Unlock()
	}
	off := m.Serial.OnLine(write)
	defer off()
	br := bufio.NewReader(r)
	for {
		line, err := br.ReadString('\n')
		if err != nil {
			return
		}
		// The realtime characters ('?' and Ctrl-X) get no "ok". Send them at once.
		line = strings.Map(func(r rune) rune {
			if r == '?' || r == 0x18 {
				m.Serial.Realtime(byte(r))
				return -1
			}
			return r
		}, line)
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		m.Serial.Send(line, false, write)
	}
}
