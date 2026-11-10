// Command mandala writes samples/mandala.gcode: a six-colour mandala with manual pen changes.
//
//	go run ./samples/mandala
//
// Each colour is one pen, T0 to T5. The job homes first. Before each colour, the firmware lifts
// the pen and waits at M6 (T<n>, M6). Change the pen, then press the knob. The light colours draw
// first, so a dark line does not smear into a light one. The program also writes
// samples/mandala.svg, a preview in the same colours.
package main

import (
	"fmt"
	"log"
	"math"
	"os"
	"strings"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/studio/plan"
)

// The drawing area is the full table: X 0 to 245, Y 0 to 390 (machine mm).
const (
	cx, cy = config.TravelX / 2.0, config.TravelY / 2.0 // centre of the mandala
	steps  = 720                                        // points on a full circle
	// The outer frame, 5 mm from the edge of the travel.
	fx0, fy0, fx1, fy1 = 5.0, 5.0, config.TravelX - 5.0, config.TravelY - 5.0
	// The centres of the corner suns, 6 mm inside the frame corners.
	sx0, sy0, sx1, sy1 = fx0 + 6, fy0 + 6, fx1 - 6, fy1 - 6
)

// The pen table: Sharpie Fine, classic colours.
var pens = []plan.Pen{
	{T: 0, Name: "Black Sharpie Fine", Color: "#1a1a1a", Width: 1.0},
	{T: 1, Name: "Red Sharpie Fine", Color: "#d62828", Width: 1.0},
	{T: 2, Name: "Orange Sharpie Fine", Color: "#f77f00", Width: 1.0},
	{T: 3, Name: "Green Sharpie Fine", Color: "#1b7f3b", Width: 1.0},
	{T: 4, Name: "Blue Sharpie Fine", Color: "#1f4fbf", Width: 1.0},
	{T: 5, Name: "Purple Sharpie Fine", Color: "#6a2c91", Width: 1.0},
}

type lines = [][]plan.Pt

// polar returns the closed curve r(t) around the centre, t from 0 to 2 pi.
func polar(r func(t float64) float64, rot float64) []plan.Pt {
	out := make([]plan.Pt, 0, steps+1)
	for i := 0; i <= steps; i++ {
		t := 2 * math.Pi * float64(i) / steps
		out = append(out, at(r(t), t+rot))
	}
	return out
}

func at(r, t float64) plan.Pt { return plan.Pt{X: cx + r*math.Cos(t), Y: cy + r*math.Sin(t)} }

func circle(x, y, r float64) []plan.Pt {
	n := max(24, int(r*6))
	out := make([]plan.Pt, 0, n+1)
	for i := 0; i <= n; i++ {
		t := 2 * math.Pi * float64(i) / float64(n)
		out = append(out, plan.Pt{X: x + r*math.Cos(t), Y: y + r*math.Sin(t)})
	}
	return out
}

// petal returns a lens from radius r0 to r1 at angle a, w wide at its middle.
func petal(r0, r1, w, a float64) []plan.Pt {
	const n = 40
	var side [2][]plan.Pt
	for s, sign := range []float64{1, -1} {
		for i := 0; i <= n; i++ {
			u := float64(i) / n
			r := r0 + (r1-r0)*u
			off := sign * w / 2 * math.Sin(math.Pi*u)
			side[s] = append(side[s], plan.Pt{
				X: cx + r*math.Cos(a) - off*math.Sin(a),
				Y: cy + r*math.Sin(a) + off*math.Cos(a),
			})
		}
	}
	out := side[0]
	for i := n - 1; i >= 0; i-- {
		out = append(out, side[1][i])
	}
	return out
}

// Orange: the inner eight-petal rose, and sun rays in the four corners.
func orange() lines {
	var l lines
	for k := 0; k < 3; k++ {
		s := 28 - 4*float64(k)
		l = append(l, polar(func(t float64) float64 { return s * math.Abs(math.Cos(4*t)) }, 0))
	}
	corners := [][3]float64{{sx0, sy0, 0}, {sx1, sy0, math.Pi / 2}, {sx1, sy1, math.Pi}, {sx0, sy1, 3 * math.Pi / 2}}
	for _, c := range corners {
		for i := 0; i <= 8; i++ {
			a := c[2] + math.Pi/2*float64(i)/8
			l = append(l, []plan.Pt{
				{X: c[0] + 4*math.Cos(a), Y: c[1] + 4*math.Sin(a)},
				{X: c[0] + 22*math.Cos(a), Y: c[1] + 22*math.Sin(a)},
			})
		}
	}
	return l
}

// Green: a ring of twelve leaves with a midrib, between radius 32 and 60.
func green() lines {
	var l lines
	for i := 0; i < 12; i++ {
		a := 2*math.Pi*float64(i)/12 + math.Pi/12
		l = append(l, petal(32, 60, 13, a), []plan.Pt{at(34, a), at(57, a)})
	}
	return l
}

// Red: the centre dot (rings), a ring of beads at radius 66, and the corner suns.
func red() lines {
	var l lines
	for r := 1.5; r <= 7.5; r += 1.5 {
		l = append(l, circle(cx, cy, r))
	}
	for i := 0; i < 36; i++ {
		p := at(66, 2*math.Pi*float64(i)/36)
		l = append(l, circle(p.X, p.Y, 2.2))
	}
	for _, c := range [][2]float64{{sx0, sy0}, {sx1, sy0}, {sx1, sy1}, {sx0, sy1}} {
		l = append(l, circle(c[0], c[1], 2.5))
	}
	return l
}

// Blue: a braid of three waves between radius 72 and 88.
func blue() lines {
	var l lines
	for k := 0; k < 3; k++ {
		ph := 2 * math.Pi * float64(k) / 3
		l = append(l, polar(func(t float64) float64 { return 80 + 7*math.Sin(18*t+ph) }, 0))
	}
	return l
}

// Purple: an outer band of scallops between radius 92 and 108.
func purple() lines {
	var l lines
	l = append(l, polar(func(t float64) float64 { return 92 }, 0))
	l = append(l, polar(func(t float64) float64 { return 92 + 15*math.Abs(math.Sin(12*t)) }, 0))
	l = append(l, polar(func(t float64) float64 { return 92 + 9*math.Abs(math.Sin(12*t)) }, 0))
	return l
}

// Black: two circles around the mandala and a double frame.
func black() lines {
	var l lines
	l = append(l, circle(cx, cy, 111), circle(cx, cy, 113.5))
	for _, d := range []float64{0, 2.5} {
		x0, y0, x1, y1 := fx0+d, fy0+d, fx1-d, fy1-d
		l = append(l, []plan.Pt{{X: x0, Y: y0}, {X: x1, Y: y0}, {X: x1, Y: y1}, {X: x0, Y: y1}, {X: x0, Y: y0}})
	}
	return l
}

func main() {
	// Light colours first, black last.
	groups := []plan.Group{
		{Pen: 2, Lines: orange()}, {Pen: 3, Lines: green()}, {Pen: 1, Lines: red()},
		{Pen: 4, Lines: blue()}, {Pen: 5, Lines: purple()}, {Pen: 0, Lines: black()},
	}
	total := 0.0
	for _, g := range groups {
		if err := plan.Check(g.Lines, config.TravelX, config.TravelY); err != nil {
			log.Fatalf("T%d: %v", g.Pen, err)
		}
		for _, ln := range g.Lines {
			for i := 1; i < len(ln); i++ {
				total += math.Hypot(ln[i].X-ln[i-1].X, ln[i].Y-ln[i-1].Y)
			}
		}
	}
	// Park at the back, so the paper is free at the end.
	park := plan.Pt{X: 5, Y: config.TravelY}
	g := plan.GCodeGroups(groups, plan.Options{Feed: 3000, Home: true, Park: &park}, true)
	var hdr strings.Builder
	hdr.WriteString("; Mandala: six colours with manual pen changes (samples/mandala/main.go)\n")
	hdr.WriteString("; The job homes first. Before each colour, the plotter stops at M6.\n")
	hdr.WriteString("; Press the knob after each pen change.\n")
	hdr.WriteString("; Pen order:\n")
	for i, gr := range groups {
		fmt.Fprintf(&hdr, ";   %d. T%d  %s\n", i+1, gr.Pen, pens[gr.Pen].Name)
	}
	fmt.Fprintf(&hdr, "; Pen-down length %.0f mm. Pen changes: %d.\n", total, len(groups))
	if err := os.WriteFile("samples/mandala.gcode", []byte(hdr.String()+g), 0o644); err != nil {
		log.Fatal(err)
	}
	if err := os.WriteFile("samples/mandala.svg", []byte(svg(groups)), 0o644); err != nil {
		log.Fatal(err)
	}
	fmt.Printf("samples/mandala.gcode: %d lines, %.0f mm pen down, %d pens\n", strings.Count(hdr.String()+g, "\n"), total, len(groups))
}

// svg draws the groups in machine coordinates, Y up, on the full table.
func svg(groups []plan.Group) string {
	var b strings.Builder
	fmt.Fprintf(&b, `<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">`+"\n",
		2*config.TravelX, 2*config.TravelY, config.TravelX, config.TravelY)
	fmt.Fprintf(&b, `<rect x="0" y="0" width="%d" height="%d" fill="#fff"/>`+"\n", config.TravelX, config.TravelY)
	fmt.Fprintf(&b, `<g transform="translate(0 %d) scale(1 -1)" fill="none" stroke-linecap="round" stroke-linejoin="round">`+"\n", config.TravelY)
	for _, g := range groups {
		fmt.Fprintf(&b, `<g stroke="%s" stroke-width="0.8">`+"\n", pens[g.Pen].Color)
		for _, ln := range g.Lines {
			b.WriteString(`<polyline points="`)
			for _, p := range ln {
				fmt.Fprintf(&b, "%.2f,%.2f ", p.X, p.Y)
			}
			b.WriteString(`"/>` + "\n")
		}
		b.WriteString("</g>\n")
	}
	b.WriteString("</g></svg>\n")
	return b.String()
}
