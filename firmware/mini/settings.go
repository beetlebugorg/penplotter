package mini

import "github.com/beetlebugorg/penplotter/firmware/config"

// Settings are the values that M500 saves.
type Settings struct {
	PenUp, PenDown uint8 // servo angles
	Speed          uint8 // feed override, percent
	Y2TrimUM       int16 // Y2 moves this far after homing, in micrometres
}

// DefaultSettings returns the values of the config package.
func DefaultSettings() Settings {
	return Settings{PenUp: config.PenUpDeg, PenDown: config.PenDownDeg, Speed: 100,
		Y2TrimUM: int16(config.Y2HomeOffsetMM * 1000)}
}

// The record: "PP", a version, the values, and a sum of all bytes before it.
const (
	settingsSize    = 9
	settingsVersion = 1
)

// Encode writes the record.
func (s Settings) Encode(b []byte) {
	b[0], b[1], b[2] = 'P', 'P', settingsVersion
	b[3], b[4], b[5] = s.PenUp, s.PenDown, s.Speed
	b[6], b[7] = byte(s.Y2TrimUM), byte(uint16(s.Y2TrimUM)>>8)
	b[8] = sum(b[:8])
}

// DecodeSettings reads a record. It returns false if the record is not valid.
func DecodeSettings(b []byte) (Settings, bool) {
	if len(b) < settingsSize || b[0] != 'P' || b[1] != 'P' || b[2] != settingsVersion || b[8] != sum(b[:8]) {
		return Settings{}, false
	}
	s := Settings{PenUp: b[3], PenDown: b[4], Speed: b[5], Y2TrimUM: int16(uint16(b[6]) | uint16(b[7])<<8)}
	if s.PenUp > 180 || s.PenDown > 180 || s.Speed < 10 || s.Speed > 200 {
		return Settings{}, false
	}
	return s, true
}

func sum(b []byte) byte {
	var v byte = 0x5A
	for _, x := range b {
		v = v*31 + x
	}
	return v
}

func (c *Controller) save() {
	if c.store == nil {
		return
	}
	var buf [settingsSize]byte
	c.set.Encode(buf[:])
	if err := c.store.Save(buf[:]); err != nil {
		c.msg = "Save failed"
	}
}

// saveLater saves 3 s after the last change, when the machine is idle.
func (c *Controller) saveLater() { c.saveAt = c.b.NowMicros() + 3_000_000 }
