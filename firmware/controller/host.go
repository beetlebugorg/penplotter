package controller

import (
	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// Status implements ui.Host.
func (c *Controller) Status() ui.Status {
	up, dn := c.PenAngles()
	s := ui.Status{
		X:        float32(c.ex.Pos(0))/config.StepsPerMM[0] - c.off[0],
		Y:        float32(c.ex.Pos(1))/config.StepsPerMM[1] - c.off[1],
		PenDown:  c.penDown,
		Homed:    c.homed,
		Motors:   c.motors,
		Busy:     !c.idle(),
		Alarm:    c.alarm,
		Lines:    c.lines,
		Progress: c.progress,
		Speed:    c.speed,
		PenUp:    up,
		PenDn:    dn,
		Msg:      c.msg,
		ES: [3]bool{c.hal.Endstop(stepgen.ChX), c.hal.Endstop(stepgen.ChY1),
			c.hal.Endstop(stepgen.ChY2)},
		Skew: float32(c.ex.Pos(stepgen.ChY2)-c.ex.Pos(stepgen.ChY1)) / config.StepsPerMMY,
		Tool: c.set.Tool,
		Net:  c.netShort(),
	}
	s.Prompt, s.PromptSub = c.prompt()
	switch {
	case c.alarm:
		s.State = "ALARM"
	case c.wait == waitHome:
		s.State = "HOME"
	case c.wait == waitTool:
		s.State = "PEN"
	case s.Busy:
		s.State = "BUSY"
	default:
		s.State = "IDLE"
	}
	return s
}

// Snapshot returns the status for a host program such as the simulator.
func (c *Controller) Snapshot() ui.Status { return c.Status() }

// Command implements ui.Host. It queues a line from the UI.
func (c *Controller) Command(line string) bool {
	if c.inLen == len(c.internal) {
		return false
	}
	c.internal[(c.inHead+c.inLen)%len(c.internal)] = line
	c.inLen++
	return true
}

// Jog implements ui.Host. It queues a relative move of one axis.
func (c *Controller) Jog(axis int, mm float32) bool {
	if c.alarm || c.wait != waitNone || c.pl.Space() < 3 {
		return false
	}
	t := [2]float32{c.machine(0), c.machine(1)}
	t[axis] += mm
	c.moveTo(t, config.JogFeed)
	return true
}

// SetPenAngles implements ui.Host. The angles are saved when the machine is idle.
func (c *Controller) SetPenAngles(up, down int) {
	c.penUp.Store(int32(up))
	c.penDn.Store(int32(down))
	c.markDirty()
}

// SetSpeed implements ui.Host.
func (c *Controller) SetSpeed(pct int) {
	c.speed = pct
	c.markDirty()
}

// pollUI reads the knob and draws the LCD.
func (c *Controller) pollUI() {
	now := c.hal.NowMicros()
	redraw := false
	if d := c.hal.Encoder(); d != 0 {
		c.ui.Turn(d)
		redraw = true
	}
	btn := c.hal.Button()
	switch {
	case btn && !c.btnDown:
		c.btnDown, c.btnSince, c.longDone = true, now, false
	case btn && !c.longDone && now-c.btnSince > config.LongPressMs*1000:
		c.longDone = true
		c.ui.LongPress()
		c.hal.Beep(60)
		redraw = true
	case !btn && c.btnDown:
		c.btnDown = false
		if !c.longDone && now-c.btnSince > 20000 {
			c.msg = ""
			c.ui.Click()
			c.hal.Beep(10)
			redraw = true
		}
	}
	if redraw || now-c.lastDraw > config.UIRefreshMs*1000 {
		c.ui.Draw()
		c.lastDraw = now
	}
	c.hal.Display().Flush(&c.ui.FB)
}

// Queued returns the number of blocks in the planner.
func (c *Controller) Queued() int { return c.pl.Len() }

// netShort describes the network for the status screen: "" with no network.
func (c *Controller) netShort() string {
	if c.net == nil {
		return ""
	}
	st := c.net.Status()
	if st.State == "up" {
		return IPString(st.IP)
	}
	if !c.set.WiFiOn || c.set.SSID == "" {
		return "wifi off"
	}
	return "wifi " + st.State
}

// WiFi implements ui.Host: the network name, the host name, and the network state.
func (c *Controller) WiFi() (ssid, host, state string, has bool) {
	if c.net == nil {
		return "", "", "", false
	}
	return c.set.SSID, c.set.Hostname, c.netLine()[6:], true
}
