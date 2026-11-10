// Package netapi serves the HTTP API of the plotter. The Pico W and the simulator use the
// same code: each gives it a Request and a Response, and the controller.
//
//	GET  /api/status   the state as JSON
//	POST /api/cmd      one G-code line; the answer is the reply text, up to "ok" or "error"
//	POST /api/job      a G-code file; it streams the lines and answers when all are queued
//	GET  /api/pens     the pen table (T0 to T15) as JSON
//	PUT  /api/pens     changes entries of the pen table
//
// docs/network-api.md describes the API. The package does not use net/http or reflection,
// so it builds with TinyGo.
package netapi

import (
	"io"
	"strconv"
	"sync/atomic"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/controller"
	"github.com/beetlebugorg/penplotter/firmware/settings"
)

// Request is one HTTP request.
type Request struct {
	Method string
	Path   string // without the query
	Query  string // the text after '?'
	Header func(name string) string
	Body   io.Reader
}

// Response sends the answer. Send is called once.
type Response interface {
	Send(code int, contentType string, body []byte)
}

// Server serves the API for one controller.
type Server struct {
	C *controller.Controller
	// Sleep waits a short time. On the Pico it must let other goroutines run.
	Sleep func(d time.Duration)
	// Now returns the time. Tests can replace it.
	Now func() time.Time
}

// CmdTimeout is the longest wait for the answer of one command (M400 waits for the moves).
const CmdTimeout = 10 * time.Minute

func (s *Server) sleep() {
	if s.Sleep != nil {
		s.Sleep(time.Millisecond)
	} else {
		time.Sleep(time.Millisecond)
	}
}

func (s *Server) now() time.Time {
	if s.Now != nil {
		return s.Now()
	}
	return time.Now()
}

// Handle serves one request.
func (s *Server) Handle(r *Request, w Response) {
	switch {
	case r.Path == "/api/status" && r.Method == "GET":
		w.Send(200, "application/json", StatusJSON(s.C.API()))
	case r.Path == "/api/cmd" && r.Method == "POST":
		s.cmd(r, w)
	case r.Path == "/api/job" && r.Method == "POST":
		s.job(r, w)
	case r.Path == "/api/pens" && r.Method == "GET":
		var pens [settings.NumPens]settings.Pen
		if !s.call(func() { pens = s.C.Pens() }) {
			w.Send(503, "application/json", errJSON("controller busy"))
			return
		}
		w.Send(200, "application/json", PensJSON(pens))
	case r.Path == "/api/pens" && r.Method == "PUT":
		s.putPens(r, w)
	case r.Path == "/" || r.Path == "/api":
		w.Send(200, "text/plain", []byte("Pen plotter "+config.Version+"\nAPI: /api/status /api/cmd /api/job /api/pens\n"))
	case len(r.Path) > 5 && r.Path[:5] == "/api/":
		w.Send(405, "application/json", errJSON("method or path not supported"))
	default:
		w.Send(404, "application/json", errJSON("not found"))
	}
}

// call runs f on the controller goroutine and waits for it.
func (s *Server) call(f func()) bool {
	var done atomic.Bool
	for tries := 0; !s.C.Do(func() { f(); done.Store(true) }); tries++ {
		if tries > 1000 {
			return false
		}
		s.sleep()
	}
	deadline := s.now().Add(5 * time.Second)
	for !done.Load() {
		if s.now().After(deadline) {
			return false
		}
		s.sleep()
	}
	return true
}

// cmd runs one line on its own port and returns the reply text.
func (s *Server) cmd(r *Request, w Response) {
	var b [256]byte
	n, _ := io.ReadFull(r.Body, b[:])
	line := trimLine(string(b[:n]))
	if line == "" {
		w.Send(400, "application/json", errJSON("empty command"))
		return
	}
	p := &controller.Pipe{}
	id := -1
	if !s.call(func() { id = s.C.AddPort("api", p) }) || id < 0 {
		w.Send(503, "application/json", errJSON("no free port"))
		return
	}
	defer s.call(func() { s.C.ClosePort(id) })
	p.FeedString(line + "\n")
	var out []byte
	var buf [256]byte
	deadline := s.now().Add(CmdTimeout)
	for {
		n := p.TakeOutput(buf[:])
		out = append(out, buf[:n]...)
		if final(out) {
			break
		}
		if s.now().After(deadline) {
			out = append(out, "error:timeout\n"...)
			break
		}
		s.sleep()
	}
	code := 200
	if lastIsError(out) {
		code = 409
	}
	w.Send(code, "text/plain", out)
}

// job streams a G-code file to a new port that owns the machine.
func (s *Server) job(r *Request, w Response) {
	name := queryValue(r.Query, "name")
	if name == "" && r.Header != nil {
		name = r.Header("X-Job-Name")
	}
	if name == "" {
		name = "job"
	}
	total := 0
	if r.Header != nil {
		total, _ = strconv.Atoi(r.Header("X-Job-Lines"))
	}
	p := &controller.Pipe{}
	id, why := -1, ""
	if !s.call(func() { id, why = s.C.StartJob(name, total, p) }) {
		w.Send(503, "application/json", errJSON("controller busy"))
		return
	}
	if id < 0 {
		w.Send(409, "application/json", errJSON(why))
		return
	}
	defer s.call(func() { s.C.ClosePort(id) })

	var cnt lineCounter
	var in [512]byte
	var out [512]byte
	pending := in[:0]
	eof := false
	replies, errs := 0, 0
	firstErr := ""
	var partial []byte
	for {
		// Feed input as the controller takes it.
		if len(pending) == 0 && !eof {
			n, err := r.Body.Read(in[:])
			pending = in[:n]
			cnt.add(pending)
			if err != nil {
				eof = true
				cnt.end()
			}
		}
		if len(pending) > 0 {
			k := p.Feed(pending)
			pending = pending[k:]
		}
		// Count the answers.
		n := p.TakeOutput(out[:])
		partial = append(partial, out[:n]...)
		for {
			i := indexByte(partial, '\n')
			if i < 0 {
				break
			}
			l := string(partial[:i])
			partial = partial[i+1:]
			switch {
			case len(l) >= 2 && l[:2] == "ok":
				replies++
			case len(l) >= 5 && l[:5] == "error":
				replies++
				errs++
				if firstErr == "" {
					firstErr = l
				}
			case len(l) >= 2 && l[:2] == "!!":
				// Emergency stop: the job ends.
				w.Send(409, "application/json", jobJSON(name, cnt.n, replies, errs+1, l))
				return
			}
		}
		if eof && len(pending) == 0 && p.InputEmpty() && replies >= cnt.n {
			break
		}
		if n == 0 && (len(pending) > 0 || eof) {
			s.sleep()
		}
	}
	w.Send(200, "application/json", jobJSON(name, cnt.n, replies, errs, firstErr))
}

func (s *Server) putPens(r *Request, w Response) {
	var b [2048]byte
	n, _ := io.ReadFull(r.Body, b[:])
	upd, err := ParsePens(b[:n])
	if err != "" {
		w.Send(400, "application/json", errJSON(err))
		return
	}
	var pens [settings.NumPens]settings.Pen
	if !s.call(func() {
		pens = s.C.Pens()
		for _, u := range upd {
			if u.HasName {
				pens[u.T].Name = u.Name
			}
			if u.HasColor {
				pens[u.T].Color = u.Color
			}
		}
		s.C.SetPens(pens)
		pens = s.C.Pens()
	}) {
		w.Send(503, "application/json", errJSON("controller busy"))
		return
	}
	w.Send(200, "application/json", PensJSON(pens))
}

// lineCounter counts the lines that the controller answers: a line with some text before
// a ';' comment. Empty lines and comment lines get no answer.
type lineCounter struct {
	n       int
	content bool
	comment bool
}

func (c *lineCounter) add(b []byte) {
	for _, x := range b {
		switch {
		case x == '\n' || x == '\r':
			if c.content {
				c.n++
			}
			c.content, c.comment = false, false
		case x == ';':
			c.comment = true
		case !c.comment:
			if !(x == '?' && !c.content) { // a '?' at the start is a status request
				c.content = true
			}
		}
	}
}

func (c *lineCounter) end() {
	if c.content {
		c.n++
		c.content = false
	}
}

func final(out []byte) bool {
	for len(out) > 0 {
		i := indexByte(out, '\n')
		if i < 0 {
			return false
		}
		l := out[:i]
		if (len(l) >= 2 && string(l[:2]) == "ok") || (len(l) >= 5 && string(l[:5]) == "error") ||
			(len(l) >= 2 && string(l[:2]) == "!!") {
			return true
		}
		out = out[i+1:]
	}
	return false
}

func lastIsError(out []byte) bool {
	for i := len(out) - 2; i >= 0; i-- {
		if out[i] == '\n' {
			return string(out[i+1:min(i+6, len(out))]) == "error"
		}
	}
	return len(out) >= 5 && string(out[:5]) == "error"
}

func indexByte(b []byte, c byte) int {
	for i, x := range b {
		if x == c {
			return i
		}
	}
	return -1
}

func trimLine(s string) string {
	i, j := 0, len(s)
	for i < j && (s[i] == ' ' || s[i] == '\t' || s[i] == '\r' || s[i] == '\n') {
		i++
	}
	for j > i && (s[j-1] == ' ' || s[j-1] == '\t' || s[j-1] == '\r' || s[j-1] == '\n') {
		j--
	}
	if k := indexByte([]byte(s[i:j]), '\n'); k >= 0 {
		j = i + k
	}
	return s[i:j]
}

// queryValue returns the value of key in a query string such as "name=a.gcode&x=1".
func queryValue(q, key string) string {
	for len(q) > 0 {
		var part string
		if i := indexByte([]byte(q), '&'); i >= 0 {
			part, q = q[:i], q[i+1:]
		} else {
			part, q = q, ""
		}
		if len(part) > len(key) && part[:len(key)] == key && part[len(key)] == '=' {
			return unescape(part[len(key)+1:])
		}
	}
	return ""
}

func unescape(s string) string {
	var b []byte
	for i := 0; i < len(s); i++ {
		switch {
		case s[i] == '+':
			b = append(b, ' ')
		case s[i] == '%' && i+2 < len(s):
			v, err := strconv.ParseUint(s[i+1:i+3], 16, 8)
			if err == nil {
				b = append(b, byte(v))
				i += 2
				continue
			}
			b = append(b, s[i])
		default:
			b = append(b, s[i])
		}
	}
	return string(b)
}
