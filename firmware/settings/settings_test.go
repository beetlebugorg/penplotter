package settings

import "testing"

func TestRoundTrip(t *testing.T) {
	s := Default()
	s.PenUp, s.PenDown = 120, 70
	s.SSID, s.Pass = "home", "secret pass"
	s.Pens[3] = Pen{Name: "Fineliner 0.3", Color: 0x123456}
	s.StaticIP = [4]byte{192, 168, 1, 50}
	s.Tool = 3
	b := make([]byte, Size)
	s.Encode(b)
	var got Settings
	if err := got.Decode(b); err != nil {
		t.Fatal(err)
	}
	if got != s {
		t.Fatalf("got %+v\nwant %+v", got, s)
	}
}

func TestBadRecords(t *testing.T) {
	var s Settings
	b := make([]byte, Size)
	for i := range b {
		b[i] = 0xFF
	}
	if err := s.Decode(b); err != ErrEmpty {
		t.Fatalf("erased flash: %v", err)
	}
	d := Default()
	d.Encode(b)
	b[40] ^= 1
	if err := s.Decode(b); err != ErrCRC {
		t.Fatalf("bit flip: %v", err)
	}
}

func TestLongTextIsCut(t *testing.T) {
	s := Default()
	s.Pens[0].Name = "a very long pen name for the table"
	b := make([]byte, Size)
	s.Encode(b)
	var got Settings
	if err := got.Decode(b); err != nil {
		t.Fatal(err)
	}
	if got.Pens[0].Name != s.Pens[0].Name[:PenNameLen] {
		t.Fatalf("name %q", got.Pens[0].Name)
	}
}

func TestStore(t *testing.T) {
	var m MemStore
	b := make([]byte, Size)
	if m.Load(b) {
		t.Fatal("empty store loads")
	}
	s := Default()
	s.Encode(b)
	if err := m.Save(b); err != nil {
		t.Fatal(err)
	}
	c := make([]byte, Size)
	if !m.Load(c) {
		t.Fatal("no load")
	}
	var got Settings
	if err := got.Decode(c); err != nil || got != s {
		t.Fatalf("store round trip: %v", err)
	}
}
