package netapi

import (
	"io"
	"net"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/controller"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// board is a minimal HAL. The controller goroutine also runs the executor ticks.
type board struct {
	ex   *stepgen.Executor
	us   uint64
	phys [3]int32
	dir  uint8
}

type nullDisplay struct{}

func (nullDisplay) Flush(fb *ui.FB) {
	for fb.Dirty() {
		fb.NextDirty()
	}
}

func (b *board) NowMicros() uint64        { return b.us }
func (b *board) SetMotors(bool)           {}
func (b *board) Endstop(ch int) bool      { return b.phys[ch] <= 0 }
func (b *board) Encoder() int             { return 0 }
func (b *board) Button() bool             { return false }
func (b *board) Beep(int)                 {}
func (b *board) ReadSerial() (byte, bool) { return 0, false }
func (b *board) WriteSerial(string)       {}
func (b *board) Display() ui.Display      { return nullDisplay{} }
func (b *board) Poll()                    {}

func startController(t *testing.T) *controller.Controller {
	b := &board{ex: &stepgen.Executor{}, phys: [3]int32{4000, 4000, 4000}}
	b.ex.Endstop = b.Endstop
	c := controller.New(b, b.ex)
	c.PublishAlways()
	stop := make(chan struct{})
	t.Cleanup(func() { close(stop) })
	go func() {
		for {
			select {
			case <-stop:
				return
			default:
			}
			c.Poll()
			for i := 0; i < 400; i++ {
				o := b.ex.Tick()
				if o.DirSet {
					b.dir = o.Dir
				}
				for a := 0; a < 3; a++ {
					if o.Step&(1<<a) != 0 {
						if b.dir&(1<<a) != 0 {
							b.phys[a]--
						} else {
							b.phys[a]++
						}
					}
				}
			}
			b.us += 400 * 1_000_000 / config.TickHz
			time.Sleep(50 * time.Microsecond)
		}
	}()
	return c
}

// TestServeHTTPOverTCP runs the raw HTTP server of the Pico W on a TCP listener and
// talks to it with net/http.
func TestServeHTTPOverTCP(t *testing.T) {
	s := &Server{C: startController(t)}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			go func() {
				s.ServeHTTP(testConn{conn})
				conn.Close()
			}()
		}
	}()
	url := "http://" + ln.Addr().String()
	r, err := http.Post(url+"/api/job?name=sq", "text/plain",
		strings.NewReader("G28\nG1 X10 Y10 F3000\nM3\nG1 X20\nM5\nM400\n"))
	if err != nil {
		t.Fatal(err)
	}
	b, _ := io.ReadAll(r.Body)
	r.Body.Close()
	if r.StatusCode != 200 || !strings.Contains(string(b), `"lines":6,"answered":6,"errors":0`) {
		t.Fatalf("job: %d %s", r.StatusCode, b)
	}
	r, err = http.Get(url + "/api/status")
	if err != nil {
		t.Fatal(err)
	}
	b, _ = io.ReadAll(r.Body)
	r.Body.Close()
	if !strings.Contains(string(b), `"homed":true`) || !strings.Contains(string(b), `"x":20.000`) {
		t.Fatalf("status: %s", b)
	}
	r, _ = http.Get(url + "/nope")
	if r.StatusCode != 404 {
		t.Fatalf("404: %d", r.StatusCode)
	}
}

func TestServeGcode(t *testing.T) {
	s := &Server{C: startController(t)}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go func() {
		conn, err := ln.Accept()
		if err == nil {
			s.ServeGcode(testConn{conn}, "tcp")
			conn.Close()
		}
	}()
	b, err := net.Dial("tcp", ln.Addr().String())
	if err != nil {
		t.Fatal(err)
	}
	defer b.Close()
	b.SetDeadline(time.Now().Add(10 * time.Second))
	buf := make([]byte, 4096)
	read := func() string {
		var out string
		for !strings.Contains(out, "ok\n") && !strings.Contains(out, "error") {
			n, err := b.Read(buf)
			if err != nil {
				t.Fatalf("read: %v (%q)", err, out)
			}
			out += string(buf[:n])
		}
		return out
	}
	b.Write([]byte("M115\n"))
	if out := read(); !strings.Contains(out, "FIRMWARE_NAME") {
		t.Fatalf("M115: %q", out)
	}
}

func TestParsePens(t *testing.T) {
	u, err := ParsePens([]byte(` [ {"t": 1, "name": "Fine \"liner\"", "color": "#00ff00", "extra": [1,{"a":2}]}, {"t":15,"color":16711680} ] `))
	if err != "" || len(u) != 2 || u[0].Name != `Fine "liner"` || u[0].Color != 0x00FF00 || u[1].T != 15 || u[1].Color != 0xFF0000 || u[1].HasName {
		t.Fatalf("%+v %q", u, err)
	}
	for _, bad := range []string{`[{"name":"x"}]`, `[{"t":16}]`, `{"t":1,"color":"red"}`, `nope`} {
		if _, err := ParsePens([]byte(bad)); err == "" {
			t.Errorf("no error for %s", bad)
		}
	}
}

type testConn struct{ net.Conn }

func (testConn) Flush() error { return nil }
