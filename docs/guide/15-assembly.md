# Assembly

This chapter takes you from the bare CR-10 base frame to the first plot. The steps follow
`hardware/penplotter-build-guide.pdf`, which has a full page and a large image for each step.

Before you start:

- Print the parts (`05-parts-and-cost`). Print the three fit tests first.
- Take the measurements in `hardware/MEASURE.md`. Measure the feet first: their height moves all the other parts.
- Before you take the CR-10 apart, check the X belt on the stock machine (`hardware/MEASURE.md`, item 61). Count the plain wheel spacers (item 62).
- Measure the head harness and the drag chain before you print the chain anchor (`hardware/MEASURE.md`, items 46 and 47).
- Keep the control box off until the wiring checks (`20-electronics-and-wiring`).

You need hex keys (2.5, 3, 4 and 5 mm), the 8 mm wrench for the eccentric spacers, scissors for
the belts, calipers, a tape measure, a meter, and a soldering iron with an M3 heat-set insert
tip. `05-parts-and-cost` lists the fasteners.

No step cuts or drills the metal of the frame.

## The wheel adjustment

The Y carriages and the X plate run on stock V-wheels. One wheel of each carriage turns on an
eccentric spacer. Turn the eccentric with the 8 mm wrench to set the preload:

1. Turn the eccentric until the wheels touch both flanks of their slots.
2. Rock the carriage by hand. Turn the eccentric a little more until the play is gone.
3. Push the carriage along its frame rail or beam. It must roll freely over the full length.
4. Hold the eccentric with the wrench and tighten its nut.

Stop when the play is gone. Too much preload makes flat spots on the wheels.

## 1. Fit tests

![The wheel fit test](../../hardware/build/img/part_fit_wheel-light.png)

1. Slide the fit slider onto the fit rail. It must slide by its weight, with no side play.
2. Push an M3 nut into the slot in the top of the fit slider. Put a pen in the bore. Turn an M3 × 20 screw in until it holds the pen.
3. Put a wheel under the eccentric hole of the fit wheel strip: an M5 × 30 screw from below, the wheel, an eccentric spacer, the strip, a nyloc nut.
4. Put a wheel under the counterbored hole: an M5 × 30 button head screw from the top, the strip, a 6 mm spacer, the wheel, a nyloc nut.
5. Lay the strip across the end of a frame rail, the wheels in the two side slots.
6. Turn the eccentric spacer. Both wheels must grip the slots before the eccentric reaches its end.

If the slider is tight or loose, change `DT_CLR` in `hardware/shape.py` by 0.05 mm. If the
eccentric cannot reach, change `WHEEL_OFF` by 0.2 mm. If the eccentric spacer is loose or tight in
its hole, change `ECC_HOLE`. Run `hardware/make.sh` and print the fit tests again.

## 2. Heat-set inserts

Put all the inserts in first, before the assembly starts. The pictures show each insert above its hole.

![The M3 inserts in the left Y carriage](../../hardware/build/img/ins_m3_ycar-light.png)

![The M3 inserts in the X plate](../../hardware/build/img/ins_m3_xplate-light.png)

![The M3 inserts in the left front base](../../hardware/build/img/ins_m3_yfront-light.png)

You need the 2 Y carriages, the X plate, the 2 front bases and 12 M3 inserts.

1. Set the iron to 220 °C with the M3 tip. Let the tip get hot.
2. Left Y carriage: find the two standoffs on the front face of the X endstop wall (first picture). Press an insert into each, from the front.
3. Y carriages: find the ledge in each of the two clamp pockets. Press an insert into each ledge, from the top.
4. X plate: turn the plate until the hole under one clamp points straight up. Press an insert down through that hole into the ledge (second picture). Do the same at the other clamp.
5. Front bases: press an insert into each of the two standoffs on the top of each base, from the top (third picture).
6. Push each insert until its top is flush with the standoff or the ledge. Let the parts cool.
7. Turn an M3 × 8 screw in and out once to check each endstop insert. Turn an M3 × 10 screw in and out once to check each jaw insert.

The M3 inserts hold the three endstop boards and the six belt jaws. The left Y carriage has 4 M3
inserts, the right Y carriage 2, the X plate 2 and each front base 2. The right front base is the
mirror image of the left base. No wheel axle goes into an insert.

## 3. Wheels on the Y carriages

![The wheels on the Y carriages](../../hardware/build/img/ywheel-light.png)

You need the 2 Y carriages, 6 V-wheels, 4 stock 6 mm spacers, 2 eccentric spacers, 6 × M5 × 35
socket head screws and 6 nyloc nuts.

1. Front outer wheel: put an M5 × 35 screw up through a wheel, a 6 mm spacer and the front boss. Put a nyloc nut on top of the boss.
2. Back outer wheel: put an M5 × 35 screw up through a wheel and an eccentric spacer into the back hole. The hex is between the wheel and the plate. Put a nyloc nut on top.
3. Inner wheel: put an M5 × 35 screw down through the 12 mm boss behind the beam. Do not put the spacer, the wheel and the nut on yet.
4. Tighten the front nut and the back nut until the wheels turn freely with no wobble.

Each carriage is a flat plate, in the form of the stock CR-10 Z carriage plate. The left carriage
has the X motor wall behind the beam end. The right carriage has the seat of the X idler fork.
The inner wheel goes on when the carriage is on the rail.

## 4. Y carriages on the frame rails

![The Y carriages on the frame rails](../../hardware/build/img/ywheel_on-light.png)

1. Stand the frame on the table, feet down.
2. Set each carriage on its rail from above: the plate on the rail top, the two outer wheels in the outer side slot.
3. Under the inner boss, put a 6 mm spacer, the inner wheel and a nyloc nut on the inner screw. The wheel runs in the inner side slot.
4. Do the wheel adjustment on each carriage. Turn the eccentric hex from outside the frame.
5. Measure the two diagonals of the frame. Make them equal, then tighten the bar screws.

## 5. Y motors behind the back bar

![The Y motor bracket](../../hardware/build/img/ydrive-light.png)

You need the 2 Y motor brackets, the 2 Y motors (42-40), 2 GT2 pulleys, 8 M3 × 10 screws,
4 M5 × 12 screws and 4 T-nuts.

1. Hold a motor on the outer face of each bracket plate, the shaft to the inside, the socket up. Put four M3 × 10 screws from the inside into the motor. Put an M3 washer under each head, or tighten by feel: the heads bear on PLA.
2. Put a GT2 pulley on each shaft, the hub to the inside. Line up its teeth with the inner top slot of the rail (31.5 mm from the outer face of the side). Tighten the set screws on the flat of the shaft.
3. Turn two M5 drop-in T-nuts into the slot in the back face of the back bar, near each end.
4. Hold each bracket on the back face of the back bar, the recess over the head of the bar end screw. Screw it on with two M5 × 12 screws.
5. Plug in each motor cable. It runs on the table behind the frame to the base board. It does not move.

Fit the motor screw that the bar hides before the bracket goes on the bar.

## 6. Front bases, Y idlers and endstops

![The front base, the idler bracket and the endstop](../../hardware/build/img/yfront-light.png)

You need the 2 front bases, the 2 idler brackets, the 2 Y idler forks, 2 GT2 20T toothed idlers,
2 M5 × 30 screws with 4 small washers and 2 nyloc nuts, 2 M3 × 20 screws with 2 M3 nuts,
2 M3 × 12 screws, 4 M5 × 12 screws, 2 M5 × 12 countersunk screws, 6 T-nuts, 2 endstop boards and
4 M3 × 8 screws.

1. Push an M3 nut into the slot in the floor of each Y idler fork, from below. The slot is under the middle of the idler.
2. Hold an idler between the two cheeks, a washer on each side. Put the M5 × 30 screw through. Tighten the nyloc nut until the idler turns freely with no play.
3. Turn two M5 drop-in T-nuts into the top slot of the front bar, near each end. Screw a front base on each end with two M5 × 12 screws. Its two lips reach over the front of the bar.
4. Turn an M5 drop-in T-nut into the front face slot of the front bar, behind the ear of each idler bracket.
5. Hold an idler bracket on the front face of the front bar, under the two lips. Put an M5 × 12 countersunk screw through the ear into the T-nut. Tighten it.
6. Put an M3 × 12 screw down through the inner lip into the bracket.
7. Set each fork on the seat of the bracket, between the two guides. Put an M3 × 20 screw through the end wall from the front into the nut. Turn it two turns only.
8. Lay a Y endstop board on the two standoffs of each front base: the parts up, the plug to the front, the switch to the back. Screw it down with two M3 × 8 screws.
9. Plug in the endstop cable from the front. Leave 20 mm for the plug and the bend of the wires.

The ear has a hole from its front face for the screw head and the hex key. The belt tension
pushes the bracket back onto the bar face. The tension screw is on the belt centre line, under the
idler. It pulls in line with the belt, so the fork does not turn in its seat.

Home is the front left corner. A striker fin on the front edge of each carriage plate meets the
lever tip. At the front stop it is 1.5 mm past the click.

## 7. Base board

![The breakout boards](../../hardware/build/img/t_boards-light.png)

You need the base board, 2 nylon M3 standoffs (4 mm) and 2 cable ties.

1. Hold the base board on the back face of the back bar, 71 mm from the left end. Put a standoff under each of its two holes. The standoffs stand on the face of the bar, beside the slot.
2. Put a cable tie through each board hole and its standoff, round the bar. Pull the ties tight.
3. Plug in `Y` (Y1 motor, left), `Z1` (Y2 motor, right), `Y-` (Y1 endstop) and `Z-` (Y2 endstop). Leave `Z2` empty.
4. Push the big 2 × 8 plug into the header. The big plug points up.

The firmware maps `Z1` to the Y2 motor and `Z-` to the Y2 endstop. Lay the endstop wires in the
bottom slots of the rails and the back bar. Press the slot cover strips over them. The board
sizes are estimates. Measure the board first (`hardware/MEASURE.md`, items 30 to 33).

## 8. X plate and pen carriage

![The pen carriage on the printed X plate](../../hardware/build/img/mount-light.png)

You need the X plate, the pen carriage, the 3 V-wheels, 1 eccentric spacer, 2 stock 6 mm spacers,
1 M5 × 30 and 2 M5 × 35 button head screws, 3 nyloc nuts and 4 M3 × 12 screws.

1. Hold the pen carriage on the front face of the X plate. The three wheel bosses come through the round holes of the pen carriage.
2. Put four M3 × 12 screws from the back through the plate into the pen carriage (T1, T2, H1, H2). They cut their own thread. Do not overtighten them.
3. Top left wheel: from the back, an M5 × 30 screw through the wheel and a 6 mm spacer into the boss. Put a nyloc nut on the front.
4. Top right wheel: from the back, an M5 × 35 screw through the wheel and the eccentric spacer (the hex toward the plate) into the boss. Put a nyloc nut on the front. Leave it loose.
5. Bottom wheel: from the back, an M5 × 35 screw through the wheel, a 6 mm spacer and the bottom boss. Put a nyloc nut on the front.

The eccentric is on the top right wheel. You turn its hex from above.

## 9. Beam and X plate

![The beam and the X plate](../../hardware/build/img/t_beam-light.png)

You need the 2020 beam, the X plate with the pen carriage, 2 M5 × 12 screws with T-nuts, the X
endstop board and 2 M3 × 8 screws.

1. Slide the X plate onto the beam from one end. The top wheels go in the top slot, the bottom wheel in the bottom slot.
2. Turn the eccentric hex of the top right wheel from above until the plate has no play. It must still roll freely. Tighten its nut.
3. Turn an M5 drop-in T-nut into the back slot of the beam, 14 mm from each end.
4. Lay the beam on the two saddles, the pen carriage to the front. The beam ends touch the stops at the outer ends of the saddles.
5. Screw the beam to each carriage with one M5 × 12 screw, through the back wall of the saddle into the T-nut.
6. Hold the X endstop board on the two standoffs on the front of the X endstop wall of the left carriage. The parts face the front, the switch is on the right, and the plug is on the left.
7. Screw the board on with two M3 × 8 screws into the inserts.

The trigger lug at the bottom left of the X plate meets the lever tip. The inner face of the left
saddle is the hard stop of the X plate. Keep the top and the bottom slots of the beam free: the X
belt runs in them.

## 10. X motor

![The X motor](../../hardware/build/img/xmotor-light.png)

You need the X motor (a 42-34), a GT2 pulley and 3 M3 × 10 screws.

1. Put the GT2 pulley on the X motor shaft, the hub toward the motor. Do not tighten it yet.
2. Hold the motor behind the left beam end, the shaft to the front through the motor wall of the left carriage, the socket up.
3. Put three M3 × 10 screws from the front through the wall into the motor. The heads sit in counterbores. The hole over the beam end stays empty.
4. Slide the pulley along the shaft until its teeth are on the beam centre line, in line with the top and the bottom slots. Tighten the set screws.

The X motor rides on the gantry, so the shorter 42-34 keeps the moving mass low.

## 11. X idler fork

![The X idler fork](../../hardware/build/img/xfork-light.png)

1. Push an M3 nut into the slot in the floor of the fork, from below. The slot is under the middle of the idler.
2. Hold the 20T toothed idler between the two cheeks, a small washer on each side.
3. Put the M5 × 30 screw through the front cheek, the washer, the idler, the washer and the back cheek. Put the nyloc nut on the back. Hold the head and turn the nut until the idler turns freely with no play.
4. Set the fork in the seat past the right beam end, the floor on the seat.
5. Put the M3 × 20 screw through the end wall from the right side of the machine, into the nut in the fork. Turn it two turns only.

The fork slides 4 mm out and 2.5 mm in. You reach the tension screw from outside the right carriage.
The tension screw is on the belt centre line, under the idler.

## 12. Head board

![The breakout boards](../../hardware/build/img/t_boards-light.png)

You need the head board, 2 nylon M3 standoffs (4 mm) and 2 cable ties.

> **Caution:** The two cable ties go round the beam, through the top and the bottom slots and
> over the front face. The X plate and its wheels pass that place. This question is open:
> `hardware/REVIEW.md` lists the options. Check that the X plate passes the ties before you
> power the motors.

1. Hold the head board on the back face of the X beam, 96 mm from the left side of the frame, the big header up. Put a standoff under each of its two holes.
2. Put a cable tie through each board hole and its standoff, round the beam. Pull the ties tight.
3. Plug in `X` (X motor), `X-` (X endstop) and the servo pigtail on `BL_T`.
4. Push the big 2 × 15 plug into the header from the top. Keep the cable straight for 35 mm, then bend it back toward the control box.

The board sizes are estimates. Measure the board first (`hardware/MEASURE.md`, items 24 to 29).
The `HEAT` socket of the head board is not used.

## 13. Y belts and belt jaws

![The Y belts](../../hardware/build/img/ybelt-light.png)

You need the 2 Y belts, 4 belt jaws, 4 M3 × 10 screws, scissors and a tape measure.

1. Cut each Y belt about 1195 mm long: 80 mm more than its length between the folds (1115 mm).
2. Turn the Y tension screw out until the fork is at the back end of its travel.
3. Lay the belt round the motor pulley at the back and the idler at the front, teeth inside. The lower run lies flat over the rail, under the two clamp blocks of the carriage.
4. First end: drop the belt end into the pocket of one clamp block from the top, through the slit of the end wall. Lay it 10 mm along the pocket floor, past the end wall. The fold stops 3 mm short of the ledge. Fold it 180 degrees back over itself.
5. Put a belt jaw into the pocket from the top, on the two layers. Put an M3 × 10 screw through the jaw into the insert in the ledge. Tighten it until the jaw is on the ledge.
6. Second end: drop the belt into the other pocket, through the slit. Pull it tight by hand. Fold it 10 mm past the end wall. Cut off the tail.
7. Clamp the second end with a jaw and an M3 × 10 screw, as in step 5.
8. Turn the tension screw in until the belt is tight. Do the same on the other side.
9. On the left carriage, the X endstop board is over the front jaw screw. Take the board off (2 screws) to reach the screw, then put it back.

The ledge top is 0.3 mm under the jaw. The screw presses the two layers 0.3 mm and stops when the
jaw is on the ledge. The length between the folds is for the fork at the middle of its travel. The
fork moves 4 mm forward and 3 mm back. If the belt is too long, open the back jaw and fold the belt
again.

## 14. X belt and belt jaws

![The X belt and the belt jaws](../../hardware/build/img/xclip-light.png)

You need the X belt, 2 belt jaws, 2 M3 × 10 screws, scissors, and a ruler or tape.

1. Cut the X belt about 960 mm long: 80 mm more than its length between the folds (879 mm).
2. Turn the M3 tension screw out until the X idler fork is at the inner end of its travel.
3. Feed the belt flat, teeth down, through the top slot of the beam from the idler end to the motor end, under the top wheels. Lay it round the pulley and back through the bottom slot.
4. First end: at one end of the X plate, lead the belt out of the bottom slot into the 45 degree slit of the clamp. Lay it 10 mm along the pocket floor, past the end wall. The fold stops 3 mm short of the ledge. Fold it 180 degrees back over itself.
5. Slide a belt jaw into the pocket from the back, under the two layers. Put an M3 × 10 screw up through the 7 mm hole under the jaw, through the jaw into the insert in the ledge. Tighten it until the jaw is on the ledge.
6. Second end: lead the belt into the other clamp. Pull it tight by hand. Fold it 10 mm past the end wall. Cut off the tail. Clamp it as in step 5.
7. Turn the M3 tension screw in. It pulls the fork outward. Stop when the belt is tight.

This is the stock CR-10 belt path: both runs lie in the slot channels of the beam. The length
between the folds is for the fork at the middle of its travel. If the belt is too long, open the
second jaw and fold the belt again. Keep the belt centred where it passes the 6.2 mm slot opening at
the clamps.

## 15. Control box and harness

![The control box and the harness](../../hardware/build/img/t_variant-light.png)

1. Stand the control box on the table, left of the frame. The LCD faces the front.
2. Run the head cable from the head board along the back of the beam to the left carriage. It goes into the drag chain in the next step.
3. Tie the head cable to the back of the beam. Tie the base cable along the back bar.
4. Plug the two cables into the box. Check the mains voltage setting of the supply.
5. Connect the USB port of the box to the computer. Flash the plotter firmware (`25-firmware`).

The size of the control box is an estimate. Put the box where the stock cables reach.

## 16. Moving cables

![The drag chain and the servo loom](../../hardware/build/img/cables-light.png)

You need the drag chain, the chain anchor, 1 M5 × 12 screw with a T-nut, 4 M3 × 10 screws, the
1/2 inch split wire loom and 2 cable ties.

1. Put the chain anchor at the back left corner, beside the left rail. Its arm goes under the rail: one M5 × 12 screw up into a T-nut in the bottom outer slot of the rail.
2. Open the links of the chain. Lay in the head harness. Close the links. The Y motor cables do not go in the chain.
3. Bolt each end link with two M3 × 10 screws: the fixed end to the anchor wall, the moving end to the tab of the left carriage plate. The lower run lies on the table, and the bend points to the front.
4. Cut the split loom to 295 mm. Push the servo lead into it.
5. Moving end: lay the loom on the front of the X plate at the top left. Put a cable tie through the slot in the plate and round the loom.
6. Lead the loom up over the plate top and back over the beam.
7. Fixed end: tie the loom to the head harness cable, just above the big plug of the head board.

Cut the chain to 506 mm. The loop of the loom between the two ties is 189 mm long. It hangs free
behind the beam and needs no printed holder. In the model its lowest point stays 41 mm or more
above the paper. A real loom is stiffer and sags less (`hardware/MEASURE.md`, item 48).

## 17. Servo

![The servo](../../hardware/build/img/servo-light.png)

1. Push the servo into the pocket, the shaft at the bottom. The wire goes out through the slot.
2. Put the two servo screws through the tabs into the tower. Plug the servo into the servo lead.
3. Do the power-up checklist (`20-electronics-and-wiring`).
4. Send `M5` (pen up), then `M3` (pen down). Leave it at pen down.
5. Put the horn on the spline. The arm points at the tab of the slider, 10° below level.

At pen up the horn lifts the slider 7.0 mm. Fine-tune the angles with the knob menu (Pen up +1
and -1, Pen down +1 and -1).

## 18. Pen slider and pen

![The pen slider](../../hardware/build/img/slider-light.png)

You need the pen slider, a pen, an M3 × 20 screw and an M3 nut.

1. Push the M3 nut into the slot in the top of the slider. Turn the M3 × 20 clamp screw into it a few turns.
2. Slide the slider onto the dovetail rail of the pen carriage from the top.
3. Send `M3` (pen down). Put the pen in the V bore until its tip touches the paper. Tighten the clamp screw.

The weight of the slider and the pen is the pen force. Pens of 8 to 15 mm fit the V bore.

## 19. Camera pole (optional)

![The camera pole](../../hardware/build/img/t_mast-light.png)

You need your camera pole with the USB webcam, the pole foot, 2 M5 × 12 screws with T-nuts, an
M6 × 16 screw, an M3 × 16 screw with an M3 nut, and cable ties.

1. Turn two M5 drop-in T-nuts into the slot in the back face of the back bar, at the centre.
2. Drop the M3 nut into the slot in the top of the right collar ear. Put the M3 × 16 screw through the two ears. Leave it loose.
3. Put the pole in the socket. Hold the foot on its side. Put the M6 × 16 screw up through the floor into the pole end. Tighten it.
4. Hold the foot and the pole behind the back bar. Screw the foot to the bar with two M5 × 12 screws. The foot hangs 3 mm over the table.
5. Tighten the M3 collar screw.
6. Tie the USB cable to the foot through the two slots, and to the pole.

The pole is 590 mm long. The camera lens is about 15 mm above the top of the pole. Plotstudio
calibrates the view (`30-software`).

## 20. First run

![The finished plotter](../../hardware/build/img/table-light.png)

1. Do the power-up checklist in `20-electronics-and-wiring`.
2. Turn on the control box. Connect its USB port to the computer.
3. Send `M119`. Push each endstop by hand and check that it changes.
4. Send `G28`. Both Y sides go to the front switches. This squares the gantry.
5. Plot `samples/square.gcode`. Measure the square: it must be 40 × 40 mm.
6. Continue with `40-calibration-and-first-plots`.

The travel is 245.9 × 395.1 mm in the model. At the back, the inner Y wheel stops at the back bar.
The firmware uses 245 × 390 mm. A4 and Letter fit.
