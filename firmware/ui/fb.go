// Package ui draws the LCD screens and runs the menus.
//
// The UI draws into a 128x64 1-bit framebuffer. A Display backend sends the
// changed rows to the panel. The ST7920 12864 panel is the first backend.
// A later touch panel (ILI9341 or ST7796 with XPT2046) can implement Display
// with a scaled copy of the framebuffer, and send touches as Input events.
package ui

// Size of the framebuffer.
const (
	Width  = 128
	Height = 64
	Stride = Width / 8
)

// FB is a 1-bit framebuffer: row-major, 16 bytes per row, MSB is the leftmost pixel.
// The UI draws into Back. Commit copies the changed rows to Front and marks them dirty.
type FB struct {
	Back  [Stride * Height]byte
	Front [Stride * Height]byte
	dirty uint64
}

// Display sends framebuffer rows to a panel.
type Display interface {
	// Flush sends changed rows. A slow panel sends at most one row per call.
	Flush(fb *FB)
}

// Clear clears the back buffer.
func (f *FB) Clear() {
	for i := range f.Back {
		f.Back[i] = 0
	}
}

// Set sets or clears one pixel.
func (f *FB) Set(x, y int, on bool) {
	if x < 0 || y < 0 || x >= Width || y >= Height {
		return
	}
	i := y*Stride + x/8
	m := byte(0x80) >> (x & 7)
	if on {
		f.Back[i] |= m
	} else {
		f.Back[i] &^= m
	}
}

// Fill sets or clears a rectangle.
func (f *FB) Fill(x, y, w, h int, on bool) {
	for j := y; j < y+h; j++ {
		for i := x; i < x+w; i++ {
			f.Set(i, j, on)
		}
	}
}

// Rect draws the outline of a rectangle.
func (f *FB) Rect(x, y, w, h int) {
	f.Fill(x, y, w, 1, true)
	f.Fill(x, y+h-1, w, 1, true)
	f.Fill(x, y, 1, h, true)
	f.Fill(x+w-1, y, 1, h, true)
}

// Text draws s at (x, y) with the 5x7 font in 6x8 cells.
// Scale 2 doubles the size. on false draws dark text on a lit area.
// It returns the x position after the text.
func (f *FB) Text(x, y int, s string, scale int, on bool) int {
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c < 32 || c > 127 {
			c = '?'
		}
		g := font[int(c-32)*5 : int(c-32)*5+5]
		for col := 0; col < 5; col++ {
			bits := g[col]
			for row := 0; row < 7; row++ {
				if bits&(1<<row) != 0 {
					for dy := 0; dy < scale; dy++ {
						for dx := 0; dx < scale; dx++ {
							f.Set(x+col*scale+dx, y+row*scale+dy, on)
						}
					}
				}
			}
		}
		x += 6 * scale
	}
	return x
}

// Commit copies the back buffer to the front buffer and marks the changed rows.
func (f *FB) Commit() {
	for y := 0; y < Height; y++ {
		r := y * Stride
		for i := 0; i < Stride; i++ {
			if f.Back[r+i] != f.Front[r+i] {
				copy(f.Front[r:r+Stride], f.Back[r:r+Stride])
				f.dirty |= 1 << y
				break
			}
		}
	}
}

// Invalidate marks all rows dirty, for example after a panel reset.
func (f *FB) Invalidate() { f.dirty = ^uint64(0) }

// Dirty tells if a row waits for the panel.
func (f *FB) Dirty() bool { return f.dirty != 0 }

// NextDirty returns the first dirty row and clears its mark.
func (f *FB) NextDirty() (y int, row []byte, ok bool) {
	if f.dirty == 0 {
		return 0, nil, false
	}
	for y = 0; y < Height; y++ {
		if f.dirty&(1<<y) != 0 {
			f.dirty &^= 1 << y
			return y, f.Front[y*Stride : y*Stride+Stride], true
		}
	}
	return 0, nil, false
}
