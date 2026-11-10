package ui

import (
	"strings"
	"testing"
)

type fakeHost struct {
	cmds      []string
	jog       float32
	st        Status
	confirmed int
}

func (h *fakeHost) Status() Status                { return h.st }
func (h *fakeHost) Command(l string) bool         { h.cmds = append(h.cmds, l); return true }
func (h *fakeHost) Jog(axis int, mm float32) bool { h.jog += mm; return true }
func (h *fakeHost) SetPenAngles(up, down int)     { h.st.PenUp, h.st.PenDn = up, down }
func (h *fakeHost) SetSpeed(p int)                { h.st.Speed = p }

// dump returns the framebuffer as text, for test failure messages.
func dump(f *FB) string {
	var b strings.Builder
	for y := 0; y < Height; y++ {
		for x := 0; x < Width; x++ {
			if f.Front[y*Stride+x/8]&(0x80>>(x&7)) != 0 {
				b.WriteByte('#')
			} else {
				b.WriteByte('.')
			}
		}
		b.WriteByte('\n')
	}
	return b.String()
}

func lit(f *FB) int {
	n := 0
	for _, v := range f.Front {
		for ; v != 0; v &= v - 1 {
			n++
		}
	}
	return n
}

func TestStatusAndMenu(t *testing.T) {
	h := &fakeHost{st: Status{X: 12.5, Y: -3.25, Speed: 100, Progress: 40, State: "IDLE", PenUp: 130, PenDn: 80}}
	u := New(h)
	u.Draw()
	if n := lit(&u.FB); n < 300 {
		t.Fatalf("status screen has %d lit pixels\n%s", n, dump(&u.FB))
	}
	if !u.FB.Dirty() {
		t.Fatal("no dirty rows after the first draw")
	}
	for u.FB.Dirty() {
		u.FB.NextDirty()
	}
	u.Draw()
	if u.FB.Dirty() {
		t.Error("an unchanged screen has dirty rows")
	}
	// Open the menu, go to "Home XY" and click it.
	u.Click()
	u.Turn(1)
	u.Draw()
	u.Click()
	if len(h.cmds) != 1 || h.cmds[0] != "G28" {
		t.Errorf("commands = %v", h.cmds)
	}
	if u.InMenu() {
		t.Error("an action does not go back to the status screen")
	}
	// Speed value: open menu, go to Speed (index 6), edit, turn 2 detents.
	u.Click()
	u.Turn(6)
	u.Click()
	u.Turn(2)
	u.Draw()
	if h.st.Speed != 120 {
		t.Errorf("speed = %d\n%s", h.st.Speed, dump(&u.FB))
	}
	// Jog: Move axis > Move X, edit, turn 3 detents of 10 mm.
	u.LongPress()
	u.Click()
	u.Turn(2)
	u.Click()
	u.Turn(2)
	u.Click()
	u.Turn(3)
	u.Draw()
	if h.jog != 30 {
		t.Errorf("jog = %v\n%s", h.jog, dump(&u.FB))
	}
}

func TestFormat(t *testing.T) {
	cases := map[string]string{
		Fixed(12.345, 2): "12.35", Fixed(-0.04, 1): "0.0", Fixed(-3.25, 2): "-3.25",
		Fixed(7, 0): "7", Itoa(-120): "-120", Itoa(0): "0",
	}
	for got, want := range cases {
		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	}
}

func (h *fakeHost) Confirm()             { h.confirmed++ }
func (h *fakeHost) PenName(i int) string { return "Pen" + Itoa(i) }
func (h *fakeHost) SetTool(t int)        { h.st.Tool = t }
func (h *fakeHost) WiFi() (string, string, string, bool) {
	return "home", "penplotter", "up 192.168.1.40", true
}

func TestPromptClickConfirms(t *testing.T) {
	h := &fakeHost{}
	u := New(h)
	h.st.Prompt, h.st.PromptSub = "Load pen T2", "Red"
	u.Draw()
	u.Click()
	if h.confirmed != 1 || u.InMenu() {
		t.Fatalf("confirmed %d, menu %v", h.confirmed, u.InMenu())
	}
}

func TestTextEditor(t *testing.T) {
	h := &fakeHost{}
	u := New(h)
	got := ""
	u.edit_("Network name", "", 8, false, func(s string) { got = s })
	// The editor starts on 'a'. Add "ab", delete "b", add "c", then OK.
	u.Click()  // a
	u.Turn(1)  // b
	u.Click()  // b
	u.Turn(-2) // DEL
	u.Click()  // delete b
	u.Turn(3)  // c
	u.Click()  // c
	u.Turn(-4) // OK
	u.Draw()   // the editor draws without a panic
	u.Click()  // done
	if got != "ac" || u.te != nil {
		t.Fatalf("got %q, editor open %v", got, u.te != nil)
	}
	// A long press cancels.
	u.edit_("Password", "", 8, true, func(s string) { got = "changed" })
	u.Click()
	u.LongPress()
	if got != "ac" || u.te != nil {
		t.Fatalf("cancel: got %q", got)
	}
}
