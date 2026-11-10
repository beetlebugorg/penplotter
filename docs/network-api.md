# Network API

The network API needs the Pico W firmware (`firmware/cmd/pico`). This build does not use it. The
stock controller build has no network: it uses USB serial only. The Pico W firmware and the
simulator (`-board pico`) serve the same API. The code is `firmware/netapi`.

| Where | Pico W | Simulator (`-board pico`) |
|---|---|---|
| HTTP API | `http://penplotter.local/api/...` (port 80) | `http://127.0.0.1:8765/api/...` (the `-addr` of plotsim) |
| G-code over TCP | `penplotter.local` port 23 | `127.0.0.1:2323` (the `-tcp` flag) |
| Name | mDNS `<hostname>.local`; `M550 P"name"` sets the host name | — |

The Pico W gets its address from DHCP. `M552 P192.168.1.50/24 G192.168.1.1` sets a fixed
address. `M552` with no words reports the address. The LCD shows it on the status screen.

All answers have `Access-Control-Allow-Origin: *`, so a web page on another host can call the
API. The API has no password. Use it on a trusted network only.

## Ports and ownership

USB, each TCP client, each `/api/cmd` call and each `/api/job` is a port of the controller.
One port at a time owns the machine:

- A port takes the machine when it sends a motion or state line while no port owns it.
- The owner keeps the machine until the machine is idle and the owner sends nothing for 2 s.
- Other ports can send the queries `M105`, `M114`, `M115`, `M119`, `M503` and `?`, and the
  safety lines `M112` (emergency stop) and `M108` (continue after a pen change prompt).
- Other lines from them get `error:busy, <owner> has the machine`.

## GET /api/status

```json
{"state":"idle","x":12.500,"y":40.000,"pen":"up","tool":0,"homed":true,"alarm":false,
 "msg":"","owner":"","progress":-1,"job":{"name":"","line":0,"total":0}}
```

| Field | Meaning |
|---|---|
| `state` | `idle`, `busy`, `homing`, `pen_change` or `alarm` |
| `x`, `y` | Work position in mm (after `G92`), at the step position of the motors |
| `pen` | `up` or `down` (the last pen command) |
| `tool` | The pen in the holder, 0 to 15 |
| `homed` | true after `G28`; false after motors off or an alarm |
| `alarm` | true after `M112`, Ctrl-X, a hard limit or a failed homing. Send `M999`, then `G28`. |
| `msg` | The message line of the LCD (errors, `M117` text) |
| `owner` | The port that owns the machine: `usb`, `tcp <address>`, `api`, or a job name |
| `progress` | Percent from the last `M73 P`, or -1 |
| `job` | `name`: the owner (the job name for `/api/job`); `line`: the lines it sent; `total`: from `X-Job-Lines`, or 0 |

The state is a copy that the controller makes every 20 ms.

## POST /api/cmd

The body is one G-code line. The answer is the reply text of the firmware, up to and with the
final `ok` or `error:...` line. Status 200 for `ok`, 409 for an error.

```sh
curl -d 'M114' http://penplotter.local/api/cmd
X:10.000 Y:20.000 Z:0.000 Count X:800 Y:1600 Y2:1600
ok
```

A line that waits (`M400`, `G28`, `M6`) answers when it is done, after 10 minutes at most.

## POST /api/job

The body is a G-code file. The firmware takes the machine for the job and streams the lines
with `ok` flow control. The answer comes when the firmware has queued all lines. The last
moves can still run: poll `/api/status` until `state` is `idle`.

| Input | Meaning |
|---|---|
| `?name=drawing.gcode` or header `X-Job-Name` | The job name for the status |
| Header `X-Job-Lines: 1234` | The number of lines, for `job.total` |
| Header `Content-Length` | Required. The Pico W does not read chunked bodies (status 411). |

```sh
curl --data-binary @drawing.gcode -H 'X-Job-Lines: 1795' 'http://penplotter.local/api/job?name=drawing.gcode'
{"name":"drawing.gcode","lines":1795,"answered":1795,"errors":0,"first_error":""}
```

- Status 409 with `{"error":"usb has the machine"}` when another port owns the machine, or
  when the machine is in alarm.
- An error line in the file does not stop the job. The answer counts the errors and gives the
  first one.
- An emergency stop ends the job with status 409.
- To stop a job, send `M112` to `/api/cmd`. This stops all motion and sets the alarm.

## GET /api/pens, PUT /api/pens

The pen table has 16 entries, T0 to T15. `M6` asks for the pen by its name.

```json
[{"t":0,"name":"Black","color":"#000000"},{"t":1,"name":"Blue","color":"#1F4FBF"}, ...]
```

`PUT` takes an array of objects (or one object). `t` is required. `name` (15 characters at
most, ASCII) and `color` (`"#RRGGBB"` or a number) are optional. The answer is the full table.
The firmware saves the table 3 s later, when the machine is idle.

```sh
curl -X PUT -d '[{"t":2,"name":"Red 0.5","color":"#D12A2A"}]' http://penplotter.local/api/pens
```

## G-code over TCP

Connect to port 23 (simulator: 2323) and send G-code lines. Each line gets `ok` or
`error:...`, as on USB. `?` and Ctrl-X work. One TCP client at a time on the Pico W.

```sh
nc penplotter.local 23
```

## Errors

Errors of the API itself are JSON: `{"error":"text"}` with status 400 (bad input), 404, 405,
409 (busy), 411 (no length) or 503 (the controller does not answer).
