// Package settings holds the values that the plotter keeps after power off: the pen angles,
// the pen table, the Wi-Fi network, and the pen change position.
//
// Encode writes a fixed binary record with a CRC. Decode checks the CRC and the version.
// A Store keeps the record: the last flash block on the Pico, a file in the simulator.
// The package does not allocate after Decode, so it runs on the microcontroller.
package settings

import (
	"encoding/binary"
	"errors"
	"hash/crc32"

	"github.com/beetlebugorg/penplotter/firmware/config"
)

// Size is the size of an encoded record in bytes.
const Size = 1024

// NumPens is the number of entries in the pen table (T0 to T15).
const NumPens = 16

// Length limits of the text fields, in bytes.
const (
	PenNameLen  = 15
	SSIDLen     = 32
	PassLen     = 63
	HostnameLen = 31
)

// Pen is one entry of the pen table.
type Pen struct {
	Name  string
	Color uint32 // 0xRRGGBB
}

// Settings is the saved state.
type Settings struct {
	PenUp, PenDown int   // servo angles in degrees
	Y2TrimUM       int32 // Y2 offset after homing, in micrometres
	Speed          int   // speed override in percent

	Pens [NumPens]Pen
	Tool int // the pen in the holder now (0..15)

	// Pen change: the park position (machine mm) and the changer type.
	ParkX, ParkY int // mm
	Changer      int // 0 = manual (LCD prompt), 1 = automatic (not built yet)

	// Wi-Fi (Pico W only). An empty SSID turns Wi-Fi off.
	WiFiOn   bool
	SSID     string
	Pass     string
	Hostname string
	StaticIP [4]byte // 0.0.0.0 = DHCP
	Gateway  [4]byte
	Netmask  uint8 // prefix length, for example 24
}

// Changer types.
const (
	ChangerManual = 0
	ChangerAuto   = 1
)

// Default returns the settings of a new board.
func Default() Settings {
	s := Settings{
		PenUp: config.PenUpDeg, PenDown: config.PenDownDeg, Speed: 100,
		ParkX: config.TravelX / 2, ParkY: 0,
		Hostname: "penplotter", Netmask: 24, WiFiOn: true,
	}
	names := [NumPens]string{"Black", "Blue", "Red", "Green", "Orange", "Purple", "Brown", "Pink",
		"Grey", "Yellow", "Cyan", "Magenta", "Navy", "Olive", "Teal", "White"}
	colors := [NumPens]uint32{0x000000, 0x1F4FBF, 0xD12A2A, 0x1E8C3A, 0xF28C1E, 0x7A3FB0, 0x7B4A2A, 0xF07AB0,
		0x808080, 0xF2D21E, 0x1EBED2, 0xD21EB4, 0x1E2A6B, 0x6B6B1E, 0x1E7A7A, 0xFFFFFF}
	for i := range s.Pens {
		s.Pens[i] = Pen{Name: names[i], Color: colors[i]}
	}
	return s
}

// Errors of Decode.
var (
	ErrEmpty   = errors.New("no settings saved")
	ErrCRC     = errors.New("settings CRC error")
	ErrVersion = errors.New("settings from another firmware version")
)

const (
	magic   = 0x31535050 // "PPS1"
	version = 1
	header  = 12 // magic, version, payload length
)

// Encode writes s into b. b must be Size bytes long.
func (s *Settings) Encode(b []byte) {
	for i := range b {
		b[i] = 0xFF // the erased flash value
	}
	w := writer{b: b, i: header}
	w.i16(s.PenUp)
	w.i16(s.PenDown)
	w.i32(s.Y2TrimUM)
	w.i16(s.Speed)
	for _, p := range s.Pens {
		w.str(p.Name, PenNameLen)
		w.u32(p.Color)
	}
	w.i16(s.Tool)
	w.i16(s.ParkX)
	w.i16(s.ParkY)
	w.i16(s.Changer)
	w.bool(s.WiFiOn)
	w.str(s.SSID, SSIDLen)
	w.str(s.Pass, PassLen)
	w.str(s.Hostname, HostnameLen)
	w.bytes(s.StaticIP[:])
	w.bytes(s.Gateway[:])
	w.u8(s.Netmask)
	n := w.i - header
	binary.LittleEndian.PutUint32(b[0:], magic)
	binary.LittleEndian.PutUint32(b[4:], version)
	binary.LittleEndian.PutUint32(b[8:], uint32(n))
	binary.LittleEndian.PutUint32(b[w.i:], crc32.ChecksumIEEE(b[:w.i]))
}

// Decode reads a record from b into s. On an error, s does not change.
func (s *Settings) Decode(b []byte) error {
	if len(b) < header+4 || binary.LittleEndian.Uint32(b) != magic {
		return ErrEmpty
	}
	if binary.LittleEndian.Uint32(b[4:]) != version {
		return ErrVersion
	}
	n := int(binary.LittleEndian.Uint32(b[8:]))
	if n < 0 || header+n+4 > len(b) {
		return ErrCRC
	}
	if crc32.ChecksumIEEE(b[:header+n]) != binary.LittleEndian.Uint32(b[header+n:]) {
		return ErrCRC
	}
	var t Settings
	r := reader{b: b[:header+n], i: header}
	t.PenUp = r.i16()
	t.PenDown = r.i16()
	t.Y2TrimUM = r.i32()
	t.Speed = r.i16()
	for i := range t.Pens {
		t.Pens[i].Name = r.str(PenNameLen)
		t.Pens[i].Color = r.u32()
	}
	t.Tool = r.i16()
	t.ParkX = r.i16()
	t.ParkY = r.i16()
	t.Changer = r.i16()
	t.WiFiOn = r.bool()
	t.SSID = r.str(SSIDLen)
	t.Pass = r.str(PassLen)
	t.Hostname = r.str(HostnameLen)
	copy(t.StaticIP[:], r.bytes(4))
	copy(t.Gateway[:], r.bytes(4))
	t.Netmask = r.u8()
	if r.bad {
		return ErrCRC
	}
	t.clamp()
	*s = t
	return nil
}

// clamp keeps the values in their valid ranges.
func (s *Settings) clamp() {
	s.PenUp = clampInt(s.PenUp, 0, 180)
	s.PenDown = clampInt(s.PenDown, 0, 180)
	s.Speed = clampInt(s.Speed, 10, 300)
	s.Tool = clampInt(s.Tool, 0, NumPens-1)
	s.ParkX = clampInt(s.ParkX, 0, config.TravelX)
	s.ParkY = clampInt(s.ParkY, 0, config.TravelY)
	s.Changer = clampInt(s.Changer, 0, 1)
	if s.Netmask > 32 {
		s.Netmask = 24
	}
	if s.Hostname == "" {
		s.Hostname = "penplotter"
	}
}

func clampInt(v, lo, hi int) int {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

// Store keeps one encoded record.
type Store interface {
	// Load reads the record into b (Size bytes). It returns false if it cannot read.
	Load(b []byte) bool
	// Save writes the record. b is Size bytes.
	Save(b []byte) error
}

// MemStore is a Store in memory, for tests.
type MemStore struct{ B []byte }

// Load implements Store.
func (m *MemStore) Load(b []byte) bool {
	if m.B == nil {
		return false
	}
	copy(b, m.B)
	return true
}

// Save implements Store.
func (m *MemStore) Save(b []byte) error {
	m.B = append(m.B[:0], b...)
	return nil
}

type writer struct {
	b []byte
	i int
}

func (w *writer) u8(v uint8) { w.b[w.i] = v; w.i++ }
func (w *writer) bool(v bool) {
	if v {
		w.u8(1)
	} else {
		w.u8(0)
	}
}
func (w *writer) i16(v int) { binary.LittleEndian.PutUint16(w.b[w.i:], uint16(int16(v))); w.i += 2 }
func (w *writer) u32(v uint32) {
	binary.LittleEndian.PutUint32(w.b[w.i:], v)
	w.i += 4
}
func (w *writer) i32(v int32)    { w.u32(uint32(v)) }
func (w *writer) bytes(p []byte) { copy(w.b[w.i:], p); w.i += len(p) }
func (w *writer) str(s string, n int) {
	if len(s) > n {
		s = s[:n]
	}
	w.u8(uint8(len(s)))
	copy(w.b[w.i:], s)
	for j := len(s); j < n; j++ {
		w.b[w.i+j] = 0
	}
	w.i += n
}

type reader struct {
	b   []byte
	i   int
	bad bool
}

func (r *reader) need(n int) bool {
	if r.i+n > len(r.b) {
		r.bad = true
		return false
	}
	return true
}
func (r *reader) u8() uint8 {
	if !r.need(1) {
		return 0
	}
	r.i++
	return r.b[r.i-1]
}
func (r *reader) bool() bool { return r.u8() != 0 }
func (r *reader) i16() int {
	if !r.need(2) {
		return 0
	}
	r.i += 2
	return int(int16(binary.LittleEndian.Uint16(r.b[r.i-2:])))
}
func (r *reader) u32() uint32 {
	if !r.need(4) {
		return 0
	}
	r.i += 4
	return binary.LittleEndian.Uint32(r.b[r.i-4:])
}
func (r *reader) i32() int32 { return int32(r.u32()) }
func (r *reader) bytes(n int) []byte {
	if !r.need(n) {
		return make([]byte, n)
	}
	r.i += n
	return r.b[r.i-n : r.i]
}
func (r *reader) str(n int) string {
	l := int(r.u8())
	p := r.bytes(n)
	if l > n {
		l = n
	}
	return string(p[:l])
}
