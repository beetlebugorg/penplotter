# Troubleshooting

Find the symptom in the left column. Do the checks in order.

## Control box and electronics

| Symptom | Checks |
|---|---|
| The box does not start | Check the mains cable and the switch of the box. Check the voltage switch of the supply (115 V for the US). |
| A motor hums but does not turn | Check the plug at the head board or the base board. Check the coil pairs with a meter (about 2 Ω in a pair). |
| A motor is hot | The onboard drivers keep the printer current. Read "Mainboard" in `docs/bom.md` before you change it. |
| A driver is dead | Never plug a motor in or out with the box on. The E driver is free, but the firmware does not use it. A move to E needs a change in `firmware/board/mega/pins.go`. |
| The motors move half the distance or twice the distance | The firmware needs 1/16 microsteps and 20-tooth pulleys. Check the pulleys. Check the board revision. |
| The servo does not move | Measure 5 V from pin 2 to pin 1 of `BL_T`. Check the signal wire on pin 3. Send `M280 P0 S90`. |
| The box resets when the servo moves | The servo takes too much current from the 5 V supply of the mainboard. Use an SG90, not a larger servo. |
| The motors stutter | Lower `TickHz` in `firmware/config/rate_avr.go` to 8000 and `MaxFeed` to 100. Build and flash again. |

## LCD and knob

| Symptom | Checks |
|---|---|
| The LCD is blank or shows garbage | Check the stock LCD ribbon at both ends. Turn the box off and on. |
| A knob item does nothing | Home, Pen up/down and Motors off work only when the machine is idle. |
| A long press does nothing | The long press stops a moving or waiting machine only. At idle it does nothing. |
| The LCD shows `ALARM` | Send `M999` over USB, then `G28`. The knob cannot clear the alarm. |
| The LCD shows `Pen T2` and `Press the knob` | This is a manual pen change. Change the pen and press the knob, or send `M108`. |
| The beeper is silent | The beeper pin (PC0) is not checked on a real board. The firmware works without it. |

## Motion and homing

| Symptom | Checks |
|---|---|
| `M119` shows a switch as triggered when it is not | Set `EndstopTriggeredHigh = false` for normally open switches. |
| One Y side moves the wrong way | Stop at once: the beam twists. Set `InvertDirY2` (or `InvertDirY`), or turn the motor plug with the power off. |
| `G28` stops with `error:homing failed` | A switch did not trigger. Send `M119` and push each switch. Check the Y2 switch at base board `Z-` and the Y1 switch at `Y-`. |
| The beam is not square after homing | Measure the error at both ends. Set `Y2HomeOffsetMM`. Flash, then send `M502` and `M500`. |
| An alarm after a move to X 0 or Y 0 | The firmware keeps a 1 mm floor after homing. Send `M999` to clear the alarm, then `G28`. |
| The square is not 40 × 40 mm | See "Steps per millimetre" in `40-calibration-and-first-plots`. |
| Lines are wavy | Tighten the belts. Rock each carriage by hand. If it has play, turn its eccentric spacer (`40-calibration-and-first-plots`). |
| A carriage has play, or the lines shift after a direction change | An eccentric spacer is loose. Turn it until the play is gone, and tighten its nut. Check that the wheel nuts are tight. |
| A carriage is hard to push, or it bumps along the travel | The preload is too high, or a wheel has a flat spot. Turn the eccentric back a little. Replace a wheel with a flat spot. |
| Rows of small waves (wobble) in long lines | A wheel wobbles on its axle, or a spacer is missing. Check the 6 mm spacers and tighten the axle nuts. Turn each wheel by hand: it must run true. |
| The beam is not square after homing, and the error changes | A Y carriage has play. Do the wheel check in `40-calibration-and-first-plots` before you set `Y2HomeOffsetMM`. |
| The X plate hits the head board ties | The ties go round the beam in the path of the X plate. This question is open: `hardware/REVIEW.md` lists the options. |
| Corners are rounded or overshoot | Lower `Accel` or `JunctionDev` in `firmware/config/config.go`. |
| Short lines draw slowly | The stock board plans 8 blocks ahead. Lower the draw speed. |

## Pen

| Symptom | Checks |
|---|---|
| The pen does not touch the paper | Set the pen height again in the pen slider (`40-calibration-and-first-plots`). Check the pen-down angle: the horn must clear the tab. |
| The pen drags at pen up | Raise the pen-up angle with `Pen up +1` on the knob, or with `M281`. Save with `M500`. |
| Lines are too thin or skip | The pen force is too low. The force is the weight of the slider and the pen. Try a heavier pen. |
| The slider sticks | Clean the dovetail. Rub PTFE dry lube on the rail. Print the fit tests with a larger `DT_CLR`. |
| The pen turns or slips in the slider | Tighten the M3 clamp screw a little. |
| The servo loom drags on the paper or a part | Check the two ties of the loom. The loop between the ties must be 189 mm. In the model the loop stays 41 mm or more above the paper (`hardware/MEASURE.md`, item 48). |
| A Z word in the G-code does not move the pen | The stock firmware uses `M3` and `M5` only. Plotstudio sends `M3` and `M5`. |

## Connections

| Symptom | Checks |
|---|---|
| No `/dev/ttyUSB0` | Use a data USB cable, not a charge cable. Turn on the box. Run `ls /dev/ttyUSB* /dev/ttyACM*`. |
| `tinygo flash` fails | Close all programs that use the port: plotstudio, `screen`. Check the `-port` value. |
| Plotstudio does not find the plotter | Start it with `-port /dev/ttyUSB0`. |
| The terminal shows garbage | Set 115200 baud. |
| `echo:ignored M117` | The stock firmware ignores some codes of other hosts. The job continues. |

## Camera and plotstudio

| Symptom | Checks |
|---|---|
| The calibration error is above 0.3 mm | Lock the focus before the calibration. Use 4 × 4 points. Click the centre of each dot. |
| The plot is offset from the scan | The camera moved after the calibration. Calibrate again. |
| The gantry hides part of the bed | Plotstudio scans twice, with the gantry at the back and at the front. Check `-scan-twice`. |
| A drawing has a red frame and does not plot | It is outside the travel. Move it or scale it. |
| A colour plots with the wrong pen | Change the colour mapping in the pen list. Or name an Inkscape layer after the pen, for example "T2 red". |
