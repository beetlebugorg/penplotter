// Command gen writes the sample G-code files in samples/.
//
//	go run ./samples/gen
package main

import (
	"fmt"
	"math"
	"os"
	"strings"
)

type pt struct{ x, y float64 }

type doc struct {
	b      strings.Builder
	ox, oy float64 // page origin on the bed
}

func (d *doc) f(format string, a ...any) { fmt.Fprintf(&d.b, format+"\n", a...) }

func (d *doc) xy(p pt) string { return fmt.Sprintf("X%.3f Y%.3f", p.x+d.ox, p.y+d.oy) }

// line draws a polyline: travel with the pen up, then draw with the pen down.
func (d *doc) line(ps ...pt) {
	d.f("G0 %s", d.xy(ps[0]))
	d.f("M3")
	for _, p := range ps[1:] {
		d.f("G1 %s", d.xy(p))
	}
	d.f("M5")
}

func (d *doc) rect(x, y, w, h float64) {
	d.line(pt{x, y}, pt{x + w, y}, pt{x + w, y + h}, pt{x, y + h}, pt{x, y})
}

func header(d *doc, title string) {
	d.f("; %s", title)
	d.f("; Pen plotter test file. G0 travels, G1 draws, M3 pen down, M5 pen up.")
	d.f("G21 ; mm")
	d.f("G90 ; absolute")
	d.f("M5")
	d.f("G28")
	d.f("G1 F3000 ; draw at 50 mm/s")
}

func footer(d *doc) {
	d.f("M5")
	d.f("G0 X0 Y0")
	d.f("M400")
}

func testDrawing() string {
	// An A4 page in portrait (210 x 297 mm), centered on the 216 x 380 mm travel.
	d := &doc{ox: 3, oy: 41}
	header(d, "test-drawing.gcode: A4 portrait calibration and art")
	d.f("; Page border, 5 mm in")
	d.rect(5, 5, 200, 287)

	d.f("; Calibration square: 100 x 100 mm, ticks every 10 mm")
	sx, sy := 55.0, 177.0
	d.rect(sx, sy, 100, 100)
	for i := 1; i < 10; i++ {
		l := 3.0
		if i == 5 {
			l = 6
		}
		x := sx + float64(i)*10
		d.line(pt{x, sy}, pt{x, sy + l})
		y := sy + float64(i)*10
		d.line(pt{sx, y}, pt{sx + l, y})
	}

	d.f("; Circle r = 40 mm with two G2 arcs")
	c := pt{sx + 50, sy + 50}
	d.f("G0 %s", d.xy(pt{c.x - 40, c.y}))
	d.f("M3")
	d.f("G2 %s I40 J0", d.xy(pt{c.x + 40, c.y}))
	d.f("G2 %s I-40 J0", d.xy(pt{c.x - 40, c.y}))
	d.f("M5")

	d.f("; Diagonals of the square: they must meet at the circle center")
	d.line(pt{sx, sy}, pt{sx + 100, sy + 100})
	d.line(pt{sx + 100, sy}, pt{sx, sy + 100})

	d.f("; Rose curve, 7 petals, r = 55 mm")
	rc := pt{105, 100}
	var rose []pt
	for i := 0; i <= 1400; i++ {
		t := float64(i) / 1400 * math.Pi
		r := 55 * math.Cos(7*t)
		rose = append(rose, pt{rc.x + r*math.Cos(t), rc.y + r*math.Sin(t)})
	}
	d.line(rose...)

	d.f("; Nested squares, each turned 6 degrees")
	for k := 0; k < 15; k++ {
		a := float64(k) * 6 * math.Pi / 180
		s := 24.0 * math.Pow(0.93, float64(k))
		var sq []pt
		for j := 0; j <= 4; j++ {
			t := a + float64(j)*math.Pi/2 + math.Pi/4
			sq = append(sq, pt{rc.x + s*math.Cos(t), rc.y + s*math.Sin(t)})
		}
		d.line(sq...)
	}

	d.f("; Line spacing strip: gaps of 2.0, 1.5, 1.0, 0.7 and 0.5 mm")
	x := 70.0
	for _, g := range []float64{2, 1.5, 1, 0.7, 0.5} {
		for i := 0; i < 8; i++ {
			d.line(pt{x, 15}, pt{x, 35})
			x += g
		}
		x += 6
	}

	d.f("; Corner marks for the paper position")
	for _, p := range []pt{{0, 0}, {210, 0}, {210, 297}, {0, 297}} {
		dx, dy := 1.0, 1.0
		if p.x > 0 {
			dx = -1
		}
		if p.y > 0 {
			dy = -1
		}
		d.line(pt{p.x + dx*8, p.y}, p, pt{p.x, p.y + dy*8})
	}
	footer(d)
	return d.b.String()
}

func square() string {
	d := &doc{ox: 20, oy: 20}
	header(d, "square.gcode: 40 mm square and a circle (quick test)")
	d.rect(0, 0, 40, 40)
	d.f("G0 %s", d.xy(pt{5, 20}))
	d.f("M3")
	d.f("G2 %s I15 J0", d.xy(pt{5, 20}))
	d.f("M5")
	footer(d)
	return d.b.String()
}

func main() {
	dir := "samples"
	if _, err := os.Stat(dir); err != nil {
		dir = "."
	}
	for name, text := range map[string]string{"test-drawing.gcode": testDrawing(), "square.gcode": square()} {
		if err := os.WriteFile(dir+"/"+name, []byte(text), 0o644); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Printf("wrote %s/%s (%d lines)\n", dir, name, strings.Count(text, "\n"))
	}
}
