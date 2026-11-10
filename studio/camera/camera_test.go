package camera

import (
	"bytes"
	"context"
	"image"
	"image/color"
	"image/jpeg"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func testJPEG(t *testing.T) []byte {
	img := image.NewRGBA(image.Rect(0, 0, 64, 48))
	img.Set(3, 3, color.White)
	var b bytes.Buffer
	if err := jpeg.Encode(&b, img, nil); err != nil {
		t.Fatal(err)
	}
	return b.Bytes()
}

func TestHTTPAndFile(t *testing.T) {
	data := testJPEG(t)
	var full string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		full = r.URL.Query().Get("full")
		w.Write(data)
	}))
	defer srv.Close()
	src, err := Open(srv.URL + "/camera.jpg")
	if err != nil {
		t.Fatal(err)
	}
	f, err := src.Grab(context.Background(), Scan)
	if err != nil || f.W != 64 || f.H != 48 || full != "1" {
		t.Fatalf("%v %+v %q", err, f, full)
	}
	p := filepath.Join(t.TempDir(), "x.jpg")
	os.WriteFile(p, data, 0o644)
	fs, _ := Open("file:" + p)
	f, err = fs.Grab(context.Background(), Live)
	if err != nil || f.W != 64 {
		t.Fatal(err)
	}
	if _, err := f.Image(); err != nil {
		t.Fatal(err)
	}
}

func TestFixJPEGAddsTables(t *testing.T) {
	data := testJPEG(t)
	// Remove the DHT segments, as a camera does.
	var out []byte
	i := 2
	out = append(out, data[:2]...)
	for i+4 <= len(data) {
		m := data[i+1]
		n := int(data[i+2])<<8 | int(data[i+3])
		if m == 0xDA {
			out = append(out, data[i:]...)
			break
		}
		if m != 0xC4 {
			out = append(out, data[i:i+2+n]...)
		}
		i += 2 + n
	}
	if _, err := jpeg.Decode(bytes.NewReader(out)); err == nil {
		t.Log("the decoder accepts a frame with no tables")
	}
	fixed, w, h, err := FixJPEG(out)
	if err != nil || w != 64 || h != 48 {
		t.Fatal(err)
	}
	if _, err := jpeg.Decode(bytes.NewReader(fixed)); err != nil {
		t.Fatal(err)
	}
}
