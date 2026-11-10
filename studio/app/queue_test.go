package app

import (
	"context"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
	"time"

	"github.com/beetlebugorg/penplotter/studio/camera"
	"github.com/beetlebugorg/penplotter/studio/plan"
)

func TestQueue(t *testing.T) {
	fp := newFakePlotter(t)
	a := New(Config{Port: fp.target(), TravelX: 250, TravelY: 395, DataDir: t.TempDir()})
	defer a.Close()
	h := a.Handler()
	two := plan.Item{Name: "first", W: 10, H: 10, X: 50, Y: 50, Scale: 1,
		Lines:  [][]plan.Pt{{{X: 0, Y: 0}, {X: 10, Y: 0}}, {{X: 0, Y: 10}, {X: 10, Y: 10}}},
		Colors: []string{"#000000", "#ff0000"}, Layers: []string{"", ""}}
	call(t, h, "POST", "/api/plot", map[string]any{"items": []plan.Item{two}})
	waitFor(t, "the job waits at M6", 3*time.Second, func() bool {
		j, _ := call(t, h, "GET", "/api/status", nil)["job"].(map[string]any)
		return j != nil && j["pen_change"] != nil
	})
	second := two
	second.Name = "second"
	r := call(t, h, "POST", "/api/plot", map[string]any{"items": []plan.Item{second}, "queue": true})
	id := int(r["queued"].(float64))
	q := call(t, h, "GET", "/api/status", nil)["queue"].([]any)
	if len(q) != 1 || q[0].(map[string]any)["name"] != "second" {
		t.Fatalf("queue: %v", q)
	}
	// No start while a job runs.
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest("POST", "/api/queue/"+itoa(id)+"/start", nil))
	if rec.Code != 409 {
		t.Fatalf("start while busy: %d", rec.Code)
	}
	fp.release <- struct{}{}
	fp.release <- struct{}{}
	waitFor(t, "the end of the first job", 3*time.Second, func() bool {
		j := call(t, h, "GET", "/api/status", nil)["job"].(map[string]any)
		return j["state"] == "done"
	})
	call(t, h, "POST", "/api/queue/"+itoa(id)+"/start", nil)
	waitFor(t, "the second job", 3*time.Second, func() bool {
		j := call(t, h, "GET", "/api/status", nil)["job"].(map[string]any)
		return j["name"] == "second"
	})
	if q := call(t, h, "GET", "/api/status", nil)["queue"].([]any); len(q) != 0 {
		t.Fatalf("the queue must be empty: %v", q)
	}
	fp.release <- struct{}{}
	fp.release <- struct{}{}
}

func itoa(n int) string { return strconv.Itoa(n) }

type namedCam struct{ name string }

func (c namedCam) Name() string { return c.name }
func (c namedCam) Close() error { return nil }
func (c namedCam) Grab(context.Context, camera.Mode) (*camera.Frame, error) {
	return nil, context.DeadlineExceeded
}

func TestCalibrationPerCamera(t *testing.T) {
	dir := t.TempDir()
	a := New(Config{Source: namedCam{"Arducam B0561 /dev/video0"}, DataDir: dir})
	defer a.Close()
	if got := filepath.Base(a.calibPath()); got != "calibration-Arducam-B0561-dev-video0.json" {
		t.Fatalf("path: %s", got)
	}
}
