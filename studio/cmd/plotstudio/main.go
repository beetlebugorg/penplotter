// Command plotstudio lays out drawings on the plotter bed with a camera, and plots them.
//
//	go run ./studio/cmd/plotstudio -port /dev/ttyACM0 -camera /dev/video0
//	go run ./studio/cmd/plotstudio -port penplotter.local -camera /dev/video0
//	go run ./studio/cmd/plotstudio -port /dev/pts/7 -camera http://127.0.0.1:8765/camera.jpg
//
// Open http://127.0.0.1:8780 in a browser.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/studio/app"
	"github.com/beetlebugorg/penplotter/studio/camera"
	"github.com/beetlebugorg/penplotter/studio/web"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:8780", "HTTP address of the UI")
	port := flag.String("port", "", "the plotter: a serial device (/dev/ttyACM0) or a network address (penplotter.local, 192.168.1.50, tcp://127.0.0.1:2323 for the simulated stock board); default: the first /dev/ttyUSB* (stock control box), then /dev/ttyACM* (Pico)")
	cam := flag.String("camera", "", "camera: /dev/video0, a number, an http:// JPEG URL, or file:<path>")
	data := flag.String("data", "", "directory for calibration.json and the library (default ~/.config/plotstudio)")
	pxmm := flag.Float64("px-per-mm", 2, "resolution of the bed view")
	park := flag.Bool("park", true, "park the gantry at the back before a scan")
	twice := flag.Bool("scan-twice", true, "scan with the gantry at the back and at the front, and join the pictures")
	split := flag.Float64("split", 0.5, "the join row of the two scan pictures, as a part of the picture height")
	lens := flag.Bool("lens", true, "fit the lens distortion when the calibration has 6 or more points")
	feed := flag.Float64("feed", 3000, "draw speed in mm/min")
	list := flag.Bool("list-cameras", false, "list the V4L2 cameras and exit")
	noOpen := flag.Bool("no-open", false, "do not open a browser")
	flag.Parse()

	if *list {
		devs := camera.List()
		if len(devs) == 0 {
			fmt.Println("no V4L2 capture devices")
		}
		b, _ := json.MarshalIndent(devs, "", "  ")
		fmt.Println(string(b))
		return
	}
	if *port == "" {
		// The CR-10 V3 control box has a CH340 chip (/dev/ttyUSB*). The Pico is /dev/ttyACM*.
		for _, pat := range []string{"/dev/ttyUSB*", "/dev/ttyACM*"} {
			if m, _ := filepath.Glob(pat); len(m) > 0 {
				*port = m[0]
				break
			}
		}
	}
	a := app.New(app.Config{
		Port: *port, Camera: *cam, TravelX: config.TravelX, TravelY: config.TravelY,
		PxPerMM: *pxmm, DataDir: *data, ParkScan: *park, ScanTwice: *twice, Split: *split, FitLens: *lens, Feed: *feed, Web: web.FS(),
	})
	defer a.Close()
	ln, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatal(err)
	}
	url := "http://" + ln.Addr().String()
	fmt.Printf("plotstudio: %s\n", url)
	if !*noOpen {
		if p, err := exec.LookPath("xdg-open"); err == nil {
			exec.Command(p, url).Start()
		}
	}
	if err := http.Serve(ln, a.Handler()); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
