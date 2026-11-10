package ui

import "github.com/beetlebugorg/penplotter/firmware/config"

// Status is what the status screen shows.
type Status struct {
	X, Y     float32 // work position in mm
	PenDown  bool
	Homed    bool
	Motors   bool
	Busy     bool
	Alarm    bool
	Lines    uint32 // G-code lines done
	Progress int    // percent, or -1 if unknown
	Speed    int    // speed override in percent
	PenUp    int    // servo angle of pen up
	PenDn    int    // servo angle of pen down
	Msg      string
	State    string
	ES       [3]bool // endstops: X, Y1, Y2
	Skew     float32 // Y2 minus Y1 in mm (0 after homing)
	Tool     int     // the pen in the holder (T0 to T15)
	Net      string  // the address, or the Wi-Fi state; "" with no Wi-Fi
	// Prompt asks the user to do something, for example "Load pen T3". A click answers it.
	Prompt    string
	PromptSub string
}

// Host is the machine side of the UI.
type Host interface {
	Status() Status
	// Command queues one G-code line. It returns false if the queue is full.
	Command(line string) bool
	// Jog queues a relative move of one axis.
	Jog(axis int, mm float32) bool
	SetPenAngles(up, down int)
	SetSpeed(pct int)
	// Confirm answers the prompt (the pen is loaded).
	Confirm()
	// PenName returns the name of pen i of the pen table.
	PenName(i int) string
	// SetTool sets the pen that is in the holder now.
	SetTool(t int)
	// WiFi returns the network name, the host name and the network state.
	// has is false if the board has no Wi-Fi.
	WiFi() (ssid, host, state string, has bool)
}

type kind uint8

const (
	kAction kind = iota
	kMenu
	kValue
	kJog
	kInfo
	kBack
)

type item struct {
	label string
	kind  kind
	act   func()
	sub   *menu
	val   *int
	min   int
	max   int
	step  int
	unit  string
	set   func(v int)
	text  func(v int) string
	live  func(s Status) string // kInfo: a label from the live status
	axis  int
}

type menu struct {
	title  string
	items  []item
	parent *menu
	cur    int
	top    int
	enter  func()
}

const rows = 6 // menu rows below the title

// UI runs the screens.
type UI struct {
	FB   FB
	host Host
	cur  *menu // nil shows the status screen
	edit bool
	main *menu

	speed, penUp, penDn, stepIdx int
	tool, changeTo               int
	te                           *textEdit
	ssid, pass                   string
}

var jogSteps = [...]float32{0.1, 1, 10, 50}

// New makes the UI and its menus.
func New(h Host) *UI {
	u := &UI{host: h, speed: 100, penUp: config.PenUpDeg, penDn: config.PenDownDeg, stepIdx: 2}
	cmd := func(s string) func() { return func() { u.host.Command(s) } }
	move := &menu{title: "Move axis", items: []item{
		{label: "< Back", kind: kBack},
		{label: "Step", kind: kValue, val: &u.stepIdx, min: 0, max: len(jogSteps) - 1, step: 1,
			text: func(v int) string { return Fixed(jogSteps[v], 1) + "mm" }},
		{label: "Move X", kind: kJog, axis: config.X},
		{label: "Move Y", kind: kJog, axis: config.Y},
		{label: "Home XY", kind: kAction, act: cmd("G28")},
	}}
	pen := &menu{title: "Pen setup", items: []item{
		{label: "< Back", kind: kBack},
		{label: "Up angle", kind: kValue, val: &u.penUp, min: 0, max: 180, step: 1, unit: "deg",
			set: func(v int) { u.host.SetPenAngles(u.penUp, u.penDn); u.host.Command("M280 P0 S" + Itoa(v)) }},
		{label: "Down angle", kind: kValue, val: &u.penDn, min: 0, max: 180, step: 1, unit: "deg",
			set: func(v int) { u.host.SetPenAngles(u.penUp, u.penDn); u.host.Command("M280 P0 S" + Itoa(v)) }},
		{label: "Test up", kind: kAction, act: func() { u.host.Command("M280 P0 S" + Itoa(u.penUp)) }},
		{label: "Test down", kind: kAction, act: func() { u.host.Command("M280 P0 S" + Itoa(u.penDn)) }},
	}}
	pen.enter = func() { s := u.host.Status(); u.penUp, u.penDn = s.PenUp, s.PenDn }
	trig := func(on bool) string {
		if on {
			return "TRIG"
		}
		return "open"
	}
	ends := &menu{title: "Endstops", items: []item{
		{label: "< Back", kind: kBack},
		{kind: kInfo, live: func(s Status) string { return "X  min   " + trig(s.ES[0]) }},
		{kind: kInfo, live: func(s Status) string { return "Y1 min   " + trig(s.ES[1]) }},
		{kind: kInfo, live: func(s Status) string { return "Y2 min   " + trig(s.ES[2]) }},
		{kind: kInfo, live: func(s Status) string { return "Y2-Y1 " + Fixed(s.Skew, 2) + "mm" }},
	}}
	penText := func(v int) string {
		n := u.host.PenName(v)
		if len(n) > 9 {
			n = n[:9]
		}
		return "T" + Itoa(v) + " " + n
	}
	pens := &menu{title: "Pens", items: []item{
		{label: "< Back", kind: kBack},
		{label: "Hold", kind: kValue, val: &u.tool, min: 0, max: 15, step: 1, text: penText,
			set: func(v int) { u.host.SetTool(v) }},
		{label: "Next", kind: kValue, val: &u.changeTo, min: 0, max: 15, step: 1, text: penText},
		{label: "Change pen now", kind: kAction, act: func() { u.host.Command("M6 T" + Itoa(u.changeTo)) }},
	}}
	pens.enter = func() { u.tool = u.host.Status().Tool; u.changeTo = u.tool }
	wifi := &menu{title: "Wi-Fi", items: []item{
		{label: "< Back", kind: kBack},
		{kind: kInfo, live: func(Status) string {
			_, _, st, has := u.host.WiFi()
			if !has {
				return "No Wi-Fi (Pico H)"
			}
			return st
		}},
		{kind: kInfo, live: func(Status) string {
			ssid, _, _, _ := u.host.WiFi()
			return "Net: " + ssid
		}},
		{kind: kInfo, live: func(Status) string {
			_, host, _, _ := u.host.WiFi()
			return host + ".local"
		}},
		{label: "Network name", kind: kAction, act: func() {
			u.edit_("Network name", u.ssid, 32, false, func(t string) { u.ssid = t })
		}},
		{label: "Password", kind: kAction, act: func() {
			u.edit_("Password", "", 63, true, func(t string) { u.pass = t })
		}},
		{label: "Connect", kind: kAction, act: func() {
			u.host.Command("M587 S\"" + u.ssid + "\" P\"" + u.pass + "\"")
		}},
		{label: "Wi-Fi on", kind: kAction, act: cmd("M552 S1")},
		{label: "Wi-Fi off", kind: kAction, act: cmd("M552 S0")},
	}}
	wifi.enter = func() { u.ssid, _, _, _ = u.host.WiFi() }
	about := &menu{title: "About", items: []item{
		{label: "< Back", kind: kBack},
		{label: "Pen plotter " + config.Version, kind: kInfo},
		{label: "TinyGo, RP2040", kind: kInfo},
		{label: "Travel " + Itoa(config.TravelX) + "x" + Itoa(config.TravelY) + "mm", kind: kInfo},
		{label: "Dual Y, table frame", kind: kInfo},
		{label: "Steps/mm " + Itoa(config.StepsPerMMX) + " " + Itoa(config.StepsPerMMY), kind: kInfo},
	}}
	u.main = &menu{title: "Menu", items: []item{
		{label: "< Status", kind: kBack},
		{label: "Home XY", kind: kAction, act: cmd("G28")},
		{label: "Move axis", kind: kMenu, sub: move},
		{label: "Pen up", kind: kAction, act: cmd("M5")},
		{label: "Pen down", kind: kAction, act: cmd("M3")},
		{label: "Pen setup", kind: kMenu, sub: pen},
		{label: "Speed", kind: kValue, val: &u.speed, min: 10, max: 300, step: 10, unit: "%",
			set: func(v int) { u.host.SetSpeed(v) }},
		{label: "Pens", kind: kMenu, sub: pens},
		{label: "Motors off", kind: kAction, act: cmd("M18")},
		{label: "Wi-Fi", kind: kMenu, sub: wifi},
		{label: "Endstops", kind: kMenu, sub: ends},
		{label: "Save settings", kind: kAction, act: cmd("M500")},
		{label: "About", kind: kMenu, sub: about},
	}}
	for _, m := range []*menu{move, pen, pens, wifi, ends, about} {
		m.parent = u.main
	}
	return u
}

// InMenu tells if a menu shows.
func (u *UI) InMenu() bool { return u.cur != nil }

// Turn handles knob detents. Positive is clockwise.
func (u *UI) Turn(d int) {
	if d == 0 {
		return
	}
	if u.te != nil {
		u.te.turn(d)
		return
	}
	if u.cur == nil {
		return
	}
	m := u.cur
	it := &m.items[m.cur]
	if u.edit {
		switch it.kind {
		case kValue:
			v := *it.val + d*it.step
			if v < it.min {
				v = it.min
			}
			if v > it.max {
				v = it.max
			}
			if v != *it.val {
				*it.val = v
				if it.set != nil {
					it.set(v)
				}
			}
		case kJog:
			u.host.Jog(it.axis, float32(d)*jogSteps[u.stepIdx])
		}
		return
	}
	m.cur += d
	if m.cur < 0 {
		m.cur = 0
	}
	if m.cur >= len(m.items) {
		m.cur = len(m.items) - 1
	}
	if m.cur < m.top {
		m.top = m.cur
	}
	if m.cur >= m.top+rows {
		m.top = m.cur - rows + 1
	}
}

// Click handles a short press of the knob.
func (u *UI) Click() {
	if u.te != nil {
		if u.te.click() {
			u.te = nil
		}
		return
	}
	if u.cur == nil && u.host.Status().Prompt != "" {
		u.host.Confirm()
		return
	}
	if u.cur == nil {
		u.cur = u.main
		u.main.cur, u.main.top = 0, 0
		u.speed = u.host.Status().Speed
		return
	}
	it := &u.cur.items[u.cur.cur]
	switch it.kind {
	case kBack:
		u.cur = u.cur.parent
	case kAction:
		it.act()
		if u.te == nil && u.cur != nil && u.cur.title != "Wi-Fi" {
			u.cur = nil
		}
	case kMenu:
		u.cur = it.sub
		it.sub.cur, it.sub.top = 0, 0
		if it.sub.enter != nil {
			it.sub.enter()
		}
	case kValue, kJog:
		u.edit = !u.edit
	}
}

// LongPress goes back to the status screen.
func (u *UI) LongPress() {
	if u.te != nil {
		u.te = nil // cancel the text
		return
	}
	u.cur = nil
	u.edit = false
}

// SyncSettings copies the saved values into the menus.
func (u *UI) SyncSettings(penUp, penDn, speed int) {
	u.penUp, u.penDn, u.speed = penUp, penDn, speed
}

// Draw renders the current screen and commits the changed rows.
func (u *UI) Draw() {
	u.FB.Clear()
	switch {
	case u.te != nil:
		u.te.draw(u)
	case u.cur != nil:
		u.drawMenu()
	default:
		if s := u.host.Status(); s.Prompt != "" {
			u.drawPrompt(s)
		} else {
			u.drawStatus()
		}
	}
	u.FB.Commit()
}

func (u *UI) bar(title, right string) {
	u.FB.Fill(0, 0, Width, 9, true)
	u.FB.Text(2, 1, title, 1, false)
	u.FB.Text(Width-2-6*len(right), 1, right, 1, false)
}

func (u *UI) drawStatus() {
	s := u.host.Status()
	u.bar("PEN PLOTTER", s.State)
	u.FB.Text(2, 12, "X", 1, true)
	u.FB.Text(14, 11, pad(Fixed(s.X, 2), 8), 2, true)
	u.FB.Text(2, 29, "Y", 1, true)
	u.FB.Text(14, 28, pad(Fixed(s.Y, 2), 8), 2, true)
	pen := "UP"
	if s.PenDown {
		pen = "DOWN"
	}
	line := "Pen " + pen + " T" + Itoa(s.Tool)
	line += " " + Itoa(s.Speed) + "%"
	if !s.Homed {
		line += " !H"
	}
	u.FB.Text(2, 45, line, 1, true)
	switch {
	case s.Msg != "":
		u.FB.Text(2, 55, s.Msg, 1, true)
	case s.Progress >= 0:
		u.FB.Rect(2, 55, 90, 8)
		u.FB.Fill(4, 57, 86*s.Progress/100, 4, true)
		u.FB.Text(96, 55, Itoa(s.Progress)+"%", 1, true)
	case s.Net != "" && s.Lines == 0:
		u.FB.Text(2, 55, s.Net, 1, true)
	default:
		u.FB.Text(2, 55, "Lines "+Itoa(int(s.Lines)), 1, true)
	}
}

func (u *UI) drawMenu() {
	m := u.cur
	u.bar(m.title, "")
	var st Status
	for i := range m.items {
		if m.items[i].live != nil {
			st = u.host.Status()
			break
		}
	}
	for r := 0; r < rows; r++ {
		i := m.top + r
		if i >= len(m.items) {
			break
		}
		it := &m.items[i]
		y := 10 + r*9
		sel := i == m.cur
		if sel {
			u.FB.Fill(0, y, Width, 9, true)
		}
		on := !sel
		label := it.label
		if it.live != nil {
			label = it.live(st)
		}
		if it.kind == kMenu {
			label += " >"
		}
		u.FB.Text(2, y+1, label, 1, on)
		val := ""
		switch it.kind {
		case kValue:
			if it.text != nil {
				val = it.text(*it.val)
			} else {
				val = Itoa(*it.val) + it.unit
			}
		case kJog:
			s := u.host.Status()
			v := s.X
			if it.axis == config.Y {
				v = s.Y
			}
			val = Fixed(v, 1)
		}
		if sel && u.edit {
			val = "[" + val + "]"
		}
		if val != "" {
			u.FB.Text(Width-2-6*len(val), y+1, val, 1, on)
		}
	}
	// Scroll mark on the right edge.
	if len(m.items) > rows {
		h := 54 * rows / len(m.items)
		y := 10 + (54-h)*m.top/(len(m.items)-rows)
		u.FB.Fill(Width-1, y, 1, h, true)
	}
}

func pad(s string, n int) string {
	for len(s) < n {
		s = " " + s
	}
	return s
}

// Itoa formats an integer.
func Itoa(v int) string {
	if v == 0 {
		return "0"
	}
	var b [12]byte
	i := len(b)
	neg := v < 0
	if neg {
		v = -v
	}
	for v > 0 {
		i--
		b[i] = byte('0' + v%10)
		v /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}

// Fixed formats v with dec decimals.
func Fixed(v float32, dec int) string {
	scale := 1
	for i := 0; i < dec; i++ {
		scale *= 10
	}
	neg := v < 0
	if neg {
		v = -v
	}
	n := int(v*float32(scale) + 0.5)
	s := Itoa(n / scale)
	if dec > 0 {
		f := Itoa(n % scale)
		for len(f) < dec {
			f = "0" + f
		}
		s += "." + f
	}
	if neg && n != 0 {
		s = "-" + s
	}
	return s
}

// drawPrompt shows a question that a click answers, as for a pen change.
func (u *UI) drawPrompt(s Status) {
	u.bar("PEN CHANGE", s.State)
	u.FB.Text(2, 14, s.Prompt, 1, true)
	u.FB.Text(2, 26, s.PromptSub, 2, true)
	u.FB.Text(2, 45, "Put the pen in the", 1, true)
	u.FB.Text(2, 55, "clamp. Then click.", 1, true)
}

// ---------------------------------------------------------------- text editor

// Characters of the text editor. Index 0 ends the text, index 1 deletes a character.
const charset = "\x02\x01abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_.@!#$%&*+=?/:;,'\"()<>[]{}^~`|\\"

// textEdit types a text with the knob: turn to choose a character, click to add it.
type textEdit struct {
	title  string
	text   []byte
	max    int
	secret bool
	sel    int
	done   func(string)
}

// edit_ opens the text editor. done gets the text when the user picks the end mark.
func (u *UI) edit_(title, text string, max int, secret bool, done func(string)) {
	u.te = &textEdit{title: title, text: []byte(text), max: max, secret: secret, sel: 2, done: done}
}

func (t *textEdit) turn(d int) {
	n := len(charset)
	t.sel = ((t.sel+d)%n + n) % n
}

// click adds the selected character. It returns true when the text is complete.
func (t *textEdit) click() bool {
	switch charset[t.sel] {
	case 2:
		t.done(string(t.text))
		return true
	case 1:
		if len(t.text) > 0 {
			t.text = t.text[:len(t.text)-1]
		}
	default:
		if len(t.text) < t.max {
			t.text = append(t.text, charset[t.sel])
		}
	}
	return false
}

func charLabel(ch byte) string {
	switch ch {
	case 2:
		return "OK"
	case 1:
		return "DEL"
	case ' ':
		return "SPC"
	}
	return string([]byte{ch})
}

func (t *textEdit) draw(u *UI) {
	u.bar(t.title, Itoa(len(t.text))+"/"+Itoa(t.max))
	shown := []byte(t.text)
	if t.secret {
		for i := 0; i < len(shown)-1; i++ {
			shown[i] = '*'
		}
	}
	if len(shown) > 20 {
		shown = shown[len(shown)-20:]
	}
	u.FB.Text(2, 13, string(shown)+"_", 1, true)
	// The character wheel: the selected character large, its neighbours small.
	n := len(charset)
	for k := -3; k <= 3; k++ {
		ch := charset[((t.sel+k)%n+n)%n]
		if k == 0 {
			continue
		}
		x := 58 + k*17
		if k > 0 {
			x += 6
		}
		lab := charLabel(ch)
		if len(lab) > 1 {
			lab = lab[:1]
		}
		u.FB.Text(x, 32, lab, 1, true)
	}
	lab := charLabel(charset[t.sel])
	u.FB.Rect(52, 26, 24, 18)
	u.FB.Text(64-3*len(lab)*2/2-len(lab)*3+3, 29, lab, 2, true)
	u.FB.Text(2, 55, "click=add hold=cancel", 1, true)
}
