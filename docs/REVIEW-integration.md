# Cross-track review

The three tracks (hardware, firmware, software) each ran five review rounds. This review checks that
their code, data and documents agree. Each round lists the findings, the fixes and the checks.

## Round 1: data and interfaces

### Findings

| # | Area | Finding |
|---|---|---|
| 1 | Pin map | `pins.go` and `docs/wiring.md` agree on all 25 pins. The changer reserves GP13, GP14, GP15 and GP26. |
| 2 | Pin map | `docs/wiring.md` put a later SPI touch panel on GP13 to GP15, GP26 and GP27. These pins belong to the pen changer. |
| 3 | Travel | The firmware (250 × 395 mm), Plotstudio (it reads the firmware config), the Printdeck package and the docs agree. The model allows 252.9 × 400.2 mm, so the firmware keeps a 3 to 5 mm margin. |
| 4 | Pen rack | The rack area (machine X 10 to 243 mm, Y 325 to 395 mm) is inside the firmware travel. Nothing stops a drawing from going into it. |
| 5 | Pen rack | The M6 park position is X 125, Y 0 (front centre). It is clear of the rack. It is the right place for a manual pen change. |
| 6 | Sim camera | The sim camera used the first mast position (200, 560, 400). The mast in `frame.json` puts the camera at (200, 468, 480). The gantry boxes of the sim camera still described the rod design. |
| 7 | Network API | The routes (`/api/status`, `/api/cmd`, `/api/job`, `/api/pens`), the state names and the ports agree in the firmware, the sim, Plotstudio, `docs/network-api.md` and the guide chapters. |
| 8 | BOM | The belt row did not give the pitch, the core or "open". The idler row did not say "toothed" or the total of 3. |
| 9 | Guide data | The hardware list in `make_pdf.py` named "parts with inserts". No part has inserts now. |
| 10 | Controller | The firmware chapter put the Pico H first. The build uses the Pico W. |
| 11 | Code | `hardware/parts.py` kept 10 functions of the old designs (paper clip, electronics plate, rod X carriage, bolts, plate keep-outs). `shape.py` kept 37 values that nothing reads. `model.py` still checked the base against the Creality plate and the paper clip strain. |
| 12 | PLA | All profiles, the guide data and the docs use PLA. Only the review logs mention PETG, as history. |

### Fixes

1. `docs/wiring.md`: the touch panel takes the LCD pins (SPI0 on GP16, GP18, GP19; CS, DC and touch on GP17, GP20 to GP22). The changer pins stay free.
2. `firmware/config`: new `PenRackY0 = 325` and `PenRackGap = 5`.
3. Plotstudio: new `-pen-rack` flag and `Config.DrawY`. With a rack, a drawing must end at Y = 320 mm. `docs/studio.md` and `docs/guide/30-software.md` describe it.
4. `sim/camera.go`: the camera pose comes from `frame.json` (`camera.pos`), with the old pose as the fallback. The gantry boxes now describe the MGN12 design: Y carriage plates and towers, the 2020 beam, the X rail and the pen carriage.
5. `docs/bom.md`: belt row 18 (GT2 open belt, 2 mm pitch, 6 mm, glass fibre, 5 m) and idler row 20 (20T toothed, 5 mm bore, 3 in total).
6. `make_pdf.py`: the hardware list gives the belt spec. The layer note names the pod tray as the part with 4 walls.
7. `docs/guide/25-firmware.md`: the Pico W comes first.
8. `hardware/parts.py`: removed `paper_clip`, `electronics_plate`, `fit_template`, `plate_slab`, `wheel_heads`, `bolts`, `teardrop_x_at`, `x_carriage`, `fit_bearing` (two copies) and `P_box_cut`. `shape.py`: removed 37 dead values. `model.py`: removed the Creality plate and paper clip checks. `cura/make_profiles.py` and `stats.py`: removed the clip profile and count.

### Checks

| Check | Result |
|---|---|
| `go vet ./...` | clean |
| `go test -race ./...` | 16 packages pass |
| Plotstudio calibration against the sim with the mast camera | RMS 0.051 mm, k1 -0.080 (true value -0.080) |
| `tinygo build -target=pico` | 75 772 B flash, 7 444 B RAM |
| `tinygo build -target=pico-w` | 550 896 B flash, 9 584 B static RAM |

## Round 2: documents and the full guide

### Findings

| # | Area | Finding |
|---|---|---|
| 1 | Hardware PDF | The first run step said that `samples/square.gcode` draws a 100 × 100 mm square. The file draws a 40 mm square. |
| 2 | Wiring | The first power-on steps named only `build/plotter.uf2`, the Pico H file. The Pico W needs `build/plotter-w.uf2`. |
| 3 | Wiring | A cross reference named a section "Reserved for the pen changer". The section is "Pins for the automatic pen changer". |
| 4 | Guide | The software chapter title had a "30 ·" prefix. The other chapters have plain titles. |
| 5 | Guide | Chapters 00, 05, 15, 20, 40, 65, 70, 75, 80 and 90 did not exist. The documents had no single PDF. |
| 6 | Images | `hardware/build/img` kept 12 images of removed parts (paper clip, electronics plate, rod X carriage, pen lift base, fit template, X carriage fit test). |
| 7 | Plotstudio | The pen rack limit had no test. |
| 8 | Repository | No root README. |
| 9 | Paths | All repository paths named in the documents exist (24 files checked). |

### Fixes

1. `hardware/make_pdf.py`: 40 × 40 mm. The hardware PDF is rebuilt.
2. `docs/wiring.md`: both UF2 names, and the right section name.
3. `docs/guide/30-software.md`: plain title.
4. New chapters `00-overview`, `05-parts-and-cost`, `15-assembly`, `20-electronics-and-wiring`, `40-calibration-and-first-plots`, `70-pen-changer`, `65-pico-w-wireless-and-printdeck`, `75-review-history`, `80-troubleshooting` and `90-reference`. The `70-pen-changer` chapter was removed later (see "Later change: simplification").
5. New generator `tools/guide`: Markdown with includes, a cover, a contents page with page numbers (two passes with pdftotext), page numbers in the footer, and the line-art images. It writes `docs/penplotter-guide.pdf`.
6. Removed the stale images.
7. New test `studio/app/rack_test.go`. This test was removed later, with the pen changer.
8. New `README.md`. The progress site has a "Full guide" tab and shows this review.

### Checks

| Check | Result |
|---|---|
| `go vet ./...` | clean |
| `go test -race ./...` | 16 packages pass, with the new rack test |
| `tinygo build -target=pico` / `-target=pico-w` | 75 772 B / 550 896 B flash |
| `hardware/make.sh` after the code cleanup | fit, mesh, overhang and support checks pass; 13 parts, 26 h 02 min, 464 g, $9.28 |
| The README quick start, on test ports | plotstudio connects to plotsim over TCP and HTTP (`link: wifi`) |
| `go run ./tools/guide` | `docs/penplotter-guide.pdf` |

## Later change: back to V-wheels

The two rounds above checked the MGN12 design. The design then went back to the stock V-wheels
(`hardware/REVIEW.md`, "Back to V-wheels"). The new values:

- Travel: the model allows 245.9 × 397.0 mm. The firmware uses 245 × 395 mm (`TravelX`, `TravelY`).
  The docs and the Printdeck example use the same values.
- The pen rack area (machine X 10 to 243 mm, Y 325 to 395 mm) stays inside the firmware travel.
- The simulator draws the V-wheel layout from `frame.json`: `x_carriage`, `x_wheels` and `y_wheels`.
- The chapters were renumbered. The file names above are the current names.

## Later change: simplification (2026-11-10)

The pen changer, the Pico W control pod, the board housings, the covers, the end caps, the pen
gauge and the X band went away (`hardware/REVIEW.md`, "Simplification"). The pen rack area, the
changer pins and the `-pen-rack` flag above no longer apply. Pen changes are by hand at `M6`. The
chapters `60`, `62`, `65` and `70` of the guide are gone.

## Open decisions

1. Licence: decided. MIT for the code, CC BY 4.0 for the designs and the docs (`LICENSE.md`).
2. The pen changer design: decided. No pen changer (2026-11-10).
3. The measurements in `hardware/MEASURE.md`: the V-wheels and the stock X carriage plate, the LCD board, the driver board holes, the buck module, the upright length.
