// Package mini is the controller for a small processor: the ATmega2560 of the stock CR-10 V3
// mainboard (8 KB RAM). It uses the same G-code parser, planner and step executor as the
// full controller, and the same replies to the host ("ok", "?" status, M114, M119).
//
// It leaves out what does not fit in 8 KB: the graphic menu (the LCD shows 4 text lines),
// the network ports, and the 16 pen names.
package mini

import (
	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/gcode"
	"github.com/beetlebugorg/penplotter/firmware/planner"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
)

// Board is the hardware. The board also runs Executor.Tick from its step timer.
type Board interface {
	NowMicros() uint64
	SetMotors(on bool)
	Endstop(ch int) bool
	Encoder() int
	Button() bool
	Beep(ms int)
	ReadSerial() (byte, bool)
	WriteSerial(s string)
	// Text writes one line (0..3) of the LCD, 16 characters.
	Text(row int, s string)
	Poll()
}

// Store keeps the settings (Settings.Encode) in a small non-volatile memory.
type Store interface {
	Load(b []byte) bool
	Save(b []byte) error
}

type waitKind uint8

const (
	waitNone waitKind = iota
	waitIdle          // M400: wait until all motion ends
	waitHome          // G28
	waitPen           // M6: wait for the knob or M108
)

// Controller is the main loop.
type Controller struct {
	b     Board
	ex    *stepgen.Executor
	pl    planner.Planner
	pr    planner.Prep
	store Store
	set   Settings

	line    [96]byte
	n       int
	ready   bool // line holds a complete line that waits for planner space
	comment bool
	local   bool // the line comes from the knob: send no reply
	gl      gcode.Line
	lineNo  uint32

	abs      bool
	scale    float32
	feed     float32
	motion   int
	off      [2]float32
	penDown  bool
	homed    bool
	motors   bool
	alarm    bool
	aborting bool
	paused   bool
	tool     int
	progress int
	msg      string

	wait     waitKind
	pending  string // the reply of the line that waits (M400, G28, M6, an arc)
	offAfter bool   // M18: motors off when the wait ends
	home     homing
	arc      gcode.Arc
	inArc    bool
	arcFeed  float32

	// The knob.
	menu     int
	btnDown  bool
	btnSince uint64
	longDone bool
	lastDraw uint64
	drawRow  int
	saveAt   uint64
}

// New makes the controller and loads the settings.
func New(b Board, ex *stepgen.Executor, st Store) *Controller {
	c := &Controller{b: b, ex: ex, store: st, abs: true, scale: 1, feed: config.DefaultFeed, motion: 1}
	c.pl.JunctionDev = config.JunctionDev
	c.pr = planner.Prep{P: &c.pl, Q: &ex.Q, TickHz: config.TickHz, SegTicks: config.SegmentTick, MinSpeed: config.MinSpeed}
	ex.HardLimits = config.HardLimits
	c.set = DefaultSettings()
	var buf [settingsSize]byte
	if st != nil && st.Load(buf[:]) {
		if s, ok := DecodeSettings(buf[:]); ok {
			c.set = s
		}
	}
	b.WriteSerial("start\nPenPlotter " + config.Version + " (TinyGo, ATmega2560)\n")
	c.msg = "Ready"
	return c
}

// Poll runs one pass of the main loop.
func (c *Controller) Poll() {
	c.readSerial()
	if c.aborting {
		if c.ex.AbortDone() {
			c.pl.Pos = [2]int32{c.ex.Pos(0), c.ex.Pos(1)}
			c.aborting = false
		}
	} else {
		c.runWait()
		c.runArc()
		if c.ready && c.wait == waitNone && !c.inArc && !c.paused {
			c.runLine()
		}
		if h := c.ex.LimitHits(); h != 0 {
			c.emergency("hard limit")
		}
		c.pr.Fill()
	}
	c.pollKnob()
	c.draw()
	if c.saveAt != 0 && c.idle() && c.b.NowMicros() > c.saveAt {
		c.saveAt = 0
		c.save()
	}
	c.b.Poll()
}

func (c *Controller) idle() bool {
	return c.pl.Len() == 0 && !c.pr.Busy() && c.ex.Q.Len() == 0 && c.ex.Idle()
}

// readSerial collects one line. Realtime characters work at once: '?' sends the status,
// Ctrl-X (0x18) stops the machine.
func (c *Controller) readSerial() {
	for !c.ready {
		ch, ok := c.b.ReadSerial()
		if !ok {
			return
		}
		switch {
		case ch == '?':
			c.b.WriteSerial(c.statusLine())
		case ch == 0x18:
			c.emergency("Ctrl-X")
		case ch == '\n' || ch == '\r':
			c.comment = false
			if c.n > 0 {
				c.ready = true
			}
		case c.comment:
		case ch == ';':
			c.comment = true
		case c.n < len(c.line):
			c.line[c.n] = ch
			c.n++
		}
	}
	// The safety lines work while another line waits.
	if c.ready && c.n >= 4 && c.line[0] == 'M' {
		switch string(c.line[:4]) {
		case "M112":
			c.emergency("M112")
			c.done("ok")
		case "M108":
			if c.wait == waitPen {
				c.finishWait()
			}
			c.done("ok")
		}
	}
}

// done ends the current line and sends the reply.
func (c *Controller) done(reply string) {
	c.n, c.ready = 0, false
	if c.local {
		c.local = false
		return
	}
	if reply != "" {
		c.b.WriteSerial(reply + "\n")
	}
}

// runLine runs the waiting line if the planner has space for it.
func (c *Controller) runLine() {
	if c.pl.Space() < 3 {
		return
	}
	if err := gcode.Parse(c.line[:c.n], &c.gl); err != nil {
		c.done("error:" + err.Error())
		return
	}
	c.lineNo++
	if c.alarm && !c.allowedInAlarm() {
		c.done("error:alarm, send M999")
		return
	}
	out := c.runWords(&c.gl)
	if c.wait != waitNone || c.inArc {
		// The reply comes when the wait or the arc ends.
		c.n = 0
		c.pending = out
		return
	}
	if out == "" {
		out = "ok"
	} else if out[0] != '!' && (len(out) < 5 || out[:5] != "error") {
		out += "\nok"
	}
	c.done(out)
}

func (c *Controller) allowedInAlarm() bool {
	for i := 0; i < c.gl.N; i++ {
		w := c.gl.W[i]
		if w.L == 'M' {
			switch int(w.V) {
			case 999, 114, 115, 119, 503, 105:
				return true
			}
		}
	}
	return false
}

// runWords runs all the words of one line.
func (c *Controller) runWords(l *gcode.Line) string {
	if f, ok := l.Get('F'); ok && f > 0 {
		c.feed = f * c.scale / 60
	}
	out := ""
	motion := -1
	for i := 0; i < l.N; i++ {
		w := l.W[i]
		code := int(w.V)
		switch w.L {
		case 'G':
			switch code {
			case 0, 1, 2, 3:
				motion = code
			case 4:
				ms := float32(0)
				if p, ok := l.Get('P'); ok {
					ms = p
				} else if s, ok := l.Get('S'); ok {
					ms = s * 1000
				}
				c.motorsOn()
				c.pl.AddDwell(msTicks(uint32(ms)), c.lineNo)
			case 20:
				c.scale = 25.4
			case 21:
				c.scale = 1
			case 28:
				c.startHome(l)
				return ""
			case 90:
				c.abs = true
			case 91:
				c.abs = false
			case 92:
				for a, L := range [2]byte{'X', 'Y'} {
					if v, ok := l.Get(L); ok {
						c.off[a] = c.machine(a) - v*c.scale
					}
				}
			default:
				return "error:unsupported G" + itoa(code)
			}
		case 'M':
			if s := c.runM(code, l); s != "" {
				out = s
			}
		case 'T':
			if code >= 0 && code < 16 {
				c.tool = code
			}
		}
	}
	if motion < 0 && (l.Has('X') || l.Has('Y')) {
		motion = c.motion
	}
	if motion >= 0 {
		c.motion = motion
		c.startMotion(l, motion)
	}
	return out
}

func (c *Controller) runM(code int, l *gcode.Line) string {
	switch code {
	case 3, 4:
		c.setPen(true)
	case 5:
		c.setPen(false)
	case 6:
		c.setPen(false)
		c.wait = waitPen
		c.msg = "Put in pen T" + itoa(c.tool)
		c.b.Beep(200)
	case 17:
		c.motorsOn()
	case 18, 84:
		c.wait = waitIdle
		c.offAfter = true
	case 73:
		if p, ok := l.Get('P'); ok {
			c.progress = int(p)
		}
	case 105:
		return "T:0 /0 B:0 /0"
	case 110:
	case 114:
		return c.position()
	case 115:
		return "FIRMWARE_NAME:PenPlotter " + config.Version + " (TinyGo, ATmega2560) MACHINE_TYPE:CR-10 V3 pen plotter"
	case 119:
		return "x_min: " + trig(c.b.Endstop(stepgen.ChX)) + "\ny1_min: " + trig(c.b.Endstop(stepgen.ChY1)) +
			"\ny2_min: " + trig(c.b.Endstop(stepgen.ChY2))
	case 280:
		if s, ok := l.Get('S'); ok {
			c.motorsOn()
			c.pl.AddPen(clampAngle(s), msTicks(config.PenSettleMs), c.lineNo)
		}
	case 281:
		if v, ok := l.Get('U'); ok {
			c.set.PenUp = uint8(clampAngle(v))
		}
		if v, ok := l.Get('D'); ok {
			c.set.PenDown = uint8(clampAngle(v))
		}
		c.saveLater()
		return "pen up:" + itoa(int(c.set.PenUp)) + " down:" + itoa(int(c.set.PenDown))
	case 400:
		c.wait = waitIdle
	case 500:
		c.save()
	case 501:
		var buf [settingsSize]byte
		if c.store != nil && c.store.Load(buf[:]) {
			if s, ok := DecodeSettings(buf[:]); ok {
				c.set = s
			}
		}
	case 502:
		c.set = DefaultSettings()
	case 503:
		return "M281 U" + itoa(int(c.set.PenUp)) + " D" + itoa(int(c.set.PenDown)) +
			"\necho:speed " + itoa(int(c.set.Speed)) + "%"
	case 999:
		c.alarm = false
		c.msg = "Ready"
	case 82, 83, 104, 106, 107, 109, 140, 190, 108, 112:
		// Printer codes: accepted, no effect. M108 and M112 run in readSerial.
	default:
		return "echo:ignored M" + itoa(code)
	}
	return ""
}

func trig(on bool) string {
	if on {
		return "TRIGGERED"
	}
	return "open"
}

func clampAngle(v float32) uint16 {
	if v < 0 {
		return 0
	}
	if v > 180 {
		return 180
	}
	return uint16(v)
}

func msTicks(ms uint32) uint32 { return ms * (config.TickHz / 1000) }

// machine returns the machine position of an axis in mm, at the end of the planned moves.
func (c *Controller) machine(a int) float32 {
	return float32(c.pl.Pos[a]) / config.StepsPerMM[a]
}

// startMotion plans G0, G1, G2 or G3.
func (c *Controller) startMotion(l *gcode.Line, motion int) {
	var t [2]float32
	for a, L := range [2]byte{'X', 'Y'} {
		cur := c.machine(a) - c.off[a]
		t[a] = cur
		if v, ok := l.Get(L); ok {
			if c.abs {
				t[a] = v * c.scale
			} else {
				t[a] = cur + v*c.scale
			}
		}
	}
	feed := c.feed * float32(c.set.Speed) / 100
	if motion == 0 {
		feed = config.RapidFeed
	}
	if motion == 2 || motion == 3 {
		i, _ := l.Get('I')
		j, _ := l.Get('J')
		r, _ := l.Get('R')
		sx, sy := c.machine(0)-c.off[0], c.machine(1)-c.off[1]
		a, ok := gcode.NewArc(sx, sy, t[0], t[1], i*c.scale, j*c.scale, r*c.scale, motion == 2,
			config.ArcMaxSeg, config.ArcTolerance)
		if ok {
			c.arc, c.inArc, c.arcFeed = a, true, feed
			c.runArc()
			return
		}
	}
	c.moveTo([2]float32{t[0] + c.off[0], t[1] + c.off[1]}, feed)
}

// runArc feeds the lines of an arc to the planner while it has space.
func (c *Controller) runArc() {
	for c.inArc && c.pl.Space() > 1 {
		x, y, ok := c.arc.Next()
		if !ok {
			c.inArc = false
			c.finishLine()
			return
		}
		c.moveTo([2]float32{x + c.off[0], y + c.off[1]}, c.arcFeed)
	}
}

func (c *Controller) moveTo(t [2]float32, speed float32) {
	var steps [2]int32
	for a := 0; a < 2; a++ {
		if config.SoftLimits && c.homed {
			if t[a] < 0 {
				t[a] = 0
			}
			if t[a] > config.Travel[a] {
				t[a] = config.Travel[a]
			}
		}
		v := t[a] * config.StepsPerMM[a]
		if v < 0 {
			steps[a] = int32(v - 0.5)
		} else {
			steps[a] = int32(v + 0.5)
		}
	}
	if speed > config.MaxFeed {
		speed = config.MaxFeed
	}
	c.motorsOn()
	c.pl.AddMove(steps, speed, config.Accel, config.StepsPerMM, c.lineNo)
}

func (c *Controller) setPen(down bool) {
	if down == c.penDown {
		return
	}
	c.penDown = down
	a := c.set.PenUp
	if down {
		a = c.set.PenDown
	}
	c.motorsOn()
	c.pl.AddPen(uint16(a), msTicks(config.PenSettleMs), c.lineNo)
}

func (c *Controller) motorsOn() { c.setMotors(true) }

func (c *Controller) setMotors(on bool) {
	if on != c.motors {
		c.motors = on
		c.b.SetMotors(on)
	}
	if !on {
		c.homed = false
	}
}

func (c *Controller) emergency(why string) {
	c.ex.Abort()
	c.pl.Clear()
	c.pr.Reset()
	c.wait, c.inArc, c.paused = waitNone, false, false
	c.n, c.ready, c.comment = 0, false, false
	c.setMotors(false)
	c.alarm = true
	c.msg = "STOP " + why
	c.b.WriteSerial("!! " + why + "\n")
	c.aborting = true
}

func (c *Controller) position() string {
	x := float32(c.pl.Pos[0])/config.StepsPerMM[0] - c.off[0]
	y := float32(c.pl.Pos[1])/config.StepsPerMM[1] - c.off[1]
	return "X:" + fixed(x/c.scale, 3) + " Y:" + fixed(y/c.scale, 3) + " Z:0.000 Count X:" +
		itoa(int(c.ex.Pos(stepgen.ChX))) + " Y:" + itoa(int(c.ex.Pos(stepgen.ChY1))) +
		" Y2:" + itoa(int(c.ex.Pos(stepgen.ChY2)))
}

// statusLine returns the Grbl-style status line for '?'.
func (c *Controller) statusLine() string {
	st := "Idle"
	switch {
	case c.alarm:
		st = "Alarm"
	case c.wait == waitHome:
		st = "Home"
	case c.paused:
		st = "Hold"
	case !c.idle():
		st = "Run"
	}
	x := float32(c.ex.Pos(0)) / config.StepsPerMM[0]
	y := float32(c.ex.Pos(1)) / config.StepsPerMM[1]
	return "<" + st + "|MPos:" + fixed(x, 3) + "," + fixed(y, 3) + ",0.000|>\n"
}

// State is a copy of the controller state for the simulator. The board firmware does not
// use it, so the linker removes it.
type State struct {
	X, Y      float32 // work position in mm
	PenDown   bool
	Homed     bool
	Motors    bool
	Busy      bool
	Alarm     bool
	Paused    bool
	Lines     uint32
	Progress  int
	Speed     int
	PenUp     int // servo angle
	PenDownAt int // servo angle
	Tool      int
	Queued    int
	Msg       string
}

// State returns the current state. Call it from the goroutine that calls Poll.
func (c *Controller) State() State {
	return State{
		X:       float32(c.ex.Pos(0))/config.StepsPerMM[0] - c.off[0],
		Y:       float32(c.ex.Pos(1))/config.StepsPerMM[1] - c.off[1],
		PenDown: c.penDown, Homed: c.homed, Motors: c.motors, Busy: !c.idle() || c.wait != waitNone,
		Alarm: c.alarm, Paused: c.paused, Lines: c.lineNo, Progress: c.progress,
		Speed: int(c.set.Speed), PenUp: int(c.set.PenUp), PenDownAt: int(c.set.PenDown),
		Tool: c.tool, Queued: c.pl.Len(), Msg: c.msg,
	}
}
