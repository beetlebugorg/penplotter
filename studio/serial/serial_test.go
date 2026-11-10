package serial

import (
	"bufio"
	"context"
	"io"
	"strings"
	"sync"
	"testing"
	"time"
)

// fake is a firmware: it answers ok to each line, and error to "BAD".
type fake struct {
	inR  *io.PipeReader
	inW  *io.PipeWriter
	outR *io.PipeReader
	outW *io.PipeWriter
	mu   sync.Mutex
	got  []string
}

func newFake() *fake {
	f := &fake{}
	f.inR, f.inW = io.Pipe()
	f.outR, f.outW = io.Pipe()
	go func() {
		f.outW.Write([]byte("start\n"))
		r := bufio.NewReader(f.inR)
		for {
			l, err := r.ReadString('\n')
			if err != nil {
				return
			}
			l = strings.TrimSpace(l)
			f.mu.Lock()
			f.got = append(f.got, l)
			f.mu.Unlock()
			time.Sleep(time.Millisecond)
			if l == "BAD" {
				f.outW.Write([]byte("error:bad\n"))
				continue
			}
			if l == "M114" {
				f.outW.Write([]byte("X:1.00 Y:2.00\n"))
			}
			f.outW.Write([]byte("ok\n"))
		}
	}()
	return f
}

func (f *fake) Read(b []byte) (int, error)  { return f.outR.Read(b) }
func (f *fake) Write(b []byte) (int, error) { return f.inW.Write(b) }
func (f *fake) Close() error                { f.inW.Close(); return f.outW.Close() }

func TestCommand(t *testing.T) {
	f := newFake()
	p := New(f, nil)
	defer p.Close()
	ctx := context.Background()
	time.Sleep(10 * time.Millisecond) // the banner
	out, err := p.Command(ctx, "M114")
	if err != nil || len(out) != 1 || !strings.HasPrefix(out[0], "X:1") {
		t.Fatalf("%v %v", out, err)
	}
	if _, err := p.Command(ctx, "BAD"); err == nil {
		t.Fatal("want an error")
	}
}

func TestStreamPauseCancel(t *testing.T) {
	f := newFake()
	p := New(f, nil)
	defer p.Close()
	var lines []string
	for i := 0; i < 200; i++ {
		lines = append(lines, "G1 X1")
	}
	j := p.Stream(lines)
	time.Sleep(20 * time.Millisecond)
	j.Pause()
	time.Sleep(20 * time.Millisecond)
	a := j.Status().Done
	time.Sleep(30 * time.Millisecond)
	if b := j.Status().Done; b > a+1 {
		t.Fatalf("pause did not stop: %d -> %d", a, b)
	}
	j.Resume()
	time.Sleep(20 * time.Millisecond)
	j.Cancel()
	j.Wait()
	st := j.Status()
	if st.State != "cancelled" || st.Done >= 200 {
		t.Fatalf("%+v", st)
	}
	time.Sleep(20 * time.Millisecond)
	f.mu.Lock()
	last := f.got[len(f.got)-1]
	f.mu.Unlock()
	if last != "M5" {
		t.Fatalf("last line %q", last)
	}
}

func TestStreamDone(t *testing.T) {
	f := newFake()
	p := New(f, nil)
	defer p.Close()
	j := p.Stream(Program("G21 ; mm\n\n(comment)\nG90\nM5\n"))
	if err := j.Wait(); err != nil {
		t.Fatal(err)
	}
	if s := j.Status(); s.State != "done" || s.Done != 3 {
		t.Fatalf("%+v", s)
	}
	_ = context.Background
}
