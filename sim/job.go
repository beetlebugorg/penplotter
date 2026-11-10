package sim

import (
	"errors"
	"strconv"
	"strings"
	"sync/atomic"
)

// job streams a G-code file to the serial port.
type job struct {
	name   string
	total  int
	done   atomic.Int32
	cancel atomic.Bool
}

// ErrBusy means that a job runs already.
var ErrBusy = errors.New("a job runs already")

// StartJob streams text to the firmware, one line per "ok".
// It sends M73 progress lines, as a print host does.
func (m *Machine) StartJob(name, text string) error {
	var lines []string
	for _, l := range strings.Split(text, "\n") {
		l = strings.TrimSpace(l)
		if l == "" || l[0] == ';' || (l[0] == '(' && strings.HasSuffix(l, ")") && strings.Count(l, "(") == 1) {
			continue
		}
		lines = append(lines, l)
	}
	j := &job{name: name, total: len(lines)}
	m.mu.Lock()
	if m.job != nil && int(m.job.done.Load()) < m.job.total && !m.job.cancel.Load() {
		m.mu.Unlock()
		return ErrBusy
	}
	m.job = j
	m.mu.Unlock()
	m.emit(Event{Kind: "serial", Dir: "tx", Text: "echo:job " + name + ", " + strconv.Itoa(len(lines)) + " lines"})
	go func() {
		pct := -1
		for i, l := range lines {
			if j.cancel.Load() {
				return
			}
			if p := i * 100 / len(lines); p != pct {
				pct = p
				m.Serial.Send("M73 P"+strconv.Itoa(p), true, nil)
			}
			r := m.Serial.Send(l, true, nil)
			if r == "error:reset" {
				return
			}
			j.done.Add(1)
		}
		m.Serial.Send("M73 P100", true, nil)
		m.emit(Event{Kind: "serial", Dir: "tx", Text: "echo:job done"})
	}()
	return nil
}

// CancelJob stops the job. The lines in the planner still run.
func (m *Machine) CancelJob() {
	m.mu.Lock()
	if m.job != nil {
		m.job.cancel.Store(true)
	}
	m.mu.Unlock()
}
