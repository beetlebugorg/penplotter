package controller

import (
	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/settings"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// Changer is an automatic pen changer: for example a rack of 16 pens, a Z axis on a 4th
// driver, a gripper servo and a Z endstop. No pins are reserved for it. The
// firmware has no changer yet. With no changer, M6 asks the user to change the pen.
type Changer interface {
	// Start begins a change from pen 'from' to pen 'to'. The pen is up and the
	// carriage stands at the park position.
	Start(from, to int)
	// Poll runs the change. It returns true when the change ends, with an error text
	// on failure.
	Poll() (done bool, err string)
}

// toolChange is the state of an M6 line.
type toolChange struct {
	active    bool
	phase     int
	to        int
	confirmed bool
	beepAt    uint64
}

// promptBeepUs is the time between beeps while the pen change waits for the user.
const promptBeepUs = 20_000_000

// jobInfo names the job of the network API.
type jobInfo struct {
	port  int
	name  string
	total int
}

// selectTool handles a T word: it selects the pen for the next M6.
func (c *Controller) selectTool(t int) string {
	if t < 0 || t >= settings.NumPens {
		return "!no pen T" + ui.Itoa(t) + " (T0 to T15)"
	}
	c.nextTool = t
	return ""
}

// startToolChange handles M6. It changes to the pen of the last T word.
func (c *Controller) startToolChange() string {
	to := c.nextTool
	if to < 0 {
		return "!M6 needs a T word first (T0 to T15)"
	}
	if to == c.set.Tool {
		return "echo:pen T" + ui.Itoa(to) + " is in the holder"
	}
	if c.set.Changer == settings.ChangerAuto && c.changer == nil {
		return "!no automatic pen changer on this board"
	}
	c.tc = toolChange{active: true, to: to}
	c.wait = waitTool
	return ""
}

// stepTool runs the pen change. It returns true when it ends, with an error text on failure.
func (c *Controller) stepTool() (bool, string) {
	switch c.tc.phase {
	case 0: // Lift the pen and go to the park position.
		c.setPen(false)
		if c.homed {
			c.moveTo([2]float32{float32(c.set.ParkX), float32(c.set.ParkY)}, config.RapidFeed)
		}
		c.tc.phase = 1
	case 1:
		if !c.idle() {
			return false, ""
		}
		if c.set.Changer == settings.ChangerAuto {
			c.changer.Start(c.set.Tool, c.tc.to)
			c.tc.phase = 3
			return false, ""
		}
		c.tc.phase = 2
		c.tc.beepAt = 0
	case 2: // Wait for the user: a click of the knob, or M108 from a host.
		now := c.hal.NowMicros()
		if now >= c.tc.beepAt {
			c.hal.Beep(300)
			c.tc.beepAt = now + promptBeepUs
		}
		if !c.tc.confirmed {
			return false, ""
		}
		c.finishTool()
		return true, ""
	case 3: // Automatic changer.
		done, err := c.changer.Poll()
		if !done {
			return false, ""
		}
		if err != "" {
			c.tc = toolChange{}
			return true, "pen change failed: " + err
		}
		c.finishTool()
		return true, ""
	}
	return false, ""
}

func (c *Controller) finishTool() {
	c.set.Tool = c.tc.to
	c.tc = toolChange{}
	c.markDirty()
}

// Confirm implements ui.Host: the user has loaded the pen. M108 does the same.
func (c *Controller) Confirm() {
	if c.tc.active && c.tc.phase == 2 {
		c.tc.confirmed = true
	}
}

// prompt returns the pen change text for the LCD, or "" if no change waits.
func (c *Controller) prompt() (string, string) {
	if !c.tc.active || c.tc.phase != 2 {
		return "", ""
	}
	p := c.set.Pens[c.tc.to]
	return "Load pen T" + ui.Itoa(c.tc.to), p.Name
}

// PenName implements ui.Host.
func (c *Controller) PenName(i int) string {
	if i < 0 || i >= settings.NumPens {
		return ""
	}
	return c.set.Pens[i].Name
}

// Pens returns the pen table. Call it from the controller goroutine.
func (c *Controller) Pens() [settings.NumPens]settings.Pen { return c.set.Pens }

// SetPens changes the pen table and saves it when the machine is idle.
// Call it from the controller goroutine.
func (c *Controller) SetPens(p [settings.NumPens]settings.Pen) {
	for i := range p {
		if len(p[i].Name) > settings.PenNameLen {
			p[i].Name = p[i].Name[:settings.PenNameLen]
		}
		p[i].Color &= 0xFFFFFF
	}
	c.set.Pens = p
	c.markDirty()
}

// SetTool tells the controller which pen is in the holder (the LCD Pens menu).
func (c *Controller) SetTool(t int) {
	if t >= 0 && t < settings.NumPens && t != c.set.Tool {
		c.set.Tool = t
		c.nextTool = t
		c.markDirty()
	}
}

// StartJob opens a port for a network job and gives it the machine.
// It returns the port id, or -1 and a reason. Call it from the controller goroutine.
func (c *Controller) StartJob(name string, total int, p Port) (int, string) {
	if c.alarm {
		return -1, "alarm, send M999"
	}
	if c.owner >= 0 {
		return -1, c.ports[c.owner].name + " has the machine"
	}
	id := c.AddPort(name, p)
	if id < 0 {
		return -1, "too many connections"
	}
	c.owner = id
	c.ownerLines = 0
	c.ownerLast = c.hal.NowMicros()
	c.job = jobInfo{port: id, name: name, total: total}
	return id, ""
}
