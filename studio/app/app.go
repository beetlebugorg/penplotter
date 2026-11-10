// Package app is the plotstudio server: the camera, the calibration, the bed view, the layout
// of drawings, and the plot. It serves the web UI and a JSON API.
package app

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/jpeg"
	"io"
	"io/fs"
	"math"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/beetlebugorg/penplotter/studio/camera"
	"github.com/beetlebugorg/penplotter/studio/geom"
	"github.com/beetlebugorg/penplotter/studio/netlink"
	"github.com/beetlebugorg/penplotter/studio/plan"
	"github.com/beetlebugorg/penplotter/studio/serial"
	"github.com/beetlebugorg/penplotter/studio/svg"
)

// Config sets up the app.
type Config struct {
	Port   string // the plotter: a serial device (/dev/ttyACM0) or a network address (penplotter.local, 192.168.1.50, host:23)
	Camera string // the camera: /dev/video0, a number, http://..., or file:...
	// Source is an open camera. It wins over Camera. A host program (Printdeck) gives its own
	// camera here.
	Source    camera.Source
	TravelX   float64 // mm
	TravelY   float64 // mm
	PxPerMM   float64 // the resolution of the bed view (default 2)
	Margin    float64 // the bed view shows this much around the travel (default 15 mm)
	DataDir   string  // calibration.json and library/ (default ~/.config/plotstudio)
	ParkScan  bool    // park the gantry at the back before a scan
	ParkX     float64 // the X of the park position (default 5 mm: clear of the X endstop at X 0)
	Feed      float64 // the draw speed in mm/min (default 3000)
	FitLens   bool    // fit the lens distortion when there are 6 or more points
	ScanTwice bool    // scan with the gantry at the back and again at the front, and join the pictures
	Split     float64 // the join row of the two pictures, as a part of the height (default 0.5)
	Web       fs.FS   // the UI files
}

// App is the server state.
type App struct {
	cfg Config

	mu      sync.Mutex
	cam     camera.Source
	port    *serial.Port
	link    string          // "usb" or "wifi": the link of port
	dev     *netlink.Client // the HTTP API of a network plotter, or nil
	devSt   netlink.Status  // the last device status (a network plotter only)
	pens    []plan.Pen      // the pen table, T0 to T15
	queue   []queuedJob     // jobs that wait; each starts on a press of Start
	qid     int
	closed  bool
	job     *serial.Job
	jobName string
	calib   *Calibration
	scan    *camera.Frame
	scanAt  time.Time
	bed     []byte // JPEG of the bed view
	bedVer  int
	logs    []logLine
	logN    int
}

type logLine struct {
	N    int    `json:"n"`
	Dir  string `json:"dir"`
	Text string `json:"text"`
}

// New makes the app. It opens the camera and the port if they are given. A failure is logged,
// not fatal: the UI shows it.
func New(cfg Config) *App {
	if cfg.PxPerMM <= 0 {
		cfg.PxPerMM = 2
	}
	if cfg.Margin <= 0 {
		cfg.Margin = 15
	}
	if cfg.Feed <= 0 {
		cfg.Feed = 3000
	}
	if cfg.ParkX < 1 {
		// At X 0 the carriage presses the X endstop: the firmware reads a hard limit there.
		cfg.ParkX = parkMargin
	}
	if cfg.DataDir == "" {
		d, _ := os.UserConfigDir()
		cfg.DataDir = filepath.Join(d, "plotstudio")
	}
	a := &App{cfg: cfg, pens: loadPens(filepath.Join(cfg.DataDir, "pens.json"))}
	if cfg.Source != nil {
		a.cam = cfg.Source
	} else if cfg.Camera != "" {
		if c, err := camera.Open(cfg.Camera); err == nil {
			a.cam = c
		} else {
			a.logf("err", "camera: %v", err)
		}
	}
	a.loadCalib()
	if a.cam != nil {
		a.restoreFocus()
	}
	if cfg.Port != "" {
		if err := a.connect(cfg.Port); err != nil {
			a.logf("err", "%v", err)
		}
	}
	go a.pollDevice()
	return a
}

// calibPath is the calibration file of the camera now. Each camera has its own file, so a
// change of camera does not use a wrong calibration.
func (a *App) calibPath() string {
	name := "calibration.json"
	if a.cam != nil {
		if s := strings.Trim(safeName.ReplaceAllString(a.cam.Name(), "-"), "-."); s != "" {
			name = "calibration-" + s + ".json"
		}
	}
	return filepath.Join(a.cfg.DataDir, name)
}

// loadCalib reads the calibration of the camera now. A calibration.json of an older version
// counts for a camera with no file of its own, when its camera name matches or is empty.
func (a *App) loadCalib() {
	a.calib = nil
	if c, err := Load(a.calibPath()); err == nil {
		a.calib = c
		return
	}
	if c, err := Load(filepath.Join(a.cfg.DataDir, "calibration.json")); err == nil {
		if a.cam == nil || c.Camera == "" || c.Camera == a.cam.Name() {
			a.calib = c
		}
	}
}

func (a *App) logf(dir, f string, args ...any) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.addLog(dir, fmt.Sprintf(f, args...))
}

func (a *App) addLog(dir, text string) {
	a.logN++
	a.logs = append(a.logs, logLine{N: a.logN, Dir: dir, Text: text})
	if len(a.logs) > 300 {
		a.logs = a.logs[len(a.logs)-300:]
	}
}

// connect opens the plotter: a serial device, or a network address (the G-code link on TCP
// port 23 and the HTTP API on port 80). It replaces the present link. A watcher reconnects
// when the link drops.
func (a *App) connect(target string) error {
	target = strings.TrimSpace(target)
	if target == "" {
		return errors.New("no plotter address")
	}
	var rw io.ReadWriteCloser
	link := "usb"
	var dev *netlink.Client
	if netlink.IsNetwork(target) {
		t, err := netlink.ParseTarget(target)
		if err != nil {
			return err
		}
		ctx, cancel := context.WithTimeout(context.Background(), 6*time.Second)
		defer cancel()
		c, err := netlink.Dial(ctx, t)
		if err != nil {
			return err
		}
		rw = c
		if t.Raw {
			// The serial line of the simulated stock board: no HTTP API. It acts as USB.
			link = "usb"
		} else {
			link = "wifi"
			base := t.HTTPBase
			if !strings.Contains(target, "http://") {
				// The system resolver may not know .local names: use the address of the link.
				ip, _, _ := net.SplitHostPort(c.RemoteAddr().String())
				_, hp, _ := net.SplitHostPort(strings.TrimPrefix(t.HTTPBase, "http://"))
				base = "http://" + net.JoinHostPort(ip, hp)
			}
			dev = netlink.NewClient(base)
		}
	} else {
		f, err := serial.Open(target)
		if err != nil {
			return err
		}
		rw = f
	}
	p := serial.New(rw, func(dir, text string) {
		a.mu.Lock()
		a.addLog(dir, text)
		a.mu.Unlock()
	})
	a.mu.Lock()
	if a.port != nil {
		a.port.Close()
	}
	a.port, a.link, a.dev = p, link, dev
	a.devSt = netlink.Status{}
	a.cfg.Port = target
	a.mu.Unlock()
	a.logf("info", "connected to %s (%s)", target, link)
	go a.watch(p, target)
	if dev != nil {
		go a.syncPensFromDevice()
	}
	return nil
}

// watch waits for the end of a link. Then it tries to open the same plotter again every 3 s,
// until that works, until another plotter is chosen, or until the app closes.
func (a *App) watch(p *serial.Port, target string) {
	<-p.Done()
	a.mu.Lock()
	if a.port != p || a.closed {
		a.mu.Unlock()
		return
	}
	a.port = nil
	a.mu.Unlock()
	a.logf("err", "lost the plotter (%s): reconnecting", target)
	for {
		time.Sleep(3 * time.Second)
		a.mu.Lock()
		stop := a.closed || a.port != nil || a.cfg.Port != target
		a.mu.Unlock()
		if stop {
			return
		}
		a.mu.Lock()
		closed := a.closed
		a.mu.Unlock()
		if closed {
			return
		}
		if err := a.connect(target); err == nil {
			return
		}
	}
}

// pollDevice reads the status of a network plotter every 2 s.
func (a *App) pollDevice() {
	for {
		time.Sleep(2 * time.Second)
		a.mu.Lock()
		dev, closed := a.dev, a.closed
		a.mu.Unlock()
		if closed {
			return
		}
		if dev == nil {
			continue
		}
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		st, err := dev.Status(ctx)
		cancel()
		if err != nil {
			st.Error = err.Error()
		}
		a.mu.Lock()
		if a.dev == dev {
			a.devSt = st
		}
		a.mu.Unlock()
	}
}

func (a *App) restoreFocus() {
	ctl, ok := a.cam.(camera.Controller)
	if !ok || a.calib == nil || a.calib.Focus == nil {
		return
	}
	if err := ctl.SetFocus(false, *a.calib.Focus); err == nil {
		a.logf("info", "camera focus fixed at %d (from the calibration)", *a.calib.Focus)
	}
}

// busy reports a running job.
func (a *App) busy() bool {
	if a.job == nil {
		return false
	}
	s := a.job.Status().State
	return s == "running" || s == "paused"
}

// commands sends lines one at a time (not as a job). It fails while a job runs.
func (a *App) commands(ctx context.Context, lines ...string) ([]string, error) {
	a.mu.Lock()
	p := a.port
	busy := a.busy()
	a.mu.Unlock()
	if p == nil {
		return nil, errors.New("no plotter: connect it (USB or Wi-Fi)")
	}
	if busy {
		return nil, errors.New("a job runs")
	}
	var out []string
	for _, l := range lines {
		r, err := p.Command(ctx, l)
		out = append(out, r...)
		if err != nil {
			return out, err
		}
	}
	return out, nil
}

func (a *App) startJob(name, program string) (*serial.Job, error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.port == nil {
		return nil, errors.New("no plotter: connect it (USB or Wi-Fi)")
	}
	if a.busy() {
		return nil, errors.New("a job runs")
	}
	a.job = a.port.Stream(serial.Program(program))
	a.jobName = name
	return a.job, nil
}

// grab takes a picture. A scan parks the gantry first (if set), and locks the exposure.
func (a *App) grab(ctx context.Context, m camera.Mode) (*camera.Frame, error) {
	a.mu.Lock()
	cam := a.cam
	a.mu.Unlock()
	if cam == nil {
		return nil, errors.New("no camera")
	}
	if m == camera.Scan {
		if ctl, ok := cam.(camera.Controller); ok {
			ctl.Lock(true)
			defer ctl.Lock(false)
		}
	}
	return cam.Grab(ctx, m)
}

// park moves the gantry out of the picture (pen up) and reports that it moved.
func (a *App) park(ctx context.Context, y float64) bool {
	if !a.cfg.ParkScan {
		return false
	}
	a.mu.Lock()
	ok := a.port != nil && !a.busy()
	a.mu.Unlock()
	if !ok {
		return false
	}
	if _, err := a.commands(ctx, "M5", fmt.Sprintf("G0 X%g Y%g", a.cfg.ParkX, y), "M400"); err != nil {
		a.logf("err", "park: %v", err)
		return false
	}
	return true
}

// Scan parks, grabs a scan picture, and makes the bed view.
//
// The camera stands behind the frame. The gantry hides a band of the table in front of it. So
// the scan takes one picture with the gantry at the back and, with ScanTwice, one more with the
// gantry at the front. The top rows of the picture (the front of the table) come from the first
// picture, the bottom rows (the back of the table) from the second.
func (a *App) Scan(ctx context.Context) error {
	parked := a.park(ctx, a.cfg.TravelY)
	f, err := a.grab(ctx, camera.Scan)
	if err != nil {
		return err
	}
	// The front park stays 5 mm from the Y endstops (Y 0): the firmware reads a pressed switch
	// as a hard limit.
	if parked && a.cfg.ScanTwice && a.park(ctx, parkMargin) {
		g, err := a.grab(ctx, camera.Scan)
		if err != nil {
			return err
		}
		split := a.cfg.Split
		if split <= 0 || split >= 1 {
			split = 0.5
		}
		if f, err = join(f, g, split); err != nil {
			return err
		}
		a.park(ctx, a.cfg.TravelY)
	}
	a.mu.Lock()
	a.scan, a.scanAt = f, time.Now()
	a.mu.Unlock()
	return a.renderBed()
}

// parkMargin keeps a park position this far from the home switches (X 0, Y 0), in mm.
const parkMargin = 5.0

// join takes the rows above split·height from top and the rows below it from bottom.
func join(top, bottom *camera.Frame, split float64) (*camera.Frame, error) {
	a, err := top.Image()
	if err != nil {
		return nil, err
	}
	b, err := bottom.Image()
	if err != nil {
		return nil, err
	}
	r := a.Bounds()
	if b.Bounds() != r {
		return nil, errors.New("scan: the two pictures have different sizes")
	}
	out := image.NewRGBA(r)
	cut := r.Min.Y + int(split*float64(r.Dy()))
	draw.Draw(out, image.Rect(r.Min.X, r.Min.Y, r.Max.X, cut), a, r.Min, draw.Src)
	draw.Draw(out, image.Rect(r.Min.X, cut, r.Max.X, r.Max.Y), b, image.Pt(r.Min.X, cut), draw.Src)
	return camera.FromImage(out)
}

// bedGeom is the bed view: machine x = X0 + (px+0.5)/PxPerMM, machine y = Y1 - (py+0.5)/PxPerMM.
// The back of the table is at the top, as a person at the front sees it.
type bedGeom struct {
	PxPerMM float64    `json:"px_per_mm"`
	X0      float64    `json:"x0"`
	Y1      float64    `json:"y1"`
	W       int        `json:"w"`
	H       int        `json:"h"`
	Travel  [2]float64 `json:"travel"`
	Ver     int        `json:"ver"`
	Has     bool       `json:"has_image"`
}

func (a *App) bedGeom() bedGeom {
	m := a.cfg.Margin
	return bedGeom{
		PxPerMM: a.cfg.PxPerMM, X0: -m, Y1: a.cfg.TravelY + m,
		W:      int(math.Round((a.cfg.TravelX + 2*m) * a.cfg.PxPerMM)),
		H:      int(math.Round((a.cfg.TravelY + 2*m) * a.cfg.PxPerMM)),
		Travel: [2]float64{a.cfg.TravelX, a.cfg.TravelY},
	}
}

func (a *App) renderBed() error {
	a.mu.Lock()
	f, c := a.scan, a.calib
	a.mu.Unlock()
	if f == nil || c == nil {
		return nil
	}
	img, err := f.Image()
	if err != nil {
		return err
	}
	g := a.bedGeom()
	sz := img.Bounds().Size()
	out := geom.WarpFunc(img, func(p geom.Pt) geom.Pt {
		m := geom.Pt{X: g.X0 + p.X/g.PxPerMM, Y: g.Y1 - p.Y/g.PxPerMM}
		q := c.ToPicture(m, sz)
		return geom.Pt{X: q.X + float64(img.Bounds().Min.X), Y: q.Y + float64(img.Bounds().Min.Y)}
	}, g.W, g.H, color.RGBA{40, 42, 46, 255})
	var b bytes.Buffer
	if err := jpeg.Encode(&b, out, &jpeg.Options{Quality: 88}); err != nil {
		return err
	}
	a.mu.Lock()
	a.bed = b.Bytes()
	a.bedVer++
	a.mu.Unlock()
	return nil
}

// Handler returns the HTTP handler.
func (a *App) Handler() http.Handler {
	mux := http.NewServeMux()
	if a.cfg.Web != nil {
		mux.Handle("/", http.FileServer(http.FS(a.cfg.Web)))
	}
	mux.HandleFunc("GET /api/status", a.hStatus)
	mux.HandleFunc("GET /api/log", a.hLog)
	mux.HandleFunc("GET /api/cameras", func(w http.ResponseWriter, r *http.Request) { writeJSON(w, camera.List()) })
	mux.HandleFunc("POST /api/camera", a.hSetCamera)
	mux.HandleFunc("GET /api/camera.jpg", a.hLive)
	mux.HandleFunc("GET /api/focus", a.hFocus)
	mux.HandleFunc("POST /api/focus", a.hFocus)
	mux.HandleFunc("POST /api/port", a.hPort)
	mux.HandleFunc("GET /api/discover", a.hDiscover)
	mux.HandleFunc("GET /api/devices", a.hDevices)
	mux.HandleFunc("POST /api/scan", a.hScan)
	mux.HandleFunc("GET /api/scan.jpg", a.hScanJPG)
	mux.HandleFunc("GET /api/bed.jpg", a.hBedJPG)
	mux.HandleFunc("GET /api/bed", func(w http.ResponseWriter, r *http.Request) {
		a.mu.Lock()
		g := a.bedGeom()
		g.Ver, g.Has = a.bedVer, a.bed != nil
		a.mu.Unlock()
		writeJSON(w, g)
	})
	mux.HandleFunc("GET /api/calib", a.hCalib)
	mux.HandleFunc("POST /api/calib/points", a.hCalibPoints)
	mux.HandleFunc("POST /api/calib/mark", a.hCalibMark)
	mux.HandleFunc("POST /api/calib/goto", a.hCalibGoto)
	mux.HandleFunc("POST /api/calib/refine", a.hCalibRefine)
	mux.HandleFunc("POST /api/calib/solve", a.hCalibSolve)
	mux.HandleFunc("POST /api/svg", a.hSVG)
	mux.HandleFunc("POST /api/gcode", a.hGCode)
	mux.HandleFunc("POST /api/plot", a.hPlot)
	mux.HandleFunc("POST /api/job/{op}", a.hJob)
	mux.HandleFunc("POST /api/queue/{id}/start", a.hQueueStart)
	mux.HandleFunc("DELETE /api/queue/{id}", a.hQueueDelete)
	mux.HandleFunc("POST /api/cmd", a.hCmd)
	mux.HandleFunc("GET /api/pens", a.hPens)
	mux.HandleFunc("PUT /api/pens", a.hPens)
	mux.HandleFunc("GET /api/library", a.hLibrary)
	mux.HandleFunc("POST /api/library", a.hLibrary)
	mux.HandleFunc("GET /api/library/{name}", a.hLibraryGet)
	return mux
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	json.NewEncoder(w).Encode(v)
}

func fail(w http.ResponseWriter, code int, err error) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
}

func readJSON(r *http.Request, v any) error {
	return json.NewDecoder(io.LimitReader(r.Body, 64<<20)).Decode(v)
}

func (a *App) hStatus(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	defer a.mu.Unlock()
	st := map[string]any{
		"port":       a.cfg.Port,
		"connected":  a.port != nil,
		"link":       a.link,
		"travel":     []float64{a.cfg.TravelX, a.cfg.TravelY},
		"camera":     "",
		"scan":       nil,
		"calib":      nil,
		"bed_ver":    a.bedVer,
		"park_scan":  a.cfg.ParkScan,
		"scan_twice": a.cfg.ScanTwice,
		"log_n":      a.logN,
	}
	if a.cam != nil {
		st["camera"] = a.cam.Name()
		_, st["camera_controls"] = a.cam.(camera.Controller)
	}
	if a.scan != nil {
		st["scan"] = map[string]any{"w": a.scan.W, "h": a.scan.H, "time": a.scanAt}
	}
	if a.calib != nil {
		st["calib"] = map[string]any{"rms_mm": a.calib.RMS, "k1": a.calib.Lens.K1, "points": len(a.calib.Pairs),
			"size": a.calib.Size, "time": a.calib.Time, "focus": a.calib.Focus}
	}
	q := make([]queuedJob, len(a.queue))
	copy(q, a.queue)
	st["queue"] = q
	st["draw_area"] = []float64{0, a.cfg.TravelY}
	if a.dev != nil {
		st["device"] = a.devSt
		st["device_online"] = a.devSt.Online
	}
	if a.job != nil {
		js := a.job.Status()
		job := map[string]any{"name": a.jobName, "state": js.State, "done": js.Done, "total": js.Total,
			"error": js.Error, "seconds": js.Seconds}
		if t := waitingPen(a.job.Lines, js.Done, js.State); t >= 0 {
			job["pen_change"] = t
		}
		st["job"] = job
	}
	writeJSON(w, st)
}

func (a *App) hLog(w http.ResponseWriter, r *http.Request) {
	var after int
	fmt.Sscanf(r.URL.Query().Get("after"), "%d", &after)
	a.mu.Lock()
	var out []logLine
	for _, l := range a.logs {
		if l.N > after {
			out = append(out, l)
		}
	}
	a.mu.Unlock()
	writeJSON(w, out)
}

func (a *App) hSetCamera(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Spec string `json:"spec"`
	}
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	c, err := camera.Open(req.Spec)
	if err != nil {
		fail(w, 400, err)
		return
	}
	a.mu.Lock()
	if a.cam != nil {
		a.cam.Close()
	}
	a.cam = c
	a.cfg.Camera = req.Spec
	a.loadCalib()
	a.bed, a.scan = nil, nil
	a.bedVer++
	a.mu.Unlock()
	a.restoreFocus()
	writeJSON(w, map[string]string{"camera": c.Name()})
}

func (a *App) hLive(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()
	f, err := a.grab(ctx, camera.Live)
	if err != nil {
		fail(w, 503, err)
		return
	}
	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "no-store")
	w.Write(f.JPEG)
}

func (a *App) hFocus(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	ctl, ok := a.cam.(camera.Controller)
	a.mu.Unlock()
	if !ok {
		writeJSON(w, camera.Focus{})
		return
	}
	if r.Method == "POST" {
		var req struct {
			Auto bool `json:"auto"`
			Pos  *int `json:"pos"`
		}
		if err := readJSON(r, &req); err != nil {
			fail(w, 400, err)
			return
		}
		pos := 0
		if req.Pos != nil {
			pos = *req.Pos
		} else if f, err := ctl.Focus(); err == nil {
			pos = f.Pos // lock at the present lens position
		}
		if err := ctl.SetFocus(req.Auto, pos); err != nil {
			fail(w, 500, err)
			return
		}
	}
	f, err := ctl.Focus()
	if err != nil {
		fail(w, 500, err)
		return
	}
	writeJSON(w, f)
}

func (a *App) hPort(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Path string `json:"path"`
	}
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	if err := a.connect(req.Path); err != nil {
		fail(w, 400, err)
		return
	}
	a.mu.Lock()
	link := a.link
	a.mu.Unlock()
	writeJSON(w, map[string]string{"port": req.Path, "link": link})
}

// hDiscover looks for plotters on the local network (mDNS, about 2 s).
func (a *App) hDiscover(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2500*time.Millisecond)
	defer cancel()
	devs, err := netlink.Discover(ctx)
	if err != nil {
		fail(w, 500, err)
		return
	}
	if devs == nil {
		devs = []netlink.Device{}
	}
	writeJSON(w, devs)
}

// hDevices lists the serial devices that can be a plotter.
func (a *App) hDevices(w http.ResponseWriter, r *http.Request) {
	var out []string
	for _, pat := range []string{"/dev/ttyACM*", "/dev/ttyUSB*", "/dev/serial/by-id/*"} {
		m, _ := filepath.Glob(pat)
		out = append(out, m...)
	}
	if out == nil {
		out = []string{}
	}
	writeJSON(w, out)
}

func (a *App) hScan(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()
	if err := a.Scan(ctx); err != nil {
		fail(w, 500, err)
		return
	}
	a.mu.Lock()
	f := a.scan
	a.mu.Unlock()
	writeJSON(w, map[string]any{"w": f.W, "h": f.H})
}

func (a *App) hScanJPG(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	f := a.scan
	a.mu.Unlock()
	if f == nil {
		fail(w, 404, errors.New("no scan yet"))
		return
	}
	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "no-store")
	w.Write(f.JPEG)
}

func (a *App) hBedJPG(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	b := a.bed
	a.mu.Unlock()
	if b == nil {
		fail(w, 404, errors.New("no bed view: calibrate and scan"))
		return
	}
	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "no-store")
	w.Write(b)
}

func (a *App) hCalib(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	c := a.calib
	a.mu.Unlock()
	writeJSON(w, c)
}

// calibPoints returns the calibration points of a grid: 0 = the 4 corners and the centre,
// 3 = 3 x 3, 4 = 4 x 4. The points are inset 12 mm from the travel.
func (a *App) calibPoints(grid int) []plan.Pt {
	return plan.Grid(grid, a.cfg.TravelX, a.cfg.TravelY, 12)
}

func (a *App) hCalibPoints(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Grid int `json:"grid"`
	}
	readJSON(r, &req)
	writeJSON(w, a.calibPoints(req.Grid))
}

// hCalibMark homes and draws a dot at each calibration point, then parks for the scan.
func (a *App) hCalibMark(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Grid int     `json:"grid"`
		Size float64 `json:"size"`
	}
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	if req.Size <= 0 {
		req.Size = 1.5
	}
	var lines [][]plan.Pt
	pts := a.calibPoints(req.Grid)
	for _, p := range pts {
		lines = append(lines, plan.Dot(p, req.Size)...)
	}
	park := plan.Pt{X: a.cfg.ParkX, Y: a.cfg.TravelY}
	prog := plan.GCode(lines, plan.Options{Feed: a.cfg.Feed, Home: true, Park: &park})
	if _, err := a.startJob("calibration marks", prog); err != nil {
		fail(w, 409, err)
		return
	}
	writeJSON(w, pts)
}

// hCalibGoto moves the pen (up) over a point, for a click on the pen tip in the picture.
func (a *App) hCalibGoto(w http.ResponseWriter, r *http.Request) {
	var req plan.Pt
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 60*time.Second)
	defer cancel()
	if _, err := a.commands(ctx, "M5", fmt.Sprintf("G0 X%.3f Y%.3f", req.X, req.Y), "M400"); err != nil {
		fail(w, 500, err)
		return
	}
	writeJSON(w, req)
}

func (a *App) hCalibRefine(w http.ResponseWriter, r *http.Request) {
	var req struct{ PX, PY float64 }
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	a.mu.Lock()
	f := a.scan
	a.mu.Unlock()
	if f == nil {
		fail(w, 404, errors.New("no scan"))
		return
	}
	img, err := f.Image()
	if err != nil {
		fail(w, 500, err)
		return
	}
	rad := max(6, f.W/120)
	p := Refine(img, geom.Pt{X: req.PX, Y: req.PY}, rad)
	writeJSON(w, map[string]float64{"px": p.X, "py": p.Y})
}

func (a *App) hCalibSolve(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Pairs []Pair `json:"pairs"`
		FitK1 *bool  `json:"fit_k1"`
		Size  [2]int `json:"size"`
	}
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	a.mu.Lock()
	f, cam := a.scan, a.cam
	a.mu.Unlock()
	sz := req.Size
	if sz == ([2]int{}) && f != nil {
		sz = [2]int{f.W, f.H}
	}
	fit := a.cfg.FitLens
	if req.FitK1 != nil {
		fit = *req.FitK1
	}
	c, err := Solve(req.Pairs, sz[0], sz[1], fit)
	if err != nil {
		fail(w, 400, err)
		return
	}
	if cam != nil {
		c.Camera = cam.Name()
		if ctl, ok := cam.(camera.Controller); ok {
			if fo, err := ctl.Focus(); err == nil && fo.Has && !fo.Auto {
				p := fo.Pos
				c.Focus = &p
			}
		}
	}
	a.mu.Lock()
	path := a.calibPath()
	a.mu.Unlock()
	if err := c.Save(path); err != nil {
		a.logf("err", "save the calibration: %v", err)
	}
	a.mu.Lock()
	a.calib = c
	a.mu.Unlock()
	a.renderBed()
	a.logf("info", "calibration: %d points, rms %.2f mm, k1 %.3f", len(c.Pairs), c.RMS, c.Lens.K1)
	writeJSON(w, c)
}

// hSVG parses an SVG file and returns its lines, moved so that the drawing starts at 0,0.
func (a *App) hSVG(w http.ResponseWriter, r *http.Request) {
	d, err := svg.Parse(io.LimitReader(r.Body, 32<<20), svg.Options{Tolerance: 0.05})
	if err != nil {
		fail(w, 400, err)
		return
	}
	writeJSON(w, normalise(d))
}

func normalise(d *svg.Drawing) plan.Item {
	mnx, mny := math.Inf(1), math.Inf(1)
	mxx, mxy := math.Inf(-1), math.Inf(-1)
	for _, l := range d.Lines {
		for _, p := range l {
			mnx, mny = math.Min(mnx, p.X), math.Min(mny, p.Y)
			mxx, mxy = math.Max(mxx, p.X), math.Max(mxy, p.Y)
		}
	}
	it := plan.Item{Scale: 1}
	if math.IsInf(mnx, 1) {
		return it
	}
	multi := false
	for i := range d.Colors {
		if d.Colors[i] != d.Colors[0] || d.Layers[i] != d.Layers[0] {
			multi = true
			break
		}
	}
	for i, l := range d.Lines {
		pl := make([]plan.Pt, len(l))
		for j, p := range l {
			pl[j] = plan.Pt{X: round3(p.X - mnx), Y: round3(p.Y - mny)}
		}
		it.Lines = append(it.Lines, pl)
		if i < len(d.Colors) {
			it.Colors = append(it.Colors, d.Colors[i])
			it.Layers = append(it.Layers, d.Layers[i])
		}
	}
	if !multi {
		// One colour and one layer: keep the colour, drop the per-line lists.
		if len(it.Colors) > 0 {
			it.Colors = []string{it.Colors[0]}
			it.Layers = []string{it.Layers[0]}
		}
	}
	it.W, it.H = mxx-mnx, mxy-mny
	return it
}

func round3(v float64) float64 { return math.Round(v*1000) / 1000 }

// queuedJob is a plot that waits for the end of the job now.
type queuedJob struct {
	ID      int            `json:"id"`
	Name    string         `json:"name"`
	Stats   map[string]any `json:"stats"`
	program string
}

type plotReq struct {
	// Queue puts the plot in the queue when a job runs.
	Queue bool        `json:"queue"`
	Items []plan.Item `json:"items"`
	Feed  float64     `json:"feed"`
	Home  bool        `json:"home"`
	Park  bool        `json:"park"`
	// ColorPens maps a line colour (#rrggbb) to a pen. A colour that is not in the map goes
	// to the pen with the nearest colour.
	ColorPens map[string]int `json:"color_pens"`
	// LayerPens uses a pen number in a layer label ("T3", "Pen 3 - red") first.
	LayerPens bool `json:"layer_pens"`
	// ToolChange starts a one-pen job with a pen change too.
	ToolChange bool `json:"tool_change"`
}

// penOf picks the pen of one line: the pen in the layer label, then the pen of the colour,
// then the pen with the nearest colour. It gives only pens of the table.
func penOf(color, layer string, req plotReq, table []plan.Pen) int {
	has := func(t int) bool {
		for _, p := range table {
			if p.T == t {
				return true
			}
		}
		return false
	}
	if req.LayerPens {
		if p := plan.LayerPen(layer); p >= 0 && has(p) {
			return p
		}
	}
	if p, ok := req.ColorPens[strings.ToLower(color)]; ok && has(p) {
		return p
	}
	if color != "" {
		if p := plan.Nearest(color, table); p >= 0 {
			return p
		}
	}
	if has(0) || len(table) == 0 {
		return 0
	}
	return table[0].T
}

// program makes the program of a plot. A job with more than one pen gets a manual pen change
// (T<n>, M6) before each pen.
func (a *App) program(req plotReq) (string, map[string]any, error) {
	a.mu.Lock()
	table := append([]plan.Pen(nil), a.pens...)
	a.mu.Unlock()
	var all [][]plan.Pt
	var pens []int
	for _, it := range req.Items {
		placed := it.Place()
		for i, l := range placed {
			color, layer := "", ""
			switch {
			case i < len(it.Colors) && len(it.Colors) == len(placed):
				color, layer = it.Colors[i], it.Layers[i]
			case len(it.Colors) == 1:
				color = it.Colors[0]
				if len(it.Layers) == 1 {
					layer = it.Layers[0]
				}
			}
			all = append(all, l)
			pens = append(pens, penOf(color, layer, req, table))
		}
	}
	if len(all) == 0 {
		return "", nil, errors.New("nothing to plot")
	}
	if err := plan.Check(all, a.cfg.TravelX, a.cfg.TravelY); err != nil {
		return "", nil, err
	}
	feed := req.Feed
	if feed <= 0 {
		feed = a.cfg.Feed
	}
	o := plan.Options{Feed: feed, Home: req.Home}
	if req.Park {
		p := plan.Pt{X: a.cfg.ParkX, Y: a.cfg.TravelY}
		o.Park = &p
	}
	groups := plan.GroupByPen(all, pens, table)
	g := plan.GCodeGroups(groups, o, req.ToolChange)
	changes := 0
	if len(groups) > 1 || req.ToolChange {
		changes = len(groups)
	}
	var draw, travel float64
	at := plan.Pt{}
	var used []int
	nlines := 0
	for _, gr := range groups {
		used = append(used, gr.Pen)
		nlines += len(gr.Lines)
		travel += plan.TravelLength(gr.Lines, at)
		for _, l := range gr.Lines {
			for i := 1; i < len(l); i++ {
				draw += math.Hypot(l[i].X-l[i-1].X, l[i].Y-l[i-1].Y)
			}
			at = l[len(l)-1]
		}
	}
	stats := map[string]any{"lines": nlines, "draw_mm": math.Round(draw),
		"travel_mm": math.Round(travel), "gcode_lines": len(serial.Program(g)),
		"pens": used, "pen_changes": changes,
		"est_s": math.Round((draw/feed*60)*1.3 + float64(nlines)*0.5)}
	return g, stats, nil
}

func (a *App) hGCode(w http.ResponseWriter, r *http.Request) {
	var req plotReq
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	g, stats, err := a.program(req)
	if err != nil {
		fail(w, 400, err)
		return
	}
	stats["gcode"] = g
	writeJSON(w, stats)
}

func (a *App) hPlot(w http.ResponseWriter, r *http.Request) {
	var req plotReq
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	g, stats, err := a.program(req)
	if err != nil {
		fail(w, 400, err)
		return
	}
	name := "layout"
	if len(req.Items) == 1 && req.Items[0].Name != "" {
		name = req.Items[0].Name
	}
	a.mu.Lock()
	busy := a.busy()
	if busy && req.Queue {
		a.qid++
		a.queue = append(a.queue, queuedJob{ID: a.qid, Name: name, Stats: stats, program: g})
		stats["queued"] = a.qid
		a.mu.Unlock()
		writeJSON(w, stats)
		return
	}
	a.mu.Unlock()
	if _, err = a.startJob(name, g); err != nil {
		fail(w, 409, err)
		return
	}
	writeJSON(w, stats)
}

func (a *App) hJob(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	j := a.job
	a.mu.Unlock()
	if j == nil {
		fail(w, 404, errors.New("no job"))
		return
	}
	switch r.PathValue("op") {
	case "pause":
		j.Pause()
	case "resume":
		j.Resume()
	case "cancel":
		j.Cancel()
	default:
		fail(w, 404, errors.New("unknown operation"))
		return
	}
	writeJSON(w, j.Status())
}

func (a *App) takeQueued(id string) (queuedJob, int, bool) {
	var n int
	fmt.Sscanf(id, "%d", &n)
	for i, q := range a.queue {
		if q.ID == n {
			return q, i, true
		}
	}
	return queuedJob{}, -1, false
}

// hQueueStart starts a queued job. The person starts each job, because a job can need new paper.
func (a *App) hQueueStart(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	q, i, ok := a.takeQueued(r.PathValue("id"))
	removed := ok && !a.busy()
	if removed {
		a.queue = append(a.queue[:i], a.queue[i+1:]...)
	}
	a.mu.Unlock()
	if !ok {
		fail(w, 404, errors.New("no such job in the queue"))
		return
	}
	if _, err := a.startJob(q.Name, q.program); err != nil {
		if removed {
			// Keep the job in the queue: the user can try again.
			a.mu.Lock()
			a.queue = append([]queuedJob{q}, a.queue...)
			a.mu.Unlock()
		}
		fail(w, 409, err)
		return
	}
	writeJSON(w, q)
}

func (a *App) hQueueDelete(w http.ResponseWriter, r *http.Request) {
	a.mu.Lock()
	_, i, ok := a.takeQueued(r.PathValue("id"))
	if ok {
		a.queue = append(a.queue[:i], a.queue[i+1:]...)
	}
	a.mu.Unlock()
	if !ok {
		fail(w, 404, errors.New("no such job in the queue"))
		return
	}
	writeJSON(w, map[string]bool{"deleted": true})
}

func (a *App) hCmd(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Lines []string `json:"lines"`
	}
	if err := readJSON(r, &req); err != nil {
		fail(w, 400, err)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 180*time.Second)
	defer cancel()
	out, err := a.commands(ctx, req.Lines...)
	if err != nil {
		fail(w, 500, err)
		return
	}
	writeJSON(w, map[string]any{"reply": out})
}

var safeName = regexp.MustCompile(`[^A-Za-z0-9_.-]+`)

func (a *App) libDir() string { return filepath.Join(a.cfg.DataDir, "library") }

func (a *App) hLibrary(w http.ResponseWriter, r *http.Request) {
	if r.Method == "POST" {
		var req struct{ Name, SVG string }
		if err := readJSON(r, &req); err != nil {
			fail(w, 400, err)
			return
		}
		name := strings.Trim(safeName.ReplaceAllString(req.Name, "-"), "-.")
		if name == "" || !strings.Contains(req.SVG, "<svg") {
			fail(w, 400, errors.New("a name and an SVG are needed"))
			return
		}
		os.MkdirAll(a.libDir(), 0o755)
		if err := os.WriteFile(filepath.Join(a.libDir(), name+".svg"), []byte(req.SVG), 0o644); err != nil {
			fail(w, 500, err)
			return
		}
	}
	ents, _ := os.ReadDir(a.libDir())
	var names []string
	for _, e := range ents {
		if strings.HasSuffix(e.Name(), ".svg") {
			names = append(names, strings.TrimSuffix(e.Name(), ".svg"))
		}
	}
	sort.Strings(names)
	writeJSON(w, names)
}

func (a *App) hLibraryGet(w http.ResponseWriter, r *http.Request) {
	name := safeName.ReplaceAllString(r.PathValue("name"), "-")
	b, err := os.ReadFile(filepath.Join(a.libDir(), name+".svg"))
	if err != nil {
		fail(w, 404, err)
		return
	}
	w.Header().Set("Content-Type", "image/svg+xml")
	w.Write(b)
}

// Bed returns the bed view picture (for tests).
func (a *App) Bed() (image.Image, error) {
	a.mu.Lock()
	b := a.bed
	a.mu.Unlock()
	if b == nil {
		return nil, errors.New("no bed view")
	}
	return jpeg.Decode(bytes.NewReader(b))
}

// Close closes the port and the camera.
func (a *App) Close() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.closed = true
	if a.port != nil {
		a.port.Close()
	}
	if a.cam != nil {
		a.cam.Close()
	}
}
