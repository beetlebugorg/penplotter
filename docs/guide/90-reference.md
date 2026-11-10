# Reference

<!-- include: 25-firmware.md#G-code reference -->

## Configuration values

The values are in `firmware/config/config.go`. Change a value, then rebuild and flash the firmware.
The values in the settings record change at run time: `M503` reports them, and `M500` saves them.
On the stock board the record holds the pen angles, the speed override and the Y2 trim.

The ATmega2560 build uses five values of `firmware/config/rate_avr.go` in place of the values
below: `TickHz` 10 000, `SegmentTick` 20, `MaxFeed` 120 mm/s, `PlannerSize` 8, `SegQueue` 16.

| Value | Default | Meaning |
|---|---|---|
| `StepsPerMMX`, `StepsPerMMY` | 80 | Steps per mm (1/16 microsteps, 20T GT2 pulley). Use 100 with a 16T pulley and idler (`hardware/MEASURE.md`, item 59). |
| `TravelX`, `TravelY` | 245, 390 | Travel in mm from the home switches (the model allows 245.9 × 395.1) |
| `InvertDirX`, `InvertDirY`, `InvertDirY2` | false, false, true | Motor directions |
| `Y2HomeOffsetMM` | 0 | Y2 moves this far after homing, to square the beam |
| `EndstopTriggeredHigh` | true | true for normally closed switches |
| `HomeFastFeed`, `HomeSlowFeed` | 30, 4 mm/s | Homing speeds |
| `HomeBackoff` | 3 mm | Back-off before the slow homing pass |
| `MaxFeed`, `RapidFeed`, `DefaultFeed` | 250, 150, 50 mm/s | Speed limit, G0 speed, G1 speed before the first F word |
| `Accel` | 1500 mm/s² | Acceleration of all moves |
| `JunctionDev` | 0.02 mm | Corner tolerance of the look-ahead |
| `PlannerSize` | 32 | Blocks in the look-ahead buffer |
| `TickHz`, `SegmentTick` | 40 000 Hz, 80 | Step timer rate; ticks per 2 ms segment |
| `PenUpDeg`, `PenDownDeg` | 130, 80 | Servo angles (90° is the horn level). Tune them in the menu. |
| `PenSettleMs` | 150 ms | Wait after each pen move |
| `EncoderPulsesPerDetent` | 4 | Encoder pulses for one knob click |

## Plotstudio options

| Option | Meaning |
|---|---|
| `-port` | The plotter: `/dev/ttyUSB0` (the control box), or `tcp://host:port` (a serial line over TCP, for example the simulated stock board) |
| `-camera` | `/dev/video0`, a camera number, an `http://` JPEG address, or `file:<path>` |
| `-list-cameras` | List the V4L2 cameras |
| `-feed` | Draw speed in mm/min (default 3000) |
| `-park`, `-scan-twice`, `-split` | Scan settings: park the gantry, two pictures, the join row |
| `-lens` | Fit the lens distortion (6 or more points) |
| `-addr` | The address of the plotstudio page (default `127.0.0.1:8780`) |
| `-data` | The folder for the calibration and the library |

## Files of the repository

| Path | Content |
|---|---|
| `README.md` | The short introduction and the quick start |
| `docs/guide/` | The chapters of this guide |
| `docs/penplotter-guide.pdf` | This guide as one PDF (`tools/guide`) |
| `docs/bom.md`, `docs/wiring.md`, `docs/network-api.md`, `docs/studio.md`, `docs/printdeck.md` | Reference documents |
| `docs/REVIEW-integration.md` | The cross-track review |
| `hardware/shape.py`, `parts.py`, `model.py` | The printed parts in build123d, the fit check, the exports |
| `hardware/make.sh` | Builds, checks, slices and documents all parts |
| `hardware/stl/`, `hardware/cad/` | The STL files in print orientation, and the STEP files |
| `hardware/stl/frame.json` | The machine geometry for the simulator and plotstudio |
| `hardware/penplotter-build-guide.pdf` | The step-by-step build guide for the hardware |
| `hardware/REVIEW.md`, `hardware/MEASURE.md` | The hardware review, the measurements to take |
| `firmware/config/` | All machine values |
| `firmware/gcode/`, `planner/`, `stepgen/` | The portable firmware core (no `machine` import) |
| `firmware/mini/` | The small controller for the stock board |
| `firmware/board/mega/`, `firmware/cmd/mega/` | The stock board code (pins, step timer, servo, LCD, knob, EEPROM) and its main program |
| `firmware/controller/`, `ui/`, `settings/`, `netapi/` | The full controller for a Pico W board. This build does not use it. |
| `firmware/board/pico/`, `firmware/cmd/pico/` | The Pico and Pico W board code and its main program. This build does not use it. |
| `sim/` | The simulator backend; `sim/web/` the 3D window and the LCD window |
| `studio/` | Plotstudio: `geom`, `svg`, `plan`, `serial`, `netlink`, `camera`, `app`, `web` |
| `integrations/printdeck/` | The Printdeck package and `printdeck.patch`. It needs a Pico W board. |
| `samples/` | `square.gcode`, `test-drawing.gcode`, `blueprint.gcode`, the six-pen test `mandala.gcode` (`samples/mandala`) and their generators |
| `tools/progress/` | The progress site |
| `tools/guide/` | The generator of `docs/penplotter-guide.pdf` |
