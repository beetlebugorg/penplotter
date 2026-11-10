package mini

// itoa formats an integer.
func itoa(v int) string {
	if v == 0 {
		return "0"
	}
	neg := v < 0
	if neg {
		v = -v
	}
	var b [12]byte
	i := len(b)
	for v > 0 {
		i--
		b[i] = byte('0' + v%10)
		v /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}

// fixed formats v with d decimals.
func fixed(v float32, d int) string {
	neg := v < 0
	if neg {
		v = -v
	}
	m := 1
	for i := 0; i < d; i++ {
		m *= 10
	}
	n := int(v*float32(m) + 0.5)
	s := itoa(n / m)
	if d > 0 {
		f := itoa(n % m)
		for len(f) < d {
			f = "0" + f
		}
		s += "." + f
	}
	if neg && n != 0 {
		s = "-" + s
	}
	return s
}

// pad cuts or fills s to n characters.
func pad(s string, n int) string {
	if len(s) >= n {
		return s[:n]
	}
	b := make([]byte, n)
	copy(b, s)
	for i := len(s); i < n; i++ {
		b[i] = ' '
	}
	return string(b)
}
