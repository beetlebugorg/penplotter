//go:build rp2040

package pico

import (
	"device/arm"
	"device/rp"
	"machine"
	"runtime/interrupt"

	"github.com/beetlebugorg/penplotter/firmware/config"
	"github.com/beetlebugorg/penplotter/firmware/stepgen"
	"github.com/beetlebugorg/penplotter/firmware/ui"
)

// Board is the Pico HAL.
type Board struct {
	Ex      *stepgen.Executor
	lcd     *ST7920
	beepEnd uint64
	beeping bool
	ledAt   uint64
	led     bool
}

// The step interrupt uses these package values. An interrupt handler cannot be a closure.
var (
	ex        *stepgen.Executor
	nextAlarm uint32
	stepPins  uint32
	stepBit   [stepgen.NumCh]uint32
	dirBit    [stepgen.NumCh]uint32
	dirInvert uint8
	servoCh   uint8
	servoTop  uint32
)

const (
	stepAlarm  = 2 // TinyGo uses alarm 0 for sleep
	tickPeriod = 1_000_000 / config.TickHz
)

// New sets up all pins and starts the step timer.
func New() *Board {
	b := &Board{Ex: &stepgen.Executor{}}
	ex = b.Ex

	ledInit()
	for _, p := range []machine.Pin{PinXStep, PinXDir, PinYStep, PinYDir, PinY2Step, PinY2Dir, PinBeeper} {
		p.Configure(machine.PinConfig{Mode: machine.PinOutput})
		p.Low()
	}
	PinEn.Configure(machine.PinConfig{Mode: machine.PinOutput})
	PinEn.High() // drivers off
	for _, p := range []machine.Pin{PinXMin, PinYMin, PinY2Min, PinEncA, PinEncB, PinEncBtn} {
		p.Configure(machine.PinConfig{Mode: machine.PinInputPullup})
	}
	stepBit = [stepgen.NumCh]uint32{1 << uint32(PinXStep), 1 << uint32(PinYStep), 1 << uint32(PinY2Step)}
	dirBit = [stepgen.NumCh]uint32{1 << uint32(PinXDir), 1 << uint32(PinYDir), 1 << uint32(PinY2Dir)}
	stepPins = stepBit[0] | stepBit[1] | stepBit[2]
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

	// Servo: 50 Hz PWM.
	servoPWM.Configure(machine.PWMConfig{Period: config.ServoPeriodUs * 1000})
	servoCh, _ = servoPWM.Channel(PinServo)
	servoTop = servoPWM.Top()
	setServo(config.PenUpDeg)

	setupEncoder()
	b.lcd = NewST7920()

	// Step timer: TIMER alarm 2, re-armed every tick.
	intr := interrupt.New(rp.IRQ_TIMER_IRQ_2, stepISR)
	intr.SetPriority(0x00)
	nextAlarm = rp.TIMER.TIMERAWL.Get() + 1000
	rp.TIMER.ALARM2.Set(nextAlarm)
	rp.TIMER.INTE.SetBits(1 << stepAlarm)
	intr.Enable()
	return b
}

var endstopPins = [stepgen.NumCh]machine.Pin{PinXMin, PinYMin, PinY2Min}

func endstop(ch int) bool {
	return endstopPins[ch].Get() == config.EndstopTriggeredHigh
}

func setServo(deg int16) {
	us := uint32(config.ServoMinUs) + uint32(deg)*(config.ServoMaxUs-config.ServoMinUs)/180
	servoPWM.Set(servoCh, servoTop*us/config.ServoPeriodUs)
}

// stepISR runs at TickHz. Keep it short.
func stepISR(interrupt.Interrupt) {
	rp.TIMER.INTR.Set(1 << stepAlarm)
	nextAlarm += tickPeriod
	if now := rp.TIMER.TIMERAWL.Get(); int32(nextAlarm-now) <= 1 {
		nextAlarm = now + tickPeriod // the tick was late; do not wait for a timer wrap
	}
	rp.TIMER.ALARM2.Set(nextAlarm)

	// End the step pulse of the previous tick. The pulse is one tick long.
	rp.SIO.GPIO_OUT_CLR.Set(stepPins)

	o := ex.Tick()
	if o.DirSet {
		d := o.Dir ^ dirInvert
		var set, clr uint32
		for a := 0; a < stepgen.NumCh; a++ {
			if d&(1<<a) != 0 {
				clr |= dirBit[a] // negative direction: DIR low
			} else {
				set |= dirBit[a]
			}
		}
		rp.SIO.GPIO_OUT_SET.Set(set)
		rp.SIO.GPIO_OUT_CLR.Set(clr)
		// The TMC2209 needs 20 ns from DIR to STEP.
		arm.Asm("nop\nnop\nnop\nnop")
	}
	if o.Servo >= 0 {
		setServo(o.Servo)
	}
	if o.Step != 0 {
		var set uint32
		for a := 0; a < stepgen.NumCh; a++ {
			if o.Step&(1<<a) != 0 {
				set |= stepBit[a]
			}
		}
		rp.SIO.GPIO_OUT_SET.Set(set)
	}
}

// NowMicros implements controller.HAL.
func (b *Board) NowMicros() uint64 {
	for {
		hi := rp.TIMER.TIMERAWH.Get()
		lo := rp.TIMER.TIMERAWL.Get()
		if rp.TIMER.TIMERAWH.Get() == hi {
			return uint64(hi)<<32 | uint64(lo)
		}
	}
}

// SetMotors implements controller.HAL.
func (b *Board) SetMotors(on bool) { PinEn.Set(!on) }

// Endstop implements controller.HAL.
func (b *Board) Endstop(ch int) bool { return endstop(ch) }

// Encoder implements controller.HAL.
func (b *Board) Encoder() int { return encoderDetents() }

// Button implements controller.HAL. The button pulls the pin to GND.
func (b *Board) Button() bool { return !PinEncBtn.Get() }

// Beep implements controller.HAL.
func (b *Board) Beep(ms int) {
	PinBeeper.High()
	b.beeping = true
	b.beepEnd = b.NowMicros() + uint64(ms)*1000
}

// ReadSerial implements controller.HAL.
func (b *Board) ReadSerial() (byte, bool) {
	if machine.Serial.Buffered() == 0 {
		return 0, false
	}
	c, err := machine.Serial.ReadByte()
	return c, err == nil
}

// WriteSerial implements controller.HAL.
func (b *Board) WriteSerial(s string) { machine.Serial.Write([]byte(s)) }

// Display implements controller.HAL.
func (b *Board) Display() ui.Display { return b.lcd }

// Poll implements controller.HAL.
func (b *Board) Poll() {
	now := b.NowMicros()
	if b.beeping && now >= b.beepEnd {
		PinBeeper.Low()
		b.beeping = false
	}
	if now-b.ledAt > 500_000 {
		b.ledAt = now
		b.led = !b.led
		ledSet(b.led)
	}
}
