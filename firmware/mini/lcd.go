package mini

import "github.com/beetlebugorg/penplotter/firmware/config"

// The knob menu: turn to choose, press to run. The menu line is the 4th LCD line.
var menuItems = [...]string{"Home", "Pen up/down", "Pause/resume", "Motors off", "Pen up +1",
	"Pen up -1", "Pen down +1", "Pen down -1", "Speed +10%", "Speed -10%", "Save settings"}

// pollKnob reads the knob. A long press (0.8 s) stops the machine.
func (c *Controller) pollKnob() {
	now := c.b.NowMicros()
	if d := c.b.Encoder(); d != 0 {
		c.menu = (c.menu + d%len(menuItems) + len(menuItems)) % len(menuItems)
	}
	btn := c.b.Button()
	switch {
	case btn && !c.btnDown:
		c.btnDown, c.btnSince, c.longDone = true, now, false
	case btn && !c.longDone && now-c.btnSince > config.LongPressMs*1000:
		c.longDone = true
		if !c.idle() || c.wait != waitNone {
			c.emergency("knob")
		}
	case !btn && c.btnDown:
		c.btnDown = false
		if !c.longDone {
			c.click()
		}
	}
}

func (c *Controller) click() {
	c.b.Beep(20)
	if c.wait == waitPen {
		c.finishWait()
		return
	}
	switch c.menu {
	case 0:
		if c.idle() && c.wait == waitNone && !c.ready {
			c.line = [96]byte{'G', '2', '8'}
			c.n, c.ready = 3, true
			c.local = true
		}
	case 1:
		if c.idle() {
			c.setPen(!c.penDown)
		}
	case 2:
		c.paused = !c.paused
		if c.paused {
			c.msg = "Paused"
		} else {
			c.msg = "Ready"
		}
	case 3:
		if c.idle() {
			c.setMotors(false)
		}
	case 4, 5, 6, 7:
		d := uint8(1)
		v := &c.set.PenUp
		if c.menu >= 6 {
			v = &c.set.PenDown
		}
		if c.menu == 5 || c.menu == 7 {
			if *v > 0 {
				*v -= d
			}
		} else if *v < 180 {
			*v += d
		}
		if c.idle() {
			c.pl.AddPen(uint16(*v), msTicks(config.PenSettleMs), c.lineNo)
			c.penDown = c.menu >= 6
		}
		c.saveLater()
	case 8:
		if c.set.Speed <= 190 {
			c.set.Speed += 10
		}
		c.saveLater()
	case 9:
		if c.set.Speed >= 20 {
			c.set.Speed -= 10
		}
		c.saveLater()
	case 10:
		c.save()
		c.msg = "Saved"
	}
}

// draw writes one LCD line every UIRefreshMs/4, so the main loop stays short.
func (c *Controller) draw() {
	now := c.b.NowMicros()
	if now-c.lastDraw < config.UIRefreshMs*1000/4 {
		return
	}
	c.lastDraw = now
	var s string
	switch c.drawRow {
	case 0:
		st := "Idle"
		switch {
		case c.alarm:
			st = "ALARM"
		case c.wait == waitHome:
			st = "Homing"
		case c.wait == waitPen:
			st = "Pen T" + itoa(c.tool)
		case c.paused:
			st = "Paused"
		case !c.idle():
			st = "Run " + itoa(c.progress) + "%"
		}
		pen := "up"
		if c.penDown {
			pen = "dn"
		}
		s = pad(st, 10) + "Pen " + pen
	case 1:
		x := float32(c.ex.Pos(0))/config.StepsPerMM[0] - c.off[0]
		y := float32(c.ex.Pos(1))/config.StepsPerMM[1] - c.off[1]
		s = pad("X"+fixed(x, 1), 8) + "Y" + fixed(y, 1)
	case 2:
		s = c.msg
		if c.wait == waitPen {
			s = "Press the knob"
		}
	case 3:
		s = ">" + menuItems[c.menu]
		switch c.menu {
		case 4, 5:
			s += " " + itoa(int(c.set.PenUp))
		case 6, 7:
			s += " " + itoa(int(c.set.PenDown))
		case 8, 9:
			s = ">Speed " + itoa(int(c.set.Speed)) + "%" + menuItems[c.menu][5:]
		}
	}
	c.b.Text(c.drawRow, pad(s, 16))
	c.drawRow = (c.drawRow + 1) % 4
}
