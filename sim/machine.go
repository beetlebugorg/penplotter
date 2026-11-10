// Package sim runs the plotter firmware on a computer.
// It uses the same controller, planner and step executor code as the board.
// BoardMega runs the small controller of the stock CR-10 V3 mainboard (ATmega2560).
// BoardPico runs the full controller of the Pico W upgrade, with the network API.
// A machine model moves the carriage, the switches, the servo and the pen ink.
package sim

import (
	"math"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/controller"
	"github.com/beetlebugorg/penplotter/firmware/mini"
	"github.com/beetlebugorg/penplotter/firmware/settings"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// Seg is one ink line in mm, in bed coordinates. The origin is the home corner.
type Seg [4]float32

// Event is a message for the UI windows that is not part of the state.
type Event struct {
	Kind string // "beep" or "serial"
	Ms   int
	Dir  string
	Text string
}

// Snapshot is the published machine state.
type Snapshot struct {
	X, Y    float32 // carriage position in mm. Y is the Y1 side.
	Y2      float32 // the Y2 side in mm
	Pen     float32 // 0 = up, 1 = down
	Servo   float32 // the servo angle in degrees
	Lift    float32 // the slider lift above the paper contact in mm (LiftOK)
	LiftOK  bool    // a linkage is set (SetPenLink)
	Over    bool    // the horn tip is over the tab: the horn stops on the tab top
	Motors  bool
	ES      [3]bool // X, Y1, Y2
	Status  ui.Status
	Queued  int
	Line    string
	Name    string // file name of the current job
	Done    int
	Total   int
	Speed   int
	PenUp   int
	PenDown int
}

// Board selects the firmware that the simulator runs.
type Board string

const (
	BoardMega Board = "mega" // the stock CR-10 V3 mainboard: small controller, USB only
	BoardPico Board = "pico" // the Pico W upgrade: full controller, Wi-Fi and the HTTP API
)

// firmware is the main loop of one board.
type firmware interface {
	Poll()
	status() (ui.Status, int, int, int) // status, queued moves, pen up and pen down angles
}

type picoFW struct{ c *controller.Controller }

func (f picoFW) Poll() { f.c.Poll() }
func (f picoFW) status() (ui.Status, int, int, int) {
	up, dn := f.c.PenAngles()
	return f.c.Status(), f.c.Queued(), up, dn
}

type megaFW struct{ c *mini.Controller }

func (f megaFW) Poll() { f.c.Poll() }
func (f megaFW) status() (ui.Status, int, int, int) {
	s := f.c.State()
	st := ui.Status{X: s.X, Y: s.Y, PenDown: s.PenDown, Homed: s.Homed, Motors: s.Motors,
		Busy: s.Busy, Alarm: s.Alarm, Lines: s.Lines, Progress: s.Progress, Speed: s.Speed,
		PenUp: s.PenUp, PenDn: s.PenDownAt, Msg: s.Msg, Tool: s.Tool, State: "Idle"}
	switch {
	case s.Alarm:
		st.State = "ALARM"
	case s.Paused:
		st.State = "Paused"
	case s.Busy:
		st.State = "Run"
	}
	return st, s.Queued, s.PenUp, s.PenDownAt
}

// Machine is the simulated plotter.
type Machine struct {
	Board  Board
	Serial *Serial
	Events chan Event
	// Store keeps the settings of the Pico W (M500). Set it before the first Reset; New uses no store.
	Store  settings.Store
	eeprom mini.Store
	net    *simNet

	start time.Time
	speed atomic.Int32
	enc   atomic.Int32
	btn   atomic.Bool

	freeHorn atomic.Bool // FreeHorn: a person lifts the slider

	motors atomic.Bool
	es     [3]atomic.Bool

	mu       sync.Mutex
	ex       *stepgen.Executor
	ctl      *controller.Controller // BoardPico only
	fw       firmware
	stop     chan struct{}
	wg       sync.WaitGroup
	status   ui.Status
	queued   int
	penUp    int
	penDown  int
	lcd      [ui.Stride * ui.Height]byte
	lcdVer   uint64
	ink      []Seg
	inkVer   uint64
	job      *job
	lastRx   string
	pubX     float32
	pubY     float32
	pubY2    float32
	pubPen   float32
	pubServo float32
	pubLift  float32
	penLink  *PenLink // the pen lift linkage (SetPenLink); nil: no linkage model
	pubOver  bool
	ttys     []*os.File

	// Model state. Only the step goroutine uses these.
	phys    [3]int32 // X, Y1, Y2 in steps; each switch is at 0
	dir     uint8
	servo   float64
	servoTo float64
	inking  bool
	inkLast [2]int32
	frac    float64
	link    *PenLink // a copy of penLink for the step goroutine
	over    bool     // the horn tip is over the tab (see penlift.go)
}

// New makes a Pico W machine. The carriage starts at an unknown position, as after power on.
// The Y2 side starts 0.6 mm behind Y1, so homing squares the beam.
func New() *Machine { return NewWith(nil) }

// NewWith makes a Pico W machine that keeps its settings in store (nil: in RAM only).
func NewWith(store settings.Store) *Machine { return NewOpts(Options{Board: BoardPico, Store: store}) }

// NewMega makes a machine with the stock mainboard. eeprom keeps the settings (nil: RAM only).
func NewMega(eeprom mini.Store) *Machine { return NewOpts(Options{Board: BoardMega, EEPROM: eeprom}) }

// Options set up a machine.
type Options struct {
	Board  Board
	Store  settings.Store // BoardPico: the flash record
	EEPROM mini.Store     // BoardMega: the EEPROM record
}

// NewOpts makes a machine.
func NewOpts(o Options) *Machine {
	if o.Board == "" {
		o.Board = BoardMega
	}
	m := &Machine{Board: o.Board, Events: make(chan Event, 1024), start: time.Now(), Store: o.Store,
		eeprom: o.EEPROM, net: &simNet{ip: [4]byte{127, 0, 0, 1}}}
	m.Serial = newSerial(m)
	m.speed.Store(1)
	m.phys = [3]int32{int32(100 * config.StepsPerMMX), int32(150 * config.StepsPerMMY), int32(150.6 * config.StepsPerMMY)}
	m.servo = config.PenUpDeg
	m.servoTo = config.PenUpDeg
	m.boot()
	return m
}

// boot makes a new executor and controller and starts them, as a power on does.
func (m *Machine) boot() {
	ex := &stepgen.Executor{}
	ex.Endstop = func(ch int) bool { return m.phys[ch] <= 0 }
	m.motors.Store(false)
	h := &hal{m: m}
	var fw firmware
	var ctl *controller.Controller
	if m.Board == BoardPico {
		ctl = controller.NewWith(h, ex, controller.Options{Store: m.Store, Net: m.net})
		fw = picoFW{ctl}
	} else {
		h.fb = &ui.FB{}
		fw = megaFW{mini.New(h, ex, m.eeprom)}
	}
	_, _, up, dn := fw.status()
	m.mu.Lock()
	m.ex, m.ctl, m.fw = ex, ctl, fw
	m.stop = make(chan struct{})
	m.penUp, m.penDown = up, dn
	m.mu.Unlock()
	m.wg.Add(2)
	go m.runSteps(ex, m.stop)
	go m.runController(fw, m.stop)
}

// Reset restarts the firmware. The carriage and the paper stay as they are.
func (m *Machine) Reset() {
	m.CancelJob()
	close(m.stop)
	m.wg.Wait()
	m.Serial.reset()
	m.boot()
}

// SetSpeed sets the simulation speed factor.
func (m *Machine) SetSpeed(x int) {
	if x < 1 {
		x = 1
	}
	if x > 100 {
		x = 100
	}
	m.speed.Store(int32(x))
}

// Turn sends knob detents.
func (m *Machine) Turn(d int) { m.enc.Add(int32(d)) }

// Press sets the knob button state.
func (m *Machine) Press(down bool) { m.btn.Store(down) }

// ClearPaper removes all ink.
func (m *Machine) ClearPaper() {
	m.mu.Lock()
	m.ink = nil
	m.inkVer++
	m.mu.Unlock()
}

func (m *Machine) emit(e Event) {
	select {
	case m.Events <- e:
	default:
	}
}

// Snapshot returns the current state.
func (m *Machine) Snapshot() Snapshot {
	m.mu.Lock()
	defer m.mu.Unlock()
	s := Snapshot{
		Status: m.status, Queued: m.queued, Speed: int(m.speed.Load()),
		Motors: m.motors.Load(), ES: [3]bool{m.es[0].Load(), m.es[1].Load(), m.es[2].Load()},
		PenUp: m.penUp, PenDown: m.penDown, Line: m.lastRx,
	}
	s.X, s.Y, s.Y2, s.Pen, s.Servo = m.pubX, m.pubY, m.pubY2, m.pubPen, m.pubServo
	s.Lift, s.LiftOK, s.Over = m.pubLift, m.penLink != nil, m.pubOver
	if j := m.job; j != nil {
		s.Done, s.Total, s.Name = int(j.done.Load()), j.total, j.name
	}
	return s
}

// LCD returns a copy of the LCD pixels and a version number.
func (m *Machine) LCD() ([ui.Stride * ui.Height]byte, uint64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.lcd, m.lcdVer
}

// Ink returns the ink lines from index i on, and the paper version.
// The version changes when the paper is cleared.
func (m *Machine) Ink(i int) ([]Seg, int, uint64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if i > len(m.ink) {
		i = len(m.ink)
	}
	out := make([]Seg, len(m.ink)-i)
	copy(out, m.ink[i:])
	return out, len(m.ink), m.inkVer
}

// runController runs the firmware main loop.
func (m *Machine) runController(fw firmware, stop chan struct{}) {
	defer m.wg.Done()
	var last time.Time
	for {
		select {
		case <-stop:
			return
		default:
		}
		fw.Poll()
		if now := time.Now(); now.Sub(last) > 5*time.Millisecond {
			last = now
			st, q, up, dn := fw.status()
			m.mu.Lock()
			m.status, m.queued, m.penUp, m.penDown = st, q, up, dn
			m.mu.Unlock()
		}
		time.Sleep(100 * time.Microsecond)
	}
}

// runSteps runs the executor ticks in real time and moves the model.
func (m *Machine) runSteps(ex *stepgen.Executor, stop chan struct{}) {
	defer m.wg.Done()
	t := time.NewTicker(time.Millisecond)
	defer t.Stop()
	last := time.Now()
	for {
		select {
		case <-stop:
			return
		case now := <-t.C:
			el := now.Sub(last).Seconds()
			last = now
			if el > 0.05 {
				el = 0.05
			}
			m.frac += el * config.TickHz * float64(m.speed.Load())
			n := int(m.frac)
			m.frac -= float64(n)
			m.mu.Lock()
			up, dn := float64(m.penUp), float64(m.penDown)
			m.link = m.penLink
			m.mu.Unlock()
			var ink []Seg
			for i := 0; i < n; i++ {
				ink = m.tick(ex, up, dn, ink)
				// Publish often, so the windows see smooth motion at high speed factors.
				if i%400 == 399 {
					ink = m.publish(ink, up, dn, false)
				}
			}
			m.publish(ink, up, dn, true)
		}
	}
}

// publish copies the model state to the shared fields and adds the new ink.
func (m *Machine) publish(ink []Seg, up, dn float64, flush bool) []Seg {
	if p := m.penPos(); flush && m.inking && p != m.inkLast {
		ink = append(ink, m.seg(m.inkLast, p))
		m.inkLast = p
	}
	for ch := range m.es {
		m.es[ch].Store(m.phys[ch] <= 0)
	}
	m.mu.Lock()
	m.ink = append(m.ink, ink...)
	m.pubX = float32(m.phys[0]) / config.StepsPerMM[0]
	m.pubY = float32(m.phys[1]) / config.StepsPerMM[1]
	m.pubY2 = float32(m.phys[2]) / config.StepsPerMM[1]
	m.pubPen = float32(penNorm(m.servo, up, dn))
	m.pubServo = float32(m.servo)
	if m.link != nil {
		m.pubLift = float32(m.link.lift(m.servo, m.over))
	}
	m.pubOver = m.over
	m.mu.Unlock()
	return ink[:0]
}

func penNorm(servo, up, dn float64) float64 {
	if up == dn {
		return 0
	}
	v := (up - servo) / (up - dn)
	return math.Max(0, math.Min(1, v))
}

const servoDegPerTick = 600.0 / config.TickHz // a hobby servo turns about 600 degrees per second

func (m *Machine) tick(ex *stepgen.Executor, up, dn float64, ink []Seg) []Seg {
	o := ex.Tick()
	if o.DirSet {
		m.dir = o.Dir
	}
	if o.Servo >= 0 {
		m.servoTo = float64(o.Servo)
	}
	if d := m.servoTo - m.servo; d != 0 {
		m.servo += math.Max(-servoDegPerTick, math.Min(servoDegPerTick, d))
	}
	if m.link != nil {
		m.servo = m.link.stop(m.servo, &m.over, m.freeHorn.Swap(false))
	}
	if o.Step != 0 && m.motors.Load() {
		for a := 0; a < 3; a++ {
			if o.Step&(1<<a) == 0 {
				continue
			}
			if m.dir&(1<<a) != 0 {
				m.phys[a]--
			} else {
				m.phys[a]++
			}
			// Hard stops of the frame: a carriage cannot go further.
			ax := min(a, 1)
			lo := int32(-2 * config.StepsPerMM[ax])
			hi := int32((config.Travel[ax] + 8) * config.StepsPerMM[ax])
			if m.phys[a] < lo {
				m.phys[a] = lo
			}
			if m.phys[a] > hi {
				m.phys[a] = hi
			}
		}
	}
	down := penTouches(m.link, m.servo, m.over, up, dn)
	p := m.penPos()
	switch {
	case down && !m.inking:
		m.inking = true
		m.inkLast = p
	case down:
		dx, dy := p[0]-m.inkLast[0], p[1]-m.inkLast[1]
		if dx*dx+dy*dy >= 16 { // 4 steps = 0.05 mm
			ink = append(ink, m.seg(m.inkLast, p))
			m.inkLast = p
		}
	case m.inking:
		if p != m.inkLast {
			ink = append(ink, m.seg(m.inkLast, p))
		}
		m.inking = false
	}
	return ink
}

// penPos returns the pen position in steps. The pen is at the middle of the beam
// in Y, so it uses the mean of Y1 and Y2.
func (m *Machine) penPos() [2]int32 {
	return [2]int32{m.phys[0], (m.phys[1] + m.phys[2]) / 2}
}

func (m *Machine) seg(a, b [2]int32) Seg {
	r := func(v int32, ax int) float32 {
		return float32(math.Round(float64(v)/float64(config.StepsPerMM[ax])*1000) / 1000)
	}
	return Seg{r(a[0], 0), r(a[1], 1), r(b[0], 0), r(b[1], 1)}
}

// hal is the controller.HAL and the mini.Board of the simulator.
type hal struct {
	m  *Machine
	fb *ui.FB // BoardMega: the text lines of the ST7920
}

func (h *hal) NowMicros() uint64        { return uint64(time.Since(h.m.start).Microseconds()) }
func (h *hal) SetMotors(on bool)        { h.m.motors.Store(on) }
func (h *hal) Endstop(a int) bool       { return h.m.es[a].Load() }
func (h *hal) Encoder() int             { return int(h.m.enc.Swap(0)) }
func (h *hal) Button() bool             { return h.m.btn.Load() }
func (h *hal) Beep(ms int)              { h.m.emit(Event{Kind: "beep", Ms: ms}) }
func (h *hal) ReadSerial() (byte, bool) { return h.m.Serial.readByte() }
func (h *hal) WriteSerial(s string)     { h.m.Serial.write(s) }
func (h *hal) Display() ui.Display      { return h }
func (h *hal) Poll()                    {}

// Text implements mini.Board. The ST7920 text mode has 4 rows of 16 cells, 8 x 16 pixels each.
// The simulator draws the 5 x 7 font in each cell.
func (h *hal) Text(row int, s string) {
	if row < 0 || row > 3 {
		return
	}
	h.fb.Fill(0, row*16, ui.Width, 16, false)
	for i := 0; i < len(s) && i < 16; i++ {
		h.fb.Text(i*8+1, row*16+4, s[i:i+1], 1, true)
	}
	h.fb.Commit()
	h.Flush(h.fb)
}

// Flush implements ui.Display. The simulator sends all dirty rows at once.
func (h *hal) Flush(fb *ui.FB) {
	if !fb.Dirty() {
		return
	}
	for fb.Dirty() {
		fb.NextDirty()
	}
	h.m.mu.Lock()
	h.m.lcd = fb.Front
	h.m.lcdVer++
	h.m.mu.Unlock()
}

// SetHTTPAddr tells the simulated Wi-Fi the address of the HTTP server.
func (m *Machine) SetHTTPAddr(addr string) {
	m.net.mu.Lock()
	m.net.ip = hostIP(addr)
	m.net.mu.Unlock()
}
