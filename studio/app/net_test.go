package app

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/beetlebugorg/penplotter/studio/plan"
)

// fakePlotter is a network plotter: G-code on a TCP port ("ok" per line, M6 waits for a
// release), and the HTTP API with the status and the pen table.
type fakePlotter struct {
	ln      net.Listener
	http    *httptest.Server
	mu      sync.Mutex
	lines   []string
	tool    int
	pens    []plan.Pen
	release chan struct{}
	conns   []net.Conn
}

func newFakePlotter(t *testing.T) *fakePlotter {
	f := &fakePlotter{release: make(chan struct{}, 8),
		pens: []plan.Pen{{T: 0, Name: "Black", Color: "#000000"}, {T: 1, Name: "Red", Color: "#ff0000"}}}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	f.ln = ln
	go func() {
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			f.mu.Lock()
			f.conns = append(f.conns, c)
			f.mu.Unlock()
			go f.serve(c)
		}
	}()
	f.http = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		f.mu.Lock()
		defer f.mu.Unlock()
		switch {
		case r.URL.Path == "/api/status":
			json.NewEncoder(w).Encode(map[string]any{"state": "idle", "tool": f.tool, "homed": true})
		case r.URL.Path == "/api/pens" && r.Method == "GET":
			json.NewEncoder(w).Encode(f.pens)
		case r.URL.Path == "/api/pens" && r.Method == "PUT":
			json.NewDecoder(r.Body).Decode(&f.pens)
		default:
			w.WriteHeader(404)
		}
	}))
	t.Cleanup(func() { ln.Close(); f.http.Close(); f.drop() })
	return f
}

func (f *fakePlotter) serve(c net.Conn) {
	r := bufio.NewReader(c)
	for {
		l, err := r.ReadString('\n')
		if err != nil {
			return
		}
		l = strings.TrimSpace(l)
		f.mu.Lock()
		f.lines = append(f.lines, l)
		if strings.HasPrefix(l, "T") {
			fmt.Sscanf(l, "T%d", &f.tool)
		}
		f.mu.Unlock()
		if l == "M6" {
			<-f.release
		}
		io.WriteString(c, "ok\n")
	}
}

func (f *fakePlotter) drop() {
	f.mu.Lock()
	defer f.mu.Unlock()
	for _, c := range f.conns {
		c.Close()
	}
	f.conns = nil
}

func (f *fakePlotter) target() string {
	_, hp, _ := net.SplitHostPort(strings.TrimPrefix(f.http.URL, "http://"))
	return "tcp://" + f.ln.Addr().String() + "?http=" + hp
}

func call(t *testing.T, h http.Handler, method, path string, body any) map[string]any {
	t.Helper()
	b, _ := json.Marshal(body)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(method, path, bytes.NewReader(b)))
	var out map[string]any
	json.Unmarshal(rec.Body.Bytes(), &out)
	if rec.Code/100 != 2 {
		t.Fatalf("%s %s: %d %s", method, path, rec.Code, rec.Body.String())
	}
	return out
}

func waitFor(t *testing.T, what string, d time.Duration, ok func() bool) {
	t.Helper()
	end := time.Now().Add(d)
	for time.Now().Before(end) {
		if ok() {
			return
		}
		time.Sleep(20 * time.Millisecond)
	}
	t.Fatalf("timeout: %s", what)
}

func TestNetworkPlotter(t *testing.T) {
	fp := newFakePlotter(t)
	a := New(Config{Port: fp.target(), TravelX: 250, TravelY: 395, DataDir: t.TempDir()})
	defer a.Close()
	h := a.Handler()

	st := call(t, h, "GET", "/api/status", nil)
	if st["connected"] != true || st["link"] != "wifi" {
		t.Fatalf("status: %v", st)
	}
	// The pen table of the plotter wins.
	waitFor(t, "pen sync", 3*time.Second, func() bool {
		a.mu.Lock()
		defer a.mu.Unlock()
		return len(a.pens) == 2
	})

	// A red and a black line: two pens, two changes, the red pen (lighter) first.
	item := plan.Item{Name: "two", W: 10, H: 10, X: 50, Y: 50, Scale: 1,
		Lines:  [][]plan.Pt{{{X: 0, Y: 0}, {X: 10, Y: 0}}, {{X: 0, Y: 10}, {X: 10, Y: 10}}},
		Colors: []string{"#000000", "#ee1111"}, Layers: []string{"", ""}}
	stats := call(t, h, "POST", "/api/plot", map[string]any{"items": []plan.Item{item}, "feed": 3000})
	if stats["pen_changes"].(float64) != 2 {
		t.Fatalf("stats: %v", stats)
	}
	waitFor(t, "the first pen change", 3*time.Second, func() bool {
		j := call(t, h, "GET", "/api/status", nil)["job"].(map[string]any)
		return j["pen_change"] == float64(1)
	})
	fp.release <- struct{}{}
	waitFor(t, "the second pen change", 3*time.Second, func() bool {
		j := call(t, h, "GET", "/api/status", nil)["job"].(map[string]any)
		return j["pen_change"] == float64(0)
	})
	fp.release <- struct{}{}
	waitFor(t, "the end of the job", 3*time.Second, func() bool {
		j := call(t, h, "GET", "/api/status", nil)["job"].(map[string]any)
		return j["state"] == "done"
	})
	fp.mu.Lock()
	got := strings.Join(fp.lines, " ")
	fp.mu.Unlock()
	if strings.Index(got, "T1 M6") < 0 || strings.Index(got, "T0 M6") < strings.Index(got, "T1 M6") {
		t.Fatalf("program: %s", got)
	}

	// A dropped link comes back.
	fp.drop()
	waitFor(t, "reconnect", 8*time.Second, func() bool {
		a.mu.Lock()
		defer a.mu.Unlock()
		fp.mu.Lock()
		n := len(fp.conns)
		fp.mu.Unlock()
		return a.port != nil && n > 0
	})
}
