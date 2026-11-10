// Command plotsim runs the pen plotter firmware in a simulator.
// It opens two windows: the LCD with the knob, and the machine in 3D.
//
//	go run ./sim/cmd/plotsim [-board mega|pico] [-gcode file] [-speed N] [-addr host:port] [-web dir] [-no-open]
//
// -board mega (the default) runs the firmware of the stock CR-10 V3 mainboard. The serial
// device and the TCP port stand in for its USB port. -board pico runs the Pico W firmware,
// with port 23 and the HTTP API.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"image"
	_ "image/jpeg"
	_ "image/png"
	"io/fs"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/sim"
)

func main() {
	board := flag.String("board", "mega", "board: mega (stock CR-10 V3 mainboard) or pico (Pico W firmware)")
	addr := flag.String("addr", "127.0.0.1:8765", "HTTP address")
	gcodeFile := flag.String("gcode", "", "G-code file to plot at start")
	speed := flag.Int("speed", 1, "simulation speed factor (1..100)")
	webDir := flag.String("web", "", "serve the window files from this directory (for development)")
	stlDir := flag.String("stl", "", "directory of the part STL files (default: hardware/stl of the repository)")
	link := flag.String("link", "", "make a symbolic link with this name to the serial device")
	noOpen := flag.Bool("no-open", false, "do not open the windows")
	camSize := flag.String("cam-size", "1296x972", "size of the simulated camera picture (the scan uses 2592x1944)")
	camK1 := flag.Float64("cam-k1", 0, "barrel distortion of the simulated camera (for example -0.08)")
	paper := flag.String("paper", "", "paper centre and angle in machine mm and degrees: x,y,deg (default 113,182,3)")
	doc := flag.String("doc", "", "PNG or JPEG picture of the document on the paper (default: a form with a signature line)")
	tcpAddr := flag.String("tcp", "127.0.0.1:2323", "TCP address for G-code clients: the USB port of the stock board, or port 23 of the Pico W (empty: off)")
	settingsPath := flag.String("settings", "", "settings file (M500), as the EEPROM or the flash (default: a file for each board; \"-\": RAM only)")
	flag.Parse()

	b := sim.Board(*board)
	if b != sim.BoardMega && b != sim.BoardPico {
		log.Fatalf("-board: %q is not mega or pico", *board)
	}
	if *settingsPath == "" {
		*settingsPath = sim.DefaultSettingsPath(b)
	}
	o := sim.Options{Board: b}
	if *settingsPath != "-" {
		st := sim.FileStore{Path: *settingsPath}
		if b == sim.BoardPico {
			o.Store = st
		} else {
			o.EEPROM = st
		}
	}
	m := sim.NewOpts(o)
	fmt.Println("plotsim: board " + string(b))
	m.SetHTTPAddr(*addr)
	if *tcpAddr != "" {
		if err := m.ServeTCP(*tcpAddr); err != nil {
			log.Fatal(err)
		}
		fmt.Println("plotsim: G-code over TCP at " + *tcpAddr)
		if b == sim.BoardMega {
			fmt.Println("plotsim: plotstudio -port tcp://" + *tcpAddr)
		}
	}
	m.SetSpeed(*speed)

	tty, err := m.StartPTY(*link)
	if err != nil {
		log.Printf("no serial device: %v", err)
	}

	var web fs.FS = sim.WebFS()
	if *webDir != "" {
		web = os.DirFS(*webDir)
	}
	if *stlDir == "" {
		if root := repoRoot(); root != "" {
			*stlDir = filepath.Join(root, "hardware", "stl")
		}
	}
	if st, err := os.Stat(*stlDir); err != nil || !st.IsDir() {
		*stlDir = ""
	}

	if *stlDir != "" {
		checkFrame(filepath.Join(*stlDir, "frame.json"))
		// The pen lift linkage: the pen inks when the horn tip is below the tab.
		if t, err := sim.LoadPenLink(filepath.Join(*stlDir, "frame.json")); err == nil {
			m.SetPenLink(t)
			fmt.Println("plotsim: pen lift linkage from frame.json")
		} else {
			log.Printf("pen lift: %v (the pen inks at 90 %% of the servo move)", err)
		}
	}

	ln, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatal(err)
	}
	srv := sim.NewServer(m, web, *stlDir)
	co := sim.CameraOptions{K1: *camK1}
	fmt.Sscanf(*camSize, "%dx%d", &co.W, &co.H)
	if *stlDir != "" {
		co.FramePath = filepath.Join(*stlDir, "frame.json")
	}
	if *paper != "" {
		fmt.Sscanf(*paper, "%g,%g,%g", &co.PaperX, &co.PaperY, &co.PaperAngle)
	}
	if *doc != "" {
		f, err := os.Open(*doc)
		if err != nil {
			log.Fatal(err)
		}
		img, _, err := image.Decode(f)
		f.Close()
		if err != nil {
			log.Fatalf("-doc: %v", err)
		}
		co.Doc = img
	}
	srv.Camera = sim.NewCamera(m, co)
	go func() { log.Fatal(http.Serve(ln, srv.Handler())) }()

	base := "http://" + ln.Addr().String()
	fmt.Printf("plotsim: %s/lcd.html and %s/machine.html\n", base, base)
	fmt.Printf("plotsim: camera %s/camera.jpg\n", base)
	if tty != "" {
		fmt.Printf("plotsim: serial device %s\n", tty)
	}
	if !*noOpen {
		openApp(base+"/machine.html", "1280,900")
		time.Sleep(400 * time.Millisecond)
		openApp(base+"/lcd.html", "560,460")
	}
	if *gcodeFile != "" {
		b, err := os.ReadFile(*gcodeFile)
		if err != nil {
			log.Fatal(err)
		}
		time.Sleep(time.Second)
		if err := m.StartJob(filepath.Base(*gcodeFile), string(b)); err != nil {
			log.Print(err)
		}
	}
	select {}
}

// checkFrame logs a warning if the firmware travel is larger than the travel in frame.json.
// It looks for a "travel" key at any depth, as [x, y] or {"x": .., "y": ..}.
func checkFrame(path string) {
	b, err := os.ReadFile(path)
	if err != nil {
		return
	}
	var doc any
	if json.Unmarshal(b, &doc) != nil {
		log.Printf("frame.json: not valid JSON")
		return
	}
	var find func(v any) (float64, float64, bool)
	find = func(v any) (float64, float64, bool) {
		switch t := v.(type) {
		case map[string]any:
			if tr, ok := t["travel"]; ok {
				switch u := tr.(type) {
				case []any:
					if len(u) >= 2 {
						x, ok1 := u[0].(float64)
						y, ok2 := u[1].(float64)
						return x, y, ok1 && ok2
					}
				case map[string]any:
					x, ok1 := u["x"].(float64)
					y, ok2 := u["y"].(float64)
					return x, y, ok1 && ok2
				}
			}
			for _, c := range t {
				if x, y, ok := find(c); ok {
					return x, y, true
				}
			}
		case []any:
			for _, c := range t {
				if x, y, ok := find(c); ok {
					return x, y, true
				}
			}
		}
		return 0, 0, false
	}
	x, y, ok := find(doc)
	// The firmware travel can be a little smaller than the travel of the model, not larger.
	if ok && (config.TravelX > x || config.TravelY > y) {
		log.Printf("warning: the firmware travel %dx%d mm is larger than the frame.json travel %gx%g mm",
			config.TravelX, config.TravelY, x, y)
	}
}

// repoRoot finds the directory with go.mod above the working directory.
func repoRoot() string {
	d, _ := os.Getwd()
	for d != "/" && d != "" {
		if _, err := os.Stat(filepath.Join(d, "go.mod")); err == nil {
			return d
		}
		d = filepath.Dir(d)
	}
	return ""
}

// openApp opens url in an app window. It tries Chromium, then Chrome, then xdg-open.
func openApp(url, size string) {
	cache, _ := os.UserCacheDir()
	profile := filepath.Join(cache, "penplotter-sim", "browser")
	for _, b := range []string{"chromium", "chromium-browser", "google-chrome", "google-chrome-stable"} {
		if p, err := exec.LookPath(b); err == nil {
			cmd := exec.Command(p, "--app="+url, "--user-data-dir="+profile, "--window-size="+size, "--no-first-run")
			if cmd.Start() == nil {
				go cmd.Wait()
				return
			}
		}
	}
	if p, err := exec.LookPath("xdg-open"); err == nil {
		exec.Command(p, url).Start()
	}
}
