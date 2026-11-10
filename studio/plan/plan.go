// Package plan places drawings on the bed and turns them into G-code for the plotter.
//
// Machine coordinates: millimetres, origin at the home corner (front left), X to the right,
// Y to the back. An item keeps its drawing in local millimetres with Y down (as in SVG). The
// top of the drawing points to the back of the table, so the drawing reads correctly for a
// person in front of the plotter.
package plan

import (
	"fmt"
	"math"
	"strings"
)

// Pt is a point in mm.
type Pt struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// Item is one drawing on the bed.
type Item struct {
	Name  string  `json:"name"`
	Lines [][]Pt  `json:"lines"` // local mm, Y down, from the top left corner of the drawing
	W     float64 `json:"w"`     // local size of the drawing in mm
	H     float64 `json:"h"`
	X     float64 `json:"x"` // machine position of the centre of the drawing
	Y     float64 `json:"y"`
	Scale float64 `json:"scale"` // 1 = the size in the file
	Angle float64 `json:"angle"` // degrees, counter-clockwise as seen from above
	// Colors and Layers give the colour (#rrggbb) and the layer label of each line, or are empty.
	Colors []string `json:"colors,omitempty"`
	Layers []string `json:"layers,omitempty"`
}

// Place returns the lines of the item in machine coordinates.
func (it Item) Place() [][]Pt {
	s := it.Scale
	if s == 0 {
		s = 1
	}
	a := it.Angle * math.Pi / 180
	c, sn := math.Cos(a), math.Sin(a)
	out := make([][]Pt, 0, len(it.Lines))
	for _, l := range it.Lines {
		pl := make([]Pt, len(l))
		for i, p := range l {
			u := (p.X - it.W/2) * s
			v := -(p.Y - it.H/2) * s // Y down in the drawing, Y to the back on the bed
			pl[i] = Pt{it.X + c*u - sn*v, it.Y + sn*u + c*v}
		}
		out = append(out, pl)
	}
	return out
}

// Bounds returns the bounding box of lines.
func Bounds(lines [][]Pt) (min, max Pt, ok bool) {
	min = Pt{math.Inf(1), math.Inf(1)}
	max = Pt{math.Inf(-1), math.Inf(-1)}
	for _, l := range lines {
		for _, p := range l {
			min.X, min.Y = math.Min(min.X, p.X), math.Min(min.Y, p.Y)
			max.X, max.Y = math.Max(max.X, p.X), math.Max(max.Y, p.Y)
			ok = true
		}
	}
	return
}

// Check returns an error if a point is outside the travel (0..tx, 0..ty).
func Check(lines [][]Pt, tx, ty float64) error {
	mn, mx, ok := Bounds(lines)
	if !ok {
		return nil
	}
	const eps = 1e-6
	if mn.X < -eps || mn.Y < -eps || mx.X > tx+eps || mx.Y > ty+eps {
		return fmt.Errorf("the drawing is outside the travel: x %.1f..%.1f, y %.1f..%.1f mm (travel %.0f x %.0f)",
			mn.X, mx.X, mn.Y, mx.Y, tx, ty)
	}
	return nil
}

// Order sorts the lines for a short pen-up travel: from start, it takes the nearest line end
// each time, and reverses a line when its far end is nearer.
func Order(lines [][]Pt, start Pt) [][]Pt {
	var todo [][]Pt
	for _, l := range lines {
		if len(l) > 0 {
			todo = append(todo, l)
		}
	}
	out := make([][]Pt, 0, len(todo))
	used := make([]bool, len(todo))
	cur := start
	d2 := func(a, b Pt) float64 { return (a.X-b.X)*(a.X-b.X) + (a.Y-b.Y)*(a.Y-b.Y) }
	for range todo {
		best, bestD, rev := -1, math.Inf(1), false
		for i, l := range todo {
			if used[i] {
				continue
			}
			if d := d2(cur, l[0]); d < bestD {
				best, bestD, rev = i, d, false
			}
			if d := d2(cur, l[len(l)-1]); d < bestD {
				best, bestD, rev = i, d, true
			}
		}
		used[best] = true
		l := todo[best]
		if rev {
			r := make([]Pt, len(l))
			for i := range l {
				r[i] = l[len(l)-1-i]
			}
			l = r
		}
		out = append(out, l)
		cur = l[len(l)-1]
	}
	return out
}

// TravelLength returns the pen-up distance of the ordered lines from start.
func TravelLength(lines [][]Pt, start Pt) float64 {
	var s float64
	cur := start
	for _, l := range lines {
		s += math.Hypot(l[0].X-cur.X, l[0].Y-cur.Y)
		cur = l[len(l)-1]
	}
	return s
}

// Options control the G-code.
type Options struct {
	Feed     float64 // draw speed in mm/min (default 3000)
	Home     bool    // G28 at the start
	Park     *Pt     // move here at the end (pen up), or nil
	PenDelay int     // ms after each pen move (0: the firmware waits for the servo itself)
	Join     float64 // join a line to the previous one if its start is this close, in mm (default 0.05)
}

// GCode makes the program for the lines, in the given order.
func GCode(lines [][]Pt, o Options) string {
	if o.Feed <= 0 {
		o.Feed = 3000
	}
	if o.Join <= 0 {
		o.Join = 0.05
	}
	var b strings.Builder
	f := func(v float64) string {
		s := fmt.Sprintf("%.3f", v)
		s = strings.TrimRight(strings.TrimRight(s, "0"), ".")
		if s == "-0" {
			s = "0"
		}
		return s
	}
	b.WriteString("; plotstudio\nG21\nG90\nM5\n")
	if o.Home {
		b.WriteString("G28\n")
	}
	pen := func(down bool) {
		if down {
			b.WriteString("M3\n")
		} else {
			b.WriteString("M5\n")
		}
		if o.PenDelay > 0 {
			fmt.Fprintf(&b, "G4 P%d\n", o.PenDelay)
		}
	}
	down := false
	var last Pt
	first := true
	for _, l := range lines {
		if len(l) == 0 {
			continue
		}
		if !first && down && math.Hypot(l[0].X-last.X, l[0].Y-last.Y) <= o.Join {
			// Go on without a pen lift.
		} else {
			if down {
				pen(false)
				down = false
			}
			fmt.Fprintf(&b, "G0 X%s Y%s\n", f(l[0].X), f(l[0].Y))
			pen(true)
			down = true
			fmt.Fprintf(&b, "G1 F%s\n", f(o.Feed))
		}
		for _, p := range l[1:] {
			fmt.Fprintf(&b, "G1 X%s Y%s\n", f(p.X), f(p.Y))
		}
		if len(l) == 1 {
			// A single point: a dot.
			fmt.Fprintf(&b, "G4 P150\n")
		}
		last = l[len(l)-1]
		first = false
	}
	if down {
		pen(false)
	}
	if o.Park != nil {
		fmt.Fprintf(&b, "G0 X%s Y%s\n", f(o.Park.X), f(o.Park.Y))
	}
	b.WriteString("M400\n")
	return b.String()
}

// Cross returns a plus mark of half size r at p: two strokes.
func Cross(p Pt, r float64) [][]Pt {
	return [][]Pt{{{p.X - r, p.Y}, {p.X + r, p.Y}}, {{p.X, p.Y - r}, {p.X, p.Y + r}}}
}

// Grid returns calibration points: n x n points over the travel, inset by margin.
// n = 0 gives the four corners and the centre.
func Grid(n int, tx, ty, margin float64) []Pt {
	if n < 2 {
		return []Pt{{margin, margin}, {tx - margin, margin}, {tx - margin, ty - margin}, {margin, ty - margin}, {tx / 2, ty / 2}}
	}
	var out []Pt
	for j := 0; j < n; j++ {
		for i := 0; i < n; i++ {
			x := margin + (tx-2*margin)*float64(i)/float64(n-1)
			y := margin + (ty-2*margin)*float64(j)/float64(n-1)
			if j%2 == 1 {
				x = margin + (tx-2*margin)*float64(n-1-i)/float64(n-1)
			}
			out = append(out, Pt{x, y})
		}
	}
	return out
}

// Dot returns a filled dot of radius r at p: concentric circles, 0.4 mm apart, and the centre.
// A camera finds the centre of a dot well: its centroid does not depend on the turn of the camera.
func Dot(p Pt, r float64) [][]Pt {
	var out [][]Pt
	for rr := r; rr > 0.2; rr -= 0.4 {
		n := max(12, int(math.Ceil(2*math.Pi*rr/0.3)))
		c := make([]Pt, 0, n+1)
		for i := 0; i <= n; i++ {
			a := 2 * math.Pi * float64(i) / float64(n)
			c = append(c, Pt{p.X + rr*math.Cos(a), p.Y + rr*math.Sin(a)})
		}
		out = append(out, c)
	}
	return append(out, []Pt{p, {p.X + 0.01, p.Y}})
}
