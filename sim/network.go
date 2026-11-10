package sim

import (
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/controller"
	"github.com/beetlebugorg/penplotter/firmware/netapi"
	"github.com/beetlebugorg/penplotter/firmware/settings"
)

// FileStore keeps the settings record in a file, as the Pico keeps it in flash.
type FileStore struct{ Path string }

// DefaultSettingsPath returns the settings file of the simulator for board b.
// The two boards use different records, so each board has its own file.
func DefaultSettingsPath(b Board) string {
	dir, err := os.UserConfigDir()
	if err != nil {
		dir = os.TempDir()
	}
	if b == BoardPico {
		return filepath.Join(dir, "penplotter-sim", "settings.bin")
	}
	return filepath.Join(dir, "penplotter-sim", "eeprom-mega.bin")
}

// Load implements settings.Store.
func (f FileStore) Load(b []byte) bool {
	d, err := os.ReadFile(f.Path)
	if err != nil {
		return false
	}
	copy(b, d)
	return true
}

// Save implements settings.Store.
func (f FileStore) Save(b []byte) error {
	if err := os.MkdirAll(filepath.Dir(f.Path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(f.Path, b, 0o644)
}

// simNet is the Wi-Fi of the simulated Pico W. It reports the address of the HTTP server.
type simNet struct {
	mu  sync.Mutex
	set settings.Settings
	ip  [4]byte
}

func (n *simNet) Status() controller.NetStatus {
	n.mu.Lock()
	defer n.mu.Unlock()
	// The simulator always answers on its HTTP address, as a Pico W on a network does.
	// "M552 S0" turns it off on the LCD only.
	if !n.set.WiFiOn {
		return controller.NetStatus{State: "off"}
	}
	return controller.NetStatus{State: "up", IP: n.ip}
}

func (n *simNet) Apply(s settings.Settings) {
	n.mu.Lock()
	n.set = s
	n.mu.Unlock()
}

// Controller runs f with the controller on its own goroutine. It returns false if the
// controller does not answer in time.
func (m *Machine) controllerDo(f func(c *controller.Controller)) bool {
	m.mu.Lock()
	ctl := m.ctl
	m.mu.Unlock()
	done := make(chan struct{})
	if !ctl.Do(func() { f(ctl); close(done) }) {
		return false
	}
	select {
	case <-done:
		return true
	case <-time.After(5 * time.Second):
		return false
	}
}

// apiServer returns the network API server of the current controller.
func (m *Machine) apiServer() *netapi.Server {
	m.mu.Lock()
	defer m.mu.Unlock()
	return &netapi.Server{C: m.ctl}
}

// ServeAPI serves /api/ with the same code as the Pico W. The stock board has no network.
func (m *Machine) ServeAPI(w http.ResponseWriter, r *http.Request) {
	if m.Board != BoardPico {
		httpResponse{w}.Send(http.StatusNotFound, "application/json",
			[]byte(`{"error":"the stock board has no network API: start plotsim with -board pico"}`))
		return
	}
	req := &netapi.Request{Method: r.Method, Path: r.URL.Path, Query: r.URL.RawQuery,
		Header: r.Header.Get, Body: r.Body}
	m.apiServer().Handle(req, httpResponse{w})
}

type httpResponse struct{ w http.ResponseWriter }

func (h httpResponse) Send(code int, ctype string, body []byte) {
	h.w.Header().Set("Content-Type", ctype)
	h.w.Header().Set("Access-Control-Allow-Origin", "*")
	h.w.WriteHeader(code)
	h.w.Write(body)
}

// ServeTCP accepts G-code clients on a TCP address. On the Pico W it is port 23: each
// client gets its own controller port with "ok" flow control. On the stock board it
// stands in for the USB serial port, as the pseudo-terminal does.
func (m *Machine) ServeTCP(addr string) error {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			go m.serveConn(conn)
		}
	}()
	return nil
}

func (m *Machine) serveConn(conn net.Conn) {
	defer conn.Close()
	if m.Board != BoardPico {
		m.serveLines(conn, conn)
		return
	}
	m.apiServer().ServeGcode(flushConn{conn}, "tcp "+conn.RemoteAddr().String())
}

// flushConn adds the Flush of the Pico W connections to a net.Conn.
type flushConn struct{ net.Conn }

func (flushConn) Flush() error { return nil }

// hostIP returns the IPv4 address of an HTTP listen address, for the simulated Wi-Fi.
func hostIP(addr string) [4]byte {
	host := addr
	if i := strings.LastIndexByte(addr, ':'); i >= 0 {
		host = addr[:i]
	}
	ip := net.ParseIP(host).To4()
	if ip == nil {
		return [4]byte{127, 0, 0, 1}
	}
	return [4]byte{ip[0], ip[1], ip[2], ip[3]}
}
