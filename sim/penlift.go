package sim

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
)

// The pen lift linkage. The servo horn lifts a tab on the pen slider. The slider and the pen fall
// by their weight. The pen touches the paper when the horn tip is below the tab.
// hardware/model.py writes the linkage to frame.json ("pen_lift").
//
// Above the slip angle, the horn tip goes past the end of the tab and the slider falls. The tip is
// then over the tab. When the horn comes down again, the tip stops on the top of the tab at the
// stall angle. The pen stays on the paper until a person lifts the slider (FreeHorn).

// PenLink is the linkage data from frame.json.
type PenLink struct {
	Lift  []float64 // the slider lift in mm for the servo angles 0..180 degrees (tip under the tab)
	Slip  float64   // servo angle: above it, the tip leaves the end of the tab
	Stall float64   // servo angle: the tip, over the tab, stops on the top of the tab (0: none)
}

// LoadPenLink reads the pen lift linkage from frame.json.
func LoadPenLink(path string) (*PenLink, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var f struct {
		PenLift *struct {
			Lift  []float64 `json:"lift_by_servo_deg"`
			Slip  float64   `json:"slip_servo"`
			Stall *float64  `json:"stall_servo"`
		} `json:"pen_lift"`
	}
	if err := json.Unmarshal(b, &f); err != nil {
		return nil, err
	}
	p := f.PenLift
	if p == nil || len(p.Lift) != 181 {
		return nil, fmt.Errorf("%s: no pen_lift.lift_by_servo_deg with 181 values", path)
	}
	l := &PenLink{Lift: p.Lift, Slip: p.Slip}
	if p.Stall != nil {
		l.Stall = *p.Stall
	}
	if l.Slip <= 0 {
		l.Slip = 181 // no slip
	}
	return l, nil
}

// SetPenLink sets the linkage. With a linkage, the pen inks when the slider rests on the paper.
// With no linkage (nil), the pen inks at 90 % of the way from the pen-up to the pen-down angle.
func (m *Machine) SetPenLink(l *PenLink) {
	if l != nil && len(l.Lift) != 181 {
		l = nil
	}
	m.mu.Lock()
	m.penLink = l
	m.mu.Unlock()
}

// FreeHorn lifts the slider by hand when the horn rests on the top of the tab. The horn goes back under the tab.
func (m *Machine) FreeHorn() { m.freeHorn.Store(true) }

// liftAt returns the slider lift in mm at a servo angle. It interpolates the table.
func liftAt(t []float64, deg float64) float64 {
	deg = math.Max(0, math.Min(180, deg))
	i := int(deg)
	if i >= 180 {
		return t[180]
	}
	f := deg - float64(i)
	return t[i]*(1-f) + t[i+1]*f
}

// stop applies the tab to the horn after a servo step. over is true while the tip is over the tab
// (after a slip). Then the horn stops on the top of the tab. free is a person who lifts the slider.
// stop returns the horn angle.
func (l *PenLink) stop(horn float64, over *bool, free bool) float64 {
	if horn >= l.Slip {
		*over = true
	} else if free || l.Stall <= 0 {
		*over = false
	}
	if *over && l.Stall > 0 && horn < l.Stall {
		return l.Stall
	}
	return horn
}

// lift returns the slider lift in mm for a horn angle. Over the tab, the slider rests on the paper.
func (l *PenLink) lift(horn float64, over bool) float64 {
	if over {
		return 0
	}
	return liftAt(l.Lift, horn)
}

// penTouches tells if the pen tip is on the paper.
func penTouches(l *PenLink, horn float64, over bool, up, dn float64) bool {
	if l == nil {
		return penNorm(horn, up, dn) >= 0.9
	}
	return l.lift(horn, over) <= 0.01
}
