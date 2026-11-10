package plotter

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"image"
	"image/color"
	"image/jpeg"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// fakeDevice is a network plotter: "ok" for each G-code line, and GET /api/status.
func fakeDevice(t *testing.T) string {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	go func() {
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			go func() {
				r := bufio.NewReader(c)
				for {
					if _, err := r.ReadString('\n'); err != nil {
						return
					}
					io.WriteString(c, "ok\n")
				}
			}()
		}
	}()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/status":
			json.NewEncoder(w).Encode(map[string]any{"state": "busy", "tool": 2, "homed": true,
				"job": map[string]any{"name": "flowers", "line": 50, "total": 200}})
		case "/api/pens":
			w.Write([]byte("[]"))
		}
	}))
	t.Cleanup(func() { ln.Close(); srv.Close() })
	_, hp, _ := net.SplitHostPort(strings.TrimPrefix(srv.URL, "http://"))
	return "tcp://" + ln.Addr().String() + "?http=" + hp
}

func jpegOf(w, h int) []byte {
	img := image.NewRGBA(image.Rect(0, 0, w, h))
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			img.Set(x, y, color.RGBA{uint8(x), uint8(y), 90, 255})
		}
	}
	var b bytes.Buffer
	jpeg.Encode(&b, img, nil)
	return b.Bytes()
}

func TestMountedInDeck(t *testing.T) {
	shots := 0
	p := New(Config{Addr: fakeDevice(t), DataDir: t.TempDir(), Snapshot: func(ctx context.Context) ([]byte, error) {
		shots++
		return jpegOf(64, 48), nil
	}})
	defer p.Close()
	mux := http.NewServeMux()
	mux.Handle("/plotter/", http.StripPrefix("/plotter", p.Handler()))
	get := func(path string) *httptest.ResponseRecorder {
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, httptest.NewRequest("GET", path, nil))
		return rec
	}
	if rec := get("/plotter/"); rec.Code != 200 || !strings.Contains(rec.Body.String(), "Plotstudio") {
		t.Fatalf("the UI under /plotter/: %d", rec.Code)
	}
	if rec := get("/plotter/app.js"); rec.Code != 200 || strings.Contains(rec.Body.String(), `"/api/`) {
		t.Fatal("app.js must use relative API links")
	}
	var st map[string]any
	json.Unmarshal(get("/plotter/api/status").Body.Bytes(), &st)
	if st["connected"] != true || st["link"] != "wifi" || st["camera"] != "printdeck" {
		t.Fatalf("status: %v", st)
	}
	if rec := get("/plotter/api/camera.jpg"); rec.Code != 200 || shots == 0 {
		t.Fatalf("camera: %d, %d shots", rec.Code, shots)
	}
	s := p.Summary(context.Background())
	if !s.Online || s.State != "busy" || s.Job != "flowers" || s.Percent != 25 || s.Tool != 2 {
		t.Fatalf("summary: %+v", s)
	}
	if !PrefixOK("/plotter/") || PrefixOK("/plotter") {
		t.Fatal("PrefixOK")
	}
}

func TestOffline(t *testing.T) {
	p := New(Config{Addr: "127.0.0.1:1", DataDir: t.TempDir()})
	defer p.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if s := p.Summary(ctx); s.Online || s.State != "offline" {
		t.Fatalf("summary: %+v", s)
	}
}
