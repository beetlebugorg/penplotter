# Hardware review

Each round reviews the printed parts and the build for these points:

- Parts count: the number of printed parts, print jobs, and loose fasteners.
- Print quality: orientation, overhangs, layer lines on load paths, tolerances, first-layer area, warping.
- Ease of build: the assembly order, tool access, hidden fasteners, inserts, and wiring access.
- Print cost: print time, filament, and cost from real CuraEngine slices (PLA, 0.3 mm layers, TAZ Workhorse SE 0.5 mm).
- Expandability: the 16-pen changer, a 4th driver, a 2nd servo, cables, and the camera.

`python3 stats.py` prints the numbers after `make.sh`. The totals leave out the fit tests. PLA costs $19.99/kg.

## Round 0: the starting point

The table plotter with MGN12 rails on both axes, the lean print settings, and the 2 mm pod walls.

| | Value |
|---|---|
| Printed parts | 16 parts in 13 print jobs (4 paper clips in one job) |
| Fit tests | 3 parts, 78 min, 22 g |
| Print time | 25 h 12 min |
| Filament | 453 g |
| Cost | $9.06 |
| Heat-set inserts | 8 (4 pen lift, 4 pod) |
| Loose fasteners | about 183 (100 of them rail screws and T-nuts) |

The mesh check failed on the pod tray: with the 2 mm wall, the corner posts stood out of the rounded outer corners by 1.5 mm. The posts are now trimmed to the outer shell.

## Round 1: fewer parts

Findings:

- The pen lift base and the X carriage are two parts with 4 heat-set inserts and 4 screws between them. The screws go in from the back, behind the X rail, where a hex key barely reaches.
- The pen lift outline still has cut-outs for the bolt heads of the Creality carriage plate. That plate is gone.
- The X carriage cannot merge with the base while the X belt clamp stands out behind the plate: the merged part would have no flat face to print on.
- The paper clips hold paper on a glass bed. The table is the bed now, so tape or a cutting mat holds the paper.
- The fit test for the X carriage tests a countersink on a standard MGN12H hole pattern. It adds 45 min for little value.

Decisions:

- Merge the pen lift base and the X carriage into one part, `pen_carriage`. It prints on its flat back face. Four M3 × 10 screws go in from the front, through counterbores, into the X block.
- Move the X belt into the plane of the carriage plate, above the plate. Tabs on the top edge of the plate clamp the lower run. The tabs print flat with the plate, with no overhang.
- Put the X motor on a wall in front of the left tower, shaft to the back. The pulley is between the wall and the tower. Put the X idler on the same wall of the right tower, on an M5 axle from the wall to the tower. The motor screws go in from behind the wall, where they are easy to reach.
- Put the X endstop on a pillar behind the motor wall. (A first try had a floating pad. The overhang check caught it.)
- Remove the plate cut-outs, the paper clips, and the X carriage fit test.

| | Round 0 | Round 1 |
|---|---|---|
| Printed parts | 16 (13 jobs) | 11 (11 jobs) |
| Fit tests | 3, 78 min, 22 g | 2, 33 min, 9 g |
| Print time | 25 h 12 min | 24 h 23 min |
| Filament | 453 g | 440 g |
| Cost | $9.06 | $8.80 |
| Heat-set inserts | 8 | 4 |
| Loose fasteners | about 183 | about 175 |

The pen carriage (2 h 33 min, 45 g) replaces the pen lift base and the X carriage (2 h 58 min, 52 g). The Y carriages grow a little: each has a motor wall now.

## Round 2: easier to build

Findings:

- The pod tray still has 4 heat-set inserts for the lid. They are the last inserts, and they need a soldering iron and an insert tip.
- The fit rail tests an insert hole. Without inserts, that test has no use.
- The three MGN12 rails take 50 M3 screws and 50 T-nuts, one in every 25 mm hole. A pen plotter has small loads. A screw in every second hole holds the rail flat and straight.
- The gantry cables (X motor, servo, X endstop, later the pen changer) have no anchor. They hang between the pod and the moving gantry.

Decisions:

- Replace the 4 pod inserts with 2.8 mm pilot holes. The M3 × 12 lid screws cut their own thread in PLA. The pod tray keeps 4 walls around the posts.
- Remove the insert hole from the fit rail.
- Put the rail screws in every second hole (50 mm apart) and in the end holes: 26 screws and 26 T-nuts.
- Add cable tie slots: two pairs in the outer side wall of each Y carriage, one pair in the belt clamp tabs of the pen carriage. The first try had flat slot tops; the overhang check caught them. The slots now have pointed tops.

| | Round 1 | Round 2 |
|---|---|---|
| Printed parts | 11 (11 jobs) | 11 (11 jobs) |
| Fit tests | 2, 33 min, 9 g | 2, 32 min, 9 g |
| Print time | 24 h 23 min | 24 h 33 min |
| Filament | 440 g | 441 g |
| Cost | $8.80 | $8.82 |
| Heat-set inserts | 4 | 0 (no soldering iron) |
| Loose fasteners | about 175 | about 127 |

The print time grows by 10 minutes: the tie slots and the pilot holes add perimeters. The build loses 48 rail screws and T-nuts, 4 inserts, and a tool.

## Round 3: room to grow

Findings:

- The future 16-pen changer needs a Z axis (a 4th stepper driver), a gripper servo (a 2nd servo output), a Z endstop, and a place for 16 pens.
- The pod has posts for 3 drivers only. Its cable notch is 60 mm wide: too small for 4 motors, 4 endstops, and 2 servos.
- Nothing in the geometry reserves space for the pen rack.

Decisions:

- Put four driver posts in one row in the pod: X, Y1, Y2, and a spare for the Z axis. The row moves 1.2 mm to clear the corner posts.
- Widen the cable notch to 80 mm.
- Reserve the back of the Y travel for the pen rack: two rows of 8 pens, 28 mm apart, at machine Y = 345 and Y = 373, X = 27 to 223. Letter paper that starts at Y = 20 ends at Y = 299, so the rack and the paper do not touch. `frame.json` carries the area and the 16 slot positions under `reserved.pen_rack`. The table images show the area.
- Record the Z axis plan in `frame.json`: a short MGN9 rail on the pen carriage and the spare driver slot. The changer itself is future work, after the first build.

| | Round 2 | Round 3 |
|---|---|---|
| Printed parts | 11 (11 jobs) | 11 (11 jobs) |
| Print time | 24 h 33 min | 24 h 37 min |
| Filament | 441 g | 442 g |
| Cost | $8.82 | $8.84 |
| Driver slots | 3 | 4 |

The firmware side (pen table T0 to T15, M6, the spare outputs) belongs to the firmware track.

## Round 4: the camera mast

Findings:

- `plotstudio` needs the Arducam B0561 over the bed, still and level. The simulator puts the camera about 400 mm over the table, behind the frame, at the centre.
- The CR-10 has two spare 2040 uprights. One makes a mast with no new metal.
- The B0561 has a U bracket with a pivot and a 1/4"-20 thread in its base. The pivot sets the tilt, so the printed mount can be a flat plate.

Decisions:

- Add `mast_foot`: a plate between the back face of the back bar and the upright, with side cheeks that hold the upright square. Two M5 screws go into T-nuts in the bar, two into T-nuts in the upright. The upright stands on the table.
- Add `camera_mount`: a flat plate with two ribs on the top end of the upright. Two M5 screws go into the tapped end of the 2040. The camera hangs under the front end on its 1/4"-20 screw.
- Mark both parts optional. The plotter works with no camera.
- The first try had the bar screws outside the plate and flat counterbore ceilings on the print bed. The plate is now wider, and each counterbore ends in a 45° cone.
- The upright length (500 mm) is an estimate. Any height from about 400 mm works: `plotstudio` calibrates the view.

| | Round 3 | Round 4 |
|---|---|---|
| Printed parts | 11 | 13 (2 optional) |
| Print time | 24 h 37 min | 26 h 45 min |
| Filament | 442 g | 478 g |
| Cost | $8.84 | $9.56 |

Without the optional mast parts, the numbers are the same as round 3.

## Round 5: print time and quality

Findings:

- The pod tray is the longest print (4 h 52 min). Its front edge is 40 mm high, but the boards and the LCD need about 27 mm at the front.
- The Y carriage plates are 8 mm thick. The block screws need 3 mm of plastic under the head. The outer side wall is 8 mm thick.
- Print quality check of every part:
  - All parts print on a large flat face. No part needs a brim on the TAZ Workhorse.
  - The tallest part is the Y carriage (97 mm), on a 72 × 74 mm plate. It stands steady.
  - The belt tension pulls the motor wall of the left Y carriage across its layers. The side wall and the tower brace the wall in an L, and a plotter belt needs little tension.
  - The dovetail of the pen carriage prints with its 60° faces as overhangs. The fit tests check that fit first.
  - The first layer uses a -0.15 mm offset against elephant foot, so the fit faces stay true.

Decisions:

- Lower the pod front to 31 mm (the slope stays 12°). The fit check keeps the LCD clear of the boards.
- Make the Y carriage plates 6 mm and the side walls 6 mm. The Y belt, the brackets and the endstop arms follow the plate height.

| | Round 4 | Round 5 |
|---|---|---|
| Printed parts | 13 (2 optional) | 13 (2 optional) |
| Print time | 26 h 45 min | 26 h 02 min |
| Filament | 478 g | 464 g |
| Cost | $9.56 | $9.28 |

## Summary

| | Round 0 | Round 5 | Round 5 without the camera mast |
|---|---|---|---|
| Printed parts | 16 (13 jobs) | 13 | 11 |
| Fit tests | 3, 78 min, 22 g | 2, 32 min, 9 g | 2, 32 min, 9 g |
| Print time | 25 h 12 min | 26 h 02 min | 23 h 54 min |
| Filament | 453 g | 464 g | 428 g |
| Cost | $9.06 | $9.28 | $8.56 |
| Heat-set inserts | 8 | 0 | 0 |
| Loose fasteners | about 183 | about 133 | about 127 |
| Driver slots | 3 | 4 | 4 |
| Camera mount | none | yes | no |

Open points:

- The Y carriages are the largest prints (4 h 20 min each). A lighter tower needs a real stiffness test first.
- The LCD board, the TMC2209 hole pattern, and the upright length are estimates (`MEASURE.md`).
- The pen changer itself (Z axis, gripper, rack) is future work. The space and the driver slot are ready.

## Variant: the stock controller

A second build keeps the stock CR-10 V3 control box and its harness. The harness
ends in two breakout boards: the head board (from the tool head) and the base board (Y and Z). The
Pico build stays as it is.

Findings:

- The pod (pod_base, pod_lid) is not needed: the stock box holds the board, the PSU and the LCD.
- The head board must move with the gantry, as on the CR-10. The back face of the X beam is free
  from x = 42 mm (the left tower) to the right tower. The pen carriage is on the front face.
- The base board fits on the back face of the back bar, between the left Y motor bracket (x = 30 mm)
  and the mast foot (x = 162 mm).
- The mated XH plugs stand 17 mm high, and the wires need 12 mm more to bend. This sets the tray
  height (42 mm).
- All board sizes are estimates from photos (+/- 2 mm).

Decisions:

- Two parts for each board: a tray and a lid. The lid slides into 45° grooves at the top of the side
  walls. A 0.6 mm ridge on the groove ledge holds it by friction. No lid screws.
- One open end: the big plug and its cable go out there, and the lid goes in there. The plug goes in
  under the lid, so you can plug it in with the lid on. The XH wires go out through a window over
  the low end wall. The lid closes the top of the window, so the window has no bridge.
- The board sits on two posts with 2.9 mm pilots (0.1 mm over SELF_TAP). The posts are 7 mm wide, so a
  new pilot can go up to about 1.5 mm off.
- The M5 screws are under the board, between the posts. The posts are 6 mm high, so the button heads
  (2.75 mm) clear the 2 mm solder tails.
- The head tray points its open end up: the big cable goes up, then back to the box. The base tray
  points its open end to +X: the 25 mm plug and the cable stay clear of the gantry and the mast foot.
- A single part (a clip-on cover with no tray) was rejected. The board needs posts, and the posts need
  a floor.

The fit check proves: the boards, the plugs, the wire bends and the big cables are clear of the trays
and lids. The lid slides out with no contact, and the ridge touches it. Over the whole Y travel, the
head housing is clear of the beam, the towers, the X motor, the back bar, the motor brackets, the mast,
the mast foot, the camera and the base housing. At the back of the travel it passes 15 mm above the
base housing. It is clear of the pen carriage over the X travel.

Slice comparison of the new parts (CuraEngine, the lean profile):

| Change | Head tray | Base tray | Result |
|---|---|---|---|
| First design (3 mm side walls, 2 mm end wall) | 72 min, 22 g | 56 min, 17 g | |
| 2 walls instead of 3 | -6 min, -3 g | -5 min, -3 g | rejected: weak screw posts |
| 10 % infill | -1 min | -1 min | rejected: no gain |
| 4 s minimum layer time | 0 | 0 | rejected: no gain |
| Outer walls 50 mm/s | -7 min | -5 min | rejected: changes the shared profile |
| 1.5 mm side walls with a 45° flare under the groove, 1.5 mm end wall | 52 min, 17 g | 40 min, 13 g | **applied** |

The lids (19 and 13 min) are 8 layers of plate. No setting changed them.

| | Pico build (no mast) | Stock controller variant (no mast) |
|---|---|---|
| Printed parts | 11 | 13 |
| Print time | 23 h 54 min | 19 h 53 min |
| Filament | 428 g | 354 g |
| Cost | $8.56 | $7.08 |

The four housing parts: 2 h 04 min, 40 g, $0.80. Open points: measure the two boards (`MEASURE.md`,
items 24 to 33). The firmware must map Z1 to the Y2 motor and Z- to the Y2 endstop.

## Back to V-wheels

The design goes back from the MGN12 rails to the stock V-wheels. Six free wheels go under the two Y
carriages. The stock X carriage plate keeps its own three wheels on the beam.

Findings:

- With no Z uprights, the Y carriages must hold the beam ends, the X motor and the X idler.
- The stock X motor bracket is part of the left Z carriage, and the stock X tensioner is part of the
  right beam end. Their shapes are not known. The Y carriages hold the X motor and the X idler.
- The stock plate has belt tabs under the beam. How the stock belt runs past the bottom wheel is
  not known. A printed clamp block on the pen carriage holds the X belt ends.
- The head housing rides on the back face of the beam, in the path of the X plate wheel bolts. The
  bolts must end inside the back face of the beam.
- The inner wheel of a Y carriage is under the path of the X plate. The carriage plate stays a narrow
  tongue there, so the X plate and the pen carriage pass over it and in front of it.
- The X belt cannot run behind the beam: the head housing is there. It runs as a vertical loop in
  front of the plate, above the wheel bolt heads.

Decisions:

- Y carriage: a 6 mm plate on 3 wheels (2 outer, 1 inner on an eccentric spacer), the Y belt block
  on the outer edge, a tower around the beam end (an M5 into the beam end, an M5 into a T-nut), a wall
  in front of the tower. Left: the X motor on the front of the wall, the X endstop on its back.
  Right: the X idler on an M5 axle between the wall and a post.
- The towers end at x = 28 mm. The X plate stops at the tower. The X travel grows from the 216 mm of
  the first V-wheel layout.
- Pen carriage: the pen lift of the first design, with M3 pilot holes in place of the heat-set
  inserts. A clamp block on its top holds the X belt ends. A toe at its left end pushes the X endstop.
- Y endstop: the switch hangs on the outer face of the idler bracket arm. The arm top is on the
  platform plane, so it prints on the bed.
- A new fit test, `fit_wheel`: one wheel hole and the eccentric hole on a strip across the rail.
- No new purchased parts except screws. The MGN12 rails, their blocks and 38 screws go away.

The fit check proves: each wheel touches the two flanks of its slot with a 0.1 mm preload (0.87 mm3)
and nothing else of the wheel touches the extrusion. The X plate eccentric moves 0.30 of its 0.8 mm.
The pen carriage is clear of the wheel bolt heads. The head screws are clear of the wheels. The
travel ends are: x min and x max the X plate at a tower, y min the slider at the front bar, y max a
rear Y wheel at the back bar. The head housing is clear of the X carriage over the X travel.

Slice comparison (left Y carriage, the lean profile):

| Change | Print time | Filament | Result |
|---|---|---|---|
| First design | 4 h 11 min | 75 g | |
| Motor wall 4.5 mm above the top motor screws | -4 min | -1 g | **applied** |
| Outer 4 mm of the tower off | -1 min | -1 g | rejected: a shorter counterbore, no real gain |
| Fit wheel strip 4 mm thick | -3 min | -1 g | rejected: the test must match the 6 mm plate |

| | MGN12 build | V-wheel build |
|---|---|---|
| Printed parts (main build) | 15 | 15 |
| Print time | 22 h 01 min | 20 h 15 min |
| Filament | 390 g | 359 g |
| Cost | $7.80 | $7.18 |
| Without the camera mast | 19 h 53 min, 354 g | 18 h 07 min, 323 g |
| Fit tests | 32 min, 9 g | 51 min, 14 g |
| Pen travel | 253 × 400 mm | 245.9 × 397.0 mm |

Open points: measure the wheel, the spacers, the eccentric spacer, the plate-to-beam distance, the
wheel bolt lengths of the X plate and the switch (`MEASURE.md`, items 16 to 23).

## Y wheels vertical, 2020 cross bars, camera pole

All axes get vertical wheels: 2 wheels on the top of each long rail, and 1 wheel
under it. New facts about the frame: the long sides are 2040, laid flat. The front and back cross bars
are 2020. Four rubber feet stand under the long sides. The camera is a USB webcam on a 590 mm pole.

Findings:

- The bottom wheel and its lugs are under the rail. They cannot pass the feet. With the feet at the
  photo positions (centres 37.5 mm from each end, under the inner bottom slot), the back feet stop
  the gantry 16 mm early.
- A foot under the outer bottom slot does not help: the web of the carriage spans the full width of
  the rail.
- The front feet do not stop the gantry: the slider hits the front bar first.
- The top wheels sit 2.1 mm deep in the top slot. They cannot roll onto a bar. The rear top wheel
  stops at the back bar, as the rear side wheel did before.
- A 2020 bar has one slot in its outer face. The two screws that hold a bar to a side have their
  heads in that face.
- The top wheel bolt heads are on the outer face of the side plate. The belt block is outside them.

Decisions:

- Y carriage: a C shape that prints upright, the web on the bed. The side plate (6 mm) carries the
  two top wheels on M5 × 30 screws, 22 mm in front of and behind the beam centre (as before). The web
  under the rail (8.5 mm, 5 mm above the table) and two 6 mm lugs carry the bottom wheel on an
  M5 × 40 screw. The eccentric hex is between the outer lug and the wheel. The 8 mm wrench reaches it
  from the back. The inner lug hole is as large as the eccentric hole, so the axle can move.
- All parts over the rail and outside the side plate have 45° undersides. The top wheels sit in
  wells with pointed roofs. Key holes through the shoulder reach the top bolt heads.
- The belt is 8 mm higher (z = 80 mm): the belt slots pass over the key holes. The motor and idler
  platforms are 8 mm higher.
- The Y endstop switch hangs on the inner face of the bracket arm. The front edge of the side plate
  pushes the lever.
- Each Y bracket has two M5 screws in T-nuts in the one bar slot, and two 10.5 mm holes over the bar
  screw heads. The base housing moves to x = 74 mm, and its two M5 screws go into the one slot.
- `fit_wheel`: a 12 mm slice of the carriage, with the top wheel hole and the two lug holes.
- Camera pole: `mast_foot` holds the pole in a 43 mm socket behind the centre of the back bar. The
  foot stands on the table. An M6 × 16 screw goes up into the pole thread. A split collar with one M3
  screw takes up the play. `camera_mount` goes away.
- Recommendation: move the two back feet to the back ends of the rails (centre 497 mm or more from
  the front), or put printed feet under the back bar ends. Then the Y travel is 397 mm again.

The fit check proves: each Y wheel touches the two flanks of its slot with a 0.1 mm preload (0.87 mm³)
and nothing else touches the rail. The carriage is 5.0 mm above the table. The wrench space and the
key paths are clear. The under-rail lug and the bolt head are clear of the pen carriage, the X plate
and the pen at both X ends: the X travel does not change. The Y brackets are clear of the bar screw
heads. The pole foot is clear of the brackets, the motors, the bar screw heads and the base housing.

| Feet | Gantry y | Y travel | Y stop |
|---|---|---|---|
| At the photo positions (37.5 mm from each end) | 73.5 to 454.5 | 381.0 mm | bottom wheel at the back foot |
| Under the outer bottom slot | 73.5 to 455.0 | 381.5 mm | the web at the back foot |
| Back feet at y = 500 mm (bar end) | 73.5 to 470.4 | 397.0 mm | top wheel at the back bar |

The eccentric spacer of a bottom wheel needs 0.1 mm of its 0.8 mm range at the design position. The
rest takes up the errors of the wheel size and of `WHEEL_OFF`.

Slice comparison (the lean profile):

| Change | Print time | Filament | Result |
|---|---|---|---|
| Left Y carriage: plate on 3 side wheels | 4 h 11 min | 75 g | before |
| Left Y carriage: the C shape | 4 h 10 min | 73 g | **applied** |
| Y motor bracket on a 2020 bar, T-nut screws at x = 45 and 60 mm | 1 h 28 min | 25 g | |
| The same, T-nut screws at x = 41 and 53 mm, the wall 8 mm shorter | 1 h 24 min | 24 g | **applied** (idler bracket: 1 h 12 min to 1 h 09 min, 21 g to 20 g) |
| Camera: mast foot and camera mount for a 2040 upright | 2 h 14 min | 38 g | before |
| Camera: pole foot | 1 h 31 min | 25 g | **applied** |

| | Before | Now |
|---|---|---|
| Main build with the camera part | 15 parts, 20 h 15 min, 359 g, $7.18 | 14 parts, 19 h 53 min, 347 g, $6.94 |
| Main build without the camera part | 13 parts, 18 h 07 min, 323 g, $6.46 | 13 parts, 18 h 22 min, 322 g, $6.44 |
| Fit tests | 51 min, 14 g | 1 h 13 min, 18 g |
| Pen travel (model) | 245.9 × 397.0 mm | 245.9 × 381.0 mm with the feet at the photo positions; 245.9 × 397.0 mm with the back feet at the rail ends |

The brackets are 4 × 3 g heavier than before: the 2020 bars put the screws beside the bar screw heads.
The fit wheel slice is taller than the old strip: it holds a top wheel and the bottom wheel.

New hardware: 2 M5 × 40 screws and 6 M5 washers for the bottom wheels (the 4 top wheels keep their
M5 × 30 screws). 20 M5 drop-in T-nuts for 2020 (16 and 4 spare). For the camera pole: 1 M6 × 16
screw, 1 M3 × 16 screw and an M3 nut.

Open points: measure the feet, the bar height and the bar screw heads (`MEASURE.md`, items 1 to 4),
the pole thread depth and the lens height (items 5 and 6).

## Printed feet and the fasteners in the model

**Removed later.** The machine already has rubber feet, so the printed feet are gone again. The four
rubber feet stay under the long rails, as modelled before. The back feet stop the bottom Y wheels:
the Y travel is 381.0 mm in the model (firmware 380). The 8 feet screws and 8 T-nuts are out of the
model and the BOM. The fastener work below stays.

The stock rubber feet stand under the 2040 sides, 37.5 mm from each end. The bottom wheel of each
Y carriage and its lugs run under the rail, so the back feet stopped the gantry: 381 mm of Y travel.

Decision: four printed feet under the ends of the cross bars. The carriages never reach the bars:
the top wheels stop at the back bar and the slider stops at the front bar. So the feet are out of
the path, and the Y travel is 397.0 mm again (model). The firmware uses 395 mm.

- Each foot is a 44 × 20 mm block under a bar end, as tall as the stock feet (`FOOT_H` = 37 mm, an
  estimate). The bars and the rails stay at the same height. The other parts use the slot heights.
- Two M5 × 12 screws go up through 30 mm counterbores into T-nuts in the bottom slot of the bar. Two
  screws stop the foot from turning. A key in the slot would need a support: the foot prints upside
  down.
- A 12.7 mm rubber pad sits in a 2 mm recess. Upside down, the recess and the counterbores open
  to the top. No support. The pad thickness is an estimate (`MEASURE.md`, item 2).
- One symmetric part fits all four corners.
- At the ends of the travel the gantry is 41 mm from the front feet and 17 mm from the back feet.

Slice comparison (the lean profile, one foot):

| Foot | Print time | Filament | Result |
|---|---|---|---|
| Corner block, 40 × 34 mm, under the bar end and the rail end, one screw in the bar, one in the rail | 1 h 12 min | 21 g | |
| The same, 10 % infill | 1 h 07 min | 20 g | |
| The same, 2 walls | 1 h 04 min | 18 g | |
| Bar block, 44 × 20 mm, two screws in the bar | 51 min | 15 g | **applied** |
| The same, 10 % infill | 48 min | 14 g | not worth the weaker part |

| | Before | Now |
|---|---|---|
| Main build with the camera part | 14 parts, 19 h 53 min, 347 g, $6.94 | 18 parts, 23 h 16 min, 407 g, $8.14 |
| Main build without the camera part | 13 parts, 18 h 22 min, 322 g, $6.44 | 17 parts, 21 h 45 min, 382 g, $7.64 |
| Pen travel (model) | 245.9 × 381.0 mm | 245.9 × 397.0 mm |

The fasteners are now context in the model (`fasteners.py`): 130 items. Each moves with its group
(static, gantry, carriage, pen). The fit check tests them at 9 gantry and X plate positions. The
length check found four errors:

- The M5 screws into T-nuts through 6 mm walls (brackets, beam, pole foot) were M5 × 10. They left
  2.2 mm of thread in the T-nut. Now M5 × 12: 4 mm of thread, the tip 6 mm into a 6.3 mm slot.
- The housing screws were M5 × 10 button heads through a 3 mm floor. The tip went 7 mm into the
  slot and hit the core. Now M5 × 8: 3.2 mm of thread.
- The beam T-nut screw clamps a 6 mm tower wall. With M5 × 12 the tip reached the core. A washer
  under the head fixes it.
- The endstop screws were M2 × 8 through a 6.4 mm switch body: 1.6 mm of thread. Now M2 × 10.

The model had the pen clamp screw 46 mm too high, above the slider. It is now in the slider. The
BOM did not list the three 6 mm idler spacers and the washer of the X idler. They are now in M27.

The T-nut model tapers at 45 degrees, as the slot cavity does. A box T-nut in the bottom slot met a
box T-nut in the face slot at the bar corner. Real drop-in T-nuts do not.

New hardware: 8 more T-nuts (28 in all, 4 spare), 8 M5 × 12 screws and 4 rubber pads for the feet,
3 M5 × 6 mm spacers, 3 more M5 washers. Open points: the bar height, the pads, the stock feet
fixing, and the slot and T-nut sizes (`MEASURE.md`, items 1 to 3 and 34 to 38).

## Belt ends with crimp clips

The belt ends were held only by friction in printed slots. Now each end folds back on itself, and a
metal crimp clip closes it. Each belt is crimped to its length on the bench, with both clips
on, and then dropped in. Each clip sits in a pocket behind an end wall. The belt lies in a slit in
the wall. The clip is larger than the slit, so the pull of the belt presses the clip on the wall.

- Clip: the OpenBuilds style "belt clamp, crimp style" for 6 mm GT2 belt, stamped steel, listed as
  18 × 7 × 8 mm folded. The listings do not say which size is which. The pockets are
  18.6 × 8.6 × 8.6 mm, so a clip fits either way. The model uses 18 × 8 × 5 mm for a crimped clip
  (ESTIMATE, `MEASURE.md` item 39).
- Y carriages: a 6 mm end wall at each end of the belt block. The slit (1.7 mm) opens to the top.
  The pocket behind it (21.6 mm) opens to the outer side; its roof rises at 45 degrees, so it prints
  with no support. The X motor wall stands over the front of the carriage, so the front end wall
  now stands 6 mm in front of the carriage. Its underside rises at 45 degrees, 0.75 mm over the Y
  switch arm. The clip bears on the wall on both sides of the slit.
- Pen carriage: the clamp block is now 15 mm tall (z 57 to 72), was 8.5 mm. Each end has a 4 mm wall.
  The slit and the pocket open to the front, so the part prints with them open to the top. A 0.6 mm
  floor stays at the back.
- Tension: the Y idlers keep their slots (5 mm each way). The X idler axle now runs in a slot in the
  wall and the post of the right carriage, 5 mm each way. The axle moved 3 mm outward (x = 383 mm
  at the middle of the slot), and the post is 22 mm wide, so the slot fits. The wall and the post
  are 4 mm taller for the pointed roof of the slot. Each slot takes up 10 mm of belt each way: a hand
  crimp error (about 2 mm) and the stretch of the belt.
- Belt lengths between the middles of the folds, with the idlers at the middle of their slots:
  Y 1145.7 mm (left and right), X 737.4 mm. `stl/frame.json` has them under "belt_lengths".
- The fit check has the clips and the folded belt ends. They move with the gantry and the X
  carriage. They are clear of the wheels, the frame, the motors, the switches and the housings over
  the whole travel. The X idler is clear of the carriage at both ends of its slot.
- The simulator gets `stl/sim2/belt_clips_gantry.stl`, `belt_clips_carriage.stl` (brass colour)
  and `belt_ends_gantry.stl`, `belt_ends_carriage.stl`. The belt runs end at the faces of the belt
  blocks: "y_clamp" [-44, 36] from the carriage, "x_clamp" the ends of the clamp block.

## Y brackets on two faces

Each Y bracket held on two M5 screws, 12 mm apart, in one slot of one face of the bar. The pulley
or the idler is 26 mm beside the bar end and 23 to 43 mm above the screws. The belt pull tips the
bracket, and the pull and the motor torque twist it about the bar end.

- The wall screws now sit at x 41 and 64 mm (23 mm apart). The wall ends at x 70 mm, 4 mm from the
  base housing.
- A block on the top face of the bar end (x 0 to 42 mm) takes two more M5 screws into T-nuts in the
  top slot. The block top is the platform plane, so it prints on the bed. The screw heads sit on a
  45 degree cone at the bottom of each counterbore: no flat ceiling in print.
- The carriages never reach the bars. The head housing passes above the back block. The pen
  carriage stops 8 mm short of the front blocks.
- The bottom face of the bar was not used: a flange under the bar needs a support in the upside
  down print. The bar end face was not used: its thread is not measured (`MEASURE.md` item 40).
- The two gussets under each platform stay.

Bolt group check (`model.py`, simple model): 30 N in each belt run (60 N at the pulley or the
idler, at the belt height), and 0.4 Nm of motor torque. Tipping turns the bracket about an edge of
the bar, with a 10 mm arm for each screw. Twisting turns it about the bar end on a vertical axis.

| Bracket | Most loaded screw before | Now |
|---|---|---|
| Y motor bracket | 92 N (2 screws in one slot) | 56 N (4 screws on two faces) |
| Y idler bracket | 147 N (2 screws in one slot) | 52 N (4 screws on two faces) |

Slices of the changed parts (the lean profile):

| Part | Before | Now |
|---|---|---|
| `y_carriage_left` | 4 h 10 min, 73 g | 4 h 10 min, 73 g |
| `y_carriage_right` | 3 h 57 min, 69 g | 4 h 02 min, 70 g |
| `pen_carriage` | 2 h 03 min, 34 g | 2 h 07 min, 35 g |
| `y_motor_bracket_left` | 1 h 24 min, 24 g | 1 h 45 min, 30 g |
| `y_motor_bracket_right` | 1 h 25 min, 24 g | 1 h 45 min, 30 g |
| `y_idler_bracket_left` | 1 h 09 min, 20 g | 1 h 33 min, 26 g |
| `y_idler_bracket_right` | 1 h 09 min, 20 g | 1 h 32 min, 26 g |

Main build now: 14 parts, 21 h 30 min, 373 g, $7.46. Without the pole foot: 13 parts, 19 h 59 min, 348 g.

## Simplification: Y belts on the rails, Y motors on the carriages

The design is now much simpler and more compact. Each Y belt now lies fixed along its rail,
and each Y motor rides on its carriage with an omega drive (as on the OpenBuilds OX). The belt loops
and the four Y brackets outside the frame are gone.

- The belt runs over the inner top slot of each 2040 rail (the top wheels use the outer slot), teeth
  down, 1.5 mm inward of the slot centre (x = 31.5 mm). The V of the slot (model value) is narrower
  than the 6 mm belt. So the belt does not sit in the slot: it runs just over the rail top, a straight
  span from each clip to the nearest idler.
- The omega: a smooth idler (front), the motor pulley (180° of wrap), a smooth idler (back). The
  idlers are 12.9 mm each side of the pulley, 66.5 mm high, so their flanges clear the rail top and
  the belt stays under the X plate (its lower edge is at z 66.7 mm). The pulley axis is at z 88.75 mm.
- The drive mount (`y_drive_*`) screws to the back face of the tower with two M3 screws. It holds the
  motor face, the two idler bosses and an arm over the omega. It prints on the motor face. The motor
  sits behind the beam, over the frame (x 49 to 89 mm on the left). The head housing moved right to
  x = 92 mm.
- The idler axles are M5 × 20 button head screws that cut their own thread in the mount. Button
  heads, and the belt 1.5 mm inward, keep them clear of the bolt tips of the top wheels.
- The front base (`y_front_*`) holds a tensioner sled (`y_tensioner`) in a channel. An M3 × 20 screw
  through the front wall pulls the sled forward: 3.7 mm each way. The back anchor (`y_rear_anchor`)
  is fixed. Both use two M5 screws into T-nuts in the top slot of the bar. On a Y belt the tail of the
  fold lies under the belt, so the clip bears on a low wall and the belt runs over the wall. The belt
  drops in from the top.
- The Y endstop sits on the front base. The front face of the X motor wall of the carriage pushes
  its lever (2.4 mm before the front stop).
- Travel: 245.9 × 365.1 mm (was 245.9 × 381.0). The back idler of each omega stops at the back
  anchor. The back feet no longer limit it. Set the firmware to 245 × 364 mm.
- Moving mass: the gantry carries the two Y motors now, about 668 g more in all: 636 g of hardware (two motors at 280 g,
  ESTIMATE, the pulleys, the idlers, the screws) and 32 g for the two printed mounts.
- The Y motor cables move with the carriages. They run in loose loops to the base housing on the back
  bar. A 1 m stepper cable is in the BOM (M31) in case a stock cable is short (`MEASURE.md` item 42).
- Y belt length between the folds: 547.9 mm (was 1145.7 mm).

Slices (the lean profile):

| Part | Before | Now |
|---|---|---|
| `y_carriage_left` | 4 h 10 min, 73 g | 4 h 07 min, 73 g |
| `y_carriage_right` | 4 h 02 min, 70 g | 4 h 00 min, 70 g |
| `y_motor_bracket_left` | 1 h 45 min, 30 g | removed |
| `y_motor_bracket_right` | 1 h 45 min, 30 g | removed |
| `y_idler_bracket_left` | 1 h 33 min, 26 g | removed |
| `y_idler_bracket_right` | 1 h 32 min, 26 g | removed |
| `y_drive_left` | new | 1 h 05 min, 16 g |
| `y_drive_right` | new | 1 h 05 min, 16 g |
| `y_front_left` | new | 0 h 31 min, 8 g |
| `y_front_right` | new | 0 h 31 min, 8 g |
| `y_tensioner` × 2 | new | 0 h 25 min, 8 g |
| `y_rear_anchor` × 2 | new | 0 h 44 min, 12 g |

Main build now: 18 parts, 19 h 11 min, 329 g, $6.58 (was 14 parts, 21 h 30 min, 373 g, $7.46). Without the pole foot: 17 parts, 17 h 40 min, 304 g.

## Side wheels again, belt ends on the bar faces, moving cables

The side-mounted wheels come back. The stock feet stay under the rails, and the omega Y drive
stays.

Y carriage:

- A 6 mm plate over the rail top. Three V-wheels on vertical axles in the side slots of the flat
  2040 rail: two outside (22 mm in front of and behind the beam centre; the back one on the
  eccentric spacer), one inside at the beam centre. Nothing goes under the rail, so the feet do not
  limit the travel.
- The plate stays outside the belt (x ≤ 28 mm). A tongue crosses over the belt in front of the X
  plate (a channel with a 45° roof) and runs back under the X plate to the inner wheel. The X plate
  passes 2.6 mm over the tongue. The inner axle is a button head in a counterbore, with the nut under
  the wheel, so nothing stands on the tongue.
- One eccentric spacer per carriage (the stock parts have two free ones). The other two wheels sit
  on the 6 mm stock spacers.
- A notch with a 45° roof under the back of the tower clears the front omega idler.

Belt ends: the study of item 2 worked. The rail tops carry only the belt.

- Front: the tensioner base still sits on the front bar top, and it now reaches 21 mm in front of
  the bar. The sled moves 3.5 mm each way.
- Back: a block on the back face of the back bar, with two M5 screws into T-nuts in the face slot.
  A wide recess clears the bar end screw head (x = 30 mm on the left, 370 mm on the right), so one
  part fits both sides. The belt runs over the bar top into the block. The omega idlers roll over
  the bar top; the back idler stops 0.8 mm short of the block.
- Travel: 245.9 × 391.8 mm (was 245.9 × 365.1). At the front the carriage plate stops at the front
  base; at the back the drive mount stops at the back block. Set the firmware to 245 × 390 mm.

Moving cables: all moving wires are carried, low, with no tall part.

Y axis (the head harness, the Y1 and the Y2 motor cables):

| Option | Cost | Print | Stops travel | Wear and snag | Build | In the sim |
|---|---|---|---|---|---|---|
| **Openable drag chain 10 × 20 R28 beside the left rail, lower run on the table** | about $13 | anchor 39 min, 11 g | no | low: the chain takes the bending | easy: open the links, lay in the cables | a clear moving chain |
| Bridge (closed) drag chain 10 × 20 R28 | about $10 | the same | no | low | hard: the big harness plug does not pass, it must be unpinned | the same |
| Band on edge (steel or PET) beside the rail | about $7 | the same | no | medium: the 7 mm harness twists the band | medium: ties every 30 mm | a thin band |
| Spiral wrap loop on the table with clip points | about $5 | clips, 20 min | no | high: it drags on the table and catches the control box | easy | a loose loop, hard to draw |

X axis (the servo lead only):

| Option | Cost | Print | Stops travel | Wear and snag | Build | In the sim |
|---|---|---|---|---|---|---|
| **Band on edge behind the beam, rolling U loop (as in an inkjet printer)** | about $7 | bracket and clip 47 min, 13 g | no | low: nothing rubs, the band is light | easy: ties, two small parts | a thin U band |
| Small drag chain (7 × 7 or 10 × 10, R18) | about $10 | a 300 mm support shelf, 2 h or more | no, but the shelf is a tall part over the gantry | low | hard: no room low (the X plate wheels sweep the beam top, the X belt loop the front) | a chain |
| Braided sleeve service loop, low | about $5 | none | no | medium: the loop sags onto the head housing and the Y motors | easy | a loose loop |
| Spiral wrap with clip points | about $3 | clips, 15 min | no | medium to high | easy | a loose loop |

Recommended and modelled: the openable drag chain for Y, the band for X. The chain anchor sits at the back left
corner, beside the left rail; its arm goes under the rail into the bottom outer slot (two M5 into T-nuts). The values are in
`shape.py` (`YCH_*`, `XST_*`), so another chain or band is a change of numbers. The fit check moves
the chain over the Y travel and the band over the X travel: they touch nothing but their mounts.
The control box moved 10 mm to the left in the images (its right side at x = -70 mm).

Slices (the lean profile; × 2 rows are for both parts):

| Part | Before | Now |
|---|---|---|
| `y_carriage_left` | 4 h 07 min, 73 g | 4 h 05 min, 73 g |
| `y_carriage_right` | 4 h 00 min, 70 g | 3 h 52 min, 69 g |
| `y_front_left` | 31 min, 8 g | 34 min, 8 g |
| `y_front_right` | 31 min, 8 g | 33 min, 9 g |
| `y_tensioner` × 2 | 25 min, 8 g | 24 min, 6 g |
| `y_rear_anchor` × 2 | 44 min, 12 g | 1 h 18 min, 22 g |
| `y_chain_anchor` | new | 39 min, 11 g |
| `x_strip_bracket` | new | 33 min, 9 g |
| `x_strip_clip` | new | 14 min, 4 g |

Main build now: 21 parts, 21 h 05 min, 361 g, $7.22 (was 18 parts, 19 h 11 min, 329 g, $6.58). Without the pole foot: 20 parts, 19 h 34 min, 336 g, $6.72 (was 17 parts, 17 h 40 min, 304 g, $6.08).

## Feet, design language, one-piece Y carriages, real hardware, joint audit (2026-11-09)

| Change | Reason |
|---|---|
| The stock rubber feet are in the model, the fit check and the sim (28 × 37 mm, ESTIMATE) | the feet were not in the model |
| One finish for all printed parts: 2 mm corner radius, 0.6 mm top chamfer, one accent colour (orange); optional end caps and a servo cover | a well designed product look |
| One-piece omega Y carriage on each side: the drive mount is gone; 2 top motor screws; 1 beam screw | the Y carriages were too complex |
| Heat-set inserts: a long M5 insert for the front outer wheel axle, M3 inserts for the Y endstop boards and the board posts | inserts are allowed where they simplify |
| Real hardware shapes (ISO 4762, ISO 7380, ISO 4032/7040, roll-in T-nuts, knurled inserts, eccentric spacer), GT2 pulleys and idlers with teeth, the Creality V-wheel with 625 bearings | real detail in the model |
| The pitch line is corrected: pitch diameter 12.73 mm (20 teeth); the belt centre 6.06 mm from the pulley axis | the drive gears must be correct; 80 steps/mm is unchanged |
| X idler fork with two cheeks; the tension screw pulls the fork; no slot in the wall | the idler bolt had too little material round it |
| The endstops are the Creality boards (20 × 20 mm); strikers hit the lever past the board corner, 1.5 mm past the click | the endstops were not to spec |
| The joint audit (hardware/audit) gates the build; the hole check in model.py | material round every hole |
| The pen changer rack at the front (6 bins), the dock replaces the slider | 6 bins fit with the stock Y home |

Design goals, scored (1 = poor, 5 = good):

| Assembly | Quality | Few visible parts | Maintenance | Quiet |
|---|---|---|---|---|
| Y carriages (one piece) | 4: stiff, audit passes but the inner wheel axle (boss 5 mm) | 3: wheel nuts and the eccentric show | 4: eccentric and Y tension reachable; wheels replaceable | 4: wheel preload by eccentric |
| X idler fork | 5: two supports, audit passes | 3 | 5: tension screw from outside | 4 |
| Endstops | 4: firm square hit, 1.5 mm overtravel | 3: boards visible | 4: 2 screws each | 5 |
| Pen carriage | 3: head screw T1 breaks into the clip pocket (open item) | 3 | 4 | 4 |
| Frame | 4 | 4: end caps, rubber feet | 5 | 4: rubber feet |

Open items (audit FAIL): the inner Y wheel axle boss (5 mm, the stock X plate is over it), the head
screw T1 of the pen carriage (it meets the right clip pocket), the upper X endstop standoff (2.5 mm of
material; the plug pins limit it). The printed X carriage (next step) removes the first two.

## Printed X carriage, the stock X belt path, fixed Y motors (2026-11-09)

| Change | Reason |
|---|---|
| The X belt in the beam slots: the stock CR-10 path (the pulley axis along Y on the beam centre line, past the left beam end; one run in the top slot channel, one in the bottom slot channel; the X plate clamps the bottom run) | the X belt runs in the beam channel, and the X axis keeps the stock CR-10 V3 layout with printed plates and a printed carriage. The old belt loop in front of the beam hit the parked tall tools at Y 0. |
| A printed X plate replaces the stock Creality plate; the pen carriage stays a separate part on the same 4 holes | a printed X carriage replaces the stock plate, and the X belt runs in the beam slot |
| Fixed Y motors: the motor behind the back bar, a toothed idler in a fork in front of the front bar; the carriage clamps the upper run of a belt loop over the rail | fixed Y motors keep the X axis light; the 2020 bars close the rail slot ends, and the belt cannot go through them without cutting the metal |
| The rails stay flat between the bars (option 1 of 3) | rails on edge or on top of the bars would hide the Y belt, but they cost frame stiffness (one stock screw or none per corner), +20 mm of gantry height through the whole pen changer, moved feet, and the same slot-lip chafe as the stock X |

The stock X path, read from the Creality CR-10 STEP model:
the 2GT pulley sits 12 to 27 mm past the beam end, its axis along the depth of the beam, on the beam centre height and the
beam centre plane; the motor stands behind the beam. The stock plate has two bent tabs under the beam, at its two ends:
the belt ends leave the bottom slot there. The return run passes in the top slot under the top wheels.

X layouts (FEA: `audit/xlayouts.py`, the plate and the pen carriage as one solid, fixed at the three wheel axles;
operating loads: the head inertia at the firmware acceleration and 1 N of pen drag in X and in Y at the dock rail):

| Layout | Rail deflection, operating / worst | Parts | Fasteners | Print | Notes |
|---|---|---|---|---|---|
| **A: printed X plate + pen carriage, top wheels 46.5 mm apart in the FEA, 47.5 mm in the final part (chosen)** | 2.5 µm / 25 µm | 2 | 4 M3 head screws | 4 h 41 min, 85 g (plate 2 h 34 min 48 g, pen carriage 2 h 07 min 37 g) | the plate prints upright (the wheel loads in the layers of the bosses), the pen carriage on its back face; the pen changer interfaces stay as they are |
| B: as A, top wheels 70 mm apart | 2.5 µm / 24 µm | 2 | 4 | about the same | the wider base changes the rail deflection by 1 %; the plate needs more room at the towers |
| C: one piece (plate and pen carriage merged) | 2.5 µm / 25 µm (the same solid) | 1 | 0 | 4 h 32 min, 82 g, before the supports it needs | it prints upright only: the servo pocket, the tower and the shelf of the pen lift then need supports or a redesign, and the pen changer interfaces move |

The limit is 50 µm. All three layouts are far under it, so the deflection does not decide. A wins on print quality (no
supports, the layers along the loads in each part), on the pen changer interfaces (unchanged), and on maintenance (the
pen carriage comes off with 4 screws). C saves the 4 M3 screws only.

Moving mass of the X carriage: the printed X plate is 48 g (slicer). The stock aluminium plate was about 60 g (ESTIMATE).
The pen carriage is 37 g (was 44 g). The X carriage is about 19 g lighter. The gantry is 628 g lighter: the two Y
motors (280 g each, ESTIMATE), their pulleys, the idlers and the screws do not ride on it now.

Endstop and travel: the X trigger lug and the Y strikers stay 1.5 mm past the click at the hard stops. Home is unchanged
(gantry y 73.94, X plate x 70.42), so the bins of the pen changer do not move. Pen travel 245.9 × 395.1 mm (the inner Y
wheel stops at the back bar): keep the firmware at 245 × 390 mm.

Clearance with the parked tall tools (all 6 bins, tool_head_tall with a 160 mm pen): the gantry parts (beam, Y carriages,
X motor, X idler fork, both belts, the head housing, the band and its bracket, the drag chain, the end caps) clear the
tools at every Y from 0. The beam face is 0.74 mm from the tools at Y 0. The X carriage itself (plate, pen carriage,
servo, wheels) clears all parked tools at every X from Y 42.0 mm; below that it is over the rack only to pick or park.

Audit: `AUDIT: OK` with `--gate` (0 gate FAILs). The FEA now runs on the X plate, both Y carriages, both idler forks
and the Y motor bracket. X plate: 4.9 MPa von Mises (SF 10), 0.6 µm at the pen carriage seats (2 µm worst case). Eight
FAILs stay outside the gate. Each one is a tool or torque note, not a strength fault:

- Key lines (4): the X idler axle head (turn the nut, hold the head), the lower X switch screw (fit it before the
  carriage goes on the rail), and one motor screw in each Y bracket (fit it before the bracket goes on the bar).
- Head preload (4): the M3 heads of the right Y motor bracket bear on PLA at 93 MPa at full snug torque (SF 0.5). Put an
  M3 washer under each head, or tighten by feel. The left bracket has the same joint.

Slices (5 walls, 40 % infill for the loaded parts):

| Part | Before | After |
|---|---|---|
| X plate (new; the stock plate was aluminium) | — | 2 h 34 min, 48 g |
| Pen carriage | 2 h 28 min, 44 g | 2 h 07 min, 37 g |
| Y carriage, left | 7 h 33 min, 137 g | 6 h 55 min, 124 g |
| Y carriage, right | 6 h 56 min, 127 g | 5 h 03 min, 92 g |
| Y front bases (2) | 1 h 10 min, 18 g | 1 h 24 min, 24 g |
| Y tensioners (2) / Y idler forks (2) | 0 h 24 min, 6 g | 0 h 51 min, 14 g |
| Y rear anchors (2) / Y motor brackets (2) | 2 h 01 min, 34 g | 2 h 16 min, 38 g |
| Y idler brackets (2, new) | — | 1 h 44 min, 32 g |
| X idler fork | 0 h 31 min, 9 g | 0 h 25 min, 7 g |
| **These parts** | **21 h 04 min, 375 g** | **23 h 19 min, 416 g** |

The new parts add 2 h 15 min and 41 g. The printed X plate alone is 2 h 34 min and 48 g: without it the set is 19 min
and 7 g lighter than before. The whole stock-controller build (no fit tests, with the pen changer dock of the other
work) is now 28 parts in 24 jobs, 30 h 34 min, 546 g ($10.92). Before it was 25 parts, 27 h 52 min, 498 g.

Design goals, scored (1 = poor, 5 = good):

| Assembly | Quality | Few visible parts | Maintenance | Quiet |
|---|---|---|---|---|
| X plate and pen carriage | 5: printed bosses of 12 mm or more, the rail deflection 2.5 µm, the T1 FAIL gone | 4: the belt in the beam, the clips behind the plate under the beam | 5: the eccentric from above; the pen carriage on 4 screws | 4: wheel preload by eccentric; the belt passes the 6.2 mm slot opening at the clamps (stock) |
| X drive (stock path) | 4: the stock geometry, 0.54 mm from the wheel tips (ESTIMATE) | 5: no belt in front of the beam | 5: the tension screw from outside the right end | 4 |
| Y drive (fixed motors) | 5: the gantry 630 g lighter, the motor cables static | 3: the belt runs over the rail top; the motors stand 20 mm outside the frame line at the back | 5: the tension screw from the front | 5: nothing rubs |
| Y carriages | 5: all three axle supports pass the audit (the inner boss 12 mm) | 4 | 4 | 4 |

## Simplification: flat Y plates, bare boards, servo loom (2026-11-10)

The pen changer is removed, and the whole build is simplified. The build uses no stock plates. The printed plates keep
the stock layouts, without the extra mounting points of the stock plates. Each Y carriage is a flat plate, and the Y travel
stays at 390 mm. The X band held up only one wire, so it is removed. The servo lead runs in a 1/2 inch split wire loom.

Removed from the model, the tooling and the guide: the pen changer (`hardware/penchanger` is removed), the Pico W
control pod, both board housings, the servo cover, the four bar end caps, the pen gauge, the X band and its two holders.

Findings:

- The stock CR-10 Z carriage plate (Creality CR-10 STEP) is an aluminium plate of 60 × 58.5 × 5.1 mm with R3 corners,
  three wheel holes in a triangle and many holes this plotter does not use. The Y carriage keeps that form: a flat
  6 mm plate on three wheels, with only the features in use.
- The beam must stay at its height (its bottom 24.5 mm over the plate top): the X plate, the pen lift and the X belt
  path depend on it. A saddle under the beam end holds that height. The tall tower and the front wall are gone.
- The X endstop board went from a 132 mm high wall to a wall in front of the beam end (top at z 110). The board faces the
  front. A trigger lug at the bottom left of the X plate reaches forward to the lever tip. Next to the plate face the
  lug is 1 mm narrower, so it passes the board edge; its left part has a 45 degree underside in X and in Y (the first
  slice showed 0.27 g of support there).
- The two board standoffs of the X endstop are one pillar from the plate (the first slice with two pointed bosses
  showed 0.39 g of support under them). A pocket with a pointed roof in the pillar clears the plug pins under the board.
- The first right plate had the seat of the X idler fork joined to the plate edge only: the FEA gave 207 MPa at the
  tension screw. The seat now reaches in to the saddle. Over the eccentric boss it leaves a 19 mm round space for the
  nyloc nut and the wrench (a seat that covered the boss failed the axle hole check of the audit).
- The first back wall stood 3.2 mm over the M5 beam screw hole; the audit wants 5 mm of material. Its top is now 0.2 mm
  under the beam top. The X motor wall now covers the whole motor face, for more material over the top M3 holes.
- The export check reported that the X lever did not reach the trigger lug. With the new board place and the new lug
  the check passes: the lug is 1.5 mm past the click at the hard stop.
- The head board stands bare on the back face of the beam. Its two cable ties go round the beam, through the top and
  the bottom slots and over the front face. The X plate and its wheels pass that place (the head board is at x 96 to
  143; the X plate travels from x 28.5). The ties are in the path of the X plate. This is open: see the end of this
  section.
- The servo loom: the model hangs it as a catenary of fixed length between the tie on the X plate and the tie at the
  head harness cable. The loop is 189 mm (the longest chord over the X travel, 164 mm, and 25 mm of slack); the whole loom is
  about 295 mm. Its lowest point: z 56.5 at X 0, z 46.8 at mid X, z 94.2 at full X, and z 41.1 at the deepest sag (X plate
  x 152.5, where the moving end is over the fixed end). The paper is at z 0: the loom stays 41 mm or more above it. The
  nearest rigid parts are the X plate at the tie (0.3 mm), the head board plug (8.0 mm) and an X wheel (8.7 mm). It
  touches only soft parts: the head harness cable at the fixed tie and the wire bends of the XH plugs. At the back of the
  Y travel (gantry y 469) the loop lies on the top of the back bar (z 57) at all X positions but full X. A real loom is
  stiffer than a catenary and sags less.

Decisions:

| Decision | Why |
|---|---|
| Flat Y plates with the stock wheel layout (outer wheels 44 mm apart, the inner wheel 18 mm behind the beam) | the flat plate is the simplest choice; the 390 mm Y travel stays; the home and the travel do not change |
| A saddle and a short back wall hold the beam; the inner face of the saddle is the X hard stop | the beam height is fixed by the X plate and the pen lift |
| The X endstop board on a wall in front of the beam end, facing the front; the trigger lug at the bottom left of the X plate | the wall is 22 mm lower than before, and the X home does not change |
| The X motor is a 42-34 (213.4 g, measured); the Y motors are 42-40 (286.7 g, measured) | two 42-34 and three 42-40 are on hand; the X motor rides on the gantry |
| The servo lead runs in the 1/2 inch split loom, in a free loop behind the beam, with one cable tie at each end | a loom is simpler than the X band and its holders |

Slices (CuraEngine, the project profiles):

| Part | Before (2026-11-10, tower carriages) | After (flat plates) |
|---|---|---|
| Y carriage, left | 5 h 30 min, 97 g | 3 h 50 min, 67 g |
| Y carriage, right | 4 h 26 min, 80 g | 3 h 30 min, 63 g |
| X plate (new lug, tie slot) | 2 h 34 min, 48 g | 2 h 32 min, 47 g |
| **Main build (no fit tests)** | **16 parts, 24 h 23 min, 431 g, $8.62** | **16 parts, 21 h 45 min, 383 g, $7.66** |

Before the whole simplification (HEAD, with the pen changer dock, the housings, the covers and the band holders) the
main build was 27 parts, 30 h 28 min, 544 g ($10.88). The fit tests stay at 49 min and 14 g.

Checks: `make.sh` exit 0. Fit check `RESULT: OK` (travel 245.9 × 395.1 mm, home unchanged at gantry y 73.94 and X plate x
70.42; both triggers 1.5 mm past the click), mesh check clean, export check OK (the X lever reaches the trigger lug),
`AUDIT: OK` with `--gate` (472 PASS, 67 WARN, 6 FAIL outside the gate: the Y motor brackets, as before), support check 0 g
for all parts (the chain anchor shows 0.02 g, under the 0.1 g limit). Firmware: TravelX 245, TravelY 390, 80 steps/mm
stay.

Open:

- The cable ties of the head board are in the path of the X plate (see above). A tie round the beam cannot stay there.
  Options: M3 drop-in T-nuts in the back slot of the beam with M3 screws through the board and the standoffs, or a
  board place outside the X travel. The choice is open.
