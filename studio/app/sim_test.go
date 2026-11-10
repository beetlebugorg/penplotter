package app

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/sim"
	"github.com/beetlebugorg/penplotter/studio/geom"
	"github.com/beetlebugorg/penplotter/studio/plan"
)

// TestWithSimulator runs plotstudio against the simulator: marks, scan, clicks, solve, plot.
func TestWithSimulator(t *testing.T) {
	if testing.Short() {
		t.Skip("slow")
	}
	m := sim.New()
	m.SetSpeed(20)
	tty, err := m.StartPTY("")
	if err != nil {
		t.Skipf("no pty: %v", err)
	}
	srv := sim.NewServer(m, nil, "")
	srv.Camera = sim.NewCamera(m, sim.CameraOptions{FramePath: "../../hardware/stl/frame.json", K1: -0.08, FullW: 1944, FullH: 1458})
	hs := httptest.NewServer(srv.Handler())
	defer hs.Close()

	a := New(Config{Port: tty, Camera: hs.URL + "/camera.jpg", TravelX: config.TravelX, TravelY: config.TravelY,
		DataDir: t.TempDir(), ParkScan: true, ScanTwice: true, FitLens: true})
	defer a.Close()
	h := a.Handler()
	call := func(method, path string, body any, out any) int {
		var b []byte
		switch v := body.(type) {
		case string:
			b = []byte(v)
		case nil:
		default:
			b, _ = json.Marshal(v)
		}
		req := httptest.NewRequest(method, path, bytes.NewReader(b))
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		if out != nil {
			json.Unmarshal(rec.Body.Bytes(), out)
		}
		if rec.Code != 200 {
			t.Logf("%s %s: %d %s", method, path, rec.Code, rec.Body.String())
		}
		return rec.Code
	}
	wait := func() {
		deadline := time.Now().Add(3 * time.Minute)
		for time.Now().Before(deadline) {
			a.mu.Lock()
			st := a.job.Status()
			a.mu.Unlock()
			if st.State == "done" {
				return
			}
			if st.State == "failed" || st.State == "cancelled" {
				a.mu.Lock()
				logs := a.logs
				if len(logs) > 40 {
					logs = logs[len(logs)-40:]
				}
				for _, l := range logs {
					t.Logf("log %s %s", l.Dir, l.Text)
				}
				a.mu.Unlock()
				t.Fatalf("job: %+v", st)
			}
			time.Sleep(50 * time.Millisecond)
		}
		t.Fatal("the job did not end")
	}

	// 1. Draw the calibration dots (3 x 3) and park.
	var pts []plan.Pt
	if c := call("POST", "/api/calib/mark", map[string]int{"grid": 3}, &pts); c != 200 || len(pts) != 9 {
		t.Fatalf("mark: %d %v", c, pts)
	}
	wait()
	// 2. Scan.
	if c := call("POST", "/api/scan", nil, nil); c != 200 {
		t.Fatal("scan")
	}
	if d := os.Getenv("STUDIO_DEBUG"); d != "" {
		os.WriteFile(d+"/scan.jpg", a.scan.JPEG, 0o644)
	}
	// 3. Click each dot: the true picture point from the simulator, moved 3 px, then refined.
	var pairs []Pair
	for i, p := range pts {
		resp, err := http.Get(fmt.Sprintf("%s/camera/project?x=%g&y=%g&full=1", hs.URL, p.X, p.Y))
		if err != nil {
			t.Fatal(err)
		}
		var pr struct{ U, V float64 }
		json.NewDecoder(resp.Body).Decode(&pr)
		resp.Body.Close()
		var q struct{ PX, PY float64 }
		call("POST", "/api/calib/refine", map[string]float64{"px": pr.U + 3, "py": pr.V - 2}, &q)
		if math.Hypot(q.PX-pr.U, q.PY-pr.V) > 1.5 {
			t.Errorf("point %d: refine went to %.1f,%.1f, the dot is at %.1f,%.1f", i, q.PX, q.PY, pr.U, pr.V)
		}
		pairs = append(pairs, Pair{PX: q.PX, PY: q.PY, X: p.X, Y: p.Y})
	}
	// 4. Solve with the lens.
	var c Calibration
	if code := call("POST", "/api/calib/solve", map[string]any{"pairs": pairs, "fit_k1": true}, &c); code != 200 {
		t.Fatal("solve")
	}
	t.Logf("calibration: rms %.3f mm, k1 %.3f", c.RMS, c.Lens.K1)
	if c.RMS > 0.4 {
		t.Errorf("rms %.2f mm is too large", c.RMS)
	}
	// Check a point that is not a calibration point.
	resp, _ := http.Get(hs.URL + "/camera/project?x=150&y=100&full=1")
	var pr struct{ U, V float64 }
	json.NewDecoder(resp.Body).Decode(&pr)
	resp.Body.Close()
	got := a.calib.ToMachine(geom.Pt{X: pr.U, Y: pr.V}, a.scan.Image2Size())
	if math.Hypot(got.X-150, got.Y-100) > 0.6 {
		t.Errorf("check point: got %.2f,%.2f, want 150,100", got.X, got.Y)
	}
	if _, err := a.Bed(); err != nil {
		t.Fatal(err)
	}
	// 5. Plot a square of 20 mm at 100,200 and find its ink.
	var it plan.Item
	call("POST", "/api/svg", `<svg width="20mm" height="20mm" viewBox="0 0 20 20"><rect x="0" y="0" width="20" height="20"/></svg>`, &it)
	it.X, it.Y, it.Scale = 100, 200, 1
	m.ClearPaper()
	if code := call("POST", "/api/plot", map[string]any{"items": []plan.Item{it}, "feed": 3000}, nil); code != 200 {
		t.Fatal("plot")
	}
	wait()
	segs, _, _ := m.Ink(0)
	if len(segs) == 0 {
		t.Fatal("no ink")
	}
	for _, s := range segs {
		for _, v := range [][2]float32{{s[0], s[1]}, {s[2], s[3]}} {
			if math.Abs(float64(v[0])-100) > 10.3 || math.Abs(float64(v[1])-200) > 10.3 {
				t.Fatalf("ink at %v is outside the square", v)
			}
		}
	}
}
