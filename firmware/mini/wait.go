package mini

import (
	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/gcode"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
)

// finishLine sends the reply of a line that waited (an arc, M400, G28, M6).
func (c *Controller) finishLine() {
	out := c.pending
	c.pending = ""
	if out == "" {
		out = "ok"
	} else if out[0] != '!' && (len(out) < 5 || out[:5] != "error") {
		out += "\nok"
	}
	c.done(out)
}

func (c *Controller) finishWait() {
	c.wait = waitNone
	if c.offAfter {
		c.offAfter = false
		c.setMotors(false)
	}
	c.msg = "Ready"
	c.finishLine()
}

// runWait advances the current wait.
func (c *Controller) runWait() {
	switch c.wait {
	case waitIdle:
		if c.idle() {
			c.finishWait()
		}
	case waitHome:
		if done, err := c.stepHome(); done {
			if err != "" {
				c.wait = waitNone
				c.pending = ""
				c.alarm = true
				c.msg = "Home failed"
				c.done("error:" + err)
				return
			}
			c.finishWait()
		}
	case waitPen:
		// The knob (pollKnob) or M108 (readSerial) ends this wait.
	}
}

// Homing: each axis goes to its switch fast, backs off, and goes to it again slowly.
// Y homes Y1 and Y2 together. Each side stops at its own switch, so the beam ends square.
type homing struct {
	axes  [2]int
	n, i  int
	phase int
}

func (c *Controller) startHome(l *gcode.Line) {
	c.home = homing{}
	if l.Has('X') {
		c.home.axes[c.home.n] = config.X
		c.home.n++
	}
	if l.Has('Y') {
		c.home.axes[c.home.n] = config.Y
		c.home.n++
	}
	if c.home.n == 0 {
		c.home.axes = [2]int{config.X, config.Y}
		c.home.n = 2
	}
	c.setPen(false)
	c.motorsOn()
	c.homed = false
	c.wait = waitHome
	c.msg = "Homing"
}

func channels(ax int) uint8 {
	if ax == config.Y {
		return 1<<stepgen.ChY1 | 1<<stepgen.ChY2
	}
	return 1 << stepgen.ChX
}

func (c *Controller) anyEndstop(ax int) bool {
	if ax == config.Y {
		return c.b.Endstop(stepgen.ChY1) || c.b.Endstop(stepgen.ChY2)
	}
	return c.b.Endstop(stepgen.ChX)
}

func (c *Controller) stepHome() (bool, string) {
	if !c.idle() {
		return false, ""
	}
	ax := c.home.axes[c.home.i]
	mask := channels(ax)
	switch c.home.phase {
	case 0: // Move off the switches if one is pressed.
		if c.anyEndstop(ax) {
			c.pushMove(ax, config.HomeClear, config.HomeFastFeed)
		}
		c.home.phase = 1
	case 1:
		c.pushHome(ax, config.HomeFastFeed, config.Travel[ax]*1.2)
		c.home.phase = 2
	case 2:
		if c.ex.HomeHits()&mask != mask {
			return true, "homing failed: an endstop did not trigger"
		}
		c.pushMove(ax, config.HomeBackoff, config.HomeFastFeed)
		c.home.phase = 3
	case 3:
		c.pushHome(ax, config.HomeSlowFeed, config.HomeBackoff*2)
		c.home.phase = 4
	case 4:
		if c.ex.HomeHits()&mask != mask {
			return true, "homing failed: an endstop did not trigger again"
		}
		if ax == config.Y && c.set.Y2TrimUM != 0 {
			c.pushTrim(float32(c.set.Y2TrimUM)/1000, config.HomeSlowFeed)
		}
		c.home.phase = 5
	case 5:
		c.ex.SetPos(stepgen.ChX+ax, 0)
		c.ex.SetLimitFloor(stepgen.ChX+ax, int32(config.StepsPerMM[ax]), true)
		if ax == config.Y {
			c.ex.SetPos(stepgen.ChY2, 0)
			c.ex.SetLimitFloor(stepgen.ChY2, int32(config.StepsPerMMY), true)
		}
		c.off[ax] = 0
		c.pl.Pos = [2]int32{c.ex.Pos(0), c.ex.Pos(1)}
		c.home.phase = 0
		c.home.i++
		if c.home.i == c.home.n {
			c.homed = true
			return true, ""
		}
	}
	c.pl.Pos = [2]int32{c.ex.Pos(0), c.ex.Pos(1)}
	return false, ""
}

func (c *Controller) pushHome(ax int, feed, maxMM float32) {
	spm := config.StepsPerMM[ax]
	c.ex.Q.Push(stepgen.Segment{
		Kind:  stepgen.Home,
		Axis:  uint8(ax),
		Dir:   1 << ax,
		Ticks: uint32(config.TickHz / (feed * spm)),
		Max:   uint32(maxMM * spm),
		Line:  c.lineNo,
	})
}

func (c *Controller) pushMove(ax int, mm, feed float32) {
	spm := config.StepsPerMM[ax]
	n := uint32(mm * spm)
	var s stepgen.Segment
	s.Kind = stepgen.Move
	s.Steps[ax] = uint16(n)
	s.Ticks = uint32(float32(n) * config.TickHz / (feed * spm))
	s.Line = c.lineNo
	c.ex.Q.Push(s)
}

func (c *Controller) pushTrim(mm, feed float32) {
	var s stepgen.Segment
	s.Kind = stepgen.Trim
	if mm < 0 {
		mm = -mm
		s.Dir = 1 << stepgen.ChY2
	}
	n := uint32(mm*config.StepsPerMMY + 0.5)
	s.Steps[1] = uint16(n)
	s.Ticks = uint32(float32(n)*config.TickHz/(feed*config.StepsPerMMY)) + 1
	s.Line = c.lineNo
	c.ex.Q.Push(s)
}
