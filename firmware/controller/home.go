package controller

import (
	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/gcode"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
)

// homing is the state of a G28 line.
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
	c.setMotors(true)
	c.setHomed(false)
	c.wait = waitHome
}

// channels returns the executor channels of an axis as a bit mask.
func channels(ax int) uint8 {
	if ax == config.Y {
		return 1<<stepgen.ChY1 | 1<<stepgen.ChY2
	}
	return 1 << stepgen.ChX
}

// missing names the switches of mask that did not trigger.
func missing(mask, hits uint8) string {
	s := ""
	for ch, name := range [3]string{"X", "Y1", "Y2"} {
		if mask&(1<<ch) != 0 && hits&(1<<ch) == 0 {
			if s != "" {
				s += ", "
			}
			s += name
		}
	}
	return s
}

// anyEndstop tells if a switch of the axis is pressed.
func (c *Controller) anyEndstop(ax int) bool {
	if ax == config.Y {
		return c.hal.Endstop(stepgen.ChY1) || c.hal.Endstop(stepgen.ChY2)
	}
	return c.hal.Endstop(stepgen.ChX)
}

// stepHome runs the next homing phase when the machine is idle.
// It returns true when homing is complete, with an error text on failure.
//
// Y homes both Y motors at the same time. Each side stops at its own switch,
// so the beam is square to the rails after homing.
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
	case 1: // Fast pass to the switches.
		c.pushHome(ax, config.HomeFastFeed, config.Travel[ax]*1.2)
		c.home.phase = 2
	case 2:
		if h := c.ex.HomeHits(); h&mask != mask {
			return true, "homing failed: no " + missing(mask, h) + " endstop"
		}
		c.pushMove(ax, config.HomeBackoff, config.HomeFastFeed)
		c.home.phase = 3
	case 3: // Slow pass for a repeatable position.
		c.pushHome(ax, config.HomeSlowFeed, config.HomeBackoff*2)
		c.home.phase = 4
	case 4:
		if h := c.ex.HomeHits(); h&mask != mask {
			return true, "homing failed: " + missing(mask, h) + " endstop does not trigger again"
		}
		if ax == config.Y && config.Y2HomeOffsetMM != 0 {
			c.pushTrim(config.Y2HomeOffsetMM, config.HomeSlowFeed)
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

// pushHome queues a move to the minimum end that stops on the endstops.
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

// pushMove queues a constant-speed move of one axis to the positive side.
// A Y move also moves Y2.
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

// pushTrim queues a move of Y2 only. Positive mm moves away from the switch.
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
