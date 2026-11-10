package geom

import (
	"image"
	"image/color"
	"image/draw"
	"math"
	"runtime"
	"sync"
)

// Warp makes a w x h image. Each output pixel (px + 0.5, py + 0.5) maps through outToSrc to a
// point in src, which is sampled with bilinear filtering. Points outside src get bg.
func Warp(src image.Image, outToSrc H, w, h int, bg color.RGBA) *image.RGBA {
	return WarpFunc(src, outToSrc.Apply, w, h, bg)
}

// WarpFunc is Warp with any map from output pixels to source pixels.
func WarpFunc(src image.Image, outToSrc func(Pt) Pt, w, h int, bg color.RGBA) *image.RGBA {
	in := toRGBA(src)
	b := in.Bounds()
	out := image.NewRGBA(image.Rect(0, 0, w, h))
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
					p := outToSrc(Pt{float64(x) + 0.5, float64(y) + 0.5})
					out.SetRGBA(x, y, bilinear(in, b, p.X-0.5, p.Y-0.5, bg))
				}
			}
		}()
	}
	wg.Wait()
	return out
}

func toRGBA(src image.Image) *image.RGBA {
	if r, ok := src.(*image.RGBA); ok {
		return r
	}
	b := src.Bounds()
	r := image.NewRGBA(b)
	draw.Draw(r, b, src, b.Min, draw.Src)
	return r
}

func bilinear(img *image.RGBA, b image.Rectangle, x, y float64, bg color.RGBA) color.RGBA {
	if math.IsNaN(x) || math.IsInf(x, 0) || math.IsNaN(y) || math.IsInf(y, 0) {
		return bg
	}
	x0, y0 := int(math.Floor(x)), int(math.Floor(y))
	if x0 < b.Min.X-1 || y0 < b.Min.Y-1 || x0 >= b.Max.X || y0 >= b.Max.Y {
		return bg
	}
	fx, fy := x-float64(x0), y-float64(y0)
	at := func(px, py int) [4]float64 {
		if px < b.Min.X || py < b.Min.Y || px >= b.Max.X || py >= b.Max.Y {
			return [4]float64{float64(bg.R), float64(bg.G), float64(bg.B), float64(bg.A)}
		}
		i := img.PixOffset(px, py)
		s := img.Pix[i : i+4 : i+4]
		return [4]float64{float64(s[0]), float64(s[1]), float64(s[2]), float64(s[3])}
	}
	c00, c10, c01, c11 := at(x0, y0), at(x0+1, y0), at(x0, y0+1), at(x0+1, y0+1)
	var o [4]uint8
	for k := 0; k < 4; k++ {
		v := c00[k]*(1-fx)*(1-fy) + c10[k]*fx*(1-fy) + c01[k]*(1-fx)*fy + c11[k]*fx*fy
		o[k] = uint8(math.Round(math.Max(0, math.Min(255, v))))
	}
	return color.RGBA{o[0], o[1], o[2], o[3]}
}
