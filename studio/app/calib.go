package app

import (
	"encoding/json"
	"errors"
	"image"
	"math"
	"os"
	"path/filepath"
	"time"

	"github.com/beetlebugorg/penplotter/studio/geom"
)

// Pair is one calibration point: a picture point (pixels of the scan picture) and the machine
// point (mm) where the pen made its mark.
type Pair struct {
	PX float64 `json:"px"`
	PY float64 `json:"py"`
	X  float64 `json:"x"`
	Y  float64 `json:"y"`
}

// Calibration maps the scan picture to machine coordinates.
type Calibration struct {
	Size   [2]int    `json:"size"` // the scan picture size
	H9     geom.H    `json:"homography"`
	Lens   geom.Lens `json:"lens"`
	RMS    float64   `json:"rms_mm"`
	Pairs  []Pair    `json:"pairs"`
	Focus  *int      `json:"focus,omitempty"` // the fixed lens position at calibration, or nil (autofocus)
	Camera string    `json:"camera"`
	Time   time.Time `json:"time"`
	Errors []float64 `json:"errors_mm"` // the error at each pair
	cam    geom.Camera
}

// Solve fits the camera. fitK1 also fits the lens distortion (6 or more pairs).
func Solve(pairs []Pair, w, h int, fitK1 bool) (*Calibration, error) {
	if w <= 0 || h <= 0 {
		return nil, errors.New("calibration: no picture size: scan first")
	}
	var px, mm []geom.Pt
	for _, p := range pairs {
		px = append(px, geom.Pt{X: p.PX, Y: p.PY})
		mm = append(mm, geom.Pt{X: p.X, Y: p.Y})
	}
	cam, rms, err := geom.Fit(px, mm, w, h, fitK1)
	if err != nil {
		return nil, err
	}
	c := &Calibration{Size: [2]int{w, h}, H9: cam.H, Lens: cam.Lens, RMS: rms, Pairs: pairs, Time: time.Now(), cam: cam}
	for i := range px {
		q := cam.ToMachine(px[i])
		c.Errors = append(c.Errors, math.Hypot(q.X-mm[i].X, q.Y-mm[i].Y))
	}
	return c, nil
}

func (c *Calibration) setup() error {
	hi, err := c.H9.Inverse()
	if err != nil {
		return err
	}
	c.cam = geom.Camera{Lens: c.Lens, H: c.H9, Hi: hi}
	return nil
}

// ToMachine maps a picture point (pixels of a picture of size sz) to machine mm.
func (c *Calibration) ToMachine(p geom.Pt, sz image.Point) geom.Pt {
	return c.cam.ToMachine(c.scaleIn(p, sz))
}

// ToPicture maps machine mm to the picture point of a picture of size sz.
func (c *Calibration) ToPicture(m geom.Pt, sz image.Point) geom.Pt {
	q := c.cam.ToCamera(m)
	if sz.X == c.Size[0] || sz.X == 0 {
		return q
	}
	return geom.Pt{X: q.X * float64(sz.X) / float64(c.Size[0]), Y: q.Y * float64(sz.Y) / float64(c.Size[1])}
}

func (c *Calibration) scaleIn(p geom.Pt, sz image.Point) geom.Pt {
	if sz.X == c.Size[0] || sz.X == 0 {
		return p
	}
	return geom.Pt{X: p.X * float64(c.Size[0]) / float64(sz.X), Y: p.Y * float64(c.Size[1]) / float64(sz.Y)}
}

// Load reads a calibration file.
func Load(path string) (*Calibration, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var c Calibration
	if err := json.Unmarshal(b, &c); err != nil {
		return nil, err
	}
	if err := c.setup(); err != nil {
		return nil, err
	}
	return &c, nil
}

// Save writes the calibration file.
func (c *Calibration) Save(path string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	b, _ := json.MarshalIndent(c, "", " ")
	return os.WriteFile(path, b, 0o644)
}

// Refine moves a click to the centre of the dark mark near it: the weighted centroid of the
// pixels that are darker than the mid level of a window around the click. It repeats the step
// from the new centre, so that the window holds the mark evenly.
func Refine(img image.Image, p geom.Pt, r int) geom.Pt {
	q := p
	for i := 0; i < 4; i++ {
		n := refineOnce(img, q, r)
		if math.Hypot(n.X-q.X, n.Y-q.Y) < 0.05 {
			return n
		}
		q = n
	}
	return q
}

func refineOnce(img image.Image, p geom.Pt, r int) geom.Pt {
	b := img.Bounds()
	x0, y0 := int(p.X)-r, int(p.Y)-r
	x1, y1 := int(p.X)+r, int(p.Y)+r
	var vals []float64
	var xs, ys []int
	lo, sum := math.Inf(1), 0.0
	for y := y0; y <= y1; y++ {
		for x := x0; x <= x1; x++ {
			if x < b.Min.X || y < b.Min.Y || x >= b.Max.X || y >= b.Max.Y {
				continue
			}
			if (x-int(p.X))*(x-int(p.X))+(y-int(p.Y))*(y-int(p.Y)) > r*r {
				continue
			}
			cr, cg, cb, _ := img.At(x, y).RGBA()
			v := 0.299*float64(cr>>8) + 0.587*float64(cg>>8) + 0.114*float64(cb>>8)
			vals, xs, ys = append(vals, v), append(xs, x), append(ys, y)
			lo = math.Min(lo, v)
			sum += v
		}
	}
	if len(vals) == 0 {
		return p
	}
	mean := sum / float64(len(vals))
	if mean-lo < 25 {
		return p // no clear mark
	}
	thr := lo + (mean-lo)*0.5
	var wx, wy, ws float64
	for i, v := range vals {
		if v < thr {
			w := thr - v
			wx += w * (float64(xs[i]) + 0.5)
			wy += w * (float64(ys[i]) + 0.5)
			ws += w
		}
	}
	if ws == 0 {
		return p
	}
	return geom.Pt{X: wx / ws, Y: wy / ws}
}
