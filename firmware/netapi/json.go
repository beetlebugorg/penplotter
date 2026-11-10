package netapi

import (
	"strconv"

	"github.com/beetlebugorg/penplotter/firmware/controller"
	"github.com/beetlebugorg/penplotter/firmware/settings"
)

// StatusJSON encodes the state. state is idle, busy, homing, pen_change or alarm:
//
//	{"state":"idle","x":0,"y":0,"pen":"up","tool":0,"homed":true,"alarm":false,"msg":"",
//	 "owner":"","progress":-1,"job":{"name":"","line":0,"total":0}}
func StatusJSON(a controller.APIStatus) []byte {
	pen := "up"
	if a.PenDown {
		pen = "down"
	}
	b := []byte(`{"state":`)
	b = appendString(b, a.State)
	b = append(b, `,"x":`...)
	b = strconv.AppendFloat(b, float64(a.X), 'f', 3, 32)
	b = append(b, `,"y":`...)
	b = strconv.AppendFloat(b, float64(a.Y), 'f', 3, 32)
	b = append(b, `,"pen":`...)
	b = appendString(b, pen)
	b = append(b, `,"tool":`...)
	b = strconv.AppendInt(b, int64(a.Tool), 10)
	b = append(b, `,"homed":`...)
	b = strconv.AppendBool(b, a.Homed)
	b = append(b, `,"alarm":`...)
	b = strconv.AppendBool(b, a.Alarm)
	b = append(b, `,"msg":`...)
	b = appendString(b, a.Msg)
	b = append(b, `,"owner":`...)
	b = appendString(b, a.Owner)
	b = append(b, `,"progress":`...)
	b = strconv.AppendInt(b, int64(a.Progress), 10)
	b = append(b, `,"job":{"name":`...)
	b = appendString(b, a.JobName)
	b = append(b, `,"line":`...)
	b = strconv.AppendInt(b, int64(a.JobLine), 10)
	b = append(b, `,"total":`...)
	b = strconv.AppendInt(b, int64(a.JobTotal), 10)
	b = append(b, "}}\n"...)
	return b
}

// PensJSON encodes the pen table: [{"t":0,"name":"Black","color":"#000000"},...].
func PensJSON(p [settings.NumPens]settings.Pen) []byte {
	b := []byte{'['}
	for i, pen := range p {
		if i > 0 {
			b = append(b, ',')
		}
		b = append(b, `{"t":`...)
		b = strconv.AppendInt(b, int64(i), 10)
		b = append(b, `,"name":`...)
		b = appendString(b, pen.Name)
		b = append(b, `,"color":"#`...)
		b = appendHex6(b, pen.Color)
		b = append(b, `"}`...)
	}
	return append(b, "]\n"...)
}

func errJSON(msg string) []byte {
	b := []byte(`{"error":`)
	b = appendString(b, msg)
	return append(b, "}\n"...)
}

func jobJSON(name string, lines, replies, errs int, firstErr string) []byte {
	b := []byte(`{"name":`)
	b = appendString(b, name)
	b = append(b, `,"lines":`...)
	b = strconv.AppendInt(b, int64(lines), 10)
	b = append(b, `,"answered":`...)
	b = strconv.AppendInt(b, int64(replies), 10)
	b = append(b, `,"errors":`...)
	b = strconv.AppendInt(b, int64(errs), 10)
	b = append(b, `,"first_error":`...)
	b = appendString(b, firstErr)
	return append(b, "}\n"...)
}

func appendString(b []byte, s string) []byte {
	const hex = "0123456789abcdef"
	b = append(b, '"')
	for i := 0; i < len(s); i++ {
		c := s[i]
		switch {
		case c == '"' || c == '\\':
			b = append(b, '\\', c)
		case c == '\n':
			b = append(b, '\\', 'n')
		case c < 0x20:
			b = append(b, '\\', 'u', '0', '0', hex[c>>4], hex[c&15])
		default:
			b = append(b, c)
		}
	}
	return append(b, '"')
}

func appendHex6(b []byte, v uint32) []byte {
	const hex = "0123456789ABCDEF"
	for sh := 20; sh >= 0; sh -= 4 {
		b = append(b, hex[(v>>uint(sh))&15])
	}
	return b
}

// PenUpdate is one entry of a PUT /api/pens body.
type PenUpdate struct {
	T        int
	Name     string
	Color    uint32
	HasName  bool
	HasColor bool
}

// ParsePens reads a JSON array of pen objects: [{"t":3,"name":"Red 0.5","color":"#D12A2A"}].
// "t" is required. "name" and "color" are optional. "color" is "#RRGGBB" or a number.
// A single object without the array also works. It returns an error text on failure.
func ParsePens(b []byte) ([]PenUpdate, string) {
	p := parser{b: b}
	var out []PenUpdate
	p.ws()
	single := p.peek() == '{'
	if !single && !p.eat('[') {
		return nil, "expected a JSON array of pens"
	}
	for {
		p.ws()
		if !single && p.eat(']') {
			break
		}
		if !p.eat('{') {
			return nil, "expected an object"
		}
		u := PenUpdate{T: -1}
		for {
			p.ws()
			if p.eat('}') {
				break
			}
			key, ok := p.str()
			if !ok {
				return nil, "bad key"
			}
			p.ws()
			if !p.eat(':') {
				return nil, "expected ':'"
			}
			p.ws()
			switch key {
			case "t":
				v, ok := p.num()
				if !ok || v < 0 || v >= settings.NumPens {
					return nil, "t must be 0 to 15"
				}
				u.T = int(v)
			case "name":
				s, ok := p.str()
				if !ok {
					return nil, "name must be a string"
				}
				u.Name, u.HasName = s, true
			case "color":
				if p.peek() == '"' {
					s, ok := p.str()
					if !ok || len(s) != 7 || s[0] != '#' {
						return nil, "color must be \"#RRGGBB\""
					}
					v, err := strconv.ParseUint(s[1:], 16, 32)
					if err != nil {
						return nil, "color must be \"#RRGGBB\""
					}
					u.Color = uint32(v)
				} else {
					v, ok := p.num()
					if !ok || v < 0 || v > 0xFFFFFF {
						return nil, "bad color"
					}
					u.Color = uint32(v)
				}
				u.HasColor = true
			default:
				if !p.skip() {
					return nil, "bad value"
				}
			}
			p.ws()
			if p.eat(',') {
				continue
			}
		}
		if u.T < 0 {
			return nil, "each pen needs \"t\""
		}
		out = append(out, u)
		if single {
			break
		}
		p.ws()
		p.eat(',')
	}
	return out, ""
}

type parser struct {
	b []byte
	i int
}

func (p *parser) peek() byte {
	if p.i < len(p.b) {
		return p.b[p.i]
	}
	return 0
}

func (p *parser) eat(c byte) bool {
	if p.peek() == c {
		p.i++
		return true
	}
	return false
}

func (p *parser) ws() {
	for p.i < len(p.b) && (p.b[p.i] == ' ' || p.b[p.i] == '\t' || p.b[p.i] == '\n' || p.b[p.i] == '\r') {
		p.i++
	}
}

func (p *parser) str() (string, bool) {
	if !p.eat('"') {
		return "", false
	}
	var out []byte
	for p.i < len(p.b) {
		c := p.b[p.i]
		p.i++
		switch c {
		case '"':
			return string(out), true
		case '\\':
			if p.i >= len(p.b) {
				return "", false
			}
			e := p.b[p.i]
			p.i++
			switch e {
			case 'n':
				out = append(out, '\n')
			case 't':
				out = append(out, '\t')
			case 'u':
				if p.i+4 > len(p.b) {
					return "", false
				}
				v, err := strconv.ParseUint(string(p.b[p.i:p.i+4]), 16, 16)
				if err != nil {
					return "", false
				}
				p.i += 4
				if v < 0x80 {
					out = append(out, byte(v))
				} else {
					out = append(out, '?') // the LCD font has ASCII only
				}
			default:
				out = append(out, e)
			}
		default:
			out = append(out, c)
		}
	}
	return "", false
}

func (p *parser) num() (float64, bool) {
	j := p.i
	for j < len(p.b) && (p.b[j] == '-' || p.b[j] == '+' || p.b[j] == '.' || p.b[j] == 'e' || p.b[j] == 'E' ||
		(p.b[j] >= '0' && p.b[j] <= '9')) {
		j++
	}
	v, err := strconv.ParseFloat(string(p.b[p.i:j]), 64)
	if err != nil {
		return 0, false
	}
	p.i = j
	return v, true
}

// skip passes over one value of a key that the API does not use.
func (p *parser) skip() bool {
	switch c := p.peek(); {
	case c == '"':
		_, ok := p.str()
		return ok
	case c == '{' || c == '[':
		depth := 0
		for p.i < len(p.b) {
			switch p.b[p.i] {
			case '{', '[':
				depth++
			case '}', ']':
				depth--
				if depth == 0 {
					p.i++
					return true
				}
			case '"':
				if _, ok := p.str(); !ok {
					return false
				}
				continue
			}
			p.i++
		}
		return false
	default:
		for p.i < len(p.b) && p.b[p.i] != ',' && p.b[p.i] != '}' && p.b[p.i] != ']' {
			p.i++
		}
		return true
	}
}
