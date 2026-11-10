# Firmware

The firmware is written in Go and built with TinyGo. On the stock controller build it runs on the
ATmega2560 of the Creality v2.5.2 mainboard. The computer talks to it over USB serial at
115200 baud. The simulator runs the same code on a computer.

The ATmega2560 has 8 KB of RAM. The full controller (`firmware/controller`, for a Pico W board)
does not fit. The stock board runs the small controller (`firmware/mini`). It uses the same G-code parser, the same
planner and the same step code. It gives the same replies to the host, so plotstudio drives it
in the same way.

## Architecture

```
 USB serial (115200) ── mini controller ──┬─ planner (look-ahead, trapezoids, 8 blocks)
                          │               └─ segment prep (2 ms) ─ queue (16) ─ step interrupt (10 kHz)
 LCD + knob ──────────────┤                                                      │
 EEPROM ── settings ──────┘                                                      └─ STEP/DIR X, Y1, Y2, servo
```

| Package | Job |
|---|---|
| `firmware/config` | All machine numbers: steps/mm, travel, speeds, homing, servo, switches. `rate_avr.go` has the values for the ATmega2560. |
| `firmware/gcode` | Parses a line into words. No allocations. Arcs (G2/G3) as short lines. |
| `firmware/planner` | The look-ahead planner and the segment preparation. |
| `firmware/stepgen` | The step executor. The step interrupt runs it 10 000 times per second. |
| `firmware/mini` | The small controller: the serial input, the G-code commands, homing, the pen change, the knob menu, and the settings. |
| `firmware/board/mega` | The mainboard code: pins, the step timer, the servo PWM, the LCD, the knob, the EEPROM. It holds the heater MOSFET (`HEAT`) off. |
| `firmware/cmd/mega` | The firmware program. |

The main loop (`Controller.Poll`) runs without a pause. Each pass reads the serial port, runs the
next line, fills the segment queue, reads the knob, and writes one LCD line. The step interrupt
takes segments from the queue. It uses integer math only and does not allocate memory.

| Value | ATmega2560 |
|---|---|
| Step timer | 10 kHz. One step per axis per tick at most. |
| Top speed | 120 mm/s. The planner limits all moves to this speed. |
| Planner | 8 blocks |
| Step queue | 16 segments of 2 ms (32 ms of motion) |
| Flash | 92 KB of 248 KB |
| RAM (static) | 4.2 KB of 8 KB |

## Build and flash

> **Caution:** Make a copy of the stock firmware first if you want it back exactly. Run
> `avrdude -c wiring -p atmega2560 -P /dev/ttyUSB0 -b 115200 -U flash:r:cr10v3-stock.hex:i`.

Install Go 1.26 and TinyGo 0.44. Then:

1. Connect the USB port of the control box to your computer.
2. Flash the firmware:

   ```sh
   tinygo flash -target=arduino-mega2560 -port /dev/ttyUSB0 ./firmware/cmd/mega
   ```

3. To build a HEX file only, run
   `tinygo build -target=arduino-mega2560 -o build/plotter-mega.hex ./firmware/cmd/mega`.

The Creality bootloader stays on the board. `tinygo flash` writes the program over USB with
avrdude. You can put Marlin back with the same USB cable.

## First boot

1. Open a terminal at 115200 baud, for example `screen /dev/ttyUSB0 115200`.
2. The firmware sends `start` and `PenPlotter 0.1.0 (TinyGo, ATmega2560)`.
3. Send `M115`. The reply names the ATmega2560 build.
4. Send `M119`. Push each switch by hand and send `M119` again. Each switch must change.
5. Check the motor directions before the first homing (`20-electronics-and-wiring`).
6. Send `G28`. X homes, then both Y sides. Each Y side stops
   at its own switch. This squares the gantry.
7. Tune the pen angles with the knob menu, or with `M281 U<up> D<down>`.
8. Send `M500` to save.

## The LCD and the knob

The LCD shows four lines of 16 characters.

| Line | Content |
|---|---|
| 1 | The state (`Idle`, `Run 45%`, `Homing`, `Paused`, `Pen T2`, `ALARM`) and the pen (`Pen up` or `Pen dn`) |
| 2 | The X and Y position in mm |
| 3 | A message: `Ready`, `Homing`, `Paused`, `Saved`, `Home failed`, `STOP` and the cause, or `Press the knob` at a pen change |
| 4 | The menu item, with `>` in front. The pen and speed items show the value. |

- Turn the knob to choose a menu item. Press it to run the item.
- Press and hold the knob for 0.8 s to stop the machine. The long press works while the machine
  moves, homes, or waits for a pen. When the machine is idle, the long press does nothing.
- Send `M999` over USB to clear the stop. Then send `G28`. The knob cannot clear the stop.

| Menu item | Job |
|---|---|
| Home | Runs `G28`. Only when the machine is idle. |
| Pen up/down | Lifts or lowers the pen. Only when the machine is idle. |
| Pause/resume | Stops the next lines. The moves in the buffer finish first. Press again to continue. |
| Motors off | Turns off the drivers. Only when the machine is idle. The machine is then not homed. |
| Pen up +1, Pen up -1 | Changes the pen-up angle by 1°. The servo moves at once. |
| Pen down +1, Pen down -1 | Changes the pen-down angle by 1°. The servo moves at once. |
| Speed +10%, Speed -10% | Changes the feed override, from 10 % to 200 %. |
| Save settings | Writes the settings to the EEPROM at once (also `M500`). |

The firmware also saves the pen angles and the speed 3 s after the last change, when the machine
is idle.

## Pen changes

The stock build has no pen table in the firmware. Plotstudio keeps it. You change the pens by
hand. Plotstudio puts `T<n>` and `M6` before the lines of each pen.

1. `T<n>` selects pen n (0 to 15).
2. `M6` lifts the pen and waits. The carriage stays where it is.
3. The beeper sounds once. LCD line 1 shows `Pen T2`. Line 3 shows `Press the knob`.
4. Loosen the clamp screw of the pen slider. Take out the old pen.
5. Put the new pen in the V bore. Set its tip height and tighten the clamp screw (`40-calibration-and-first-plots`).
6. Press the knob. A host can also send `M108`. The job continues.

## G-code reference

The firmware sends `ok` when it has queued a line. A sender sends the next line after each
`ok`. Text after `;` is a comment. The G-code part of a line can have up to 96 characters.

| Code | Action |
|---|---|
| `G0 X Y` | Travel move at the rapid speed (limited to 120 mm/s). |
| `G1 X Y F` | Draw move at F (mm/min). |
| `G2`, `G3` | Clockwise and counter-clockwise arcs with I/J or R. |
| `G4 P<ms>`, `G4 S<s>` | Wait. |
| `G20`, `G21` | Inches, millimetres. |
| `G28`, `G28 X`, `G28 Y` | Home. Y homes both sides and squares the gantry. |
| `G90`, `G91` | Absolute, relative. |
| `G92 X Y` | Set the current position. |
| `M3`, `M4` / `M5` | Pen down / pen up. |
| `T<n>`, `M6` | Select pen n (0 to 15); wait for a pen change by hand. |
| `M108` | Continue after the pen change prompt. |
| `M17` | Motors on. |
| `M18`, `M84` | Motors off, after the queued moves. The machine is then not homed. |
| `M73 P<percent>` | Progress on the LCD. |
| `M105` | A dummy temperature reply for print hosts. |
| `M112`, Ctrl-X | Emergency stop. Then `M999` and `G28`. |
| `M114` | Position, with the step counts of X, Y1 and Y2. |
| `M115` | Firmware name. |
| `M119` | Switches: `x_min`, `y1_min`, `y2_min`. |
| `M280 P0 S<deg>` | Move the servo. |
| `M281 U<deg> D<deg>` | Set the pen up and down angles. |
| `M400` | Wait for the moves to end. |
| `M500`, `M501`, `M502` | Save the settings to the EEPROM, load them, set the defaults (not saved). |
| `M503` | Report the pen angles and the speed override. |
| `M999` | Clear the alarm. |
| `?` | Status line: `<Idle|MPos:x,y,0.000|>`. The states are `Idle`, `Run`, `Home`, `Hold` and `Alarm`. |

Notes:

- A Z word does not move the pen. Use `M3` and `M5`.
- Printer codes (`M82`, `M83`, `M104`, `M106`, `M107`, `M109`, `M140`, `M190`) get `ok` with no
  action. Other M codes, for example `M117`, get `echo:ignored` and `ok`.
- An unknown G code gets `error:unsupported`.

Safety:

- **Soft limits:** after homing, the firmware keeps all moves inside the travel (245 × 390 mm).
- **Hard limits:** a switch that closes during a move toward it stops all motion and sets the
  alarm (`!! hard limit`). After homing, a switch that closes within 1 mm of home is the home
  position, so a move to 0,0 works.
- **Failed homing:** if a switch does not trigger, the reply is `error:homing failed` and the
  alarm is set. The LCD shows `Home failed`.
- **Alarm:** after an alarm, the firmware answers only `M999`, `M112`, `M108` and the queries
  (`M105`, `M114`, `M115`, `M119`, `M503`, `?`). Other lines get `error:alarm, send M999`.
  Send `M999`, then `G28`.

## Settings

The settings record is in the EEPROM. It holds the pen-up angle, the pen-down angle, the speed
override and the Y2 trim. A new board uses the values of `firmware/config/config.go`.

| Command | Action |
|---|---|
| `M281 U<deg> D<deg>` | Set the pen angles. The firmware saves them 3 s later. |
| `M500` | Save now. |
| `M501` | Load the saved record. |
| `M502` | Set the values of `config.go`. Send `M500` to keep them. |
| `M503` | Report: `M281 U130 D80` and `echo:speed 100%`. |

The Y2 trim comes from `Y2HomeOffsetMM` in `config.go`. No G-code changes it. After you change it
and flash the firmware, send `M502` and `M500`. `M502` also resets the pen angles, so set them
again.

## Simulator

The simulator runs the same controller code with a model of the machine. With no `-board` flag,
it simulates the stock board.

```sh
go run ./sim/cmd/plotsim -gcode samples/test-drawing.gcode
```

Two windows show the LCD with the knob, and the machine in 3D. The pen change prompt shows on the
simulated LCD, and a press of the simulated knob answers it.

| Flag | Default | Content |
|---|---|---|
| `-board` | `mega` | `mega`: the stock board. `pico`: the Pico W firmware. This build does not use it. |
| `-addr` | `127.0.0.1:8765` | The windows and the simulated camera |
| `-tcp` | `127.0.0.1:2323` | G-code over TCP. With `-board mega`, it stands in for the USB serial port. |
| `-settings` | a file for each board in the user config folder | The settings file (`M500`). `-settings -` keeps them in RAM only. |
| `-speed` | 1 | Simulation speed factor |
| `-gcode` | none | A file to plot at the start |

The simulator also prints a serial device, for example `/dev/pts/3`. Plotstudio can use it, or
`tcp://127.0.0.1:2323` (`30-software`).

## Limits of this build

- No Wi-Fi, no HTTP API, no Printdeck. Connect a computer or a Raspberry Pi with USB.
- No pen table with names and colours. Plotstudio keeps the pen table on the computer.
- No graphic menus and no jog menu. Use G-code for jog moves.
- 120 mm/s top speed. A pen plotter seldom goes faster than 60 mm/s with ink on paper.
- 8 planner blocks and 16 step segments (32 ms of motion). Short lines at high speed can slow
  down at the corners.
- Pen changes are by hand, at each `M6`.
- The step timing and the LCD timing are not tested on a real board. If the motors stutter,
  lower `TickHz` in `firmware/config/rate_avr.go` to 8000 and lower `MaxFeed` to 100.

The repository also has a full controller for a Pico W board (`firmware/cmd/pico`), with Wi-Fi
and the network API. This build does not use it. `firmware/README.md` describes it.
