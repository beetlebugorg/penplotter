#!/usr/bin/env python3
"""Pen plotter: write the build guide PDF (penplotter-build-guide.pdf).
Run after model.py, cura/make_profiles.py, and lineart/render.mjs. Needs Chromium.
The images are the line-art renders of lineart/render.mjs, light theme, with a transparent background."""

import json
import subprocess
from pathlib import Path

import shape as S

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
IMG = BUILD / "img"
OUT = HERE / "penplotter-build-guide.pdf"

SUMMARY = json.loads((BUILD / "parts.json").read_text())
FILAMENT = json.loads((BUILD / "filament.json").read_text())
SUPPORTS = json.loads((BUILD / "supports.json").read_text())
FIT = SUMMARY["fit"]
PRICE_PER_KG = 19.99                 # USD, PLA


def cost(grams):
    return grams / 1000 * PRICE_PER_KG


def print_time(name):
    """The print time in seconds from the CuraEngine slice: its last ;TIME_ELAPSED: line, or 0.
    The ;TIME: line in the header is a placeholder when CuraEngine runs on its own."""
    path = BUILD / "slice" / f"{name}.gcode"
    if not path.exists():
        return 0
    with path.open("rb") as fh:
        fh.seek(0, 2)
        fh.seek(max(0, fh.tell() - 20000))
        tail = fh.read().decode(errors="ignore")
    found = [l for l in tail.splitlines() if l.startswith(";TIME_ELAPSED:")]
    return int(float(found[-1].split(":")[1])) if found else 0


def hm(seconds):
    h, m = divmod(round(seconds / 60), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


FRAME = SUMMARY.get("frame", {})
TRAVEL = FRAME.get("travel", [250, 395])
BELT_L = SUMMARY.get("belt_lengths", {"y_left": 0, "x": 0})        # each belt between the middles of its two folds
FAST = SUMMARY.get("fasteners", {"by_item": {}, "by_part": {}, "joints": []})
CAB = SUMMARY.get("cables", {})

# Name, colour, count, print notes. The order is the order of the parts list. This is the main
# build: the stock controller build. The stock CR-10 V3 control box and its harness stay. The two
# breakout boards of the harness stand bare on nylon standoffs, held by cable ties.
PRINTS = [
    ("fit_rail", "Light blue", 1, "Back face on the bed. Tests the dovetail rail."),
    ("fit_slider", "Light blue", 1, "Upright. The slot, the pen bore, the clamp screw, and the nut."),
    ("fit_wheel", "Light blue", 1, "Flat. A strip of the Y carriage plate across the rail: the eccentric hole of an outer wheel and the hole of the inner wheel."),
    ("y_carriage_left", "Light blue", 1, "Flat, the plate on the bed. A 6 mm plate on 3 side wheels with the Y belt clamps, the beam saddle, the Y endstop striker, the chain tab, the X motor wall, and the X endstop wall."),
    ("y_carriage_right", "Light blue", 1, "Flat, the plate on the bed. A 6 mm plate on 3 side wheels with the Y belt clamps, the beam saddle, the Y endstop striker, and the seat of the X idler fork."),
    ("x_carriage_plate", "Light blue", 1, "Upright, the bottom edge on the bed. The printed X plate: 3 wheel bosses, the 2 X belt clamps under the beam, the X endstop trigger lug, the tie slot of the servo loom. The pen carriage bolts to its front."),
    ("y_front_left", "Light blue", 1, "Bottom on the bed. Front left: the Y1 endstop board, and the arm in front of the bar with the seat of the Y idler fork."),
    ("y_front_right", "Light blue", 1, "Bottom on the bed. Front right: the mirror image, with the Y2 endstop board."),
    ("y_idler_fork", "Light blue", 2, "Floor on the bed. Print 2. Holds a Y idler between two cheeks; the M3 tension screw pulls it forward."),
    ("y_idler_bracket_left", "Light blue", 1, "On its front face (the end wall). The seat and the end wall of the left Y idler fork, in front of the front bar."),
    ("y_idler_bracket_right", "Light blue", 1, "On its front face. The mirror image, for the right side."),
    ("y_motor_mount_left", "Light blue", 1, "On the motor face. Holds the Y1 motor behind the back bar, left. Two M5 into the back face slot of the bar."),
    ("y_motor_mount_right", "Light blue", 1, "On the motor face. The mirror image, for the Y2 motor, right."),
    ("y_chain_anchor", "Light blue", 1, "On its front face. Holds the fixed end of the Y drag chain under the left rail, at the back."),
    ("x_idler_fork", "Light blue", 1, "Floor on the bed. Holds the X idler between two cheeks past the right beam end. It slides in the seat of the right carriage; an M3 screw from outside sets the X belt tension."),
    ("pen_carriage", "Light blue", 1, "Back face on the bed. The pen lift. It bolts to the front of the printed X plate with 4 M3 screws."),
    ("pen_slider", "Light blue", 1, "Upright. Holds the pen in its V bore with an M3 clamp screw. It slides on the dovetail rail of the pen carriage."),
    ("mast_foot", "Light blue", 1, "Floor on the bed. Holds the camera pole behind the back bar."),
    ("belt_jaw", "Light blue", 6, "Flat on the bed. Print 6: one for each belt end (2 on each Y carriage, 2 on the X plate). An M3 screw presses it on the folded belt end."),
]

SETTINGS = [
    ("Profiles", "One Cura profile for each part: run <code>python3 cura/make_profiles.py --install</code> with Cura "
                 "closed, then pick “Pen plotter - …”."),
    ("Material", "PLA, 2.85 mm, 0.5 mm nozzle. PLA softens at about 55 °C. Keep the printed parts out of the sun and away from heat."),
    ("Temperature", "220 °C nozzle (215 °C first layer), 60 °C bed, fan 100 %. The PLA values of the desiccant project on this printer."),
    ("Layers", "0.3 mm layers, 0.9 mm top and bottom, 15 % gyroid infill, skirt. 3 walls (1.5 mm). The rail fit test has 4 walls (2 mm). Outer walls 40 mm/s."),
    ("Supports", "Off. A slice with supports on (60°, everywhere) adds 0 g of support to each part."),
]

TOOLS = [
    (1, "The stock CR-10 V3 control box (v2.5.2 board, 350 W supply, LCD, knob) and its harness, with the two breakout boards"),
    (3, "NEMA 17 steppers from the CR-10 (on hand): one 42-34 for X (it rides on the gantry: shorter and lighter), two 42-40 for Y1 and Y2"),
    (9, "Stock V-wheels (625 bearings): 3 for the X plate and 6 for the Y carriages, with 6 × 6 mm spacers and 3 eccentric spacers (from the stock X plate, the Z carriages and the bed carriage)"),
    (3, "M5 heat-set inserts, long (9.5 mm long, 7 mm across): the front outer Y wheel axles (2) and the bottom X wheel axle (1)"),
    (2, "M5 × 30 socket head screws: the front outer Y wheel axles (the head under the wheel, through the long insert)"),
    (4, "M5 × 35 socket head screws and M5 nyloc nuts: the back outer Y wheel axles on the eccentric spacers (2), and the inner Y wheel axles, the head on the 12 mm boss (2)"),
    (3, "X wheel axles: M5 × 30 (top left) and M5 × 35 (top right, eccentric) with M5 nyloc nuts in front, M5 × 25 (bottom) into the insert; 2 stock 6 mm spacers"),
    (17, "M5 drop-in T-nuts for 2020 slots: 4 for the Y front bases, 2 for the ears of the Y idler brackets, 4 for the Y motor brackets, 2 for the beam, 1 for the Y chain anchor, 2 for the camera pole foot, and 2 spare"),
    (2, "M5 × 12 countersunk screws (ISO 10642): the ears of the Y idler brackets, into T-nuts in the front face slot of the front bar"),
    (13, "M5 × 12 screws: the front bases (4), the Y motor brackets (4), the beam (2, through the back wall of each saddle into the back slot), the Y chain anchor (1), the camera pole foot (2) (T-nuts above)"),
    (3, "Idler forks: an M5 × 30 axle through both cheeks with 2 small washers and a nyloc nut, and an M3 × 20 tension screw with an M3 nut (one X fork, two Y forks)"),
    (3, "GT2 20T toothed idlers, 5 mm bore: one X idler, two Y idlers"),
    (6, "Belt jaws (printed), each with an M3 × 10 screw and an M3 heat-set insert: 2 on each Y carriage and 2 on the X plate"),
    (4, "M3 × 12 screws from the back of the X plate into the pen carriage (T1, T2, H1, H2); they cut their own thread"),
    (11, "Motor screws, M3 × 10: 3 for the X motor (from the front of its wall), 8 for the Y motors (4 each, from inside the bracket)"),
    (4, "M3 × 10 screws: the two end links of the Y chain; they cut their own thread"),
    (3, "Creality endstop boards (the stock X, Y and Z boards: 20 × 20 mm, KW12 switch, XH plug), 6 M3 × 8 screws and 6 M3 heat-set inserts (the belt jaws have 6 more)"),
    (4, "Nylon M3 standoffs, 4 mm: two under each breakout board"),
    (1, "3-wire servo pigtail with an XH 5-pin plug: the pen servo on BL_T of the head board"),
    (1, f"1/2 inch split wire loom (on hand), about {CAB.get('x_loom_len', 0) / 10 + 5:.0f} cm: the servo lead from the head board to the X plate, a free loop behind the beam"),
    (1, "Openable drag chain, inner 10 × 20 mm (10 × 15 is enough now), R28, about 0.5 m (cut from 1 m): the head harness only"),
    (18, "Cable ties, 2.5 mm: 2 for each breakout board (through the board holes and round the extrusion), 1 at each end of the servo loom, and 12 for the harness on the gantry and on the back bar"),
    (1, "MG90S or SG90 servo, with its horn and its two screws"),
    (1, f"GT2 open belt, 2 mm pitch, 6 mm wide, glass fibre, 5 m roll (the two Y belts are {BELT_L['y_left'] / 1000:.2f} m each and the X belt {BELT_L['x'] / 1000:.2f} m between the folds); 3 20T pulleys (5 mm bore) and 3 20T toothed idlers (5 mm bore)"),
    (1, "Camera pole foot (optional): 2 M5 × 12 screws (T-nuts above), 1 M6 × 16 screw into the pole end, 1 M3 × 16 screw and an M3 nut for the collar"),
    (1, "Calipers, hex keys (2.5, 3, 4, 5 mm), the wrench for the stock eccentric spacers (8 mm, as on the CR-10), and a soldering iron with M5 and M3 heat-set insert tips"),
]

FLASH = "tinygo flash -target=arduino-mega2560 -port /dev/ttyUSB0 ./firmware/cmd/mega"

# Each step: image, title, what you need, the steps, a note, and (optional) the image height in mm.
STEPS = [
    ("part_fit_rail", "Fit tests", ["fit rail", "fit slider", "fit wheel", "M3 × 20", "M3 nut", "a pen", "2 V-wheels"], [
        "Slide the fit slider onto the fit rail. It must slide by its weight, with no side play.",
        "Push the nut into the slot in the top of the fit slider. Put a pen in the bore. Turn the screw until it holds the pen.",
        "Put a wheel under the eccentric hole of the fit wheel strip: an M5 × 30 screw from below, the wheel, an eccentric spacer, the strip, a nyloc nut.",
        "Put a wheel under the counterbored hole: an M5 × 30 button head screw from the top, the strip, a 6 mm spacer, the wheel, a nyloc nut.",
        "Lay the strip across the end of a frame rail, the wheels in the two side slots. Turn the eccentric spacer. Both wheels must grip the slots before the eccentric reaches its end.",
    ], "If the slider is tight or loose, change <code>DT_CLR</code>. If the eccentric cannot reach, change <code>WHEEL_OFF</code>. "
       "See the last page. Then run <code>make.sh</code> and print the fit tests again."),
    # The heat-set inserts go in first, by size, before the assembly starts.
    ([("ins_m5_ycar", "Y carriage, left and right: 1 each"), ("ins_m5_xplate", "X plate: 1")],
     "M5 inserts (all parts)", ["2 Y carriages", "X plate", "3 M5 heat-set inserts (long)", "soldering iron, M5 insert tip", "M5 × 25 and M5 × 30 screws"], [
        "Set the iron to 220 °C. Let the tip get hot.",
        "Y carriages: lay each carriage on its plate. Find the round boss on the plate top, at the front outer wheel (left picture).",
        "Put an insert on the hole, the small end down. Put the tip in the insert. Push the insert straight down with light force, until its top is flush with the boss.",
        "Take the tip out straight up. Let the part cool for one minute.",
        "X plate: lay the plate on its back, the wheel bosses up. Press an insert into the face of the bottom wheel boss (right picture).",
        "Turn a screw in and out once to check each thread: M5 × 30 from below in the carriages, M5 × 25 in the X plate.",
    ], "The M5 inserts hold the front outer Y wheel axles and the bottom X wheel axle.", 80),
    ([("ins_m3_ycar", "Y carriages: 4 in the left, 2 in the right"), ("ins_m3_xplate", "X plate: 2, from below"),
      ("ins_m3_yfront", "Front bases: 2 each")],
     "M3 inserts (all parts)", ["2 Y carriages", "X plate", "2 front bases", "12 M3 heat-set inserts", "soldering iron, M3 insert tip", "M3 × 8 and M3 × 10 screws"], [
        "Change to the M3 tip. Let it get hot.",
        "Y carriages: press an insert into the ledge of each belt pocket, from the top. The ledge is the raised floor at the inner end of the pocket.",
        "Left Y carriage: press an insert into each of the two standoffs on the front face of the X endstop wall, from the front.",
        "X plate: turn the plate so that the hole under a belt pocket points straight up. Press the insert down through this hole into the ledge. Do the other pocket the same way.",
        "Front bases: press an insert into each of the two standoffs on the top of each base, from the top.",
        "Push each insert until its top is flush. Let the parts cool. Turn a screw in and out once to check each thread: M3 × 10 in the ledges, M3 × 8 in the standoffs.",
    ], "The 6 inserts in the ledges hold the belt jaws. The 6 inserts in the standoffs hold the three endstop boards. "
       "The right front base is the mirror image of the left base.", 62),
    ("ywheel", "Wheels on the Y carriages", ["2 Y carriages", "6 V-wheels", "4 spacers", "2 eccentric spacers", "2 × M5 × 30", "4 × M5 × 35", "4 nyloc nuts"], [
        "Front outer wheel: put an M5 × 30 screw up through a wheel and a 6 mm spacer, into the insert in the front boss of the plate, outside the rail. There is no nut.",
        "Back outer wheel: put an M5 × 35 screw up through a wheel and an eccentric spacer, into the back hole. The hex is between the wheel and the plate. Put a nyloc nut on top.",
        "Inner wheel: put an M5 × 35 screw down through the 12 mm boss behind the beam. Do not put the spacer, the wheel and the nut on yet.",
        "Tighten the front screw and the back nut until the wheels turn freely with no wobble.",
    ], "Each carriage is a flat plate, as the stock CR-10 Z carriage plate. The left carriage has the X motor wall behind the beam end. "
       "The right carriage has the seat of the X idler fork. The inner wheel goes on when the carriage is on the rail."),
    ("ywheel_on", "Y carriages on the rails", ["frame", "2 Y carriages with wheels", "4 mm hex key", "8 mm wrench"], [
        "Stand the frame on the table, feet down.",
        "Set each carriage on its rail from above: the plate on the rail top, the two outer wheels in the outer side slot.",
        "Under the inner boss, put a 6 mm spacer, the inner wheel and a nyloc nut on the inner screw. The wheel runs in the inner side slot.",
        "Turn the eccentric hex with the 8 mm wrench from outside the frame, until the carriage has no play. It must still roll freely. Tighten its nut.",
        "Measure the two diagonals of the frame. Make them equal, then tighten the bar screws.",
    ], "Too much preload makes flat spots on the wheels. Stop when the play is gone. Nothing of the carriage goes under the rail, so the feet stay where they are."),
    ("ydrive", "Y motors behind the back bar", ["2 Y motor brackets", "2 Y motors (42-40)", "2 GT2 pulleys", "8 × M3 × 10", "4 × M5 × 12 + T-nuts"], [
        "Hold a 42-40 motor on the outer face of each bracket plate, the shaft through the plate to the inside, the socket up. Put four M3 × 10 screws from the inside into the motor.",
        "Put a GT2 pulley on each shaft, the hub to the inside. Line up its teeth with the inner top slot of the rail (31.5 mm from the outer face of the side). Tighten the set screws on the flat of the shaft.",
        "Turn two M5 drop-in T-nuts into the slot in the back face of the back bar, near each end, right of the bar end screw heads.",
        "Hold each bracket on the back face of the back bar, the recess over the head of the bar end screw. Screw it on with two M5 × 12 screws.",
        "Plug in each motor cable. It goes along the table behind the frame to the base board (step \"Breakout boards\"). It does not move.",
    ], "The Y motors stand still. The gantry does not carry them, and the Y motor cables are out of the drag chain.", 100),
    ("yfront", "Front bases, Y idlers and endstops", ["2 front bases", "2 idler brackets", "2 × M3 × 12", "2 × M5 × 12 countersunk + T-nuts", "2 Y idler forks", "2 20T idlers", "2 × M5 × 30 + 4 washers + 2 nyloc", "2 × M3 × 20 + 2 nuts", "4 × M5 × 12 + T-nuts", "2 switches", "4 × M3 × 8"], [
        "Push an M3 nut into the slot in the floor of each Y idler fork, from below. The slot is under the middle of the idler.",
        "Hold an idler between the two cheeks, a washer on each side. Put the M5 × 30 screw through. Tighten the nyloc nut until the idler turns freely with no play.",
        "Turn two M5 drop-in T-nuts into the top slot of the front bar, near each end. Screw a front base on each end with two M5 × 12 screws. Its two lips reach over the front of the bar.",
        "Turn an M5 drop-in T-nut into the front face slot of the front bar, behind the ear of each idler bracket.",
        "Hold an idler bracket on the front face of the front bar, under the two lips. Put an M5 × 12 countersunk screw through the hole in the front of the ear into the T-nut. Tighten it.",
        "Put an M3 × 12 screw down through the inner lip into the bracket.",
        "Set each fork on the seat of the bracket, between the two guides. Put an M3 × 20 screw through the end wall from the front into the nut. Turn it two turns only.",
        "Lay a Y endstop board on the two standoffs of each front base, the parts up, the plug to the front, the switch to the back. Screw it down with two M3 × 8 screws.",
        "Plug in the endstop cable from the front. Leave 20 mm for the plug and the bend of the wires.",
    ], "Home is the front left corner. A striker on the front edge of each carriage plate meets the lever tip. At the front stop it is 1.5 mm past the click.", 78),
    ("t_boards", "Breakout boards", ["head board", "base board", "4 nylon M3 standoffs, 4 mm", "4 cable ties"], [
        f"Base board: hold it on the back face of the back bar, {S.BB_X0:.0f} mm from the left end, a standoff under each of its two holes. The standoffs stand on the face of the bar, beside the slot.",
        "Put a cable tie through each board hole and its standoff, round the bar. Pull the ties tight.",
        "Plug in Y (Y1 motor, left), Z1 (Y2 motor, right), Y- (Y1 endstop) and Z- (Y2 endstop). Leave Z2 empty. Push the big 2 × 8 plug into the header.",
        f"Head board: hold it on the back face of the X beam, {S.HB_X0:.0f} mm from the left side of the frame, the big header up, on two standoffs. Tie it to the beam in the same way.",
        "Plug in X (X motor), X- (X endstop) and the servo pigtail on BL_T. Push the big 2 × 15 plug into the header from the top. Keep the cable straight for 35 mm, then bend it back toward the control box.",
    ], "The firmware maps Z1 to the Y2 motor and Z- to the Y2 endstop. The board sizes are estimates: measure the boards first (MEASURE.md).", 100),
    ("mount", "X plate and pen carriage", ["X plate", "pen carriage", "3 V-wheels", "1 eccentric spacer", "M5 × 30, M5 × 35, M5 × 25", "2 nyloc nuts", "2 stock 6 mm spacers", "4 × M3 × 12"], [
        "Hold the pen carriage on the front face of the X plate. The three wheel bosses come through the round holes of the pen carriage.",
        "Put four M3 × 12 screws from the back through the plate into the pen carriage (T1, T2, H1, H2). They cut their own thread. Do not overtighten them.",
        "Top left wheel: from the back, an M5 × 30 screw through the wheel and a 6 mm spacer, into the boss (the spacer in the recess). Put a nyloc nut on the front.",
        "Top right wheel: from the back, an M5 × 35 screw through the wheel and the eccentric spacer (the hex toward the plate), into the boss. Put a nyloc nut on the front. Leave it loose.",
        "Bottom wheel: from the back, an M5 × 25 screw through the wheel and a 6 mm spacer, into the insert in the bottom boss (the spacer in the recess).",
    ], "The eccentric is on the top right wheel. Turn its hex from above with the wrench.", 95),
    ("t_beam", "Beam and X plate", ["2020 beam", "X plate with the pen carriage", "2 × M5 × 12 + T-nuts", "X switch", "2 × M3 × 8"], [
        "Slide the X plate onto the beam from one end. The top wheels go in the top slot, the bottom wheel in the bottom slot.",
        "Turn the eccentric hex of the top right wheel from above until the plate has no play. It must still roll freely. Tighten its nut.",
        "Turn an M5 drop-in T-nut into the back slot of the beam, 14 mm from each end.",
        "Lay the beam on the two saddles, the pen carriage to the front. The beam ends touch the stops at the outer ends of the saddles.",
        "Screw the beam to each carriage with one M5 × 12 screw, through the back wall of the saddle into the T-nut.",
        "Screw the X endstop board on the two standoffs on the front of the X endstop wall of the left carriage with two M3 × 8 screws: the parts to the front, the switch to the right, the plug to the left. The trigger lug at the bottom left of the X plate meets the lever tip.",
    ], "Keep the top and the bottom slots of the beam free: the X belt runs in them. The inner face of the left saddle is the hard stop of the X plate."),
    ("xmotor", "X motor", ["X motor (42-34)", "GT2 pulley", "3 × M3 × 10"], [
        "Put the GT2 pulley on the X motor shaft, the hub toward the motor. Do not tighten it yet.",
        "Hold the motor behind the left beam end, the shaft to the front through the motor wall of the left carriage, the socket up.",
        "Put three M3 × 10 screws from the front through the wall into the motor. The heads sit in counterbores. The hole over the beam end stays empty.",
        "Slide the pulley along the shaft until its teeth are on the beam centre line, in line with the top and the bottom slots. Tighten the set screws.",
    ], "The X motor is a 42-34: it rides on the gantry, so the shorter motor keeps the moving mass low. "
       "The motor stands behind the left beam end, as on the stock CR-10. The pulley turns free past the beam end."),
    ("xfork", "X idler fork", ["idler fork", "20T toothed idler", "M5 × 30", "2 small M5 washers (7.5 mm)", "M5 nyloc nut", "M3 × 20", "M3 nut"], [
        "Push an M3 nut into the slot in the floor of the fork, from below. The slot is under the middle of the idler.",
        "Hold the idler between the two cheeks of the fork, a washer on each side.",
        "Put the M5 × 30 screw through the front cheek, the washer, the idler, the washer and the back cheek. Put the nyloc nut on the back. Tighten it until the idler turns freely with no play.",
        "Set the fork in the seat past the right beam end, the floor on the seat.",
        "Put the M3 × 20 screw through the end wall from the outside (the right side of the machine), into the nut in the fork. Turn it two turns only. It sets the X belt tension later (step \"X belt\").",
    ], "The idler axle has a support at each end. The fork slides 4 mm out and 2.5 mm in. The tension screw head is on the outside of the right carriage: you reach it without taking anything off.", 95),
    ("ybelt", "Y belts and belt jaws", ["2 Y belts", "4 belt jaws", "4 × M3 × 10", "scissors"], [
        "Turn the Y tension screw out until the fork is at the back end of its travel.",
        f"Cut each Y belt about {BELT_L['y_left'] + 80:.0f} mm long.",
        "Front block: lay the belt end in the slit of the end wall, teeth down. Lay 10 mm of it on the pocket floor, past the end wall. Fold the end back over itself. The fold stops 3 mm short of the ledge.",
        "Lay a jaw on the two layers, the screw hole over the ledge. Put an M3 × 10 screw through the jaw into the insert. Tighten it until the jaw is down on the ledge.",
        "On the left carriage the X endstop board is over the front jaw screw. Take the board off (2 screws) to reach the screw, then put it back.",
        "Lay the belt round the idler at the front and the motor pulley at the back, teeth inside. The lower run lies over the rail, under the two clamp blocks.",
        "Back block: pull the belt tight by hand through the slit. Fold it back 10 mm past the end wall, cut the tail, and clamp it with a jaw in the same way.",
        "Turn the tension screw in until the belt is tight. Do the same on the other side.",
    ], "The jaw stops on the ledge, so the screw presses the two layers 0.3 mm and no more. "
       f"The length between the two folds is {BELT_L['y_left']:.1f} mm in the model, with the fork at the middle of its travel. "
       f"The fork moves {abs(S.YIDLER_TRAVEL[0]):.0f} mm forward and {S.YIDLER_TRAVEL[1]:.0f} mm back. If the belt is too long, open the back jaw and fold the belt again.", 85),
    ("xclip", "X belt and belt jaws", ["X belt", "2 belt jaws", "2 × M3 × 10", "scissors"], [
        "Turn the M3 tension screw out until the X idler fork is at the inner end of its travel.",
        f"Cut the X belt about {BELT_L['x'] + 80:.0f} mm long.",
        "Feed the belt flat, teeth down, through the top slot of the beam from the idler end to the motor end, under the top wheels. Lay it round the pulley and back through the bottom slot.",
        "Left clamp: from the back, lead the belt out of the bottom slot into the 45 degree slit and 10 mm along the pocket, past the end wall. Fold the end back under itself, 3 mm short of the ledge.",
        "Slide a jaw into the pocket from the back, under the two layers. Put an M3 × 10 screw from below through the hole under the jaw, through the jaw, into the insert. Tighten it until the jaw is on the ledge.",
        "Right clamp: pull the belt tight by hand, fold it, cut the tail, and clamp it in the same way.",
        "Turn the M3 tension screw in. It pulls the fork outward. Stop when the belt is tight.",
    ], f"This is the stock CR-10 belt path: both runs lie in the slot channels of the beam, so no belt stands in front of the beam. "
       f"The length between the folds is {BELT_L['x']:.1f} mm in the model, with the fork at the middle of its travel. The belt passes the 6.2 mm slot opening at the clamps: keep it centred.", 105),
    ("t_variant", "Control box and harness", ["stock control box", "stock harness", "cable ties", "USB cable"], [
        "Stand the control box on the table, left of the frame. The LCD faces the front.",
        "Run the head cable from the head board along the back of the beam to the left carriage. It goes into the Y drag chain (step \"Moving cables\"), and leaves the chain at its fixed end, at the back left corner.",
        "Tie the head cable to the back of the beam. Tie the base cable along the back bar.",
        "Plug the two cables into the box. Check the mains voltage setting of the supply.",
        f"Connect the USB port of the box to the computer. Flash the plotter firmware: <code>{FLASH}</code>.",
    ], "The size of the control box is an estimate. Put the box where the stock cables reach. From the back: the head board rides "
       "on the beam, and the base board is on the back bar.", 105),
    ("cables", "Moving cables", ["Y drag chain", "servo loom (1/2 inch split loom)", "chain anchor", "1 × M5 × 12 + T-nut", "4 × M3 × 10", "2 cable ties"], [
        "Put the chain anchor at the back left corner, beside the left rail. Its arm goes under the rail: one M5 × 12 screw up into a T-nut in the bottom outer slot of the rail. The arm is wide round the screw, so the screw has 5 mm of material all round.",
        "Open the links of the chain. Lay in the head harness. Close the links. The Y motor cables do not go in the chain: the Y motors do not move.",
        "Bolt the end links with two M3 × 10 screws each: the fixed end to the anchor wall, the moving end to the tab of the left carriage plate. The lower run lies on the table, the bend points to the front.",
        f"Cut the split loom to {CAB.get('x_loom_len', 0):.0f} mm. Push the servo lead into it.",
        "Moving end: lay the loom on the front of the X plate at the top left. Put a cable tie through the slot in the plate and round the loom. Lead the loom up over the plate top and back over the beam.",
        f"Fixed end: tie the loom to the head harness cable, just above the big plug of the head board. The loop between the two ties is {CAB.get('x_loop_len', 0):.0f} mm long and hangs free behind the beam.",
    ], f"Cut the chain to {CAB.get('y_chain_len', 0):.0f} mm. The servo loom needs no printed holder. "
       f"In the model the lowest point of the loop stays {CAB.get('loom_low', 0):.0f} mm or more above the paper.", 78),
    ("servo", "Servo", ["servo", "horn", "2 servo screws"], [
        "Push the servo into the pocket, the shaft at the bottom. The wire goes out through the slot.",
        "Put the two servo screws through the tabs into the tower. Plug the servo into the servo pigtail.",
        "Send <code>M5</code> (pen up), then <code>M3</code> (pen down). Leave it at pen down.",
        f"Put the horn on the spline. The arm points at the tab of the slider, {abs(S.PEN_DOWN_DEG):.0f}° below level.",
    ], f"At pen up the horn lifts the slider {FIT['lift']:.1f} mm. Fine-tune the angles with the LCD menu: "
       "<i>Pen up +1</i>, <i>Pen up -1</i>, <i>Pen down +1</i>, <i>Pen down -1</i>."),
    ("slider", "Pen slider and pen", ["pen slider", "pen", "M3 × 20", "M3 nut"], [
        "Push the M3 nut into the slot in the top of the slider. Turn the M3 × 20 clamp screw into it a few turns.",
        "Slide the slider onto the dovetail rail of the pen carriage from the top.",
        "Send <code>M3</code> (pen down). Put the pen in the V bore until its tip touches the paper. Tighten the clamp screw.",
    ], f"The weight of the slider and the pen is the pen force. Pens of {FIT['pen_min']:.0f} to {FIT['pen_max']:.0f} mm fit the V bore."),
    ("t_mast", "Camera pole (optional)", ["camera pole", "pole foot", "2 × M5 × 12 + T-nuts", "M6 × 16", "M3 × 16 + nut", "cable ties"], [
        "Turn two M5 drop-in T-nuts into the slot in the back face of the back bar, at the centre.",
        "Drop the M3 nut into the slot in the top of the right collar ear. Put the M3 × 16 screw through the two ears. Leave it loose.",
        "Put the pole in the socket. Hold the foot on its side. Put the M6 × 16 screw up through the floor into the pole end. Tighten it.",
        "Hold the foot and the pole behind the back bar. Screw the foot to the bar with two M5 × 12 screws. The foot hangs 3 mm over the table.",
        "Tighten the M3 collar screw. Tie the USB cable to the foot through the two slots, and to the pole.",
    ], "The pole is 590 mm long. The camera lens is about 15 mm above the top of the pole. plotstudio calibrates the view."),
    ("table", "First run", ["USB cable", "mains cable"], [
        "Connect the control box to the mains and turn it on. Connect the box to the computer with USB.",
        "Send <code>M119</code>. Push each endstop by hand and check that it changes.",
        "Send <code>G28</code>. Both Y sides go to the front switches. This squares the gantry.",
        "Plot <code>samples/square.gcode</code>. Measure the square: it must be 40 × 40 mm.",
        "For layout with the camera, run <code>plotstudio</code> (<code>docs/studio.md</code>).",
    ], f"The travel is {TRAVEL[0]:.0f} × {TRAVEL[1]:.0f} mm in the model. A4 and Letter fit. "
       f"Set the firmware to {int(TRAVEL[0])} × {min(int(TRAVEL[1]), 390)} mm."),
]

ADJUST = [
    ("The slider is tight or has play on the rail", "DT_CLR", f"{S.DT_CLR:.2f}",
     "Add 0.05 if it is tight. Subtract 0.05 if it has play. Reprint the fit tests."),
    ("A self-tapping screw is loose in its pilot hole", "SELF_TAP", f"{S.SELF_TAP:.1f}",
     "Subtract 0.1 for a tighter thread. Add 0.1 if the screw is hard to turn."),
    ("The servo does not fit its pocket", "SERVO_W, SERVO_L", f"{S.SERVO_W:.1f}, {S.SERVO_L:.1f}",
     "The servo sizes are data sheet values. Measure your servo."),
    ("The horn does not reach the tab", "HORN_L", f"{S.HORN_L:.0f}",
     "Measure from the shaft to the centre of the round end of the horn arm."),
    ("The eccentric cannot take up the play of a carriage", "WHEEL_OFF", f"{S.WHEEL_OFF:.1f}",
     "Subtract 0.2 if the wheels do not reach the slots. Add 0.2 if the eccentric is at its end before the wheels turn freely. The fit wheel test checks it."),
    ("The eccentric spacer is loose or tight in its hole", "ECC_HOLE", f"{S.ECC_HOLE:.1f}",
     "Measure the shank of the eccentric spacer. Add 0.1 to it."),
    ("The beam is loose on the saddles", "CRADLE_CLR", f"{S.CRADLE_CLR:.1f}",
     "Subtract 0.1. The two M5 screws pull the beam against the back walls, so a small gap is fine."),
    ("The pen does not reach the paper", "DROP", f"{S.DROP:.0f}",
     "Set the pen in the slider at pen down first. DROP lowers the whole pen lift."),
]

CSS = """
  @page { size: A4; margin: 0; }
  * { box-sizing: border-box; }
  :root { --ink: #16181a; --ink-2: #4a4f55; --accent: #0a7f63; --bg: #fbfbf9; --grid: #ececE6; --line: #e2e2dc;
          --mono: "JetBrains Mono", "JetBrainsMono Nerd Font", ui-monospace, monospace; }
  body { margin: 0; font-family: "Inter", "Helvetica Neue", Helvetica, Arial, "Liberation Sans", sans-serif; color: var(--ink); }
  .page { width: 210mm; height: 297mm; padding: 16mm 16mm 14mm; page-break-after: always; position: relative; overflow: hidden; }
  .page:last-child { page-break-after: auto; }
  h1 { font-size: 50pt; letter-spacing: 2pt; margin: 0; font-weight: 800; }
  h2 { font-size: 20pt; margin: 0 0 5mm; font-weight: 700; }
  .sub { font-size: 24pt; font-weight: 700; margin-top: 2mm; color: var(--accent); }
  .num { font: 800 72pt/1 var(--mono); color: var(--accent); }
  .head { display: flex; align-items: flex-end; gap: 8mm; border-bottom: 0.6mm solid var(--ink); padding-bottom: 4mm; }
  .head .title { font-size: 22pt; font-weight: 700; padding-bottom: 3mm; }
  .fig { width: 100%; margin: 4mm 0; padding: 4mm; text-align: center; border: 0.3mm solid var(--line); border-radius: 3mm;
         background-color: var(--bg); background-size: 6mm 6mm;
         background-image: linear-gradient(var(--grid) 0.15mm, transparent 0.15mm), linear-gradient(90deg, var(--grid) 0.15mm, transparent 0.15mm); }
  .fig img { max-width: 100%; max-height: 130mm; vertical-align: middle; }
  .need { display: flex; flex-wrap: wrap; gap: 3mm; margin: 4mm 0; }
  .chip { border: 0.4mm solid var(--ink); border-radius: 999px; padding: 1.5mm 4mm; font: 600 10pt var(--mono); }
  ol, ul { font-size: 12pt; line-height: 1.5; padding-left: 6mm; margin: 2mm 0; }
  p { font-size: 12pt; line-height: 1.5; margin: 2mm 0; }
  .note { border: 0.4mm solid var(--accent); border-radius: 3mm; padding: 3mm 5mm; margin-top: 4mm; font-size: 11.5pt; background: #e3f3ee; }
  .note b { color: var(--accent); }
  table { border-collapse: collapse; width: 100%; font-size: 10.5pt; }
  td, th { border-bottom: 0.2mm solid #999; padding: 1.4mm 2mm; vertical-align: middle; text-align: left; }
  th { border-bottom: 0.6mm solid #111; }
  td.q { font-weight: 800; font-size: 13pt; width: 12mm; }
  td.n, th.n { text-align: right; white-space: nowrap; }
  tr.total td { font-weight: 800; border-top: 0.6mm solid #111; border-bottom: none; }
  .thumb { width: 18mm; height: 11mm; object-fit: contain; display: block; }
  .grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; }
  .grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; }
  .grid4 .card img { height: 17mm; }
  .grid5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 2.5mm; }
  .grid5 .card { font-size: 7.6pt; padding: 2mm; }
  .grid5 .card img { height: 15mm; }
  .grid5 .card b { font-size: 9pt; }
  .grid6 { display: grid; grid-template-columns: repeat(6, 1fr); gap: 2mm; }
  .grid6 .card { font-size: 7pt; padding: 1.6mm; }
  .grid6 .card img { height: 13mm; }
  .grid6 .card b { font-size: 8pt; }
  .card { border: 0.3mm solid var(--line); background: var(--bg); border-radius: 3mm; padding: 2.5mm; font-size: 8.8pt; line-height: 1.3; }
  .card img { width: 100%; height: 20mm; object-fit: contain; }
  .card b { display: block; font-size: 11pt; margin: 1mm 0; }
  .sw { display: inline-block; width: 3.5mm; height: 3.5mm; border-radius: 1mm; vertical-align: -0.5mm; margin-right: 1.5mm; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; }
  code { font-size: 0.92em; }
  table.tight td { padding: 0.6mm 2mm; }
  table.tight .thumb { height: 8mm; }
  .foot { position: absolute; bottom: 8mm; left: 16mm; right: 16mm; font-size: 9.5pt; color: #555; display: flex; justify-content: space-between; }
"""

SWATCH = {"Light blue": "#7FB6E0"}   # one accent colour for all printed parts, as in the sim


def img(name):
    return (IMG / f"{name}-light.png").as_uri()


def foot(n):
    return f'<div class="foot"><span>CR-10 V3 table plotter · build guide</span><span>{n}</span></div>'


def cover():
    return f"""<section class="page">
  <h1 style="font-size:40pt">PEN PLOTTER</h1><div class="sub">A table plotter from a CR-10 V3</div>
  <p style="margin-top:4mm;max-width:170mm">The base frame of a CR-10 V3 stands on the table, and the table is the bed. Stock
  V-wheels carry both axes: three under each flat Y carriage plate, in the side slots of the frame rail, and three on the
  printed X plate on the beam. The X belt runs in the top and bottom slots of the beam, as on the stock CR-10. Two Y motors
  stand still behind the back bar and move the gantry, and homing squares it on two switches. A servo lifts a pen slider
  on a dovetail rail; the weight of the slider and the pen is the pen force. The stock CR-10 V3 control box stands beside
  the frame, and the stock harness stays. Its two breakout boards stand on nylon standoffs, held by cable ties. The
  firmware is written in Go and runs on the ATmega2560 of the stock board. A camera and <code>plotstudio</code> place a
  drawing on the paper that lies on the table.</p>
  <div class="fig"><img src="{img('table')}" style="max-height:105mm"></div>
  <p style="font-size:10pt;color:#444">The plotter at home, from the front right, with the control box at the left. Travel {TRAVEL[0]:.0f} × {TRAVEL[1]:.0f} mm.</p>
  <div class="note"><b>Measurements.</b> The frame sizes are measured. The servo sizes, the wheel sizes, the breakout boards and
  the control box are data sheet values or estimates. Print the fit tests first. <code>MEASURE.md</code> lists the
  measurements to take.</div>
  {foot(1)}
</section>"""


PROJECT_DIR = Path(__file__).resolve().parent


def _stl_size(name):
    """The bed size of a part from its STL (for a part that parts.json does not list)."""
    import struct
    data = (PROJECT_DIR / "stl" / f"{name}.stl").read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    lo, hi = [1e9] * 3, [-1e9] * 3
    for i in range(n):
        o = 84 + i * 50 + 12
        for k in range(3):
            v = struct.unpack("<3f", data[o + 12 * k:o + 12 * k + 12])
            lo = [min(a, b) for a, b in zip(lo, v)]
            hi = [max(a, b) for a, b in zip(hi, v)]
    return {"size": [h - l for h, l in zip(hi, lo)]}


def print_page():
    rows = []
    tg = tm = 0
    tsum = [0]
    for name, colour, k, _ in PRINTS:
        p = SUMMARY["parts"].get(name) or _stl_size(name)
        g, m = FILAMENT[name]["grams"] * k, FILAMENT[name]["metres"] * k
        tg += g
        tm += m
        sx, sy, sz = p["size"]
        tt = print_time(name) * k
        tsum[0] += tt
        rows.append(f'<tr><td><img class="thumb" src="{img("part_" + name)}"></td><td><code>{name}</code>{f" × {k}" if k > 1 else ""}</td>'
                    f'<td class="n">{sx:.0f} × {sy:.0f} × {sz:.0f}</td><td class="n">{hm(tt)}</td><td class="n">{g:.0f} g</td><td class="n">{m:.1f} m</td><td class="n">${cost(g):.2f}</td></tr>')
    rows.append(f'<tr class="total"><td></td><td>Total ({sum(p[2] for p in PRINTS)} parts, with the fit tests)</td><td></td><td class="n">{hm(tsum[0])}</td><td class="n">{tg:.0f} g</td><td class="n">{tm:.1f} m</td>'
                f'<td class="n">${cost(tg):.2f}</td></tr>')
    cards = "".join(f'<div class="card"><img src="{img("part_" + n)}"><b>{n.replace("_", " ")}</b>'
                    f'<span class="sw" style="background:{SWATCH[c]}"></span>{c} · support check {SUPPORTS[n]:.0f} g<br>{t}</div>'
                    for n, c, _, t in PRINTS)
    st = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in SETTINGS)
    tools = "".join(f'<tr><td class="q">{q}×</td><td>{t}</td></tr>' for q, t in TOOLS)
    return f"""<section class="page">
  <h2>Printed parts</h2>
  <table class="tight"><tr><th></th><th>Part</th><th class="n">Size on the bed (mm)</th><th class="n">Print time</th><th class="n">Filament</th><th class="n">Length</th><th class="n">Cost</th></tr>
  {''.join(rows)}</table>
  <p style="font-size:9.5pt;color:#444">Print time, filament and cost from slices with the Cura profiles of this project (CuraEngine, 0.3 mm layers, PLA,
  TAZ Workhorse SE 0.5 mm), with the skirt. The print times are CuraEngine estimates.
  Cost at ${PRICE_PER_KG:.2f}/kg. The fit test parts are for the first print only. The camera pole foot is optional.</p>
  {foot(2)}
</section>
<section class="page">
  <h2>Hardware</h2>
  <table class="tight" style="font-size:8.8pt">{tools}</table>
  <p style="font-size:9pt;color:#444">The electronics and the sources are in <code>docs/bom.md</code> of the project.</p>
  {foot(3)}
</section>
<section class="page">
  <h2>Print</h2>
  <table class="tight" style="font-size:8.6pt">{st}</table>
  <p style="font-size:10pt">The STL files are in their print orientation. Load them, do not turn them. The settings are for the LulzBot TAZ Workhorse.</p>
  <div class="grid6">{cards}</div>
  {foot(4)}
</section>"""


PART_NAMES = {"frame (stock)": "Frame (stock screws)",
              "y_front_left": "Y front base, left", "y_front_right": "Y front base, right",
              "y_idler_fork_left": "Y idler fork, left", "y_idler_fork_right": "Y idler fork, right",
              "y_motor_mount_left": "Y motor bracket, left", "y_motor_mount_right": "Y motor bracket, right",
              "y_idler_bracket_left": "Y idler bracket, left", "y_idler_bracket_right": "Y idler bracket, right",
              "y_chain_anchor": "Y chain anchor",
              "y_carriage_left": "Y carriage, left (X motor)",
              "y_carriage_right": "Y carriage, right (X idler)", "x_idler_fork": "X idler fork", "pen_carriage": "Pen carriage", "pen_slider": "Pen slider",
              "x_carriage_plate": "X plate", "mast_foot": "Camera pole foot (optional)"}


def fastener_page(n):
    """The fasteners of the model: the count for each part, the totals, and the screw length check."""
    rows = []
    for p, label in PART_NAMES.items():
        d = FAST["by_part"].get(p)
        if not d:
            continue
        txt = ", ".join(f"{v} × {k.replace(' x ', ' × ')}" for k, v in sorted(d.items()))
        rows.append(f'<tr><td>{label}</td><td class="n">{sum(d.values())}</td><td>{txt}</td></tr>')
    buy = {k: v for k, v in FAST["by_item"].items() if "stock" not in k}
    stock = {k: v for k, v in FAST["by_item"].items() if "stock" in k}
    tot = ", ".join(f"{v} × {k.replace(' x ', ' × ')}" for k, v in buy.items())
    tst = ", ".join(f"{v} × {k.replace(' x ', ' × ')}" for k, v in stock.items())
    jt = "".join(f"<tr><td>{j['count']} × {j['item'].replace(' x ', ' × ')}</td><td>{j['name']}</td><td>{j['text']}</td></tr>"
                 for j in FAST["joints"])
    return f"""<section class="page">
  <h2>Fasteners</h2>
  <p style="font-size:9.5pt">The model has each screw, nut, washer, spacer and T-nut of the main build. The fit check moves
  them with the parts over the whole travel. No fastener touches a printed part, the frame, a belt or another fastener.
  The exceptions are the intended contacts: a T-nut in a slot, a screw in a motor thread or in a heat-set insert. The
  build uses 15 heat-set inserts: 3 long M5 inserts for wheel axles, 6 M3 inserts for the endstop boards and 6 M3 inserts for the belt jaws.
  The other M2 and M3 screws in plastic cut their own thread.</p>
  <table class="tight" style="font-size:7.8pt"><tr><th>Part</th><th class="n">Items</th><th>Fasteners</th></tr>{''.join(rows)}</table>
  <p style="font-size:8.2pt;margin-top:2mm"><b>To buy (in the model):</b> {tot}. Buy 2 more T-nuts as spares.
  <b>Stock:</b> {tst}.</p>
  {foot(n)}
</section>
<section class="page">
  <h2>Screw lengths</h2>
  <p style="font-size:9.5pt"><code>model.py</code> checks each screw length. A screw into a T-nut needs at least
  {S.TNUT_ENGAGE:.0f} mm of thread in the T-nut, and its tip must stay out of the core of the extrusion. A screw that cuts
  its own thread needs enough thread in the plastic and must not reach the end of the pilot hole. A screw with a nut
  must stand at least 1 mm out of the nut. The slot and T-nut sizes are estimates (<code>MEASURE.md</code>).</p>
  <table class="tight" style="font-size:8.4pt;margin-top:2mm"><tr><th>Screws</th><th>Joint</th><th>Length check</th></tr>{jt}</table>
  {foot(n + 1)}
</section>"""


def step_page(i, step, n):
    shot, title, need, items, note = step[:5]
    h = step[5] if len(step) > 5 else 120
    chips = "".join(f'<div class="chip">{x}</div>' for x in need)
    lis = "".join(f"<li>{t}</li>" for t in items)
    nt = f'<div class="note"><b>Note.</b> {note}</div>' if note else ""
    if isinstance(shot, list):
        # Two or more pictures side by side, each with a caption.
        cells = "".join(f'<figure style="flex:1;margin:0;text-align:center"><img src="{img(nm)}" style="max-width:100%;max-height:{h}mm">'
                        f'<figcaption style="font-size:10pt;margin-top:1mm">{cap}</figcaption></figure>' for nm, cap in shot)
        fig = f'<div class="fig" style="display:flex;gap:6mm;align-items:flex-end">{cells}</div>'
    else:
        fig = f'<div class="fig"><img src="{img(shot)}" style="max-height:{h}mm"></div>'
    return f"""<section class="page">
  <div class="head"><div class="num">{i}</div><div class="title">{title}</div></div>
  <div class="need">{chips}</div>
  {fig}
  <ol>{lis}</ol>{nt}
  {foot(n)}
</section>"""


def review_page(n):
    """The simplification of 2026-11-10: what changed, and the totals of the main build."""
    main = [p for p in PRINTS if not p[0].startswith("fit_")]
    t = sum(print_time(nm) * k for nm, _, k, _ in main)
    g = sum(FILAMENT[nm]["grams"] * k for nm, _, k, _ in main)
    return f"""<section class="page">
  <h2>The simplification</h2>
  <p>The build is simplified. The pen changer, the Pico W control
  pod, the two board housings, the bar end caps, the servo cover, the pen gauge and the X band with its two holders are gone.
  <code>REVIEW.md</code> has the findings and the reasons.</p>
  <ul style="font-size:11pt">
    <li>Each Y carriage is a flat 6 mm plate, as the stock CR-10 Z carriage plate, with only the features this plotter uses:
    the wheel bosses, the Y belt clamps, a beam saddle, the Y endstop striker; on the left the chain tab, the X motor wall
    and the X endstop wall; on the right the seat of the X idler fork. The wheel layout and the travel are unchanged.</li>
    <li>The breakout boards stand bare on two 4 mm nylon standoffs each, held by cable ties.</li>
    <li>The servo lead runs in a 1/2 inch split wire loom, in a free loop behind the beam, with one cable tie at each end.</li>
    <li>The X motor is a 42-34 ({S.XMOTOR_MASS:.0f} g); the Y motors are 42-40 ({S.MOTOR_MASS:.0f} g).</li>
  </ul>
  <p>The main build is now {sum(k for _, _, k, _ in main)} parts, {hm(t)}, {g:.0f} g of PLA, ${cost(g):.2f}
  (before the simplification: 27 parts, 30 h 28 min, 544 g, $10.88). The travel is {TRAVEL[0]:.0f} × {TRAVEL[1]:.0f} mm.</p>
  <h2 style="margin-top:6mm">Print settings</h2>
  <ul style="font-size:11pt">
    <li>Infill: 15 % gyroid. Top and bottom: 0.9 mm (3 layers).</li>
    <li>Walls: 3 lines (1.5 mm); 4 lines (2 mm) on the rail fit test.</li>
    <li>Outer walls 40 mm/s, skins 45 mm/s. At 0.3 mm layers the flow limit of the 0.5 mm nozzle (about 8 mm³/s) caps the
    other speeds near 55 mm/s.</li>
  </ul>
  {foot(n)}
</section>"""


def end_page(n):
    rows = "".join(f"<tr><td>{a}</td><td><code>{b}</code></td><td class=\"n\">{c}</td><td>{d}</td></tr>"
                   for a, b, c, d in ADJUST)
    return f"""<section class="page">
  <h2>Adjust the fit</h2>
  <p>Change the values in <code>shape.py</code>, run <code>make.sh</code>, and print the part again. <code>make.sh</code> checks
  the fit, the meshes, and the supports before it writes the files.</p>
  <table style="font-size:9pt"><tr><th>Problem</th><th>Value</th><th class="n">Now</th><th>Change</th></tr>{rows}</table>
  <div class="cols" style="margin-top:5mm">
    <div class="fig" style="margin:0"><img src="{img('up')}" style="max-height:80mm"></div>
    <div><p style="font-size:10.5pt">Pen up: the horn turns to {FIT['pen_up_deg']:.0f}° and lifts the slider
    {FIT['lift']:.1f} mm. Pen down: the horn is {FIT['tab_gap']:.0f} mm under the tab, and the pen rests on the paper.</p>
    <p style="font-size:10.5pt">The pen carriage holds the pen lift. Four M3 screws hold it
    on the front of the printed X plate. Printed jaws clamp the X belt ends in two pockets of the X plate, under the beam.</p></div>
  </div>
  {foot(n)}
</section>"""


def main():
    pages = [cover(), print_page(), "", "", fastener_page(5), ""]
    for i, st in enumerate(STEPS):
        pages.append(step_page(i + 1, st, len(pages) + 1))
    pages.append(review_page(len(pages) + 1))
    pages.append(end_page(len(pages) + 1))
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Pen plotter build guide</title>'
            f'<style>{CSS}</style></head><body>{"".join(p for p in pages if p)}</body></html>')
    src = BUILD / "build.html"
    src.write_text(html)
    subprocess.run(["chromium", "--headless", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={OUT}", src.as_uri()], check=True, capture_output=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
