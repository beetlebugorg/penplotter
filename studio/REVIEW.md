# Plotstudio review rounds

Each round reviews the software that the user touches, fixes what it finds, and tests the fix:
`go test -race ./studio/... ./integrations/...`, headless Chromium screenshots of the UI, and a run
against a simulator instance. The date of all rounds is 2026-11-07.

## Round 1: Wi-Fi

Found:

- Plotstudio connects only to a serial device. The Pico W plotter is on Wi-Fi.
- A lost link (USB cable, Wi-Fi drop) stops plotstudio until a restart.

Changed:

- New package `studio/netlink`: the TCP G-code link (port 23), mDNS discovery and `.local`
  names in pure Go (a small DNS encoder and decoder, one-shot queries), and the HTTP API client
  (`/api/status`, `/api/pens`, `/api/job`, `/api/cmd`).
- `serial.Port` runs on any byte stream, so the TCP link uses the same line stream, pause, resume
  and cancel as USB. `Port.Done` reports the end of the link.
- The **Plotter** card: an address field (USB path or network address), **Connect**, **Find**.
  The chip shows **USB** or **Wi-Fi**. On Wi-Fi the card shows the state of the plotter.
- A watcher reconnects to the same plotter every 3 s.
- `tcp://host:port?http=port` sets both ports, for the simulator and the tests.

Tested: DNS records with compression pointers, the address forms, the HTTP client against a fake
server, the TCP link, and a fake Wi-Fi plotter that drops its link (`net_test.go`).

## Round 2: multi-pen jobs

Found:

- The SVG reader drops colours and layers. All lines go to one pen.
- The firmware has a pen table T0 to T15 and `Tn` / `M6`, but plotstudio has no use of it.

Changed:

- `studio/svg` reads the stroke colour of each line (the fill colour when there is no stroke),
  inherited through groups, from attributes and `style`, as `#rgb`, `#rrggbb`, `rgb()` or a name.
  It reads the Inkscape layer label.
- `studio/plan`: the 16-pen table, the nearest pen in CIE L*a*b*, pen numbers in layer names
  (`T3`, `Pen 3`), groups of lines by pen (light pens first), and one program with `M5`, `Tn`,
  `M6` before each group.
- The UI: a **Pens** card with the colours of the layout and a pen for each, and a pen table
  editor. The table syncs with the plotter on Wi-Fi; the table of the plotter wins at a connect.
- The bed view draws each line in the colour of its pen.
- The job status reports `pen_change` while the job waits at `M6`. The UI shows the pen to load.

Tested: colours and layers from an Inkscape-style SVG, nearest pens, the group order, the
program, and a fake plotter that holds at `M6`. On the simulator: a 4-colour drawing ran with 4
pen changes (yellow, light blue, green, black), with a knob press at each.

Found while testing: with no scan, the bed view is dark in the dark theme, and black lines do not
show. The bed view is now paper white with no scan.

## Round 3: Printdeck

Studied: Printdeck runs one printer for each deck (`newPrinter`: Klipper or ChiTu). `ui.Printer`
has about 50 methods for a 3D printer. The camera hub gives `Source.Snapshot` and `Frame.JPEG`.
The remote server protects pages with `rs.Auth`.

Chose: plotstudio as a library at `/plotter/` on the deck (`docs/printdeck.md` has the three
routes and the reasons).

Changed:

- `app.Config.Source`: a host program gives its own camera.
- The UI uses relative links, so it works under a path prefix.
- New package `integrations/printdeck/plotter`: plotstudio with a Snapshot camera, `Summary` for
  a deck tile, and `Discover`. It has no import of Printdeck.
- `integrations/printdeck/printdeck.patch`: `cmd/printdeck/plotterweb.go`, one line in
  `web.go`, `go.mod` and `go.sum`.

Tested: the package mounted at `/plotter/` with a fake camera and a fake plotter. The patch
applies to the printdeck repository (`git apply --check`), and a patched copy of the deck builds
and passes `go vet`.

## Round 4: robustness and UX

Found:

- A second plot while a job runs fails with "a job runs".
- One calibration file serves all cameras. A change of camera uses a wrong calibration.
- The end-to-end simulator test failed with the new firmware: the scan parked at X 0 and Y 0,
  on the home switches, and the firmware read a hard limit and stopped in an alarm. The second
  scan picture then did not happen, and the left tower hid a calibration dot (rms 1.15 mm).
- The firmware alarm (`error:alarm, send M999`) has no control in the UI.

Changed:

- A job queue: **Plot** reads **Add to queue** while a job runs. Each queued job starts on a press
  of **Start**, so the paper can change first.
- A calibration file for each camera (`calibration-<camera>.json`). The old file stays in use for
  its camera.
- The park positions stay 5 mm from the home switches. The calibration test is at rms 0.036 mm
  again.
- **Clear alarm** shows when the plotter is in an alarm. It sends `M999` and `G28`.
- The pen change prompt also shows over the bed view, with a solid background.
- Device states are in one form: `PEN CHANGE` and `pen_change` both give `pen_change`.

Tested: the queue against a fake plotter, the calibration file name, the full simulator flow
(`sim_test.go`), the UI at 1400 px and at 390 px (phone).

## Round 5: code quality and docs

Found:

- After `Close`, a reconnect or a pen sync can still write files (a test folder failed to clear).
- Against the simulator API, every status poll failed: the plotter sends `"pen":"up"`, and the
  client wanted a number. The API also sends `alarm`, `msg` and `progress`.
- A job that streams over TCP has no total on the plotter, so a deck tile showed 0 %.

Changed:

- `Close` stops the reconnect and the file writes.
- `netlink.Status` reads the pen as a word or a number, and keeps `alarm`, `msg`, `owner` and
  `progress`. The Plotter card shows the message of the LCD.
- `plotter.Summary` uses `progress` when the plotter has no total.
- `gofmt` and `go vet` are clean. The tests pass three times in a row with the race detector.
- Docs: `docs/studio.md` (Wi-Fi, pens, queue, alarm, API), `docs/printdeck.md`,
  `docs/guide/30-software.md`, `integrations/printdeck/README.md`.

Tested end to end on the simulator over Wi-Fi (`tcp://127.0.0.1:2393?http=8791`): the pen table
came from the plotter (16 pens), the drawing mapped to 4 of them, the job stopped at each pen
change, the knob went on, and the job ended (202 of 202 lines).

## Open items

- The V4L2 code, the focus lock and the Wi-Fi link are not tested on real hardware.
- The mDNS discovery is tested with crafted packets, not with the firmware of the Pico W.
- The deck screens of Printdeck have no plotter tile yet (`docs/printdeck.md`, step 6).
- The repository has a license file, `LICENSE.md`: MIT for the code, CC BY 4.0 for the designs
  and the docs.
