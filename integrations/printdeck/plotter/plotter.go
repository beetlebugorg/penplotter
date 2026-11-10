// Package plotter adds the pen plotter to Printdeck as an accessory machine.
//
// Printdeck runs one 3D printer for each deck. The plotter does not replace that printer. The
// deck mounts the whole plotstudio server (the bed scan, the layout, the pens, the plot) at
// /plotter/ behind its own login, and gives it the main camera of the deck. The deck screens can
// show a small status tile from Summary.
//
// This package has no import of Printdeck. Printdeck passes its camera as a Snapshot function, so
// the package builds and tests in the penplotter repository. docs/printdeck.md has the design,
// and printdeck.patch the code for Printdeck.
package plotter

import (
	"bytes"
	"context"
	"errors"
	"image"
	_ "image/jpeg"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/beetlebugorg/penplotter/studio/app"
	"github.com/beetlebugorg/penplotter/studio/camera"
	"github.com/beetlebugorg/penplotter/studio/netlink"
	studioweb "github.com/beetlebugorg/penplotter/studio/web"
)

// Snapshot returns a JPEG picture of the camera now. In Printdeck it wraps
// camera.Source.Snapshot and Frame.JPEG.
type Snapshot func(ctx context.Context) ([]byte, error)

// Config sets up the plotter in the deck.
type Config struct {
	// Addr is the plotter: "penplotter.local" (the default), an IP address, or "host:port".
	Addr string
	// DataDir keeps the calibration of the camera, the pen table and the signature library.
	DataDir string
	// TravelX and TravelY are the travel of the plotter in mm (default 245 x 390).
	TravelX, TravelY float64
	// Snapshot is the camera that sees the plotter bed, or nil for no camera.
	Snapshot Snapshot
	// CameraName names the camera in the calibration. A new camera needs a new calibration.
	CameraName string
}

// Plotter is the plotter accessory of a deck.
type Plotter struct {
	cfg Config
	app *app.App
	cli *netlink.Client

	mu     sync.Mutex
	last   Summary
	lastAt time.Time
}

// New makes the accessory. It connects to the plotter in the background, and keeps trying.
func New(cfg Config) *Plotter {
	if cfg.Addr == "" {
		cfg.Addr = netlink.DefaultHost
	}
	if cfg.TravelX <= 0 {
		cfg.TravelX = 245
	}
	if cfg.TravelY <= 0 {
		cfg.TravelY = 390
	}
	if cfg.CameraName == "" {
		cfg.CameraName = "printdeck"
	}
	ac := app.Config{
		Port: cfg.Addr, TravelX: cfg.TravelX, TravelY: cfg.TravelY, DataDir: cfg.DataDir,
		ParkScan: true, ParkX: 0, ScanTwice: true, FitLens: true, Web: studioweb.FS(),
	}
	if cfg.Snapshot != nil {
		ac.Source = &snapSource{snap: cfg.Snapshot, name: cfg.CameraName}
	}
	p := &Plotter{cfg: cfg, app: app.New(ac)}
	if t, err := netlink.ParseTarget(cfg.Addr); err == nil {
		p.cli = netlink.NewClient(t.HTTPBase)
	}
	return p
}

// Handler serves plotstudio. Mount it with a prefix that ends in a slash:
//
//	mux.Handle("/plotter/", http.StripPrefix("/plotter", p.Handler()))
func (p *Plotter) Handler() http.Handler { return p.app.Handler() }

// Close stops the link and the camera adapter.
func (p *Plotter) Close() { p.app.Close() }

// Summary is the plotter for a status tile on the deck screens.
type Summary struct {
	Online    bool    `json:"online"`
	State     string  `json:"state"` // idle, busy, paused, pen_change, error, offline
	Job       string  `json:"job"`
	Percent   float64 `json:"percent"`
	Tool      int     `json:"tool"`
	PenChange bool    `json:"pen_change"`
	Error     string  `json:"error,omitempty"`
}

// Summary reads the plotter status (GET /api/status of the plotter). It keeps the last answer
// for 2 s, so a screen can call it on each frame.
func (p *Plotter) Summary(ctx context.Context) Summary {
	p.mu.Lock()
	if time.Since(p.lastAt) < 2*time.Second {
		s := p.last
		p.mu.Unlock()
		return s
	}
	p.mu.Unlock()
	s := Summary{State: "offline"}
	if p.cli != nil {
		c, cancel := context.WithTimeout(ctx, 2*time.Second)
		st, err := p.cli.Status(c)
		cancel()
		if err == nil {
			s = Summary{Online: true, State: st.State, Tool: st.Tool, Error: st.Error,
				PenChange: st.State == "pen_change"}
			if st.Job != nil {
				s.Job = st.Job.Name
				if st.Job.Total > 0 {
					s.Percent = 100 * float64(st.Job.Line) / float64(st.Job.Total)
				}
			}
			if st.Progress > 0 {
				// A job streamed over TCP has no total on the plotter: it sends M73 progress.
				s.Percent = st.Progress
			}
		} else {
			s.Error = err.Error()
		}
	}
	p.mu.Lock()
	p.last, p.lastAt = s, time.Now()
	p.mu.Unlock()
	return s
}

// Discover finds plotters on the local network (mDNS, about 2 s).
func Discover(ctx context.Context) ([]netlink.Device, error) { return netlink.Discover(ctx) }

// snapSource is a plotstudio camera made from a Snapshot function.
type snapSource struct {
	snap Snapshot
	name string
}

func (s *snapSource) Name() string { return s.name }
func (s *snapSource) Close() error { return nil }

// Grab takes a picture. The deck camera has one size, so the live view and the scan get the same
// picture. A scan takes two pictures and keeps the second: the first can be a frame from before
// the gantry stopped.
func (s *snapSource) Grab(ctx context.Context, m camera.Mode) (*camera.Frame, error) {
	n := 1
	if m == camera.Scan {
		n = 2
	}
	var b []byte
	var err error
	for i := 0; i < n; i++ {
		if b, err = s.snap(ctx); err != nil {
			return nil, err
		}
		if i+1 < n {
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(400 * time.Millisecond):
			}
		}
	}
	if len(b) < 2 || !bytes.HasPrefix(b, []byte{0xFF, 0xD8}) {
		return nil, errors.New("plotter: the deck camera gave no JPEG picture")
	}
	cfg, _, err := image.DecodeConfig(bytes.NewReader(b))
	if err != nil {
		return nil, err
	}
	return &camera.Frame{JPEG: b, W: cfg.Width, H: cfg.Height}, nil
}

// PrefixOK reports that a mount prefix works with the relative links of the UI: it must end
// with a slash.
func PrefixOK(prefix string) bool { return strings.HasSuffix(prefix, "/") }
