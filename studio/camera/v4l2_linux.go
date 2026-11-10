package camera

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"image"
	"path/filepath"
	"sort"
	"sync"
	"time"
	"unsafe"

	"golang.org/x/sys/unix"
)

// The V4L2 API of Linux (linux/videodev2.h). The struct layouts follow the Printdeck camera
// package.

type v4l2Capability struct {
	Driver       [16]byte
	Card         [32]byte
	BusInfo      [32]byte
	Version      uint32
	Capabilities uint32
	DeviceCaps   uint32
	Reserved     [3]uint32
}

type v4l2FmtDesc struct {
	Index       uint32
	Type        uint32
	Flags       uint32
	Description [32]byte
	PixelFormat uint32
	MbusCode    uint32
	Reserved    [3]uint32
}

type v4l2PixFormat struct {
	Width, Height, PixelFormat, Field, BytesPerLine, SizeImage, Colorspace, Priv uint32
	Flags, YCbCrEnc, Quantization, XferFunc                                      uint32
}

type v4l2Format struct {
	Type uint32
	Fmt  struct {
		_   [0]uintptr
		Pix v4l2PixFormat
		_   [200 - unsafe.Sizeof(v4l2PixFormat{})]byte
	}
}

type v4l2FrmSizeEnum struct {
	Index       uint32
	PixelFormat uint32
	Type        uint32
	Size        [6]uint32
	Reserved    [2]uint32
}

type v4l2RequestBuffers struct {
	Count, Type, Memory, Capabilities uint32
	Flags                             uint8
	Reserved                          [3]uint8
}

type v4l2Buffer struct {
	Index, Type, BytesUsed, Flags, Field uint32
	Timestamp                            unix.Timeval
	Timecode                             [16]byte
	Sequence, Memory                     uint32
	M                                    uintptr
	Length, Reserved2, RequestFD         uint32
}

type v4l2QueryCtrl struct {
	ID, Type                        uint32
	Name                            [32]byte
	Minimum, Maximum, Step, Default int32
	Flags                           uint32
	Reserved                        [2]uint32
}

type v4l2Control struct {
	ID    uint32
	Value int32
}

const (
	capVideoCapture = 0x00000001
	capDeviceCaps   = 0x80000000

	bufTypeVideoCapture = 1
	memoryMMAP          = 1
	bufFlagError        = 0x40
	frmSizeDiscrete     = 1
	ctrlFlagDisabled    = 0x0001

	cidExposureAuto     = 0x009a0901 // menu: 1 manual, 3 aperture priority (auto)
	cidExposureAbsolute = 0x009a0902
	cidAutoWhiteBalance = 0x0098090c
	cidFocusAbsolute    = 0x009a090a
	cidFocusAuto        = 0x009a090c
)

func ioc(dir, nr, size uintptr) uintptr { return dir<<30 | size<<16 | 'V'<<8 | nr }

var (
	vidiocQueryCap      = ioc(2, 0, unsafe.Sizeof(v4l2Capability{}))
	vidiocEnumFmt       = ioc(3, 2, unsafe.Sizeof(v4l2FmtDesc{}))
	vidiocSFmt          = ioc(3, 5, unsafe.Sizeof(v4l2Format{}))
	vidiocReqBufs       = ioc(3, 8, unsafe.Sizeof(v4l2RequestBuffers{}))
	vidiocQueryBuf      = ioc(3, 9, unsafe.Sizeof(v4l2Buffer{}))
	vidiocQBuf          = ioc(3, 15, unsafe.Sizeof(v4l2Buffer{}))
	vidiocDQBuf         = ioc(3, 17, unsafe.Sizeof(v4l2Buffer{}))
	vidiocStreamOn      = ioc(1, 18, unsafe.Sizeof(int32(0)))
	vidiocStreamOff     = ioc(1, 19, unsafe.Sizeof(int32(0)))
	vidiocGCtrl         = ioc(3, 27, unsafe.Sizeof(v4l2Control{}))
	vidiocSCtrl         = ioc(3, 28, unsafe.Sizeof(v4l2Control{}))
	vidiocQueryCtrl     = ioc(3, 36, unsafe.Sizeof(v4l2QueryCtrl{}))
	vidiocEnumFrameSize = ioc(3, 74, unsafe.Sizeof(v4l2FrmSizeEnum{}))
)

func ioctl(fd int, req uintptr, arg unsafe.Pointer) error {
	for {
		_, _, e := unix.Syscall(unix.SYS_IOCTL, uintptr(fd), req, uintptr(arg))
		if e == unix.EINTR {
			continue
		}
		if e != 0 {
			return e
		}
		return nil
	}
}

func fourcc(s string) uint32 {
	return uint32(s[0]) | uint32(s[1])<<8 | uint32(s[2])<<16 | uint32(s[3])<<24
}

func fourccName(v uint32) string {
	return string([]byte{byte(v), byte(v >> 8), byte(v >> 16), byte(v >> 24)})
}

func cString(b []byte) string {
	if i := bytes.IndexByte(b, 0); i >= 0 {
		b = b[:i]
	}
	return string(b)
}

// Device is a V4L2 capture device.
type Device struct {
	Path  string   `json:"path"`
	Name  string   `json:"name"`
	Sizes []string `json:"sizes"` // MJPEG sizes, the largest first
}

// List returns the capture devices.
func List() []Device {
	paths, _ := filepath.Glob("/dev/video*")
	sort.Strings(paths)
	var out []Device
	for _, p := range paths {
		fd, err := unix.Open(p, unix.O_RDWR|unix.O_NONBLOCK|unix.O_CLOEXEC, 0)
		if err != nil {
			continue
		}
		var c v4l2Capability
		if ioctl(fd, vidiocQueryCap, unsafe.Pointer(&c)) == nil {
			caps := c.Capabilities
			if caps&capDeviceCaps != 0 {
				caps = c.DeviceCaps
			}
			if caps&capVideoCapture != 0 {
				d := Device{Path: p, Name: cString(c.Card[:])}
				if f, ok := pickFormat(fd); ok {
					for _, s := range sizes(fd, f) {
						d.Sizes = append(d.Sizes, fmt.Sprintf("%s %dx%d", f, s.X, s.Y))
					}
				}
				out = append(out, d)
			}
		}
		unix.Close(fd)
	}
	return out
}

var formats = []string{"MJPG", "JPEG", "YUYV"}

func pickFormat(fd int) (string, bool) {
	have := map[string]bool{}
	for i := uint32(0); i < 64; i++ {
		d := v4l2FmtDesc{Index: i, Type: bufTypeVideoCapture}
		if ioctl(fd, vidiocEnumFmt, unsafe.Pointer(&d)) != nil {
			break
		}
		have[fourccName(d.PixelFormat)] = true
	}
	for _, f := range formats {
		if have[f] {
			return f, true
		}
	}
	return "", false
}

// sizes returns the discrete sizes of a format, the largest first.
func sizes(fd int, f string) []image.Point {
	var out []image.Point
	for i := uint32(0); i < 128; i++ {
		e := v4l2FrmSizeEnum{Index: i, PixelFormat: fourcc(f)}
		if ioctl(fd, vidiocEnumFrameSize, unsafe.Pointer(&e)) != nil {
			break
		}
		if e.Type == frmSizeDiscrete {
			out = append(out, image.Pt(int(e.Size[0]), int(e.Size[1])))
		} else {
			out = append(out, image.Pt(int(e.Size[1]), int(e.Size[4])))
			break
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].X*out[i].Y > out[j].X*out[j].Y })
	return out
}

// LiveMax is the largest size of a live picture.
var LiveMax = image.Pt(1920, 1080)

// V4L2 is a webcam. It keeps the stream open between grabs, and closes it after IdleClose with
// no grab. A grab in another mode restarts the stream at the size of that mode.
type V4L2 struct {
	Path      string
	IdleClose time.Duration

	mu      sync.Mutex
	fd      int
	format  string
	size    image.Point
	bpl     int
	bufs    [][]byte
	last    time.Time
	timer   *time.Timer
	focusAt *int // the fixed lens position to set after each open, or nil for autofocus
	locked  bool
}

// OpenV4L2 checks the device and returns the source. The stream opens at the first grab.
func OpenV4L2(path string) (*V4L2, error) {
	fd, err := unix.Open(path, unix.O_RDWR|unix.O_NONBLOCK|unix.O_CLOEXEC, 0)
	if err != nil {
		return nil, fmt.Errorf("camera: open %s: %w", path, err)
	}
	defer unix.Close(fd)
	var c v4l2Capability
	if err := ioctl(fd, vidiocQueryCap, unsafe.Pointer(&c)); err != nil {
		return nil, fmt.Errorf("camera: %s is not a V4L2 device: %w", path, err)
	}
	if _, ok := pickFormat(fd); !ok {
		return nil, fmt.Errorf("camera: %s has no MJPEG or YUYV format", path)
	}
	return &V4L2{Path: path, fd: -1, IdleClose: 20 * time.Second}, nil
}

func (v *V4L2) Name() string { return v.Path }

// Close stops the stream.
func (v *V4L2) Close() error {
	v.mu.Lock()
	defer v.mu.Unlock()
	v.stop()
	return nil
}

func (v *V4L2) stop() {
	if v.fd < 0 {
		return
	}
	typ := int32(bufTypeVideoCapture)
	ioctl(v.fd, vidiocStreamOff, unsafe.Pointer(&typ))
	for _, b := range v.bufs {
		unix.Munmap(b)
	}
	v.bufs = nil
	rb := v4l2RequestBuffers{Count: 0, Type: bufTypeVideoCapture, Memory: memoryMMAP}
	ioctl(v.fd, vidiocReqBufs, unsafe.Pointer(&rb))
	unix.Close(v.fd)
	v.fd = -1
}

func (v *V4L2) want(m Mode, all []image.Point) image.Point {
	if len(all) == 0 {
		return LiveMax
	}
	if m == Scan {
		return all[0]
	}
	for _, s := range all {
		if s.X <= LiveMax.X && s.Y <= LiveMax.Y {
			return s
		}
	}
	return all[len(all)-1]
}

func (v *V4L2) start(m Mode) error {
	fd, err := unix.Open(v.Path, unix.O_RDWR|unix.O_NONBLOCK|unix.O_CLOEXEC, 0)
	if err != nil {
		return fmt.Errorf("camera: open: %w", err)
	}
	f, ok := pickFormat(fd)
	if !ok {
		unix.Close(fd)
		return errors.New("camera: no MJPEG or YUYV format")
	}
	sz := v.want(m, sizes(fd, f))
	var vf v4l2Format
	vf.Type = bufTypeVideoCapture
	vf.Fmt.Pix = v4l2PixFormat{Width: uint32(sz.X), Height: uint32(sz.Y), PixelFormat: fourcc(f)}
	if err := ioctl(fd, vidiocSFmt, unsafe.Pointer(&vf)); err != nil {
		unix.Close(fd)
		if err == unix.EBUSY {
			return errors.New("camera: another program uses the camera")
		}
		return fmt.Errorf("camera: set the format: %w", err)
	}
	v.fd = fd
	v.format = fourccName(vf.Fmt.Pix.PixelFormat)
	v.size = image.Pt(int(vf.Fmt.Pix.Width), int(vf.Fmt.Pix.Height))
	v.bpl = int(vf.Fmt.Pix.BytesPerLine)
	rb := v4l2RequestBuffers{Count: 3, Type: bufTypeVideoCapture, Memory: memoryMMAP}
	if err := ioctl(fd, vidiocReqBufs, unsafe.Pointer(&rb)); err != nil || rb.Count == 0 {
		v.stop()
		return fmt.Errorf("camera: request buffers: %v", err)
	}
	for i := uint32(0); i < rb.Count; i++ {
		b := v4l2Buffer{Index: i, Type: bufTypeVideoCapture, Memory: memoryMMAP}
		if err := ioctl(fd, vidiocQueryBuf, unsafe.Pointer(&b)); err != nil {
			v.stop()
			return fmt.Errorf("camera: query a buffer: %w", err)
		}
		mem, err := unix.Mmap(fd, int64(b.M), int(b.Length), unix.PROT_READ|unix.PROT_WRITE, unix.MAP_SHARED)
		if err != nil {
			v.stop()
			return fmt.Errorf("camera: map a buffer: %w", err)
		}
		v.bufs = append(v.bufs, mem)
		if err := ioctl(fd, vidiocQBuf, unsafe.Pointer(&b)); err != nil {
			v.stop()
			return fmt.Errorf("camera: queue a buffer: %w", err)
		}
	}
	typ := int32(bufTypeVideoCapture)
	if err := ioctl(fd, vidiocStreamOn, unsafe.Pointer(&typ)); err != nil {
		v.stop()
		if err == unix.ENOSPC {
			return errors.New("camera: too little USB bandwidth: use another USB port")
		}
		return fmt.Errorf("camera: start the stream: %w", err)
	}
	if v.focusAt != nil {
		v.setCtrl(cidFocusAuto, 0)
		v.setCtrl(cidFocusAbsolute, *v.focusAt)
	}
	return nil
}

// frame waits for the next frame and returns a copy of it.
func (v *V4L2) frame(ctx context.Context) ([]byte, error) {
	fds := []unix.PollFd{{Fd: int32(v.fd), Events: unix.POLLIN}}
	deadline := time.Now().Add(5 * time.Second)
	for ctx.Err() == nil {
		if time.Now().After(deadline) {
			return nil, errors.New("camera: no frame")
		}
		n, err := unix.Poll(fds, 200)
		if err != nil && err != unix.EINTR {
			return nil, err
		}
		if n <= 0 {
			continue
		}
		b := v4l2Buffer{Type: bufTypeVideoCapture, Memory: memoryMMAP}
		if err := ioctl(v.fd, vidiocDQBuf, unsafe.Pointer(&b)); err != nil {
			if err == unix.EAGAIN {
				continue
			}
			return nil, fmt.Errorf("camera: read a frame: %w", err)
		}
		var data []byte
		if b.Flags&bufFlagError == 0 && b.BytesUsed > 0 && int(b.Index) < len(v.bufs) {
			src := v.bufs[b.Index][:min(int(b.BytesUsed), len(v.bufs[b.Index]))]
			data = append([]byte(nil), src...)
		}
		ioctl(v.fd, vidiocQBuf, unsafe.Pointer(&b))
		if data != nil {
			return data, nil
		}
	}
	return nil, ctx.Err()
}

// Grab returns a fresh picture. After a start it drops the first frames, which can be dark.
func (v *V4L2) Grab(ctx context.Context, m Mode) (*Frame, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	v.last = time.Now()
	if v.timer == nil && v.IdleClose > 0 {
		v.timer = time.AfterFunc(v.IdleClose, v.idle)
	}
	fresh := false
	if v.fd >= 0 {
		var all []image.Point
		if f, ok := pickFormat(v.fd); ok {
			all = sizes(v.fd, f)
		}
		if v.want(m, all) != v.size {
			v.stop()
		}
	}
	if v.fd < 0 {
		if err := v.start(m); err != nil {
			return nil, err
		}
		fresh = true
	}
	drop := 1 // a queued frame can be old: take the next one
	if fresh {
		drop = 4
	}
	var data []byte
	var err error
	for i := 0; i <= drop; i++ {
		if data, err = v.frame(ctx); err != nil {
			v.stop()
			return nil, err
		}
	}
	return v.toFrame(data)
}

func (v *V4L2) idle() {
	v.mu.Lock()
	defer v.mu.Unlock()
	if time.Since(v.last) >= v.IdleClose {
		v.stop()
		v.timer = nil
		return
	}
	v.timer = time.AfterFunc(v.IdleClose-time.Since(v.last)+time.Second, v.idle)
}

func (v *V4L2) toFrame(data []byte) (*Frame, error) {
	switch v.format {
	case "MJPG", "JPEG":
		b, w, h, err := FixJPEG(data)
		if err != nil {
			return nil, err
		}
		return &Frame{JPEG: b, W: w, H: h}, nil
	case "YUYV":
		w, h := v.size.X, v.size.Y
		bpl := v.bpl
		if bpl == 0 {
			bpl = 2 * w
		}
		if len(data) < bpl*h {
			return nil, errors.New("camera: short YUYV frame")
		}
		img := image.NewYCbCr(image.Rect(0, 0, w, h), image.YCbCrSubsampleRatio422)
		for y := 0; y < h; y++ {
			row := data[y*bpl:]
			for x := 0; x+1 < w; x += 2 {
				i := x * 2
				img.Y[y*img.YStride+x] = row[i]
				img.Y[y*img.YStride+x+1] = row[i+2]
				ci := y*img.CStride + x/2
				img.Cb[ci] = row[i+1]
				img.Cr[ci] = row[i+3]
			}
		}
		return FromImage(img)
	}
	return nil, fmt.Errorf("camera: format %s", v.format)
}

func (v *V4L2) ctrlFD() (int, func(), error) {
	if v.fd >= 0 {
		return v.fd, func() {}, nil
	}
	fd, err := unix.Open(v.Path, unix.O_RDWR|unix.O_NONBLOCK|unix.O_CLOEXEC, 0)
	if err != nil {
		return -1, nil, err
	}
	return fd, func() { unix.Close(fd) }, nil
}

func (v *V4L2) setCtrl(id uint32, val int) error {
	fd, done, err := v.ctrlFD()
	if err != nil {
		return err
	}
	defer done()
	c := v4l2Control{ID: id, Value: int32(val)}
	return ioctl(fd, vidiocSCtrl, unsafe.Pointer(&c))
}

func (v *V4L2) getCtrl(id uint32) (int, error) {
	fd, done, err := v.ctrlFD()
	if err != nil {
		return 0, err
	}
	defer done()
	c := v4l2Control{ID: id}
	err = ioctl(fd, vidiocGCtrl, unsafe.Pointer(&c))
	return int(c.Value), err
}

func (v *V4L2) queryCtrl(id uint32) (v4l2QueryCtrl, bool) {
	fd, done, err := v.ctrlFD()
	if err != nil {
		return v4l2QueryCtrl{}, false
	}
	defer done()
	q := v4l2QueryCtrl{ID: id}
	if ioctl(fd, vidiocQueryCtrl, unsafe.Pointer(&q)) != nil || q.Flags&ctrlFlagDisabled != 0 {
		return q, false
	}
	return q, true
}

// Focus returns the lens state.
func (v *V4L2) Focus() (Focus, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	q, ok := v.queryCtrl(cidFocusAbsolute)
	if !ok {
		return Focus{}, nil
	}
	f := Focus{Has: true, Min: int(q.Minimum), Max: int(q.Maximum)}
	if a, err := v.getCtrl(cidFocusAuto); err == nil {
		f.Auto = a != 0
	}
	f.Pos, _ = v.getCtrl(cidFocusAbsolute)
	return f, nil
}

// SetFocus sets autofocus, or a fixed lens position. The fixed position stays for later
// streams. A change of focus moves the picture a little, so calibrate after it.
func (v *V4L2) SetFocus(auto bool, pos int) error {
	v.mu.Lock()
	defer v.mu.Unlock()
	if auto {
		v.focusAt = nil
		return v.setCtrl(cidFocusAuto, 1)
	}
	p := pos
	v.focusAt = &p
	v.setCtrl(cidFocusAuto, 0)
	return v.setCtrl(cidFocusAbsolute, pos)
}

// Lock fixes the exposure and the white balance at their present values, or frees them.
func (v *V4L2) Lock(on bool) error {
	v.mu.Lock()
	defer v.mu.Unlock()
	if on == v.locked {
		return nil
	}
	if on {
		if e, err := v.getCtrl(cidExposureAbsolute); err == nil {
			v.setCtrl(cidExposureAuto, 1)
			v.setCtrl(cidExposureAbsolute, e)
		}
		v.setCtrl(cidAutoWhiteBalance, 0)
	} else {
		v.setCtrl(cidExposureAuto, 3)
		v.setCtrl(cidAutoWhiteBalance, 1)
	}
	v.locked = on
	return nil
}
