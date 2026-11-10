package sim

import (
	"strings"
	"sync"
)

// Serial is the USB serial port of the simulated board.
// Several sources share it: the job streamer, the pseudo-terminal and the console.
// It sends one line at a time and waits for "ok" or "error".
type Serial struct {
	m      *Machine
	lineMu sync.Mutex // one line at a time

	mu    sync.Mutex
	rx    []byte
	tx    []byte
	cur   *request
	extra map[int]func(line string) // receivers of lines that are not replies
	nextX int
}

type request struct {
	quiet bool
	reply func(line string)
	done  chan string
}

func newSerial(m *Machine) *Serial { return &Serial{m: m} }

// Send sends one line and waits for its "ok" or "error" line, which it returns.
// reply gets each response line. quiet hides the line and its "ok" from the windows.
func (s *Serial) Send(line string, quiet bool, reply func(string)) string {
	s.lineMu.Lock()
	defer s.lineMu.Unlock()
	r := &request{quiet: quiet, reply: reply, done: make(chan string, 1)}
	s.mu.Lock()
	s.cur = r
	s.rx = append(s.rx, line...)
	s.rx = append(s.rx, '\n')
	s.mu.Unlock()
	if !quiet {
		s.m.emit(Event{Kind: "serial", Dir: "rx", Text: line})
	}
	if !strings.HasPrefix(line, "M73 ") { // progress lines from the streamer
		s.m.mu.Lock()
		s.m.lastRx = line
		s.m.mu.Unlock()
	}
	return <-r.done
}

// Realtime sends one realtime character. It does not wait for a reply.
func (s *Serial) Realtime(b byte) {
	s.mu.Lock()
	s.rx = append(s.rx, b)
	s.mu.Unlock()
}

// OnLine adds a receiver for lines that are not replies to a request.
// The returned function removes the receiver.
func (s *Serial) OnLine(f func(string)) func() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.extra == nil {
		s.extra = map[int]func(string){}
	}
	id := s.nextX
	s.nextX++
	s.extra[id] = f
	return func() {
		s.mu.Lock()
		delete(s.extra, id)
		s.mu.Unlock()
	}
}

func (s *Serial) readByte() (byte, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.rx) == 0 {
		return 0, false
	}
	b := s.rx[0]
	s.rx = s.rx[1:]
	return b, true
}

// write gets text from the firmware and routes each complete line.
func (s *Serial) write(text string) {
	type out struct {
		f    func(string)
		line string
	}
	var calls []out
	var events []Event
	s.mu.Lock()
	s.tx = append(s.tx, text...)
	for {
		i := strings.IndexByte(string(s.tx), '\n')
		if i < 0 {
			break
		}
		line := strings.TrimRight(string(s.tx[:i]), "\r")
		s.tx = s.tx[i+1:]
		final := strings.HasPrefix(line, "ok") || strings.HasPrefix(line, "error")
		r := s.cur
		if r == nil {
			for _, f := range s.extra {
				calls = append(calls, out{f, line})
			}
			events = append(events, Event{Kind: "serial", Dir: "tx", Text: line})
			continue
		}
		if r.reply != nil {
			calls = append(calls, out{r.reply, line})
		}
		if !r.quiet || !strings.HasPrefix(line, "ok") {
			events = append(events, Event{Kind: "serial", Dir: "tx", Text: line})
		}
		if final {
			r.done <- line
			s.cur = nil
		}
	}
	s.mu.Unlock()
	for _, c := range calls {
		c.f(c.line)
	}
	for _, e := range events {
		s.m.emit(e)
	}
}

// reset drops all pending bytes and ends the waiting line with an error.
func (s *Serial) reset() {
	s.mu.Lock()
	s.rx, s.tx = nil, nil
	if s.cur != nil {
		s.cur.done <- "error:reset"
		s.cur = nil
	}
	s.mu.Unlock()
}
