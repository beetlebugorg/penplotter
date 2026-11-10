// Package gcode parses G-code lines into letter and number words.
// It does not allocate memory, so it runs on the microcontroller.
package gcode

import "errors"

// MaxWords is the maximum number of words on one line.
const MaxWords = 16

// Word is one letter and its number, for example X12.5.
type Word struct {
	L byte
	V float32
}

// Line holds the words of one G-code line.
type Line struct {
	W [MaxWords]Word
	N int
}

// Errors of Parse.
var (
	ErrTooManyWords = errors.New("too many words")
	ErrBadNumber    = errors.New("bad number")
	ErrBadLetter    = errors.New("bad letter")
)

// Parse reads the words of s into out.
// It removes comments in parentheses and comments after ';'.
// It ignores the line number word (N) and the checksum ('*').
func Parse(s []byte, out *Line) error {
	out.N = 0
	i := 0
	for i < len(s) {
		c := s[i]
		switch {
		case c == ';' || c == '*':
			return nil
		case c == '(':
			for i < len(s) && s[i] != ')' {
				i++
			}
			i++
			continue
		case c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '%':
			i++
			continue
		}
		if c >= 'a' && c <= 'z' {
			c -= 'a' - 'A'
		}
		if c < 'A' || c > 'Z' {
			return ErrBadLetter
		}
		i++
		v, n, ok := parseNumber(s[i:])
		if !ok {
			// Axis words can have no number, as in "G28 X". G and M words need one.
			if c == 'G' || c == 'M' || hasSign(s[i:i+n]) || (n < len(s[i:]) && s[i+n] != ' ' && s[i+n] != '\t' && !isLetter(s[i+n])) {
				return ErrBadNumber
			}
			v = 0
		}
		i += n
		if c == 'N' {
			continue
		}
		if out.N == MaxWords {
			return ErrTooManyWords
		}
		out.W[out.N] = Word{L: c, V: v}
		out.N++
	}
	return nil
}

// parseNumber reads a decimal number with an optional sign.
// It returns the value, the number of bytes used, and true on success.
func parseNumber(s []byte) (float32, int, bool) {
	i := 0
	for i < len(s) && (s[i] == ' ' || s[i] == '\t') {
		i++
	}
	neg := false
	if i < len(s) && (s[i] == '-' || s[i] == '+') {
		neg = s[i] == '-'
		i++
	}
	var whole float64
	var frac float64
	scale := 1.0
	digits := 0
	for i < len(s) && s[i] >= '0' && s[i] <= '9' {
		whole = whole*10 + float64(s[i]-'0')
		i++
		digits++
	}
	if i < len(s) && s[i] == '.' {
		i++
		for i < len(s) && s[i] >= '0' && s[i] <= '9' {
			frac = frac*10 + float64(s[i]-'0')
			scale *= 10
			i++
			digits++
		}
	}
	if digits == 0 {
		return 0, i, false
	}
	v := whole + frac/scale
	if neg {
		v = -v
	}
	return float32(v), i, true
}

// Get returns the value of the first word with letter c.
func (l *Line) Get(c byte) (float32, bool) {
	for i := 0; i < l.N; i++ {
		if l.W[i].L == c {
			return l.W[i].V, true
		}
	}
	return 0, false
}

// Has tells if the line has a word with letter c.
func (l *Line) Has(c byte) bool {
	_, ok := l.Get(c)
	return ok
}

func isLetter(c byte) bool { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') }

func hasSign(s []byte) bool {
	for _, c := range s {
		if c == '-' || c == '+' || c == '.' {
			return true
		}
	}
	return false
}
