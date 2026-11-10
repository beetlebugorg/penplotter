package sim

import (
	"context"
	"encoding/json"
	"math"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/coder/websocket"
)

func waitJob(t *testing.T, m *Machine, d time.Duration) {
	t.Helper()
	end := time.Now().Add(d)
	for time.Now().Before(end) {
		s := m.Snapshot()
		if s.Total > 0 && s.Done == s.Total && !s.Status.Busy && s.Queued == 0 {
			return
		}
		time.Sleep(20 * time.Millisecond)
	}
	s := m.Snapshot()
	t.Fatalf("job did not finish: %d/%d busy=%v state=%s", s.Done, s.Total, s.Status.Busy, s.Status.State)
}

func TestPlotSquare(t *testing.T) {
	text, err := os.ReadFile("../samples/square.gcode")
	if err != nil {
		t.Fatal(err)
	}
	m := New()
	m.SetSpeed(100)
	if err := m.StartJob("square.gcode", string(text)); err != nil {
		t.Fatal(err)
	}
	waitJob(t, m, 30*time.Second)
	for end := time.Now().Add(5 * time.Second); time.Now().Before(end); time.Sleep(10 * time.Millisecond) {
		if s := m.Snapshot(); s.X == 0 && s.Y == 0 && s.Y2 == 0 && s.Pen < 0.01 {
			break
		}
	}
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
		// The servo needs time to lift, so allow a short tail of ink.
		if math.Abs(lo[a]-20) > 0.3 || math.Abs(hi[a]-60) > 0.3 {
			t.Errorf("axis %d ink from %.2f to %.2f, want 20 to 60", a, lo[a], hi[a])
		}
	}
	// The model publishes a little after the firmware. Wait for the end position.
	var s Snapshot
	for end := time.Now().Add(5 * time.Second); time.Now().Before(end); time.Sleep(10 * time.Millisecond) {
		s = m.Snapshot()
		if s.X == 0 && s.Y == 0 && s.Y2 == 0 && s.Pen < 0.01 {
			break
		}
	}
	if !s.Status.Homed || s.X != 0 || s.Y != 0 || s.Y2 != 0 || s.Pen > 0.01 {
		t.Errorf("end state: homed=%v x=%v y=%v y2=%v pen=%v", s.Status.Homed, s.X, s.Y, s.Y2, s.Pen)
	}
}

func TestWebSocketStart(t *testing.T) {
	m := New()
	srv := httptest.NewServer(NewServer(m, WebFS(), "").Handler())
	defer srv.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	c, _, err := websocket.Dial(ctx, "ws"+strings.TrimPrefix(srv.URL, "http")+"/ws", nil)
	if err != nil {
		t.Fatal(err)
	}
	defer c.CloseNow()
	seen := map[string]bool{}
	for len(seen) < 3 {
		_, data, err := c.Read(ctx)
		if err != nil {
			t.Fatalf("read: %v (seen %v)", err, seen)
		}
		var msg struct {
			T       string          `json:"t"`
			Machine json.RawMessage `json:"machine"`
			Bits    string          `json:"bits"`
		}
		json.Unmarshal(data, &msg)
		seen[msg.T] = true
		if msg.T == "hello" && !strings.Contains(string(msg.Machine), `"layout":"table"`) {
			t.Errorf("hello has no table layout: %s", msg.Machine)
		}
		if msg.T == "lcd" && len(msg.Bits) != 1368 {
			t.Errorf("lcd bits length %d", len(msg.Bits))
		}
	}
	if !seen["hello"] || !seen["lcd"] || !seen["state"] {
		t.Errorf("start messages: %v", seen)
	}
	// A console line gets a reply on the serial channel.
	c.Write(ctx, websocket.MessageText, []byte(`{"t":"line","text":"M115"}`))
	for {
		_, data, err := c.Read(ctx)
		if err != nil {
			t.Fatal(err)
		}
		if strings.Contains(string(data), "FIRMWARE_NAME") {
			break
		}
	}
}
