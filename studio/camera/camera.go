// Package camera grabs pictures for plotstudio: from a V4L2 webcam (Linux, pure Go), from an
// HTTP URL that returns a JPEG (the simulator, an IP camera), or from an image file.
package camera

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"image"
	"image/jpeg"
	_ "image/png" // decode PNG files and URLs
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

// Mode selects the picture size.
type Mode int

const (
	Live Mode = iota // a quick picture for the live view (about 1920 x 1080 at most)
	Scan             // the largest picture, for the scan of the bed
)

// Frame is one picture.
type Frame struct {
	JPEG []byte
	W, H int
	img  image.Image
}

// Image decodes the frame (once).
func (f *Frame) Image() (image.Image, error) {
	if f.img != nil {
		return f.img, nil
	}
	img, _, err := image.Decode(bytes.NewReader(f.JPEG))
	if err != nil {
		return nil, err
	}
	f.img = img
	return img, nil
}

// FromImage makes a frame from a decoded picture.
func FromImage(img image.Image) (*Frame, error) {
	var b bytes.Buffer
	if err := jpeg.Encode(&b, img, &jpeg.Options{Quality: 90}); err != nil {
		return nil, err
	}
	r := img.Bounds()
	return &Frame{JPEG: b.Bytes(), W: r.Dx(), H: r.Dy(), img: img}, nil
}

// Source gives pictures.
type Source interface {
	Grab(ctx context.Context, m Mode) (*Frame, error)
	Name() string
	Close() error
}

// Focus is the lens control of a camera.
type Focus struct {
	Has  bool `json:"has"`
	Auto bool `json:"auto"`
	Pos  int  `json:"pos"`
	Min  int  `json:"min"`
	Max  int  `json:"max"`
}

// Controller is a source with lens and exposure controls (the V4L2 source).
type Controller interface {
	Focus() (Focus, error)
	// SetFocus sets autofocus on, or a fixed lens position.
	SetFocus(auto bool, pos int) error
	// Lock fixes the exposure and the white balance at their present values (on), or gives them
	// back to the camera (off).
	Lock(on bool) error
}

// Open opens a source: "file:<path>", "http://..." or "https://...", or a V4L2 device path
// ("/dev/video0") or number ("0").
func Open(spec string) (Source, error) {
	switch {
	case spec == "":
		return nil, errors.New("camera: no camera given")
	case strings.HasPrefix(spec, "http://") || strings.HasPrefix(spec, "https://"):
		return &HTTP{URL: spec}, nil
	case strings.HasPrefix(spec, "file:"):
		return &File{Path: strings.TrimPrefix(spec, "file:")}, nil
	}
	if !strings.HasPrefix(spec, "/") {
		spec = "/dev/video" + spec
	}
	v, err := OpenV4L2(spec)
	if err != nil {
		return nil, err
	}
	return v, nil
}

// HTTP grabs a JPEG (or PNG) picture from a URL. A Scan adds "full=1" to the query, which
// the simulator uses for its large picture.
type HTTP struct {
	URL    string
	Client *http.Client
}

func (h *HTTP) Name() string { return h.URL }
func (h *HTTP) Close() error { return nil }

func (h *HTTP) Grab(ctx context.Context, m Mode) (*Frame, error) {
	u := h.URL
	if m == Scan {
		if strings.Contains(u, "?") {
			u += "&full=1"
		} else {
			u += "?full=1"
		}
	}
	req, err := http.NewRequestWithContext(ctx, "GET", u, nil)
	if err != nil {
		return nil, err
	}
	c := h.Client
	if c == nil {
		c = &http.Client{Timeout: 20 * time.Second}
	}
	resp, err := c.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("camera: %s: %s", u, resp.Status)
	}
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	return decodeBytes(b)
}

// File reads a picture file at each grab.
type File struct{ Path string }

func (f *File) Name() string { return "file:" + f.Path }
func (f *File) Close() error { return nil }

func (f *File) Grab(ctx context.Context, m Mode) (*Frame, error) {
	b, err := os.ReadFile(f.Path)
	if err != nil {
		return nil, err
	}
	return decodeBytes(b)
}

func decodeBytes(b []byte) (*Frame, error) {
	if len(b) > 2 && b[0] == 0xFF && b[1] == 0xD8 {
		fixed, w, h, err := FixJPEG(b)
		if err == nil {
			return &Frame{JPEG: fixed, W: w, H: h}, nil
		}
	}
	img, _, err := image.Decode(bytes.NewReader(b))
	if err != nil {
		return nil, fmt.Errorf("camera: decode: %w", err)
	}
	return FromImage(img)
}

// Image2Size returns the picture size as a point.
func (f *Frame) Image2Size() image.Point { return image.Pt(f.W, f.H) }
