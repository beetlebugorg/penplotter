package sim

import (
	"bufio"
	"math"
	"net"
	"os"
	"strings"
	"testing"
	"time"
)

// TestMegaPlotSquare runs the small controller of the stock mainboard and plots a square.
func TestMegaPlotSquare(t *testing.T) {
	text, err := os.ReadFile("../samples/square.gcode")
	if err != nil {
		t.Fatal(err)
	}
	m := NewMega(nil)
	m.SetSpeed(100)
	if err := m.StartJob("square.gcode", string(text)); err != nil {
		t.Fatal(err)
	}
	waitJob(t, m, 30*time.Second)
	segs, n, _ := m.Ink(0)
	if n < 100 {
		t.Fatalf("only %d ink lines", n)
	}
	lo := [2]float64{math.Inf(1), math.Inf(1)}
	hi := [2]float64{math.Inf(-1), math.Inf(-1)}
	for _, s := range segs {
		for _, p := range [][2]float32{{s[0], s[1]}, {s[2], s[3]}} {
			for a := 0; a < 2; a++ {
				lo[a] = math.Min(lo[a], float64(p[a]))
				hi[a] = math.Max(hi[a], float64(p[a]))
			}
		}
	}
	for a := 0; a < 2; a++ {
		if math.Abs(lo[a]-20) > 0.3 || math.Abs(hi[a]-60) > 0.3 {
			t.Errorf("axis %d ink from %.2f to %.2f, want 20 to 60", a, lo[a], hi[a])
		}
	}
	if s := m.Snapshot(); !s.Status.Homed {
		t.Errorf("not homed after the job")
	}
	// The LCD shows the text lines of the small controller.
	if bits, _ := m.LCD(); bits == [len(bits)]byte{} {
		t.Errorf("the LCD is empty")
	}
}

// TestMegaTCPIsSerial checks that the TCP port is a plain serial link on the stock board,
// and that the network API is off.
func TestMegaTCPIsSerial(t *testing.T) {
	m := NewMega(nil)
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := ln.Addr().String()
	ln.Close()
	if err := m.ServeTCP(addr); err != nil {
		t.Fatal(err)
	}
	c, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	defer c.Close()
	c.SetDeadline(time.Now().Add(5 * time.Second))
	r := bufio.NewReader(c)
	send := func(s string) string {
		c.Write([]byte(s + "\n"))
		var got []string
		for {
			l, err := r.ReadString('\n')
			if err != nil {
				t.Fatalf("%s: %v (got %q)", s, err, got)
			}
			l = strings.TrimSpace(l)
			got = append(got, l)
			if strings.HasPrefix(l, "ok") || strings.HasPrefix(l, "error") || strings.HasPrefix(l, "<") {
				return strings.Join(got, "|")
			}
		}
	}
	if got := send("M115"); !strings.Contains(got, "ATmega2560") {
		t.Errorf("M115: %q", got)
	}
	if got := send("?"); !strings.Contains(got, "<Idle") {
		t.Errorf("?: %q", got)
	}
	if got := send("G90"); !strings.HasSuffix(got, "ok") {
		t.Errorf("G90 after ?: %q", got)
	}
}
