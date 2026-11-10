//go:build atmega2560

package mega

import (
	"device/avr"
	"machine"
	"runtime/interrupt"
	"runtime/volatile"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
)

// Board is the HAL of the stock CR-10 V3 mainboard.
type Board struct {
	Ex      *stepgen.Executor
	lcd     *ST7920
	beepEnd uint64
	beeping bool
}

// The step interrupt uses these package values. An interrupt handler cannot be a closure.
var (
	ex        *stepgen.Executor
	dirInvert uint8
	tickCount volatile.Register32 // step ticks since the start (TickHz)

	// Received bytes. The UART buffer of TinyGo holds only 32 bytes, so the step
	// interrupt moves the bytes to this larger ring.
	rx         [256]byte
	rxHead     volatile.Register8 // written by the interrupt
	rxTail     uint8              // written by the main loop
	encDivider uint8
)

const (
	// Timer 4 runs at 16 MHz / 8 = 2 MHz. CTC mode, TOP = OCR4A.
	tickTop = 16_000_000/8/config.TickHz - 1
	// Timer 1 runs at 2 MHz too: 0.5 us per count. Fast PWM, TOP = ICR1 (mode 14).
	servoTop = 2*config.ServoPeriodUs - 1
)

// New sets up all pins and starts the step timer.
func New() *Board {
	b := &Board{Ex: &stepgen.Executor{}}
	ex = b.Ex

	machine.Serial.Configure(machine.UARTConfig{BaudRate: 115200})

	for _, p := range []machine.Pin{PinXStep, PinXDir, PinYStep, PinYDir, PinY2Step, PinY2Dir,
		PinEStep, PinEDir, PinBeeper} {
		p.Configure(machine.PinConfig{Mode: machine.PinOutput})
		p.Low()
	}
	for _, p := range []machine.Pin{PinXEn, PinYEn, PinY2En, PinEEn} {
		p.Configure(machine.PinConfig{Mode: machine.PinOutput})
		p.High() // drivers off
	}
	for _, p := range []machine.Pin{PinXMin, PinYMin, PinY2Min, PinEncA, PinEncB, PinEncBtn} {
		p.Configure(machine.PinConfig{Mode: machine.PinInputPullup})
	}
	if config.InvertDirX {
		dirInvert |= 1
	}
	if config.InvertDirY {
		dirInvert |= 2
	}
	if config.InvertDirY2 {
		dirInvert |= 4
	}
	b.Ex.Endstop = endstop

	// Servo: hardware PWM on OC1A, 50 Hz.
	PinServo.Configure(machine.PinConfig{Mode: machine.PinOutput})
	avr.TCCR1A.Set(0x80 | 0x02) // COM1A1, WGM11
	avr.TCCR1B.Set(0x10 | 0x08 | 0x02)
	avr.ICR1H.Set(uint8(servoTop >> 8))
	avr.ICR1L.Set(uint8(servoTop & 0xFF))
	setServo(config.PenUpDeg)

	// The heater output is not used. Hold its MOSFET off.
	PinHeater.Configure(machine.PinConfig{Mode: machine.PinOutput})
	PinHeater.Low()

	encState = encRead()
	b.lcd = NewST7920()

	// Step timer: timer 4, compare match A.
	interrupt.New(avr.IRQ_TIMER4_COMPA, stepISR) // AVR interrupts are always on; TIMSK4 starts it
	avr.TCCR4A.Set(0)
	avr.TCCR4B.Set(0x08 | 0x02) // WGM42 (CTC), clock / 8
	avr.OCR4AH.Set(uint8(tickTop >> 8))
	avr.OCR4AL.Set(uint8(tickTop & 0xFF))
	avr.TIMSK4.Set(0x02) // OCIE4A
	return b
}

var endstopPins = [stepgen.NumCh]machine.Pin{PinXMin, PinYMin, PinY2Min}

func endstop(ch int) bool {
	return endstopPins[ch].Get() == config.EndstopTriggeredHigh
}

// setServo sets the pulse width for an angle. A 16-bit register needs the high byte first.
func setServo(deg int16) {
	us := uint32(config.ServoMinUs) + uint32(deg)*(config.ServoMaxUs-config.ServoMinUs)/180
	v := uint16(us * 2)
	avr.OCR1AH.Set(uint8(v >> 8))
	avr.OCR1AL.Set(uint8(v))
}

// Step and direction bits on their ports. X and Y1 are on port F, Y2 is on port L.
const (
	bitXStep  = 1 << 0 // PF0
	bitXDir   = 1 << 1 // PF1
	bitYStep  = 1 << 6 // PF6
	bitYDir   = 1 << 7 // PF7
	bitY2Step = 1 << 3 // PL3
	bitY2Dir  = 1 << 1 // PL1
)

// stepISR runs at TickHz. Keep it short: at 10 kHz it has 1600 clock cycles.
func stepISR(interrupt.Interrupt) {
	// End the step pulse of the previous tick. The pulse is one tick long.
	avr.PORTF.ClearBits(bitXStep | bitYStep)
	avr.PORTL.ClearBits(bitY2Step)
	tickCount.Set(tickCount.Get() + 1)

	o := ex.Tick()
	if o.DirSet {
		d := o.Dir ^ dirInvert
		f := avr.PORTF.Get() &^ (bitXDir | bitYDir)
		if d&1 == 0 {
			f |= bitXDir // positive direction: DIR high
		}
		if d&2 == 0 {
			f |= bitYDir
		}
		avr.PORTF.Set(f)
		if d&4 == 0 {
			avr.PORTL.SetBits(bitY2Dir)
		} else {
			avr.PORTL.ClearBits(bitY2Dir)
		}
	}
	if o.Servo >= 0 {
		setServo(o.Servo)
	}
	if o.Step != 0 {
		var f uint8
		if o.Step&1 != 0 {
			f |= bitXStep
		}
		if o.Step&2 != 0 {
			f |= bitYStep
		}
		if f != 0 {
			avr.PORTF.SetBits(f)
		}
		if o.Step&4 != 0 {
			avr.PORTL.SetBits(bitY2Step)
		}
	}

	// Move received bytes to the large ring.
	for machine.Serial.Buffered() > 0 {
		h := rxHead.Get()
		if h+1 == rxTail {
			break // ring full: the host waits for "ok", so this does not happen
		}
		c, _ := machine.Serial.ReadByte()
		rx[h] = c
		rxHead.Set(h + 1)
	}

	// The encoder pins have no pin change interrupt. Read them at 2.5 kHz.
	encDivider++
	if encDivider >= 4 {
		encDivider = 0
		encPoll()
	}
}

// NowMicros implements mini.Board. The resolution is one step tick (100 us).
func (b *Board) NowMicros() uint64 {
	m := interrupt.Disable()
	t := tickCount.Get()
	interrupt.Restore(m)
	return uint64(t) * (1_000_000 / config.TickHz)
}

// SetMotors implements mini.Board. Port F also has step bits that the interrupt
// changes, so the change of the enable pins must not be interrupted.
func (b *Board) SetMotors(on bool) {
	m := interrupt.Disable()
	PinXEn.Set(!on)
	PinYEn.Set(!on)
	PinY2En.Set(!on)
	interrupt.Restore(m)
}

// Endstop implements mini.Board.
func (b *Board) Endstop(ch int) bool { return endstop(ch) }

// Encoder implements mini.Board.
func (b *Board) Encoder() int { return encoderDetents() }

// Button implements mini.Board. The button pulls the pin to GND.
func (b *Board) Button() bool { return !PinEncBtn.Get() }

// Beep implements mini.Board.
func (b *Board) Beep(ms int) {
	PinBeeper.High()
	b.beeping = true
	b.beepEnd = b.NowMicros() + uint64(ms)*1000
}

// ReadSerial implements mini.Board.
func (b *Board) ReadSerial() (byte, bool) {
	if rxTail == rxHead.Get() {
		return 0, false
	}
	c := rx[rxTail]
	rxTail++
	return c, true
}

// WriteSerial implements mini.Board.
func (b *Board) WriteSerial(s string) {
	for i := 0; i < len(s); i++ {
		machine.Serial.WriteByte(s[i])
	}
}

// Text implements mini.Board.
func (b *Board) Text(row int, s string) { b.lcd.Text(row, s) }

// Poll implements mini.Board.
func (b *Board) Poll() {
	if b.beeping && b.NowMicros() >= b.beepEnd {
		PinBeeper.Low()
		b.beeping = false
	}
}
