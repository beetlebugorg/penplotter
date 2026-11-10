# Review history

The design went through several rounds of review. Each round checked the design, changed it, and
ran the checks again. The tables below are a record. Many of the parts that they name are no longer in the build: the
pod, the housings, the X band and the pen changer went away on 2026-11-10 (step 19). The detailed
logs are:

- `hardware/REVIEW.md`: the printed parts, five rounds, the change back to V-wheels, the vertical Y
  wheels, the feet, the belt clips, the Y brackets, the omega Y drive, the side wheels, the moving
  cables, the printed X plate, the fixed Y motors, and the simplification of 2026-11-10.
- `firmware/REVIEW.md`: the firmware and Wi-Fi, five rounds.
- `studio/REVIEW.md`: plotstudio and Printdeck, five rounds.
- `docs/REVIEW-integration.md`: the cross-track review, two rounds.

## The design changes

| Step | Change | Reason |
|---|---|---|
| 1 | A pen lift on the CR-10 X carriage, the CR-10 moving bed | The first layout used the CR-10 as it was. |
| 2 | The frame on the table; the table is the bed | No moving bed. Any surface under the frame is the bed. |
| 3 | Two Y motors, each with its own belt and switch | A gantry on two frame rails needs a drive on each side. Homing squares it. |
| 4 | X on two 10 mm rods with LM10UU bearings | This replaced the CR-10 X carriage and its V-wheels. |
| 5 | MGN12 linear rails on X and Y | More accurate, and the travel grew from 216 × 384 mm to 253 × 400 mm. |
| 6 | A small control pod and a 24 V brick | The CR-10 box held a 350 W supply. The plotter needs 30 to 40 W. |
| 7 | PLA only | All parts print in PLA. |
| 8 | Print time review | 15 % gyroid infill, 3 top and bottom layers, faster outer walls, thinner pod walls. About a third less print time. |
| 9 | The stock controller build is the main build | The stock control box, its drivers and its harness work for a pen plotter. Two small housings replace the pod. The Pico W build becomes an optional upgrade. |
| 10 | Back to V-wheels | The plotter reuses the 9 stock V-wheels and the stock X carriage plate. The MGN12 rails cost money, and the stock wheels are free. The travel is 245.9 × 397.0 mm (245 × 395 mm in the firmware). |
| 11 | Vertical Y wheels, 2020 cross bars, camera pole | All axes use vertical wheels. The Y carriage became a C shape: 2 wheels on top of the rail, 1 under it. A printed foot holds a camera pole. The camera mount went away. |
| 12 | Printed feet, tried and removed | Printed feet under the cross bar ends gave 397 mm of Y travel. The machine already has feet, so they stay under the rails. The back feet stop the bottom Y wheels: 381 mm in the model, 380 mm in the firmware. |
| 13 | Belt crimp clips | A metal clip closes each folded belt end. You crimp each belt to length on the bench and drop it into pockets. The idler slots set the tension. |
| 14 | Y brackets on two faces | 4 screws in two slots of the bar end. The most loaded screw drops from 92 N to 56 N (motor bracket) and from 147 N to 52 N (idler bracket). |
| 15 | Y belts fixed on the rails, Y motors on the carriages (omega drive) | The goal is a simpler design with compact parts. The 4 corner brackets and the belt loops outside the frame go away. The cost is Y travel: 381 → 365 mm in the model (364 mm in the firmware). |
| 16 | Side wheels again, belt ends on the bar faces, a drag chain and a band for the moving cables | The side-mounted wheels come back. The stock feet stay under the rails, and the omega Y drive stays. Nothing goes under the rail, so the feet do not limit the travel. The back belt end moves to the back face of the back bar. The travel grows from 365 to 392 mm in the model (390 mm in the firmware). All moving wires are carried low. |
| 17 | Pen changer at the front | A rack with 6 bins hooks over the front bar. A magnetic dock replaces the pen slider. The old 16-pen rack at the back is gone: the beam passes over the back of the travel and hits standing pens. The drawing area with the changer starts at Y 95. |
| 18 | Printed X plate, the stock X belt path, fixed Y motors | A printed X carriage replaces the stock plate, and the X belt runs in the beam slots. The old belt loop in front of the beam hit the parked tall tools at Y 0. The Y motors moved behind the back bar: the gantry is about 630 g lighter, and the Y motor cables do not move. The travel is 395.1 mm in the model (390 mm in the firmware). |
| 19 | Simplification: no pen changer, flat Y plates, bare boards, servo loom | The pen changer is dropped and the build is simpler. The pen changer, the Pico W pod, the board housings, the servo cover, the bar end caps, the pen gauge and the X band went away. The printed plates copy the stock CR-10 layouts with only the features in use. Pen changes are by hand. 16 parts, 21 h 45 min, 383 g. |

## Hardware rounds

| Round | Change | Parts | Print time | Filament | Cost |
|---|---|---|---|---|---|
| 0 | Start | 16 | 25 h 12 min | 453 g | $9.06 |
| 1 | The pen lift and the X carriage are one part. The paper clips and the X carriage fit test go away. | 11 | 24 h 23 min | 440 g | $8.80 |
| 2 | No heat-set inserts. Rail screws in every second hole (52 instead of 100). Cable tie slots. | 11 | 24 h 33 min | 441 g | $8.82 |
| 3 | A 4th driver slot in the pod. The 16-pen rack area is reserved. | 11 | 24 h 37 min | 442 g | $8.84 |
| 4 | A camera mast foot and a camera mount (optional) | 13 | 26 h 45 min | 478 g | $9.56 |
| 5 | A lower pod front, thinner Y carriage plates, print orientation checks | 13 | 26 h 02 min | 464 g | $9.28 |

Without the 2 optional camera parts, the result is 11 parts, 23 h 54 min, 428 g and $8.56. The
fit tests went from 78 min to 32 min. The heat-set inserts went from 8 to 0. The loose fasteners
went from about 183 to 127.

The stock controller build drops the pod and adds 4 small housing parts. With the MGN12 rails, it
was 13 parts, 19 h 53 min, 354 g and $7.08.

## Back to V-wheels

The review rounds used MGN12 rails on both axes. After the rounds, the design went back to the stock
V-wheels. The reasons:

- The plotter reuses the 9 stock V-wheels: 3 on the stock X carriage plate and 6 free wheels from
  the Z carriages and the bed carriage.
- The stock X carriage plate stays. The pen carriage bolts to its 4 tool head holes.
- No rails to buy. The 3 MGN12 rails with their blocks and 38 rail and block screws go away. The
  purchased parts drop from about $165 to about $103.

| | MGN12 build | V-wheel build |
|---|---|---|
| Printed parts, main build | 13 | 13 |
| Print time | 19 h 53 min | 18 h 07 min |
| Filament | 354 g | 323 g |
| Cost | $7.08 | $6.46 |
| With the camera mast (15 parts) | 22 h 01 min, 390 g, $7.80 | 20 h 15 min, 359 g, $7.18 |
| Fit tests | 2 parts, 32 min, 9 g | 3 parts, 51 min, 14 g |
| Pen travel (model) | 253 × 400 mm | 245.9 × 397.0 mm |
| Pen travel (firmware) | 250 × 395 mm | 245 × 395 mm |

The open measurements are in `hardware/MEASURE.md`, items 16 to 23: the wheel size, the
axle-to-face distance, the spacer height, the eccentric shank, the plate-to-beam distance, the wheel
bolt length behind the beam, the wheel bolt positions, and the switch size and holes.

## Feet, fasteners, belt clips and brackets

**Feet.** The stock rubber feet stand under the 2040 rails, 37.5 mm from each end. The bottom wheel
of each Y carriage runs under the rail, so the back feet stop the gantry. A design with four printed
feet under the cross bar ends gave 397.0 mm of Y travel. The machine already has feet, so the printed
feet went away again. The Y travel is 381.0 mm in the model and 380 mm in the firmware.

**Fasteners.** The fasteners are now in the model. The fit check moves them with the parts. The
length check found four errors:

| Screw | Before | Now |
|---|---|---|
| M5 into a T-nut through a 6 mm wall (brackets, beam, pole foot) | M5 × 10: 2.2 mm of thread in the T-nut | M5 × 12: 4 mm of thread, the tip 6 mm into a 6.3 mm slot |
| Housing screws through a 3 mm floor | M5 × 10 button head: the tip hit the core | M5 × 8 button head: 3.2 mm of thread |
| Beam tower T-nut screw | M5 × 12: the tip reached the core | M5 × 12 with a washer under the head |
| Endstop screws through a 6.4 mm switch body | M2 × 8: 1.6 mm of thread | M2 × 10 |

**Belt clips.** Each belt end folds back on itself, and a metal crimp clip closes it. Each clip sits
in a pocket behind an end wall. The belt lies in a slit in the wall. The Y idlers and the X idler
move 5 mm each way in their slots. This takes up a crimp error and the stretch of the belt.

**Y brackets.** Each bracket held on 2 screws in one slot. Now it has 2 screws in the outer face slot
(at x = 41 and 64 mm) and 2 in the top slot of the bar end.

| Bracket | Most loaded screw before | Now |
|---|---|---|
| Y motor bracket | 92 N | 56 N |
| Y idler bracket | 147 N | 52 N |

| | Before (vertical Y wheels) | After these changes |
|---|---|---|
| Main build | 13 parts, 18 h 22 min, 322 g, $6.44 | 13 parts, 19 h 59 min, 348 g, $6.96 |
| With the camera part | 14 parts, 19 h 53 min, 347 g, $6.94 | 14 parts, 21 h 30 min, 373 g, $7.46 |
| Pen travel (model) | 245.9 × 381.0 mm | 245.9 × 381.0 mm |

## Omega Y drive

The design becomes simpler and more compact. Each Y belt now lies fixed along its rail, teeth
down. A front base with a tensioner sled and a back anchor hold its two clips. Each Y motor rides on
its carriage, on a drive mount behind the beam. The belt goes under a smooth idler, over the motor
pulley (180° of wrap), and under a second smooth idler. The 4 corner brackets and the belt loops
outside the frame are gone.

- The back idler of each omega stops at the back anchor. The Y travel is 365.1 mm in the model
  (381.0 mm before). The firmware uses 364 mm.
- The two Y motors ride on the gantry: about 668 g more moving mass.
- The Y motor cables move with the carriages. BOM line M31 adds two 1 m stepper cables in case a
  stock cable is short.
- The head housing moved right to x = 92 mm, beside the left Y motor.

| | Before | Now |
|---|---|---|
| Main build | 13 parts, 19 h 59 min, 348 g, $6.96 | 17 parts, 17 h 40 min, 304 g, $6.08 |
| With the camera part | 14 parts, 21 h 30 min, 373 g, $7.46 | 18 parts, 19 h 11 min, 329 g, $6.58 |
| Pen travel (model) | 245.9 × 381.0 mm | 245.9 × 365.1 mm |

## Side wheels, belt ends on the bar faces, moving cables

The design goes back to the side-mounted wheels. The stock feet stay under the rails. The omega Y
drive stays.

- **Y carriage.** A 6 mm plate over the rail top runs on 3 V-wheels on vertical axles in the side
  slots. Two wheels run outside, 22 mm in front of and behind the beam centre. The back one turns on
  the eccentric spacer. One wheel runs inside at the beam centre, on a tongue that crosses over the
  belt. Nothing goes under the rail.
- **Belt ends.** The front base stays on the top of the front bar. The sled moves 3.5 mm each way. A
  back block on the back face of the back bar holds the back end, with two M5 screws in the face
  slot. A recess clears the bar end screw head, so one part fits both sides. The Y belt is 598.2 mm
  between the folds.
- **Travel.** 245.9 × 391.8 mm in the model (245.9 × 365.1 mm before). At the front the carriage plate
  stops at the front base. At the back the drive mount stops at the back block. The firmware uses
  245 × 390 mm.
- **Control box.** Its right side is now at x = −70 mm.

All moving wires must be carried low, with no tall part. These were the options for the Y
axis (the head harness and the two Y motor cables):

| Option | Cost | Print | Stops travel | Wear and snag | Build |
|---|---|---|---|---|---|
| **Openable drag chain 10 × 20 R28 beside the left rail, lower run on the table (chosen)** | about $13 | anchor 39 min, 11 g | no | low: the chain takes the bending | easy: open the links, lay in the cables |
| Bridge (closed) drag chain 10 × 20 R28 | about $10 | the same | no | low | hard: the big harness plug does not pass, so you must unpin it |
| Band on edge (steel or PET) beside the rail | about $7 | the same | no | medium: the 7 mm harness twists the band | medium: ties every 30 mm |
| Spiral wrap loop on the table with clip points | about $5 | clips, 20 min | no | high: it drags on the table and catches the control box | easy |

These were the options for the X axis (the servo lead only):

| Option | Cost | Print | Stops travel | Wear and snag | Build |
|---|---|---|---|---|---|
| **Band on edge behind the beam, rolling U loop, as in an inkjet printer (chosen)** | about $7 | bracket and clip 47 min, 13 g | no | low: nothing rubs, and the band is light | easy: ties, two small parts |
| Small drag chain (7 × 7 or 10 × 10, R18) | about $10 | a 300 mm support shelf, 2 h or more | no, but the shelf is a tall part over the gantry | low | hard: no low space (the X plate wheels sweep the beam top, and the X belt loop the front) |
| Braided sleeve service loop, low | about $5 | none | no | medium: the loop sags onto the head housing and the Y motors | easy |
| Spiral wrap with clip points | about $3 | clips, 15 min | no | medium to high | easy |

The fit check moves the chain over the Y travel and the band over the X travel. They touch nothing
but their mounts. The chain and band sizes are values in `hardware/shape.py`, so another chain or
band is a change of numbers.

| | Before | Now |
|---|---|---|
| Main build | 17 parts, 17 h 40 min, 304 g, $6.08 | 20 parts, 19 h 34 min, 336 g, $6.72 |
| With the camera part | 18 parts, 19 h 11 min, 329 g, $6.58 | 21 parts, 21 h 05 min, 361 g, $7.22 |
| Fit tests | 1 h 13 min, 18 g | 48 min, 13 g |
| Pen travel (model) | 245.9 × 365.1 mm | 245.9 × 391.8 mm |

## Simplification (2026-11-10)

The pen changer is dropped and the whole build is simpler. The build uses no stock plates, because
they have many mounting points that the plotter does not use.

- **Removed.** The pen changer, the Pico W control pod, both board housings, the servo cover, the
  four bar end caps, the pen gauge, and the X band with its two holders.
- **Y carriages.** Each one is a flat 6 mm plate, in the form of the stock CR-10 Z carriage
  plate. The outer wheels are 44 mm apart. The inner wheel is 18 mm behind the beam, on a 12 mm
  boss. A saddle holds the beam at its old height. The Y travel stays 390 mm.
- **X endstop.** The board moved to the front of a wall in front of the beam end. A lug at the
  bottom left of the X plate presses its lever. The wall is 22 mm lower than before.
- **Boards.** The two breakout boards stand bare on nylon standoffs, held by cable ties.
- **Servo lead.** It runs in a 1/2 inch split wire loom, with a cable tie at each end. The model
  hangs the loop as a catenary. Its lowest point stays 41 mm or more above the paper.
- **Motors.** The X motor is a 42-34 (213.4 g). The Y motors are 42-40 (286.7 g).

| | Before | Now |
|---|---|---|
| Main build | 27 parts, 30 h 28 min, 544 g, $10.88 | 16 parts, 21 h 45 min, 383 g, $7.66 |
| Heat-set inserts | 13 (and 1 M4 for the changer dock) | 9 |
| Pen travel (model) | 245.9 × 395.1 mm | 245.9 × 395.1 mm |
| Fit tests | 49 min, 14 g | 49 min, 14 g |

One question is open. The cable ties of the head board go round the beam, in the path of the X
plate. The options are M3 drop-in T-nuts in the back slot of the beam with M3 screws through the
board and the standoffs, or a board place outside the X travel. This decision is open.

## Firmware rounds

| Round | Topic | Main changes |
|---|---|---|
| 1 | Core and settings | Long comment lines no longer fail a job. Hard limits stop all motion. A 1 mm floor after homing allows a move to 0,0. Settings in flash with a CRC: pen angles, pen table, Wi-Fi, park position (`M500` to `M503`). |
| 2 | Several hosts | Up to 6 connections, one owner at a time. Queries and safety lines from any connection. The `firmware/netapi` package. The network API in the simulator. |
| 3 | Wi-Fi | The Pico W driver and network stack in pure Go. DHCP or a fixed address, mDNS, HTTP on port 80, G-code on port 23. Credentials from the LCD or USB. |
| 4 | Pens | The 16-pen table, `T<n>`, `M6`, `M108`. The manual change with an LCD prompt. The `Changer` interface. Pins reserved for a changer. |
| 5 | Robustness | Lower-case API states. Fewer allocations on the Pico H. Tests for vpype and Inkscape G-code and for the pen change prompt. |

| Build | Flash | Static RAM |
|---|---|---|
| Pico H | 75 772 B | 7 444 B |
| Pico W | 550 896 B | 9 584 B (about 40 KB at run time) |

## Software rounds

| Round | Topic | Main changes |
|---|---|---|
| 1 | Wi-Fi | TCP link, mDNS discovery, HTTP client, reconnect every 3 s. |
| 2 | Multi-pen | SVG stroke colours and Inkscape layers. Nearest pen by colour (CIE Lab). Pens from light to dark with `T<n>` and `M6`. The pen table editor. |
| 3 | Printdeck | Plotstudio as a library at `/plotter/`, with the deck camera. A patch for Printdeck. |
| 4 | Robustness | A job queue, a calibration file for each camera, scan parks 5 mm clear of the switches, a clear-alarm button. |
| 5 | Quality | A status decoding bug fixed. Clean `gofmt` and `go vet`. The documents. |

## Cross-track rounds

`docs/REVIEW-integration.md` has the findings. The main ones:

- The simulator camera reads its position from the mast in `frame.json`.
- The parts list gives the exact belt and idler type.
- Old code of earlier designs is gone from `hardware/`.
