# Simulator pages

The two pages of the plotter simulator. The Go backend (`sim/cmd/plotsim`) serves them and runs the firmware.

- `lcd.html`: the LCD and the knob of the control pod, a reset button, and a serial console.
- `machine.html`: the plotter in 3D on a table. It shows the frame, the motors, the belts, the cables, the pen lift, the ink on the paper, and the control pod with the live LCD.

Open each page in its own window. Both pages connect to the WebSocket `/ws` on the same server.

## Controls

LCD page:

- Drag the knob or turn the mouse wheel on it. One step is one detent (20 detents in one turn).
- Click the knob to push it. Hold the mouse button to hold the knob down.
- Keys: Left and Right turn the knob. Enter and Space push it.
- Open "Serial console" to see the lines and to send a G-code line.

Machine page:

- Left drag turns the view. Right drag pans. The wheel zooms.
- T makes the tool head see-through. F shows the paper. H goes back to the first view.
- "Open G-code…" sends a file to the plotter. You can also drop a file on the window.
- The speed buttons set the simulation speed (1× to 50×).
- "Clear" removes the ink. A4 and Letter change the paper.
- "Controls" (or J) shows the jog pad and the servo slider.
  - The jog pad moves X and Y by the step (0.1, 1, 10 or 50 mm). The arrow keys also jog. "Go" moves to the X and Y values. The pad sends absolute `G90 G0` moves, clamped to the firmware travel. It works only after G28, and not during a job.
  - The servo slider sends `M280 P0 S<deg>`. The marks show the pen-down (D) and pen-up (U) angles of `M281`, and the angle where the horn tip meets the tab. The red zone is the slip zone: there the horn tip goes past the end of the tab.
  - `M280` does not change the pen state of the firmware. After a slider move, `M3` or `M5` does nothing if the firmware thinks the pen is already there.

## Protocol

Each WebSocket message is one JSON object.

Server to page:

| Message | Content |
|---|---|
| `hello` | `machine`: `layout` (`table`), `travel`, `steps_per_mm`, `pen_up_deg`, `pen_down_deg`, `lcd` |
| `state` | `x`, `y` (mm from the home corner), `y2` (the right side), `pen` (0 = up, 1 = down), `en`, `homed`, `es` {`x`, `y`, `y2`}, `busy`, `q`, `line`, `done`, `total`, `speed`, `servo` (the servo angle in degrees), and an optional `name` (the job file) |
| `ink` | `s`: a list of `[x0, y0, x1, y1]` segments in mm |
| `lcd` | `bits`: base64 of 1024 bytes. 128 x 64 pixels, 16 bytes for each row, the MSB is the left pixel. |
| `beep` | `ms`: the length of the tone |
| `serial` | `dir`: `rx` (the board receives the line) or `tx` (the board sends the line), and `text` |

Page to server: `enc` {`d`: +1 or -1}, `btn` {`down`}, `gcode` {`name`, `text`}, `line` {`text`}, `speed` {`x`}, `paper` {`clear`}, `reset`.

The machine page clears the ink when it gets `hello`. Send all ink of the current sheet after `hello`, so that a new window shows the full drawing.

## Machine data and printed parts

The machine page shows a table plotter. The paper lies on a cutting mat on the table and does not move. The gantry rides on V-wheels in the two long frame rails. Two Y motors (Y1 left, Y2 right) drive the gantry.

The page builds the machine from `/stl/frame.json`. Until that file loads, it uses the measured values in `DEFAULT_CFG` in `machine.js`.

- All values are frame coordinates in mm. The origin is the front-left outer corner of the frame, on the table. X goes to the right, Y goes to the back, Z goes up.
- `parts` lists STL files in frame coordinates (Z up), at machine home, with the pen down. `moves` is `static`, `gantry` (moves with Y), `carriage` (moves with X and Y), `pen` (like `carriage`, and it lifts by the linkage lift), or `horn` (like `carriage`, and it turns about the servo shaft).
- `pen_lift` is the servo linkage. `pivot` is the servo shaft (the axis is along y). The horn angle above level is the servo angle less `servo_level_deg`. `horn.stl` is at `stl_deg`. `lift_by_servo_deg` gives the slider lift for each servo degree: the horn tip lifts the tab, and at lift 0 the pen rests on the paper. With no `pen_lift`, the pen lifts by (1 - pen) x `pen_lift_mm`.
- A part hides the simple shapes of the same item. The item comes from words in the file name: `y_carriage`, `motor_bracket` or `y_motor`, `idler`, `beam`, `x_rail`, `y_rail`, `x_block`, `y_block`, `x_motor`, `x_idler`, `rod`, `bearing`, `x_plate` or `x_carriage`, `pen_lift`, `slider` or `screw`, `servo` or `horn`, `pen.stl`, `foot`, `cable_post`.
- The plotter uses stock V-wheels on both axes. `beam` is the 2020 X beam. `x_motor`, `x_idler` and `x_belt` place the X drive: a vertical belt loop in front of the stock X carriage plate. `x_carriage` gives the plate (`plate_front_y`, `box`). `x_wheels` gives the 3 wheel centres on the plate. `y_wheels` gives the 3 wheel centres of each Y carriage, in the side slots of the frame rails. The page also reads two older layouts: `x_rail` and `y_rails` (MGN12 rails), or `rods` (two steel rods).
- The guide keys (`beam`, `x_rail`, `y_rails`, `rods`, `x_motor`, `x_idler`, `x_belt`, `x_carriage`, `x_wheels`, `y_wheels`) come as one set. If `frame.json` has one of them, the page uses none of the defaults for the others.
- `paper_z` is the height of the paper top. The mat and the table top go under it.
- `state.y2` turns the gantry when it is different from `state.y`. `state.es.y` lights the Y1 endstop. `state.es.y2` lights the Y2 endstop.

## Control pod

The pod is a printed desk console on the table, left of the front-left frame corner. `POD` in `machine.js` sets its position and direction. The page draws it as a simple shape (the pod STL files are gone with the Pico W upgrade, 2026-11-10). All cables leave through the notch in the back wall. A 24 V power brick connects to the barrel jack on the back wall.

## Coordinates

`f2s` in `machine.js` converts frame coordinates to scene coordinates. `machineToFrame` converts the machine position to the frame position of the pen tip. Change `machineToFrame` if the home corner changes.

## Work on the pages without the backend

`dev/mock_server.mjs` is a fake machine. It does not run the firmware.

```sh
cd sim/web/dev
npm install
DEMO=1 node mock_server.mjs 8090
```

Open http://localhost:8090/lcd.html and http://localhost:8090/machine.html. `DEMO=1` starts a demo plot. The menu on the LCD also has "PLOT DEMO".

`dev/shots.mjs` opens both pages in headless Chromium, prints the console errors, and writes PNG files:

```sh
node shots.mjs http://localhost:8090 shots
```

It uses `/usr/bin/chromium`. Set `CHROMIUM` to use a different browser.
