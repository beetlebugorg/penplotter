# Simulator WebSocket protocol

The simulator (`go run ./sim/cmd/plotsim`) serves the windows over HTTP and a WebSocket at `/ws`.
Each WebSocket message is one JSON object. The key `t` gives the message type. It is always the first key.

## Server to window

### hello

The server sends `hello` first, after each connect.

```json
{"t":"hello","machine":{"travel":[216,380],"bed":[216,380],"steps_per_mm":[80,80],"pen_up_deg":130,"pen_down_deg":80,"lcd":[128,64],"layout":"table"}}
```

- `travel`: X and Y travel in mm, from the home switches.
- `bed`: size of the drawing area on the table in mm.
- `layout`: `"table"`. The frame stands on the table and the paper lies on the table. The X beam rides on two Y carriages. Each Y side has its own motor and endstop (Y1 left, Y2 right).
- `pen_up_deg`, `pen_down_deg`: servo angles at connect time.
- `lcd`: LCD size in pixels.

After `hello`, the server sends the full LCD, all ink so far, and a state message.

### state

The server sends `state` about 60 times per second.

```json
{"t":"state","x":12.5,"y":40.25,"y2":40.25,"pen":1,"en":true,"homed":true,"es":{"x":false,"y":false,"y2":false},"busy":true,"q":12,"line":"G1 X12.500 Y40.250","name":"test-drawing.gcode","done":120,"total":1795,"speed":1}
```

| Key | Meaning |
|---|---|
| `x`, `y` | Carriage position in mm. `y` is the Y1 (left) side. The origin is the home corner: X min (left), Y min (front). |
| `y2` | The Y2 (right) side in mm. It differs from `y` before homing, so the beam is not square. Homing squares it. |
| `pen` | Servo position: 0 = up, 1 = down. It changes during the servo move. With no linkage data, ink starts at 0.9. |
| `en` | The motors are on. |
| `homed` | The firmware is homed. |
| `es` | The endstop switches are pressed: `x`, `y` (Y1) and `y2`. |
| `busy` | The firmware has motion in its queues. |
| `q` | Blocks in the planner. |
| `line` | The last G-code line sent to the firmware. |
| `name` | File name of the current job. The key is not present before the first job. |
| `done`, `total` | Lines sent and total lines of the current job. Both are 0 before the first job. |
| `speed` | Simulation speed factor. |
| `servo` | The horn angle in servo degrees. `pen` stops at 0 and 1. The horn can stop on the tab before the commanded angle (`over`). |
| `pen_up_deg`, `pen_down_deg` | The pen-up and pen-down angles now (`M281 U` and `D`). |
| `lift` | The slider lift in mm above the paper contact. 0: the pen is on the paper, and the pen inks. Only with the linkage data (frame.json `pen_lift`). |
| `over` | The horn tip went past the end of the tab, and the tip is now over the tab. The horn stops on the top of the tab and the pen stays on the paper. Send `freehorn` to clear it. The key is not present when it is false. |

The carriage can be at a position below 0 (to -2 mm) before homing.
At power on the simulator puts Y2 0.6 mm behind Y1.

### ink

New pen lines since the last `ink` message. Units are machine mm. The origin is the home position of the pen tip.
The pen Y position is the mean of Y1 and Y2.

```json
{"t":"ink","s":[[20,20,20.05,20],[20.05,20,20.1,20]]}
```

Each item is `[x0, y0, x1, y1]`. A connect gets all ink in chunks of up to 5000 items.

### paper

The paper was cleared. Remove all ink. New ink follows in `ink` messages.

```json
{"t":"paper","clear":true}
```

### lcd

The LCD pixels, on each change.

```json
{"t":"lcd","bits":"<base64>"}
```

`bits` holds 1024 bytes: 64 rows of 16 bytes, row-major. The most significant bit of each byte is the leftmost pixel. A set bit is a lit pixel.

### beep

```json
{"t":"beep","ms":60}
```

### serial

A line on the serial port. `rx`: the board receives the line. `tx`: the board sends the line.

```json
{"t":"serial","dir":"tx","text":"FIRMWARE_NAME:PenPlotter 0.1.0 (TinyGo) ..."}
```

The server does not send the lines of a job and their `ok` replies. The `state` message shows the job progress.
Error lines of a job are sent. Lines from the pseudo-terminal and the console are sent.

## Window to server

| Message | Action |
|---|---|
| `{"t":"enc","d":1}` | Turn the knob one detent. 1 is clockwise, -1 is counter-clockwise. |
| `{"t":"btn","down":true}` | Press the knob button. Send `{"t":"btn","down":false}` to release it. A press of 0.8 s or more is a long press. |
| `{"t":"gcode","name":"file.gcode","text":"..."}` | Start a job. The server streams the lines with flow control (one line per `ok`). It adds `M73` progress lines. One job runs at a time. |
| `{"t":"line","text":"G28"}` | Send one console line. The reply comes as `serial` messages. The server sends the lines in the order they come. |
| `{"t":"speed","x":10}` | Set the simulation speed factor (1 to 100). |
| `{"t":"paper","clear":true}` | Clear the paper. |
| `{"t":"reset"}` | Restart the firmware. The job stops. The carriage, the servo and the paper stay. |
| `{"t":"freehorn"}` | Lift the pen slider by hand when the horn rests on the top of the tab (`over`). The horn goes back under the tab. |

## Other HTTP paths

- `/lcd.html`, `/machine.html`: the two windows.
- `/stl/<path>`: the files of `hardware/stl/`, if that directory exists. Subdirectories work, for example `/stl/sim_parts.json` and `/stl/sim/pen_lift.stl`. A path cannot leave the directory.

## Network API and TCP port

The simulator serves the network API of the Pico W under `/api/` on its HTTP address, with
the same code (`firmware/netapi`). `docs/network-api.md` describes it.

`-tcp 127.0.0.1:2323` (the default) accepts raw G-code clients, as port 23 of the Pico W.
`-tcp ""` turns it off. Each client is a controller port with its own `ok` flow control.

`-settings <file>` keeps the settings (`M500`) in a file, as the Pico keeps them in flash.
The default is `penplotter-sim/settings.bin` in the user configuration folder. `-settings ""`
keeps them in RAM only.

The state message carries the LCD state in `status`. The pen change prompt shows on the
simulated LCD. A click of the simulated knob answers it.

## Serial device

The simulator also makes a pseudo-terminal, for example `/dev/pts/7`. It prints the path at start.
A G-code sender can open it as a serial port. Use `-link <path>` to make a symbolic link with a fixed name.
