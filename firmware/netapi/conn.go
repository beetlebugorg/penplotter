package netapi

import (
	"errors"
	"io"
	"net"
	"strconv"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/controller"
)

// Conn is one TCP connection. A net.Conn with a no-op Flush works, and so does a
// connection of the Pico W network stack.
type Conn interface {
	io.ReadWriter
	Flush() error
	SetReadDeadline(t time.Time) error
}

// ServeGcode bridges a TCP client to a controller port: G-code lines in, replies out,
// with "ok" flow control as on the USB port. It returns when the client closes.
func (s *Server) ServeGcode(conn Conn, name string) {
	p := &controller.Pipe{}
	id := -1
	if !s.call(func() { id = s.C.AddPort(name, p) }) || id < 0 {
		conn.Write([]byte("error:too many connections\n"))
		conn.Flush()
		return
	}
	defer s.call(func() { s.C.ClosePort(id) })
	conn.Write([]byte("echo:pen plotter, send G-code lines\n"))
	conn.Flush()
	var in [256]byte
	var out [512]byte
	pending := in[:0]
	for {
		if n := p.TakeOutput(out[:]); n > 0 {
			if _, err := conn.Write(out[:n]); err != nil {
				return
			}
			conn.Flush()
		}
		if len(pending) > 0 {
			k := p.Feed(pending)
			pending = pending[k:]
			if len(pending) > 0 {
				s.sleep()
				continue
			}
		}
		conn.SetReadDeadline(s.now().Add(5 * time.Millisecond))
		n, err := conn.Read(in[:])
		pending = in[:n]
		if err != nil && n == 0 {
			if errors.Is(err, io.EOF) || errors.Is(err, net.ErrClosed) {
				return
			}
			// A read timeout: send the output, then read again.
		}
	}
}

// ServeHTTP reads one HTTP/1.1 request from conn, serves it, and writes the response.
// The body must have a Content-Length. The connection closes after the response.
func (s *Server) ServeHTTP(conn Conn) {
	var hb [1024]byte
	n, end := 0, -1
	deadline := s.now().Add(10 * time.Second)
	for end < 0 {
		if n == len(hb) {
			writeResponse(conn, 431, "application/json", errJSON("header too large"))
			return
		}
		conn.SetReadDeadline(s.now().Add(50 * time.Millisecond))
		k, err := conn.Read(hb[n:])
		n += k
		end = headerEnd(hb[:n])
		if err != nil && k == 0 && end < 0 {
			if errors.Is(err, io.EOF) || errors.Is(err, net.ErrClosed) || s.now().After(deadline) {
				return
			}
		}
	}
	head := string(hb[:end])
	method, target, ok := requestLine(head)
	if !ok {
		writeResponse(conn, 400, "application/json", errJSON("bad request"))
		return
	}
	path, query := target, ""
	for i := 0; i < len(target); i++ {
		if target[i] == '?' {
			path, query = target[:i], target[i+1:]
			break
		}
	}
	hdr := func(name string) string { return header(head, name) }
	length := 0
	if v := hdr("Content-Length"); v != "" {
		length, _ = strconv.Atoi(v)
	} else if hdr("Transfer-Encoding") != "" {
		writeResponse(conn, 411, "application/json", errJSON("send a Content-Length"))
		return
	}
	body := &bodyReader{conn: conn, pre: hb[end+4 : n], left: length, s: s}
	req := &Request{Method: method, Path: path, Query: query, Header: hdr, Body: body}
	s.Handle(req, &connResponse{conn: conn})
}

type connResponse struct {
	conn Conn
	sent bool
}

func (r *connResponse) Send(code int, ctype string, body []byte) {
	if r.sent {
		return
	}
	r.sent = true
	writeResponse(r.conn, code, ctype, body)
}

func writeResponse(conn Conn, code int, ctype string, body []byte) {
	h := "HTTP/1.1 " + strconv.Itoa(code) + " " + reason(code) + "\r\nContent-Type: " + ctype +
		"\r\nContent-Length: " + strconv.Itoa(len(body)) +
		"\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n"
	conn.Write([]byte(h))
	for len(body) > 0 {
		n, err := conn.Write(body)
		if err != nil {
			return
		}
		body = body[n:]
	}
	conn.Flush()
}

func reason(code int) string {
	switch code {
	case 200:
		return "OK"
	case 400:
		return "Bad Request"
	case 404:
		return "Not Found"
	case 405:
		return "Method Not Allowed"
	case 409:
		return "Conflict"
	case 411:
		return "Length Required"
	case 431:
		return "Request Header Fields Too Large"
	case 503:
		return "Service Unavailable"
	}
	return "Status"
}

// bodyReader reads Content-Length bytes: first the bytes after the header, then the conn.
type bodyReader struct {
	conn Conn
	pre  []byte
	left int
	s    *Server
}

func (b *bodyReader) Read(p []byte) (int, error) {
	if b.left <= 0 {
		return 0, io.EOF
	}
	if len(p) > b.left {
		p = p[:b.left]
	}
	if len(b.pre) > 0 {
		n := copy(p, b.pre)
		b.pre = b.pre[n:]
		b.left -= n
		return n, nil
	}
	deadline := b.s.now().Add(30 * time.Second)
	for {
		b.conn.SetReadDeadline(b.s.now().Add(100 * time.Millisecond))
		n, err := b.conn.Read(p)
		b.left -= n
		if n > 0 {
			return n, nil
		}
		if err != nil && (errors.Is(err, io.EOF) || errors.Is(err, net.ErrClosed)) {
			return 0, io.ErrUnexpectedEOF
		}
		if b.s.now().After(deadline) {
			return 0, errors.New("body timeout")
		}
	}
}

func headerEnd(b []byte) int {
	for i := 0; i+3 < len(b); i++ {
		if b[i] == '\r' && b[i+1] == '\n' && b[i+2] == '\r' && b[i+3] == '\n' {
			return i
		}
	}
	return -1
}

func requestLine(head string) (method, target string, ok bool) {
	line := head
	for i := 0; i < len(head); i++ {
		if head[i] == '\r' {
			line = head[:i]
			break
		}
	}
	var parts [3]string
	k, start := 0, 0
	for i := 0; i <= len(line) && k < 3; i++ {
		if i == len(line) || line[i] == ' ' {
			parts[k] = line[start:i]
			k++
			start = i + 1
		}
	}
	return parts[0], parts[1], k == 3 && parts[0] != "" && parts[1] != ""
}

// header returns the value of a header line (the name is case-insensitive).
func header(head, name string) string {
	i := 0
	for i < len(head) {
		j := i
		for j < len(head) && head[j] != '\r' {
			j++
		}
		line := head[i:j]
		if len(line) > len(name) && line[len(name)] == ':' && equalFold(line[:len(name)], name) {
			v := line[len(name)+1:]
			for len(v) > 0 && v[0] == ' ' {
				v = v[1:]
			}
			return v
		}
		i = j + 2
	}
	return ""
}

func equalFold(a, b string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := 0; i < len(a); i++ {
		x, y := a[i], b[i]
		if x >= 'A' && x <= 'Z' {
			x += 32
		}
		if y >= 'A' && y <= 'Z' {
			y += 32
		}
		if x != y {
			return false
		}
	}
	return true
}
