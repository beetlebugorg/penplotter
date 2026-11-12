#!/usr/bin/env python3
"""Pen plotter parts: build the parts, check the fit, and write the files.
Run with: uv run --no-project --with build123d python model.py

Fit check:
  - The pen carriage, the Y carriages and the brackets do not touch the frame, the wheels, the
    motors, the switches or each other, over the whole travel.
  - Each V-wheel sits in its slot: it touches the two flanks of the V when the eccentric spacer
    pushes it in, and no other part of the wheel touches the extrusion.
  - The pen carriage is clear of the wheel bolt heads of the stock X plate. The pen reaches the table.
  - The front features of the base stand on the back layer (no support in print).
  - The servo fits its pocket. The horn does not touch the base.
  - The slider is clear of the base at pen down, at pen up, and on the path off the top of the rail.
  - The horn is clear of the tab at pen down. At pen up, the horn lifts the slider by LIFT.
  - Pens of 8 and 15 mm fit the V. The clamp screw reaches the 8 mm pen.
  - The pen is clear of the shelf and the base.
  - The breakout boards (bare, on two standoffs each): each board, its plugs, the wire bends and the
    big plug cable are clear of the moving parts. The head board rides on the gantry and is clear of
    the frame, the brackets, the mast and the base board over the whole Y travel, and of the X
    carriage and the servo loom over the X travel.
  - The servo loom: a slack loop (catenary) behind the beam; its lowest point stays above the paper and
    it is clear of the rigid parts over the X and Y travel.
Output:
  cad/<part>.step, cad/pen-lift-assembly.step, cad/table-plotter-assembly.step (the boards and the
  control box)
  stl/<part>.stl                each printed part, in its print orientation
  build/mesh/*.stl              the meshes for the images, build/manifest.json, build/parts.json
"""

import json
import math
import os
import sys

from build123d import Align, Color, Compound, Cylinder, Location, Plane, Pos, Rot, export_step, export_stl
MINZ = (Align.CENTER, Align.CENTER, Align.MIN)

import fasteners as F
import parts as P
import shape as S

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

COLOURS = {"petg": S.ACCENT, "extrusion": "#2B2E33", "plate": "#A7A49C", "servo": "#2F5DA8", "horn": "#F2F2F2",
           "pen": "#2A2A2A", "steel": "#6E6E6E", "pcb": "#2E6B3A"}


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def log(msg):
    print(msg, flush=True)


def overlap(a, b):
    ba, bb = a.bounding_box(), b.bounding_box()
    if (ba.min.X > bb.max.X or bb.min.X > ba.max.X or ba.min.Y > bb.max.Y or bb.min.Y > ba.max.Y
            or ba.min.Z > bb.max.Z or bb.min.Z > ba.max.Z):
        return 0.0
    common = a & b
    return 0.0 if common is None else common.volume


def _mirror_stl_x(src, dst):
    """Write the mirror image (x -> -x) of a binary STL, with the triangle winding turned over."""
    import struct
    data = open(src, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    out = bytearray(data[:84])
    for i in range(n):
        rec = data[84 + i * 50:84 + i * 50 + 50]
        f = list(struct.unpack("<12f", rec[:48]))
        nx, ny, nz, v1, v2, v3 = f[0:3], None, None, f[3:6], f[6:9], f[9:12]
        nx = [-f[0], f[1], f[2]]
        v1, v2, v3 = [-v1[0], v1[1], v1[2]], [-v2[0], v2[1], v2[2]], [-v3[0], v3[1], v3[2]]
        out += struct.pack("<12f", *nx, *v1, *v3, *v2) + rec[48:50]
    open(dst, "wb").write(bytes(out))


# The render material for each material of a context_detail kit: dark parts and bought (light) parts.
CD_MAT = {"steel": "steel", "gold": "steel", "label": "steel", "nylon": "steel", "motor_stack": "steel",
          "smd_light": "steel", "plunger": "servo", "servo": "servo"}


def cd_meshes(prefix, kit, grp):
    """One image mesh for each material of a context_detail kit: [(name, solid, mat, group)]."""
    out = []
    for m, sl in kit.items():
        if sl:
            out.append((f"{prefix}_{m}", Compound(children=sl), CD_MAT.get(m, "pen"), grp))
    return out


def _cd():
    try:
        import context_detail as CD
        return CD
    except Exception as e:                      # the detail models are for the views only
        log(f"  context_detail not used: {e}")
        return None


def _empty(sh):
    try:
        return sh.wrapped is None
    except AssertionError:
        return True


def print_pose(shape):
    """Centre on X and Y, bottom at Z = 0."""
    bb = shape.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape


def back_down(shape):
    """World -Y to print +Z: the back face (Y = 0) on the bed."""
    return Rot(-90, 0, 0) * shape


def front_down(shape):
    """Plate frame +Y up: the front face of the X carriage on the bed."""
    return Rot(90, 0, 0) * shape


def upside_down(shape):
    """Turn the part over: the platform of a bracket on the bed."""
    return Rot(180, 0, 0) * shape


def check(problems):
    base = P.base()
    if len(base.solids()) != 1:
        problems.append(f"the base is {len(base.solids())} solids")
    # Every front feature stands on the back layer: the part at Y < -BASE_T, moved back onto
    # the plane Y = -BASE_T + 0.1, must lie inside the back layer outline.
    # Take a thin slice of the front features just in front of the back layer, move it 0.4 mm
    # back into the back layer, and subtract the back layer. What is left hangs in the air.
    back = P.extrude(P.xz_face(P.footprint()), S.BASE_T, dir=P.MY)
    sl = base & P.box(-200, 200, -S.BASE_T - 0.2, -S.BASE_T - 0.1, -200, 200)
    if sl is not None and sl.volume > 0:
        out = (Pos(0, 0.4, 0) * sl) - back
        if out is not None and out.volume > 0.05:
            problems.append(f"a front feature hangs outside the back layer: {out.volume:.2f} mm3")

    servo = P.servo_body()
    v = overlap(servo, base)
    if v > 0.01:
        problems.append(f"the servo does not fit its pocket: {v:.2f} mm3")
    for deg in (S.PEN_DOWN_DEG, 15.0, S.PEN_UP_DEG):
        v = overlap(P.horn(deg), base)
        if v > 0.01:
            problems.append(f"the horn touches the base at {deg:.0f} deg: {v:.2f} mm3")

    # The slider on the rail.
    for z0, what in ((S.SLIDER_Z0, "pen down"), (S.SLIDER_Z0 + S.LIFT, "pen up"), (S.SHELF_TOP, "on the shelf")):
        v = overlap(P.slider(z0), base)
        if v > 0.01:
            problems.append(f"the slider touches the base ({what}): {v:.2f} mm3")
    for dz in range(0, int(S.RAIL_TOP - S.SHELF_TOP) + 6, 6):
        v = overlap(P.slider(S.SLIDER_Z0 + dz), base)
        if v > 0.01:
            problems.append(f"the slider touches the base {dz} mm up the rail: {v:.2f} mm3")
            break
    # Removal: the slider must not touch the horn when it goes up, with the horn at pen down.
    hd = P.horn(S.PEN_DOWN_DEG)
    for dz in range(int(S.LIFT) + 2, int(S.RAIL_TOP) + 2, 6):
        if overlap(P.slider(S.SLIDER_Z0 + dz), hd) > 0.01:
            problems.append(f"the slider hits the horn {dz} mm up the rail")
            break
    # The horn and the tab.
    if overlap(hd, P.slider()) > 0.01:
        problems.append("the horn touches the tab at pen down: the pen does not rest on the paper")
    hu = P.horn(S.PEN_UP_DEG)
    if overlap(hu, P.slider(S.SLIDER_Z0 + S.LIFT + 0.1)) > 0.01:
        problems.append("the horn goes into the tab at pen up")
    if overlap(hu, P.slider(S.SLIDER_Z0 + S.LIFT - 0.3)) < 0.001:
        problems.append("the horn does not lift the tab at pen up")
    # The horn and the servo case are clear of the slider at all angles.
    for deg in range(int(S.PEN_DOWN_DEG), int(S.PEN_UP_DEG) + 1, 10):
        lift = max(0.0, (S.tip_c(deg) - S.tip_c(S.PEN_DOWN_DEG)) - S.TAB_GAP * math.sqrt(2))
        if overlap(P.horn(deg), P.slider(S.SLIDER_Z0 + lift + 0.1)) > 0.01:
            problems.append(f"the horn goes into the slider at {deg} deg")
    if overlap(servo, P.slider(S.SLIDER_Z0 + S.LIFT)) > 0.01:
        problems.append("the slider touches the servo")

    # The pens.
    sl = P.slider()
    reach = {}
    for d in (S.PEN_MIN, S.PEN_MAX):
        pen = P.pen(d - 0.05, S.SLIDER_Z0 - 30.0)
        for name, other in (("slider", sl), ("base", base)):
            v = overlap(pen, other)
            if v > 0.01:
                problems.append(f"a {d:.0f} mm pen touches the {name}: {v:.2f} mm3")
        screw, x_head = P.clamp_screw(d)
        reach[d] = S.SLIDER_X0 - x_head      # the screw stands out of the slider by this much
        if reach[d] < 1.0:
            problems.append(f"the clamp screw is too short for a {d:.0f} mm pen")
    v = overlap(P.servo_body(), P.pen(S.PEN_MAX, S.SLIDER_Z0 - 30.0))
    if v > 0.01:
        problems.append("the pen touches the servo")
    return base, reach


# ================================================================ the table plotter

def head(z_pen_tip):
    """The moving head in the plate frame: the stock X carriage (plate, wheels, wheel bolts), the
    pen carriage, the slider at pen down, the servo, the horn, and a 12 mm pen with its tip at z_pen_tip."""
    return [("pen carriage", P.pen_carriage())] + P.x_carriage() + [
            ("slider", P.slider()),
            ("servo", P.servo_body()), ("horn", P.horn(S.PEN_DOWN_DEG)),
            ("pen", P.pen(S.PEN_SIZE_SIM, z_pen_tip))]


def dz():
    """The plate frame z of the table, negated: the pen tip goes down to the paper at PAPER_Z."""
    return S.PLATE_DZ - S.PAPER_Z


def y_wheel_items(c, side="left"):
    """The wheels, spacers, bolt heads and nuts of one Y carriage: [(name, solid)]."""
    items = [(f"{side} Y wheel {i}", w) for i, w in enumerate(P.y_wheels(c))]
    # The heat-set insert is in the wall of its hole by design: it is not a clash item.
    items += [(f"{side} Y wheel {n} {i}", s) for i, (n, s) in enumerate(P.y_wheel_stack(c)) if n != "insert"]
    if side == "right":
        items = [(n, P.mirror_x(s)) for n, s in items]
    return items


def frame_side(c):
    """The static and gantry solids at the left side, with the gantry at y = c."""
    bars = P.frame_bars()
    return [("left Y carriage", P.y_carriage(c, "motor")), ("left rail", bars["left rail"]), ("X motor", P.x_motor(c)),
            ("X switch", P.x_switch(c))] + y_wheel_items(c)


def right_side(c):
    bars = P.frame_bars()
    return [("right Y carriage", P.mirror_x(P.y_carriage(c, "idler"))), ("right rail", bars["right rail"]),
            ("X idler", P.x_idler(c)), ("X idler fork", P.x_idler_fork(c))] + y_wheel_items(c, "right")


def hits(moving, fixed):
    for a, sa in moving:
        for b, sb in fixed:
            if overlap(sa, sb) > 0.01:
                return f"{a} / {b}"
    return None


def search(lo, hi, bad, steps=9):
    """Bisection: bad(lo) is True, bad(hi) is False. Return the first good value (within 0.2 mm)."""
    for _ in range(steps):
        mid = (lo + hi) / 2
        if bad(mid):
            lo = mid
        else:
            hi = mid
    return hi


def check_wheels(problems):
    """Each wheel sits in its slot. At the design position the wheel only touches the flanks of
    the V. With the eccentric preload it presses into the flanks. No other part of a wheel, a
    spacer, a bolt or a nut touches the extrusion."""
    c = S.FRAME_Y / 2
    rail = P.rail_slotted()
    beam = P.beam_slotted(c)
    t = P.plate_offset(S.FRAME_X / 2, c)
    groups = [("Y", rail, P.y_wheels(c), P.y_wheels(c, S.WHEEL_PRELOAD)),
              ("X", beam, [t * w for w in P.x_wheels()], [t * w for w in P.x_wheels(S.WHEEL_PRELOAD)])]
    contact = {}
    for axis, ext, nominal, pressed in groups:
        for i, (w0, w1) in enumerate(zip(nominal, pressed)):
            v0, v1 = overlap(w0, ext), overlap(w1, ext)
            contact[f"{axis}{i}"] = round(v1, 2)
            if v0 > 0.01:
                problems.append(f"{axis} wheel {i} goes into the extrusion at its design position: {v0:.2f} mm3")
            if v1 < 0.05:
                problems.append(f"{axis} wheel {i} does not touch the slot with a {S.WHEEL_PRELOAD} mm preload")
            if v1 > 5.0:
                problems.append(f"{axis} wheel {i} goes too far into the slot: {v1:.2f} mm3")
    for n, s in y_wheel_items(c):
        if not n.startswith("left Y wheel ") or n[len("left Y wheel "):].isdigit():
            continue
        if overlap(s, P.frame_bars()["left rail"]) > 0.01:
            problems.append(f"the {n} touches the rail")
    for n, s in P.x_carriage():
        if "wheel" not in n and overlap(t * s, P.beam(c)) > 0.01:
            problems.append(f"the {n} touches the beam")
    # The eccentric spacers can reach the contact position.
    ecc_x = abs((S.PLATE_BEAM_Z + S.BEAM / 2 + S.WHEEL_OFF) - S.X_WHEELS[S.X_ECC][2])
    if ecc_x > S.ECC_RANGE:
        problems.append(f"the eccentric of the X plate must move {ecc_x:.2f} mm: more than its range")
    return contact, ecc_x


def check_frame(problems):
    """Fit check of the frame parts, and the travel limits of the pen."""
    d = dz()
    tip_z = -d                                  # the pen tip on the table, in the plate frame
    hd = head(tip_z)
    bars = P.frame_bars()
    c_mid = S.FRAME_Y / 2
    # The Y carriages: clear of the rail, the beam, the motor, the switch and their own wheels.
    car = P.y_carriage(c_mid, "motor")
    for name, sh in [("left rail", bars["left rail"]), ("X motor", P.x_motor(c_mid)), ("beam", P.beam(c_mid)),
                     ("X switch", P.x_switch(c_mid))] + y_wheel_items(c_mid):
        v = overlap(car, sh)
        if v > 0.01:
            problems.append(f"the left Y carriage touches the {name}: {v:.2f} mm3")
    car_r = P.mirror_x(P.y_carriage(c_mid, "idler"))
    for name, sh in [("right rail", bars["right rail"]), ("beam", P.beam(c_mid)), ("X idler", P.x_idler(c_mid)),
                     ("X idler fork", P.x_idler_fork(c_mid))] + \
            y_wheel_items(c_mid, "right"):
        v = overlap(car_r, sh)
        if v > 0.01:
            problems.append(f"the right Y carriage touches the {name}: {v:.2f} mm3")
    # The X idler fork at both ends of its travel: clear of the right carriage; the idler clear of the fork.
    for dx in S.XIDLER_TRAVEL:
        fk = P.x_idler_fork(c_mid, dx)
        for name, a, b_ in (("idler", P.x_idler(c_mid, dx), car_r), ("fork", fk, car_r), ("idler in the fork", P.x_idler(c_mid, dx), fk)):
            if overlap(a, b_) > 0.01:
                problems.append(f"the X {name} {dx:+.0f} mm along its travel touches the right Y carriage or the fork")
    if overlap(P.x_motor(c_mid), P.x_switch(c_mid)) > 0.01:
        problems.append("the X motor touches the X switch")
    # The carriage plate stays over the rail: nothing of it goes below the rail top.
    car_low = car.bounding_box().min.Z
    if car_low < S.RAIL_TOP_Z:
        problems.append(f"the Y carriage reaches down to z {car_low:.1f}, under the rail top")
    # Tool access. The 8 mm wrench on the hex of the eccentric spacer (the back outer wheel), between
    # the wheel and the plate, from outside the frame. The hex keys reach the outer bolt heads from below.
    x, y, _ = P.y_wheel_pos(c_mid)[S.YW_ECC]
    zh0, zh1 = S.YW_Z + S.WHEEL_T / 2 + 1.0, S.YP_Z0 - 1.0
    wrench = P.box(-80.0, x + 4.0, y - 6.0, y + 6.0, zh0, zh1)
    for name, sh in [("Y carriage", car), ("left rail", bars["left rail"])] + \
            [(n, w) for n, w in y_wheel_items(c_mid) if n.split()[-1].isdigit() and len(n.split()) == 4]:
        if overlap(wrench, sh) > 0.01:
            problems.append(f"the eccentric wrench touches the {name}")
    contact, ecc_x = check_wheels(problems)
    # The pen carriage on the printed X plate: clear of the plate (the bosses pass through it) and the wheels.
    pc = P.pen_carriage()
    if len(pc.solids()) != 1:
        problems.append(f"the pen carriage is {len(pc.solids())} solids")
    for n, s in P.x_carriage():
        v = overlap(pc, s)
        if v > 0.01:
            problems.append(f"the pen carriage touches the {n}: {v:.2f} mm3")
    # The moving head (not the wheels) does not touch the beam.
    t_mid = P.plate_offset(S.FRAME_X / 2, c_mid)
    for n, s in hd:
        if "wheel" in n:
            continue
        v = overlap(t_mid * s, P.beam(c_mid))
        if v > 0.01:
            problems.append(f"the {n} touches the beam: {v:.2f} mm3")
    # The pen reaches the table, and the rest of the head stays above it.
    low = min((t_mid * s).bounding_box().min.Z for n, s in hd if n != "pen") - S.PAPER_Z
    if low < 5.0:
        problems.append(f"the head is only {low:.1f} mm above the table")
    reach = d + S.SLIDER_Z0
    if not 10.0 <= reach <= 40.0:
        problems.append(f"the pen must stand {reach:.1f} mm out of the slider to reach the table")
    # The Y drive (static): the motor bracket, the motor, the pulley, the idler and its fork at both ends
    # of the fork travel: clear of each other and of the frame. The belt clear of all but the pulley and
    # the idler (it wraps them) and the clamp blocks of the carriage (it is clamped there).
    ydr = [("Y motor bracket", P.y_motor_mount()), ("Y motor", P.y_stepper()[0]), ("Y pulley", P.y_stepper()[1]),
           ("Y front base", P.y_front_base()), ("Y idler bracket", P.y_idler_bracket()), ("Y switch", P.y_switch())]
    for dy in S.YIDLER_TRAVEL + (0.0,):
        ydr2 = ydr + [("Y idler", P.y_idler(dy)), ("Y idler fork", P.y_idler_fork(dy))]
        for i, (n, sh) in enumerate(ydr2):
            for m, other in ydr2[i + 1:] + [(k, v) for k, v in bars.items()] + [("left Y carriage", car)]:
                if {n, m} in ({"Y idler", "Y idler fork"},):
                    if overlap(sh, other) > 0.01:
                        problems.append(f"the Y idler touches its fork at dy {dy:+.0f}")
                    continue
                if overlap(sh, other) > 0.01:
                    problems.append(f"the {n} touches the {m} (Y fork at dy {dy:+.0f})")
    belt = P.y_belt(c_mid)
    for m, other in [("left Y carriage", car), ("beam", P.beam(c_mid)), ("X motor", P.x_motor(c_mid)),
                     ("Y motor bracket", P.y_motor_mount()), ("Y motor", P.y_stepper()[0]), ("Y front base", P.y_front_base()),
                     ("Y idler fork", P.y_idler_fork()), ("Y switch", P.y_switch())] + y_wheel_items(c_mid) + \
            [(k, v) for k, v in bars.items()]:
        if overlap(belt, other) > 0.01:
            problems.append(f"the Y belt touches the {m}")
    wrap = 180.0                                     # the belt runs vertical between the idlers and the pulley
    xp_mid = S.FRAME_X / 2

    def head_at(xp, c):
        t = P.plate_offset(xp, c)
        return [(n, t * s) for n, s in hd]

    ft = P.feet()
    # The belt itself is not a stop: it runs through the omega. The clips sit inside the pockets.
    front_nf = [("front bar", bars["front bar"]), ("Y front base", P.y_front_base()), ("Y idler bracket", P.y_idler_bracket()),
                ("Y idler fork", P.y_idler_fork()),
                ("Y idler", P.y_idler()), ("Y switch", P.y_switch())]
    back_nf = [("back bar", bars["back bar"]), ("Y motor bracket", P.y_motor_mount()), ("Y motor", P.y_stepper()[0]),
               ("Y pulley", P.y_stepper()[1])]
    front_nf += [("right " + n, P.mirror_x(s)) for n, s in front_nf[1:] if n != "Y switch"]
    front_nf += [("right Y switch", P.es_parts("y_right")["body"])]
    back_nf += [("right " + n, P.mirror_x(s)) for n, s in back_nf[1:]]
    front = front_nf + [("front left foot", ft[0])]
    back = back_nf + [("back left foot", ft[1])]

    def gantry_low(c):
        return [("car", P.y_carriage(c, "motor")), ("X motor", P.x_motor(c)), ("car right", P.mirror_x(P.y_carriage(c, "idler"))),
                ("X idler fork", P.x_idler_fork(c))] + y_wheel_items(c) + y_wheel_items(c, "right")

    def bad_front(c):
        return hits(head_at(xp_mid, c), front) is not None or hits(gantry_low(c), front) is not None

    def bad_back(c):
        return hits(head_at(xp_mid, c), back) is not None or hits(gantry_low(c), back) is not None
    c_min = search(S.BAR_D, c_mid, bad_front) + 0.5
    c_max = S.FRAME_Y - (search(S.BAR_D, c_mid, lambda c: bad_back(S.FRAME_Y - c)) + 0.5)
    # The same with no feet: the printed feet must not shorten the travel.
    c_min_nf = search(S.BAR_D, c_mid, lambda c: hits(head_at(xp_mid, c), front_nf) is not None
                      or hits(gantry_low(c), front_nf) is not None) + 0.5
    c_max_nf = S.FRAME_Y - (search(S.BAR_D, c_mid, lambda c: hits(head_at(xp_mid, S.FRAME_Y - c), back_nf) is not None
                                   or hits(gantry_low(S.FRAME_Y - c), back_nf) is not None) + 0.5)
    left = frame_side(c_mid)
    right = right_side(c_mid)
    xp_min = search(0.0, xp_mid, lambda xp: hits(head_at(xp, c_mid), left) is not None) + 0.5
    xp_max = S.FRAME_X - (search(0.0, xp_mid, lambda xp: hits(head_at(S.FRAME_X - xp, c_mid), right) is not None) + 0.5)
    # The ends: check again, with the gantry at both ends of Y.
    for xp in (xp_min, xp_max):
        for c in (c_min, c_max):
            fixed = frame_side(c) + right_side(c) + front + back
            h = hits(head_at(xp, c), fixed)
            if h:
                problems.append(f"at the travel limit x {xp:.0f}, y {c:.0f}: {h}")
    # What stops the head at each end: the first part that touches 1 mm further.
    stops = {"x min": hits(head_at(xp_min - 1.0, c_mid), left), "x max": hits(head_at(xp_max + 1.0, c_mid), right),
             "y min": hits(head_at(xp_mid, c_min - 1.0), front) or hits(gantry_low(c_min - 1.0), front),
             "y max": hits(head_at(xp_mid, c_max + 1.0), back) or hits(gantry_low(c_max + 1.0), back)}
    # The endstops: the X toe and the Y carriage front edge at the travel limits.
    # The overtravel past the click of each lever at the hard stop (see check_endstops).
    x_gap = P.es_click("x", c_min)[0] - (xp_min + S.X_TRIGGER[0])
    y_gap = P.es_click("y_left")[1] - P.y_striker(c_min, "motor").bounding_box().min.Y
    tip_dx = S.V_X - S.PEN_SIZE_SIM / 2 * math.sqrt(2)
    lim = {"xp": (xp_min, xp_max), "c": (c_min, c_max), "dz": d,
           "home_pen": (xp_min + tip_dx, c_min - S.PLATE_FRONT + S.PEN_CY),
           "travel": (xp_max - xp_min, c_max - c_min),
           "pen_reach": reach, "head_low": low, "stops": stops, "switch_gap": (x_gap, y_gap),
           "contact": contact, "ecc_x": ecc_x, "car_low": car_low, "wrap": wrap,
           "c_nofeet": (c_min_nf, c_max_nf),
           "stops_nofeet": {"y min": hits(head_at(xp_mid, c_min_nf - 1.0), front_nf) or hits(gantry_low(c_min_nf - 1.0), front_nf),
                            "y max": hits(head_at(xp_mid, c_max_nf + 1.0), back_nf) or hits(gantry_low(c_max_nf + 1.0), back_nf)}}
    return lim


def ydrive_items(c=None):
    """The left Y drive (static now): the motor, the pulley, the idler."""
    body, pulley = P.y_stepper()
    return [("Y motor", body), ("Y pulley", pulley), ("Y idler", P.y_idler())]


def ydrive_items_right(c):
    return [("right " + n, P.mirror_x(sh)) for n, sh in ydrive_items(c)]


def y_static_items():
    """The static Y parts of both sides: the front bases, the idler forks, the motor brackets, the switches, the
    motors, the pulleys and the idlers."""
    left = [("Y front base", P.y_front_base()), ("Y idler bracket", P.y_idler_bracket()), ("Y idler fork", P.y_idler_fork()),
            ("Y motor bracket", P.y_motor_mount()),
            ("Y switch", P.y_switch())] + ydrive_items()
    return left + [("right " + n, P.mirror_x(sh)) for n, sh in left]


CTRL_X1 = -70.0                  # the right side of the stock control box (x): left of the Y chain


def ctrl_box():
    return P.box(CTRL_X1 - S.CTRL_BOX[0], CTRL_X1, 70.0, 70.0 + S.CTRL_BOX[1], 0.0, S.CTRL_BOX[2])


LOOM_SOFT = ("head cable", "head xh")   # the head harness cable (the fixed tie is on it) and the wire bends of the XH plugs
LOOM_REST = ("back bar",)                # the loop may lie on the top of the back bar at the back of the Y travel (reported)


def check_cables(problems, lim):
    """The moving cables: the Y chain over the Y travel and the servo loom over the X travel. The chain
    touches nothing but its own end mounts. The chain is long enough, and its bend stays inside the frame
    length. The loom (a catenary of fixed length) stays above the paper and clear of the rigid parts; it
    may touch the head harness cable and the wire bends of the XH plugs (soft)."""
    c0, c1 = lim["c"]
    x0, x1 = lim["xp"]
    xm = (x0 + x1) / 2
    ym0, _, yf = P.y_chain_points(c0)
    if S.YCH_RUNS < yf - ym0:
        problems.append(f"the Y chain is too short: the runs need {yf - ym0:.0f} mm")
    if abs(x0 - S.XP_TRAVEL[0]) > 0.2 or abs(x1 - S.XP_TRAVEL[1]) > 0.2:
        problems.append(f"XP_TRAVEL in shape.py is not the X travel of the fit check ({x0:.2f}, {x1:.2f})")
    st = ctx_static() + [("control box", ctrl_box())]
    for i in range(7):
        c = c0 + (c1 - c0) * i / 6
        ch = P.y_chain(c)
        for n, sh in st + ctx_gantry(c) + ctx_carriage(xm, c):
            if n in ("Y chain", "Y chain anchor") or (n == "left Y carriage"):
                continue
            if overlap(ch, sh) > 0.01:
                problems.append(f"the Y chain at gantry y {c:.0f} touches the {n}")
                break
        if overlap(ch, P.y_carriage(c, "motor")) > 0.01 or overlap(ch, P.y_chain_anchor()) > 0.01:
            problems.append(f"the Y chain at gantry y {c:.0f} goes into its tab or its anchor")
    # The servo loom at the X ends, the middle, and where the chord of the loop is 0 (the deepest sag).
    x_deep = S.LOOM_FIX_X - S.LOOM_DX
    loom = {}
    for name, xp in (("X 0", x0), ("X mid", xm), ("X full", x1), ("deepest", min(max(x_deep, x0), x1))):
        rec = {"xp": round(xp, 1)}
        for c in (c0, c1):
            lm = P.x_loom(c, xp)
            low, lx = P.x_loom_lowest(c, xp)
            rec["low_z"], rec["low_x"] = round(low, 1), round(lx, 1)
            if low <= S.PAPER_Z:
                problems.append(f"the servo loom touches the paper at X plate x {xp:.0f} (lowest point z {low:.1f})")
            gaps, soft = [], set()
            for n, sh in st + ctx_gantry(c) + ctx_carriage(xp, c):
                if n.startswith(LOOM_SOFT):
                    if overlap(lm, sh) > 0.01:
                        soft.add(n)
                    continue
                if n.startswith(LOOM_REST):
                    if overlap(lm, sh) > 0.01:
                        top = sh.bounding_box().max.Z
                        rec.setdefault("rests", []).append(f"lies on the {n} top (z {top:.0f}) at gantry y {c:.0f}: "
                                                           f"the free loop reaches z {low:.1f}")
                    continue
                if overlap(lm, sh) > 0.01:
                    problems.append(f"the servo loom at X plate x {xp:.0f}, gantry y {c:.0f} touches the {n}")
                    continue
                if c == c0:
                    try:
                        gaps.append((lm.distance_to(sh), n))
                    except Exception:
                        pass
            if c == c0:
                rec["gaps"] = [(round(d, 1), n) for d, n in sorted(gaps)[:3]]
                rec["soft"] = sorted(soft)
        loom[name] = rec
    pts = P.x_loom_points(c0, x0)
    end = (pts[1][2] - pts[0][2]) + (pts[2][1] - pts[1][1])
    loom_len = P.loom_len() + end + S.LOOM_FIX_DOWN
    return {"y_chain_len": S.YCH_RUNS + math.pi * S.YCH_R + 2 * S.YCH_END, "x_loom_len": loom_len,
            "x_loop_len": P.loom_len(), "loom": loom, "loom_low": min(r["low_z"] for r in loom.values()) - S.PAPER_Z}


def foot_swept(f, dy):
    """The foot f swept from y to y - dy: the space that a gantry part at the front end of the travel
    must miss, so that the part at y + dy misses the foot."""
    bb = f.bounding_box()
    r, cx, cy = (bb.max.X - bb.min.X) / 2, (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2
    return (P.box(cx - r, cx + r, cy - dy, cy, bb.min.Z, bb.max.Z) + f + Pos(0, -dy, 0) * f)


def check_endstops(problems, lim):
    """The Creality endstop boards. At the hard stop of each axis the trigger is past the click of the
    lever by ES_OVERTRAVEL, in line with the click point, and clear of the board and the switch body.
    The plug zone (the plug and its wire bend) stays clear of every part over the full travel."""
    c0, c1 = lim["c"]
    x0, x1 = lim["xp"]
    lo, hi = S.ES_OVERTRAVEL
    out = {}
    # Y: the striker column of each carriage.
    for w, end in (("y_left", "motor"), ("y_right", "idler")):
        st = P.y_striker(c0, end)
        if end == "idler":
            st = P.mirror_x(st)
        bb = st.bounding_box()
        cx, cy, cz = P.es_click(w)
        ot = cy - bb.min.Y
        out[w] = round(ot, 2)
        if not (lo <= ot <= hi):
            problems.append(f"the {w} endstop: the striker goes {ot:.1f} mm past the click (want {lo}-{hi})")
        if not (bb.min.X <= cx <= bb.max.X and bb.min.Z <= cz <= bb.max.Z):
            problems.append(f"the {w} striker is not in line with the click point of the lever")
        es = P.es_parts(w)
        gantry = ctx_gantry(c0) + y_wheel_items(c0) + y_wheel_items(c0, "right")
        h = hits(gantry, [("board", es["body"]), ("plug zone", es["plug_zone"])])
        if h:
            problems.append(f"the {w} endstop board or plug zone touches {h} at the front stop")
        h = hits([("plug zone", es["plug_zone"])], [(n, s) for n, s in ctx_static() if "switch" not in n and "front base" not in n.lower()])
        if h:
            problems.append(f"the {w} plug zone touches {h}")
    # X: the trigger lug at the top left of the X plate.
    cx, cy, cz = P.es_click("x", c0)
    lx0, lx1, lz0, lz1, ld = S.X_TRIGGER
    xf = x0 + lx0
    ot = cx - xf
    out["x"] = round(ot, 2)
    if not (lo <= ot <= hi):
        problems.append(f"the X endstop: the trigger lug goes {ot:.1f} mm past the click (want {lo}-{hi})")
    zb0, zb1 = S.PLATE_DZ + lz0, S.PLATE_DZ + lz1
    yb0, yb1 = c0 - S.PLATE_FRONT - ld, c0 - S.PLATE_FRONT
    if not (zb0 <= cz <= zb1 and yb0 <= cy <= yb1):
        problems.append("the trigger lug is not in line with the click point of the X endstop lever")
    for xp in (x0, (x0 + x1) / 2, x1):
        for c in (c0, c1):
            es = P.es_parts("x", c)
            h = hits(ctx_carriage(xp, c), [("X board", es["body"]), ("X plug zone", es["plug_zone"])])
            if h:
                problems.append(f"the X endstop board or plug zone touches {h} (X plate x {xp:.0f})")
                break
    es = P.es_parts("x", c0)
    h = hits([("X plug zone", es["plug_zone"])], [(n, s) for n, s in ctx_gantry(c0) if n not in ("X switch",)])
    if h:
        problems.append(f"the X plug zone touches {h}")
    return out



def check_x_belt(problems, lim):
    """The X belt in the slot channels of the beam (the stock CR-10 path): clear of the slot walls,
    the lips and the core, and clear of the V-wheel tips over it. The wheel tip gap must be 0.3 mm or
    more (ESTIMATE of the tip depth: MEASURE.md). Returns the gaps (mm)."""
    c = S.FRAME_Y / 2
    x0, x1 = 150.0, 250.0
    beam = P.beam_real(c, x0, x1)
    t, w = S.BELT_T, S.BELT_W
    out = {}
    for name, z in (("bottom run", S.XB_RUNS[0]), ("top run", S.XB_RUNS[1])):
        run = P.box(x0, x1, c + S.XB_Y - w / 2, c + S.XB_Y + w / 2, z - t / 2, z + t / 2)
        if overlap(run, beam) > 0.001:
            problems.append(f"the X belt {name} touches the slot of the beam")
        out[name] = round(run.distance_to(beam), 2)
    # The wheel tips over the belt: the eccentric preload pushes the top right wheel in.
    tip = S.WHEEL_TIP_DEPTH + S.WHEEL_PRELOAD
    gap = S.XB_DEPTH - t / 2 - tip
    out["wheel tip"] = round(gap, 2)
    if gap < 0.3:
        problems.append(f"the X wheel tips come within {gap:.2f} mm of the X belt (want 0.3 or more)")
    # The side gaps in the channel and the slot opening at the clamp exit (the stock layout: the belt
    # passes the opening there).
    out["side"] = round((S.SLOT_CH_W - w) / 2, 2)
    out["opening"] = round((S.SLOT_OPEN - w) / 2, 2)
    return out


def check_feet(problems, lim):
    """The rubber feet stand under the long rails, near the corners. Each foot must miss every moving
    part over the full travel, the Y chain at each end, the chain anchor arm, and the inner wheel path.
    The check sweeps each foot over the full Y travel, so it covers every gantry position. Returns the
    smallest gaps (mm)."""
    ft = P.feet()
    names = ["front left foot", "back left foot", "front right foot", "back right foot"]
    c0, c1 = lim["c"]
    x0, x1 = lim["xp"]
    # Envelope: the inner wheel path is at x 45.5 and more; the chain anchor arm at x 15 and less.
    for n, f in zip(names, ft):
        bb = f.bounding_box()
        xi = bb.max.X if bb.min.X < S.FRAME_X / 2 else S.FRAME_X - bb.min.X
        xo = bb.min.X if bb.min.X < S.FRAME_X / 2 else S.FRAME_X - bb.max.X
        if xi > S.YT_LEG_X[1]:
            problems.append(f"the {n} reaches x {xi:.1f}: into the inner wheel path (x {S.YT_LEG_X[1]})")
        if xo < 15.0 and bb.max.Y > S.YCH_ANCHOR_Y[0] and bb.min.Y < S.YCH_ANCHOR_Y[1]:
            problems.append(f"the {n} reaches x {xo:.1f}: onto the chain anchor arm")
    moving = ctx_gantry(c0) + y_wheel_items(c0) + y_wheel_items(c0, "right")
    moving += ctx_carriage(x0, c0) + ctx_carriage(x1, c0)
    swept = [(n, foot_swept(f, c1 - c0)) for n, f in zip(names, ft)]
    h = hits(moving, swept)
    if h:
        problems.append(f"a moving part touches a foot in the Y travel: {h}")
    static = [("Y chain anchor", P.y_chain_anchor())] + [(f"Y chain at y {c:.0f}", P.y_chain(c)) for c in (c0, c1)]
    static += [(n, s) for n, s in y_static_items()]
    h = hits(static, list(zip(names, ft)))
    if h:
        problems.append(f"a foot touches {h}")
    def near(f, items):
        fb = f.bounding_box()
        return [s for _, s in items if s.bounding_box().min.X < fb.max.X + 40 and s.bounding_box().max.X > fb.min.X - 40]

    gap = {}
    for (n, f), (_, sw) in zip(zip(names, ft), swept):
        g_m = min([sw.distance_to(s) for s in near(sw, moving)] or [99.0])
        g_s = min([f.distance_to(s) for s in near(f, static)] or [99.0])
        gap[n] = (round(g_m, 1), round(g_s, 1))
    return gap


def check_mast(problems):
    """The camera pole: the foot on the back bar, the pole in the socket, clear of the brackets and
    the bar screw heads."""
    bars = P.frame_bars()
    foot, pole = P.mast_foot(), P.pole()
    for name, a, b in (("pole foot / back bar", foot, bars["back bar"]), ("pole foot / pole", foot, pole),
                       ("pole / back bar", pole, bars["back bar"]), ("pole foot / camera", foot, P.camera())):
        v = overlap(a, b)
        if v > 0.01:
            problems.append(f"{name} overlap: {v:.2f} mm3")
    others = y_static_items()
    others += [(f"bar screw head {i}", h) for i, h in enumerate(P.bar_screw_heads())]
    for name, other in others:
        if overlap(foot, other) > 0.01:
            problems.append(f"the pole foot touches the {name}")
    if foot.bounding_box().min.Z < -1e-6:
        problems.append("the pole foot goes below the table")
    # The pole sits in the socket: the gap all round, the floor under it.
    grip = S.MFOOT_TOP - S.MFOOT_FLOOR
    if grip < 30.0:
        problems.append(f"the pole socket is only {grip:.0f} mm deep")
    return grip


def board_world(kind, c=None):
    """The board items (board, plugs, wire bends, cable, standoffs) of one breakout board, in frame coordinates."""
    tf = P.brk_tf(kind, c)
    return [(f"{kind} {n}", tf * b) for n, b in P.brk_board(kind)]


def check_boards(problems, lim):
    """The two bare breakout boards. The standoffs stand on the extrusion face. The base board is clear
    of the frame, the brackets, the motors and the mast. The head board, its plugs, the wire bends and the
    big plug cable are clear of the frame, the brackets, the mast and the base board over the whole Y
    travel, and of the X carriage over the X travel. The beam and the back bar may touch
    only the standoffs."""
    bars = P.frame_bars()
    c0, c1 = lim["c"]
    # Each standoff stands on its extrusion face, beside the slot opening: moved 0.2 mm into the
    # extrusion (with its slots), the whole ring of the standoff is in material.
    bar = Pos(0, 0, S.BAR_SLOT_Z[0] - S.BZ) * P.beam_real(S.FRAME_Y - S.BAR_D / 2, 0.0, S.FRAME_X)
    for kind, host, what in (("head", P.beam_real(c0), "beam"), ("base", bar, "back bar")):
        for n, s in board_world(kind, c0):
            if n.startswith(f"{kind} standoff"):
                ring = math.pi * (S.BRD_STANDOFF_D ** 2 - 3.2 ** 2) / 4
                if overlap(Pos(0, -0.2, 0) * s, host) < 0.95 * 0.2 * ring:
                    problems.append(f"the {n} is not on the face of the {what} (the slot opening is under it)")
    fixed = [("back bar", bars["back bar"]), ("left rail", bars["left rail"]),
             ("pole foot", P.mast_foot()), ("pole", P.pole())] + y_static_items()
    base = board_world("base")
    h = hits([(n, s) for n, s in base if "standoff" not in n], fixed)
    if h:
        problems.append(f"the base board: {h}")
    fixed += [("camera", P.camera()), ("front bar", bars["front bar"])] + base
    fixed += [(f"bar screw head {i}", h) for i, h in enumerate(P.bar_screw_heads())]
    fixed += [(f"foot {i}", f) for i, f in enumerate(P.feet())]
    # The gantry over the whole Y travel: the head board against the static parts, and the gantry
    # parts against the base board.
    for i in range(7):
        c = c0 + (c1 - c0) * i / 6
        head = board_world("head", c)
        gantry = [("beam", P.beam(c)), ("left Y carriage", P.y_carriage(c, "motor")), ("X motor", P.x_motor(c)),
                  ("X switch", P.x_switch(c)), ("right Y carriage", P.mirror_x(P.y_carriage(c, "idler"))),
                  ("X idler", P.x_idler(c)), ("X idler fork", P.x_idler_fork(c))] + y_wheel_items(c) + y_wheel_items(c, "right")
        gantry += ydrive_items(c) + ydrive_items_right(c)
        h = hits([(n, s) for n, s in head if "standoff" not in n], fixed + gantry)
        if h:
            problems.append(f"the head board at gantry y {c:.0f}: {h}")
            break
        h = hits(gantry + [("Y chain", P.y_chain(c))], [(n, s) for n, s in base if "standoff" not in n])
        if h:
            problems.append(f"the base board at gantry y {c:.0f}: {h}")
            break
    # The X carriage and the pen carriage over the X travel, with the gantry at the back.
    head = board_world("head", c1)
    moving = [("pen carriage", P.pen_carriage())] + P.x_carriage()
    for i in range(9):
        xp = lim["xp"][0] + (lim["xp"][1] - lim["xp"][0]) * i / 8
        t = P.plate_offset(xp, c1)
        h = hits(head, [(n, t * s) for n, s in moving])
        if h:
            problems.append(f"the head board at pen carriage x {xp:.0f}: {h}")
    hz = min(s.bounding_box().min.Z for _, s in head)
    bz = max(s.bounding_box().max.Z for _, s in base)
    hy = max(s.bounding_box().max.Y for _, s in head)
    return {"head_low_z": hz, "base_top_z": bz, "head_back_y": hy}


# ================================================================ fasteners

def _strip(n):
    for side in ("left ", "right "):
        if n.startswith(side):
            return n[len(side):]
    return n


def allowed(f, name):
    """True if the fastener f may touch the context solid name (an intended engagement)."""
    n = _strip(name)
    for a in f.allow:
        if n == a or n.endswith(" " + a) or (n.startswith(a + " ") and n[len(a) + 1:].isdigit()):
            return True
    return False


def ctx_static():
    bars = P.frame_bars()
    out = list(bars.items())
    out += [(f"foot {i}", f) for i, f in enumerate(P.feet())]
    out += y_static_items()
    out += [("Y chain anchor", P.y_chain_anchor())]
    out += [("pole foot", P.mast_foot()), ("pole", P.pole()), ("camera", P.camera())]
    out += board_world("base")
    return out


def ctx_gantry(c):
    out = [("left Y carriage", P.y_carriage(c, "motor")), ("right Y carriage", P.mirror_x(P.y_carriage(c, "idler"))),
           ("beam", P.beam(c)), ("X motor", P.x_motor(c)), ("X idler", P.x_idler(c)), ("X idler fork", P.x_idler_fork(c)),
           ("X switch", P.x_switch(c))]
    out += [(n, s) for side in ("left", "right") for n, s in y_wheel_items(c, side) if n.split()[-1].isdigit() and len(n.split()) == 4]
    out += board_world("head", c)
    out += [("Y belt", P.y_belt(c)), ("right Y belt", P.mirror_x(P.y_belt(c)))]
    return out


def ctx_carriage(xp, c):
    t = P.plate_offset(xp, c)
    return [(n, t * s) for n, s in head(-dz()) if not n.startswith("X bolt")] + [("X belt", P.x_belt_loop(c, xp))]


def check_fasteners(problems, lim):
    """The fasteners: each screw length, and no clash with the printed parts, the frame, the
    motors, the belts or each other, at the ends and the middle of the travel. A fastener may touch
    only the solids in its allow list (a T-nut in a bar slot, a screw in a motor thread)."""
    c0, c1 = lim["c"]
    x0, x1 = lim["xp"]
    cm, xm = (c0 + c1) / 2, (x0 + x1) / 2
    items, joints = F.build(cm, xm)
    for j in joints:
        ok, txt = F.check_joint(j)
        if not ok:
            problems.append(f"screw length: {j.name} ({j.item}): {txt}")
    found = []
    st = ctx_static()
    configs = [(cm, xm), (c0, x0), (c0, x1), (c1, x0), (c1, x1), (c0, xm), (c1, xm),
               (c0 + (c1 - c0) / 4, xm), (c0 + 3 * (c1 - c0) / 4, xm)]
    for k, (c, xp) in enumerate(configs):
        its = items if k == 0 else F.build(c, xp)[0]
        ctx = st + ctx_gantry(c) + ctx_carriage(xp, c)
        for f in its:
            for n, sh in ctx:
                if allowed(f, n):
                    continue
                if overlap(f.solid, sh) > 0.01:
                    found.append(f"{f.name} ({f.item}) / {n} at gantry y {c:.0f}, X plate x {xp:.0f}")
        # The fasteners against each other (moving groups at this position).
        for i, a in enumerate(its):
            for b in its[i + 1:]:
                if k > 0 and a.group == b.group:
                    continue
                if overlap(a.solid, b.solid) > 0.01:
                    found.append(f"{a.name} / {b.name} at gantry y {c:.0f}, X plate x {xp:.0f}")
    for msg in dict.fromkeys(found):
        problems.append("fastener clash: " + msg)
    by_item, by_part = F.counts(items)
    return {"items": items, "joints": joints, "by_item": by_item, "by_part": by_part, "configs": len(configs)}


# The sim files that context_detail.py writes (the bought parts with detail).
DETAIL_FILES = ("x_motor", "y_stepper_left", "y_stepper_right", "y_endstops", "head_board", "base_board", "servo",
                "horn", "pen")


# The printed part or stock item that each fastener holds, and the sim2 file that draws it. "frame"
# means the sim draws it itself (bars, rails, beam, wheels, motors).
SIM_HOST = {"y_carriage_left": "y_carriage_left", "y_carriage_right": "y_carriage_right",
            "y_front_left": "y_front_left", "y_front_right": "y_front_right",
            "y_chain_anchor": "y_chain_anchor", "x_idler_fork": "x_idler_fork",
            "mast_foot": "mast_foot", "pen_carriage": "pen_carriage", "pen_slider": "pen_slider",
            "x_carriage_plate": "x_carriage_plate", "frame (stock)": "frame",
            "y_motor_mount_left": "y_motor_mount_left", "y_motor_mount_right": "y_motor_mount_right",
            "y_idler_fork_left": "y_idler_fork_left", "y_idler_fork_right": "y_idler_fork_right",
            "y_idler_bracket_left": "y_idler_bracket_left", "y_idler_bracket_right": "y_idler_bracket_right"}
# The printed parts of the main build that have a place on the machine (not the fit tests).
PLACED = ("y_carriage_left", "y_carriage_right", "y_front_left", "y_front_right",
          "y_motor_mount_left", "y_motor_mount_right", "y_idler_fork_left", "y_idler_fork_right", "y_idler_bracket_left",
          "y_idler_bracket_right", "mast_foot", "x_carriage_plate",
          "y_chain_anchor", "x_idler_fork", "pen_carriage", "pen_slider")


def _into_insert(f, fitems):
    """True if the screw f goes into a heat-set insert (an insert centre on its axis)."""
    from build123d import Vector
    p0, dv = Vector(*f.meta["p"]), Vector(*f.meta["d"]).normalized()
    for g in fitems:
        if g.kind == "insert" and "p" in g.meta:
            q = Vector(*g.meta["p"]) - p0
            if (q - dv * q.dot(dv)).length < 0.5 and 0 <= q.dot(dv) <= f.meta["length"] + 1:
                return True
    return False


def check_holes(problems, fitems, hosts):
    """The material round each screw hole and each insert in a printed part. For a screw: a ring of
    1 x d (M3: 3 mm, M5: 5 mm) round the hole, over the length where the screw is in the part. For a
    heat-set insert: a ring out to 1.5 x its outside diameter, over its depth. At least HOLE_FILL_MIN
    of each ring must be material. hosts maps a part name to its solid at the same position as the
    fasteners. Returns the result lines."""
    from build123d import Vector
    lines = []
    for f in fitems:
        m = f.meta
        host = hosts.get(f.part)
        if not m or host is None or "p" not in m or f.kind not in ("screw", "insert"):
            continue
        if f.kind == "screw" and _into_insert(f, fitems):
            continue                       # the insert check covers this hole (1.5 x the insert diameter)
        d = int(f.size[1:])
        p0, dv = Vector(*m["p"]), Vector(*m["d"])
        if f.kind == "insert":
            r0, r1, ln = m["hole"] / 2, 1.5 * m["od"] / 2, m["depth"]
        else:
            r0, r1, ln = S.SHANK[f.size] / 2 + 0.45, S.SHANK[f.size] / 2 + 0.45 + S.HOLE_WALL_K * d, m["length"]
        pl = Plane(origin=p0, z_dir=dv)
        probe = Location(pl) * (Cylinder(r0 + 0.6, ln, align=MINZ) - Cylinder(r0 + 0.05, ln, align=MINZ))
        inside = host & probe
        if inside is None or inside.volume < 0.05:
            continue
        # One ring for each stretch of the hole in material (a fork has two cheeks, a clamp a slit).
        for k, piece in enumerate(inside.solids()):
            bb = piece.bounding_box()
            ss = [(Vector(x, y, z) - p0).dot(dv) for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y)
                  for z in (bb.min.Z, bb.max.Z)]
            s0, s1 = max(0.0, min(ss)), min(ln, max(ss))
            if s1 - s0 < 0.5:
                continue
            ring = Location(Plane(origin=p0 + dv * s0, z_dir=dv)) * (Cylinder(r1, s1 - s0, align=MINZ) - Cylinder(r0, s1 - s0, align=MINZ))
            mat = host & ring
            # A nut or an insert in its trap counts as material.
            extra = 0.0
            for g in fitems:
                if g.kind in ("nut", "nyloc", "insert") and g.part == f.part:
                    q = g.solid & ring
                    if q is not None and q.volume > 0:
                        q = q - host                  # only the part of the nut or insert that is not plastic already
                        extra += q.volume if q is not None else 0.0
            fill = ((mat.volume if mat is not None else 0.0) + extra) / ring.volume
            ok = fill >= S.HOLE_FILL_MIN
            lines.append((ok, f"{f.part}: {f.name} ({f.item}), stretch {k + 1}: {fill * 100:.0f} % material in a "
                              f"{r1 - r0:.1f} mm ring over {s1 - s0:.1f} mm"))
            if not ok:
                problems.append(f"thin wall round a hole: {lines[-1][1]}")
    return lines


def check_sim_export(files, fitems):
    """Each fastener's host part and each placed printed part must be in the sim export. Stops the
    build if one is missing. Prints the list of exported files."""
    names = {f["file"][len("sim2/"):-len(".stl")] for f in files}
    missing = set()
    for f in fitems:
        host = SIM_HOST.get(f.part)
        if host is None or (host != "frame" and host not in names):
            missing.add(f"{f.part} (host of {f.name})")
    for p in PLACED:
        if SIM_HOST[p] not in names:
            missing.add(p)
    log("  sim2 export: " + ", ".join(f"{f['file'][5:]} ({f['moves']})" for f in files))
    if missing:
        log("  SIM EXPORT MISSING: " + "; ".join(sorted(missing)))
        log("RESULT: CLASHES")
        sys.exit(1)


def belt_lengths():
    """The length of each belt between the middles of its two folds, along the pitch line, with the
    idler at the middle of its travel. Crimp the belts to these lengths on the bench. Both belts are
    loops round a 20T pulley and a 20T idler (two half wraps on the pitch line), cut at the carriage."""
    wrap = math.pi * S.PULLEY_PD
    # X: the bottom run from the left exit point to the pulley, the top run, the bottom run from the
    # idler to the right exit point, and the slant from each exit point to its fold.
    xi = S.XI_X
    px = S.XM_X
    span = S.XP_X[1] - S.XP_X[0]
    lx = 2 * (xi - px) - span + wrap + 2 * P.x_folds_u()
    # Y: from the front fold to the idler, the lower run, from the pulley to the back fold.
    f, b_ = P.y_belt_folds(0.0)
    ly = 2 * (S.YM_Y - S.YI_Y) - (b_ - f) + wrap
    return {"y_left": ly, "y_right": ly, "x": lx}


def ydrive_mass():
    """The mass that the Y motors move now (g): the gantry without the Y motors (they stand at the
    back of the frame). Kept for the report: the mass taken off the gantry."""
    return -(2 * S.MOTOR_MASS + 2 * 10.0 + 4 * 8.0 + 2 * 8.0)


# The servo angle that puts the horn level (firmware/config: 90 degrees). The firmware angle is the
# horn angle above level plus this value. PEN_UP_DEG 40 is 130, PEN_DOWN_DEG -10 is 80.
SERVO_LEVEL = 90.0


def tab_lift(deg):
    """The slider lift (mm above pen down) that the round end of the horn gives at a horn angle.
    The slider falls by its weight. It rests on the horn tip, or on the paper (0) when the horn is lower.
    The tab underside is the 45 degree line from SLIDER_X1 to TAB_X1. Returns 0 when the tip is off the tab."""
    tx, tz = S.horn_tip(deg)
    r = S.HORN_TIP_R
    xs, xe = S.SLIDER_X1, S.TAB_X1
    zs = S.SLIDER_Z0 + S.TAB_Z0                       # the underside at the slider face, at pen down
    lo, hi = max(xs, tx - r), min(xe, tx + r)
    if lo > hi:
        return 0.0
    # The highest point of the circle over the line z = zs + (x - xs): the tangent point, or an end of the tab.
    x = min(max(tx - r / math.sqrt(2), lo), hi)
    top = tz + math.sqrt(max(0.0, r * r - (x - tx) ** 2))
    return max(0.0, top - (zs + (x - xs)))


def tip_in_tab_top(deg):
    """True if the round end of the horn goes into the flat top of the tab, with the pen on the paper.
    This happens only when the horn comes down from above the slip angle: the tip is then over the tab."""
    tx, tz = S.horn_tip(deg)
    r = S.HORN_TIP_R
    lo, hi = max(S.SLIDER_X1 - 0.5, tx - r), min(S.TAB_X1, tx + r)
    if lo > hi:
        return False
    x = min(max(tx, lo), hi)
    top = S.SLIDER_Z0 + S.TAB_Z0 + (S.TAB_X1 - S.SLIDER_X1) + S.TAB_TOP
    return tz - math.sqrt(max(0.0, r * r - (x - tx) ** 2)) < top


def pen_lift_json(xp0, c0):
    """The servo, horn and slider linkage for the simulator, in frame coordinates at machine home.
    The horn turns about the shaft (axis along y). horn.stl is at stl_deg. The pen group moves up by lift."""
    fx = lambda x: round(xp0 + x, 3)
    fz = lambda z: round(S.PLATE_DZ + z, 3)
    lifts = [tab_lift(s - SERVO_LEVEL) for s in range(181)]
    # The contact angle: the horn tip meets the tab (bisection between pen down and pen up).
    a, b = S.PEN_DOWN_DEG, S.PEN_UP_DEG
    for _ in range(40):
        m = (a + b) / 2
        a, b = (m, b) if tab_lift(m) <= 0.0 else (a, m)
    # The slip angle: above pen up, the tip goes past the end of the tab and the slider falls.
    lo, hi = S.PEN_UP_DEG, 90.0
    for _ in range(40):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if tab_lift(m) > 0.0 else (lo, m)
    # The stall angle: after the slip, the slider falls and the tip is over the tab. When the horn comes
    # down again, the tip lands on the top of the tab and pushes the pen into the paper.
    stall = None
    deg = lo
    while deg > -90.0:
        if tip_in_tab_top(deg - 0.05):
            stall = deg
            break
        deg -= 0.05
    z_b =S.TAB_Z0 + (S.TAB_X1 - S.SLIDER_X1)
    return {
        "note": "The horn turns about pivot (axis y). Horn angle above level = servo deg - servo_level_deg. "
                "horn.stl is at stl_deg. The tab underside is a 45 degree line z - x = const: z = underside_z at "
                "x = tab_x[0], at pen down. The pen tip is on the paper at lift 0 (pen down pose of the pen parts). "
                "lift_by_servo_deg: the slider lift in mm for servo 0..180 deg (tip under the tab). Above slip_servo "
                "the tip leaves the end of the tab and the slider falls. The tip is then over the tab: when the horn "
                "comes down again, it stops on the top of the tab at stall_servo (top_x, top_z) and pushes on the pen.",
        "pivot": [fx(S.SHAFT_X), round(c0 - S.PLATE_FRONT + S.HORN_Y, 3), fz(S.SHAFT_Z)],
        "axis": "y",
        "servo_level_deg": SERVO_LEVEL,
        "stl_deg": S.PEN_DOWN_DEG,
        "horn_len": S.HORN_L,
        "tip_r": S.HORN_TIP_R,
        "tab_x": [fx(S.SLIDER_X1), fx(S.TAB_X1)],
        "underside_z": fz(S.SLIDER_Z0 + S.TAB_Z0),
        "top_x": [fx(S.SLIDER_X1 - 0.5), fx(S.TAB_X1)],
        "top_z": fz(S.SLIDER_Z0 + z_b + S.TAB_TOP),
        "floor_lift": 0.0,
        "shelf_lift": -S.HOVER,
        "pen_down_servo": S.PEN_DOWN_DEG + SERVO_LEVEL,
        "pen_up_servo": S.PEN_UP_DEG + SERVO_LEVEL,
        "contact_servo": round(a + SERVO_LEVEL, 2),
        "slip_servo": round(lo + SERVO_LEVEL, 2),
        "stall_servo": None if stall is None else round(stall + SERVO_LEVEL, 2),
        "lift_mm": round(S.LIFT, 3),
        "gap_at_pen_down": S.TAB_GAP,
        "lift_by_servo_deg": [round(v, 3) for v in lifts],
    }


def frame_json(lim, sim_files, fcounts=None):
    bars = P.frame_bars()

    def bb(s):
        b = s.bounding_box()
        return [round(v, 2) for v in (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z)]
    xr = S.FRAME_X
    c0 = lim["c"][0]
    xp0 = lim["xp"][0]
    t = P.plate_offset(xp0, c0)
    return {
        "units": "mm",
        "origin": "front left outer corner of the frame, on the table. X right, Y to the back, Z up.",
        "bars": [{"name": n, "box": bb(s)} for n, s in bars.items() if "bar" in n],
        "rails": [{"name": n, "box": bb(s)} for n, s in bars.items() if "rail" in n],
        "feet": [[round(f.center().X, 1), round(f.center().Y, 1)] for f in P.feet()],
        "foot": {"d": S.FOOT_D, "h": S.FOOT_H},
        # The guide: V-wheels. The beam alone (no x_rail, no y_rails, no rods) is the V-wheel layout.
        "beam": {"box": bb(P.beam(c0)), "profile": [S.BEAM, S.BEAM]},
        "guide": "V-wheels: 3 per Y carriage (2 in the outer side slot of the rail, 1 in the inner side slot), 3 on the printed X plate on the beam",
        "x_motor": {"pos": [S.XM_X, round(c0 + S.XB_Y, 2), round(S.BZ, 2)], "shaft": "-y",
                    "body_y": [round(c0 + S.XM_FACE_DY, 2), round(c0 + S.XM_FACE_DY + S.XMOTOR_L, 2)],
                    "note": "pos: the pulley centre; the motor stands behind the left beam end, shaft to the front"},
        "x_idler": {"pos": [S.XI_X, round(c0 + S.XB_Y, 2), round(S.BZ, 2)], "travel_x": [-v for v in S.XIDLER_TRAVEL],
                    "fork": True, "axis": "y"},
        "belt_lengths": {k: round(v, 1) for k, v in belt_lengths().items()},
        # The X belt (the stock CR-10 path): a loop round the pulley and the idler (axles along y), flat
        # (width along y): the top run in the top slot channel, the bottom run in the bottom slot channel
        # of the beam. The carriage clamps the bottom run: at each end of the plate ("x_clamp", frame x at
        # home) the belt leaves the slot at 45 degrees down into a clip pocket under the beam.
        "x_clamp": [round(xp0 + S.XP_X[0], 2), round(xp0 + S.XP_X[1], 2)],
        "x_clips": [round(xp0 + S.XP_X[0] + (P.XCL_POCKET_U[0] + S.JAW_POCKET / 2) * 0.7071, 2),
                    round(xp0 + S.XP_X[1] - (P.XCL_POCKET_U[0] + S.JAW_POCKET / 2) * 0.7071, 2)],
        "belt_clip": {"size": [round(S.JAW_LEN, 1), S.JAW_W, S.JAW_T],
                      "note": "printed belt jaw on each folded belt end, with an M3 x 10 into an M3 insert; "
                              "size: along the belt, across the belt width, thickness"},
        "x_belt": {"y": round(c0 + S.XB_Y, 2), "z_runs": [round(v, 2) for v in S.XB_RUNS], "clamped": "lower", "axis": "y",
                   "slant_deg": S.XCL_SLANT,
                   "plane": "loop in the x-z plane, flat (width along y): the top run in the top slot channel and the bottom "
                            "run in the bottom slot channel of the beam (the stock CR-10 path); the axles point along y"},
        "x_carriage": {"plate_front_y": round(c0 - S.PLATE_FRONT, 2), "box": bb(t * P.x_carriage_plate()),
                       "note": "the printed X plate; the pen carriage bolts to its front face"},
        "y_wheels": [[[round(x, 2), round(y, 2), round(z, 2)] for x, y, z in P.y_wheel_pos(c0)],
                     [[round(xr - x, 2), round(y, 2), round(z, 2)] for x, y, z in P.y_wheel_pos(c0)]],
        "y_wheel_axis": "z",
        "y_wheel_slots": "side slots of the rails: two wheels outside each rail, one inside (the back outer wheel on the eccentric)",
        "x_wheels": [[round(xp0 + x, 2), round(c0, 2), round(S.PLATE_DZ + (S.PLATE_BEAM_Z + (1 if z > S.PLATE_BEAM_Z else -1) * (S.BEAM / 2 + S.WHEEL_OFF)), 2)]
                     for _, x, z in S.X_WHEELS],
        "x_wheel_ecc": S.X_ECC,
        "wheel": {"d": S.WHEEL_D, "t": S.WHEEL_T, "axis_y": "z", "axis_x": "y"},
        "home_pen": [round(v, 2) for v in lim["home_pen"]],
        "carriage_y0": round(c0, 2),
        "carriage_x0": round(xp0, 2),
        "travel": [round(v, 1) for v in lim["travel"]],
        "pen_lift_mm": round(S.LIFT, 2),
        "pen_lift": pen_lift_json(xp0, c0),
        # The Y drive: fixed motors. Each Y belt is a loop over its rail (flat, width along x): the lower run
        # 1 mm over the rail top, the upper run clamped by the carriage (two clamp blocks, offsets dy from
        # carriage_y0). The motor stands behind the back bar, the idler in front of the front bar (static).
        "y_belt": {
            "x": [S.YB_X, xr - S.YB_X], "z_runs": [round(S.YB_LOW, 2), round(S.YB_HIGH, 2)], "w": S.BELT_W, "t": S.BELT_T,
            "clamped": "upper", "clamp_dy": [S.YCL_FRONT[0], S.YCL_BACK[0]],
            "pulley": {"y": S.YM_Y, "z": round(S.YB_AX, 2), "r": round(S.PULLEY_OD / 2 - S.GT2_TOOTH_H, 2),
                       "teeth": S.PULLEY_TEETH, "pitch_d": round(S.PULLEY_PD, 3)},
            "idler": {"y": S.YI_Y, "z": round(S.YB_AX, 2), "r": round(S.PULLEY_OD / 2 - S.GT2_TOOTH_H, 2), "travel_y": list(S.YIDLER_TRAVEL)},
            "motor": {"x": [round(S.YM_FACE_X - S.MOTOR_L, 2), round(S.YM_FACE_X, 2)], "y": S.YM_Y, "z": round(S.YB_AX, 2),
                      "size": S.MOTOR, "shaft": "+x on the left, -x on the right (mirror)", "moves": "static"},
            "note": "a loop round the motor pulley (back) and the idler (front); the carriage clamps the upper run",
        },
        "belt": {"z": round(S.YB_Z, 2), "w": S.BELT_W},
        # The moving cables. Each entry draws a carrier from its fixed end to its moving end at any
        # carriage position: the two runs lie in "plane"; the bend has radius "bend_r" at the centre
        # line; "runs" is the length of the two runs together (constant). The bend sits at
        # (fixed + moving -/+ runs) / 2 along the run axis (see "bend_side").
        "chains": [
            {"name": "y", "kind": "drag chain, openable" if S.YCH_OPEN else "drag chain",
             "inner_hw": list(S.YCH_INNER), "outer_hw": list(S.YCH_OUTER), "bend_r": S.YCH_R,
             "plane": {"type": "y-z", "x": S.YCH_X}, "axis": "y", "bend_side": "-y (front)",
             "fixed": {"y": S.YCH_FIX_Y, "z": S.YCH_ZL, "moves": "static", "note": "the end of the lower run, on the table"},
             "moving": {"dy": round(sum(S.YCH_TAB_Y) / 2, 2), "z": S.YCH_ZU, "moves": "gantry",
                        "note": "offset from carriage_y0; the end of the upper run, on the left carriage tab"},
             "runs": S.YCH_RUNS, "end_link": S.YCH_END,
             "bend_formula": "y_bend = (fixed_y + moving_y - runs) / 2"},
            {"name": "x", "kind": "split wire loom, free slack loop (catenary)", "axis": "x", "d": S.LOOM_D, "length": round(P.loom_len(), 1),
             "plane": {"type": "x-z", "dy": round(S.LOOM_Y, 2)}, "z": round(S.LOOM_Z, 2),
             "fixed": {"x": round(S.LOOM_FIX_X, 2), "moves": "gantry",
                       "note": "the tie round the head harness cable; dy from carriage_y0 (plane.dy)"},
             "moving": {"dx": S.LOOM_DX, "moves": "carriage",
                        "tie": {"dy": round(-S.PLATE_FRONT - S.LOOM_D / 2 - 0.3, 2),
                                "z": round(S.PLATE_DZ + (S.LOOM_TIE[2] + S.LOOM_TIE[3]) / 2, 2)},
                        "note": "dx from the X plate origin (carriage_x0 at home); the loom goes from the tie slot up the "
                                "front of the X plate (tie.dy, tie.z), back over the plate top at z to the loop plane"},
             "formula": "between the two ends (same z) the loop is a catenary of the given length: "
                        "2 a sinh(chord / 2a) = length, z = z_end - sag + a (cosh((x - x_mid) / a) - 1)"},
        ],
        # The click point of each lever (the Creality endstop boards).
        "endstops": [{"name": "y1", "pos": [round(v, 2) for v in P.es_click("y_left")], "dir": "-y"},
                     {"name": "y2", "pos": [round(v, 2) for v in P.es_click("y_right")], "dir": "-y"},
                     {"name": "x", "pos": [round(v, 2) for v in P.es_click("x", c0)], "dir": "-x"}],
        "camera": {"pos": [S.MAST_X, round(S.POLE_Y, 1), round(S.CAM_Z, 1)],
                   "mast": {"box": bb(P.pole())},
                   "note": "USB webcam on the top end of a 590 mm pole (17.85 mm, measured), in a printed foot behind "
                           "the back bar. The lens height above the pole top (15 mm) is an ESTIMATE."},
        "parts": sim_files,
        "fasteners": {"note": "context geometry of the main build, one STL for each group that moves (sim2/fasteners_*.stl); "
                              "no heat-set inserts", "counts": fcounts},
        "paper_z": round(S.PAPER_Z, 2),
        "status": "Frame sizes are measured. The wheel sizes, the belt lines and the carriages are design values, not yet built.",
    }


def main():
    problems = []
    base, reach = check(problems)
    lim = check_frame(problems)
    feet_gap = check_feet(problems, lim)
    es_ot = check_endstops(problems, lim)
    xbelt = check_x_belt(problems, lim)
    log(f"  X belt in the beam slots (gaps, mm): {xbelt}")
    log(f"  endstop boards: overtravel past the click at the hard stop (mm): {es_ot}; plug zones clear over the travel")
    log(f"  feet: smallest gap to a moving part over the full travel / to a static part (mm): {feet_gap}")
    fz = check_fasteners(problems, lim)
    cab = check_cables(problems, lim)
    grip = check_mast(problems)
    var = check_boards(problems, lim)
    for p in problems:
        log("  CLASH: " + p)
    if not problems:
        log("  fit check: the slider runs on the rail "
            "from the shelf to the top. The horn lifts the tab only at pen up. 8 and 15 mm pens fit.")
    log(f"  pen lift: {S.LIFT:.1f} mm at {S.PEN_UP_DEG:.0f} deg; horn {S.TAB_GAP:.1f} mm under the tab at "
        f"{S.PEN_DOWN_DEG:.0f} deg; the slider rests {S.HOVER:.0f} mm above the shelf at pen down")
    pl = pen_lift_json(0.0, 0.0)
    log(f"  pen lift linkage (servo deg): the horn tip meets the tab at {pl['contact_servo']}, pen up "
        f"{pl['pen_up_servo']:.0f} lifts {pl['lift_by_servo_deg'][int(pl['pen_up_servo'])]:.2f} mm, the tip slips off "
        f"the tab end above {pl['slip_servo']}; after a slip the horn stops on the tab top at {pl['stall_servo']}")
    log(f"  clamp screw M3 x {S.CLAMP_SCREW_L:.0f}: stands out {reach[S.PEN_MIN]:.1f} mm with an 8 mm pen, "
        f"{reach[S.PEN_MAX]:.1f} mm with a 15 mm pen")
    log(f"  wheels: each touches its slot (contact {min(lim['contact'].values()):.2f} to {max(lim['contact'].values()):.2f} mm3 "
        f"at a {S.WHEEL_PRELOAD} mm preload); the X plate eccentric moves {lim['ecc_x']:.2f} of {S.ECC_RANGE} mm")
    log(f"  table plotter: pen travel {lim['travel'][0]:.1f} x {lim['travel'][1]:.1f} mm; home pen at frame "
        f"({lim['home_pen'][0]:.1f}, {lim['home_pen'][1]:.1f}); the pen stands {lim['pen_reach']:.1f} mm out of the slider; "
        f"the head is {lim['head_low']:.1f} mm above the table")
    log(f"  gantry y {lim['c'][0]:.1f} to {lim['c'][1]:.1f}; plate x {lim['xp'][0]:.1f} to {lim['xp'][1]:.1f}")
    cn = lim["c_nofeet"]
    log(f"  with no feet: gantry y {cn[0]:.1f} to {cn[1]:.1f}, Y travel {cn[1] - cn[0]:.1f} mm; "
        f"stops: " + "; ".join(f"{k}: {v}" for k, v in lim["stops_nofeet"].items()))
    log(f"  Y carriage: lowest point {lim['car_low']:.1f} mm above the table")
    log("  travel stops: " + "; ".join(f"{k}: {v}" for k, v in lim["stops"].items()))
    log(f"  endstops at home: the X trigger lug is {lim['switch_gap'][0]:.1f} mm past the click of the X lever; the Y "
        f"striker is {lim['switch_gap'][1]:.1f} mm past the click of the Y lever")
    log(f"  camera pole: a {S.POLE_D} mm pole in a {grip:.0f} mm socket; the lens at z {S.CAM_Z:.0f} (ESTIMATE)")
    log(f"  breakout boards: at the back of the Y travel the head board reaches frame y "
        f"{var['head_back_y']:.0f}, its lowest point is at z {var['head_low_z']:.0f}; the base board cable reaches "
        f"z {var['base_top_z']:.0f}")
    for k, r in cab["loom"].items():
        log(f"  servo loom at {k} (X plate x {r['xp']}): lowest point z {r['low_z']} (x {r['low_x']}), paper z {S.PAPER_Z}; "
            f"nearest rigid parts {r['gaps']}; soft contact {r['soft'] or 'none'}" + (f"; {'; '.join(r['rests'])}" if r.get("rests") else ""))
    bl = belt_lengths()
    log(f"  belt lengths between the folds (idler at the middle of its slot): Y {bl['y_left']:.1f} mm each, X {bl['x']:.1f} mm")
    log(f"  Y drive: fixed motors behind the back bar, idlers in front of the front bar; belt wrap {lim['wrap']:.0f} deg; "
        f"the gantry is {-ydrive_mass():.0f} g lighter (2 Y motors at {S.MOTOR_MASS:.0f} g measured, pulleys, idlers, screws); the X motor is a 42-34 ({S.XMOTOR_MASS:.0f} g measured)")
    log(f"  moving cables: Y drag chain {S.YCH_INNER[0]:.0f} x {S.YCH_INNER[1]:.0f} R{S.YCH_R:.0f}, about {cab['y_chain_len']:.0f} mm; "
        f"servo loom {S.LOOM_D} mm, about {cab['x_loom_len']:.0f} mm (loop {cab['x_loop_len']:.0f} mm); clear over the travel")
    log(f"  fasteners: {len(fz['items'])} items, checked at {fz['configs']} gantry and X plate positions; screw lengths:")
    for j in fz["joints"]:
        log(f"    {'ok ' if j.result['ok'] else 'BAD'} {j.count:2d} x {j.item:28s} {j.name}: {j.result['text']}")
    log("  fastener counts: " + "; ".join(f"{v} x {k}" for k, v in sorted(fz["by_item"].items())))
    if "--no-export" in sys.argv:
        log("RESULT: " + ("CLASHES" if problems else "OK"))
        return

    mesh_dir = os.path.join(BUILD, "mesh")
    for d in ("cad", "stl", mesh_dir):
        os.makedirs(os.path.join(HERE, d), exist_ok=True)
    for d in (mesh_dir, os.path.join(HERE, "cad"), os.path.join(HERE, "stl")):
        for f in os.listdir(d):
            if os.path.isfile(os.path.join(d, f)):
                os.remove(os.path.join(d, f))
    manifest, children, summary = [], [], {"parts": {}}

    def mesh(name, shape, mat, group, tol=0.01):
        export_stl(shape, os.path.join(mesh_dir, name + ".stl"), tolerance=tol, angular_tolerance=0.08)
        manifest.append({"name": name, "file": name + ".stl", "material": mat, "group": group})

    slider = P.slider()
    printed = {
        "pen_carriage": (P.pen_carriage(), back_down),
        "pen_slider": (slider, None),
        "mast_foot": (P.mast_foot(), None),
        "y_carriage_left": (P.y_carriage(0.0, "motor"), None),
        "y_carriage_right": (P.mirror_x(P.y_carriage(0.0, "idler")), None),
        "y_front_left": (P.y_front_base(), None),
        "y_front_right": (P.y_front_base("right"), None),
        "y_motor_mount_left": (P.y_motor_mount(), lambda sh: Rot(0, -90, 0) * sh),
        "y_motor_mount_right": (P.mirror_x(P.y_motor_mount()), lambda sh: Rot(0, 90, 0) * sh),
        "y_idler_fork": (P.y_idler_fork_print(), None),
        "y_idler_bracket_left": (P.y_idler_bracket(), front_down),
        "y_idler_bracket_right": (P.y_idler_bracket("right"), front_down),
        "x_carriage_plate": (P.x_carriage_plate(), None),
        "y_chain_anchor": (P.y_chain_anchor(), lambda sh: Rot(-90, 0, 0) * sh),
        "x_idler_fork": (P.x_idler_fork_print(), None),
        "fit_rail": (P.fit_rail(), back_down),
        "fit_slider": (P.fit_slider(), None),
        "fit_wheel": (P.fit_wheel(), None),
        "belt_jaw": (P.belt_jaw(), None),
    }
    for name, (shape, pose_fn) in printed.items():
        export_step(shape, os.path.join(HERE, "cad", name + ".step"))
        pose = print_pose(pose_fn(shape) if pose_fn else shape)
        export_stl(pose, os.path.join(HERE, "stl", name + ".stl"), tolerance=0.004, angular_tolerance=0.05)
        if name in ("y_carriage_right", "y_motor_mount_right", "y_idler_bracket_right"):
            # The mesh of a mirrored, filleted solid can have open edges: mirror the mesh of the
            # left-hand (idler) part instead. The print pose is centred on X, so -x keeps it centred.
            tmp = os.path.join(BUILD, "_idler_tmp.stl")
            left = {"y_carriage_right": lambda: P.y_carriage(0.0, "idler"), "y_motor_mount_right": lambda: Rot(0, -90, 0) * P.y_motor_mount(),
                    "y_idler_bracket_right": lambda: front_down(P.y_idler_bracket())}[name]()
            export_stl(print_pose(left), tmp, tolerance=0.004, angular_tolerance=0.05)
            _mirror_stl_x(tmp, os.path.join(HERE, "stl", name + ".stl"))
            os.remove(tmp)
        bb = pose.bounding_box()
        summary["parts"][name] = {"size": [round(bb.size.X, 1), round(bb.size.Y, 1), round(bb.size.Z, 1)],
                                  "volume_cm3": round(shape.volume / 1000, 1)}
        log(f"  {name:21s} print size {bb.size.X:5.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f} mm, "
            f"volume {shape.volume / 1000:5.1f} cm3, valid {pose.is_valid}, {len(pose.solids())} solid")
        mesh("print_" + name, pose, "petg", "print_" + name)

    # The pen carriage on the stock X carriage plate, in the plate frame.
    servo = P.servo_body()
    pc = P.pen_carriage()
    assembly = [("pen_lift", pc, "petg"), ("pen_slider", slider, "petg"), ("servo", servo, "servo"),
                ("horn_down", P.horn(S.PEN_DOWN_DEG), "horn"),
                ("pen", P.pen(12.0, S.SLIDER_Z0 - 32.0), "pen"),
                ("screw", P.clamp_screw(12.0)[0], "steel")]
    for name, shape, mat in assembly:
        mesh(name, shape, mat, name)
        shape.label, shape.color = name, Color(*hex_rgb(COLOURS[mat]))
        children.append(shape)
    # Pen up: the slider, the pen, the screw and the horn at the up angle.
    up = Pos(0, 0, S.LIFT)
    mesh("up_slider", up * slider, "petg", "up")
    mesh("up_pen", up * P.pen(12.0, S.SLIDER_Z0 - 32.0), "pen", "up")
    mesh("up_screw", up * P.clamp_screw(12.0)[0], "steel", "up")
    mesh("horn_up", P.horn(S.PEN_UP_DEG), "horn", "up")
    # The printed X plate with its wheels.
    for n, s in P.x_carriage():
        mat = "petg" if n == "X plate" else "plate"
        mesh("plate_" + n.replace(" ", "_"), s, mat, "plate")
        s.label, s.color = n, Color(*hex_rgb(COLOURS[mat]))
        children.append(s)
    export_step(Compound(children=children, label="pen-lift"), os.path.join(HERE, "cad", "pen-lift-assembly.step"))

    # The table plotter for the simulator: frame coordinates, machine home, pen down.
    sim2 = os.path.join(HERE, "stl", "sim2")
    os.makedirs(sim2, exist_ok=True)
    # The bought parts with detail (motors, boards, endstops, servo, horn, pen) come from
    # context_detail.py when it exists: do not remove or overwrite those files.
    detail = os.path.exists(os.path.join(HERE, "context_detail.py"))
    keep = DETAIL_FILES if detail else ()
    for f in os.listdir(sim2):
        if f[:-len(".stl")] not in keep:
            os.remove(os.path.join(sim2, f))
    c0, xp0 = lim["c"][0], lim["xp"][0]
    t = P.plate_offset(xp0, c0)
    tip = -lim["dz"]
    items = [
        ("y_carriage_left", P.y_carriage(c0, "motor"), S.ACCENT, "gantry"),
        ("y_carriage_right", P.mirror_x(P.y_carriage(c0, "idler")), S.ACCENT, "gantry"),
        ("beam", P.beam(c0), "#1E1F22", "gantry"),
        ("x_motor", P.x_motor_parts(c0)[0], "#202020", "gantry"),
        ("x_pulley", P.x_motor_parts(c0)[1], "#9A9A9A", "gantry"),
        ("x_idler", P.x_idler(c0), "#9A9A9A", "gantry"),
        ("x_idler_fork", P.x_idler_fork(c0), S.ACCENT, "gantry"),
        ("mast_foot", P.mast_foot(), S.ACCENT, "static"),
        ("y_front_left", P.y_front_base(), S.ACCENT, "static"),
        ("y_front_right", P.y_front_base("right"), S.ACCENT, "static"),
        ("y_motor_mount_left", P.y_motor_mount(), S.ACCENT, "static"),
        ("y_motor_mount_right", P.y_motor_mount("right"), S.ACCENT, "static"),
        ("y_idler_fork_left", P.y_idler_fork(), S.ACCENT, "static"),
        ("y_idler_fork_right", P.y_idler_fork(0.0, "right"), S.ACCENT, "static"),
        ("y_idler_bracket_left", P.y_idler_bracket(), S.ACCENT, "static"),
        ("y_idler_bracket_right", P.y_idler_bracket("right"), S.ACCENT, "static"),
        ("y_endstops", Compound(children=[P.es_parts(w)[k] for w in ("y_left", "y_right") for k in ("body", "lever")]),
         "#202020", "static"),
        ("y_chain_anchor", P.y_chain_anchor(), S.ACCENT, "static"),
        ("y_stepper_left", P.y_stepper()[0], "#202020", "static"),
        ("y_stepper_right", P.mirror_x(P.y_stepper()[0]), "#202020", "static"),
        ("y_pulleys_left", Compound(children=[P.y_stepper()[1], P.y_idler()]), "#9A9A9A", "static"),
        ("y_pulleys_right", P.mirror_x(Compound(children=[P.y_stepper()[1], P.y_idler()])), "#9A9A9A", "static"),
        ("x_carriage_plate", t * P.x_carriage_plate(), S.ACCENT, "carriage"),
        ("pen_carriage", t * pc, S.ACCENT, "carriage"),
        ("servo", t * servo, "#2F5DA8", "carriage"),
        ("horn", t * P.horn(S.PEN_DOWN_DEG), "#F2F2F2", "horn"),   # the sim turns it (pen_lift)
        ("pen_slider", t * slider, S.ACCENT, "pen"),
        ("pen", t * P.pen(S.PEN_SIZE_SIM, tip), "#202020", "pen"),
    ]
    # The fasteners: one file for each group that moves (the same fasteners as the fit check).
    fitems, _ = F.build(c0, xp0)
    for grp in ("static", "gantry", "carriage", "pen"):
        sel = [f.solid for f in fitems if f.group == grp and f.kind not in ("clip", "belt", "insert")]
        if sel:
            items.append((f"fasteners_{grp}", Compound(children=sel), "#B8BCC2", grp))
    # The brass heat-set inserts (in the Y carriages).
    for grp in ("static", "gantry", "carriage"):
        ins = [f.solid for f in fitems if f.kind == "insert" and f.group == grp]
        if ins:
            items.append((f"inserts_{grp}", Compound(children=ins), "#C9A23F", grp))
    # The belt ends: the printed belt jaws and the folded belt ends.
    for grp in ("gantry", "carriage"):
        items.append((f"belt_clips_{grp}", Compound(children=[f.solid for f in fitems if f.group == grp and f.kind == "clip"]),
                      S.ACCENT, grp))
        items.append((f"belt_ends_{grp}", Compound(children=[f.solid for f in fitems if f.group == grp and f.kind == "belt"]),
                      "#2B2B2B", grp))
    # The two breakout boards with their plugs and standoffs. The head board rides on the gantry, the
    # base board is static.
    for kind, c, moves in (("head", c0, "gantry"), ("base", None, "static")):
        board = [sh for n, sh in board_world(kind, c)]
        items.append((f"{kind}_board", Compound(children=board), "#2E7D32", moves))
    files = []
    for name, shape, colour, moves in items:
        if name in keep and os.path.exists(os.path.join(sim2, name + ".stl")):
            files.append({"file": "sim2/" + name + ".stl", "color": colour, "moves": moves})
            continue
        # The small hardware gets a coarser mesh: it keeps the sim fast.
        small = name.startswith(("fasteners_", "inserts_", "belt_clips_", "y_pulleys_"))
        export_stl(shape, os.path.join(sim2, name + ".stl"), tolerance=0.06 if small else 0.03,
                   angular_tolerance=0.35 if small else 0.12)
        files.append({"file": "sim2/" + name + ".stl", "color": colour, "moves": moves})
    check_sim_export(files, fitems)
    # The material round each hole in the printed parts (the parts at the fastener positions).
    by_name = {n: sh for n, sh, _, _ in items}
    hosts = {part: by_name[sim] for part, sim in SIM_HOST.items() if sim in by_name}
    hole_lines = check_holes(problems, fitems, hosts)
    bad = [txt for ok, txt in hole_lines if not ok]
    log(f"  hole check: {len(hole_lines)} holes in printed parts, {len(bad)} with thin walls")
    for txt in bad:
        log("    THIN: " + txt)
    # The whole table plotter: meshes for the images, and one STEP assembly.
    asm = []
    for n, s in P.frame_bars().items():
        asm.append(("frame_" + n.replace(" ", "_"), s, "extrusion", "frame"))
    for i, f in enumerate(P.feet()):
        asm.append((f"foot_{i}", f, "pen", "frame"))
    for i, h in enumerate(P.bar_screw_heads()):
        asm.append((f"bar_screw_{i}", h, "steel", "frame"))
    CD = _cd()
    for n, sh in ydrive_items(c0) + ydrive_items_right(c0):
        if "motor" in n and CD:
            kit = (CD.y_stepper_right if n.startswith("right") else CD.y_stepper_left)(c0)[0]
            asm += cd_meshes(n.replace(" ", "_"), kit, "motors")
        else:
            asm.append((n.replace(" ", "_"), sh, "pen" if "motor" in n else "steel", "motors"))
    asm.append(("y_belt_l", P.y_belt(c0), "pen", "belts"))
    asm.append(("y_chain", P.y_chain(c0), "pen", "cables"))
    asm.append(("x_loom", P.x_loom(c0, xp0), "pen", "cables"))
    asm.append(("y_chain_anchor", P.y_chain_anchor(), "petg", "cables"))
    asm.append(("y_belt_r", P.mirror_x(P.y_belt(c0)), "pen", "belts"))
    asm.append(("x_belt", P.x_belt_loop(c0, xp0), "pen", "belts"))
    for side in ("left", "right"):
        for n, s in y_wheel_items(c0, side):
            asm.append((n.replace(" ", "_"), s, "plate" if n.split()[-1].isdigit() and len(n.split()) == 4 else "steel", "wheels"))
    if CD:
        asm += cd_meshes("x_switch", CD.x_endstop(c0, xp0)[0], "ycar")
        asm += cd_meshes("y_switch_l", CD.y_endstop_left(c0)[0], "brackets")
        asm += cd_meshes("y_switch_r", CD.y_endstop_right(c0)[0], "brackets")
    else:
        asm.append(("x_switch", P.x_switch(c0), "pen", "ycar"))
    for n, sh in y_static_items():
        if CD and "switch" in n:
            continue
        if n.endswith(("Y motor", "Y pulley", "Y idler")):
            continue                                  # the Y drive loop above has them
        asm.append((n.replace(" ", "_"), sh, "pen" if "switch" in n else "petg", "brackets"))
    for n, s in P.x_carriage():
        asm.append(("xcar_" + n.replace(" ", "_"), t * s, "petg" if n == "X plate" else "plate", "head"))
    for name, shape, colour, moves in items:
        if name == "x_carriage_plate":
            continue
        mat = {S.ACCENT: "petg", "#A7A49C": "plate", "#2F5DA8": "servo", "#F2F2F2": "horn", "#B8BCC2": "steel"}.get(colour, "pen")
        if name.startswith(("y_carriage", "x_idler_fork")):
            grp = "ycar"
        elif name.startswith(("y_front", "y_motor_mount", "y_idler_fork", "y_idler_bracket", "y_endstops", "y_drive", "y_stepper", "y_pulleys",
                              "y_chain_anchor")):
            continue
        elif name == "beam":
            grp = "beam"
        elif name == "x_motor" and CD:
            asm += cd_meshes("x_motor", CD.x_motor(c0)[0], "motors")
            continue
        elif name == "servo" and CD:
            asm += cd_meshes("servo", CD.servo(t)[0], "head")
            continue
        elif name in ("x_motor", "x_pulley", "x_idler"):
            grp = "motors"
        elif name == "mast_foot":
            continue
        elif name.startswith(("fasteners_", "inserts_", "belt_", "head_board", "base_board")):
            continue
        else:
            grp = "head"
        asm.append((name, shape, mat, grp))
    # The fasteners for the images: the wheel stacks, the stock X wheel bolts and the bar screw
    # heads are in other groups already.
    for grp in ("static", "gantry", "carriage", "pen"):
        sel = [f.solid for f in fitems if f.group == grp and "Y wheel" not in f.name and not f.stock
               and f.kind not in ("clip", "belt")]
        asm.append((f"fast_{grp}", Compound(children=sel), "steel", "fast"))
    for grp in ("gantry", "carriage"):
        asm.append((f"clips_{grp}", Compound(children=[f.solid for f in fitems if f.group == grp and f.kind == "clip"]),
                    "steel", "clips"))
        asm.append((f"beltends_{grp}", Compound(children=[f.solid for f in fitems if f.group == grp and f.kind == "belt"]),
                    "pen", "clips"))
    asm = [a for a in asm if not _empty(a[1])]  # an empty group
    for name, shape, mat, grp in asm:
        mesh("t_" + name, shape, mat, "t_" + grp, 0.03)
    # The left Y carriage on a short length of its rail, for the close-up images.
    cv = S.FRAME_Y / 2
    mesh("yl_rail", P.rail_slotted() & P.box(-1, S.RAIL_W + 1, cv - 60, cv + 60, 0, 100), "plate", "yl_rail", 0.02)
    mesh("yl_car", P.y_carriage(cv, "motor"), "petg", "yl_car", 0.02)
    for i, w in enumerate(P.y_wheels(cv)):
        mesh(f"yl_wheel_{i}", w, "plate", "yl_wtop" if i < 2 else "yl_wbot", 0.02)
    for i, (n, sh) in enumerate(P.y_wheel_stack(cv)):
        mesh(f"yl_stack_{i}", sh, "steel", "yl_wtop" if i < 8 else "yl_wbot", 0.02)
    # The left Y drive at the back left corner (the close-up of the Y motor step): the corner of the
    # frame, the bracket, the motor, the pulley and the belt there.
    back = P.box(-30, 75, S.FRAME_Y - 60, S.FRAME_Y + 60, 0, 120)
    for n, sh in P.frame_bars().items():
        part = sh & back
        if part is not None and part.volume > 0:
            mesh("yd_" + n.replace(" ", "_"), part, "plate", "yd_frame", 0.02)
    mesh("yd_mount", P.y_motor_mount(), "petg", "yd_mount", 0.02)
    if CD:
        for mn, msh, mm, _ in cd_meshes("yd_motor", CD.y_stepper_left(cv)[0], "yd_motor"):
            mesh(mn, msh, mm, "yd_motor", 0.02)
    else:
        mesh("yd_motor", P.y_stepper()[0], "pen", "yd_motor", 0.02)
    mesh("yd_pulley", P.y_stepper()[1], "plate", "yd_omega", 0.02)
    mesh("yd_belt", P.y_belt(cv) & P.box(-1, 60, S.FRAME_Y - 60, S.FRAME_Y + 60, 0, 200), "pen", "yd_belt", 0.02)
    fy, _ = F.build(cv, lim["xp"][0])
    for f in fy:
        if f.name.startswith(("left Y motor screw", "left Y motor bracket screw")):
            mesh("yd_" + f.name.replace(" ", "_"), f.solid, "steel", "yd_screws", 0.02)
    # The X idler fork past the right beam end (the close-up of the X idler step): the end of the right
    # tower, the beam end, the fork, the idler, the axle, the tension screw and its nut, the belt there.
    xf_box = P.box(S.FRAME_X - 30, S.FRAME_X + 60, cv - 30, cv + 30, 60, 130)
    mesh("xf_car", P.mirror_x(P.y_carriage(cv, "idler")) & xf_box, "petg", "xf_car", 0.02)
    mesh("xf_beam", P.beam_real(cv, S.FRAME_X - 30, S.BEAM_X0 + S.BEAM_L), "plate", "xf_beam", 0.02)
    mesh("xf_fork", P.x_idler_fork(cv), "petg", "xf_fork", 0.02)
    mesh("xf_idler", P.x_idler(cv), "plate", "xf_idler", 0.02)
    mesh("xf_belt", P.x_belt_loop(cv, lim["xp"][0]) & xf_box, "pen", "xf_belt", 0.02)
    for f in fy:
        if f.name.startswith(("right X idler axle", "right X idler washer", "right X idler nut", "X idler axle", "X idler washer",
                              "X idler nut")):
            mesh("xf_" + f.name.replace(" ", "_"), f.solid, "steel", "xf_axle", 0.02)
        elif "X tension" in f.name:
            mesh("xf_" + f.name.replace(" ", "_"), f.solid, "steel", "xf_tension", 0.02)
    # The X motor behind the left beam end (the close-up of the X motor step): the left tower, the beam
    # end, the motor, the pulley, the belt in the top and bottom slots.
    xm_box = P.box(-60, 45, cv - 45, cv + 60, 55, 160)
    mesh("xm_car", P.y_carriage(cv, "motor") & xm_box, "petg", "xm_car", 0.02)
    mesh("xm_beam", P.beam_real(cv, S.BEAM_X0, 45), "plate", "xm_beam", 0.02)
    if CD:
        for mn, msh, mm, _ in cd_meshes("xm_motor", CD.x_motor(cv)[0], "xm_motor"):
            mesh(mn, msh, mm, "xm_motor", 0.02)
    else:
        mesh("xm_motor", P.x_motor_parts(cv)[0], "pen", "xm_motor", 0.02)
    mesh("xm_pulley", P.x_motor_parts(cv)[1], "plate", "xm_pulley", 0.02)
    mesh("xm_belt", P.x_belt_loop(cv, lim["xp"][0]) & xm_box, "pen", "xm_belt", 0.02)
    for f in fy:
        if f.name.startswith(("left X motor screw", "beam screw", "left beam screw")):
            mesh("xm_" + f.name.replace(" ", "_"), f.solid, "steel", "xm_screws", 0.02)
    # The front end of the left Y belt: the corner of the frame, the base, the idler fork, the idler,
    # the switch, the belt there.
    corner = P.box(-1, 60, -40, 75, 0, 100)
    for n, sh in P.frame_bars().items():
        part = sh & corner
        if part is not None and part.volume > 0:
            mesh("ya_" + n.replace(" ", "_"), part, "plate", "ya_frame", 0.02)
    mesh("ya_base", P.y_front_base(), "petg", "ya_base", 0.02)
    mesh("ya_fork", P.y_idler_fork(), "petg", "ya_sled", 0.02)
    mesh("ya_bracket", P.y_idler_bracket(), "petg", "ya_bracket", 0.02)
    mesh("ya_idler", P.y_idler(), "plate", "ya_idler", 0.02)
    if CD:
        for mn, msh, mm, _ in cd_meshes("ya_switch", CD.y_endstop_left(S.YC_HOME)[0], "ya_switch"):
            mesh(mn, msh, mm, "ya_switch", 0.02)
    else:
        mesh("ya_switch", P.y_switch(), "pen", "ya_switch", 0.02)
    mesh("ya_run", P.y_belt(S.YC_HOME) & corner, "pen", "ya_belt", 0.02)
    for f in fy:
        if f.name.startswith(("left Y idler", "left Y tension", "Y idler", "Y tension")):
            mesh("ya_" + f.name.replace(" ", "_"), f.solid, "steel", "ya_clip", 0.02)
    # The X belt ends in the clamp blocks of the X plate (plate frame), with the plate.
    mesh("xp_plate", P.x_carriage_plate(), "petg", "xp_plate", 0.02)
    for i, w in enumerate(P.x_wheels()):
        mesh(f"xp_wheel_{i}", w, "plate", "xp_wheels", 0.02)
    for i, (k, sh) in enumerate(P.x_belt_ends()):
        mesh(f"x{k}_{i}", sh, "steel" if k == "clip" else "pen", "xclip" if k == "clip" else "xbelt", 0.02)
    for name, shape, mat in (("pole", P.pole(), "plate"), ("mast_foot", P.mast_foot(), "petg"), ("camera", P.camera(), "pen")):
        mesh("t_" + name, shape, mat, "t_mast", 0.03)
    # The stock controller build: the breakout boards on the frame, and the stock control box on
    # the table left of the frame. ESTIMATE: the box is about 290 x 210 x 85 mm, the LCD on the front.
    tchildren = []
    for name, shape, mat, grp in asm:
        shape.label, shape.color = name, Color(*hex_rgb(COLOURS[mat]))
        tchildren.append(shape)
    for kind, c in (("head", lim["c"][0]), ("base", None)):
        for n, s in board_world(kind, c):
            if "tails" in n:
                continue
            mat = "horn" if "standoff" in n else "pen"
            mesh("t_v_" + n.replace(" ", "_").replace("-", "m"), s, mat, "t_boards", 0.03)
            s.label, s.color = n, Color(*hex_rgb(COLOURS[mat if mat != "pen" else "pcb"]))
            tchildren.append(s)
    bx0, by0 = CTRL_X1 - S.CTRL_BOX[0], 70.0
    box = P.box(bx0, bx0 + S.CTRL_BOX[0], by0, by0 + S.CTRL_BOX[1], 0.0, S.CTRL_BOX[2])
    lcd = P.box(bx0 + 40, bx0 + 140, by0 - 1.5, by0, 18.0, 70.0)
    knob = Pos(bx0 + 175, by0, 44.0) * Rot(90, 0, 0) * P.Cylinder(9.0, 14.0, align=(P.Align.CENTER, P.Align.CENTER, P.Align.MIN))
    ctrl = [("ctrl_box", box, "plate"), ("ctrl_lcd", lcd, "pen"), ("ctrl_knob", knob, "pen")]
    if CD:
        ctrl = [(n, sh, m) for n, sh, m, _ in cd_meshes("ctrl", CD.ctrl_box()[0], "t_box")]
    for name, shape, mat in ctrl:
        mesh("t_" + name, shape, mat, "t_box", 0.05)
        shape.label, shape.color = name, Color(*hex_rgb(COLOURS[mat]))
        tchildren.append(shape)
    export_step(Compound(children=tchildren, label="table-plotter"), os.path.join(HERE, "cad", "table-plotter-assembly.step"))
    summary["boards"] = {k: round(v, 1) for k, v in var.items()}
    with open(os.path.join(HERE, "stl", "frame.json"), "w") as fh:
        json.dump(frame_json(lim, files, dict(sorted(fz["by_item"].items()))), fh, indent=1)
    summary["frame"] = {"travel": [round(v, 1) for v in lim["travel"]], "home_pen": [round(v, 1) for v in lim["home_pen"]],
                        "pen_reach": round(lim["pen_reach"], 1), "c": [round(v, 1) for v in lim["c"]],
                        "xp": [round(v, 1) for v in lim["xp"]], "stops": lim["stops"],
                        "switch_gap": [round(v, 1) for v in lim["switch_gap"]],
                        "c_nofeet": [round(v, 1) for v in lim["c_nofeet"]], "stops_nofeet": lim["stops_nofeet"]}
    summary["belt_lengths"] = {k: round(v, 1) for k, v in belt_lengths().items()}
    summary["cables"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in cab.items()}
    summary["ydrive"] = {"mass_g": round(ydrive_mass()), "wrap_deg": lim["wrap"], "fork_travel": list(S.YIDLER_TRAVEL)}
    summary["fasteners"] = {"by_item": dict(sorted(fz["by_item"].items())), "by_part": fz["by_part"],
                            "joints": [{"name": j.name, "item": j.item, "count": j.count, "ok": j.result["ok"],
                                        "text": j.result["text"]} for j in fz["joints"]]}

    summary["fit"] = {"lift": round(S.LIFT, 2), "pen_up_deg": S.PEN_UP_DEG, "pen_down_deg": S.PEN_DOWN_DEG,
                      "hover": S.HOVER, "tab_gap": S.TAB_GAP, "pen_min": S.PEN_MIN, "pen_max": S.PEN_MAX,
                      "screw_l": S.CLAMP_SCREW_L, "dt_clr": S.DT_CLR, "pen_tip_below_slider": 32.0}
    with open(os.path.join(BUILD, "parts.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    with open(os.path.join(BUILD, "manifest.json"), "w") as fh:
        json.dump({"parts": manifest}, fh, indent=1)
    log("RESULT: " + ("CLASHES" if problems else "OK"))


if __name__ == "__main__":
    main()
