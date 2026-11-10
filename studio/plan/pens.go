package plan

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// MaxPens is the size of the pen table: T0 to T15.
const MaxPens = 16

// Pen is one entry of the pen table.
type Pen struct {
	T     int    `json:"t"`
	Name  string `json:"name"`
	Color string `json:"color"` // #rrggbb
	// Width is the line width in mm (0: not set).
	Width float64 `json:"width,omitempty"`
}

// DefaultPens is a 16-colour table: the colours of a common fineliner set.
func DefaultPens() []Pen {
	cols := []struct{ n, c string }{
		{"Black", "#1a1a1a"}, {"Grey", "#7a7a7a"}, {"Red", "#d62828"}, {"Orange", "#f77f00"},
		{"Yellow", "#f2c500"}, {"Light green", "#7bc043"}, {"Green", "#1b7f3b"}, {"Teal", "#16a3a3"},
		{"Light blue", "#4aa8e0"}, {"Blue", "#1f4fbf"}, {"Navy", "#14215e"}, {"Purple", "#6a2c91"},
		{"Pink", "#e05a9b"}, {"Brown", "#7a4a24"}, {"Sepia", "#5e4b3c"}, {"Gold", "#b8902a"},
	}
	out := make([]Pen, len(cols))
	for i, c := range cols {
		out[i] = Pen{T: i, Name: c.n + " 0.5", Color: c.c, Width: 0.5}
	}
	return out
}

func rgb(hex string) (r, g, b float64, ok bool) {
	h := strings.TrimPrefix(strings.TrimSpace(hex), "#")
	if len(h) != 6 {
		return 0, 0, 0, false
	}
	v, err := strconv.ParseUint(h, 16, 32)
	if err != nil {
		return 0, 0, 0, false
	}
	return float64(v >> 16 & 255), float64(v >> 8 & 255), float64(v & 255), true
}

// lab converts sRGB to CIE L*a*b* (D65), for a colour distance that follows the eye.
func lab(hex string) (l, a, b float64, ok bool) {
	r, g, bl, ok := rgb(hex)
	if !ok {
		return
	}
	lin := func(c float64) float64 {
		c /= 255
		if c <= 0.04045 {
			return c / 12.92
		}
		return math.Pow((c+0.055)/1.055, 2.4)
	}
	R, G, B := lin(r), lin(g), lin(bl)
	x := (0.4124*R + 0.3576*G + 0.1805*B) / 0.95047
	y := 0.2126*R + 0.7152*G + 0.0722*B
	z := (0.0193*R + 0.1192*G + 0.9505*B) / 1.08883
	f := func(t float64) float64 {
		if t > 0.008856 {
			return math.Cbrt(t)
		}
		return 7.787*t + 16.0/116
	}
	fx, fy, fz := f(x), f(y), f(z)
	return 116*fy - 16, 500 * (fx - fy), 200 * (fy - fz), true
}

// Nearest returns the T of the pen whose colour is nearest to hex (CIE76 distance in Lab).
// It returns -1 for an empty table or a colour it cannot read.
func Nearest(hex string, pens []Pen) int {
	l1, a1, b1, ok := lab(hex)
	if !ok {
		return -1
	}
	best, bt := math.Inf(1), -1
	for _, p := range pens {
		l2, a2, b2, ok := lab(p.Color)
		if !ok {
			continue
		}
		d := (l1-l2)*(l1-l2) + (a1-a2)*(a1-a2) + (b1-b2)*(b1-b2)
		if d < best {
			best, bt = d, p.T
		}
	}
	return bt
}

// Lightness is the L* of a colour (0 black to 100 white), or 50 for an unknown colour.
func Lightness(hex string) float64 {
	l, _, _, ok := lab(hex)
	if !ok {
		return 50
	}
	return l
}

var layerPen = regexp.MustCompile(`^\s*(?:t|pen\s*|tool\s*)?(\d{1,2})\b`)

// LayerPen reads a pen number from a layer label: "3", "T3", "Pen 3 - red", "tool 12". It
// returns -1 when the label names no pen in 0..15.
func LayerPen(label string) int {
	m := layerPen.FindStringSubmatch(strings.ToLower(label))
	if m == nil {
		return -1
	}
	n, _ := strconv.Atoi(m[1])
	if n >= MaxPens {
		return -1
	}
	return n
}

// Group is the lines of one pen.
type Group struct {
	Pen   int    `json:"pen"`
	Lines [][]Pt `json:"-"`
}

// GroupByPen sorts lines into one group for each pen. pens gives the pen of each line. The
// groups go from the lightest pen colour to the darkest, so that dark lines draw over light
// ones and a light pen does not pick up dark ink. Each pen changes once. The lines of a group
// are in plot order (Order), from the end of the previous group.
func GroupByPen(lines [][]Pt, pens []int, table []Pen) []Group {
	by := map[int][][]Pt{}
	for i, l := range lines {
		p := 0
		if i < len(pens) && pens[i] >= 0 {
			p = pens[i]
		}
		by[p] = append(by[p], l)
	}
	color := map[int]string{}
	for _, p := range table {
		color[p.T] = p.Color
	}
	keys := make([]int, 0, len(by))
	for k := range by {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		li, lj := Lightness(color[keys[i]]), Lightness(color[keys[j]])
		if math.Abs(li-lj) > 1e-9 {
			return li > lj
		}
		return keys[i] < keys[j]
	})
	var out []Group
	at := Pt{}
	for _, k := range keys {
		ord := Order(by[k], at)
		if n := len(ord); n > 0 {
			l := ord[n-1]
			at = l[len(l)-1]
		}
		out = append(out, Group{Pen: k, Lines: ord})
	}
	return out
}

// GCodeGroups makes one program for groups of lines. With more than one group (or with
// o.ToolChange), each group starts with a pen change: pen up, "Tn", "M6". The firmware stops
// at M6 and shows "Load pen n" on the LCD until the knob is pressed.
func GCodeGroups(groups []Group, o Options, toolChange bool) string {
	if len(groups) == 0 {
		return GCode(nil, o)
	}
	if len(groups) == 1 && !toolChange {
		return GCode(groups[0].Lines, o)
	}
	// Make each group without its header and footer, then join them.
	var b strings.Builder
	head := GCode(nil, Options{Feed: o.Feed, Home: o.Home})
	head = strings.TrimSuffix(head, "M400\n")
	b.WriteString(head)
	inner := o
	inner.Home, inner.Park = false, nil
	for _, g := range groups {
		fmt.Fprintf(&b, "M5\nT%d\nM6\n", g.Pen)
		body := GCode(g.Lines, inner)
		body = strings.TrimPrefix(body, "; plotstudio\nG21\nG90\nM5\n")
		body = strings.TrimSuffix(body, "M400\n")
		b.WriteString(body)
	}
	if o.Park != nil {
		fmt.Fprintf(&b, "G0 X%s Y%s\n", trim(o.Park.X), trim(o.Park.Y))
	}
	b.WriteString("M400\n")
	return b.String()
}

func trim(v float64) string {
	s := strings.TrimRight(strings.TrimRight(fmt.Sprintf("%.3f", v), "0"), ".")
	if s == "-0" {
		return "0"
	}
	return s
}
