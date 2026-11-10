package sim

import (
	"bytes"
	"encoding/json"
	"image"
	"image/color"
	"image/jpeg"
	"math"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"sync"

	"github.com/beetlebugorg/penplotter/firmware/config"
)

// Camera renders the picture of a camera above the plotter. The camera stands on a mast at
// the back of the frame and looks down at the table. The picture shows the table, the cutting
// mat, the frame, the paper with a document, the ink, and the gantry at its present position.
// plotstudio uses it to test the scan and the calibration.
//
// Frame coordinates (hardware/stl/frame.json): the origin is the front left outer corner of
// the frame, on the table. X to the right, Y to the back, Z up.
type Camera struct {
	m   *Machine
	opt CameraOptions
	geo frameGeo

	fx, fy, cx, cy float64
	pos, fwd       vec3
	right, down    vec3
}

// CameraOptions set up the simulated camera.
type CameraOptions struct {
	W, H       int         // the live picture size (default 1296 x 972)
	FullW      int         // the scan picture size, for ?full=1 (default 2592 x 1944)
	FullH      int         //
	Pos        [3]float64  // camera position (default 200, 560, 400)
	Target     [3]float64  // the point at the centre of the picture (default 200, 300, 0: the whole frame opening is in the picture)
	FOV        [2]float64  // degrees across and up (default 65 x 52)
	Roll       float64     // degrees (default 1)
	K1         float64     // radial distortion of the picture (0 = none, -0.08 = barrel)
	FramePath  string      // frame.json; it can be empty
	Doc        image.Image // a picture of the document on the paper, or nil for the built-in form
	PaperX     float64     // the paper centre, in machine mm (default 113, 182)
	PaperY     float64     //
	PaperAngle float64     // degrees (default 3)
	PaperW     float64     // mm (default 210 x 297, A4 portrait)
	PaperH     float64     //
}

type vec3 [3]float64

func (a vec3) add(b vec3) vec3    { return vec3{a[0] + b[0], a[1] + b[1], a[2] + b[2]} }
func (a vec3) sub(b vec3) vec3    { return vec3{a[0] - b[0], a[1] - b[1], a[2] - b[2]} }
func (a vec3) mul(s float64) vec3 { return vec3{a[0] * s, a[1] * s, a[2] * s} }
func (a vec3) dot(b vec3) float64 { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] }
func (a vec3) cross(b vec3) vec3 {
	return vec3{a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]}
}
func (a vec3) norm() vec3 { return a.mul(1 / math.Sqrt(a.dot(a))) }

type box struct {
	min, max vec3
	col      [3]float64
}

type frameGeo struct {
	boxes     []box
	homePen   [2]float64
	carriageY float64
	carriageX float64
	camPos    *[3]float64 // the camera on the mast, from frame.json; nil if it is not there
}

func defaultGeo() frameGeo {
	dark := [3]float64{44, 46, 50}
	return frameGeo{
		boxes: []box{
			{vec3{0, 0, 17}, vec3{400, 20, 57}, dark},
			{vec3{0, 500, 17}, vec3{400, 520, 57}, dark},
			{vec3{0, 20, 37}, vec3{40, 500, 57}, dark},
			{vec3{360, 20, 37}, vec3{400, 500, 57}, dark},
		},
		homePen: [2]float64{81.2, 36.1}, carriageY: 78.05, carriageX: 82.0,
	}
}

func loadGeo(path string) frameGeo {
	g := defaultGeo()
	b, err := os.ReadFile(path)
	if err != nil {
		return g
	}
	var f struct {
		Bars, Rails []struct {
			Box []float64 `json:"box"`
		}
		HomePen    []float64 `json:"home_pen"`
		CarriageY0 *float64  `json:"carriage_y0"`
		CarriageX0 *float64  `json:"carriage_x0"`
		Camera     *struct {
			Pos []float64 `json:"pos"`
		} `json:"camera"`
	}
	if json.Unmarshal(b, &f) != nil {
		return g
	}
	var boxes []box
	for _, x := range append(f.Bars, f.Rails...) {
		if len(x.Box) == 6 {
			boxes = append(boxes, box{vec3{x.Box[0], x.Box[1], x.Box[2]}, vec3{x.Box[3], x.Box[4], x.Box[5]}, [3]float64{44, 46, 50}})
		}
	}
	if len(boxes) > 0 {
		g.boxes = boxes
	}
	if len(f.HomePen) == 2 {
		g.homePen = [2]float64{f.HomePen[0], f.HomePen[1]}
	}
	if f.CarriageY0 != nil {
		g.carriageY = *f.CarriageY0
	}
	if f.CarriageX0 != nil {
		g.carriageX = *f.CarriageX0
	}
	if f.Camera != nil && len(f.Camera.Pos) == 3 {
		g.camPos = &[3]float64{f.Camera.Pos[0], f.Camera.Pos[1], f.Camera.Pos[2]}
	}
	return g
}

// NewCamera makes the camera of machine m.
func NewCamera(m *Machine, o CameraOptions) *Camera {
	if o.W == 0 {
		o.W, o.H = 1296, 972
	}
	if o.FullW == 0 {
		o.FullW, o.FullH = 2592, 1944
	}
	geo := loadGeo(o.FramePath)
	if o.Pos == ([3]float64{}) {
		// The camera on the mast (frame.json), else the first mast position.
		o.Pos = [3]float64{200, 560, 400}
		if geo.camPos != nil {
			o.Pos = *geo.camPos
		}
	}
	if o.Target == ([3]float64{}) {
		o.Target = [3]float64{200, 300, 0}
	}
	if o.FOV == ([2]float64{}) {
		o.FOV = [2]float64{65, 52}
	}
	if o.PaperW == 0 {
		o.PaperW, o.PaperH = 210, 297
	}
	if o.PaperX == 0 && o.PaperY == 0 {
		o.PaperX, o.PaperY, o.PaperAngle = 113, 182, 3
	}
	c := &Camera{m: m, opt: o, geo: geo}
	c.pos = vec3(o.Pos)
	c.fwd = vec3(o.Target).sub(c.pos).norm()
	r := c.fwd.cross(vec3{0, 0, 1}).norm()
	d := c.fwd.cross(r).norm()
	a := o.Roll * math.Pi / 180
	c.right = r.mul(math.Cos(a)).add(d.mul(math.Sin(a)))
	c.down = d.mul(math.Cos(a)).sub(r.mul(math.Sin(a)))
	return c
}

// intrinsics returns the focal lengths and the centre for a picture of w x h.
func (c *Camera) intrinsics(w, h int) (fx, fy, cx, cy float64) {
	fx = float64(w) / 2 / math.Tan(c.opt.FOV[0]/2*math.Pi/180)
	fy = float64(h) / 2 / math.Tan(c.opt.FOV[1]/2*math.Pi/180)
	return fx, fy, float64(w) / 2, float64(h) / 2
}

// lens: normalised by half the diagonal, as in plotstudio. ideal = observed·(1 + K1 r²).
func (c *Camera) undistort(u, v float64, w, h int) (float64, float64) {
	if c.opt.K1 == 0 {
		return u, v
	}
	cx, cy, s := float64(w)/2, float64(h)/2, math.Hypot(float64(w), float64(h))/2
	x, y := (u-cx)/s, (v-cy)/s
	f := 1 + c.opt.K1*(x*x+y*y)
	return cx + x*f*s, cy + y*f*s
}

func (c *Camera) distort(u, v float64, w, h int) (float64, float64) {
	if c.opt.K1 == 0 {
		return u, v
	}
	cx, cy, s := float64(w)/2, float64(h)/2, math.Hypot(float64(w), float64(h))/2
	qu, qv := (u-cx)/s, (v-cy)/s
	x, y := qu, qv
	for i := 0; i < 20; i++ {
		f := 1 + c.opt.K1*(x*x+y*y)
		x, y = qu/f, qv/f
	}
	return cx + x*s, cy + y*s
}

// Project returns the picture point (w x h picture) of a frame point.
func (c *Camera) Project(p vec3, w, h int) (float64, float64, bool) {
	fx, fy, cx, cy := c.intrinsics(w, h)
	d := p.sub(c.pos)
	z := d.dot(c.fwd)
	if z <= 0 {
		return 0, 0, false
	}
	u := cx + fx*d.dot(c.right)/z
	v := cy + fy*d.dot(c.down)/z
	u, v = c.distort(u, v, w, h)
	return u, v, true
}

// scene is the state for one picture.
type scene struct {
	c       *Camera
	boxes   []box
	ink     []uint8 // the ink mask in machine mm, inkRes px per mm
	inkW    int
	inkH    int
	paper   [5]float64 // centre x, y (frame), cos, sin, angle
	homePen [2]float64
}

const (
	inkRes    = 4.0
	inkMargin = 10.0
)

func (c *Camera) newScene() *scene {
	s := &scene{c: c, homePen: c.geo.homePen}
	s.boxes = append(s.boxes, c.geo.boxes...)
	snap := c.m.Snapshot()
	ym := float64(snap.Y+snap.Y2) / 2
	cy := c.geo.carriageY + ym
	xp := c.geo.carriageX + float64(snap.X)
	orange := [3]float64{232, 119, 46}
	grey := [3]float64{176, 178, 182}
	dark := [3]float64{38, 38, 40}
	// The Y carriages on their V-wheels with the towers, the 2020 beam, the stock X carriage
	// plate, and the pen carriage. The boxes are simple envelopes of the parts in hardware/
	// (hardware/stl/sim2), relative to the beam centre (cy) and the plate origin (xp).
	for _, sx := range []float64{1, -1} {
		mx := func(x0, x1 float64) (float64, float64) {
			if sx > 0 {
				return x0, x1
			}
			return 400 - x1, 400 - x0
		}
		a, b := mx(-24, 58)
		s.boxes = append(s.boxes, box{vec3{a, cy - 37, 58}, vec3{b, cy + 30, 64}, orange})
		a, b = mx(-14, 28)
		s.boxes = append(s.boxes, box{vec3{a, cy - 21, 64}, vec3{b, cy + 21, 161}, orange})
	}
	s.boxes = append(s.boxes,
		box{vec3{-7.5, cy - 10, 88.6}, vec3{407.5, cy + 10, 108.6}, dark},
		box{vec3{xp - 41.5, cy - 13.6, 66.7}, vec3{xp + 55.2, cy + 8.9, 143.3}, grey},
		box{vec3{xp - 40, cy - 37.6, 17.5}, vec3{xp + 37.5, cy - 13.6, 139}, orange},
	)
	px := s.homePen[0] + float64(snap.X)
	py := s.homePen[1] + ym
	lift := float64(1-snap.Pen) * 7
	if snap.LiftOK {
		lift = float64(snap.Lift) // the linkage model (frame.json pen_lift)
	}
	s.boxes = append(s.boxes, box{vec3{px - 6, py - 6, lift + 2}, vec3{px + 6, py + 6, 150}, dark})
	// The ink.
	tx, ty := float64(config.TravelX), float64(config.TravelY)
	s.inkW = int((tx + 2*inkMargin) * inkRes)
	s.inkH = int((ty + 2*inkMargin) * inkRes)
	s.ink = make([]uint8, s.inkW*s.inkH)
	segs, _, _ := c.m.Ink(0)
	for _, g := range segs {
		s.stroke(float64(g[0]), float64(g[1]), float64(g[2]), float64(g[3]))
	}
	o := c.opt
	a := o.PaperAngle
	ar := a * math.Pi / 180
	s.paper = [5]float64{s.homePen[0] + o.PaperX, s.homePen[1] + o.PaperY, math.Cos(ar), math.Sin(ar), a}
	return s
}

func (s *scene) stroke(x0, y0, x1, y1 float64) {
	const r = 1.3 // px: a line about 0.65 mm wide
	toPx := func(x, y float64) (float64, float64) {
		return (x + inkMargin) * inkRes, (y + inkMargin) * inkRes
	}
	ax, ay := toPx(x0, y0)
	bx, by := toPx(x1, y1)
	n := int(math.Ceil(math.Hypot(bx-ax, by-ay)/0.5)) + 1
	for i := 0; i <= n; i++ {
		t := float64(i) / float64(n)
		cx, cy := ax+(bx-ax)*t, ay+(by-ay)*t
		for yy := int(cy - r); yy <= int(cy+r)+1; yy++ {
			for xx := int(cx - r); xx <= int(cx+r)+1; xx++ {
				if xx < 0 || yy < 0 || xx >= s.inkW || yy >= s.inkH {
					continue
				}
				if (float64(xx)+0.5-cx)*(float64(xx)+0.5-cx)+(float64(yy)+0.5-cy)*(float64(yy)+0.5-cy) <= r*r {
					s.ink[yy*s.inkW+xx] = 1
				}
			}
		}
	}
}

// table returns the colour of the table plane at frame point (x, y).
func (s *scene) table(x, y float64) [3]float64 {
	// Ink.
	mx, my := x-s.homePen[0], y-s.homePen[1]
	ix, iy := int((mx+inkMargin)*inkRes), int((my+inkMargin)*inkRes)
	if ix >= 0 && iy >= 0 && ix < s.inkW && iy < s.inkH && s.ink[iy*s.inkW+ix] != 0 {
		return [3]float64{24, 34, 110}
	}
	// Paper and document.
	o := s.c.opt
	rx, ry := x-s.paper[0], y-s.paper[1]
	a := rx*s.paper[2] + ry*s.paper[3]
	b := -rx*s.paper[3] + ry*s.paper[2]
	u, v := a+o.PaperW/2, o.PaperH/2-b
	if u >= 0 && u <= o.PaperW && v >= 0 && v <= o.PaperH {
		return s.document(u, v)
	}
	// The cutting mat, under the frame.
	if math.Abs(x-200) <= 228.5 && math.Abs(y-260) <= 305 {
		g := [3]float64{188, 196, 190}
		lx := math.Mod(x-200+228.5, 25.4)
		ly := math.Mod(y-260+305, 25.4)
		if lx < 0.5 || ly < 0.5 {
			g = [3]float64{150, 160, 154}
		}
		return g
	}
	// Wood.
	gr := math.Sin(y*0.045+math.Sin(x*0.013)*2.5)*10 + math.Sin(y*0.31)*4
	return [3]float64{168 + gr, 120 + gr*0.8, 78 + gr*0.5}
}

// document returns the colour of the paper at (u, v): mm from the top left corner.
func (s *scene) document(u, v float64) [3]float64 {
	white := [3]float64{246, 246, 242}
	o := s.c.opt
	if o.Doc != nil {
		b := o.Doc.Bounds()
		px := b.Min.X + int(u/o.PaperW*float64(b.Dx()))
		py := b.Min.Y + int(v/o.PaperH*float64(b.Dy()))
		r, g, bl, _ := o.Doc.At(min(px, b.Max.X-1), min(py, b.Max.Y-1)).RGBA()
		return [3]float64{float64(r >> 8), float64(g >> 8), float64(bl >> 8)}
	}
	ink := [3]float64{40, 40, 46}
	grey := [3]float64{160, 160, 166}
	in := func(u0, u1, v0, v1 float64) bool { return u >= u0 && u <= u1 && v >= v0 && v <= v1 }
	switch {
	case in(20, 110, 16, 24):
		return ink // the title
	case in(150, 190, 16, 20):
		return grey
	}
	for k := 0; k < 16; k++ {
		vv := 40 + 7*float64(k)
		end := 190 - float64((k*37)%55)
		if k%5 == 4 {
			end = 120
		}
		if in(20, end, vv, vv+2.2) {
			return grey
		}
	}
	// The signature line with an X, and the date line.
	if in(105, 190, 239.6, 240.4) || in(20, 80, 239.6, 240.4) {
		return ink
	}
	if in(105, 135, 243, 245) || in(20, 40, 243, 245) {
		return grey
	}
	if u >= 107 && u <= 114 && v >= 231 && v <= 238 {
		d1 := math.Abs((u - 107) - (v - 231))
		d2 := math.Abs((u - 107) - (238 - v))
		if d1 < 0.7 || d2 < 0.7 {
			return ink
		}
	}
	return white
}

func (b box) hit(o, d vec3) (float64, vec3, bool) {
	tmin, tmax := -math.MaxFloat64, math.MaxFloat64
	var n vec3
	for i := 0; i < 3; i++ {
		if math.Abs(d[i]) < 1e-12 {
			if o[i] < b.min[i] || o[i] > b.max[i] {
				return 0, n, false
			}
			continue
		}
		t1 := (b.min[i] - o[i]) / d[i]
		t2 := (b.max[i] - o[i]) / d[i]
		sgn := -1.0
		if t1 > t2 {
			t1, t2 = t2, t1
			sgn = 1
		}
		if t1 > tmin {
			tmin = t1
			n = vec3{}
			n[i] = sgn
		}
		tmax = math.Min(tmax, t2)
		if tmin > tmax {
			return 0, n, false
		}
	}
	if tmin <= 0 {
		return 0, n, false
	}
	return tmin, n, true
}

var light = vec3{0.3, -0.45, 1}.norm()

func (s *scene) shade(d vec3) [3]float64 {
	best := math.MaxFloat64
	var col [3]float64
	var nrm vec3
	hit := false
	for _, b := range s.boxes {
		if t, n, ok := b.hit(s.c.pos, d); ok && t < best {
			best, col, nrm, hit = t, b.col, n, true
		}
	}
	if d[2] < 0 {
		if t := -s.c.pos[2] / d[2]; t < best {
			p := s.c.pos.add(d.mul(t))
			return s.table(p[0], p[1])
		}
	}
	if !hit {
		return [3]float64{60, 64, 70}
	}
	k := 0.55 + 0.45*math.Max(0, nrm.dot(light))
	return [3]float64{col[0] * k, col[1] * k, col[2] * k}
}

// Render draws a picture of w x h.
func (c *Camera) Render(w, h int) *image.RGBA {
	s := c.newScene()
	fx, fy, cx, cy := c.intrinsics(w, h)
	img := image.NewRGBA(image.Rect(0, 0, w, h))
	rows := make(chan int, h)
	for y := 0; y < h; y++ {
		rows <- y
	}
	close(rows)
	var wg sync.WaitGroup
	for k := 0; k < runtime.NumCPU(); k++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for y := range rows {
				for x := 0; x < w; x++ {
					// 2 x 2 samples in each pixel: thin ink lines do not break up.
					var col [3]float64
					for _, o := range [4][2]float64{{0.25, 0.25}, {0.75, 0.25}, {0.25, 0.75}, {0.75, 0.75}} {
						u, v := c.undistort(float64(x)+o[0], float64(y)+o[1], w, h)
						d := c.fwd.add(c.right.mul((u - cx) / fx)).add(c.down.mul((v - cy) / fy)).norm()
						k := s.shade(d)
						col[0], col[1], col[2] = col[0]+k[0]/4, col[1]+k[1]/4, col[2]+k[2]/4
					}
					img.SetRGBA(x, y, color.RGBA{clamp8(col[0]), clamp8(col[1]), clamp8(col[2]), 255})
				}
			}
		}()
	}
	wg.Wait()
	return img
}

func clamp8(v float64) uint8 { return uint8(math.Max(0, math.Min(255, math.Round(v)))) }

// ServeHTTP serves /camera.jpg (?full=1 for the scan size), /camera.json (the camera data) and
// /camera/project?x=&y= (the picture point of a machine point on the table, for tests).
func (c *Camera) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	full := r.URL.Query().Get("full") == "1"
	pw, ph := c.opt.W, c.opt.H
	if full {
		pw, ph = c.opt.FullW, c.opt.FullH
	}
	switch r.URL.Path {
	case "/camera.jpg":
		img := c.Render(pw, ph)
		var b bytes.Buffer
		jpeg.Encode(&b, img, &jpeg.Options{Quality: 88})
		w.Header().Set("Content-Type", "image/jpeg")
		w.Header().Set("Cache-Control", "no-store")
		w.Write(b.Bytes())
	case "/camera.json":
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"size": []int{c.opt.W, c.opt.H}, "full": []int{c.opt.FullW, c.opt.FullH},
			"pos": c.opt.Pos, "target": c.opt.Target, "fov": c.opt.FOV, "k1": c.opt.K1,
			"home_pen": c.geo.homePen,
		})
	case "/camera/project":
		x, _ := strconv.ParseFloat(r.URL.Query().Get("x"), 64)
		y, _ := strconv.ParseFloat(r.URL.Query().Get("y"), 64)
		p := vec3{c.geo.homePen[0] + x, c.geo.homePen[1] + y, 0}
		u, v, ok := c.Project(p, pw, ph)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"u": u, "v": v, "ok": ok, "w": pw, "h": ph})
	default:
		http.NotFound(w, r)
	}
}
