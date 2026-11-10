package controller

import "sync"

// Port is one host connection: the USB serial port, a TCP client, a network job, or a
// command from the network API. The controller reads lines from each port and answers on
// the same port.
//
// One port at a time owns the machine. The owner sends motion and state lines. The other
// ports can send queries (M105, M114, M115, M119, M503, ?) and the safety lines M112 and
// M108. Other lines from them get "error:busy". The owner keeps the machine until the
// machine is idle and the owner sends nothing for OwnerHoldMs.
type Port interface {
	// ReadByte returns the next byte from the host, if there is one.
	Get() (byte, bool)
	// Write sends text to the host.
	Write(s string)
}

// MaxPorts is the number of ports the controller can serve at the same time.
const MaxPorts = 6

// OwnerHoldMs is how long an owner keeps the machine after its last line, when the machine is idle.
const OwnerHoldMs = 2000

// USB is the id of the USB serial port. It is always open.
const USB = 0

type portState struct {
	p        Port
	name     string
	open     bool
	buf      [lineMax]byte
	n        int
	ready    bool
	overflow bool
	comment  bool
}

// halPort is the USB serial port of the board.
type halPort struct{ h HAL }

func (p halPort) Get() (byte, bool) { return p.h.ReadSerial() }
func (p halPort) Write(s string)    { p.h.WriteSerial(s) }

// AddPort opens a port and returns its id, or -1 if all ports are in use.
// Call it from the controller goroutine, or through Do.
func (c *Controller) AddPort(name string, p Port) int {
	for i := 1; i < MaxPorts; i++ {
		if !c.ports[i].open {
			c.ports[i] = portState{p: p, name: name, open: true}
			return i
		}
	}
	return -1
}

// ClosePort closes a port. The moves that it queued still run.
func (c *Controller) ClosePort(id int) {
	if id <= USB || id >= MaxPorts || !c.ports[id].open {
		return
	}
	c.ports[id] = portState{}
	if c.owner == id {
		c.owner = -1
	}
	if c.waitPort == id {
		c.waitPort = -1 // the answer of the waiting line goes nowhere
	}
}

// OwnerName returns the name of the port that owns the machine, or "".
func (c *Controller) OwnerName() string {
	if c.owner < 0 {
		return ""
	}
	return c.ports[c.owner].name
}

// readPorts collects input from each open port, up to one complete line per port.
// The real-time characters work at once: '?' sends the status, Ctrl-X stops the machine.
func (c *Controller) readPorts() {
	for id := range c.ports {
		ps := &c.ports[id]
		if !ps.open {
			continue
		}
		for !ps.ready {
			b, ok := ps.p.Get()
			if !ok {
				break
			}
			switch b {
			case '?':
				if ps.n == 0 {
					ps.p.Write(c.statusLine())
					continue
				}
			case 0x18: // Ctrl-X
				c.emergency("reset (" + ps.name + ")")
				continue
			case '\n', '\r':
				if ps.overflow {
					ps.p.Write("error:line too long\n")
					ps.n, ps.overflow, ps.comment = 0, false, false
					continue
				}
				ps.comment = false
				if ps.n > 0 {
					ps.ready = true
				}
				continue
			case ';':
				// A comment can be longer than a line: do not keep it.
				ps.comment = true
			}
			if ps.comment {
				continue
			}
			if ps.n == lineMax {
				ps.overflow = true
				continue
			}
			ps.buf[ps.n] = b
			ps.n++
		}
	}
}

// dispatch runs the ready lines. Queries run at once on any port. Lines of the owner run
// when the planner has space and no line waits. Other lines get "error:busy".
func (c *Controller) dispatch() {
	if c.wait == waitNone && c.inLen > 0 && c.pl.Space() >= 3 {
		s := c.internal[c.inHead]
		c.inHead = (c.inHead + 1) % len(c.internal)
		c.inLen--
		c.exec(s, -1)
	}
	for k := 0; k < MaxPorts; k++ {
		id := (c.rr + k) % MaxPorts
		ps := &c.ports[id]
		if !ps.open || !ps.ready {
			continue
		}
		line := string(ps.buf[:ps.n])
		switch {
		case isQuery(line) || isSafety(line):
			ps.n, ps.ready = 0, false
			c.exec(line, id)
		case c.owner >= 0 && c.owner != id:
			ps.n, ps.ready = 0, false
			ps.p.Write("error:busy, " + c.ports[c.owner].name + " has the machine\n")
		case c.wait == waitNone && c.pl.Space() >= 3:
			ps.n, ps.ready = 0, false
			if c.owner != id {
				c.owner = id
				c.ownerLines = 0
			}
			c.ownerLast = c.hal.NowMicros()
			c.lineNo++
			c.ownerLines++
			c.exec(line, id)
		}
	}
	c.rr = (c.rr + 1) % MaxPorts
	// Release the owner when the machine is idle and the owner is quiet.
	if c.owner >= 0 && c.wait == waitNone && !c.ports[c.owner].ready && c.idle() &&
		c.hal.NowMicros()-c.ownerLast > OwnerHoldMs*1000 {
		c.owner = -1
	}
}

// isQuery tells if a line only reads the state. Any port can send it.
func isQuery(line string) bool {
	m, ok := mcode(line)
	if !ok {
		return false
	}
	switch m {
	case 105, 114, 115, 119, 503:
		return true
	}
	return false
}

// isSafety tells if a line is an emergency stop (M112) or a continue (M108).
// Any port can send them.
func isSafety(line string) bool {
	m, ok := mcode(line)
	return ok && (m == 112 || m == 108)
}

// mcode returns the number of a line that starts with an M word, as in "M114".
func mcode(line string) (int, bool) {
	t := trim(line)
	if len(t) < 2 || (t[0] != 'M' && t[0] != 'm') {
		return 0, false
	}
	v, i := 0, 1
	for i < len(t) && t[i] >= '0' && t[i] <= '9' {
		v = v*10 + int(t[i]-'0')
		i++
	}
	if i == 1 || (i < len(t) && t[i] != ' ' && t[i] != '\t' && t[i] != ';') {
		return 0, false
	}
	return v, true
}

// Pipe is a Port for a goroutine other than the controller: a TCP client, a network job,
// or one API command. The other goroutine feeds input with Feed and reads output with
// TakeOutput. It is safe for two goroutines.
type Pipe struct {
	mu     sync.Mutex
	in     [1024]byte
	ih, it int // input head and tail (count)
	out    []byte
	eof    bool
}

// pipeOutMax limits the output buffer. Older text drops when a client does not read.
const pipeOutMax = 4096

// Feed adds input. It returns the number of bytes it took; the rest must wait.
func (p *Pipe) Feed(b []byte) int {
	p.mu.Lock()
	defer p.mu.Unlock()
	n := 0
	for _, x := range b {
		if p.ih-p.it == len(p.in) {
			break
		}
		p.in[p.ih%len(p.in)] = x
		p.ih++
		n++
	}
	return n
}

// FeedString adds a whole line of input. It returns false if it does not fit.
func (p *Pipe) FeedString(s string) bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.in)-(p.ih-p.it) < len(s) {
		return false
	}
	for i := 0; i < len(s); i++ {
		p.in[p.ih%len(p.in)] = s[i]
		p.ih++
	}
	return true
}

// InputEmpty tells if the controller has read all input.
func (p *Pipe) InputEmpty() bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.ih == p.it
}

// ReadByte implements Port.
func (p *Pipe) Get() (byte, bool) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.ih == p.it {
		return 0, false
	}
	b := p.in[p.it%len(p.in)]
	p.it++
	return b, true
}

// Write implements Port.
func (p *Pipe) Write(s string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.out)+len(s) > pipeOutMax {
		drop := len(p.out) + len(s) - pipeOutMax
		if drop > len(p.out) {
			drop = len(p.out)
		}
		p.out = append(p.out[:0], p.out[drop:]...)
	}
	p.out = append(p.out, s...)
}

// TakeOutput moves the output into b and returns the number of bytes.
func (p *Pipe) TakeOutput(b []byte) int {
	p.mu.Lock()
	defer p.mu.Unlock()
	n := copy(b, p.out)
	p.out = append(p.out[:0], p.out[n:]...)
	return n
}
