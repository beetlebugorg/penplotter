package netlink

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// Target is a parsed plotter address.
type Target struct {
	Host     string // a host name or an IP address
	GCode    int    // the G-code TCP port (default 23)
	HTTPBase string // the base URL of the HTTP API, for example http://penplotter.local
	// Raw is true for "tcp://host:port" without "?http=". The link is a plain serial line
	// with no HTTP API, as the simulated stock board gives.
	Raw bool
}

// IsNetwork reports that a plotter address names a network device, not a serial device. A
// serial device is a path ("/dev/ttyACM0", "COM3"). The network forms are "penplotter.local",
// "192.168.1.50", "host:2323", "tcp://host:23", and "http://host:8080" (the HTTP API base;
// the G-code port is then 23 on the same host).
func IsNetwork(addr string) bool {
	a := strings.TrimSpace(addr)
	if a == "" || strings.HasPrefix(a, "/") || strings.HasPrefix(strings.ToUpper(a), "COM") {
		return false
	}
	return true
}

// ParseTarget reads a network plotter address. A "?http=PORT" suffix sets the HTTP port (the
// simulator serves the API on its own port): "tcp://127.0.0.1:2323?http=8766".
// "tcp://host:port" without the suffix is a plain serial line (Target.Raw).
func ParseTarget(addr string) (Target, error) {
	a := strings.TrimSpace(addr)
	t := Target{GCode: 23}
	httpPort := ""
	if i := strings.Index(a, "?http="); i >= 0 {
		httpPort = a[i+6:]
		a = a[:i]
		if n, err := strconv.Atoi(httpPort); err != nil || n <= 0 || n > 65535 {
			return t, fmt.Errorf("netlink: bad HTTP port in %q", addr)
		}
	}
	switch {
	case strings.HasPrefix(a, "tcp://"):
		a = strings.TrimPrefix(a, "tcp://")
		t.Raw = httpPort == ""
	case strings.HasPrefix(a, "http://"):
		a = strings.TrimSuffix(strings.TrimPrefix(a, "http://"), "/")
		if h, p, err := net.SplitHostPort(a); err == nil {
			t.Host, httpPort = h, p
		} else {
			t.Host = a
		}
		t.HTTPBase = "http://" + net.JoinHostPort(t.Host, orDefault(httpPort, "80"))
		return t, nil
	}
	if h, p, err := net.SplitHostPort(a); err == nil {
		n, err := strconv.Atoi(p)
		if err != nil || n <= 0 || n > 65535 {
			return t, fmt.Errorf("netlink: bad port in %q", addr)
		}
		t.Host, t.GCode = h, n
	} else {
		t.Host = a
	}
	if t.Host == "" {
		return t, fmt.Errorf("netlink: no host in %q", addr)
	}
	t.HTTPBase = "http://" + net.JoinHostPort(t.Host, orDefault(httpPort, "80"))
	return t, nil
}

func orDefault(s, d string) string {
	if s == "" {
		return d
	}
	return s
}

// Dial opens the raw G-code link: one line per command, "ok" after each line.
func Dial(ctx context.Context, t Target) (net.Conn, error) {
	ip, err := Resolve(ctx, t.Host)
	if err != nil {
		return nil, err
	}
	var d net.Dialer
	c, err := d.DialContext(ctx, "tcp", net.JoinHostPort(ip, strconv.Itoa(t.GCode)))
	if err != nil {
		return nil, fmt.Errorf("netlink: connect to %s: %w", t.Host, err)
	}
	if tc, ok := c.(*net.TCPConn); ok {
		tc.SetKeepAlive(true)
		tc.SetKeepAlivePeriod(10 * time.Second)
		tc.SetNoDelay(true)
	}
	return c, nil
}

// Status is the reply of GET /api/status.
type Status struct {
	State    string   `json:"state"` // idle, busy, home, pen_change, alarm (NormalState)
	X        float64  `json:"x"`
	Y        float64  `json:"y"`
	Pen      PenState `json:"pen"` // 0 up, 1 down
	Tool     int      `json:"tool"`
	Homed    bool     `json:"homed"`
	Alarm    bool     `json:"alarm"`
	Msg      string   `json:"msg,omitempty"`      // the message of the LCD, for example the pen to load
	Owner    string   `json:"owner,omitempty"`    // the link that runs the job now
	Progress float64  `json:"progress,omitempty"` // percent, or -1
	Job      *JobRef  `json:"job,omitempty"`
	Error    string   `json:"error,omitempty"`
	Online   bool     `json:"-"` // set by the poller: the last request worked
}

// PenState is the pen position: 0 up, 1 down. The API sends "up" or "down"; a number works too.
type PenState float64

// UnmarshalJSON reads "up", "down", or a number.
func (p *PenState) UnmarshalJSON(b []byte) error {
	s := strings.Trim(strings.TrimSpace(string(b)), `"`)
	switch strings.ToLower(s) {
	case "up", "", "null":
		*p = 0
	case "down":
		*p = 1
	default:
		v, err := strconv.ParseFloat(s, 64)
		if err != nil {
			return fmt.Errorf("netlink: pen %q", s)
		}
		*p = PenState(v)
	}
	return nil
}

// JobRef is the job part of Status.
type JobRef struct {
	Name  string `json:"name"`
	Line  int    `json:"line"`
	Total int    `json:"total"`
}

// Pen is one entry of the pen table (T0 to T15).
type Pen struct {
	T     int    `json:"t"`
	Name  string `json:"name"`
	Color string `json:"color"` // #rrggbb
}

// Client talks to the HTTP API of the plotter.
type Client struct {
	Base string // for example http://192.168.1.50
	HTTP *http.Client
}

// NewClient makes a client with short timeouts. The plotter is on the local network.
func NewClient(base string) *Client {
	return &Client{Base: strings.TrimSuffix(base, "/"), HTTP: &http.Client{Timeout: 5 * time.Second}}
}

// ErrBusy is the reply to a job while another job runs (HTTP 409).
var ErrBusy = errors.New("netlink: the plotter is busy")

func (c *Client) do(ctx context.Context, method, path, ctype string, body []byte, out any) error {
	req, err := http.NewRequestWithContext(ctx, method, c.Base+path, bytes.NewReader(body))
	if err != nil {
		return err
	}
	if ctype != "" {
		req.Header.Set("Content-Type", ctype)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if resp.StatusCode == http.StatusConflict {
		return ErrBusy
	}
	if resp.StatusCode/100 != 2 {
		msg := strings.TrimSpace(string(data))
		var e struct{ Error string }
		if json.Unmarshal(data, &e) == nil && e.Error != "" {
			msg = e.Error
		}
		return fmt.Errorf("netlink: %s %s: %d %s", method, path, resp.StatusCode, msg)
	}
	if out != nil && len(data) > 0 {
		return json.Unmarshal(data, out)
	}
	return nil
}

// Status reads GET /api/status. The state is in lower case with "_" for spaces: the firmware
// sends "PEN CHANGE", the API document "pen_change"; both give "pen_change".
func (c *Client) Status(ctx context.Context) (Status, error) {
	var s Status
	err := c.do(ctx, "GET", "/api/status", "", nil, &s)
	s.Online = err == nil
	s.State = NormalState(s.State)
	if s.Alarm {
		s.State = "alarm"
	}
	return s, err
}

// NormalState writes a plotter state in lower case, with "_" for spaces.
func NormalState(s string) string {
	return strings.ReplaceAll(strings.ToLower(strings.TrimSpace(s)), " ", "_")
}

// Pens reads the pen table.
func (c *Client) Pens(ctx context.Context) ([]Pen, error) {
	var p []Pen
	return p, c.do(ctx, "GET", "/api/pens", "", nil, &p)
}

// SetPens writes the pen table.
func (c *Client) SetPens(ctx context.Context, pens []Pen) error {
	b, _ := json.Marshal(pens)
	return c.do(ctx, "PUT", "/api/pens", "application/json", b, nil)
}

// Job sends a whole G-code program. The plotter runs it on its own. ErrBusy means that a job
// runs already.
func (c *Client) Job(ctx context.Context, name, gcode string) error {
	path := "/api/job"
	if name != "" {
		path += "?name=" + urlEscape(name)
	}
	return c.do(ctx, "POST", path, "text/plain", []byte(gcode), nil)
}

// Cmd sends one line, for example "M5" or "G28".
func (c *Client) Cmd(ctx context.Context, line string) error {
	return c.do(ctx, "POST", "/api/cmd", "text/plain", []byte(line), nil)
}

func urlEscape(s string) string {
	var b strings.Builder
	for _, r := range s {
		if r < 128 && (r == '-' || r == '_' || r == '.' || ('0' <= r && r <= '9') || ('a' <= r && r <= 'z') || ('A' <= r && r <= 'Z')) {
			b.WriteRune(r)
		} else {
			for _, c := range []byte(string(r)) {
				fmt.Fprintf(&b, "%%%02X", c)
			}
		}
	}
	return b.String()
}
