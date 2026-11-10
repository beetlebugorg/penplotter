package sim

import (
	"bufio"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/beetlebugorg/penplotter/firmware/settings"
)

func apiServer(t *testing.T, m *Machine) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("/api/", m.ServeAPI)
	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	return srv
}

func post(t *testing.T, url, body string, hdr map[string]string) (int, string) {
	t.Helper()
	req, _ := http.NewRequest("POST", url, strings.NewReader(body))
	for k, v := range hdr {
		req.Header.Set(k, v)
	}
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer r.Body.Close()
	b, _ := io.ReadAll(r.Body)
	return r.StatusCode, string(b)
}

func status(t *testing.T, url string) map[string]any {
	t.Helper()
	r, err := http.Get(url + "/api/status")
	if err != nil {
		t.Fatal(err)
	}
	defer r.Body.Close()
	var st map[string]any
	if err := json.NewDecoder(r.Body).Decode(&st); err != nil {
		t.Fatal(err)
	}
	return st
}

func TestAPIJobStatusAndCmd(t *testing.T) {
	m := New()
	m.SetSpeed(100)
	srv := apiServer(t, m)

	code, out := post(t, srv.URL+"/api/cmd", "M115", nil)
	if code != 200 || !strings.Contains(out, "FIRMWARE_NAME") || !strings.HasSuffix(out, "ok\n") {
		t.Fatalf("M115: %d %q", code, out)
	}
	job := "; a comment line\nG28\nG1 X20 Y10 F6000 ; go\nM3\nG1 X40\nM5\n\nG0 X0 Y0\nM400\n"
	code, out = post(t, srv.URL+"/api/job?name=test.gcode", job, map[string]string{"X-Job-Lines": "7"})
	if code != 200 {
		t.Fatalf("job: %d %s", code, out)
	}
	var res struct {
		Lines, Answered, Errors int
	}
	if err := json.Unmarshal([]byte(out), &res); err != nil || res.Lines != 7 || res.Answered != 7 || res.Errors != 0 {
		t.Fatalf("job result %s (%v)", out, err)
	}
	// The status is published every 20 ms: wait for the idle state.
	st := status(t, srv.URL)
	for end := time.Now().Add(2 * time.Second); st["state"] != "idle" && time.Now().Before(end); time.Sleep(10 * time.Millisecond) {
		st = status(t, srv.URL)
	}
	if st["homed"] != true || st["state"] != "idle" || st["pen"] != "up" {
		t.Fatalf("status %v", st)
	}
	code, out = post(t, srv.URL+"/api/cmd", "M114", nil)
	if code != 200 || !strings.Contains(out, "X:0.000 Y:0.000") {
		t.Fatalf("M114: %d %q", code, out)
	}
	code, out = post(t, srv.URL+"/api/cmd", "G1 X999 Y-5", nil)
	if code != 200 {
		t.Fatalf("soft limits: %d %q", code, out)
	}
}

func TestAPIBusyWhileUSBOwns(t *testing.T) {
	m := New()
	m.SetSpeed(1)
	srv := apiServer(t, m)
	// The USB port starts a long move and owns the machine.
	go m.Serial.Send("G1 X200 Y200 F600", true, nil)
	for end := time.Now().Add(3 * time.Second); time.Now().Before(end); time.Sleep(10 * time.Millisecond) {
		if status(t, srv.URL)["owner"] == "usb" {
			break
		}
	}
	code, out := post(t, srv.URL+"/api/job", "G1 X10\n", nil)
	if code != 409 || !strings.Contains(out, "usb has the machine") {
		t.Fatalf("job while busy: %d %s", code, out)
	}
	code, out = post(t, srv.URL+"/api/cmd", "G1 X5", nil)
	if code != 409 || !strings.Contains(out, "error:busy") {
		t.Fatalf("cmd while busy: %d %q", code, out)
	}
	// Queries still work.
	code, out = post(t, srv.URL+"/api/cmd", "M119", nil)
	if code != 200 || !strings.Contains(out, "x_min") {
		t.Fatalf("query while busy: %d %q", code, out)
	}
	// M112 from the network stops the machine.
	post(t, srv.URL+"/api/cmd", "M112", nil)
	st := status(t, srv.URL)
	for end := time.Now().Add(2 * time.Second); st["alarm"] != true && time.Now().Before(end); time.Sleep(10 * time.Millisecond) {
		st = status(t, srv.URL)
	}
	if st["alarm"] != true || st["state"] != "alarm" {
		t.Fatalf("no alarm after M112: %v", st)
	}
}

func TestAPIPensAndSettingsSurviveReset(t *testing.T) {
	store := FileStore{Path: filepath.Join(t.TempDir(), "settings.bin")}
	m := NewWith(store)
	srv := apiServer(t, m)
	req, _ := http.NewRequest("PUT", srv.URL+"/api/pens", strings.NewReader(`[{"t":2,"name":"Red 0.5","color":"#FF0000"},{"t":5,"color":255}]`))
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	var pens []struct {
		T     int
		Name  string
		Color string
	}
	json.NewDecoder(r.Body).Decode(&pens)
	r.Body.Close()
	if len(pens) != settings.NumPens || pens[2].Name != "Red 0.5" || pens[2].Color != "#FF0000" || pens[5].Color != "#0000FF" {
		t.Fatalf("pens %+v", pens)
	}
	post(t, srv.URL+"/api/cmd", "M281 U120 D75", nil)
	if code, out := post(t, srv.URL+"/api/cmd", "M500", nil); code != 200 {
		t.Fatalf("M500: %d %q", code, out)
	}
	m.Reset()
	code, out := post(t, srv.URL+"/api/cmd", "M503", nil)
	if code != 200 || !strings.Contains(out, "M281 U120 D75") || !strings.Contains(out, "T2 Red 0.5 #FF0000") {
		t.Fatalf("M503 after reset: %q", out)
	}
	r, _ = http.Get(srv.URL + "/api/pens")
	b, _ := io.ReadAll(r.Body)
	r.Body.Close()
	if !strings.Contains(string(b), `"Red 0.5"`) {
		t.Fatalf("pens after reset: %s", b)
	}
}

func TestTCPPortAndOwnership(t *testing.T) {
	m := New()
	m.SetSpeed(100)
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := ln.Addr().String()
	ln.Close()
	if err := m.ServeTCP(addr); err != nil {
		t.Fatal(err)
	}
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	r := bufio.NewReader(conn)
	send := func(line string) string {
		conn.Write([]byte(line + "\n"))
		var out string
		conn.SetReadDeadline(time.Now().Add(20 * time.Second))
		for {
			l, err := r.ReadString('\n')
			if err != nil {
				t.Fatalf("%s: %v (%q)", line, err, out)
			}
			out += l
			if strings.HasPrefix(l, "ok") || strings.HasPrefix(l, "error") {
				return out
			}
		}
	}
	if out := send("G28"); !strings.HasSuffix(out, "ok\n") {
		t.Fatalf("G28: %q", out)
	}
	// While the TCP client owns the machine, USB motion lines are busy.
	conn.Write([]byte("G1 X100 F300\n"))
	time.Sleep(100 * time.Millisecond)
	if out := m.Serial.Send("G1 Y50", true, nil); !strings.HasPrefix(out, "error:busy") {
		t.Fatalf("USB while TCP owns: %q", out)
	}
	if out := m.Serial.Send("M114", true, nil); out != "ok" {
		t.Fatalf("USB query while TCP owns: %q", out)
	}
}

// TestPenChangePromptOnLCD runs M6 in the simulator: the LCD shows the prompt and a
// click of the simulated knob answers it, as on the real board.
func TestPenChangePromptOnLCD(t *testing.T) {
	m := New()
	m.SetSpeed(100)
	if r := m.Serial.Send("G28", true, nil); r != "ok" {
		t.Fatalf("G28: %q", r)
	}
	done := make(chan string, 1)
	go func() { done <- m.Serial.Send("M6 T4", true, nil) }()
	deadline := time.Now().Add(20 * time.Second)
	for m.Snapshot().Status.Prompt == "" {
		if time.Now().After(deadline) {
			t.Fatal("no prompt")
		}
		time.Sleep(10 * time.Millisecond)
	}
	if p := m.Snapshot().Status; p.Prompt != "Load pen T4" {
		t.Fatalf("prompt %q", p.Prompt)
	}
	m.Press(true)
	time.Sleep(60 * time.Millisecond)
	m.Press(false)
	select {
	case r := <-done:
		if r != "ok" {
			t.Fatalf("M6: %q", r)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("the click did not end the pen change")
	}
	// The snapshot updates every 5 ms.
	for end := time.Now().Add(2 * time.Second); m.Snapshot().Status.Tool != 4 && time.Now().Before(end); {
		time.Sleep(10 * time.Millisecond)
	}
	if code := m.Snapshot().Status.Tool; code != 4 {
		t.Fatalf("tool %d", code)
	}
}
