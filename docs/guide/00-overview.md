# Overview

![The table plotter at home](../../hardware/build/img/table-light.png)

The pen plotter is the base frame of a dismantled Creality CR-10 V3 on a table. The table is the
bed: the paper lies on the table, and the gantry moves over it.
Stock V-wheels carry both axes: three on each printed Y carriage, and three on the printed X plate.
The motors do not move. Two Y motors stand behind the back bar, and the X motor stands at the left
end of the beam. The X belt runs in the slots of the beam, as on the stock CR-10.
A servo lifts the pen. The stock CR-10 V3 control box stands beside the frame and drives
the plotter. The stock harness stays. The two small Creality boards of the harness stand bare
on nylon standoffs, held by cable ties.

The printed parts copy the stock CR-10 layouts. They keep only the features that the plotter
uses. Each Y carriage is a flat 6 mm plate, in the form of the stock Z carriage plate.

The firmware is written in Go and built with TinyGo. It runs on the ATmega2560 of the stock
mainboard. A simulator runs the same firmware code on a computer. Plotstudio is the computer
program for the plotter: it scans the bed with a camera, places SVG drawings and signatures on
the paper, and plots them in up to 16 pen colours over USB. You change the pens by hand.

## Specifications

| Value | |
|---|---|
| Pen travel | 245 × 390 mm in the firmware (the model allows 245.9 × 395.1 mm) |
| Paper | A4 and Letter fit. Larger sheets fit under the frame, and the plotter draws on the travel area. |
| Home | The front left corner. Homing squares the gantry on two Y switches. |
| Resolution | 80 steps/mm on X, Y1 and Y2 (1/16 microsteps, 20T GT2 pulleys) |
| Speeds | Draw 50 mm/s (plotstudio default), limit 120 mm/s, acceleration 1500 mm/s² |
| Pen lift | 7.0 mm, by a hobby servo |
| Pen force | The weight of the pen slider and the pen |
| Pens | One pen in the V bore of the pen slider: round barrels 8 to 15 mm. `T0` to `T15` in the G-code. You change the pen by hand at each `M6`. |
| Motors | X: a 42-34 (213.4 g). Y1 and Y2: 42-40 (286.7 g). |
| Controller | The stock CR-10 V3 control box: Creality v2.5.2 mainboard, ATmega2560, 16 MHz, 8 KB RAM |
| Drivers | The onboard drivers of the mainboard: X, Y (Y1) and Z (Y2). E is free. |
| Power | The stock 350 W supply in the control box |
| LCD | The stock ST7920 LCD: 4 text lines, an 11-item knob menu |
| Connection | USB serial at 115200 baud |
| Camera | A USB webcam on your 590 mm pole, in an optional printed pole foot, for plotstudio |

## Cost and print time

| Item | Value |
|---|---|
| Purchased parts | about $181 before tax |
| Printed parts | 22 parts (16 print jobs) in 23 h 08 min, 406 g of PLA, $8.12. This includes the camera pole foot. |
| Total cost | about $189 before tax |
| Fit tests | 3 parts, 49 min, 14 g |
| Heat-set inserts | 12, all M3 |

The print values come from CuraEngine slices: PLA, 0.3 mm layers, a LulzBot TAZ Workhorse with the
0.5 mm SE tool head, and PLA at $19.99/kg (`hardware/stats.py`). `05-parts-and-cost` has the details.

## How the pieces connect

```
 Computer                                  Control box (stock)                 Machine
 ────────                                  ───────────────────                 ───────
 plotstudio ──USB serial, 115200──────────► ATmega2560 (TinyGo firmware)
   camera scan, layout, pens                 G-code, planner, steps ──► X driver ──► X motor
   G-code, "ok" for each line                LCD + knob (ST7920)        Y driver ──► Y1 motor (left)
                                             settings in EEPROM         Z driver ──► Y2 motor (right)
                                                                        servo    ──► pen lift
                                                                        endstops ◄── X, Y1, Y2
 USB webcam on the pole ──USB──► plotstudio (V4L2)
 350 W supply ──► mainboard ──► stock harness ──► head board (X beam), base board (back bar)
```

The `HEAT` output of the head board (the heater MOSFET, D10, PB4) is not used. The firmware holds
it off.

## The chapters

- **Parts and cost** (`05-parts-and-cost`): what to buy and what to print.
- **Hardware** (`10-hardware`, `15-assembly`): the frame, the V-wheels, the fixed motors, the
  belts, the printed parts, the breakout boards, the moving cables.
- **Electronics and wiring** (`20-electronics-and-wiring`): the control box, the stock harness,
  the servo, the switches.
- **Firmware** (`25-firmware`): the ATmega2560 build, the LCD and the knob, the G-code, the pen
  change.
- **Software** (`30-software`): plotstudio, the simulator, multi-pen jobs.
- **Calibration and first plots** (`40-calibration-and-first-plots`).
- **Review history, troubleshooting and reference** (`75-review-history`, `80-troubleshooting`,
  `90-reference`).

## The repository

| Folder | Content |
|---|---|
| `hardware/` | The printed parts in build123d, the checks, the slices, the build guide PDF |
| `firmware/` | The TinyGo firmware: portable core packages, the small controller and the board code for the ATmega2560. The folder also has code for a Pico W board. This build does not use it. |
| `sim/` | The simulator: the same firmware code, a 3D window, an LCD window and a camera |
| `studio/` | Plotstudio: camera, calibration, SVG, layout, pens, G-code, serial and network links |
| `integrations/printdeck/` | The Printdeck package and the patch. Printdeck needs a Pico W board, so this build does not use it. |
| `samples/` | Test drawings, a blueprint generator, and the six-pen mandala (`samples/mandala`) |
| `tools/` | The progress site and the guide generator |
| `docs/` | This guide and the reference documents |

## Status

The design is complete and checked in software. It is not built yet. These parts have no test on
real hardware: the step and LCD timing on the ATmega2560, the `BL_T` pin order, the fit of the
printed parts, the sag of the servo loom, and the camera capture.
Values marked ESTIMATE come from data sheets or photos. `hardware/MEASURE.md` lists the
measurements to take before you print.

One question is open. The cable ties of the head board go round the beam, in the path of the X
plate and its wheels. `hardware/REVIEW.md` lists the options. Check this before you tie the head
board on (`15-assembly`).
