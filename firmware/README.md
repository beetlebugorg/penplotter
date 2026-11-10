# Firmware

Firmware for the CR-10 V3 pen plotter, written in Go and built with TinyGo. The main build runs on
the stock CR-10 V3 mainboard (Creality v2.5.2, ATmega2560). The repository also has firmware for
a Raspberry Pi Pico W, or for a Pico H with USB only. This build does not use it.

The frame stands on the table, and the paper lies on the table. The X beam rides on two Y carriages.
Each Y side has its own motor and endstop (Y1 left, Y2 right). The travel is 245 x 395 mm.

`docs/guide/25-firmware.md` is the chapter for the stock board: the LCD and the knob, the G-code,
and the settings. This file also describes the Pico W firmware. `REVIEW.md` is the review log.

## Build and flash: stock CR-10 V3 mainboard (ATmega2560)

```sh
tinygo flash -target=arduino-mega2560 -port /dev/ttyUSB0 ./firmware/cmd/mega
tinygo build -target=arduino-mega2560 -o build/plotter-mega.hex ./firmware/cmd/mega
```

The Creality v2.5.2 board keeps its Arduino bootloader, so `tinygo flash` writes the program over
USB with avrdude. The serial port runs at 115200 baud. The board has 8 KB of RAM, so it runs the
small controller (`mini/`), not `controller/`. The small controller has the same G-code core and
the same replies to the host. It has no graphic menu (the LCD shows 4 text lines and an 11-item
knob menu), no Wi-Fi, and no pen names. The step rate is 10 kHz
(`config/rate_avr.go`), so the top speed is 120 mm/s. `docs/wiring.md` has the pin map.

## Build and flash: Pico W firmware

This build does not use the Pico W firmware.

```sh
tinygo build -target=pico-w -o build/plotter-w.uf2 ./firmware/cmd/pico   # Pico W, USB and Wi-Fi
tinygo build -target=pico   -o build/plotter.uf2   ./firmware/cmd/pico   # Pico H, USB only
```

1. Hold the BOOTSEL button of the Pico and connect the USB cable.
2. Copy the `.uf2` file to the RPI-RP2 drive.

You can also flash with `tinygo flash -target=pico ./firmware/cmd/pico`. After the first flash, TinyGo resets the Pico over USB.

| Build | Flash | RAM (static) |
|---|---|---|
| ATmega2560 (`plotter-mega.hex`) | 92 KB of 248 KB | 4.2 KB of 8 KB |
| Pico H (`plotter.uf2`) | 75 KB | - |
| Pico W (`plotter-w.uf2`) | 551 KB | - |

## Test

```sh
go test ./firmware/... ./sim/...
go run ./sim/cmd/plotsim -gcode samples/test-drawing.gcode -speed 10              # stock board
go run ./sim/cmd/plotsim -board pico -gcode samples/test-drawing.gcode -speed 10  # Pico W
```

The simulator runs the same controller, planner and step executor code as the boards. With no
`-board` flag, it runs the small controller of the stock board.

## Packages

| Package | Content |
|---|---|
| `config` | All machine numbers: steps/mm, travel, speeds, homing, servo angles, endstop polarity. `rate_avr.go` and `rate.go` hold the step rate and buffer sizes for each processor. |
| `gcode` | The line parser and the G2/G3 arc splitter. |
| `planner` | The block buffer with look-ahead (junction deviation, trapezoid profiles), and `Prep`, which cuts blocks into 2 ms segments. |
| `stepgen` | The segment queue and the executor. The step timer calls `Executor.Tick` at 10 kHz (ATmega2560) or 40 kHz (Pico). The executor has three step channels: X, Y1 and Y2. |
| `mini` | The small controller for the stock board: serial input, G-code commands, homing, the pen change prompt, the 4-line LCD and the knob menu, the EEPROM settings. |
| `board/mega` | The stock mainboard: pins, the step timer interrupt (10 kHz), the servo PWM, the ST7920 LCD, the encoder and the EEPROM. |
| `cmd/mega` | The firmware program for the stock board. |
| `ui` | Pico W firmware: the 128x64 framebuffer, the font, the status screen and the menus. |
| `controller` | Pico W firmware: the main loop: serial input, G-code commands, homing, the UI input, and the LCD updates. |
| `board/pico` | Pico W firmware: the Pico hardware: pins, the step timer interrupt, the ST7920 LCD, the encoder and the servo. |
| `cmd/pico` | The firmware program for the Pico and the Pico W. |

The portable packages do not import `machine`. A new board needs a new `board/...` package that implements `controller.HAL` and calls `Executor.Tick` from a timer.
A touch panel needs a new `ui.Display` backend. `docs/wiring.md` lists the free pins for it (SPI1).

## Motion

- The main loop parses one line, plans it, and fills the segment queue. The Pico has 64 segments (128 ms). The ATmega2560 has 16 segments (32 ms).
- The step interrupt runs one segment at a time. It sends at most one step per axis per tick. The Pico ticks at 40 kHz (planner limit 250 mm/s). The ATmega2560 ticks at 10 kHz (planner limit 120 mm/s).
- Pen and dwell blocks stop the motion before them. The servo moves, then the firmware waits `PenSettleMs`.
- The planner knows two axes, X and Y. In each Y move, Y2 steps exactly with Y1.
- Homing moves each axis to its switch fast, backs off 3 mm, and moves to the switch slowly.
- Y homes both sides at the same time. Each side stops at its own switch, so homing squares the beam. `Y2HomeOffsetMM` adds a trim move of Y2 after homing.

## G-code

This table is for the full controller of the Pico W firmware. The small controller of the stock
board has the same core codes. It has no Z words for the pen, no `M117`, no Wi-Fi codes and no park
move at `M6`. Its lines can have 96 characters. `docs/guide/25-firmware.md` has its table.

The firmware sends `ok` when it has queued a line. A sender can send the next line after each `ok`.

| Code | Action |
|---|---|
| `G0 X Y Z` | Travel move at `RapidFeed`. A Z word moves the pen: Z > 0 up, Z ≤ 0 down. |
| `G1 X Y Z F` | Draw move at the F speed (mm/min). |
| `G2`, `G3` | Clockwise and counter-clockwise arcs with I/J or R. |
| `G4 P<ms>` or `G4 S<s>` | Wait. |
| `G20`, `G21` | Inches, millimetres. |
| `G28` | Home X, then Y (both Y sides). `G28 X` or `G28 Y` homes one axis. |
| `G90`, `G91` | Absolute, relative positions. |
| `G92 X Y` | Set the current position. |
| `M3`, `M4` | Pen down. |
| `M5` | Pen up. |
| `T<n>` | Select pen n (0 to 15) for the next `M6`. |
| `M6` or `M6 T<n>` | Change the pen: lift it, park, show "Load pen Tn" on the LCD, wait for a knob click or `M108`. |
| `M108` | Continue after a pen change prompt. Any port can send it. |
| `M17` | Motors on. |
| `M18`, `M84` | Motors off, after the queued motion. The machine is then not homed. |
| `M73 P<percent>` | Show the progress on the LCD. |
| `M105` | Dummy temperature reply for print hosts. |
| `M112` | Emergency stop. Send `M999` to continue. Home again after it. |
| `M114` | Report the position, with the step counts of X, Y1 and Y2. |
| `M115` | Report the firmware name. |
| `M117 <text>` | Show a message on the LCD. |
| `M119` | Report the endstops: `x_min`, `y1_min`, `y2_min`. |
| `M280 P0 S<deg>` | Move the servo to an angle. |
| `M281 U<deg> D<deg>` | Set the pen up and pen down angles. |
| `M400` | Wait for the queued motion to finish. |
| `M500`, `M501`, `M502` | Save the settings to flash, load them, set the defaults (not saved). |
| `M503` | Report the settings as G-code lines. |
| `M550 P"name"` | Set the host name (Pico W: `name.local`). |
| `M552` | Report Wi-Fi. `S0`/`S1` off/on, `P192.168.1.50/24` fixed address (`P0.0.0.0` = DHCP), `G<ip>` gateway. |
| `M587 S"network" P"password"` | Set the Wi-Fi network and join it. `M588` removes it. |
| `M999` | Clear the alarm state. |
| `?` | Status report, without a newline: `<Idle|MPos:x,y,0.000|>`. |
| Ctrl-X | Emergency stop. |

Other temperature and fan codes get `ok` with no action. Unknown codes get `echo:ignored` and `ok`.
Text after `;` is a comment and has no length limit. The G-code part of a line can have 128 bytes.

### Ports and ownership

USB, each TCP client (Pico W port 23) and each network API job is a port. One port at a time
owns the machine. Other ports can send queries (`M105`, `M114`, `M115`, `M119`, `M503`, `?`)
and the safety lines `M112` and `M108`. Their other lines get `error:busy, <port> has the
machine`. The owner keeps the machine until it is idle and quiet for 2 s.

## LCD and knob: stock board

The LCD shows 4 text lines: the state and the pen, the X and Y position, a message, and the menu.
Turn the knob to choose an item. Press it to run the item. Hold it for 0.8 s to stop a moving or
waiting machine; send `M999` to clear the stop.

The 11 items: Home, Pen up/down, Pause/resume, Motors off, Pen up +1, Pen up -1, Pen down +1,
Pen down -1, Speed +10%, Speed -10%, Save settings.

At `M6` the pen lifts and the carriage stays in place. The LCD shows `Pen Tn` and `Press the knob`.
Press the knob, or send `M108`.

## LCD menu: Pico W firmware

Click the knob to open the menu. Turn it to select. Click to run an item or to edit a value. Click again to stop the edit. Hold the knob for 0.8 s to go back to the status screen.

- Home XY
- Move axis: step size (0.1, 1, 10, 50 mm), Move X, Move Y, Home XY
- Pen up, Pen down
- Pen setup: up angle, down angle, test up, test down
- Speed: override from 10 % to 300 %
- Pens: the pen in the holder, the next pen, change pen now
- Motors off
- Wi-Fi: state, network, host name, type the network name and the password with the knob, connect, on, off
- Endstops: the live state of X, Y1, Y2, and the Y2-Y1 difference
- Save settings
- About

During a pen change the status screen shows "PEN CHANGE" and the pen to load. Click the knob
when the pen is in the clamp.

The text editor (Wi-Fi): turn the knob to choose a character, click to add it. `DEL` removes
the last character, `OK` ends the text. Hold the knob to cancel.
