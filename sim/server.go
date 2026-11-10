package sim

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"io/fs"
	"net/http"
	"sync"
	"time"

	"github.com/coder/websocket"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// Server serves the windows and the WebSocket at /ws.
type Server struct {
	m   *Machine
	web fs.FS
	stl string

	// Camera, if set, serves /camera.jpg, /camera.json and /camera/project.
	Camera http.Handler

	mu      sync.Mutex
	clients map[*client]bool
	inkSent int
	inkVer  uint64
	lcdVer  uint64
	lines   chan string // console lines from the windows, in order
}

type client struct {
	send chan []byte
	done chan struct{}
}

// NewServer makes a server. stlDir is the directory of the part files; it can be empty.
func NewServer(m *Machine, web fs.FS, stlDir string) *Server {
	s := &Server{m: m, web: web, stl: stlDir, clients: map[*client]bool{}, lines: make(chan string, 256)}
	go s.broadcastLoop()
	go s.lineLoop()
	return s
}

// Handler returns the HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/ws", s.serveWS)
	mux.HandleFunc("/api/", s.m.ServeAPI)
	if s.Camera != nil {
		mux.Handle("/camera.jpg", s.Camera)
		mux.Handle("/camera.json", s.Camera)
		mux.Handle("/camera/project", s.Camera)
	}
	if s.stl != "" {
		// http.Dir cleans each path, so a request cannot leave the directory.
		// Subdirectories work, for example /stl/sim/pen_lift.stl.
		mux.Handle("/stl/", http.StripPrefix("/stl/", http.FileServer(http.Dir(s.stl))))
	}
	mux.Handle("/", http.FileServer(http.FS(s.web)))
	return mux
}

func mustJSON(v any) []byte {
	b, _ := json.Marshal(v)
	return b
}

// The message structs keep "t" as the first key.
type helloMachine struct {
	Travel     [2]float32 `json:"travel"`
	Bed        [2]float32 `json:"bed"`
	StepsPerMM [2]float32 `json:"steps_per_mm"`
	PenUpDeg   int        `json:"pen_up_deg"`
	PenDownDeg int        `json:"pen_down_deg"`
	LCD        [2]int     `json:"lcd"`
	Layout     string     `json:"layout"`
	Board      string     `json:"board"` // "mega" (stock CR-10 V3 mainboard) or "pico"
}

type helloMsg struct {
	T       string       `json:"t"`
	Machine helloMachine `json:"machine"`
}

type stateOut struct {
	T     string          `json:"t"`
	X     float32         `json:"x"`
	Y     float32         `json:"y"`
	Y2    float32         `json:"y2"`
	Pen   float32         `json:"pen"`
	En    bool            `json:"en"`
	Homed bool            `json:"homed"`
	ES    map[string]bool `json:"es"`
	Busy  bool            `json:"busy"`
	Q     int             `json:"q"`
	Line  string          `json:"line"`
	Name  string          `json:"name,omitempty"`
	Done  int             `json:"done"`
	Total int             `json:"total"`
	Speed int             `json:"speed"`
	Servo float32         `json:"servo"`          // the servo angle in degrees
	PU    int             `json:"pen_up_deg"`     // the pen-up angle now (M281 U)
	PD    int             `json:"pen_down_deg"`   // the pen-down angle now (M281 D)
	Lift  *float32        `json:"lift,omitempty"` // the slider lift in mm, with a linkage model
	Over  bool            `json:"over,omitempty"` // the horn tip is over the tab (see penlift.go)
}

type inkOut struct {
	T string `json:"t"`
	S []Seg  `json:"s"`
}

type lcdOut struct {
	T    string `json:"t"`
	Bits string `json:"bits"`
}

type beepOut struct {
	T  string `json:"t"`
	Ms int    `json:"ms"`
}

type serialOut struct {
	T    string `json:"t"`
	Dir  string `json:"dir"`
	Text string `json:"text"`
}

type paperOut struct {
	T     string `json:"t"`
	Clear bool   `json:"clear"`
}

func (s *Server) hello() []byte {
	snap := s.m.Snapshot()
	return mustJSON(helloMsg{T: "hello", Machine: helloMachine{
		Travel:     [2]float32{config.TravelX, config.TravelY},
		Bed:        [2]float32{config.BedX, config.BedY},
		StepsPerMM: [2]float32{config.StepsPerMMX, config.StepsPerMMY},
		PenUpDeg:   snap.PenUp,
		PenDownDeg: snap.PenDown,
		LCD:        [2]int{ui.Width, ui.Height},
		Layout:     "table",
		Board:      string(s.m.Board),
	}})
}

func lcdMsg(bits [ui.Stride * ui.Height]byte) []byte {
	return mustJSON(lcdOut{T: "lcd", Bits: base64.StdEncoding.EncodeToString(bits[:])})
}

const inkChunk = 5000

func inkMsgs(segs []Seg) [][]byte {
	var out [][]byte
	for len(segs) > 0 {
		n := min(len(segs), inkChunk)
		out = append(out, mustJSON(inkOut{T: "ink", S: segs[:n]}))
		segs = segs[n:]
	}
	return out
}

func stateMsg(sn Snapshot) []byte {
	o := stateOut{
		T: "state", X: sn.X, Y: sn.Y, Y2: sn.Y2, Pen: sn.Pen, En: sn.Motors,
		Homed: sn.Status.Homed, ES: map[string]bool{"x": sn.ES[0], "y": sn.ES[1], "y2": sn.ES[2]},
		Busy: sn.Status.Busy, Q: sn.Queued, Line: sn.Line, Name: sn.Name, Done: sn.Done,
		Total: sn.Total, Speed: sn.Speed, Servo: sn.Servo, PU: sn.PenUp, PD: sn.PenDown,
	}
	if sn.LiftOK {
		o.Lift, o.Over = &sn.Lift, sn.Over
	}
	return mustJSON(o)
}

func (s *Server) serveWS(w http.ResponseWriter, r *http.Request) {
	conn, err := websocket.Accept(w, r, &websocket.AcceptOptions{
		OriginPatterns: []string{"localhost:*", "127.0.0.1:*"},
	})
	if err != nil {
		return
	}
	conn.SetReadLimit(64 << 20) // G-code uploads can be large
	c := &client{send: make(chan []byte, 4096), done: make(chan struct{})}
	ctx, cancel := context.WithCancel(r.Context())
	defer cancel()

	// Register and send the start messages under the lock, so that no ink is lost.
	s.mu.Lock()
	c.send <- s.hello()
	bits, _ := s.m.LCD()
	c.send <- lcdMsg(bits)
	segs, _, _ := s.m.Ink(0)
	if len(segs) > s.inkSent {
		segs = segs[:s.inkSent]
	}
	for _, msg := range inkMsgs(segs) {
		select {
		case c.send <- msg:
		default:
		}
	}
	c.send <- stateMsg(s.m.Snapshot())
	s.clients[c] = true
	s.mu.Unlock()

	go func() {
		defer cancel()
		for {
			select {
			case msg := <-c.send:
				wctx, wc := context.WithTimeout(ctx, 10*time.Second)
				err := conn.Write(wctx, websocket.MessageText, msg)
				wc()
				if err != nil {
					return
				}
			case <-c.done:
				return
			case <-ctx.Done():
				return
			}
		}
	}()
	for {
		_, data, err := conn.Read(ctx)
		if err != nil {
			break
		}
		s.handle(data)
	}
	s.mu.Lock()
	delete(s.clients, c)
	s.mu.Unlock()
	conn.Close(websocket.StatusNormalClosure, "")
}

type inMsg struct {
	T     string  `json:"t"`
	D     int     `json:"d"`
	Down  bool    `json:"down"`
	Name  string  `json:"name"`
	Text  string  `json:"text"`
	X     float64 `json:"x"`
	Clear bool    `json:"clear"`
}

func (s *Server) handle(data []byte) {
	var m inMsg
	if json.Unmarshal(data, &m) != nil {
		return
	}
	switch m.T {
	case "enc":
		s.m.Turn(m.D)
	case "btn":
		s.m.Press(m.Down)
	case "gcode":
		if err := s.m.StartJob(m.Name, m.Text); err != nil {
			s.m.emit(Event{Kind: "serial", Dir: "tx", Text: "error:" + err.Error()})
		}
	case "line":
		select {
		case s.lines <- m.Text:
		default:
			s.m.emit(Event{Kind: "serial", Dir: "tx", Text: "error:too many console lines"})
		}
	case "speed":
		s.m.SetSpeed(int(m.X))
	case "paper":
		if m.Clear {
			s.m.ClearPaper()
		}
	case "reset":
		go s.m.Reset()
	case "freehorn":
		s.m.FreeHorn()
	}
}

// lineLoop sends the console lines one at a time. The order stays the same as in the window.
func (s *Server) lineLoop() {
	for l := range s.lines {
		s.m.Serial.Send(l, false, nil)
	}
}

func (s *Server) broadcast(msg []byte) {
	for c := range s.clients {
		select {
		case c.send <- msg:
		default:
			// The client is too slow. Drop it; the window reconnects and gets all state again.
			delete(s.clients, c)
			close(c.done)
		}
	}
}

func (s *Server) broadcastLoop() {
	t := time.NewTicker(time.Second / 60)
	defer t.Stop()
	for {
		select {
		case e := <-s.m.Events:
			var msg []byte
			switch e.Kind {
			case "beep":
				msg = mustJSON(beepOut{T: "beep", Ms: e.Ms})
			case "serial":
				msg = mustJSON(serialOut{T: "serial", Dir: e.Dir, Text: e.Text})
			default:
				continue
			}
			s.mu.Lock()
			s.broadcast(msg)
			s.mu.Unlock()
		case <-t.C:
			s.mu.Lock()
			segs, n, ver := s.m.Ink(s.inkSent)
			if ver != s.inkVer {
				// The paper was cleared. Tell the windows, then send the new ink.
				s.broadcast(mustJSON(paperOut{T: "paper", Clear: true}))
				segs, n, _ = s.m.Ink(0)
				s.inkVer = ver
			}
			s.inkSent = n
			for _, msg := range inkMsgs(segs) {
				s.broadcast(msg)
			}
			if bits, v := s.m.LCD(); v != s.lcdVer {
				s.lcdVer = v
				s.broadcast(lcdMsg(bits))
			}
			s.broadcast(stateMsg(s.m.Snapshot()))
			s.mu.Unlock()
		}
	}
}
