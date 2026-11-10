package app

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/beetlebugorg/penplotter/studio/netlink"
	"github.com/beetlebugorg/penplotter/studio/plan"
	"github.com/beetlebugorg/penplotter/studio/svg"
)

// loadPens reads the pen table. A missing or bad file gives the default table.
func loadPens(path string) []plan.Pen {
	b, err := os.ReadFile(path)
	if err != nil {
		return plan.DefaultPens()
	}
	var p []plan.Pen
	if err := json.Unmarshal(b, &p); err != nil || checkPens(p) != nil {
		return plan.DefaultPens()
	}
	return p
}

func (a *App) pensPath() string { return filepath.Join(a.cfg.DataDir, "pens.json") }

func (a *App) savePens(p []plan.Pen) error {
	a.mu.Lock()
	closed := a.closed
	a.mu.Unlock()
	if closed {
		return nil // the app stops: no new files in its folder
	}
	if err := os.MkdirAll(a.cfg.DataDir, 0o755); err != nil {
		return err
	}
	b, _ := json.MarshalIndent(p, "", " ")
	return os.WriteFile(a.pensPath(), b, 0o644)
}

// checkPens makes sure that each pen has a T in 0..15 (each T once) and a #rrggbb colour.
func checkPens(p []plan.Pen) error {
	if len(p) == 0 || len(p) > plan.MaxPens {
		return fmt.Errorf("pens: the table has %d pens; it needs 1 to %d", len(p), plan.MaxPens)
	}
	seen := map[int]bool{}
	for i := range p {
		if p[i].T < 0 || p[i].T >= plan.MaxPens || seen[p[i].T] {
			return fmt.Errorf("pens: T%d is out of range or twice in the table", p[i].T)
		}
		seen[p[i].T] = true
		c := svg.ParseColor(p[i].Color)
		if c == "" {
			return fmt.Errorf("pens: T%d: %q is not a colour", p[i].T, p[i].Color)
		}
		p[i].Color = c
		p[i].Name = strings.TrimSpace(p[i].Name)
		if p[i].Width < 0 || p[i].Width > 10 {
			return fmt.Errorf("pens: T%d: width %g mm is not in 0..10", p[i].T, p[i].Width)
		}
	}
	return nil
}

func toNet(p []plan.Pen) []netlink.Pen {
	out := make([]netlink.Pen, len(p))
	for i, x := range p {
		out[i] = netlink.Pen{T: x.T, Name: x.Name, Color: x.Color}
	}
	return out
}

// fromNet converts the table of a network plotter. The plotter keeps only T, name and colour.
// The other fields come from old, the pen with the same T in the table of plotstudio.
func fromNet(p []netlink.Pen, old []plan.Pen) []plan.Pen {
	byT := map[int]plan.Pen{}
	for _, x := range old {
		byT[x.T] = x
	}
	out := make([]plan.Pen, len(p))
	for i, x := range p {
		o := byT[x.T]
		o.T, o.Name, o.Color = x.T, x.Name, x.Color
		out[i] = o
	}
	return out
}

// syncPensFromDevice reads the pen table of a network plotter after a connect. The plotter
// keeps the table of the pens in its holder, so its table wins. An empty table on the plotter
// gets the table of plotstudio.
func (a *App) syncPensFromDevice() {
	a.mu.Lock()
	dev := a.dev
	a.mu.Unlock()
	if dev == nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	p, err := dev.Pens(ctx)
	if err != nil {
		a.logf("err", "read the pen table of the plotter: %v", err)
		return
	}
	a.mu.Lock()
	pp := fromNet(p, a.pens)
	a.mu.Unlock()
	if len(pp) == 0 || checkPens(pp) != nil {
		a.mu.Lock()
		mine := append([]plan.Pen(nil), a.pens...)
		a.mu.Unlock()
		if err := dev.SetPens(ctx, toNet(mine)); err != nil {
			a.logf("err", "write the pen table to the plotter: %v", err)
		}
		return
	}
	a.mu.Lock()
	a.pens = pp
	a.mu.Unlock()
	a.savePens(pp)
	a.logf("info", "pen table: %d pens from the plotter", len(pp))
}

func (a *App) hPens(w http.ResponseWriter, r *http.Request) {
	if r.Method == "PUT" {
		var p []plan.Pen
		if err := readJSON(r, &p); err != nil {
			fail(w, 400, err)
			return
		}
		if err := checkPens(p); err != nil {
			fail(w, 400, err)
			return
		}
		if err := a.savePens(p); err != nil {
			fail(w, 500, err)
			return
		}
		a.mu.Lock()
		a.pens = p
		dev := a.dev
		a.mu.Unlock()
		if dev != nil {
			ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
			err := dev.SetPens(ctx, toNet(p))
			cancel()
			if err != nil {
				a.logf("err", "write the pen table to the plotter: %v", err)
			}
		}
	}
	a.mu.Lock()
	p := append([]plan.Pen(nil), a.pens...)
	a.mu.Unlock()
	writeJSON(w, p)
}

// waitingPen returns the pen that the job waits for, or -1. The job waits at an M6 line until
// the person loads the pen and presses the knob.
func waitingPen(lines []string, done int, state string) int {
	if state != "running" || done >= len(lines) || !strings.HasPrefix(strings.ToUpper(lines[done]), "M6") {
		return -1
	}
	for i := done - 1; i >= 0; i-- {
		l := strings.ToUpper(lines[i])
		if strings.HasPrefix(l, "T") {
			var t int
			if _, err := fmt.Sscanf(l, "T%d", &t); err == nil {
				return t
			}
		}
	}
	return 0
}
