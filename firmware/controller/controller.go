package controller

import (
	"sync/atomic"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/gcode"
	"github.com/beetlebugorg/penplotter/firmware/planner"
	"github.com/beetlebugorg/penplotter/firmware/settings"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// What a line waits for before the controller sends "ok".
type waitKind uint8

const (
	waitNone waitKind = iota
	waitIdle
	waitHome
	waitArc
	waitTool
)

// After a wait for idle, the controller can do one more thing.
type afterKind uint8

const (
	afterNone afterKind = iota
	afterMotorsOff
	afterSave
)

const lineMax = 128

// Controller is the main loop state.
type Controller struct {
	hal HAL
	ex  *stepgen.Executor
	pl  planner.Planner
	pr  planner.Prep
	ui  *ui.UI

	// G-code state.
	abs     bool
	scale   float32 // mm per unit
	feed    float32 // mm/s for G1
	motion  int     // modal motion: 0 or 1
	off     [2]float32
	penDown bool
	homed   bool
	motors  bool
	alarm   bool
	speed   int // override in percent
	penUp   atomic.Int32
	penDn   atomic.Int32

	// Host ports. Port 0 is the USB serial port of the board.
	ports      [MaxPorts]portState
	rr         int    // the port that dispatch looks at first
	owner      int    // the port that owns the machine, or -1
	ownerLast  uint64 // time of the last line of the owner
	ownerLines uint32
	lineNo     uint32
	lines      uint32
	progress   int
	msg        string

	// Lines from the UI.
	internal [8]string
	inHead   int
	inLen    int

	// The line that waits.
	wait     waitKind
	after    afterKind
	waitPort int // the port that gets the answer, or -1 for the UI
	arc      gcode.Arc
	arcSpeed float32
	home     homing

	// Saved settings, the pen table and the network.
	set       settings.Settings
	store     settings.Store
	net       Network
	changer   Changer
	saveAt    uint64 // time of the next automatic save, or 0
	aborting  bool   // an emergency stop waits for the step interrupt
	pubAlways bool   // publish the API state with no network
	nextTool  int    // the pen of the last T word, or -1
	tc        toolChange
	job       jobInfo
	mb        mailbox
	pub       published

	// UI timing.
	lastDraw uint64
	btnDown  bool
	btnSince uint64
	longDone bool
}

// New makes a controller with no settings store, no network and no pen changer.
// ex is the executor that the board runs from its step timer.
func New(h HAL, ex *stepgen.Executor) *Controller { return NewWith(h, ex, Options{}) }

// NewWith makes a controller with the optional parts of a board.
func NewWith(h HAL, ex *stepgen.Executor, o Options) *Controller {
	c := &Controller{hal: h, ex: ex, owner: -1, waitPort: -1, nextTool: -1,
		store: o.Store, net: o.Net, changer: o.Changer}
	ex.HardLimits = config.HardLimits
	c.job.port = -1
	c.ports[USB] = portState{p: halPort{h}, name: "usb", open: true}
	c.pl.JunctionDev = config.JunctionDev
	c.pr = planner.Prep{P: &c.pl, Q: &ex.Q, TickHz: config.TickHz, SegTicks: config.SegmentTick, MinSpeed: config.MinSpeed}
	c.abs = true
	c.scale = 1
	c.feed = config.DefaultFeed
	c.speed = 100
	c.progress = -1
	c.penUp.Store(config.PenUpDeg)
	c.penDn.Store(config.PenDownDeg)
	c.ui = ui.New(c)
	note := c.loadSettings()
	c.applySettings()
	// Lift the pen at power on.
	c.pl.AddPen(uint16(c.set.PenUp), msTicks(config.PenSettleMs), 0)
	c.hal.WriteSerial("start\necho:" + note + "\n")
	return c
}

func msTicks(ms uint32) uint32 { return ms * (config.TickHz / 1000) }

// UI returns the user interface.
func (c *Controller) UI() *ui.UI { return c.ui }

// PenAngles returns the servo angles for pen up and pen down. It is safe from other goroutines.
func (c *Controller) PenAngles() (up, down int) {
	return int(c.penUp.Load()), int(c.penDn.Load())
}

// Poll runs one pass of the main loop.
func (c *Controller) Poll() {
	c.runMailbox()
	c.readPorts()
	if c.aborting {
		// Wait for the step interrupt to drop its segments, then take its position.
		if c.ex.AbortDone() {
			c.pl.Pos = [2]int32{c.ex.Pos(0), c.ex.Pos(1)}
			c.aborting = false
		}
	} else {
		c.runWait()
		c.dispatch()
		if h := c.ex.LimitHits(); h != 0 {
			c.emergency("hard limit " + missing(h, 0))
		}
		c.pr.Fill()
	}
	c.pollUI()
	c.publish()
	c.hal.Poll()
}

// reply sends text to a port. Port -1 is the UI: it shows errors on the LCD.
func (c *Controller) reply(port int, s string) {
	if port >= 0 && port < MaxPorts && c.ports[port].open {
		c.ports[port].p.Write(s + "\n")
	} else if port < 0 && len(s) > 5 && s[:5] == "error" {
		c.msg = s[6:]
		c.hal.Beep(200)
	}
}

// exec runs one G-code line from a port (-1 is the UI).
func (c *Controller) exec(s string, port int) {
	serial := port >= 0
	if serial && port == c.owner {
		c.lines++
	}
	t := trim(s)
	if t == "" {
		c.reply(port, "ok")
		return
	}
	if len(t) >= 4 && (t[:4] == "M117" || t[:4] == "m117") {
		c.msg = trim(t[4:])
		c.reply(port, "ok")
		return
	}
	before := c.wait
	if r, ok := c.textCommand(t); ok {
		if r != "" && r[0] == '!' {
			c.reply(port, "error:"+r[1:])
			return
		}
		if r != "" {
			c.reply(port, r)
		}
		if before == waitNone && c.wait != waitNone {
			c.waitPort = port
			return
		}
		c.reply(port, "ok")
		return
	}
	var l gcode.Line
	if err := gcode.Parse([]byte(t), &l); err != nil {
		c.reply(port, "error:"+err.Error())
		return
	}
	if c.alarm && !(l.Has('M') && (isM(&l, 999) || isM(&l, 114) || isM(&l, 119) || isM(&l, 115) ||
		isM(&l, 105) || isM(&l, 503) || isM(&l, 112))) {
		c.reply(port, "error:alarm, send M999")
		return
	}
	msg := c.run(&l)
	if before == waitNone && c.wait != waitNone {
		c.waitPort = port
		return
	}
	if msg != "" && msg[0] == '!' {
		c.reply(port, "error:"+msg[1:])
		return
	}
	if msg != "" && serial {
		c.reply(port, msg)
	}
	c.reply(port, "ok")
}

func isM(l *gcode.Line, code int) bool {
	v, _ := l.Get('M')
	return int(v) == code
}

// run executes the words of a line. It returns text for the host.
// Text that starts with '!' is an error.
func (c *Controller) run(l *gcode.Line) string {
	if f, ok := l.Get('F'); ok && f > 0 {
		c.feed = f * c.scale / 60
	}
	motion := -1
	out := ""
	for i := 0; i < l.N; i++ {
		w := l.W[i]
		code := int(w.V)
		frac := w.V - float32(code)
		if frac != 0 {
			continue // G-codes such as G92.1 are not supported
		}
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
				c.pl.AddDwell(msTicks(uint32(ms)), c.lineNo)
				return ""
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
				if !l.Has('X') && !l.Has('Y') {
					c.off = [2]float32{c.machine(0), c.machine(1)}
				}
				return ""
			case 17, 18, 19, 40, 49, 80, 94:
				// Plane, cutter compensation and feed modes: accepted, no effect.
			default:
				out = "echo:ignored G" + ui.Itoa(code)
			}
		case 'M':
			if code == 6 {
				if t, ok := l.Get('T'); ok {
					if r := c.selectTool(int(t)); r != "" {
						return r
					}
				}
			}
			return c.runM(code, l)
		case 'T':
			if r := c.selectTool(code); r != "" {
				return r
			}
		}
	}
	if motion < 0 && (l.Has('X') || l.Has('Y') || l.Has('Z')) {
		motion = c.motion
	}
	switch motion {
	case 0, 1:
		c.motion = motion
		if z, ok := l.Get('Z'); ok {
			c.setPen(z <= 0)
		}
		if l.Has('X') || l.Has('Y') {
			c.moveTo(c.target(l), c.moveSpeed(motion))
		}
	case 2, 3:
		return c.startArc(l, motion == 2)
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
		return c.startToolChange()
	case 108:
		c.Confirm()
	case 17:
		c.setMotors(true)
	case 18, 84:
		c.wait, c.after = waitIdle, afterMotorsOff
	case 73:
		if p, ok := l.Get('P'); ok {
			c.progress = int(p)
		}
	case 105:
		return "T:0 /0 B:0 /0"
	case 110:
	case 112:
		c.emergency("M112")
	case 114:
		return c.position()
	case 115:
		return "FIRMWARE_NAME:PenPlotter " + config.Version + " (TinyGo) MACHINE_TYPE:CR-10 V3 pen plotter"
	case 119:
		return "x_min: " + trig(c.hal.Endstop(stepgen.ChX)) + "\ny1_min: " + trig(c.hal.Endstop(stepgen.ChY1)) +
			"\ny2_min: " + trig(c.hal.Endstop(stepgen.ChY2))
	case 280:
		if s, ok := l.Get('S'); ok {
			c.setMotors(true)
			c.pl.AddPen(clampAngle(s), msTicks(config.PenSettleMs), c.lineNo)
		}
	case 281:
		up, dn := c.PenAngles()
		if v, ok := l.Get('U'); ok {
			up = int(clampAngle(v))
		}
		if v, ok := l.Get('D'); ok {
			dn = int(clampAngle(v))
		}
		c.SetPenAngles(up, dn)
		c.ui.SyncSettings(up, dn, c.speed)
		return "pen up:" + ui.Itoa(up) + " down:" + ui.Itoa(dn)
	case 400:
		c.wait = waitIdle
	case 999:
		c.alarm = false
		c.msg = ""
	case 82, 83, 104, 106, 107, 109, 140, 190:
		// Printer codes from generic G-code: accepted, no effect.
	default:
		return "echo:ignored M" + ui.Itoa(code)
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
	return uint16(v + 0.5)
}

// machine returns the machine position of an axis in mm, at the end of the queued moves.
func (c *Controller) machine(axis int) float32 {
	return float32(c.pl.Pos[axis]) / config.StepsPerMM[axis]
}

// target returns the machine position of the X and Y words.
func (c *Controller) target(l *gcode.Line) [2]float32 {
	t := [2]float32{c.machine(0), c.machine(1)}
	for a, L := range [2]byte{'X', 'Y'} {
		if v, ok := l.Get(L); ok {
			if c.abs {
				t[a] = v*c.scale + c.off[a]
			} else {
				t[a] += v * c.scale
			}
		}
	}
	return t
}

func (c *Controller) moveSpeed(motion int) float32 {
	v := c.feed
	if motion == 0 {
		v = config.RapidFeed
	}
	v = v * float32(c.speed) / 100
	if v > config.MaxFeed {
		v = config.MaxFeed
	}
	if v < config.MinSpeed {
		v = config.MinSpeed
	}
	return v
}

// moveTo queues a straight move to machine position t (mm).
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
	c.setMotors(true)
	c.pl.AddMove(steps, speed, config.Accel, config.StepsPerMM, c.lineNo)
}

func (c *Controller) setPen(down bool) {
	if down == c.penDown {
		return
	}
	c.penDown = down
	a := c.penUp.Load()
	if down {
		a = c.penDn.Load()
	}
	c.setMotors(true)
	c.pl.AddPen(uint16(a), msTicks(config.PenSettleMs), c.lineNo)
}

func (c *Controller) setMotors(on bool) {
	if on != c.motors {
		c.motors = on
		c.hal.SetMotors(on)
	}
	if !on {
		c.setHomed(false)
	}
}

// setHomed sets the homed state and the hard limit floors: after homing, a switch that
// closes within 1 mm of home is the home position, not a crash.
func (c *Controller) setHomed(h bool) {
	c.homed = h
	for ch := 0; ch < stepgen.NumCh; ch++ {
		ax := min(ch, 1)
		c.ex.SetLimitFloor(ch, int32(config.StepsPerMM[ax]), h)
	}
}

// startArc starts a G2/G3 line. The points go to the planner in later passes.
func (c *Controller) startArc(l *gcode.Line, cw bool) string {
	s := [2]float32{c.machine(0) - c.off[0], c.machine(1) - c.off[1]}
	e := c.target(l)
	e[0] -= c.off[0]
	e[1] -= c.off[1]
	i, _ := l.Get('I')
	j, _ := l.Get('J')
	r, _ := l.Get('R')
	a, ok := gcode.NewArc(s[0], s[1], e[0], e[1], i*c.scale, j*c.scale, r*c.scale, cw, config.ArcMaxSeg, config.ArcTolerance)
	if !ok {
		return "!bad arc"
	}
	if z, ok := l.Get('Z'); ok {
		c.setPen(z <= 0)
	}
	c.motion = 1
	c.arc = a
	c.arcSpeed = c.moveSpeed(1)
	c.wait = waitArc
	return ""
}

// idle tells if all queued motion is complete.
func (c *Controller) idle() bool {
	return c.pl.Len() == 0 && !c.pr.Busy() && c.ex.Idle()
}

// runWait continues the line that waits.
func (c *Controller) runWait() {
	switch c.wait {
	case waitNone:
		return
	case waitArc:
		for c.pl.Space() > 1 {
			x, y, ok := c.arc.Next()
			if !ok {
				c.finishWait("")
				return
			}
			c.moveTo([2]float32{x + c.off[0], y + c.off[1]}, c.arcSpeed)
		}
	case waitIdle:
		if !c.idle() {
			return
		}
		r := ""
		switch c.after {
		case afterMotorsOff:
			c.setMotors(false)
		case afterSave:
			r = c.saveSettings()
		}
		c.after = afterNone
		c.finishWait(r)
	case waitTool:
		if done, err := c.stepTool(); done {
			if err != "" {
				c.alarm = true
				c.finishWait("!" + err)
				return
			}
			c.finishWait("")
		}
	case waitHome:
		if done, err := c.stepHome(); done {
			if err != "" {
				c.alarm = true
				c.finishWait("!" + err)
				return
			}
			c.finishWait("")
		}
	}
}

func (c *Controller) finishWait(msg string) {
	c.wait = waitNone
	p := c.waitPort
	c.waitPort = -1
	if msg != "" && msg[0] == '!' {
		c.reply(p, "error:"+msg[1:])
		return
	}
	c.reply(p, "ok")
}

// emergency stops all motion at once.
func (c *Controller) emergency(why string) {
	c.ex.Abort()
	c.pl.Clear()
	c.pr.Reset()
	if c.wait != waitNone {
		c.finishWait("!stopped")
	}
	c.wait = waitNone
	c.tc = toolChange{}
	c.inLen = 0
	for i := range c.ports {
		c.ports[i].n, c.ports[i].ready, c.ports[i].comment = 0, false, false
	}
	c.setMotors(false)
	c.alarm = true
	c.msg = "STOP: " + why
	for i := range c.ports {
		if c.ports[i].open {
			c.ports[i].p.Write("!! " + why + "\n")
		}
	}
	c.aborting = true
}

func (c *Controller) position() string {
	x := float32(c.pl.Pos[0])/config.StepsPerMM[0] - c.off[0]
	y := float32(c.pl.Pos[1])/config.StepsPerMM[1] - c.off[1]
	return "X:" + ui.Fixed(x/c.scale, 3) + " Y:" + ui.Fixed(y/c.scale, 3) + " Z:0.000 Count X:" +
		ui.Itoa(int(c.ex.Pos(stepgen.ChX))) + " Y:" + ui.Itoa(int(c.ex.Pos(stepgen.ChY1))) +
		" Y2:" + ui.Itoa(int(c.ex.Pos(stepgen.ChY2)))
}

// statusLine returns the Grbl-style status line for '?'.
func (c *Controller) statusLine() string {
	st := "Idle"
	switch {
	case c.alarm:
		st = "Alarm"
	case c.wait == waitHome:
		st = "Home"
	case !c.idle():
		st = "Run"
	}
	x := float32(c.ex.Pos(0)) / config.StepsPerMM[0]
	y := float32(c.ex.Pos(1)) / config.StepsPerMM[1]
	return "<" + st + "|MPos:" + ui.Fixed(x, 3) + "," + ui.Fixed(y, 3) + ",0.000|>\n"
}

func trim(s string) string {
	i, j := 0, len(s)
	for i < j && (s[i] == ' ' || s[i] == '\t' || s[i] == '\r' || s[i] == '\n') {
		i++
	}
	for j > i && (s[j-1] == ' ' || s[j-1] == '\t' || s[j-1] == '\r' || s[j-1] == '\n') {
		j--
	}
	return s[i:j]
}
