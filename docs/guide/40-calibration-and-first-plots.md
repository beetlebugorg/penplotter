# Calibration and first plots

Do these steps after the assembly and the power-up checklist. Each step needs the one before it.
Send the G-code from a terminal on the USB port, for example `screen /dev/ttyUSB0 115200`.
Close the terminal before you connect plotstudio. Only one program can use the port.

## 1. Wheels and eccentrics

Check the wheels before you square the gantry. A loose carriage gives a false squaring result.

1. Turn the motors off. Rock each Y carriage and the X carriage plate by hand.
2. If a carriage has play, turn its eccentric spacer a little with the 8 mm wrench. Then tighten its nut.
3. Push the gantry from the front to the back, and the X carriage from the left to the right. Each must roll freely, with no tight spot.
4. Turn each wheel with a finger. A wheel that does not turn has too little preload. A wheel that is hard to push along has too much.

## 2. Homing and squaring

1. Send `M119` with the carriages away from the switches. All three switches read `open`.
2. Send `G28`. X homes first. Then both Y sides move to the front.
3. Each Y side stops at its own switch. This makes the beam square to the frame rails.
4. Measure the beam position at the left and at the right end, from the front bar.
5. If the two values differ, set `Y2HomeOffsetMM` in `firmware/config/config.go` to the difference. A positive value moves Y2 away from its switch after homing.
6. Build and flash the firmware (`25-firmware`).
7. Send `M502`, then `M500`. The saved settings now hold the new trim. `M502` also resets the pen angles, so set them again in section 5.
8. Home again.

`M114` shows the step counts of X, Y1 and Y2. After homing, the Y1 and Y2 counts are 0.

## 3. Steps per millimetre

The firmware uses 80 steps/mm on all axes: 200 steps per turn, 1/16 microsteps, and a 20-tooth GT2 pulley (40 mm per turn).

1. Tape a sheet of paper to the table.
2. Set the pen height (section 4), then plot `samples/square.gcode`.
3. Measure the square with calipers. It must be 40.0 × 40.0 mm.
4. A value of 20 mm or 80 mm means a different microstep setting on the drivers or a different pulley. The stock board runs at 1/16. Fix the hardware first.
5. For a small error on a correct setup, set `StepsPerMMX` or `StepsPerMMY` in `firmware/config/config.go`: new value = 80 × 40 / measured.

## 4. Pen height

The gantry height is fixed. The clamp screw of the pen slider sets the pen height.

1. Send `M3` (pen down).
2. Loosen the clamp screw. Put the pen in the V bore until its tip touches the paper.
3. Tighten the clamp screw. Do not overtighten it: the slider is PLA.
4. Send `M5` (pen up). The tip must lift clear of the paper.

The weight of the slider and the pen is the pen force. A heavier pen gives more force. Pens of 8
to 15 mm fit the V bore. Set the height again after each pen change.

## 5. Servo angles

The horn must clear the tab at pen down and lift the slider 7 mm at pen up.

1. Send `M5`. The pen must lift clear of the paper.
2. Send `M3`. The pen must rest on the paper. The horn must not touch the tab.
3. Change the angles with the knob. Turn it to `Pen up +1`, `Pen up -1`, `Pen down +1` or `Pen down -1`, and press it. Each press changes the angle by 1°, and the servo moves at once. The menu line shows the angle.
4. Or send `M281 U<up degrees> D<down degrees>`. `M503` reports the angles.
5. Start from the defaults: up 130°, down 80° (90° is the horn level).
6. Turn the knob to `Save settings` and press it, or send `M500`. The firmware also saves 3 s after the last change.

## 6. Camera calibration

Do this once for each camera position. `30-software` has the full steps.

1. Start plotstudio with the camera.
2. Lock the focus when the picture is sharp.
3. Push **Calibrate → Draw marks**. The plotter draws a grid of dots.
4. Push **Click marks** and click each dot.
5. Push **Solve**. An error below 0.3 mm is good. The simulator gives about 0.05 mm.

## 7. First SVG

1. Put the paper on the table, inside the travel.
2. Push **Scan the bed** in plotstudio.
3. Drop an SVG file on the bed view. Drag, scale and turn it onto the paper.
4. Check **Show path**, then push **Plot**.

Start with a line drawing. Plotstudio plots the lines (strokes) of the SVG. It does not fill areas.

## 8. A multi-pen job

1. Open the pen table in plotstudio. Give each pen a name and a colour. The table stays in plotstudio.
2. Load an SVG with coloured lines, or with Inkscape layers named after pens (for example "T2 red").
3. Plotstudio maps each colour to the nearest pen. Change a mapping in the list if needed.
4. Push **Plot**. The job plots the pens from light to dark.
5. At each pen change, the pen lifts and the carriage stops where it is. The beeper sounds once. The LCD shows `Pen Tn` on line 1 and `Press the knob` on line 3.
6. Change the pen in the pen slider and set its height (section 4). Press the knob to go on. A host can also send `M108`.
7. Run `samples/mandala.gcode` as the first six-pen test (`30-software`).

To stop a job at once, press and hold the knob for 0.8 s. Send `M999` and `G28` before the next job.
