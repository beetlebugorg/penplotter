// Package serial talks to the plotter firmware: one G-code line at a time, each acknowledged
// with "ok" (or "error").
package serial

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"strings"
	"sync"
	"time"
)

// Port is a line link to the firmware.
type Port struct {
	rw    io.ReadWriteCloser
	lines chan string
	mu    sync.Mutex // one command at a time
	log   func(dir, text string)
	done  chan struct{}
}

// New wraps an open device. log gets each line ("tx" sent, "rx" received); it can be nil.
func New(rw io.ReadWriteCloser, log func(dir, text string)) *Port {
	if log == nil {
		log = func(string, string) {}
	}
	p := &Port{rw: rw, lines: make(chan string, 256), log: log, done: make(chan struct{})}
	go p.read()
	return p
}

func (p *Port) read() {
	defer close(p.done)
	r := bufio.NewReader(p.rw)
	for {
		s, err := r.ReadString('\n')
		s = strings.TrimSpace(s)
		if s != "" {
			p.log("rx", s)
			select {
			case p.lines <- s:
			default:
				// Nobody waits: drop old lines.
				select {
				case <-p.lines:
				default:
				}
				p.lines <- s
			}
		}
		if err != nil {
			return
		}
	}
}

// Close closes the device.
func (p *Port) Close() error { return p.rw.Close() }

// Done is closed when the device stops: a closed port, a lost USB device, a dropped network link.
func (p *Port) Done() <-chan struct{} { return p.done }

// ErrClosed is the error of a port whose device is gone.
var ErrClosed = errors.New("serial: the device is closed")

// Command sends one line and waits for its "ok". It returns the other lines of the reply.
// An "error" reply gives an error.
func (p *Port) Command(ctx context.Context, line string) ([]string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.command(ctx, line)
}

func (p *Port) command(ctx context.Context, line string) ([]string, error) {
	line = strings.TrimSpace(line)
	// Drop old lines (a banner, a late echo).
	for {
		select {
		case <-p.lines:
			continue
		default:
		}
		break
	}
	p.log("tx", line)
	if _, err := io.WriteString(p.rw, line+"\n"); err != nil {
		return nil, err
	}
	var out []string
	for {
		select {
		case <-ctx.Done():
			return out, ctx.Err()
		case <-p.done:
			return out, ErrClosed
		case s := <-p.lines:
			switch {
			case strings.HasPrefix(s, "ok"):
				return out, nil
			case strings.HasPrefix(s, "error"):
				return out, fmt.Errorf("serial: %q: %s", line, s)
			default:
				out = append(out, s)
			}
		}
	}
}

// Program splits G-code text into the lines to send: no comments, no empty lines.
func Program(text string) []string {
	var out []string
	for _, l := range strings.Split(text, "\n") {
		if i := strings.IndexByte(l, ';'); i >= 0 {
			l = l[:i]
		}
		if i := strings.IndexByte(l, '('); i >= 0 && strings.HasSuffix(strings.TrimSpace(l), ")") {
			l = l[:i]
		}
		l = strings.TrimSpace(l)
		if l != "" {
			out = append(out, l)
		}
	}
	return out
}

// Job streams a program. Pause, Resume and Cancel control it.
type Job struct {
	Lines []string

	mu      sync.Mutex
	done    int
	paused  bool
	state   string // "running", "paused", "done", "cancelled", "failed"
	err     error
	resume  chan struct{}
	cancel  context.CancelFunc
	started time.Time
	ended   time.Time
}

// Status is the progress of a job.
type Status struct {
	State   string  `json:"state"`
	Done    int     `json:"done"`
	Total   int     `json:"total"`
	Error   string  `json:"error,omitempty"`
	Seconds float64 `json:"seconds"`
}

// Status returns the progress.
func (j *Job) Status() Status {
	j.mu.Lock()
	defer j.mu.Unlock()
	s := Status{State: j.state, Done: j.done, Total: len(j.Lines)}
	if j.err != nil {
		s.Error = j.err.Error()
	}
	end := j.ended
	if end.IsZero() {
		end = time.Now()
	}
	s.Seconds = end.Sub(j.started).Seconds()
	return s
}

// Pause stops after the current line.
func (j *Job) Pause() {
	j.mu.Lock()
	defer j.mu.Unlock()
	if j.state == "running" {
		j.paused, j.state = true, "paused"
	}
}

// Resume goes on after a pause.
func (j *Job) Resume() {
	j.mu.Lock()
	defer j.mu.Unlock()
	if j.paused {
		j.paused, j.state = false, "running"
		select {
		case j.resume <- struct{}{}:
		default:
		}
	}
}

// Cancel stops the job. The port then sends M5 to lift the pen.
func (j *Job) Cancel() {
	j.mu.Lock()
	c := j.cancel
	j.mu.Unlock()
	if c != nil {
		c()
	}
}

// Wait waits for the end of the job and returns its error.
func (j *Job) Wait() error {
	for {
		s := j.Status()
		if s.State == "done" || s.State == "cancelled" || s.State == "failed" {
			j.mu.Lock()
			defer j.mu.Unlock()
			return j.err
		}
		time.Sleep(20 * time.Millisecond)
	}
}

// Stream starts a job. The port runs one job at a time: other commands wait for its end.
func (p *Port) Stream(lines []string) *Job {
	ctx, cancel := context.WithCancel(context.Background())
	j := &Job{Lines: lines, state: "running", resume: make(chan struct{}, 1), cancel: cancel, started: time.Now()}
	go func() {
		p.mu.Lock()
		defer p.mu.Unlock()
		var err error
		for i, l := range lines {
			for {
				j.mu.Lock()
				paused := j.paused
				j.mu.Unlock()
				if !paused {
					break
				}
				select {
				case <-j.resume:
				case <-ctx.Done():
				}
				if ctx.Err() != nil {
					break
				}
			}
			if ctx.Err() != nil {
				break
			}
			if _, err = p.command(ctx, l); err != nil {
				break
			}
			j.mu.Lock()
			j.done = i + 1
			j.mu.Unlock()
		}
		state := "done"
		if ctx.Err() != nil {
			state, err = "cancelled", nil
			c, cc := context.WithTimeout(context.Background(), 5*time.Second)
			p.command(c, "M5")
			cc()
		} else if err != nil {
			state = "failed"
		}
		cancel()
		j.mu.Lock()
		j.state, j.err, j.ended = state, err, time.Now()
		j.mu.Unlock()
	}()
	return j
}
