package controller

import (
	"strings"
	"testing"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/settings"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// fake is a board with a carriage model. The test runs the executor ticks.
type fake struct {
	ex    *stepgen.Executor
	in    []byte
	out   strings.Builder
	us    uint64
	phys  [3]int32 // X, Y1, Y2 positions in steps; each switch is at 0
	dir   uint8
	servo int
	pen   []int
}

type nullDisplay struct{}

func (nullDisplay) Flush(fb *ui.FB) {
	for fb.Dirty() {
		fb.NextDirty()
	}
}

func (f *fake) NowMicros() uint64    { return f.us }
func (f *fake) SetMotors(bool)       {}
func (f *fake) Endstop(a int) bool   { return f.phys[a] <= 0 }
func (f *fake) Encoder() int         { return 0 }
func (f *fake) Button() bool         { return false }
func (f *fake) Beep(int)             {}
func (f *fake) WriteSerial(s string) { f.out.WriteString(s) }
func (f *fake) Display() ui.Display  { return nullDisplay{} }
func (f *fake) Poll()                {}
func (f *fake) ReadSerial() (byte, bool) {
	if len(f.in) == 0 {
		return 0, false
	}
	b := f.in[0]
	f.in = f.in[1:]
	return b, true
}

func (f *fake) tick(n int) {
	for i := 0; i < n; i++ {
		o := f.ex.Tick()
		if o.DirSet {
			f.dir = o.Dir
		}
		if o.Servo >= 0 {
			f.servo = int(o.Servo)
			f.pen = append(f.pen, f.servo)
		}
		for a := 0; a < 3; a++ {
			if o.Step&(1<<a) != 0 {
				if f.dir&(1<<a) != 0 {
					f.phys[a]--
				} else {
					f.phys[a]++
				}
			}
		}
	}
	f.us += uint64(n) * 1_000_000 / config.TickHz
}

func runLines(t *testing.T, f *fake, c *Controller, text string) {
	t.Helper()
	f.in = append(f.in, text...)
	want := strings.Count(text, "\n")
	start := f.out.Len() // count only the answers to these lines
	for i := 0; i < 2_000_000; i++ {
		c.Poll()
		f.tick(200)
		out := f.out.String()[start:]
		if strings.Count(out, "ok\n")+strings.Count(out, "error:") >= want && c.idle() {
			return
		}
	}
	t.Fatalf("lines did not finish; output:\n%s", f.out.String())
}

func newFake() (*fake, *Controller) {
	ex := &stepgen.Executor{}
	// Y2 starts 0.6 mm behind Y1: the beam is not square at power on.
	f := &fake{ex: ex, phys: [3]int32{100 * 80, 50 * 80, 50*80 + 48}}
	ex.Endstop = f.Endstop
	return f, New(f, ex)
}

func TestHomeDrawAndReport(t *testing.T) {
	f, c := newFake()
	runLines(t, f, c, "G28\nG1 X10 Y20 F6000\nM3\nG1 X30\nG2 X30 Y40 I0 J10\nM5\nG0 X0 Y0\nM400\nM114\n")
	out := f.out.String()
	if strings.Contains(out, "error") {
		t.Fatalf("error in output:\n%s", out)
	}
	if !c.homed {
		t.Error("not homed")
	}
	if f.phys != [3]int32{0, 0, 0} || c.ex.Pos(0) != 0 || c.ex.Pos(1) != 0 || c.ex.Pos(2) != 0 {
		t.Errorf("phys %v pos %d %d", f.phys, c.ex.Pos(0), c.ex.Pos(1))
	}
	// Power-on pen up, G28 pen up is no change, M3 down, M5 up.
	if len(f.pen) != 3 || f.pen[1] != config.PenDownDeg || f.pen[2] != config.PenUpDeg {
		t.Errorf("servo sequence %v", f.pen)
	}
	if !strings.Contains(out, "X:0.000 Y:0.000") {
		t.Errorf("M114 output:\n%s", out)
	}
}

func TestHomeFailsWithoutSwitch(t *testing.T) {
	f, c := newFake()
	f.phys = [3]int32{1 << 30, 0, 0} // the switch is out of reach
	runLines(t, f, c, "G28 X\n")
	if !strings.Contains(f.out.String(), "error:homing failed") || !c.alarm {
		t.Errorf("output:\n%s", f.out.String())
	}
}

func TestDualYSquaresAndReports(t *testing.T) {
	f, c := newFake()
	runLines(t, f, c, "G28 Y\nG1 Y100 F6000\nM400\nM119\n")
	if f.phys[1] != 8000 || f.phys[2] != 8000 {
		t.Errorf("Y1 %d, Y2 %d: the beam is not square", f.phys[1], f.phys[2])
	}
	out := f.out.String()
	for _, want := range []string{"x_min: open", "y1_min: open", "y2_min: open"} {
		if !strings.Contains(out, want) {
			t.Errorf("M119 output has no %q:\n%s", want, out)
		}
	}
	// A missing Y2 switch gives an error that names Y2.
	f2, c2 := newFake()
	f2.phys[2] = 1 << 30
	runLines(t, f2, c2, "G28 Y\n")
	if !strings.Contains(f2.out.String(), "no Y2 endstop") {
		t.Errorf("output:\n%s", f2.out.String())
	}
}

func TestRelativeUnitsAndOffsets(t *testing.T) {
	f, c := newFake()
	runLines(t, f, c, "G28\nG92 X5 Y5\nG91\nG1 X1 Y-1 F600\nG90\nG20\nG1 X1\nG21\nM114\n")
	// X: G92 X5 at 0 -> offset -5. Relative +1 -> 1. Then X1 inch = 25.4 work -> 20.4 machine.
	if got := c.ex.Pos(0); got != 1632 {
		t.Errorf("x steps = %d", got)
	}
	// Y: relative -1 from 0 is clamped by the soft limit to 0.
	if got := c.ex.Pos(1); got != 0 {
		t.Errorf("y steps = %d", got)
	}
}

func TestPenChangeWaitsForConfirm(t *testing.T) {
	f, c := newFake()
	runLines(t, f, c, "G28\nG1 X50 Y60 F6000\nM3\n")
	f.in = append(f.in, "T3 M6\nG1 X70\n"...)
	for i := 0; i < 20000; i++ {
		c.Poll()
		f.tick(200)
	}
	st := c.Status()
	if st.State != "PEN" || st.Prompt != "Load pen T3" || st.PromptSub != "Green" {
		t.Fatalf("state %q prompt %q %q", st.State, st.Prompt, st.PromptSub)
	}
	if st.PenDown {
		t.Fatal("the pen is down during the change")
	}
	// The carriage parks at the pen change position.
	if f.phys[0] != int32(config.TravelX/2*80) || f.phys[1] != 0 {
		t.Fatalf("not parked: %v", f.phys)
	}
	// M108 on a second port answers the prompt.
	p := &Pipe{}
	id := c.AddPort("api", p)
	p.FeedString("M108\n")
	runLines(t, f, c, "")
	for i := 0; i < 20000 && c.Status().State != "IDLE"; i++ {
		c.Poll()
		f.tick(200)
	}
	if c.set.Tool != 3 || c.Status().Prompt != "" {
		t.Fatalf("tool %d prompt %q", c.set.Tool, c.Status().Prompt)
	}
	if f.phys[0] != 70*80 {
		t.Fatalf("the job did not continue: %v", f.phys)
	}
	c.ClosePort(id)
	// Errors: no T word, a bad pen, the automatic changer without hardware.
	runLines(t, f, c, "T16\nM6 T3\nM400\n")
	out := f.out.String()
	if !strings.Contains(out, "error:no pen T16") || !strings.Contains(out, "echo:pen T3 is in the holder") {
		t.Fatalf("output:\n%s", out)
	}
}

func TestHardLimitBeforeHoming(t *testing.T) {
	f, c := newFake()
	// Not homed: a move far to -X runs into the X switch.
	runLines(t, f, c, "G91\nG1 X-200 F6000\n")
	for i := 0; i < 50000 && !c.alarm; i++ {
		c.Poll()
		f.tick(200)
	}
	if !c.alarm || !strings.Contains(c.msg, "hard limit X") {
		t.Fatalf("alarm %v msg %q", c.alarm, c.msg)
	}
	if f.phys[0] < -2 {
		t.Fatalf("the carriage went %d steps past the switch", -f.phys[0])
	}
	// After homing, a move to home does not trip the limit.
	runLines(t, f, c, "M999\nG90\nG28\nG1 X30 Y30 F6000\nG0 X0 Y0\nM400\n")
	if c.alarm {
		t.Fatalf("alarm after a move to home: %s", c.msg)
	}
}

func TestOwnerAndQueries(t *testing.T) {
	f, c := newFake()
	p := &Pipe{}
	id := c.AddPort("tcp", p)
	p.FeedString("G28\nG1 X100 F600\n")
	for i := 0; i < 200 && c.OwnerName() != "tcp"; i++ {
		c.Poll()
		f.tick(200)
	}
	// USB: a motion line is busy, a query works, '?' works.
	f.in = append(f.in, "G1 Y5\nM114\n?"...)
	for i := 0; i < 50; i++ {
		c.Poll()
		f.tick(200)
	}
	out := f.out.String()
	if !strings.Contains(out, "error:busy, tcp has the machine") || !strings.Contains(out, "X:") || !strings.Contains(out, "<Home|") && !strings.Contains(out, "<Run|") {
		t.Fatalf("usb output:\n%s", out)
	}
	// The owner is released after the moves end and OwnerHoldMs passes.
	c.ClosePort(id)
	if c.OwnerName() != "" {
		t.Fatal("closed port still owns the machine")
	}
}

func TestSettingsSaveAndLoad(t *testing.T) {
	f := &fake{ex: &stepgen.Executor{}, phys: [3]int32{4000, 4000, 4000}}
	f.ex.Endstop = f.Endstop
	store := &settings.MemStore{}
	c := NewWith(f, f.ex, Options{Store: store})
	runLines(t, f, c, "M281 U125 D70\nM550 P\"plotter2\"\nM500\n")
	if store.B == nil {
		t.Fatal("M500 did not save")
	}
	f2 := &fake{ex: &stepgen.Executor{}, phys: [3]int32{4000, 4000, 4000}}
	f2.ex.Endstop = f2.Endstop
	c2 := NewWith(f2, f2.ex, Options{Store: store})
	if up, dn := c2.PenAngles(); up != 125 || dn != 70 || c2.set.Hostname != "plotter2" {
		t.Fatalf("loaded %d %d %q", up, dn, c2.set.Hostname)
	}
	// The power-on pen lift uses the saved angle.
	for i := 0; i < 10; i++ {
		c2.Poll()
		f2.tick(200)
	}
	if len(f2.pen) == 0 || f2.pen[0] != 125 {
		t.Fatalf("power-on servo %v", f2.pen)
	}
	runLines(t, f2, c2, "M587 S\"home net\" P\"pw 1\"\nM503\n")
	if !strings.Contains(f2.out.String(), "M281 U125 D70") || !strings.Contains(f2.out.String(), "wifi: none on this board") {
		t.Fatalf("M503:\n%s", f2.out.String())
	}
	if c2.set.SSID != "home net" || c2.set.Pass != "pw 1" {
		t.Fatalf("M587: %q %q", c2.set.SSID, c2.set.Pass)
	}
}

func TestLongCommentLine(t *testing.T) {
	f, c := newFake()
	// A comment-only line gets no answer; a long comment after G-code does not count.
	f.in = append(f.in, "; "+strings.Repeat("vpype header text ", 20)+"\n"...)
	runLines(t, f, c, "G21 ; "+strings.Repeat("x", 200)+"\n")
	if strings.Contains(f.out.String(), "error") {
		t.Fatalf("output:\n%s", f.out.String())
	}
}

// TestDialects runs G-code in the styles of vpype, Inkscape and other tools.
func TestDialects(t *testing.T) {
	f, c := newFake()
	runLines(t, f, c, "%\n(Inkscape output)\nG21\nG90\nG28\nM03 S1000\nG00 X10 Y10\nG01 Z-1.000 F1200\nG01 X20.5 Y10\nG00 Z5\nM05\ng1 x5 y5\nN10 G1 X6*57\nG4 P10\nM2\n")
	out := f.out.String()
	if strings.Contains(out, "error") {
		t.Fatalf("output:\n%s", out)
	}
	if f.phys[0] != 6*80 || f.phys[1] != 5*80 {
		t.Fatalf("position %v", f.phys)
	}
}
