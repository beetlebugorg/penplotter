# The pen plotter in Printdeck

> **Note:** Printdeck needs a Pico W board with the Pico W firmware (`firmware/cmd/pico`). The
> deck reaches the plotter over Wi-Fi and the HTTP API. The build in the guide uses the stock
> control box. It has USB only, so it does not work with Printdeck.

Printdeck runs one 3D printer next to its touch screen. This document adds the pen plotter to the
same deck as an accessory machine. The deck keeps its printer. The plotter gets a page at
`/plotter/` on the remote screen of the deck, and the camera of the deck scans the plotter bed.

## What the user gets

- The remote screen of the deck has a page `/plotter/`, behind the same login.
- The page is plotstudio: the bed scan, the layout of SVG files and signatures, the pen table,
  multi-pen jobs, the queue, and pause, resume and cancel.
- The deck connects to the plotter over Wi-Fi: `penplotter.local`, or an IP address.
- The camera of the deck (for example the Arducam B0561 over the bed) takes the scan pictures.
  The plotter needs no camera of its own when the deck camera sees its bed.
- A deck screen can show a status tile: online, state, job and percent, the pen now, and a pen
  change prompt (`plotter.Summary`).

## Three routes

| Route | For | Against |
|---|---|---|
| 1. A plotter backend for `ui.Printer` | The plotter shows on the deck screens like the printer. | `ui.Printer` has about 50 methods for heaters, extrusion, pressure advance, Klipper config and spools. A plotter answers "not supported" to most of them. And `newPrinter` picks one backend for each deck, so the plotter replaces the 3D printer. |
| 2. The plotter looks like Klipper or Moonraker | No new code in Printdeck. | The deck talks to Klipper on its API socket, with Klipper objects and macros. The firmware of the plotter runs on a Pico W with 264 KB of RAM. A Klipper API on it is large work for no gain. |
| 3. Plotstudio as a library, mounted at `/plotter/` | One new file in Printdeck and a few lines. The deck keeps its printer. All plotstudio features come at once, with their tests. The camera of the deck goes to plotstudio through one function. | The plotter page is a web page, not a native deck screen. A native tile needs a small screen later (step 6). |

**The choice is route 3.** It adds the plotter without a change to the printer code of the deck.
It reuses all of plotstudio, which has its own tests against the simulator. The camera of the
deck feeds it through a small adapter, so the deck camera code does not change.

## Data flow

```
 browser ──login── deck remote screen (mux)
                     │
                     └── /plotter/  ── plotter.Plotter (integrations/printdeck/plotter)
                                          │
                                          ├── plotstudio app (studio/app): UI, layout, pens, queue
                                          │      │
                                          │      ├── TCP 23: G-code lines, "ok" for each ─────► Pico W plotter
                                          │      └── HTTP 80: /api/status, /api/pens ─────────► Pico W plotter
                                          │
                                          └── Snapshot() ── app.Camera.Source(sel).Snapshot ── camera hub of the deck
```

- The G-code goes over the TCP link, line by line, with `ok` flow control. So pause, resume and
  cancel act at once, and a pen change (`M6`) shows as a prompt.
- The status poll and the pen table use the HTTP API of the plotter (`docs/network-api.md`).
- The camera adapter takes two pictures for a scan and keeps the second: the first can show the
  gantry in motion.

## What Printdeck needs

`integrations/printdeck/printdeck.patch` has all the changes. It applies to the `printdeck`
repository with `git apply` and builds (checked on 2026-11-07).

| File | Change |
|---|---|
| `deck/cmd/printdeck/plotterweb.go` | New. `registerPlotter` reads `plotter.json`, makes the plotter with the deck camera, and mounts it at `/plotter/` behind `rs.Auth`. |
| `deck/cmd/printdeck/web.go` | One line: `registerPlotter(mux, rs, cfg, app)` after `registerRollPages`. |
| `deck/go.mod` | `require github.com/beetlebugorg/penplotter`, a `replace` to the penplotter checkout, and `go 1.26.0` (the penplotter module needs Go 1.26). |
| `deck/go.sum` | The sums of the new requirement. |

`plotter.json` in the state folder of the deck turns the plotter on:

```json
{"addr": "penplotter.local", "camera": "", "travelX": 245, "travelY": 390}
```

- `addr`: the plotter. A deck with no `plotter.json` has no plotter page.
- `camera`: the camera of the deck: `""` for the main camera, a role, a number, or an ID.
- `travelX`, `travelY`: the travel in mm.

The plotter keeps its calibration, its pen table and its signature library in `plotter/` in the
state folder of the deck.

## Licenses

Printdeck is under the GNU Affero GPL, version 3. The plotter code links into the deck binary.
The code of the penplotter repository is under the MIT License (see `LICENSE.md`). MIT code can
go into an AGPL-3.0 program, so the two licenses agree. The deck binary as a whole is under the
AGPL-3.0.

## Steps

1. Clone beetlebugorg/printdeck next to this repository. Apply the patch in the printdeck
   checkout:

   ```sh
   cd printdeck
   git apply ../penplotter/integrations/printdeck/printdeck.patch
   ```

2. Check the `replace` line in `deck/go.mod`. It points to `../../penplotter`, a checkout next to
   the printdeck checkout. For a release build, use a tagged version of the penplotter module and
   remove the `replace` line.
3. Build the deck: `cd deck && go build ./cmd/printdeck`.
4. Put `plotter.json` in the state folder of the deck, and start the deck. Open
   `http://<deck>/plotter/`.
5. Later: add a tile to the deck screens with `plotter.Summary` (online, state, job, percent, pen
   change). The tile opens `/plotter/` on a phone through a QR code, as the roll pages do.
7. Later: let a project of the deck hold plotter jobs, next to its prints.

## Test

- `go test ./integrations/...` mounts the plotter at `/plotter/` with a fake camera and a fake
  Wi-Fi plotter. It checks the page, the relative links, the status, the camera and `Summary`.
- The patch was applied to a copy of `printdeck/deck`, and `go build ./cmd/printdeck` and
  `go vet ./cmd/printdeck` passed.
