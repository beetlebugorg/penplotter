package mini

import (
	"strings"
	"testing"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
)

// fake is a board with a carriage model. The test runs the executor ticks.
type fake struct {
	ex   *stepgen.Executor
	in   []byte
	out  strings.Builder
	us   uint64
	phys [3]int32 // X, Y1, Y2 positions in steps; each switch is at 0
	dir  uint8
	pen  []int
	btn  bool
	lcd  [4]string
	mem  []byte
}

func (f *fake) NowMicros() uint64      { return f.us }
func (f *fake) SetMotors(bool)         {}
func (f *fake) Endstop(a int) bool     { return f.phys[a] <= 0 }
func (f *fake) Encoder() int           { return 0 }
func (f *fake) Button() bool           { return f.btn }
func (f *fake) Beep(int)               {}
func (f *fake) WriteSerial(s string)   { f.out.WriteString(s) }
func (f *fake) Text(row int, s string) { f.lcd[row] = s }
func (f *fake) Poll()                  {}
func (f *fake) Load(b []byte) bool     { return copy(b, f.mem) == len(b) }
func (f *fake) Save(b []byte) error    { f.mem = append([]byte(nil), b...); return nil }
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
			f.pen = append(f.pen, int(o.Servo))
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

func run(t *testing.T, f *fake, c *Controller, text string) string {
	t.Helper()
	f.in = append(f.in, text...)
	want := strings.Count(text, "\n")
	start := f.out.Len()
	for i := 0; i < 2_000_000; i++ {
		c.Poll()
		f.tick(200)
		out := f.out.String()[start:]
		if strings.Count(out, "ok\n")+strings.Count(out, "error:") >= want && c.idle() {
			return out
		}
	}
	t.Fatalf("lines did not finish; output:\n%s", f.out.String())
	return ""
}

func newFake() (*fake, *Controller) {
	ex := &stepgen.Executor{}
	f := &fake{ex: ex, phys: [3]int32{100 * 80, 50 * 80, 50*80 + 48}}
	ex.Endstop = f.Endstop
	return f, New(f, ex, f)
}

func TestHomeDrawAndReport(t *testing.T) {
	f, c := newFake()
	out := run(t, f, c, "G28\nG1 X10 Y20 F6000\nM3\nG1 X30\nG2 X30 Y40 I0 J10\nM5\nG0 X0 Y0\nM400\nM114\n")
	if strings.Contains(out, "error") {
		t.Fatalf("error in output:\n%s", out)
	}
	if !c.homed || f.phys != [3]int32{0, 0, 0} {
		t.Errorf("homed %v phys %v", c.homed, f.phys)
	}
	if len(f.pen) != 2 || f.pen[0] != config.PenDownDeg || f.pen[1] != config.PenUpDeg {
		t.Errorf("servo sequence %v", f.pen)
	}
	if !strings.Contains(out, "X:0.000 Y:0.000") {
		t.Errorf("M114 output:\n%s", out)
	}
}

func TestArcEndsAtTarget(t *testing.T) {
	f, c := newFake()
	run(t, f, c, "G28\nG1 X50 Y50 F3000\nG2 X70 Y50 I10 J0\nM400\n")
	if f.phys[0] != 70*80 || f.phys[1] != 50*80 || f.phys[2] != 50*80 {
		t.Errorf("phys %v", f.phys)
	}
}

func TestServoAngle(t *testing.T) {
	f, c := newFake()
	run(t, f, c, "M280 S10\nM280 S90\n")
	if len(f.pen) != 2 || f.pen[0] != 10 || f.pen[1] != 90 {
		t.Errorf("servo %v", f.pen)
	}
}

// M280 does not change the pen state. After "M5, M280 S69", G28 must not move the servo again.
func TestHomeKeepsServoAfterM280(t *testing.T) {
	f, c := newFake()
	run(t, f, c, "M3\nM5\nM280 P0 S69\nG28\nM400\n")
	if len(f.pen) != 3 || f.pen[2] != 69 {
		t.Errorf("servo sequence %v, want down, up, 69 and no move at G28", f.pen)
	}
}

func TestPenChangeWaitsForKnob(t *testing.T) {
	f, c := newFake()
	f.in = append(f.in, "T3\nM6\n"...)
	for i := 0; i < 200; i++ {
		c.Poll()
		f.tick(200)
	}
	if strings.Count(f.out.String(), "ok\n") != 1 || c.wait != waitPen {
		t.Fatalf("M6 did not wait: %q", f.out.String())
	}
	f.btn = true
	for i := 0; i < 5; i++ {
		c.Poll()
		f.tick(200)
	}
	f.btn = false
	for i := 0; i < 5; i++ {
		c.Poll()
		f.tick(200)
	}
	if strings.Count(f.out.String(), "ok\n") != 2 {
		t.Fatalf("no ok after the knob: %q", f.out.String())
	}
}

func TestSettingsSurvive(t *testing.T) {
	f, c := newFake()
	run(t, f, c, "M281 U120 D70\nM500\n")
	c2 := New(f, f.ex, f)
	if c2.set.PenUp != 120 || c2.set.PenDown != 70 {
		t.Errorf("loaded %+v", c2.set)
	}
}

func TestAlarmBlocksMotion(t *testing.T) {
	f, c := newFake()
	run(t, f, c, "M112\n")
	out := run(t, f, c, "G1 X10\n")
	if !strings.Contains(out, "error:alarm") {
		t.Errorf("motion in alarm:\n%s", out)
	}
	if out := run(t, f, c, "M999\nG1 X1\n"); strings.Contains(out, "error") {
		t.Errorf("after M999:\n%s", out)
	}
}

func TestStatusQuery(t *testing.T) {
	f, c := newFake()
	f.in = append(f.in, '?')
	c.Poll()
	if !strings.HasPrefix(f.out.String()[strings.Index(f.out.String(), "<"):], "<Idle|MPos:") {
		t.Errorf("status: %q", f.out.String())
	}
}
