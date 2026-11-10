package controller

import (
	"sync"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/settings"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// Network is the Wi-Fi of a board. The Pico H and the tests have none.
type Network interface {
	// Status returns the state of the network for the LCD, M552 and the API.
	Status() NetStatus
	// Apply starts, restarts or stops the network with new settings.
	Apply(s settings.Settings)
}

// NetStatus is the state of the network.
type NetStatus struct {
	State string  // "off", "joining", "up", or "error"
	Err   string  // the error text when State is "error"
	IP    [4]byte // the address when State is "up"
}

// Options are the optional parts of a board.
type Options struct {
	Store   settings.Store // keeps the settings; nil keeps them in RAM only
	Net     Network        // the Wi-Fi; nil if the board has none
	Changer Changer        // the automatic pen changer; nil if there is none
}

// saveDelayUs is the wait after the last change before an automatic save.
const saveDelayUs = 3_000_000

// loadSettings reads the saved settings, or uses the defaults.
func (c *Controller) loadSettings() string {
	c.set = settings.Default()
	if c.store == nil {
		return "settings: defaults (no store)"
	}
	b := make([]byte, settings.Size)
	if !c.store.Load(b) {
		return "settings: defaults (none saved)"
	}
	if err := c.set.Decode(b); err != nil {
		c.set = settings.Default()
		return "settings: defaults (saved record not usable)"
	}
	return "settings: loaded"
}

// applySettings copies the settings to the running state.
func (c *Controller) applySettings() {
	c.penUp.Store(int32(c.set.PenUp))
	c.penDn.Store(int32(c.set.PenDown))
	c.speed = c.set.Speed
	c.ui.SyncSettings(c.set.PenUp, c.set.PenDown, c.set.Speed)
	if c.net != nil {
		c.net.Apply(c.set)
	}
}

// snapshotSettings copies the running state into the settings.
func (c *Controller) snapshotSettings() {
	up, dn := c.PenAngles()
	c.set.PenUp, c.set.PenDown, c.set.Speed = up, dn, c.speed
}

// saveSettings writes the settings to the store. Call it only when the machine is idle:
// a flash write stops the step interrupt on the Pico.
func (c *Controller) saveSettings() string {
	c.snapshotSettings()
	c.saveAt = 0
	if c.store == nil {
		return "!no settings store"
	}
	b := make([]byte, settings.Size)
	c.set.Encode(b)
	if err := c.store.Save(b); err != nil {
		return "!save failed: " + err.Error()
	}
	return ""
}

// markDirty asks for an automatic save when the machine is idle.
func (c *Controller) markDirty() {
	c.saveAt = c.hal.NowMicros() + saveDelayUs
}

// autoSave saves the settings when a change waits, the time is up and the machine is idle.
func (c *Controller) autoSave() {
	if c.saveAt == 0 || c.hal.NowMicros() < c.saveAt || c.wait != waitNone || !c.idle() || c.alarm {
		return
	}
	if r := c.saveSettings(); r != "" {
		c.msg = r[1:]
	}
}

// textCommand runs the lines with quoted text, which the G-code parser does not read:
// M587 S"ssid" P"password", M550 P"name". It also runs M500 to M503 and M552.
// It returns false if the line is not one of them.
func (c *Controller) textCommand(t string) (string, bool) {
	m, ok := mcode(t)
	if !ok {
		return "", false
	}
	switch m {
	case 500: // save
		if !c.idle() || c.wait != waitNone {
			c.wait, c.after = waitIdle, afterSave
			return "", true
		}
		return c.saveSettings(), true
	case 501: // load
		r := c.loadSettings()
		c.applySettings()
		c.saveAt = 0
		return "echo:" + r, true
	case 502: // defaults, not saved
		c.set = settings.Default()
		c.applySettings()
		return "echo:defaults set, send M500 to save", true
	case 503: // report
		return c.report(), true
	case 587: // Wi-Fi network
		ssid, ok1 := quoted(t, 'S')
		pass, _ := quoted(t, 'P')
		if !ok1 || ssid == "" || len(ssid) > settings.SSIDLen || len(pass) > settings.PassLen {
			return "!use M587 S\"network\" P\"password\"", true
		}
		c.set.SSID, c.set.Pass, c.set.WiFiOn = ssid, pass, true
		c.changedNet()
		return "echo:wifi network " + ssid, true
	case 588: // forget the network
		c.set.SSID, c.set.Pass = "", ""
		c.changedNet()
		return "echo:wifi network removed", true
	case 550: // host name
		name, ok := quoted(t, 'P')
		if !ok || !validHost(name) {
			return "!use M550 P\"name\" (letters, digits, -)", true
		}
		c.set.Hostname = name
		c.changedNet()
		return "echo:host name " + name, true
	case 552: // Wi-Fi on/off, address, report
		return c.m552(t), true
	}
	return "", false
}

func (c *Controller) changedNet() {
	c.markDirty()
	if c.net != nil {
		c.net.Apply(c.set)
	}
}

// m552 handles M552: S0/S1 turns Wi-Fi off/on, P<ip>[/bits] sets a fixed address
// (P0.0.0.0 uses DHCP), G<ip> sets the gateway. With no words it reports the state.
func (c *Controller) m552(t string) string {
	changed := false
	if v, ok := word(t, 'S'); ok {
		c.set.WiFiOn = v != "0"
		changed = true
	}
	if v, ok := word(t, 'P'); ok {
		ip, bits, ok := parseIP(v)
		if !ok {
			return "!bad address " + v
		}
		c.set.StaticIP = ip
		if bits > 0 {
			c.set.Netmask = uint8(bits)
		}
		changed = true
	}
	if v, ok := word(t, 'G'); ok {
		ip, _, ok := parseIP(v)
		if !ok {
			return "!bad gateway " + v
		}
		c.set.Gateway = ip
		changed = true
	}
	if changed {
		c.changedNet()
	}
	return "echo:" + c.netLine()
}

// netLine describes the network in one line.
func (c *Controller) netLine() string {
	if c.net == nil {
		return "wifi: none on this board"
	}
	st := c.net.Status()
	s := "wifi: " + st.State
	if st.State == "up" {
		s += " " + IPString(st.IP) + " " + c.set.Hostname + ".local"
	}
	if st.Err != "" {
		s += " (" + st.Err + ")"
	}
	if c.set.SSID != "" {
		s += " ssid " + c.set.SSID
	}
	return s
}

// report returns the settings as G-code lines that set them again (M503).
func (c *Controller) report() string {
	c.snapshotSettings()
	s := &c.set
	r := "echo:pen angles\nM281 U" + ui.Itoa(s.PenUp) + " D" + ui.Itoa(s.PenDown) +
		"\necho:speed " + ui.Itoa(s.Speed) + "%\necho:pen change T" + ui.Itoa(s.Tool) + " in the holder, park X" +
		ui.Itoa(s.ParkX) + " Y" + ui.Itoa(s.ParkY) + ", changer " + changerName(s.Changer) +
		"\necho:" + c.netLine() + "\nM550 P\"" + s.Hostname + "\""
	if s.StaticIP != [4]byte{} {
		r += "\nM552 P" + IPString(s.StaticIP) + "/" + ui.Itoa(int(s.Netmask)) + " G" + IPString(s.Gateway)
	}
	for i, p := range s.Pens {
		r += "\necho:T" + ui.Itoa(i) + " " + p.Name + " #" + hex6(p.Color)
	}
	return r
}

func changerName(k int) string {
	if k == settings.ChangerAuto {
		return "automatic"
	}
	return "manual"
}

// Settings returns a copy of the settings. Call it from the controller goroutine.
func (c *Controller) Settings() settings.Settings {
	c.snapshotSettings()
	return c.set
}

// ---------------------------------------------------------------- other goroutines

// mailbox holds work from other goroutines (the network API) for the controller goroutine.
type mailbox struct {
	mu  sync.Mutex
	fns [8]func()
	n   int
}

// Do runs f on the controller goroutine at the next Poll. It returns false if the
// mailbox is full. It is safe from any goroutine.
func (c *Controller) Do(f func()) bool {
	c.mb.mu.Lock()
	defer c.mb.mu.Unlock()
	if c.mb.n == len(c.mb.fns) {
		return false
	}
	c.mb.fns[c.mb.n] = f
	c.mb.n++
	return true
}

func (c *Controller) runMailbox() {
	c.mb.mu.Lock()
	n := c.mb.n
	var fns [8]func()
	copy(fns[:], c.mb.fns[:n])
	c.mb.n = 0
	c.mb.mu.Unlock()
	for i := 0; i < n; i++ {
		fns[i]()
	}
}

// apiState maps the LCD state to the API state: idle, busy, homing, pen_change, alarm.
func apiState(lcd string) string {
	switch lcd {
	case "BUSY":
		return "busy"
	case "HOME":
		return "homing"
	case "PEN":
		return "pen_change"
	case "ALARM":
		return "alarm"
	}
	return "idle"
}

// APIStatus is the state for the network API.
type APIStatus struct {
	State    string // idle, busy, homing, pen_change, alarm
	X, Y     float32
	PenDown  bool
	Tool     int
	Homed    bool
	Alarm    bool
	Msg      string
	Owner    string // the port that owns the machine
	JobName  string
	JobLine  int
	JobTotal int
	Progress int // percent from M73, or -1
}

type published struct {
	mu sync.Mutex
	st APIStatus
	at uint64
}

// publish copies the state for other goroutines, every 20 ms. A board without a network
// has no other goroutine, so it only runs the automatic save.
func (c *Controller) publish() {
	now := c.hal.NowMicros()
	if now-c.pub.at < 20_000 {
		return
	}
	if c.net == nil && !c.pubAlways {
		c.pub.at = now
		c.autoSave()
		return
	}
	s := c.Status()
	a := APIStatus{State: apiState(s.State), X: s.X, Y: s.Y, PenDown: s.PenDown, Tool: c.set.Tool, Homed: s.Homed,
		Alarm: s.Alarm, Msg: s.Msg, Owner: c.OwnerName(), Progress: c.progress}
	if c.owner >= 0 {
		a.JobName = c.ports[c.owner].name
		a.JobLine = int(c.ownerLines)
		if c.job.port == c.owner {
			a.JobName, a.JobTotal = c.job.name, c.job.total
		}
	}
	c.pub.mu.Lock()
	c.pub.st, c.pub.at = a, now
	c.pub.mu.Unlock()
	c.autoSave()
}

// PublishAlways makes the controller publish its state for the API even without a
// network (the tests of the API use it).
func (c *Controller) PublishAlways() { c.pubAlways = true }

// API returns the last published state. It is safe from any goroutine.
func (c *Controller) API() APIStatus {
	c.pub.mu.Lock()
	defer c.pub.mu.Unlock()
	return c.pub.st
}

// ---------------------------------------------------------------- text helpers

// quoted returns the quoted text after a letter, as in S"my network".
func quoted(t string, letter byte) (string, bool) {
	for i := 0; i+1 < len(t); i++ {
		if (t[i] == letter || t[i] == letter+32) && t[i+1] == '"' && (i == 0 || t[i-1] == ' ') {
			j := i + 2
			for k := j; k < len(t); k++ {
				if t[k] == '"' {
					return t[j:k], true
				}
			}
			return "", false
		}
	}
	return "", false
}

// word returns the text of a word, as "192.168.1.5" in "M552 P192.168.1.5".
func word(t string, letter byte) (string, bool) {
	for i := 1; i < len(t); i++ {
		if (t[i] == letter || t[i] == letter+32) && (t[i-1] == ' ' || t[i-1] == '\t') {
			j := i + 1
			for j < len(t) && t[j] != ' ' && t[j] != '\t' && t[j] != ';' {
				j++
			}
			return t[i+1 : j], true
		}
	}
	return "", false
}

// parseIP reads "a.b.c.d" or "a.b.c.d/bits".
func parseIP(s string) ([4]byte, int, bool) {
	var ip [4]byte
	part, n, digits, bits := 0, 0, 0, 0
	for i := 0; i <= len(s); i++ {
		if i == len(s) || s[i] == '.' || s[i] == '/' {
			if digits == 0 || n > 255 || part > 3 {
				return ip, 0, false
			}
			ip[part] = byte(n)
			part++
			n, digits = 0, 0
			if i < len(s) && s[i] == '/' {
				for _, ch := range s[i+1:] {
					if ch < '0' || ch > '9' {
						return ip, 0, false
					}
					bits = bits*10 + int(ch-'0')
				}
				if bits > 32 {
					return ip, 0, false
				}
				break
			}
			continue
		}
		if s[i] < '0' || s[i] > '9' {
			return ip, 0, false
		}
		n = n*10 + int(s[i]-'0')
		digits++
	}
	return ip, bits, part == 4
}

// IPString formats an IPv4 address.
func IPString(ip [4]byte) string {
	return ui.Itoa(int(ip[0])) + "." + ui.Itoa(int(ip[1])) + "." + ui.Itoa(int(ip[2])) + "." + ui.Itoa(int(ip[3]))
}

func validHost(s string) bool {
	if s == "" || len(s) > settings.HostnameLen {
		return false
	}
	for i := 0; i < len(s); i++ {
		ch := s[i]
		if !(ch >= 'a' && ch <= 'z' || ch >= 'A' && ch <= 'Z' || ch >= '0' && ch <= '9' || ch == '-') {
			return false
		}
	}
	return true
}

func hex6(v uint32) string {
	const h = "0123456789ABCDEF"
	var b [6]byte
	for i := 5; i >= 0; i-- {
		b[i] = h[v&15]
		v >>= 4
	}
	return string(b[:])
}

// keep the config import used (travel clamps live in settings).
var _ = config.TravelX
