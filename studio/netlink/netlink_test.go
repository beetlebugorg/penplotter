package netlink

import (
	"bufio"
	"context"
	"encoding/binary"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// response builds an mDNS response: a PTR, an SRV and an A record, with a compression pointer
// from the SRV target to the A record name.
func response() []byte {
	b := make([]byte, 12)
	binary.BigEndian.PutUint16(b[2:], 0x8400)
	binary.BigEndian.PutUint16(b[6:], 3)
	rec := func(b []byte, name []byte, t uint16, data []byte) []byte {
		b = append(b, name...)
		b = binary.BigEndian.AppendUint16(b, t)
		b = binary.BigEndian.AppendUint16(b, 1)
		b = binary.BigEndian.AppendUint32(b, 120)
		b = binary.BigEndian.AppendUint16(b, uint16(len(data)))
		return append(b, data...)
	}
	inst := encodeName(nil, "studio-plotter."+Service)
	b = rec(b, encodeName(nil, Service), typePTR, inst)
	hostOff := 0
	srv := []byte{0, 0, 0, 0, 0, 23}
	// The SRV target points to the A record name, which follows.
	b = rec(b, inst, typeSRV, append(srv, 0xC0, 0)) // placeholder pointer, fixed below
	ptrAt := len(b) - 2
	hostOff = len(b)
	b = rec(b, encodeName(nil, "penplotter.local"), typeA, []byte{192, 168, 1, 50})
	binary.BigEndian.PutUint16(b[ptrAt:], 0xC000|uint16(hostOff))
	return b
}

func TestParseResponse(t *testing.T) {
	rs, err := parse(response())
	if err != nil {
		t.Fatal(err)
	}
	if len(rs) != 3 {
		t.Fatalf("records: %d", len(rs))
	}
	if rs[2].name != "penplotter.local" || net.IP(rs[2].data).String() != "192.168.1.50" {
		t.Fatalf("A record: %+v", rs[2])
	}
	h, _, err := readName(rs[1].msg, rs[1].off+6)
	if err != nil || h != "penplotter.local" {
		t.Fatalf("SRV target %q %v", h, err)
	}
}

func TestQueryEncoding(t *testing.T) {
	q := encodeQuery(7, []question{{"penplotter.local", typeA}})
	if binary.BigEndian.Uint16(q[4:]) != 1 {
		t.Fatal("question count")
	}
	n, off, err := readName(q, 12)
	if err != nil || n != "penplotter.local" || binary.BigEndian.Uint16(q[off:]) != typeA {
		t.Fatalf("%q %v", n, err)
	}
}

func TestParseTarget(t *testing.T) {
	cases := map[string]Target{
		"penplotter.local":               {Host: "penplotter.local", GCode: 23, HTTPBase: "http://penplotter.local:80"},
		"192.168.1.50:2323":              {Host: "192.168.1.50", GCode: 2323, HTTPBase: "http://192.168.1.50:80"},
		"tcp://10.0.0.2":                 {Host: "10.0.0.2", GCode: 23, HTTPBase: "http://10.0.0.2:80", Raw: true},
		"http://127.0.0.1:8790/":         {Host: "127.0.0.1", GCode: 23, HTTPBase: "http://127.0.0.1:8790"},
		"tcp://127.0.0.1:2323?http=8766": {Host: "127.0.0.1", GCode: 2323, HTTPBase: "http://127.0.0.1:8766"},
	}
	for in, want := range cases {
		got, err := ParseTarget(in)
		if err != nil || got != want {
			t.Errorf("%s: %+v %v", in, got, err)
		}
	}
	for _, s := range []string{"/dev/ttyACM0", "COM3", ""} {
		if IsNetwork(s) {
			t.Errorf("%q is not a network address", s)
		}
	}
	if !IsNetwork("penplotter.local") {
		t.Error("penplotter.local is a network address")
	}
}

func TestClient(t *testing.T) {
	pens := []Pen{{T: 0, Name: "Black", Color: "#000000"}}
	busy := false
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/api/status":
			// The firmware form: upper case state, the pen as a word.
			w.Write([]byte(`{"state":"PEN CHANGE","x":1,"y":2,"pen":"down","tool":3,"homed":true,"alarm":false,"msg":"Load pen T3","progress":-1}`))
		case r.URL.Path == "/api/pens" && r.Method == "GET":
			json.NewEncoder(w).Encode(pens)
		case r.URL.Path == "/api/pens" && r.Method == "PUT":
			json.NewDecoder(r.Body).Decode(&pens)
		case r.URL.Path == "/api/job":
			if busy {
				w.WriteHeader(409)
				return
			}
			busy = true
		case r.URL.Path == "/api/cmd":
			b, _ := io.ReadAll(r.Body)
			if strings.TrimSpace(string(b)) == "" {
				w.WriteHeader(400)
			}
		}
	}))
	defer srv.Close()
	c := NewClient(srv.URL)
	ctx := context.Background()
	s, err := c.Status(ctx)
	if err != nil || !s.Online || s.Tool != 3 || !s.Homed || s.State != "pen_change" || s.Pen != 1 || s.Msg != "Load pen T3" {
		t.Fatalf("status %+v %v", s, err)
	}
	if err := c.SetPens(ctx, append(pens, Pen{T: 1, Name: "Red", Color: "#ff0000"})); err != nil {
		t.Fatal(err)
	}
	p, err := c.Pens(ctx)
	if err != nil || len(p) != 2 || p[1].Color != "#ff0000" {
		t.Fatalf("pens %+v %v", p, err)
	}
	if err := c.Job(ctx, "a b.gcode", "G28\n"); err != nil {
		t.Fatal(err)
	}
	if err := c.Job(ctx, "x", "G28\n"); err != ErrBusy {
		t.Fatalf("want ErrBusy, got %v", err)
	}
	if err := c.Cmd(ctx, "M5"); err != nil {
		t.Fatal(err)
	}
}

func TestDial(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go func() {
		c, err := ln.Accept()
		if err != nil {
			return
		}
		r := bufio.NewReader(c)
		for {
			if _, err := r.ReadString('\n'); err != nil {
				return
			}
			io.WriteString(c, "ok\n")
		}
	}()
	tg, _ := ParseTarget(ln.Addr().String())
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	c, err := Dial(ctx, tg)
	if err != nil {
		t.Fatal(err)
	}
	defer c.Close()
	io.WriteString(c, "M114\n")
	line, err := bufio.NewReader(c).ReadString('\n')
	if err != nil || strings.TrimSpace(line) != "ok" {
		t.Fatalf("%q %v", line, err)
	}
}
