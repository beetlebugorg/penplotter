# Measurements to take

Take each value with calipers or a tape. Write it in `shape.py`, remove the `ESTIMATE` mark, and run `make.sh`.

## Already measured

- The frame: outside 400 × 520 mm, inside 320 × 480 mm, table to the rail tops 57 mm. The long sides are 2040, laid
  flat. The front and back cross bars are 2020.
- The X beam: 2020, 415 mm long.
- The camera pole: 17.85 mm outside diameter, 590 mm long, an M6 thread in each end.

## Frame and feet

These values decide the Y travel and the height of the frame. Measure them first.

1. The feet: the distance from the front end and from the back end of the frame to the centre of each foot. The design
   uses 37.5 mm (`FOOT_Y`). Nothing of the carriages goes under the rails, so the feet do not limit the Y travel. Check
   that each foot stays clear of the inner wheel and its nut (they pass beside the rail, at x 45.5 mm and more), of the
   Y drag chain (outside the left rail), and of the arm of the chain anchor (under the left rail at the back, y 480 to
   512 mm, x up to 15 mm).
2. The feet: the distance from the outer face of the side to the centre of a foot, the diameter at the top, and the
   height (the bottom of a rail above the table). The design uses 31 mm, 28 mm and 37 mm (`FOOT_X`, `FOOT_D`,
   `FOOT_H`). All three are ESTIMATES. With these values a foot covers x 17 to 45 mm. That leaves 0.5 mm to the inner
   wheel path and 2 mm to the chain anchor arm. If your foot is wider than 28 mm, tell me the size: the anchor arm or
   the foot position must change. The other parts use the slot heights, so `FOOT_H` moves them all.
3. The feet: how they hold on (a screw, a threaded stud, a T-nut, glue), and its size. Can a foot slide along its slot?
4. The two screws in each bar end: the distance from the outer face of the side to each screw head, and the head
   diameter and height. The design uses 10 and 30 mm, and 8.5 × 5 mm (`BAR_SCREW_X`, `BAR_SCREW_HEAD`). The heads
   sit on the outer faces of the bars. No part covers them now.

## Camera pole

5. The M6 thread in the bottom end of the pole: its depth. The design uses an M6 × 16 screw: 4 mm of floor and 12 mm
   in the thread (`POLE_THREAD`, `M6_BOLT_L`). Use a shorter screw if the thread is shorter than 13 mm.
6. The camera: the height of the lens above the top of the pole. The design uses 15 mm (`CAM_ABOVE`).

## Control pod

Items 7 to 13 were for the Pico W control pod. The pod is gone (2026-11-10): skip them.

## Pen lift

14. The servo body: the width, the length, and the depth below the tabs. The pocket uses 12.4 × 22.8 × 16.0 mm.
15. The servo horn: from the shaft to the centre of the round end of the arm. The design uses 14 mm.

## V-wheels and the X plate

The stock X plate is not used now. A printed X plate holds the three stock X wheels. Keep the three wheels, the
eccentric spacer, the stock X motor, its pulley and the X belt.

16. A V-wheel: the outside diameter and the thickness. The design uses 24.4 × 10.2 mm (`WHEEL_D`, `WHEEL_T`).
17. A wheel in a slot: the distance from the face of the extrusion to the centre of the axle. Put the stock X carriage
    plate on the beam, measure across the outside of the top and the bottom wheel bolts, subtract the bolt diameter and
    20 mm, and halve it. The design uses 10.1 mm (`WHEEL_OFF`). The fit wheel test checks it.
18. A wheel spacer: the height. The design uses 6 mm (`SPACER_H`).
19. An eccentric spacer: the diameter and the length of the shank, the height of the hex, and its size across the flats.
    The design uses a 7.5 mm hole (`ECC_HOLE`), a 6 mm hex, and an 8 mm wrench. The shank must not be longer than the
    boss of the X plate (12 mm) or the Y carriage plate and boss (12 mm).
20. The stock X carriage plate on the beam: the distance from the front face of the plate to the front face of the
    beam. The design uses 3.6 mm (`PLATE_FRONT` is 13.6 mm, to the beam centre). The printed X plate keeps it.
21. (Not needed now: the X wheel axles are new button head screws, and their heads stay 2 mm in front of the back
    face of the beam.)
22. (Not needed now: the X wheels are on the printed X plate, `X_WHEELS`.)
23. (Not needed now: the endstops are the Creality boards, item 52.)
59. **The V-wheel tip in its slot (new, important).** How far the V of a wheel goes into the slot, from the face of the
    extrusion to the tip of the wheel. The model uses 2.6 mm (`WHEEL_TIP_DEPTH`, from `WHEEL_D`, `WHEEL_TIP` and
    `WHEEL_OFF`: ESTIMATE). The X belt runs in the top and the bottom slot channels of the beam, under the wheel tips
    (the stock CR-10 path), with its back 3.2 mm under the face. The fit check wants 0.3 mm or more between the tip and
    the belt. Measure it on the stock X plate on the beam: a depth gauge in the slot beside a wheel, or the wheel tip
    against a straight edge. If the gap is under 0.3 mm, use a GT2 16T pulley and a 16T toothed idler: the runs then
    lie 1.3 mm deeper, and the firmware needs 100 steps/mm.
60. **The 2020 slot channel of the beam (new).** The width of the slot opening at its narrowest point, the width of
    the channel behind the lips, the depth of the lips, and the depth from the face to the core. The model uses 6.2,
    11.0, 1.8 and 6.3 mm (`SLOT_OPEN`, `SLOT_CH_W`, `SLOT_LIP`, `SLOT_DEPTH`: ESTIMATE, V-slot data sheet). The 6 mm X
    belt lies in the channel with 2.5 mm to each side; it passes the 6.2 mm opening where it leaves the slot at the
    clamps of the X plate.
61. **The X belt on the stock machine (new).** Before you take the CR-10 apart: does the X belt touch the wheel tips or
    the slot lips anywhere? Is the stock X idler a 20T toothed idler or two F688 flanged bearings? The model uses a 20T
    toothed idler (`TIDLER`), so both runs are at the same depth.
62. **The plain wheel spacers (new).** Count the plain 6 mm spacers on the stock X plate, the Z carriages and the bed
    carriage. The build needs 6 (4 on the Y carriages, 2 on the printed X plate). Measure the length and the outside
    diameter of one. The model uses 6.0 mm long and 10 mm across (`SPACER_H`, `WASHER`: ESTIMATE). The printed X plate
    has a recess 11 mm across for each one.

## Stock controller variant: the two breakout boards

The sizes come from photos. They can be 2 mm off. The boards stand bare on two 4 mm nylon standoffs each, held by
cable ties through the board holes (2026-11-10). The sizes set where the standoffs stand on the extrusion face and
the room for the plugs.

Head board (the tool head breakout, `HB_*` in `shape.py`):

24. The two M3 holes: the distance between their centres. The model uses 33 mm (`HB_HOLES_U`).
25. The hole line: its distance from the board edge opposite the big header. The model uses 21 mm (`HB_HOLES_V`).
26. The first hole: its distance from the short edge at the BL_T socket. The model uses 8 mm (`HB_HOLES_U`).
27. The board: the length along the header and the width. The model uses 47 × 38 mm (`HB_PCB`).
28. The big plug: its height over the board, and how far it stands past the board edge. The design uses 10 mm and 3 mm (`MF_PLUG_H`, `HB_PLUG_OUT`).
29. A mated XH plug: its height over the board. The design uses 17 mm (`XH_H`).

Base board (the Y/Z breakout, `BB_*` in `shape.py`):

30. The two M3 holes: the distance between their centres. The model uses 34.7 mm (`BB_HOLES_U`).
31. The hole line: its distance from the board edge with the XH sockets. The model uses 16 mm (`BB_HOLES_V`).
32. The board: the length along the header and the width. The model uses 41 × 30 mm (`BB_PCB`).
33. The big plug with its latch: how far it stands past the board edge. The design uses 25 mm (`BB_PLUG_OUT`).

## Y drive (fixed motors)

41. Done (2026-11-10): a 42-40 is 286.7 g (`MOTOR_MASS`, the Y motors) and a 42-34 is 213.4 g (`XMOTOR_MASS`, the
    X motor), measured.
42. The stock Y motor cable and the stock Z motor cable (now the Y2 motor): their lengths, and the socket on the motor
    (6-pin PH2.0 is usual). The Y motors stand behind the back bar. Y1 is about 0.4 m from the base board, Y2 about
    0.8 m along the table behind the frame. If a cable is shorter, use a 1.5 m stepper cable (BOM line M31).
43. A GT2 20T toothed idler: the flange diameter and the width. The design uses 18 and 8.5 mm (`TIDLER`).
44. A GT2 pulley: the width of the toothed part with its flanges, and the hub length. The teeth must line up with the
    idler, 31.5 mm from the outer face of the rail (`YB_X`).
45. The bar end screw heads on the back face of the back bar: the distance from the outer face of the side to each
    head, and the head size. The Y motor bracket has a recess over the head at 30 mm; the motor stands 0.85 mm behind
    the heads (`BAR_SCREW_X`, `BAR_SCREW_HEAD`: ESTIMATE). If a head stands out more than 5 mm, tell me.

## Moving cables

46. The head harness (the cable from the control box to the head board): its outside diameter, its length, and the
    size of the big plug (width, height, length). The design passes it through an openable 10 × 20 mm chain. The
    diameter is an ESTIMATE (6 to 8 mm).
47. The drag chain you buy: its outer height and width, its bend radius at the centre line, and the length of an end
    link with its bracket. The design uses 15 × 27 mm, R28 and 12 mm (`YCH_OUTER`, `YCH_R`, `YCH_END`). The M3 screws
    go through the side wall of the end link (2 mm, `YCH_LINK_WALL`).
48. The servo loom (1/2 inch split loom, on hand): check that the loop hangs free behind the beam at each X position
    and that its lowest point stays off the paper. The model uses a 12.7 mm loom and a catenary (`LOOM_*`); a real loom
    is stiffer and sags less. At the back of the Y travel the model loop lies on the top of the back bar.
49. The smooth (toothless) idlers (BOM M20), when they arrive: the diameter of the belt face, the diameter of
    the flanges, the overall width, and the bore. The model uses 12 mm, 18 mm, 8.5 mm and 5 mm (`SIDLER_R`,
    `SIDLER_FL`, `IDLER_H`). All are ESTIMATES (typical retail values). The belt face sets the spacing of
    the omega idlers (`OMEGA_IDY`) and the belt length.
50. The stock GT2 pulleys and the stock X idler: count the teeth of a pulley (the model and the firmware use
    20 teeth: 80 steps/mm). Measure the pulley: the flange diameter, the hub diameter and length, and the
    overall length (`PULLEY`, ESTIMATE: 16, 13, 7 and 16 mm). Look at the X idler: is it toothed or smooth?
    The model uses a 20T toothed idler, 18 mm flanges, 8.5 mm wide (`TIDLER`, ESTIMATE). The X belt loop
    has its teeth inside, so a toothed idler is correct there.
51. The insert for the front outer Y wheel (BOM M34): its length and its outside diameter. The model uses an
    M5 short insert, 5.8 mm long and 7 mm across, in a 6.4 mm hole 7 mm deep (`INSERT_M5`). A longer insert
    needs a deeper hole: tell me its size.
52. The endstop boards: where the lever clicks (how far out from the board edge, and how far along it
    from the corner), how far the lever can go past the click, and the height of the switch and the
    plug over the board. The model uses a click 1.0 mm out, at 2.5 mm past the corner, and 1.5 mm of
    overtravel (`ES`, `ES_OVERTRAVEL`: ESTIMATES). Measure the pin height under the board too (the
    standoffs are 4 mm).

## Bought parts (context_detail.py)

The detailed models of the bought parts use these values. `context_detail.py` marks each one.

53. The endstop board, the lever tip in the free position: its distance out from the board edge under the
    switch, in mm. The model uses about 4 mm (ESTIMATE). The lever clicks at 1.0 mm (measured).
54. The endstop board, the switch body: its distance from the board edge with the holes, and its size
    (across, along the edge, height). The model uses 14.3 mm, and 5.8 × 12.8 × 6.5 mm (ESTIMATE, `CD.EB`).
55. The endstop board, the two mounting holes: the diameter. The model uses 3.2 mm (M3, ESTIMATE).
56. A stepper motor: the shaft length from the pilot boss face, the length of the flat, and the side of the
    6-pin socket (the model puts it on the back end cap). The model uses 24 mm and 15 mm (`CD.NEMA`).
57. The control box: the length, the depth and the height, and the places of the LCD, the knob, the USB
    socket, the SD slot, the power inlet and the cable exits. The model uses 290 × 210 × 85 mm (ESTIMATE).
58. The drag chain: the link pitch. The sim uses 18 mm (ESTIMATE).

## Flat Y plates and the servo loom (2026-11-10)

63. The X endstop on the X endstop wall of the left carriage: after the build, push the X plate by hand to the left
    stop. The trigger lug at the bottom left of the X plate must click the lever before the plate touches the saddle.
    The model has 1.5 mm of overtravel (`ES_OVERTRAVEL`, ESTIMATE).
64. The head harness cable over the head board: its diameter where the servo loom is tied to it. The model uses 9 mm
    (`MF_CABLE_D`, ESTIMATE). The loop plane is behind it (`LOOM_Y`).
65. The 42-34 X motor: its body length. The model uses 34 mm (`XMOTOR_L`, from the type name). Check that the socket
    end clears the drag chain tab.
