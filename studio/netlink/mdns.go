// Package netlink connects plotstudio to the plotter over the network: mDNS discovery, the raw
// G-code link on TCP port 23, and the HTTP API on port 80 (docs/network-api.md).
//
// The mDNS code is a small, pure-Go DNS encoder and decoder. It sends one-shot queries
// ("legacy unicast", RFC 6762 section 6.7): the responder answers to the source port.
package netlink

import (
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"net"
	"sort"
	"strings"
	"time"
)

// Service is the mDNS service type of the plotter.
const Service = "_penplotter._tcp.local"

// DefaultHost is the mDNS host name of the plotter.
const DefaultHost = "penplotter.local"

var mdnsAddr = &net.UDPAddr{IP: net.IPv4(224, 0, 0, 251), Port: 5353}

const (
	typeA   = 1
	typePTR = 12
	typeTXT = 16
	typeSRV = 33
)

// Device is a plotter found on the network.
type Device struct {
	Name string `json:"name"` // the instance or host name
	Host string `json:"host"` // the host name, for example penplotter.local
	IP   string `json:"ip"`
	Port int    `json:"port"` // the G-code port (23 when the record has no SRV)
}

// Addr is the G-code address of the device: ip:port.
func (d Device) Addr() string { return net.JoinHostPort(d.IP, fmt.Sprint(d.Port)) }

type question struct {
	name  string
	qtype uint16
}

type record struct {
	name  string
	rtype uint16
	data  []byte // raw RDATA
	msg   []byte // the whole message, for names with compression pointers
	off   int    // the offset of RDATA in msg
}

func encodeName(b []byte, name string) []byte {
	for _, label := range strings.Split(strings.TrimSuffix(name, "."), ".") {
		if label == "" {
			continue
		}
		b = append(b, byte(len(label)))
		b = append(b, label...)
	}
	return append(b, 0)
}

func encodeQuery(id uint16, qs []question) []byte {
	b := make([]byte, 12, 128)
	binary.BigEndian.PutUint16(b[0:], id)
	binary.BigEndian.PutUint16(b[4:], uint16(len(qs)))
	for _, q := range qs {
		b = encodeName(b, q.name)
		b = binary.BigEndian.AppendUint16(b, q.qtype)
		b = binary.BigEndian.AppendUint16(b, 1) // class IN
	}
	return b
}

// readName reads a name at off, with compression pointers. It returns the name and the offset
// after the name in the original position.
func readName(msg []byte, off int) (string, int, error) {
	var labels []string
	end := -1
	for hops := 0; hops < 64; hops++ {
		if off >= len(msg) {
			return "", 0, errors.New("mdns: name out of range")
		}
		l := int(msg[off])
		switch {
		case l == 0:
			if end < 0 {
				end = off + 1
			}
			return strings.Join(labels, "."), end, nil
		case l&0xC0 == 0xC0:
			if off+1 >= len(msg) {
				return "", 0, errors.New("mdns: bad pointer")
			}
			if end < 0 {
				end = off + 2
			}
			off = int(binary.BigEndian.Uint16(msg[off:]) & 0x3FFF)
		default:
			if off+1+l > len(msg) {
				return "", 0, errors.New("mdns: label out of range")
			}
			labels = append(labels, string(msg[off+1:off+1+l]))
			off += 1 + l
		}
	}
	return "", 0, errors.New("mdns: name loop")
}

// parse returns the answer, authority and additional records of a response.
func parse(msg []byte) ([]record, error) {
	if len(msg) < 12 {
		return nil, errors.New("mdns: short message")
	}
	qd := int(binary.BigEndian.Uint16(msg[4:]))
	n := int(binary.BigEndian.Uint16(msg[6:])) + int(binary.BigEndian.Uint16(msg[8:])) + int(binary.BigEndian.Uint16(msg[10:]))
	off := 12
	for i := 0; i < qd; i++ {
		_, o, err := readName(msg, off)
		if err != nil {
			return nil, err
		}
		off = o + 4
	}
	var out []record
	for i := 0; i < n; i++ {
		name, o, err := readName(msg, off)
		if err != nil {
			return out, err
		}
		if o+10 > len(msg) {
			return out, errors.New("mdns: short record")
		}
		rt := binary.BigEndian.Uint16(msg[o:])
		rl := int(binary.BigEndian.Uint16(msg[o+8:]))
		if o+10+rl > len(msg) {
			return out, errors.New("mdns: short rdata")
		}
		out = append(out, record{name: strings.ToLower(name), rtype: rt, data: msg[o+10 : o+10+rl], msg: msg, off: o + 10})
		off = o + 10 + rl
	}
	return out, nil
}

// query sends the questions and collects the records of all answers until the context ends.
func query(ctx context.Context, qs []question) ([]record, error) {
	c, err := net.ListenUDP("udp4", &net.UDPAddr{})
	if err != nil {
		return nil, err
	}
	defer c.Close()
	msg := encodeQuery(0x5050, qs)
	deadline, ok := ctx.Deadline()
	if !ok {
		deadline = time.Now().Add(1500 * time.Millisecond)
	}
	c.SetDeadline(deadline)
	// Send twice: one UDP packet can get lost.
	for i := 0; i < 2; i++ {
		if _, err := c.WriteToUDP(msg, mdnsAddr); err != nil {
			return nil, err
		}
	}
	var out []record
	buf := make([]byte, 9000)
	for {
		n, _, err := c.ReadFromUDP(buf)
		if err != nil {
			break // the deadline
		}
		rs, _ := parse(append([]byte(nil), buf[:n]...))
		out = append(out, rs...)
	}
	return out, nil
}

// Resolve finds the IPv4 address of a host. A name that ends in ".local" goes to mDNS. Other
// names go to the system resolver.
func Resolve(ctx context.Context, host string) (string, error) {
	if ip := net.ParseIP(host); ip != nil {
		return host, nil
	}
	if !strings.HasSuffix(strings.ToLower(strings.TrimSuffix(host, ".")), ".local") {
		ips, err := net.DefaultResolver.LookupIPAddr(ctx, host)
		if err != nil {
			return "", err
		}
		for _, ip := range ips {
			if v4 := ip.IP.To4(); v4 != nil {
				return v4.String(), nil
			}
		}
		return "", fmt.Errorf("netlink: %s has no IPv4 address", host)
	}
	if _, ok := ctx.Deadline(); !ok {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, 1500*time.Millisecond)
		defer cancel()
	}
	rs, err := query(ctx, []question{{host, typeA}})
	if err != nil {
		return "", err
	}
	want := strings.ToLower(strings.TrimSuffix(host, "."))
	for _, r := range rs {
		if r.rtype == typeA && r.name == want && len(r.data) == 4 {
			return net.IP(r.data).String(), nil
		}
	}
	return "", fmt.Errorf("netlink: no mDNS answer for %s: check that the plotter is on and on the same network", host)
}

// Discover asks for plotters on the local network: the service records of Service and the A
// record of DefaultHost. It returns each device once.
func Discover(ctx context.Context) ([]Device, error) {
	if _, ok := ctx.Deadline(); !ok {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, 2*time.Second)
		defer cancel()
	}
	rs, err := query(ctx, []question{{Service, typePTR}, {DefaultHost, typeA}})
	if err != nil {
		return nil, err
	}
	addr := map[string]string{} // host -> ip
	type srv struct {
		host string
		port int
	}
	srvs := map[string]srv{} // instance -> host, port
	var instances []string
	for _, r := range rs {
		switch r.rtype {
		case typeA:
			if len(r.data) == 4 {
				addr[r.name] = net.IP(r.data).String()
			}
		case typePTR:
			if r.name == Service {
				if n, _, err := readName(r.msg, r.off); err == nil {
					instances = append(instances, strings.ToLower(n))
				}
			}
		case typeSRV:
			if len(r.data) >= 7 {
				port := int(binary.BigEndian.Uint16(r.data[4:]))
				if h, _, err := readName(r.msg, r.off+6); err == nil {
					srvs[r.name] = srv{strings.ToLower(h), port}
				}
			}
		}
	}
	seen := map[string]bool{}
	var out []Device
	add := func(d Device) {
		if d.IP == "" || seen[d.Addr()] {
			return
		}
		seen[d.Addr()] = true
		out = append(out, d)
	}
	for _, in := range instances {
		s, ok := srvs[in]
		if !ok {
			continue
		}
		name := strings.TrimSuffix(in, "."+Service)
		add(Device{Name: name, Host: s.host, IP: addr[s.host], Port: s.port})
	}
	if ip, ok := addr[DefaultHost]; ok {
		add(Device{Name: "penplotter", Host: DefaultHost, IP: ip, Port: 23})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out, nil
}
