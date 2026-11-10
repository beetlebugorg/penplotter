package plan

import (
	"strings"
	"testing"
)

func TestNearestAndLayerPen(t *testing.T) {
	pens := DefaultPens()
	if Nearest("#000000", pens) != 0 || Nearest("#ff0000", pens) != 2 || Nearest("#0000ff", pens) != 9 {
		t.Errorf("nearest: %d %d %d", Nearest("#000000", pens), Nearest("#ff0000", pens), Nearest("#0000ff", pens))
	}
	if Nearest("bad", pens) != -1 {
		t.Error("bad colour")
	}
	for label, want := range map[string]int{"3": 3, "T3": 3, "Pen 12 - teal": 12, "tool 15": 15, "16": -1, "Layer 1": -1, "": -1} {
		if got := LayerPen(label); got != want {
			t.Errorf("LayerPen(%q) = %d, want %d", label, got, want)
		}
	}
}

func TestGroupsAndGCode(t *testing.T) {
	pens := DefaultPens()
	lines := [][]Pt{{{0, 0}, {10, 0}}, {{0, 5}, {10, 5}}, {{0, 10}, {10, 10}}}
	groups := GroupByPen(lines, []int{0, 4, 0}, pens) // black, yellow, black
	if len(groups) != 2 || groups[0].Pen != 4 || groups[1].Pen != 0 || len(groups[1].Lines) != 2 {
		t.Fatalf("groups: %+v", groups)
	}
	g := GCodeGroups(groups, Options{Feed: 3000, Home: true, Park: &Pt{0, 300}}, false)
	if strings.Count(g, "M6") != 2 || !strings.Contains(g, "T4\nM6") || !strings.Contains(g, "T0\nM6") {
		t.Fatalf("pen changes:\n%s", g)
	}
	if strings.Index(g, "T4") > strings.Index(g, "T0") {
		t.Error("the light pen must come first")
	}
	if strings.Count(g, "G28") != 1 || !strings.HasSuffix(g, "G0 X0 Y300\nM400\n") {
		t.Errorf("header or footer:\n%s", g)
	}
	one := GCodeGroups(GroupByPen(lines, nil, pens), Options{}, false)
	if strings.Contains(one, "M6") {
		t.Error("a one-pen job has no pen change")
	}
	if !strings.Contains(GCodeGroups(GroupByPen(lines, nil, pens), Options{}, true), "T0\nM6") {
		t.Error("tool change on request")
	}
}
