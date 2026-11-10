# Wiring

This page shows how to connect the plotter parts to the controller.
The frame stands on the table. The paper lies on the table. The X beam rides on two Y carriages. Each Y carriage runs on 3 V-wheels in a long frame rail.
Each Y side has its own motor, belt and endstop: Y1 on the left, Y2 on the right. So the plotter uses three motor drivers.
`docs/bom.md` lists the parts and where to buy them.

The build uses the stock CR-10 V3 control box. The first part of this page is for that build.
The second part is for the Pico W firmware in `firmware/cmd/pico`. This build does not use it.

## Stock controller wiring

The stock control box holds the Creality v2.5.2 mainboard (ATmega2560, 16 MHz, 8 KB RAM), the 350 W supply, and the LCD with the knob.
The stock harness stays as it is. It ends at two small Creality boards: the head board on the X beam and the base board on the back bar.
Each board stands bare on two 4 mm nylon standoffs, held by cable ties.
The pin map is also in `firmware/board/mega/pins.go`. Keep the two the same.

### Safety rules

- Turn off the control box before you connect or disconnect a motor. A motor that you disconnect from a powered driver can destroy the driver.
- Turn off the control box before you connect the servo.
- Make no changes inside the control box. All plotter parts connect to the head board and the base board.
- Check the voltage switch of the supply before the first power on. Set 115 V for the US.

### Block diagram

```
 Control box (stock)                      Stock harness          Plotter parts
 ───────────────────                      ─────────────          ─────────────
 350 W supply, 24 V ──► v2.5.2 mainboard
 USB (115200 baud) ──► ATmega2560 ──► X driver  ──► head board X     ──► X motor
                                  ──► Y driver  ──► base board Y     ──► Y1 motor (left)
                                  ──► Z driver  ──► base board Z1    ──► Y2 motor (right)
                                  ◄── X min     ◄── head board X-    ◄── X endstop
                                  ◄── Y min     ◄── base board Y-    ◄── Y1 endstop (front left)
                                  ◄── Z min     ◄── base board Z-    ◄── Y2 endstop (front right)
                                  ──► servo PWM ──► head board BL_T  ──► pen servo
 LCD with knob (ST7920) on the stock ribbon
```

### Board sockets

| Board socket | Plotter part | Mainboard driver or pin |
|---|---|---|
| Head board `X` | X motor | X driver |
| Head board `X-` | X endstop | X min (PE5) |
| Head board `BL_T` | Pen servo (through a pigtail) | Servo signal PB5 (D11), 5 V, GND |
| Base board `Y` | Y1 motor (left) | Y driver |
| Base board `Z1` | Y2 motor (right) | Z driver |
| Base board `Y-` | Y1 endstop (front left) | Y min (PJ1) |
| Base board `Z-` | Y2 endstop (front right) | Z min (PD3) |
| Base board `Z2` | Not used | Z driver (parallel to `Z1`) |
| Head board `HEAT` | Not used | Heater MOSFET PB4 (D10). The firmware holds it off. |
| Head board `E`, `TH`, `FAN`, `K_FAN` | Not used | Leave them empty |

### Pen servo on `BL_T`

The `BL_T` socket has five pins: GND, 5 V, signal, GND, and a sensor pin that the plotter does not use.
A JST XH 5-pin pigtail connects the socket to a 70 cm servo extension (BOM line S2). You can also make the lead with S3 and S6.

| Servo wire | `BL_T` pin |
|---|---|
| Brown (GND) | GND (pin 1) |
| Red (5 V) | 5 V (pin 2) |
| Orange (signal) | Signal (pin 3) |

> **Caution:** Measure the `BL_T` pins with a meter before you connect the servo. With the box
> on, pin 2 must show 5 V to pin 1. The pin order comes from the board silkscreen and from
> earlier work on this tool head. It is not checked on your board.

The mainboard 5 V supply also feeds the LCD and the processor. An SG90 servo takes about 0.25 A when it moves.
Use an SG90 or an MG90S. Do not use a large servo.

The default angles are 130° for pen up and 80° for pen down. At 90° the horn is level.
Tune the angles with the knob menu (Pen up +1 and -1, Pen down +1 and -1), or send `M281 U<up> D<down>`.

### Mainboard pin map

The firmware uses these ATmega2560 pins. Nothing in this table needs a wire from you. The stock harness and the stock LCD ribbon connect them.

| Signal | ATmega2560 pin | Note |
|---|---|---|
| X STEP, DIR, EN | PF0, PF1, PD7 | X driver |
| Y1 STEP, DIR, EN | PF6, PF7, PF2 | Y driver |
| Y2 STEP, DIR, EN | PL3, PL1, PK0 | Z driver |
| X endstop | PE5 | Head board `X-` |
| Y1 endstop | PJ1 | Base board `Y-` |
| Y2 endstop | PD3 | Base board `Z-` |
| Servo | PB5 (D11, OC1A) | Head board `BL_T`, signal pin |
| LCD CS (RS) | PH1 | ST7920 |
| LCD SCK (E) | PA1 | ST7920 |
| LCD data (R/W) | PH0 | ST7920 |
| Encoder A, B | PC4, PC6 | The knob |
| Encoder button | PC2 | Low when pressed |
| Beeper | PC0 (D37) | Check it on your board |
| E STEP, DIR, EN | PA4, PA6, PA2 | Free. Kept for a later Z axis. |

The EN pins are active low. The firmware sets them high at power on, so the motors are off until a move.
The onboard drivers run at 1/16 microsteps. The firmware uses 80 steps/mm, which needs 1/16.

### Motor current

The onboard drivers keep the current setting of the printer. Do not change it.
A pen plotter needs less force than a printer. If a motor gets hot, read `docs/bom.md`, "Mainboard", before you touch the drivers.

### Endstops

There are three switches: X min (left), Y1 min (front left) and Y2 min (front right).
The stock switches are probably normally closed to GND. The firmware treats a HIGH pin as triggered, the same as the stock firmware.
The mainboard pins use their internal pull-ups.

Test the switches before the first `G28`:

1. Send `M119`.
2. The reply shows `x_min: open`, `y1_min: open` and `y2_min: open` when the carriages are away from the switches.
3. Push each switch by hand and send `M119` again. The reply must show `TRIGGERED` for that switch only.
4. If the result is the opposite, set `EndstopTriggeredHigh = false` in `firmware/config/config.go`. Then build and flash the firmware again.

### Cable lengths

The lengths come from the cable routes of the 3D view (`sim/web/wiring.js`) and the anchors of `hardware/stl/detail/manifest.json`. They are the lengths of the straight route segments, plug to plug. Add slack for the plugs and the bends.

| Cable | Moves | Route | Length |
|---|---|---|---|
| Head harness | yes | From the control box along the table to the back left corner, through the Y drag chain (506 mm), then along the back of the beam to the head board. | about 1.2 m (ESTIMATE) |
| Base harness | no | From the base board along the table behind the frame, then forward to the control box. | about 0.6 m (ESTIMATE) |
| Y1 motor | no | From the base board down behind the back bar, along the table, up to the motor. | about 0.28 m |
| Y2 motor | no | The same route as Y1, along the table to the right motor. | about 0.53 m |
| Y1 endstop | no | Round the front left corner, in the bottom outer slot of the left rail and the bottom slot of the back bar, to the base board. | about 0.83 m |
| Y2 endstop | no | Round the front right corner, in the bottom outer slot of the right rail and the bottom slot of the back bar, to the base board. | about 1.03 m |
| Servo lead | yes | From `BL_T` on the head board, in a free loop behind the beam, over the beam and the X plate top, down the front of the X plate to the servo. | The 70 cm extension (BOM line S2). The loom is 295 mm. |

- The Y motors stand behind the back bar on printed brackets. Their cables do not move and do not go in the drag chain.
- Only the head harness runs in the drag chain. The X motor and the X endstop plug into the head board on the gantry.
- The servo lead runs in a 1/2 inch split wire loom (BOM line M33). Cut the loom to 295 mm.
- One cable tie goes through the slot at the top left of the X plate. The other tie holds the loom to the head harness cable, above the big plug of the head board.
- The loop of the loom between the two ties is 189 mm long. It hangs free behind the beam.
- If a stock endstop cable is too short, add a JST XH 2-pin extension (BOM line S5).
- If a stock motor cable is too short, use a 1.5 m stepper cable (BOM line M31).
- The static cables lie on adhesive tie mounts on the table (BOM line M37). The endstop wires lie under slot cover strips (BOM line M36).

### Motor directions

The Y2 motor is a mirror of the Y1 motor, so `InvertDirY2 = true` is the default. In normal moves Y2 steps with Y1.
Test the Y direction before the first `G28`. Two sides that move in opposite directions twist the beam.

1. Move both Y carriages by hand to the middle of the travel.
2. Send `G91`, then `G1 Y5 F600`, then `G90`.
3. Both Y carriages must move 5 mm to the back.
4. If one side moves to the front, turn off the box at once. Set `InvertDirY` or `InvertDirY2` in `firmware/config/config.go`, then build and flash the firmware again.
5. Do the same test for X with `G1 X5 F600`. The carriage must move to the right. If not, set `InvertDirX`.

### Homing and squaring

`G28` homes X, then Y. `G28 Y` homes Y only.

1. Both Y motors move to the front at the same time.
2. Each side stops when its own switch triggers. This makes the beam square to the frame rails.
3. Both sides back off 3 mm and move to the switches again slowly.
4. If the beam is still not square, measure the error. Set `Y2HomeOffsetMM` in `firmware/config/config.go`. After homing, Y2 moves this distance alone. A positive value moves Y2 away from its switch.

`M114` shows the step counters of X, Y1 and Y2. After homing, the Y1 and Y2 counters are 0.

## Pico W firmware wiring

This build does not use the Pico W firmware. This part shows how to connect a Raspberry Pi Pico W to the CR-10 V3 parts for that firmware.
The pin map is also in `firmware/board/pico/pins.go`. Keep the two the same.

### Safety rules

- Disconnect the 24 V supply before you connect or disconnect a motor. A motor that you disconnect from a powered driver can destroy the driver.
- Set the buck converter to 5.1 V before you connect it to the Pico.
- Do not connect a 5 V signal to a Pico pin. The Pico pins are 3.3 V only.
- Connect all GND points together: power supply, buck converter, drivers, Pico, 74AHCT125, LCD.

### Block diagram

```
 24 V PSU ──┬── VM  TMC2209 X  ── X motor
            ├── VM  TMC2209 Y1 ── Y1 motor (left)
            ├── VM  TMC2209 Y2 ── Y2 motor (right)
            └── IN  buck ── 5.1 V ──┬── 1N5819 ──> Pico VSYS (pin 39)
                                    ├── servo red wire
                                    ├── 74AHCT125 VCC (pin 14)
                                    └── EXP1 pin 10 (LCD 5 V)

 Pico 3V3 (pin 36) ── VDD of the 3 TMC2209 boards, MS1, MS2
 Pico GPIO ── STEP/DIR/EN, endstops, servo signal, encoder
 Pico GPIO ── 74AHCT125 ── LCD CS, SCK, data, beeper
```

### Pico pin table

| Pico GPIO | Pico pin | Signal | Goes to |
|---|---|---|---|
| GP2 | 4 | X STEP | TMC2209 X, STEP |
| GP3 | 5 | X DIR | TMC2209 X, DIR |
| GP4 | 6 | Y1 STEP | TMC2209 Y1 (left), STEP |
| GP5 | 7 | Y1 DIR | TMC2209 Y1 (left), DIR |
| GP6 | 9 | EN (active low) | EN of all 3 TMC2209 boards |
| GP7 | 10 | X endstop | X switch signal wire |
| GP8 | 11 | Y1 endstop | Y1 (left) switch signal wire |
| GP9 | 12 | Servo signal | Servo orange (or yellow) wire |
| GP10 | 14 | Y2 STEP | TMC2209 Y2 (right), STEP |
| GP11 | 15 | Y2 DIR | TMC2209 Y2 (right), DIR |
| GP12 | 16 | Y2 endstop | Y2 (right) switch signal wire |
| GP16 | 21 | Beeper | 74AHCT125 input 4A (pin 12) |
| GP17 | 22 | LCD CS | 74AHCT125 input 1A (pin 2) |
| GP18 | 24 | LCD SCK (SPI0 SCK) | 74AHCT125 input 2A (pin 5) |
| GP19 | 25 | LCD data (SPI0 TX) | 74AHCT125 input 3A (pin 9) |
| GP20 | 26 | Encoder A | EXP1 pin 3 |
| GP21 | 27 | Encoder B | EXP1 pin 5 |
| GP22 | 29 | Encoder button | EXP1 pin 2 |
| GP25 | — | On-board LED (Pico H only) | Blinks while the firmware runs |
| 3V3 OUT | 36 | 3.3 V logic | TMC2209 VDD, MS1, MS2 |
| VSYS | 39 | 5 V input | Buck output through the 1N5819 |
| GND | 38 and others | Ground | Common ground |

Free pins: GP0 and GP1 (debug UART), GP13, GP14, GP15, GP26, GP27 and GP28.

A later SPI touch panel replaces the 12864 LCD and the knob, so it takes their pins:

| Touch panel signal | Pico pin |
|---|---|
| SPI0 SCK | GP18 |
| SPI0 TX (MOSI) | GP19 |
| SPI0 RX (MISO, touch controller) | GP16 (the beeper moves to GP27) |
| Display CS | GP17 |
| Display DC | GP20 |
| Touch CS | GP21 |
| Touch IRQ | GP22 |

Run a 3.3 V panel (ILI9341 or ST7796 with an XPT2046) straight from the Pico, without the 74AHCT125.

#### Pico W

The Pico W has the same pin map. Its Wi-Fi chip uses GP23, GP24, GP25 and GP29 inside the
board, and the PIO0 block. Do not connect anything to these pins. The on-board LED of the
Pico W is on the Wi-Fi chip, so the firmware does not blink it.

### Stepper drivers (Adafruit TMC2209 breakout)

You need three boards: X, Y1 and Y2. The drivers run in standalone STEP/DIR mode. The firmware does not use the UART.

| TMC2209 board pin | Connect to |
|---|---|
| VDD (logic supply) | Pico 3V3 (pin 36) |
| GND (logic) | Pico GND |
| VM (motor supply terminal) | 24 V |
| GND (motor supply terminal) | PSU GND |
| STEP | GP2 (X), GP4 (Y1) or GP10 (Y2) |
| DIR | GP3 (X), GP5 (Y1) or GP11 (Y2) |
| EN | GP6 (all 3 boards) |
| MS1 | 3.3 V (HIGH) |
| MS2 | 3.3 V (HIGH) |
| Motor outputs (1A, 1B, 2A, 2B) | The 4 motor wires: one coil on 1A/1B, the other coil on 2A/2B |

Notes:

- VDD sets the logic level. With VDD at 3.3 V the 3.3 V Pico signals are valid.
- MS1 and MS2 both HIGH set 1/16 microsteps. Both LOW set 1/8. The firmware uses 80 steps/mm, which needs 1/16.
- EN is active low. The firmware drives GP6 HIGH at power on, so the motors are off until a move.
- Put a 100 µF, 35 V or higher electrolytic capacitor across VM and GND, close to each driver. Check the polarity.
- Leave PDN_UART and the UART pins unconnected. Read the Adafruit guide for the default level of each pin.
- The Y2 motor is a mirror of the Y1 motor, so `InvertDirY2 = true` is the default. In normal moves Y2 steps with Y1.
- If an axis moves the wrong way, set `InvertDirX`, `InvertDirY` or `InvertDirY2` in `firmware/config/config.go`. You can also turn one motor plug around, with the power off.
- Test the Y direction before the first `G28 Y`. Jog Y by 1 mm in the LCD menu. Both Y carriages must move to the back. If one side moves to the front, stop and change its direction setting. Two sides that move in opposite directions twist the beam.

#### Motor current

Start at about 0.8 A RMS on all three drivers. Set the same VREF on Y1 and Y2, so both sides of the beam get the same force. Read the label of your motors (probably Creality 42-40). A pen plotter needs little force, so a low current is good. The motors and drivers stay cooler.

The TMC2209 datasheet gives the current from the reference voltage:

```
I_RMS = (VREF / 2.5 V) × (0.325 V / (R_SENSE + 0.02 Ω)) × 0.707
```

With R_SENSE = 0.11 Ω this is about `VREF = 1.41 × I_RMS`. So 0.8 A needs about 1.13 V.
Read R_SENSE on your board and in the Adafruit guide before you set VREF.
Measure VREF between the potentiometer (or the VREF pad) and GND, with the motors disconnected.

### Endstops

There are three switches: X min (left), Y1 min (front left) and Y2 min (front right).
The stock switches are probably normally closed to GND. The stock firmware treats a HIGH pin as triggered.
The Pico uses its internal pull-up to 3.3 V. Do not connect the switch to 5 V.

| Switch wire | Connect to |
|---|---|
| Signal | GP7 (X), GP8 (Y1) or GP12 (Y2) |
| GND | Pico GND |

The plug is probably a 3-pin JST-XH with 2 wires. Find the signal wire and the GND wire with a meter.

Test the switches before the first G28:

1. Send `M119`.
2. The reply shows `x_min: open`, `y1_min: open` and `y2_min: open` when the carriages are away from the switches.
3. Push each switch by hand and send `M119` again. The reply must show `TRIGGERED` for that switch only.
4. You can also see the three switches on the LCD: Menu > Endstops.
5. If the result is the opposite, set `EndstopTriggeredHigh = false` in `firmware/config/config.go`.

### Pen servo

| Servo wire | Connect to |
|---|---|
| Brown or black | GND |
| Red | Buck 5.1 V (before the diode) |
| Orange or yellow | GP9 |

Do not power the servo from the Pico 3V3 pin or from VSYS. A servo pulls current peaks that can reset the Pico.

The default angles are 130° for pen up and 80° for pen down. At 90° the horn is level.
Tune the angles in the LCD menu: Menu > Pen setup. You can also send `M281 U<up> D<down>`.

### LCD (CR-10 V3 12864 display)

The display uses an ST7920 controller in serial mode. It runs at 5 V.
The 74AHCT125 changes the 3.3 V Pico signals to 5 V signals.

#### EXP1 pinout

The display PCB calls the plug "EXP3". The old mainboard calls it "EXP1".
Confirm each pin with a meter before you connect the Pico. Pins 9 and 10 are the most likely GND and 5 V, but measure them.

| EXP1 pin | Signal | Connect to |
|---|---|---|
| 1 | Beeper | 74AHCT125 output 4Y (pin 11) |
| 2 | Encoder button | GP22 |
| 3 | Encoder A | GP20 |
| 4 | Not used | — |
| 5 | Encoder B | GP21 |
| 6 | ST7920 SCLK (E) | 74AHCT125 output 2Y (pin 6) |
| 7 | ST7920 CS (RS) | 74AHCT125 output 1Y (pin 3) |
| 8 | ST7920 SID data (R/W) | 74AHCT125 output 3Y (pin 8) |
| 9 | GND | GND |
| 10 | 5 V | Buck 5.1 V |

#### 74AHCT125 wiring (DIP-14)

| 74AHCT125 pin | Name | Connect to |
|---|---|---|
| 1 | 1OE | GND |
| 2 | 1A | GP17 (LCD CS) |
| 3 | 1Y | EXP1 pin 7 |
| 4 | 2OE | GND |
| 5 | 2A | GP18 (LCD SCK) |
| 6 | 2Y | EXP1 pin 6 |
| 7 | GND | GND |
| 8 | 3Y | EXP1 pin 8 |
| 9 | 3A | GP19 (LCD data) |
| 10 | 3OE | GND |
| 11 | 4Y | EXP1 pin 1 (beeper) |
| 12 | 4A | GP16 (beeper) |
| 13 | 4OE | GND |
| 14 | VCC | 5.1 V |

Put a 100 nF capacitor between pin 14 and pin 7, close to the chip.

#### Beeper

One 74AHCT125 output gives about 8 mA. Measure the buzzer current at 5 V before you connect it.
If the buzzer needs more than 8 mA, use an NPN transistor:

1. Connect 4Y through a 1 kΩ resistor to the base of a 2N3904.
2. Connect the emitter to GND.
3. Connect the buzzer between 5 V and the collector.

You can also leave the beeper disconnected. The firmware works without it.

#### Encoder inputs

The encoder and the button connect directly to the Pico. The Pico pull-ups hold them at 3.3 V.
A pull-up to 5 V on the display board would put 5 V on a Pico pin. Check for this before you connect:

1. Disconnect the display from all power.
2. Measure the resistance from EXP1 pins 2, 3 and 5 to EXP1 pin 10 (5 V).
3. If you measure a low value (for example 10 kΩ), the display has pull-ups to 5 V.
4. In that case, put each of the 3 lines through a series 10 kΩ resistor and a 3.3 V clamp, or use a second level shifter.
5. If you measure an open circuit, connect the lines directly.

### Homing and squaring

`G28` homes X, then Y. `G28 Y` homes Y only.

1. Both Y motors move to the front at the same time.
2. Each side stops when its own switch triggers. This makes the beam square to the frame rails.
3. Both sides back off 3 mm and move to the switches again slowly.
4. If the beam is still not square, measure the error. Set `Y2HomeOffsetMM` in `firmware/config/config.go`. After homing, Y2 moves this distance alone. A positive value moves Y2 away from its switch.

The Menu > Endstops screen shows "Y2-Y1": the difference between the two Y step counters. It is 0 after homing.

### Power

1. Set the buck converter output to 5.1 V with a meter. Do this with no load.
2. Connect the buck output through a 1N5819 Schottky diode to VSYS (pin 39). The stripe of the diode goes to VSYS.
3. The diode lets you connect the USB cable at the same time. USB power cannot flow back into the buck converter.

A general-purpose silicon diode (1N4001 type) also works. It drops 0.7 V, so VSYS gets about 4.4 V. The Pico accepts 1.8 V to 5.5 V on VSYS.

### First power on

1. Disconnect the motors. Connect the 24 V supply.
2. Measure 5.1 V at the buck output and about 4.8 V at VSYS.
3. Set VREF on both drivers.
4. Disconnect the 24 V supply. Connect the motors.
5. Connect the USB cable. Hold BOOTSEL when you connect it the first time, then copy `build/plotter-w.uf2` (Pico W) or `build/plotter.uf2` (Pico H) to the RPI-RP2 drive.
6. Connect a serial terminal at any baud rate. Send `M115`. The reply shows the firmware name.
7. Send `M119` and test the endstops.
8. Move each axis a short distance away from the switch with the LCD menu (Menu > Move axis). Check that both Y carriages move in the same direction.
9. Send `G28`.
