# Plotstudio

Plotstudio lays out drawings on the real bed with a camera, and then plots them.

1. Put a sheet on the table, for example a form that needs a signature.
2. Scan the bed. Plotstudio turns the skewed camera picture into a flat top view in machine millimetres.
3. Put an SVG file or a signature on the top view. Drag it, scale it, and turn it.
4. Plot. The pen draws where the drawing is in the top view. A drawing with more colours uses more pens.

Plotstudio is pure Go. It needs no OpenCV and no cgo. It runs on Linux. It drives the stock controller build over USB serial at 115200 baud. It can also drive a plotter with the Pico W firmware over Wi-Fi. This build does not use the Pico W firmware.

## Run it with the simulator

1. Start the simulator. Its camera looks at the simulated table, paper and ink. With no `-board`
   flag, it simulates the stock board.

   ```sh
   go run ./sim/cmd/plotsim -cam-k1 -0.08
   ```

   It takes G-code on `127.0.0.1:2323`, in place of the USB serial port. It also prints the
   serial device, for example `/dev/pts/3`, and the camera URL.

2. Start plotstudio with the TCP port (or the serial device) and the camera URL.

   ```sh
   go run ./studio/cmd/plotstudio -port tcp://127.0.0.1:2323 -camera http://127.0.0.1:8765/camera.jpg
   ```

   To simulate the Pico W firmware, start the simulator with `-board pico`, and give plotstudio
   `-port "tcp://127.0.0.1:2323?http=8765"`. Plotstudio then also reads the HTTP API.

3. Open http://127.0.0.1:8780.

The simulator flags for the camera:

| Flag | Meaning |
|---|---|
| `-cam-size 1296x972` | The size of the live picture. A scan uses 2592 x 1944. |
| `-cam-k1 -0.08` | Barrel distortion of the lens. 0 is a perfect lens. |
| `-paper 113,182,3` | The paper centre in machine mm and its angle in degrees. |
| `-doc form.png` | A picture of the document on the paper. The default is a form with a signature line. |

`/camera.json` gives the data of the simulated camera. `/camera/project?x=..&y=..` gives the picture point of a machine point. The tests use it.

## Run it with the plotter and a webcam

1. List the cameras.

   ```sh
   go run ./studio/cmd/plotstudio -list-cameras
   ```

2. Start plotstudio. Give the plotter as a USB device or as a network address.

   ```sh
   go run ./studio/cmd/plotstudio -port /dev/ttyUSB0 -camera /dev/video0       # stock control box
   go run ./studio/cmd/plotstudio -port penplotter.local -camera /dev/video0   # Pico W firmware, Wi-Fi
   ```

   The control box shows up as `/dev/ttyUSB0`. With no `-port`, plotstudio uses the first
   `/dev/ttyUSB*` device. If there is none, it uses the first `/dev/ttyACM*` device (a Pico).

Plotstudio uses the MJPEG mode of the camera. A live picture uses the largest size up to 1920 x 1080. A scan uses the largest size, for example 4656 x 3496 on the Arducam B0561. During a scan, plotstudio fixes the exposure and the white balance.

## Connect the plotter

The **Plotter** card connects the plotter. Type an address and push **Connect**. Push **Find** to look for plotters.

| Address | Link |
|---|---|
| `/dev/ttyUSB0` | USB: the stock control box. |
| `/dev/ttyACM0` | USB: a Pico W or a Pico H with the Pico W firmware. |
| `tcp://127.0.0.1:2323` | A plain serial line over TCP, with no HTTP API. The chip shows **USB**. Use it for the simulated stock board. |
| `penplotter.local` | Wi-Fi (Pico W firmware). Plotstudio finds the address with mDNS. |
| `192.168.1.50` | Wi-Fi (Pico W firmware), by IP address. |
| `192.168.1.50:2323` | Wi-Fi (Pico W firmware), with another G-code port. |
| `tcp://127.0.0.1:2323?http=8766` | Wi-Fi, with another G-code port and another HTTP port (the simulated Pico W). |

- On Wi-Fi, plotstudio sends the G-code on TCP port 23, one line at a time, and waits for each `ok`. So pause, resume and cancel work as on USB.
- On Wi-Fi, plotstudio also reads `GET /api/status` of the plotter every 2 s, and the pen table at each connect. `docs/network-api.md` has the API of the plotter.
- **Find** sends an mDNS query for `_penplotter._tcp.local` and `penplotter.local`, and lists the USB devices. It takes 2 s.
- A lost link (a USB cable, a Wi-Fi drop) does not stop plotstudio. It tries the same plotter again every 3 s.
- The chip at the top shows the link: **USB** or **Wi-Fi**.

## Put the camera in position

- Put the camera on the top of the camera pole, behind the centre of the back bar. The lens is about 616 mm above the table.
- Point it down and a little forward. The picture must show the whole frame opening (320 x 480 mm).
- Fix the pole well. A camera that moves after the calibration puts the drawings in the wrong position.
- Fix the focus (the Lock button) before you calibrate. A change of focus moves the picture a little. The calibration file keeps the lens position, and plotstudio sets it again at the next start.

## Calibrate

The calibration finds the map from the camera picture to machine millimetres. It also finds the barrel distortion of the lens (k1) when there are 6 or more points.

1. Put a sheet of paper on the bed, over the whole travel.
2. Select the number of points. Use 3 × 3 or 4 × 4 for the best result.
3. Push **1. Draw marks**. The plotter homes and draws a small dot at each point. Then it parks.
4. Push **2. Click marks**. Plotstudio scans the bed and shows the camera picture.
5. Click each dot in the order that the hint gives. Plotstudio moves each click to the centre of the dot. Turn the mouse wheel to zoom. Drag to pan.
6. Push **Solve**. Plotstudio shows the error in mm. An error below 0.3 mm is good.

Each camera has its own calibration file: `~/.config/plotstudio/calibration-<camera>.json`. A change of camera loads the calibration of that camera, or none. A `calibration.json` of an older version stays in use for its camera.

## Scan

The camera stands behind the frame, so the gantry hides a band of the table. A scan therefore takes two pictures:

1. With the gantry at the back. The front of the table is clear.
2. With the gantry at the front. The back of the table is clear.

Plotstudio joins the two pictures at the middle row (`-split 0.5`). Then it parks the gantry at the back again. Use `-scan-twice=false` for one picture, and `-park=false` for no gantry moves.

The park positions stay 5 mm from the home switches (X 5, and Y 5 at the front). At X 0 or Y 0 the carriage presses a switch, and the firmware reads it as a hard limit.

## Lay out and plot

- **SVG file**: add an SVG file, or drop it on the bed view. Plotstudio reads paths, lines, polylines, polygons, rectangles, circles, ellipses, groups with transforms, and the viewBox. It reads the stroke colour of each line (the fill colour when there is no stroke), and the Inkscape layer.
- **Signature**: sign in the pad. The pad is 75 × 25 mm on the paper. **Save** keeps the signature in the library (`~/.config/plotstudio/library/`). **Add to bed** puts it on the bed view.
- Drag an item to move it. Drag a corner to scale it. Drag the round handle to turn it. The arrow keys move it by 0.5 mm (5 mm with Shift).
- The X, Y, W, H and Angle fields give exact values. X and Y are the centre of the item in machine mm.
- An item outside the travel has a red frame. Plotstudio does not plot it.
- With no scan, the bed view is paper white, so the lines show in the colours of their pens.
- **Show path** shows the pen-up moves.
- **Plot** sends the G-code. Plotstudio orders the strokes for short pen-up moves.

## Pens and colours

The plotter has a pen table of 16 pens: T0 to T15. Each pen has a name and a colour. Plotstudio uses the table to plot a drawing with more colours.

1. Open **Pens → Pen table**. Give each pen in your holder a name and its colour. Leave a row empty for no pen. Push **Save the table**. On the stock build, the table stays in plotstudio. On Wi-Fi (Pico W firmware), the table goes to the plotter too.
2. Add a drawing. The **Pens** card lists each colour of the drawings, with the pen for it. Plotstudio picks the pen with the nearest colour (the distance in CIE L*a*b*, as the eye sees colour).
3. Change a pen in the list if you want another one. Plotstudio keeps the choice for that colour.
4. **Layer names pick pens**: a layer named `3`, `T3`, `Pen 3` or `Tool 3` plots with pen 3, whatever its colour.

A drawing with more pens plots one pen at a time:

- The lightest pen goes first and the darkest pen last. A dark line then draws over a light line, and a light pen does not pick up dark ink.
- Each pen changes once. Before the lines of a pen, the program has `M5`, `Tn` and `M6`.
- The firmware stops at `M6` with the pen up and shows the pen on the LCD. On the stock build the carriage stays where it is. The Pico W firmware parks it first. Plotstudio shows **Pen change: load Tn** over the bed view. Put the pen in the holder, then press the knob. The job goes on.
- A one-pen job has no pen change. Check **pen change at the start of a one-pen job** to add one.

The pen table is in `~/.config/plotstudio/pens.json`. On Wi-Fi, the table of the plotter wins at each connect, because the plotter knows the pens in its holder. An empty table on the plotter gets the table of plotstudio.

## Queue

- While a job runs, the **Plot** button reads **Add to queue**. The layout goes into the queue.
- The queue is under the progress bar. Each job has **Start** and **Remove**.
- A queued job does not start on its own. Change the paper, then push **Start**.

## Alarm

The firmware stops in an alarm after a failed homing, a pressed switch during a move, a failed pen change, or an emergency stop (`M112`). Then it answers each line with `error:alarm, send M999`.

- The **Clear alarm** button shows in the **Plotter** card. It sends `M999` and `G28`.
- Check that nothing blocks the gantry before you push it.

## API

| Request | Action |
|---|---|
| `GET /api/status` | The plotter (`link`: `usb` or `wifi`, `device`: the status of a Wi-Fi plotter), the camera, the calibration, the job (`pen_change`: the pen that the job waits for), and the queue. |
| `POST /api/port` `{"path":"penplotter.local"}` | Connect a plotter: a serial device or a network address. |
| `GET /api/discover` | Plotters on the network (mDNS). |
| `GET /api/devices` | Serial devices. |
| `POST /api/scan` | Park, take the scan pictures, and make the bed view. |
| `GET /api/scan.jpg`, `GET /api/bed.jpg`, `GET /api/bed` | The scan picture, the bed view, and its geometry. |
| `GET /api/camera.jpg` | A live picture. |
| `POST /api/calib/mark` `{"grid":3}` | Draw the calibration dots. |
| `POST /api/calib/refine` `{"px":..,"py":..}` | Move a click to the centre of a dot. |
| `POST /api/calib/solve` `{"pairs":[{"px","py","x","y"}],"fit_k1":true}` | Solve and save the calibration. |
| `POST /api/svg` | Read an SVG file. The reply is an item, with `colors` and `layers` for each line. |
| `POST /api/gcode`, `POST /api/plot` | Make the G-code, or plot it. The body: `{"items":[..], "color_pens":{"#ff0000":2}, "layer_pens":true, "tool_change":false, "queue":false}`. The reply has `pens` and `pen_changes`. |
| `POST /api/queue/{id}/start`, `DELETE /api/queue/{id}` | Start or remove a queued job. |
| `GET /api/pens`, `PUT /api/pens` | The pen table: `[{"t":0,"name":"Black 0.5","color":"#1a1a1a","width":0.5}]`. `width` is optional. |
| `POST /api/job/pause`, `resume`, `cancel` | Control the job. A cancel lifts the pen. |
| `POST /api/cmd` `{"lines":["G28"]}` | Send G-code lines. |
| `GET /api/focus`, `POST /api/focus` `{"auto":false}` | The lens control of a V4L2 camera. |

The UI uses relative links (`api/status`). So plotstudio also works under a path prefix, for example at `/plotter/` in Printdeck (`docs/printdeck.md`).

## Code

| Package | Content |
|---|---|
| `studio/geom` | Homography (normalised DLT), lens model, calibration fit, picture warp. |
| `studio/svg` | The SVG reader, with stroke colours and layers. |
| `studio/plan` | Placement, stroke order, the pen table, pen groups, G-code, calibration points. |
| `studio/serial` | The serial port (raw tty), and the line stream with `ok` flow control. It also runs on a TCP link. |
| `studio/netlink` | The Wi-Fi plotter: mDNS discovery, the TCP G-code link, and the HTTP API client. |
| `studio/camera` | V4L2 capture (MJPEG, YUYV), HTTP and file sources. |
| `studio/app` | The server and the API. `sim_test.go` runs the whole flow against the simulator. `net_test.go` and `queue_test.go` use a fake Wi-Fi plotter. |
| `studio/web` | The UI. |
| `integrations/printdeck/plotter` | Plotstudio as an accessory of Printdeck. |
| `sim/camera.go` | The simulated camera. |

`studio/REVIEW.md` has the review rounds of this software.
