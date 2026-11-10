//go:build rp2040 && cyw43439

package pico

// Wi-Fi of the Pico W: the CYW43439 chip (pure-Go driver, github.com/soypat/cyw43439) and
// the lneto TCP/IP stack. It serves:
//
//	port 80: the HTTP API (firmware/netapi)
//	port 23: raw G-code lines with "ok" flow control, as on USB
//	mDNS:    <hostname>.local
//
// Build with: tinygo build -target=pico-w -o build/plotter-w.uf2 ./firmware/cmd/pico
// The chip uses GP23, GP24, GP25 and GP29, and PIO0.

import (
	"errors"
	"net/netip"
	"runtime"
	"sync"
	"time"

	"github.com/soypat/cyw43439"
	"github.com/soypat/lneto"
	"github.com/soypat/lneto/dns"
	"github.com/soypat/lneto/dns/mdns"
	"github.com/soypat/lneto/tcp"
	"github.com/soypat/lneto/x/xnet"

	"github.com/beetlebugorg/penplotter/firmware/controller"
	"github.com/beetlebugorg/penplotter/firmware/netapi"
	"github.com/beetlebugorg/penplotter/firmware/settings"
)

const (
	httpPort  = 80
	gcodePort = 23
	httpConns = 2 // HTTP requests at the same time
)

// wifi is the Network of the Pico W.
type wifi struct {
	mu   sync.Mutex
	want settings.Settings
	gen  int // Apply changes it
	st   controller.NetStatus

	dev     *cyw43439.Device
	stack   xnet.StackAsync
	sendbuf []byte
	srv     *netapi.Server
	httpN   int // HTTP goroutines that run
	gcodeOn bool
}

var wl = &wifi{}

// Network returns the Wi-Fi of the Pico W.
func (b *Board) Network() controller.Network { return wl }

// Start starts the network goroutine. It joins the network in the settings.
func (b *Board) Start(c *controller.Controller) {
	wl.srv = &netapi.Server{C: c, Sleep: time.Sleep}
	go wl.run()
}

// Yield lets the network goroutines run. The scheduler is cooperative.
func (b *Board) Yield() { runtime.Gosched() }

// The LED of the Pico W is on the Wi-Fi chip. The firmware does not blink it.
func ledInit()       {}
func ledSet(on bool) {}

// Status implements controller.Network.
func (w *wifi) Status() controller.NetStatus {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.st
}

// Apply implements controller.Network. The network goroutine restarts with the new settings.
func (w *wifi) Apply(s settings.Settings) {
	w.mu.Lock()
	old := w.want
	w.want = s
	if old.WiFiOn != s.WiFiOn || old.SSID != s.SSID || old.Pass != s.Pass || old.Hostname != s.Hostname ||
		old.StaticIP != s.StaticIP || old.Gateway != s.Gateway || old.Netmask != s.Netmask {
		w.gen++
	}
	w.mu.Unlock()
}

func (w *wifi) setState(state, errText string, ip [4]byte) {
	w.mu.Lock()
	w.st = controller.NetStatus{State: state, Err: errText, IP: ip}
	w.mu.Unlock()
}

func (w *wifi) settings() (settings.Settings, int) {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.want, w.gen
}

func (w *wifi) changed(gen int) bool {
	_, g := w.settings()
	return g != gen
}

// run joins and serves, and starts again when the settings change or the link drops.
func (w *wifi) run() {
	time.Sleep(500 * time.Millisecond) // let the controller start first
	for {
		s, gen := w.settings()
		if !s.WiFiOn || s.SSID == "" {
			w.setState("off", "", [4]byte{})
			w.wait(gen, 0)
			continue
		}
		w.setState("joining", "", [4]byte{})
		ip, err := w.up(s)
		if err != nil {
			w.setState("error", err.Error(), [4]byte{})
			w.wait(gen, 20*time.Second)
			continue
		}
		w.setState("up", "", ip)
		w.serve(s, gen, ip)
	}
}

// wait sleeps until the settings change, or for d (0: no limit).
func (w *wifi) wait(gen int, d time.Duration) {
	end := time.Now().Add(d)
	for !w.changed(gen) && (d == 0 || time.Now().Before(end)) {
		time.Sleep(100 * time.Millisecond)
	}
}

// up starts the chip (once), joins the network and gets an address.
func (w *wifi) up(s settings.Settings) ([4]byte, error) {
	var none [4]byte
	if w.dev == nil {
		dev := cyw43439.NewPicoWDevice()
		if err := dev.Init(cyw43439.DefaultWifiConfig()); err != nil {
			return none, errors.New("wifi chip: " + err.Error())
		}
		w.dev = dev
		w.sendbuf = make([]byte, cyw43439.MaxFrameSize)
		dev.RecvEthHandle(func(pkt []byte) { w.stack.IngressEthernet(pkt) })
		go w.pump()
	}
	if err := w.dev.Join(s.SSID, cyw43439.JoinOptions{Passphrase: s.Pass}); err != nil {
		return none, errors.New("join " + s.SSID + ": " + err.Error())
	}
	// The chip drops multicast frames unless it knows the mDNS group.
	w.dev.SetMulticastList([][6]byte{{0x01, 0x00, 0x5e, 0x00, 0x00, 0xfb}})
	mac, err := w.dev.HardwareAddr6()
	if err != nil {
		return none, err
	}
	err = w.stack.Reset(xnet.StackConfig{
		StaticAddress4:    s.StaticIP,
		Hostname:          s.Hostname,
		MaxActiveTCPPorts: 4,
		MaxActiveUDPPorts: 2,
		AcceptMulticast:   true,
		RandSeed:          time.Now().UnixNano(),
		HardwareAddress:   mac,
		MTU:               1500,
		PassivePeers:      8,
		ICMPQueueLimit:    2,
	})
	if err != nil {
		return none, err
	}
	w.stack.EnableICMP(true)
	retry := w.stack.StackRetrying(backoff)
	gw := netip.AddrFrom4(s.Gateway)
	if s.StaticIP == none {
		res, err := retry.DoDHCPv4(none, 3*time.Second, 3)
		if err != nil {
			return none, errors.New("DHCP: " + err.Error())
		}
		if err := w.stack.AssimilateDHCPResults(res); err != nil {
			return none, err
		}
		gw = res.Router
	} else {
		w.stack.SetSubnet4(s.StaticIP, s.Netmask)
	}
	if gw.IsValid() && !gw.IsUnspecified() {
		if hw, err := retry.DoResolveHardwareAddress6(gw, 500*time.Millisecond, 4); err == nil {
			w.stack.SetGatewayHardwareAddr(hw)
		}
	}
	return w.stack.Addr4(), nil
}

// pump moves frames between the chip and the stack.
func (w *wifi) pump() {
	for {
		got, _ := w.dev.PollOne()
		n, err := w.stack.EgressEthernet(w.sendbuf)
		if err == nil && n > 0 {
			w.dev.SendEth(w.sendbuf[:n])
		}
		if !got && n == 0 {
			time.Sleep(2 * time.Millisecond)
		}
	}
}

// serve runs mDNS and the two listeners until the settings change or the link drops.
func (w *wifi) serve(s settings.Settings, gen int, ip [4]byte) {
	var md mdns.Client
	addr := ip
	var host dns.Name
	err := host.Parse(s.Hostname + ".local")
	if err == nil {
		err = md.Configure(mdns.ClientConfig{
			LocalPort:     mdns.Port,
			MulticastAddr: []byte{224, 0, 0, 251},
			Services:      []mdns.Service{{Host: host, Addr: addr[:]}},
		})
	}
	if err == nil {
		w.stack.RegisterUDP4(&md, [4]byte{}, mdns.Port)
	}
	httpPool, err1 := w.stack.NewTCPPool(xnet.TCPPoolConfig{
		PoolSize: httpConns, QueueSize: 3, TxBufSize: 1536, RxBufSize: 1024,
		EstablishedTimeout: 5 * time.Second, ClosingTimeout: 5 * time.Second,
		NewBackoff: func() lneto.BackoffStrategy { return backoff },
	})
	gcodePool, err2 := w.stack.NewTCPPool(xnet.TCPPoolConfig{
		PoolSize: 1, QueueSize: 3, TxBufSize: 1024, RxBufSize: 1024,
		EstablishedTimeout: 5 * time.Second, ClosingTimeout: 5 * time.Second,
		NewBackoff: func() lneto.BackoffStrategy { return backoff },
	})
	if err1 != nil || err2 != nil {
		w.setState("error", "no memory for TCP", ip)
		w.wait(gen, 20*time.Second)
		return
	}
	var lhttp, lgcode tcp.Listener
	lhttp.Reset(httpPort, httpPool)
	lgcode.Reset(gcodePort, gcodePool)
	w.stack.RegisterListenerTCP(&lhttp)
	w.stack.RegisterListenerTCP(&lgcode)
	for !w.changed(gen) && w.dev.IsLinkUp() {
		idle := true
		if lhttp.NumberOfReadyToAccept() > 0 && w.httpN < httpConns {
			if conn, err := lhttp.TryAccept(); err == nil {
				idle = false
				w.httpN++
				go func() {
					w.srv.ServeHTTP(conn)
					conn.Close()
					w.httpN--
				}()
			}
		}
		if lgcode.NumberOfReadyToAccept() > 0 && !w.gcodeOn {
			if conn, err := lgcode.TryAccept(); err == nil {
				idle = false
				w.gcodeOn = true
				go func() {
					w.srv.ServeGcode(conn, "tcp")
					conn.Close()
					w.gcodeOn = false
				}()
			}
		}
		httpPool.CheckTimeouts()
		gcodePool.CheckTimeouts()
		if idle {
			time.Sleep(5 * time.Millisecond)
		}
	}
	lhttp.Close()
	lgcode.Close()
	if !w.dev.IsLinkUp() {
		w.setState("joining", "link lost", [4]byte{})
	}
}

// backoff waits between polls of a TCP connection: 1 µs, doubling, at most 5 ms.
func backoff(n uint) time.Duration {
	wait := time.Microsecond << min(n, 22)
	if wait > 5*time.Millisecond {
		wait = 5 * time.Millisecond
	}
	return wait
}
