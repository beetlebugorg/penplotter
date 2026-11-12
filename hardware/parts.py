"""Pen plotter parts for a CR-10 V3, in build123d. shape.py has all the dimensions and the
world frame. Each part is modelled in world coordinates. model.py turns it to its print pose."""

import math

from build123d import (Align, Axis, Box, Circle, Cone, Cylinder, Location, Plane, Polygon, Pos, Rectangle, revolve,
                       Rot, Sketch, Vector, extrude, offset)

import shape as S

MIN = (Align.MIN, Align.MIN, Align.MIN)
PX, MY, PZ = (1, 0, 0), (0, -1, 0), (0, 0, 1)


def poly(*pts):
    """A polygon with its points in counter-clockwise order, so the face normal is +Z (local)."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area > 0 else pts[::-1]), align=None)


def box(x0, x1, y0, y1, z0, z1):
    """A box from the corner ranges, in any order."""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=MIN)


def xz_face(sk):
    """A sketch in (x, z) on the plane Y = 0. Extrude toward -Y."""
    return Plane.XZ * sk


def drill_cut(d, depth, cone=True):
    """A hole along +Z from Z = 0, with a 45 degree cone at the end (no flat ceiling)."""
    r = d / 2
    c = Cylinder(r, depth, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if cone:
        c += Pos(0, 0, depth) * Cone(r, 0.3, r - 0.3, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return c


def to_minus_y(solid):
    """Turn a solid that points along +Z so that it points along -Y."""
    return Rot(90, 0, 0) * solid


# ---------------------------------------------------------------- the base

def footprint():
    """The outline of the back layer, in (x, z): the rectangles less the wheel bolt keep-outs."""
    sk = None
    for x0, x1, z0, z1 in S.BASE_RECTS:
        r = Pos((x0 + x1) / 2, (z0 + z1) / 2) * Rectangle(x1 - x0, z1 - z0)
        sk = r if sk is None else sk + r
    for _, x, z, rad in S.WHEEL_BOLTS:
        # The wheel bosses of the X plate come forward through the pen carriage: a teardrop keep-out
        # (the bosses have pointed undersides, the plate prints upright).
        r = rad + S.KEEP_CLR
        k = r / math.sqrt(2)
        sk -= Pos(x, z) * (Circle(r) + poly((-k, -k), (0, -r * math.sqrt(2)), (k, -k), (0, 0)))
        # The 2 mm rib under the boss (45 degrees, down to the back face): a slot 3 mm wide, 12 mm tall.
        sk -= Pos(x, z - rad * math.sqrt(2) - 5.5) * Rectangle(3.0, 12.0)
    # Round the outer corners, but keep the size.
    return offset(offset(sk, -S.BASE_R), S.BASE_R)


def rail_profile(grow=0.0, y_back=None):
    """The dovetail section in (x, y). grow makes it larger on each side (for the slot)."""
    t = 1 / math.tan(math.radians(S.RAIL_ANGLE))
    gh = grow / math.sin(math.radians(S.RAIL_ANGLE))
    y_root = -S.BASE_T
    y_out = y_root - S.RAIL_D - grow
    y_b = y_root if y_back is None else y_back
    half_b = S.RAIL_W0 / 2 + gh - (y_b - y_root) * t
    half_o = S.RAIL_W0 / 2 + gh + (y_root - y_out) * t
    return poly((S.RAIL_X - half_b, y_b), (S.RAIL_X + half_b, y_b),
                   (S.RAIL_X + half_o, y_out), (S.RAIL_X - half_o, y_out))


def rail(z0=S.SHELF_TOP, z1=S.RAIL_TOP):
    return extrude(Plane.XY.offset(z0) * rail_profile(y_back=-S.BASE_T + 0.5), z1 - z0, dir=PZ)


def head_screw_cuts():
    """Pilot holes for the four M3 head screws. They come from the rear, through the carriage
    plate, and cut their own thread in the pen carriage."""
    cuts = None
    for _, x, z in S.HEAD_HOLES:
        c = Pos(x, 0.5, z) * to_minus_y(drill_cut(S.SELF_TAP, S.HEAD_SCREW_DEPTH + 0.5))
        cuts = c if cuts is None else cuts + c
    return cuts


def servo_pocket():
    c = S.SERVO_CLR
    pocket = box(S.SHAFT_X - S.SERVO_W / 2 - c, S.SHAFT_X + S.SERVO_W / 2 + c,
                 -S.BASE_T, S.SERVO_FACE - 1, S.BODY_Z0 - c, S.BODY_Z1 + c)
    wire = box(S.SHAFT_X - S.WIRE_SLOT / 2, S.SHAFT_X + S.WIRE_SLOT / 2,
               -S.BASE_T - 2, S.SERVO_FACE - 1, S.BODY_Z1, S.TOWER_Z[1] + 1)
    holes = None
    for dz in (-S.SERVO_TAB_HOLES / 2, S.SERVO_TAB_HOLES / 2):
        h = Pos(S.SHAFT_X, S.SERVO_FACE, S.BODY_ZC + dz) * Rot(-90, 0, 0) * drill_cut(S.M2_PILOT, 8.0)
        holes = h if holes is None else holes + h
    return pocket + wire + holes


def base():
    """The pen lift: the back layer, the rail, the shelf and the servo tower, in the plate frame."""
    back = extrude(xz_face(footprint()), S.BASE_T, dir=MY)
    shelf_rect = S.BASE_RECTS[3]
    shelf = box(shelf_rect[0] + S.BASE_R, shelf_rect[1] - S.BASE_R, -S.BASE_T + 0.5, S.SHELF_FRONT,
                shelf_rect[2] + 0.5, S.SHELF_TOP)
    tower = box(S.TOWER_X[0], S.TOWER_X[1], -S.BASE_T + 0.5, S.SERVO_FACE, S.TOWER_Z[0], S.TOWER_Z[1])
    part = back + rail() + shelf + tower
    part -= servo_pocket()
    # The wheel boss keep-outs go through the whole part: no front feature hangs over a keep-out of the
    # back layer.
    for _, x, z, rad in S.WHEEL_BOLTS:
        r = rad + S.KEEP_CLR
        k = r / math.sqrt(2)
        sk = Pos(x, z) * (Circle(r) + poly((-k, -k), (0, -r * math.sqrt(2)), (k, -k), (0, 0)))
        part -= Pos(0, 1, 0) * extrude(xz_face(sk), 80.0, dir=MY)
    return part


# ---------------------------------------------------------------- the slider

def bore_2d():
    """The pen bore in (x, y): a round part and a 90 degree V to +X."""
    r = S.PEN_R
    cx, cy = S.PEN_CX, S.PEN_CY
    k = r / math.sqrt(2)
    v = poly((cx, cy), (cx + k, cy + k), (S.V_X, cy), (cx + k, cy - k))
    return Pos(cx, cy) * Circle(r) + v


def teardrop_x(d, x0, x1, y, z, up=True):
    """A hole along X with a pointed top, for a hole in a vertical wall. up=False points it
    down, for a part that prints upside down."""
    r = d / 2
    k = r / math.sqrt(2)
    s = 1 if up else -1
    sk = Circle(r) + poly((-k, s * k), (0, s * r * math.sqrt(2)), (k, s * k), (0, 0))
    return extrude(Plane.YZ.offset(x0) * (Pos(y, z) * sk), x1 - x0, dir=PX)


def slider(z0=S.SLIDER_Z0):
    """The pen slider, with its bottom at z0 (world)."""
    h = S.SLIDER_H
    body = box(S.SLIDER_X0, S.SLIDER_X1, S.SLIDER_BACK, S.SLIDER_FRONT, 0, h)
    # The tab: a 45 degree underside, a flat top.
    x0, x1 = S.SLIDER_X1 - 0.5, S.TAB_X1
    z_a = S.TAB_Z0 - 0.5
    z_b = S.TAB_Z0 + (x1 - S.SLIDER_X1)
    top = z_b + S.TAB_TOP
    tab_sk = poly((x0, z_a), (x1, z_b), (x1, top), (x0, top))
    # The tab stops at the front face of the slider: a corner past the face has no material under it in the print.
    ty1 = max(S.TAB_Y[1], S.SLIDER_FRONT)
    tab = extrude(Plane.XZ.offset(-S.TAB_Y[0]) * tab_sk, S.TAB_Y[0] - ty1, dir=MY)
    part = body + tab
    slot = extrude(Plane.XY.offset(-1) * rail_profile(grow=S.DT_CLR, y_back=S.SLIDER_BACK + 1), h + 2, dir=PZ)
    bore = extrude(Plane.XY.offset(-1) * bore_2d(), h + 2, dir=PZ)
    screw = teardrop_x(S.M3_CLEAR, S.SLIDER_X0 - 1, S.PEN_CX - S.PEN_R + 1, S.PEN_CY, S.CLAMP_Z)
    nut_x = S.SLIDER_X0 + S.WALL_NUT / 2
    nut_t = S.M3_NUT_T + 0.3
    nut_w = S.M3_NUT_AF + 0.4
    nut_corner = S.M3_NUT_AF / math.cos(math.radians(30)) / 2 + 0.3
    nut = box(nut_x - nut_t / 2, nut_x + nut_t / 2, S.PEN_CY - nut_w / 2, S.PEN_CY + nut_w / 2,
              S.CLAMP_Z - nut_corner, h + 1)
    part = part - slot - bore - screw - nut
    return Pos(0, 0, z0) * part


# ---------------------------------------------------------------- fit tests

def fit_rail():
    """A 20 mm length of the rail on a backing block."""
    z0, z1 = 20.0, 40.0
    back = box(S.RAIL_X - 9, S.RAIL_X + 9, 0, -S.BASE_T, z0, z1)
    return back + rail(z0, z1)


def fit_slider():
    """The top 13 mm of the slider: the slot, the bore, the clamp screw, and the nut slot."""
    z_cut = S.CLAMP_Z - 5.0
    s = slider(0)
    return s & box(-100, 100, -100, 100, z_cut, S.SLIDER_H + 1)


# ---------------------------------------------------------------- context

def servo_body():
    """The servo: body, tabs, case top, spline. Nominal size (no clearance)."""
    x0, x1 = S.SHAFT_X - S.SERVO_W / 2, S.SHAFT_X + S.SERVO_W / 2
    body = box(x0, x1, -S.BASE_T, S.SERVO_FACE, S.BODY_Z0, S.BODY_Z1)
    tabs = box(x0, x1, S.SERVO_FACE, S.SERVO_FACE - S.SERVO_TAB_T,
               S.BODY_ZC - S.SERVO_TAB_L / 2, S.BODY_ZC + S.SERVO_TAB_L / 2)
    top = box(x0, x1, S.SERVO_FACE - S.SERVO_TAB_T, S.SERVO_FACE - S.SERVO_TAB_T - S.SERVO_TOP, S.BODY_Z0, S.BODY_Z1)
    y_case = S.SERVO_FACE - S.SERVO_TAB_T - S.SERVO_TOP
    spline = Pos(S.SHAFT_X, y_case, S.SHAFT_Z) * to_minus_y(
        Cylinder(2.4, S.SERVO_SPLINE_H, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return body + tabs + top + spline


def horn(deg):
    """The horn hub and one arm, at an angle above level. The arm points to -X."""
    t = S.HORN_T
    hub_h = S.HORN_HUB[1]
    y_hub0 = S.SPLINE_TOP + 1.0
    hub = Pos(S.SHAFT_X, y_hub0, S.SHAFT_Z) * to_minus_y(
        Cylinder(S.HORN_HUB[0] / 2, hub_h, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    tx, tz = S.horn_tip(deg)
    a = math.radians(deg)
    nx, nz = -math.sin(a), -math.cos(a)        # normal to the arm, in (x, z)
    w0, w1 = 3.0, S.HORN_TIP_R
    sk = (poly((S.SHAFT_X + nx * w0, S.SHAFT_Z + nz * w0), (tx + nx * w1, tz + nz * w1),
                  (tx - nx * w1, tz - nz * w1), (S.SHAFT_X - nx * w0, S.SHAFT_Z - nz * w0))
          + Pos(tx, tz) * Circle(w1) + Pos(S.SHAFT_X, S.SHAFT_Z) * Circle(w0))
    arm = extrude(Plane.XZ.offset(-(S.HORN_Y + t / 2)) * sk, t, dir=MY)
    return hub + arm


def pen(d, z_tip, length=140.0):
    """A pen of diameter d, in the V of the bore, with its tip at z_tip."""
    r = d / 2
    cx = S.V_X - r * math.sqrt(2)
    cone = 8.0
    p = Pos(cx, S.PEN_CY, z_tip) * Cone(0.4, r, cone, align=(Align.CENTER, Align.CENTER, Align.MIN))
    p += Pos(cx, S.PEN_CY, z_tip + cone) * Cylinder(r, length - cone, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return p


def clamp_screw(d):
    """The M3 clamp screw, pushed in until it touches a pen of diameter d, with the slider at pen down."""
    r = d / 2
    cx = S.V_X - r * math.sqrt(2)
    x_tip = cx - r - 0.05
    x_head = x_tip - S.CLAMP_SCREW_L
    z = S.SLIDER_Z0 + S.CLAMP_Z               # CLAMP_Z is above the bottom of the slider
    s = Pos(x_head, S.PEN_CY, z) * Rot(0, 90, 0) * Cylinder(S.SHANK["M3"] / 2, S.CLAMP_SCREW_L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s += Pos(x_head, S.PEN_CY, z) * Rot(0, -90, 0) * Cylinder(2.75, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return s, x_head


# ================================================================ the table plotter
# Frame coordinates (shape.py): origin at the front left outer corner of the frame, on the table.

MINZ = (Align.CENTER, Align.CENTER, Align.MIN)


_RIGHT = {}


def _right_carriage():
    """The right carriage at gantry y = 0: the mirror of the finished idler carriage, healed."""
    if "r" not in _RIGHT:
        m = _mirror_plain(_fin(("y_carriage", "idler"), lambda: raw_y_carriage(0.0, "idler"), UP["y_carriage"]))
        if not m.is_valid:
            m = m.fix()
        _RIGHT["r"] = m
    return _RIGHT["r"]


def _mirror_plain(shape):
    return shape.mirror(Plane.YZ.offset(S.FRAME_X / 2))


def mirror_x(shape):
    """The mirror image about the centre plane of the frame (x = FRAME_X / 2)."""
    if hasattr(shape, "_mirror_alt"):
        return shape._mirror_alt()
    out = _mirror_plain(shape)
    if hasattr(out, "is_valid") and not out.is_valid:
        out = out.fix()                    # a mirrored fillet can lose its tolerances: heal it
    return out


def teardrop_y(d, x, z, y0, y1, up=True):
    """A hole along Y with a pointed top (for a vertical wall that prints upright). up=False
    points it down, for a part that prints upside down."""
    r = d / 2
    k = r / math.sqrt(2)
    s = 1 if up else -1
    sk = Circle(r) + poly((-k, s * k), (0, s * r * math.sqrt(2)), (k, s * k), (0, 0))
    y0, y1 = sorted((y0, y1))
    return extrude(Plane.XZ.offset(-y0) * (Pos(x, z) * sk), y1 - y0, dir=(0, 1, 0))


def gable_slot_x(x0, x1, yc, half, z0, z1):
    """A slot along X with a 45 degree pointed roof (no flat ceiling in print)."""
    pts = ((yc - half, z0), (yc + half, z0), (yc + half, z1), (yc, z1 + half), (yc - half, z1))
    return extrude(Plane.YZ.offset(x0) * poly(*pts), x1 - x0, dir=PX)


# ---------------------------------------------------------------- V-wheels and slots

def wheel():
    """A stock V-wheel on an axle along Z, centred on the origin (the real shape: v_wheel_real)."""
    return v_wheel_real()


def wheel_simple():
    """The old V-wheel: flat faces, two 45 degree flanks, a flat tip."""
    r_tip = S.WHEEL_D / 2
    h = S.WHEEL_T / 2
    r_face = r_tip + S.WHEEL_TIP - h          # the flanks start here
    rb = S.WHEEL_BORE / 2
    pts = [(rb, -h), (r_face, -h), (r_tip, -S.WHEEL_TIP), (r_tip, S.WHEEL_TIP), (r_face, h), (rb, h)]
    return revolve(Plane.XZ * poly(*pts), Axis.Z)


def x_axis(solid):
    """Turn a solid that points along +Z so that it points along +X."""
    return Rot(0, 90, 0) * solid






def _zcyl(r, z0, z1, x, y):
    """A cylinder along Z from z0 to z1."""
    z0, z1 = sorted((z0, z1))
    return Pos(x, y, z0) * Cylinder(r, z1 - z0, align=MINZ)


def _xcyl(r, x0, x1, y, z):
    """A cylinder along X from x0 to x1."""
    return Pos(x0, y, z) * x_axis(Cylinder(r, x1 - x0, align=MINZ))




def hex_nut(af, t, bore):
    """A hex nut on an axis along Z, from Z = 0 to t."""
    from build123d import RegularPolygon
    h = extrude(RegularPolygon(af / math.sqrt(3), 6), t, dir=PZ)
    return h - Pos(0, 0, -1) * Cylinder(bore, t + 2, align=MINZ)


def v_groove_y(x_face, inward, zc, y0, y1):
    """The V of a slot in a side face at x = x_face, along Y. inward = +1 if the extrusion is at
    x > x_face."""
    w = S.SLOT_V / 2
    pts = ((x_face - inward, zc - w - 1.0), (x_face - inward, zc + w + 1.0), (x_face + inward * w, zc))
    return extrude(Plane.XZ.offset(-y0) * poly(*pts), y1 - y0, dir=(0, 1, 0))


def v_groove_x(z_face, inward, yc, x0, x1):
    """The V of a slot in a top or bottom face at z = z_face, along X. inward = +1 if the extrusion
    is at z > z_face."""
    w = S.SLOT_V / 2
    pts = ((yc - w - 1.0, z_face - inward), (yc + w + 1.0, z_face - inward), (yc, z_face + inward * w))
    return extrude(Plane.YZ.offset(x0) * poly(*pts), x1 - x0, dir=PX)


def v_groove_tb(z_face, inward, xc, y0, y1):
    """The V of a slot in a top or bottom face at z = z_face, along Y. inward = +1 if the extrusion
    is at z > z_face (the bottom face)."""
    w = S.SLOT_V / 2
    pts = ((xc - w - 1.0, z_face - inward), (xc + w + 1.0, z_face - inward), (xc, z_face + inward * w))
    return extrude(Plane.XZ.offset(-y0) * poly(*pts), y1 - y0, dir=(0, 1, 0))


def rail_slotted():
    """The left frame rail with the V of its six slots (for the wheel contact check)."""
    r = frame_bars()["left rail"]
    y0, y1 = S.BAR_D, S.FRAME_Y - S.BAR_D
    zc = S.RAIL_TOP_Z - S.RAIL_H / 2
    r = r - v_groove_y(0.0, 1, zc, y0, y1) - v_groove_y(S.RAIL_W, -1, zc, y0, y1)
    for xc in (S.SLOT_OUT_X, S.SLOT_IN_X):
        r = r - v_groove_tb(S.RAIL_TOP_Z, -1, xc, y0, y1) - v_groove_tb(S.RAIL_TOP_Z - S.RAIL_H, 1, xc, y0, y1)
    return r


def beam(c=0.0):
    return box(S.BEAM_X0, S.BEAM_X0 + S.BEAM_L, c - S.BEAM / 2, c + S.BEAM / 2, S.BEAM_Z0, S.BEAM_Z0 + S.BEAM)


def beam_slotted(c=0.0):
    """The beam with the V of its top and bottom slots (for the wheel contact check)."""
    x0, x1 = S.BEAM_X0, S.BEAM_X0 + S.BEAM_L
    return beam(c) - v_groove_x(S.BEAM_Z0 + S.BEAM, -1, c, x0, x1) - v_groove_x(S.BEAM_Z0, 1, c, x0, x1)


# ---------------------------------------------------------------- the stock X carriage (plate frame)

_PLATE = {}












def plate_offset(xp, c):
    """The transform from the plate frame to frame coordinates: the X carriage plate at x = xp
    (plate origin), on the beam of a gantry at y = c."""
    return Pos(xp, c - S.PLATE_FRONT, S.PLATE_DZ)


# ---------------------------------------------------------------- the pen carriage



# ---------------------------------------------------------------- the Y carriages



def y_striker(c, end):
    """The striker of the Y endstop: a fin on the front edge of the plate, in line with the lever near its
    tip, over the corner of the board (v 0.5 to 3.5: no switch body there). Its front face is 1.5 mm past
    the click at the front stop. Its underside is 1.5 mm over the board at the face and slopes down at
    45 degrees to the plate (no support). Left: the board of y_left; right (built at the left position,
    then mirrored): the board of y_right."""
    v0, v1 = S.YSTRIKER
    if end == "motor":
        x0, x1 = S.ES_Y_ORIGIN[0] - v1, S.ES_Y_ORIGIN[0] - v0
    else:
        x0, x1 = S.FRAME_X - (S.ES_Y_RIGHT_ORIGIN - v0), S.FRAME_X - (S.ES_Y_RIGHT_ORIGIN - v1)
    zp = S.YF_TOP + S.ES_STANDOFF + S.ES["pcb"][2]       # the board top
    zc = zp - S.ES["pcb"][2] + S.ES["click"][2]
    ot = sum(S.ES_OVERTRAVEL) / 2
    yc = es_click("y_left")[1]
    yf = yc - ot + (c - S.YC_HOME)                       # the face, at this gantry y
    zb = zp + 1.5
    ztop = zc + 3.0
    z1 = S.YP_Z1 - 0.5
    yb = yf + max(S.YSTRIKER_D, zb - z1 + 1.0)
    prof = poly((yf, zb), (yf, ztop), (yb, ztop), (yb, z1), (yf + (zb - z1), z1))
    return extrude(Plane.YZ.offset(x0) * prof, x1 - x0, dir=PX)


# ---------------------------------------------------------------- belt ends: crimp clips in pockets















def x_switch(c=0.0):
    """The X endstop board on the front of the X endstop wall (context): the board, its switch, the plug
    and the pins (not the lever)."""
    return es_parts("x", c)["body"]


# ---------------------------------------------------------------- the Y drive (left side; the right is the mirror)

def _ycyl(r, y0, y1, x, z):
    """A cylinder along Y."""
    y0, y1 = sorted((y0, y1))
    return Pos(x, y0, z) * Rot(-90, 0, 0) * Cylinder(r, y1 - y0, align=MINZ)


def teardrop_y_mx(d, x, z, y0, y1):
    """A hole along Y with a point toward -X (the top when the part prints on its +X face)."""
    r = d / 2
    k = r / math.sqrt(2)
    sk = Circle(r) + poly((-k, k), (-r * math.sqrt(2), 0), (-k, -k), (0, 0))
    y0, y1 = sorted((y0, y1))
    return extrude(Plane.XZ.offset(-y0) * (Pos(x, z) * sk), y1 - y0, dir=(0, 1, 0))




























def y_switch():
    """The left Y endstop board on the front base (context): the board, its switch, the plug and the
    pins (not the lever)."""
    return es_parts("y_left")["body"]




# ---------------------------------------------------------------- moving cables

def hole_up(d, p0, axis, length, up):
    """A round hole of diameter d from p0 along the unit vector axis, with a 45 degree point toward the
    unit vector up (the top in print). For the parts that print on a side face."""
    from build123d import Location
    r = d / 2
    k = r / math.sqrt(2)
    sk = Circle(r) + poly((-k, k), (0, r * math.sqrt(2)), (k, k), (0, 0))
    ax, up_ = Vector(*axis), Vector(*up)
    xd = up_.cross(ax)
    return Location(Plane(origin=p0, x_dir=xd, z_dir=ax)) * extrude(sk, length, dir=PZ)


def y_chain_points(c):
    """The left Y chain at gantry y = c: the moving end, the bend and the fixed end (y)."""
    ym = c + sum(S.YCH_TAB_Y) / 2
    yf = S.YCH_FIX_Y
    yb = (yf + ym - S.YCH_RUNS) / 2
    return ym, yb, yf


def y_chain(c):
    """The Y drag chain at gantry y = c (context): the lower run on the table from the fixed end to the
    bend at the front, the bend (radius YCH_R at the centre line), the upper run back to the end link
    on the carriage tab. Outer size YCH_OUTER."""
    h, w = S.YCH_OUTER
    x0, x1 = S.YCH_X - w / 2, S.YCH_X + w / 2
    ym, yb, yf = y_chain_points(c)
    zl, zu = S.YCH_ZL, S.YCH_ZU
    e = S.YCH_END / 2
    parts = [box(x0, x1, yb, yf + S.YCH_END, zl - h / 2, zl + h / 2),
             box(x0, x1, yb, ym + e, zu - h / 2, zu + h / 2)]
    zc = (zl + zu) / 2
    ring = _xcyl(S.YCH_R + h / 2, x0, x1, yb, zc) - _xcyl(S.YCH_R - h / 2, x0 - 1, x1 + 1, yb, zc)
    parts.append(ring & box(x0 - 1, x1 + 1, yb - S.YCH_R - h, yb, zc - S.YCH_R - h, zc + S.YCH_R + h))
    out = parts[0]
    for q in parts[1:]:
        out = out + q
    return out


def y_chain_anchor():
    """The fixed end of the Y chain at the back left corner: a wall beside the end link (two M3 into
    the link), and an arm under the rail with two M5 screws into T-nuts in the bottom outer slot. A prism
    along Y: it prints on its front face."""
    x1 = S.YCH_X + S.YCH_OUTER[1] / 2 + 0.5           # the inner face of the chain
    y0, y1 = S.YCH_ANCHOR_Y
    zr = S.RAIL_TOP_Z - S.RAIL_H                      # the rail bottom (z 37)
    pts = [(x1, 0.0), (x1 + 8.0, 0.0), (x1 + 8.0, zr - 6.5), (-4.0, zr - 6.5), (-4.0, zr - 6.0), (15.0, zr - 6.0),
           (15.0, zr), (-4.0, zr), (-4.0, zr - 0.5), (x1, zr - 0.5)]
    part = extrude(Plane.XZ.offset(-y0) * poly(*pts), y1 - y0, dir=(0, 1, 0))
    # It prints with the back face on the bed (Rot(-90, 0, 0)): the top in print is -Y.
    for y in S.YCH_ARM_SCREWS:
        # A wider arm round the hole: 5 mm of material all round. A 45 degree edge keeps it 0.5 mm
        # from the back left foot, and it needs no support (the print up is -Y).
        xr = S.SLOT_OUT_X + S.M5_CLEAR / 2 + 5.1
        y45 = y - 2.9
        pad = poly((15.0 - 0.5, y45 - (xr - 15.0) - 0.5), (xr, y45), (xr, y1), (15.0 - 0.5, y1))
        part += extrude(Plane.XY.offset(zr - 6.5) * pad, 6.5, dir=PZ)
        part -= hole_up(S.M5_CLEAR, (S.SLOT_OUT_X, y, zr - 8), (0, 0, 1), 10.0, (0, -1, 0))
    # The two M3 pilots for the end link, across the wall (along X).
    ys_ = (S.YCH_FIX_Y + 2.5, S.YCH_FIX_Y + S.YCH_END - 2.5)   # 7 mm apart: 3 mm of material between the holes
    for y in ys_:
        # A 9 mm boss with a pointed side toward the bed (+Y in the print): no overhang.
        rb_ = 5.0
        zb_ = max(S.YCH_ZL, rb_)
        k = rb_ / math.sqrt(2)
        prof = Pos(y, zb_) * Circle(rb_) + poly((y + k, zb_ - k), (y + rb_ * math.sqrt(2), zb_), (y + k, zb_ + k), (y, zb_))
        part += extrude(Plane.YZ.offset(x1) * prof, 10.0, dir=PX) & box(x1, x1 + 10, y0, y1, 0, 40)
    for y in ys_:
        part -= hole_up(S.SELF_TAP, (x1 - 1, y, S.YCH_ZL), (1, 0, 0), 10.0, (0, -1, 0))
    return part


def loom_len():
    """The length of the slack loop of the servo loom: the longest chord over the X travel and a margin."""
    x0, x1 = S.XP_TRAVEL
    return max(abs(x + S.LOOM_DX - S.LOOM_FIX_X) for x in (x0, x1)) + S.LOOM_MARGIN


def catenary(s, ln):
    """A hanging cable of length ln between two points at the same height, s apart: the parameter a
    (mm) and the sag. A chord near 0 gives a U of two straight strands (a = 0, sag ln / 2)."""
    if s < 0.5:
        return 0.0, ln / 2
    if ln <= s:
        return float("inf"), 0.0
    lo, hi = 1e-3, 1e7
    for _ in range(200):
        a = math.sqrt(lo * hi)
        u = min(s / (2 * a), 700.0)
        if 2 * a * math.sinh(u) > ln:
            lo = a
        else:
            hi = a
    a = math.sqrt(lo * hi)
    return a, a * (math.cosh(s / (2 * a)) - 1)


def x_loom_points(c, xp, n=24):
    """The centre line of the servo loom at gantry y = c and X plate x = xp: the moving end from the tie
    slot up the front of the X plate, over the plate top and the beam to the loop plane, the slack loop (a
    catenary), and the fixed end at the head harness cable. [(x, y, z)]."""
    ln = loom_len()
    xm, xf = xp + S.LOOM_DX, S.LOOM_FIX_X
    yl, zt = c + S.LOOM_Y, S.LOOM_Z
    yfront = c - S.PLATE_FRONT - S.LOOM_D / 2 - 0.3
    zt0 = S.PLATE_DZ + (S.LOOM_TIE[2] + S.LOOM_TIE[3]) / 2
    pts = [(xm, yfront, zt0), (xm, yfront, zt), (xm, yl, zt)]
    s = abs(xf - xm)
    a, sag = catenary(s, ln)
    sg = 1 if xf >= xm else -1
    if a == 0.0:
        xs = xm + sg * s / 2
        pts += [(xs, yl, zt - sag), (xf, yl, zt)]
        return pts
    xc = (xm + xf) / 2
    for i in range(1, n + 1):
        x = xm + (xf - xm) * i / n
        z = zt - sag + (a * (math.cosh((x - xc) / a) - 1) if math.isfinite(a) else sag)
        pts.append((x, yl, z))
    return pts


def x_loom(c, xp):
    """The servo loom as round segments (context), gantry y = c, X plate x = xp."""
    from build123d import Compound, Location, Solid
    r = S.LOOM_D / 2
    pts = x_loom_points(c, xp)
    segs = []
    for p0, p1 in zip(pts, pts[1:]):
        v = Vector(*p1) - Vector(*p0)
        if v.length < 0.05:
            continue
        cyl = Solid.make_cylinder(r, v.length, Plane(origin=p0, z_dir=v))
        segs.append(cyl)
        segs.append(Solid.make_sphere(r).moved(Location(Vector(*p1))))
    return Compound(children=segs)


def x_loom_lowest(c, xp):
    """The lowest point of the loom underside (z) and its x."""
    pts = x_loom_points(c, xp, 96)
    p = min(pts, key=lambda q: q[2])
    return p[2] - S.LOOM_D / 2, p[0]


def fit_wheel():
    """A 12 mm strip of the carriage plate across the rail: the eccentric hole of an outer wheel and
    the counterbored hole of the inner wheel. Put an outer wheel and the inner wheel on it: they
    must grip the side slots before the eccentric reaches its end. It prints flat."""
    h = 6.0
    part = box(S.YW_OUT_X - 8.0, S.YW_IN_X + 8.0, -h, h, S.YP_Z0, S.YP_Z1)
    part -= _zcyl(S.ECC_HOLE / 2, S.YP_Z0 - 1, S.YP_Z1 + 1, S.YW_OUT_X, 0.0)
    part -= _zcyl(S.M5_CLEAR / 2, S.YP_Z0 - 1, S.YP_Z1 + 1, S.YW_IN_X, 0.0)
    part -= _zcyl(S.INNER_CB[0] / 2, S.YP_Z1 - S.INNER_CB[1], S.YP_Z1 + 1, S.YW_IN_X, 0.0)
    return part


def bar_screw_heads():
    """The heads of the eight screws that hold the bars to the sides (context)."""
    out = []
    d, h = S.BAR_SCREW_HEAD
    for x in S.BAR_SCREW_X + tuple(S.FRAME_X - x for x in S.BAR_SCREW_X):
        out.append(Pos(x, -h, S.BAR_SLOT_Z[0]) * Rot(-90, 0, 0) * Cylinder(d / 2, h, align=MINZ))
        out.append(Pos(x, S.FRAME_Y, S.BAR_SLOT_Z[0]) * Rot(-90, 0, 0) * Cylinder(d / 2, h, align=MINZ))
    return out


# ---------------------------------------------------------------- frame context

def frame_bars():
    fy, fx = S.FRAME_Y, S.FRAME_X
    z0 = S.BAR_Z0
    return {
        "front bar": box(0, fx, 0, S.BAR_D, z0, z0 + S.BAR_H),
        "back bar": box(0, fx, fy - S.BAR_D, fy, z0, z0 + S.BAR_H),
        "left rail": box(0, S.RAIL_W, S.BAR_D, fy - S.BAR_D, S.RAIL_TOP_Z - S.RAIL_H, S.RAIL_TOP_Z),
        "right rail": box(fx - S.RAIL_W, fx, S.BAR_D, fy - S.BAR_D, S.RAIL_TOP_Z - S.RAIL_H, S.RAIL_TOP_Z),
    }


def feet():
    """The four rubber feet under the long rails (context, ESTIMATE: position and size):
    front left, back left, front right, back right."""
    out = []
    for x in (S.FOOT_X, S.FRAME_X - S.FOOT_X):
        for y in S.FOOT_Y:
            f = Cylinder(S.FOOT_D / 2, S.FOOT_H, align=MINZ)
            f = f.chamfer(2.0, None, [f.edges().sort_by(Axis.Z)[0]])  # the soft lower edge of a rubber foot
            out.append(Pos(x, y, 0) * f)
    return out


# ================================================================ camera pole

def pole():
    """The camera pole, standing in the foot (context)."""
    return Pos(S.MAST_X, S.POLE_Y, S.POLE_Z0) * Cylinder(S.POLE_D / 2, S.POLE_L, align=MINZ)


def mast_foot():
    """The foot of the camera pole. A plate on the back face of the back bar (two M5 screws in
    T-nuts in the bar slot), and a socket for the pole behind it. It hangs on the bar, 3 mm over the
    table: an M6 bolt goes up through it into the pole end, its head in a counterbore. A split
    collar at the back of the socket and one M3 screw take up the play; the M3 nut drops into a
    slot from the top. Two cable tie slots hold the USB cable. It prints upright, the floor on the bed."""
    cx, cy = S.MAST_X, S.POLE_Y
    y0, y1 = S.FRAME_Y, S.FRAME_Y + S.MFOOT_PLATE
    zt, hx, ro = S.MFOOT_TOP, S.MFOOT_HALF_X, S.POLE_R_OUT
    # The plate: full width at the bar, 45 degrees in below the bar to the socket, on the bed.
    zb, z0 = S.BAR_Z0, S.MFOOT_Z0
    zk = zb - (hx - ro)
    pts = ((cx - hx, zt), (cx + hx, zt), (cx + hx, zb), (cx + ro, zk), (cx + ro, z0), (cx - ro, z0), (cx - ro, zk), (cx - hx, zb))
    part = extrude(Plane.XZ.offset(-y0) * poly(*pts), y1 - y0, dir=(0, 1, 0))
    part += Pos(cx, cy, z0) * Cylinder(ro, zt - z0, align=MINZ)
    # The collar ears at the back, each side of the slit.
    ey0, ey1 = cy + ro - 2.0, cy + ro + S.COLLAR_EAR
    part += box(cx - 6.8, cx + 6.8, ey0, ey1, z0, zt)
    # The socket, the slit, the M6 hole and its counterbore (with a 45 degree cone: no flat ceiling).
    rb = S.POLE_D / 2 + S.POLE_CLR
    part -= Pos(cx, cy, S.MFOOT_FLOOR) * Cylinder(rb, zt, align=MINZ)
    part -= box(cx - 0.8, cx + 0.8, cy, ey1 + 1, S.MFOOT_FLOOR, zt + 1)
    part -= Pos(cx, cy, z0 - 1) * Cylinder(S.M6_CLEAR / 2, S.MFOOT_FLOOR - z0 + 2, align=MINZ)
    rh, hh = S.M6_HEAD[0] / 2 + 0.5, S.M6_HEAD[1] + 0.5
    part -= Pos(cx, cy, z0 - 1) * Cylinder(rh, hh + 1, align=MINZ)
    part -= Pos(cx, cy, z0 + hh) * Cone(rh, S.M6_CLEAR / 2, rh - S.M6_CLEAR / 2, align=MINZ)
    # The M3 collar screw across the slit, and the hex trap for its nut on the +X ear.
    ys, zs = (ey0 + ey1) / 2, (S.MFOOT_FLOOR + zt) / 2
    part -= teardrop_x(S.M3_CLEAR, cx - 8, cx + 8, ys, zs)
    # The nut drops into a slot from the top of the ear (no ceiling in print).
    nw, nt = S.M3_NUT_AF + 0.4, S.M3_NUT_T + 0.4
    xn = cx + 3.6
    part -= box(xn - nt / 2, xn + nt / 2, ys - nw / 2, ys + nw / 2, zs - S.M3_NUT_AF / math.sqrt(3) - 0.3, zt + 1)
    # The two M5 screws into T-nuts in the bar slot.
    for dx in (-25.0, 25.0):
        part -= teardrop_y(S.M5_CLEAR, cx + dx, S.BAR_SLOT_Z[0], y0 - 1, y1 + 1)
    # Cable tie slots through the plate, each side of the socket (vertical, pointed top).
    for sx in (-1, 1):
        x = cx + sx * (ro + 9.0)
        pts = ((x - 0.8, 28.0), (x + 0.8, 28.0), (x + 0.8, 31.0), (x, 31.8), (x - 0.8, 31.0))
        part -= extrude(Plane.XZ.offset(-(y0 - 1)) * poly(*pts), S.MFOOT_PLATE + 2, dir=(0, 1, 0))
    return part


def camera():
    """The USB webcam on the top end of the pole (context, simplified)."""
    return box(S.MAST_X - 15.0, S.MAST_X + 15.0, S.POLE_Y - 12.0, S.POLE_Y + 12.0, S.POLE_TOP, S.POLE_TOP + 30.0)


# ================================================================ the stock breakout boards
# The two breakout boards of the stock CR-10 V3 harness (context). Each board stands bare on two 4 mm
# nylon standoffs on an extrusion face. Two cable ties go through the board holes and round the
# extrusion. Each board is modelled in its pose frame (shape.py): z = 0 on the extrusion face.

def brk(kind):
    """The sizes of one board in its pose frame. kind is "head" or "base"."""
    if kind == "head":
        (U, V), holes_u, hv = S.HB_PCB, S.HB_HOLES_U, S.HB_HOLES_V
        hdr, pin, pout, xh, used = S.HB_HDR_U, S.HB_PLUG_IN, S.HB_PLUG_OUT, S.HB_XH, S.HB_USED
    else:
        (U, V), holes_u, hv = S.BB_PCB, S.BB_HOLES_U, S.BB_HOLES_V
        hdr, pin, pout, xh, used = S.BB_HDR_U, S.BB_PLUG_IN, S.BB_PLUG_OUT, S.BB_XH, S.BB_USED
    xb0 = 0.0                                     # the board edge at v = 0
    zp = S.BRD_STANDOFF                           # the board underside
    zt = zp + S.BRK_PCB_T                         # the board top
    return dict(U=U, V=V, xb0=xb0, zp=zp, zt=zt, holes=[(xb0 + hv, U / 2 - u) for u in holes_u], hdr=hdr, pin=pin,
                pout=pout, xh=xh, used=used)


def _yu(d, u0, u1):
    """Board u range to the local y range (y = U/2 - u)."""
    return d["U"] / 2 - u1, d["U"] / 2 - u0


def brk_board(kind, bend=True):
    """The board, its plugs and its two standoffs (context), in the pose frame: [(name, solid)].
    With bend=True, the used XH plugs carry a block for the wire bend above them (for the fit check)."""
    d = brk(kind)
    xb0, zp, zt, V = d["xb0"], d["zp"], d["zt"], d["V"]
    out = [("pcb", box(xb0, xb0 + V, -d["U"] / 2, d["U"] / 2, zp, zt))]
    y0, y1 = _yu(d, *d["hdr"])
    xe = xb0 + V + d["pout"]
    out.append(("plug", box(xb0 + V - d["pin"], xe, y0, y1, zt, zt + S.MF_PLUG_H)))
    out.append(("tails", box(xb0 + V - d["pin"] + 0.5, xb0 + V - 0.5, y0 + 0.5, y1 - 0.5, zp - S.BRK_TAILS, zp)))
    r = S.MF_CABLE_D / 2
    out.append(("cable", Pos(xe, (y0 + y1) / 2, zt + S.MF_PLUG_H / 2) * Rot(0, 90, 0) * Cylinder(
        r, S.MF_CABLE, align=(Align.CENTER, Align.CENTER, Align.MIN))))
    for name, u0, u1, v0, v1 in d["xh"]:
        a, b = _yu(d, u0, u1)
        hgt = S.XH_H + (S.XH_BEND if bend and name in d["used"] else 0.0)
        out.append(("xh " + name, box(xb0 + v0, xb0 + v1, a, b, zt, zt + hgt)))
        out.append(("tails " + name, box(xb0 + v0 + 0.5, xb0 + v1 - 0.5, a + 0.5, b - 0.5, zp - S.BRK_TAILS, zp)))
    for i, (x, y) in enumerate(d["holes"]):
        sd = Cylinder(S.BRD_STANDOFF_D / 2, zp, align=(Align.CENTER, Align.CENTER, Align.MIN))
        out.append((f"standoff {i}", Pos(x, y, 0) * (sd - Cylinder(1.6, zp + 1, align=(Align.CENTER, Align.CENTER, Align.MIN)))))
    return out


def brk_tf(kind, c=None):
    """Pose frame to frame coordinates. Local x (v) goes up (+Z): the big plug points up. Local y
    goes to +X. Local z goes back (+Y). head: on the back face of the X beam of a gantry at y = c.
    base: on the back face of the back bar."""
    from build123d import Location
    d = brk(kind)
    if kind == "head":
        return Location(Plane((S.HB_X0 + d["U"] / 2, c + S.BEAM / 2, S.HB_Z0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)))
    return Location(Plane((S.BB_X0 + d["U"] / 2, S.FRAME_Y, S.BB_Z0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)))


# ---------------------------------------------------------------------------
# The design language: one finish for all printed parts of the main build.
# - Each outside corner that stands up in the print gets the radius EDGE_R.
# - Each outside edge of a top face in the print gets the chamfer EDGE_CH.
# The finish removes material at outside edges only. It adds no overhang, and it does not
# change a mating face, a hole or a pocket. An edge that does not take the finish keeps its shape.
# ================================================================ fixed motors, the stock X belt path, the printed X plate
# (2026-11-09). These definitions replace the omega Y drive, the X belt loop in front of the plate and the
# stock Creality X plate. shape.py has the values and the reasons.

def beam_profile_cut(c, x0, x1):
    """The four slots of the 2020 beam as a solid along X from x0 to x1 (for the belt checks): the
    opening between the lips, the channel behind the lips, the 45 degree taper to the core. ESTIMATE
    (V-slot data sheet). The beam centre is at y = c, z = BZ."""
    o, lip, w, flat, dep = S.SLOT_OPEN / 2, S.SLOT_LIP, S.SLOT_CH_W / 2, S.SLOT_CH_FLAT, S.SLOT_DEPTH
    h = S.BEAM / 2
    # One slot in the local (s, d) frame: s across the slot, d the depth from the face (0) into the beam.
    pts = [(-o, -0.01), (o, -0.01), (o, lip), (w, lip), (w, flat), (w - (dep - flat), dep), (-(w - (dep - flat)), dep),
           (-w, flat), (-w, lip), (-o, lip)]
    out = None
    for face in ("top", "bottom", "front", "back"):
        if face == "top":
            q = [(c + s, S.BZ + h - d) for s, d in pts]
        elif face == "bottom":
            q = [(c + s, S.BZ - h + d) for s, d in pts]
        elif face == "front":
            q = [(c - h + d, S.BZ + s) for s, d in pts]
        else:
            q = [(c + h - d, S.BZ + s) for s, d in pts]
        sl = extrude(Plane.YZ.offset(x0) * poly(*q), x1 - x0, dir=PX)
        out = sl if out is None else out + sl
    return out


def beam_real(c=0.0, x0=None, x1=None):
    """The 2020 beam with its four slot channels and the centre bore (the belt checks)."""
    x0 = S.BEAM_X0 if x0 is None else x0
    x1 = S.BEAM_X0 + S.BEAM_L if x1 is None else x1
    b = box(x0, x1, c - S.BEAM / 2, c + S.BEAM / 2, S.BEAM_Z0, S.BEAM_Z0 + S.BEAM)
    b -= beam_profile_cut(c, x0 - 1, x1 + 1)
    b -= _xcyl(2.1, x0 - 1, x1 + 1, c, S.BZ)
    return b


# ---------------------------------------------------------------- the X belt (stock path)

def x_pulley_at(c):
    """The X pulley centre (frame) at gantry y = c."""
    return (S.XM_X, c + S.XB_Y, S.BZ)


def x_idler_at(c, dx=0.0):
    """The X idler centre (frame), dx along the fork travel (left model dx: -dx tightens)."""
    return (S.FRAME_X - (S.XIDLER_X + dx), c + S.XB_Y, S.BZ)


def x_motor_parts(c=0.0):
    """The X motor behind the left beam end (shaft to the front, along -Y) and its GT2 pulley on the
    beam centre line. The motor face is on the back of the motor wall of the left tower."""
    px, py, pz = x_pulley_at(c)
    yf = c + S.XM_FACE_DY
    h = S.MOTOR / 2
    body = box(px - h, px + h, yf, yf + S.XMOTOR_L, pz - h, pz + h)
    # The pulley: its Z axis points to -Y; the outer flange at the front, the hub to the back.
    y0 = py - S.PULLEY["teeth_w"] / 2 - S.PULLEY["flange_t"]
    pulley = Pos(px, y0, pz) * Rot(-90, 0, 0) * gt2_pulley()
    return body, pulley


def x_motor(c=0.0):
    body, pulley = x_motor_parts(c)
    return body + pulley


def x_idler(c=0.0, dx=0.0):
    """The X idler (20T, toothed) past the right beam end, axle along Y, dx along the fork travel."""
    ix, iy, iz = x_idler_at(c, dx)
    h = S.TIDLER["h"]
    return Pos(ix, iy - h / 2, iz) * Rot(-90, 0, 0) * gt2_idler(toothed=True)


def x_belt_loop(c, xp):
    """The X belt outside the carriage (context, gantry y = c, X plate at xp): the top run in the top
    slot from the pulley to the idler, the two half wraps, and the bottom run in the bottom slot from
    the pulley and from the idler to the two ends of the carriage. 6 wide (y), 1.4 thick (z)."""
    t, w = S.BELT_T, S.BELT_W
    px, py, pz = x_pulley_at(c)
    ix = x_idler_at(c)[0]
    y0, y1 = py - w / 2, py + w / 2
    zb, zt = S.XB_RUNS
    xl, xr = xp + S.XP_X[0], xp + S.XP_X[1]
    parts = [box(px, ix, y0, y1, zt - t / 2, zt + t / 2), box(px, xl, y0, y1, zb - t / 2, zb + t / 2),
             box(xr, ix, y0, y1, zb - t / 2, zb + t / 2)]
    r = S.BELT_RUN
    for x, s in ((px, -1), (ix, 1)):
        ring = _ycyl(r + t / 2, y0, y1, x, pz) - _ycyl(r - t / 2, y0 - 1, y1 + 1, x, pz)
        parts.append(ring & box(x, x + s * (r + 2), y0 - 1, y1 + 1, pz - r - 2, pz + r + 2))
    out = parts[0]
    for q in parts[1:]:
        out = out + q
    return out


def x_belt_run_lengths(c, xp):
    """For the belt length: the straight pieces and the wraps (pitch line)."""
    px = S.XM_X
    ix = x_idler_at(c)[0]
    return {"top": ix - px, "left": xp + S.XP_X[0] - px, "right": ix - (xp + S.XP_X[1])}


# ---------------------------------------------------------------- the clamps of the X plate (plate frame)

def _xcl_frame(side):
    """The slant frame of one clamp: the exit point (x, z) on the bottom run at the plate end, the unit
    vector e along the belt into the pocket, and n across it (in the XZ plane), in the plate frame."""
    zb = S.XB_RUNS[0] - S.PLATE_DZ
    a = math.radians(S.XCL_SLANT)
    if side == "left":
        return (S.XP_X[0], zb), (math.cos(a), -math.sin(a)), (math.sin(a), math.cos(a))
    return (S.XP_X[1], zb), (-math.cos(a), -math.sin(a)), (-math.sin(a), math.cos(a))


def _slant_box(side, u0, u1, n0, n1, y0, y1):
    """A box in the slant frame of a clamp: u along the belt, n across, y as it is."""
    (x0, z0), e, n = _xcl_frame(side)
    pts = [(x0 + e[0] * u + n[0] * v, z0 + e[1] * u + n[1] * v) for u, v in ((u0, n0), (u1, n0), (u1, n1), (u0, n1))]
    return extrude(Plane.XZ.offset(-y0) * poly(*pts), y1 - y0, dir=(0, 1, 0))


XCL_POCKET_U = (S.XCL_WALL_U + S.CLIP_WALL, S.XCL_WALL_U + S.CLIP_WALL + S.CLIP_POCKET[0] + S.CLIP_LOOP)
# The top of the belt path, the slit and the pocket (n): one 45 degree ceiling from the slot exit to the
# pocket end. A step up in this ceiling makes a tooth that starts in the air in the print.
XCL_VT = S.BELT_T / 2 + 1.5


def x_jaw_point(side, u, p):
    """A point of an X clamp: u along the belt from the exit point, p from the belt centre toward the
    jaw (-n). Returns (x, y, z) in the plate frame, at the belt centre plane y."""
    (x0, z0), e, n = _xcl_frame(side)
    return (x0 + e[0] * u - n[0] * p, S.PLATE_FRONT + S.XB_Y, z0 + e[1] * u - n[1] * p)


def x_jaw_axis(side):
    """The jaw screw of an X clamp: the point on the jaw top and the direction into the clamp (+n)."""
    (_, _), _, n = _xcl_frame(side)
    top = x_jaw_point(side, XCL_POCKET_U[0] + S.JAW_SCREW_U, S.JAW_UNDER + S.JAW_T)
    return top, (n[0], 0.0, n[1])


def x_clamp_cuts(side):
    """The belt path, the slit through the end wall and the jaw pocket of one clamp, all open to the
    back (+y): the belt drops in from behind the beam, and the jaw slides in from the back. The pocket
    floor is on the beam side of the belt. Past the fold the floor is a ledge with the M3 insert. A hole
    under the jaw lets the screw head and the hex key in."""
    yb = S.PLATE_FRONT + S.XB_Y
    w = S.BELT_W / 2 + 0.6
    u0, u1 = XCL_POCKET_U
    hp = S.CLIP_POCKET[1] / 2
    pj = S.JAW_UNDER + S.JAW_T + 0.3
    uf = u0 + S.JAW_L + S.JAW_FOLD
    cut = _slant_box(side, -3.0, S.XCL_WALL_U + 0.1, -S.BELT_T / 2 - 0.9, XCL_VT, yb - w, S.XCL_BACK + 1)
    cut += _slant_box(side, S.XCL_WALL_U - 0.1, u0 + 0.1, -S.BELT_SLOT / 2, XCL_VT, yb - w, S.XCL_BACK + 1)
    cut += _slant_box(side, u0, uf, -pj, S.BELT_T / 2, yb - hp, S.XCL_BACK + 1)
    cut += _slant_box(side, uf - 0.01, u1, -pj, -S.JAW_LEDGE, yb - hp, S.XCL_BACK + 1)
    top, d = x_jaw_axis(side)
    ledge = x_jaw_point(side, u0 + S.JAW_SCREW_U, S.JAW_LEDGE)
    cut += Location(Plane(origin=ledge, z_dir=d)) * Cylinder(S.INSERT_M3["hole"] / 2, S.JAW_INSERT_DEPTH, align=MINZ)
    cut += Location(Plane(origin=top, z_dir=(-d[0], 0, -d[2]))) * Cylinder(S.JAW_HEAD_HOLE / 2, 30.0, align=MINZ)
    return cut


def x_clamp_block(side):
    """The block of one clamp under the beam: from the plate back to XCL_BACK, under the beam bottom.
    Past the fold it reaches further toward the beam, round the M3 insert of the jaw."""
    u0, u1 = XCL_POCKET_U
    pj = S.JAW_UNDER + S.JAW_T + 0.3
    blk = _slant_box(side, S.XCL_WALL_U - 1.0, u1 + 2.4, -pj - 2.4, XCL_VT + 2.4, 0.0, S.XCL_BACK)
    blk += _slant_box(side, u0 + S.JAW_L + S.JAW_FOLD - 1.0, u1 + 2.4, 0.0, 8.0, 0.0, S.XCL_BACK)
    # Under the screw end the block is solid down to the bed: the hole for the screw head opens in the
    # bottom face, and no part of the wall under the pocket hangs in the air.
    blk += _slant_box(side, u0 + S.JAW_L + S.JAW_FOLD - 1.0, u1 + 2.4, -40.0, -pj, 0.0, S.XCL_BACK)
    ztop = S.PLATE_BEAM_Z - S.BEAM / 2 - 0.5
    x0, x1 = S.XP_X
    return blk & box(x0, x1, -1, S.XCL_BACK + 1, S.XP_Z[0], ztop)


def x_belt_ends():
    """The two X belt ends on the carriage (context, plate frame): the slant from the slot into the
    pocket, the 180 degree fold back over the run, and the printed jaw on the two layers.
    [(kind, solid)]"""
    out = []
    yb = S.PLATE_FRONT + S.XB_Y
    y0, y1 = yb - S.BELT_W / 2, yb + S.BELT_W / 2
    t = S.BELT_T
    u0, u1 = XCL_POCKET_U
    for side in ("left", "right"):
        # The fold lies on the jaw side (-n) of the run.
        uf = u0 + S.JAW_L
        belt = _slant_box(side, 0.0, uf, -t / 2, t / 2, y0, y1)
        belt += _slant_box(side, uf, uf + t, -1.5 * t, t / 2, y0, y1)
        belt += _slant_box(side, u0 + 0.3, uf, -1.5 * t, -t / 2, y0, y1)
        out.append(("belt", belt))
        jaw = _slant_box(side, u0 + 0.2, u1 - 0.2, -(S.JAW_UNDER + S.JAW_T), -S.JAW_UNDER, yb - S.JAW_W / 2, yb + S.JAW_W / 2)
        top, d = x_jaw_axis(side)
        jaw -= Location(Plane(origin=top, z_dir=d)) * Cylinder(S.M3_CLEAR / 2, S.JAW_T + 1, align=MINZ)
        out.append(("clip", jaw))
    return out


def x_folds_u():
    """The fold of each X belt end, along the slant from the exit point (for the belt length)."""
    return XCL_POCKET_U[0] + S.JAW_L + S.BELT_T / 2


# ---------------------------------------------------------------- the printed X plate (plate frame)

def x_wheel_axis(i):
    _, x, z = S.X_WHEELS[i]
    return x, z


def x_carriage_plate():
    """The printed X plate, in the plate frame. A plate on the front of the beam (5 mm above and below
    the beam, 3 mm in front of it), three wheel bosses (12 mm or more: they come forward through the
    pen carriage), the two belt clamps under the beam at its ends, the four tool head holes, the X
    endstop trigger lug at the bottom left, and the tie slot of the servo loom at the top left. It prints upright: the bosses have pointed undersides."""
    x0, x1 = S.XP_X
    z0, z1 = S.XP_Z
    zb0, zb1 = S.PLATE_BEAM_Z - S.BEAM / 2 - 0.5, S.PLATE_BEAM_Z + S.BEAM / 2 + 0.5
    part = box(x0, x1, 0.0, S.XP_T, z0, z1)
    part += box(x0, x1, 0.0, S.XP_THICK, z0, zb0)
    # Over the beam: the step from 3 to 5 mm has a 45 degree underside (the plate prints upright).
    up = poly((0.0, zb1), (S.XP_T, zb1), (S.XP_THICK, zb1 + S.XP_THICK - S.XP_T), (S.XP_THICK, z1), (0.0, z1))
    part += extrude(Plane.YZ.offset(x0) * up, x1 - x0, dir=PX)
    for side in ("left", "right"):
        part += x_clamp_block(side)
    # The wheel bosses: pointed undersides (no overhang in the print).
    for i in range(3):
        x, z = x_wheel_axis(i)
        y0, y1 = S.XW_BOSS_Y[i]
        part += teardrop_y(2 * S.XW_BOSS_RS[i], x, z, y0, y1, up=False)
    # A 2 mm rib under each boss where it stands out of the plate, with a 45 degree underside toward the
    # plate: the first layer of a boss then does not start in the air.
    for i in range(3):
        x, z = x_wheel_axis(i)
        y0, y1 = S.XW_BOSS_Y[i]
        tip = z - S.XW_BOSS_RS[i] * math.sqrt(2)                  # the teardrop point
        if y0 < 0:
            rib = poly((0.5, tip - 0.5 + y0), (y0, tip), (y0, z), (0.5, z))
            part += extrude(Plane.YZ.offset(x - 1.0) * rib, 2.0, dir=PX) & box(x - 2, x + 2, -20, 20, S.XP_Z[0], 200)
        if y1 > S.XP_THICK and not (S.PLATE_BEAM_Z - S.BEAM / 2 < tip < S.PLATE_BEAM_Z + S.BEAM / 2 + 5):
            rib = poly((S.XP_THICK - 0.5, tip - (y1 - S.XP_THICK) - 0.5), (y1, tip), (y1, z), (S.XP_THICK - 0.5, z))
            part += extrude(Plane.YZ.offset(x - 1.0) * rib, 2.0, dir=PX) & box(x - 2, x + 2, -20, 20, S.XP_Z[0], 200)
    # The trigger lug of the X endstop at the bottom left, in front of the plate, with a 45 degree
    # underside. Next to the plate face the lug starts XLUG_NOTCH[0] further right: the edge of the
    # endstop board is there at the hard stop.
    lx0, lx1, lz0, lz1, ld = S.X_TRIGGER
    prof = poly((S.XP_T - 0.5, lz0 - ld - S.XP_T + 0.5), (-ld, lz0), (-ld, lz1), (S.XP_T - 0.5, lz1))
    lug = extrude(Plane.YZ.offset(lx0) * prof, lx1 - lx0, dir=PX)
    nw, nd = S.XLUG_NOTCH
    lug -= box(lx0 - 1, lx0 + nw, -nd, 0.0, lz0 - ld - 10, lz1 + 1)
    # The part of the lug left of the notch: its underside rises 45 degrees toward the left as well, so each
    # layer grows from the lug beside it (no layer starts in the air).
    k = lz0 - ld + lx0 + nw                    # the underside plane: z + x + y = k
    y0 = -ld - 1.0
    zl = lz0 - ld - 20.0
    wedge = poly((lx0 - 1, zl), (lx0 + nw, zl), (lx0 + nw, k - y0 - (lx0 + nw)), (lx0 - 1, k - y0 - (lx0 - 1)))
    lug -= extrude(Plane.XZ.offset(-y0) * wedge, (1.0 - y0) * math.sqrt(2), dir=(0, 1, -1))
    part += lug
    # The tie slot of the servo loom at the top left (a pointed top: no flat ceiling).
    tx0, tx1, tz0, tz1 = S.LOOM_TIE
    ts = poly((tx0, tz0), (tx1, tz0), (tx1, tz1), ((tx0 + tx1) / 2, tz1 + (tx1 - tx0) / 2), (tx0, tz1))
    part -= extrude(Plane.XZ.offset(1) * ts, S.XP_THICK + 2, dir=(0, 1, 0))
    # The clamp cuts, the wheel holes.
    for side in ("left", "right"):
        part -= x_clamp_cuts(side)
    for i in range(3):
        x, z = x_wheel_axis(i)
        y0, y1 = S.XW_BOSS_Y[i]
        if i == S.X_ECC:
            part -= teardrop_y(S.ECC_HOLE, x, z, y0 - 1, y1 + 1)
            # Room for the 11 mm wrench on the hex, from above: the plate back stops at the boss face (down
            # to the beam band, so no thin plate stays round the hex).
            part -= box(x - 9.0, x + 9.0, y1, S.XP_THICK + 1, z - 10.0, z1 + 1)
        else:
            # The stock 6 mm spacer stands in the back of the plate (a pointed top: no flat ceiling).
            part -= teardrop_y(S.WASHER[0] + 1.0, x, z, y1, S.XP_THICK + 1)
        if i != S.X_ECC:
            part -= teardrop_y(S.M5_CLEAR, x, z, y0 - 1, y1 + 1)
    # The four tool head holes: M3 clearance, the heads on the back face.
    for name, x, z in S.HEAD_HOLES:
        part -= teardrop_y(S.M3_CLEAR, x, z, -1, S.XP_THICK + 1)
    # The beam band: keep 0.6 mm from the beam face. Over the beam the cut rises at 45 degrees behind the
    # plate (no flat underside where a boss stands out behind the plate).
    band = poly((S.XP_T, zb0), (30.0, zb0), (30.0, zb1 + 30.0 - S.XP_T), (S.XP_T, zb1))
    part -= extrude(Plane.YZ.offset(x0 - 1) * band, x1 - x0 + 2, dir=PX)
    return part


def x_wheels(preload=0.0):
    """The three X wheels in the plate frame. The top wheels sit in the top slot of the beam, the
    bottom wheel in the bottom slot. The eccentric (top right) pushes its wheel down by preload."""
    bc = S.PLATE_BEAM_Z
    out = []
    for i, (_, x, z) in enumerate(S.X_WHEELS):
        if z > bc:
            zc = bc + S.BEAM / 2 + S.WHEEL_OFF - preload
        else:
            zc = bc - S.BEAM / 2 - S.WHEEL_OFF + preload
        out.append(Pos(x, S.PLATE_FRONT, zc) * Rot(90, 0, 0) * wheel())
    return out


def x_wheel_bolts():
    return []


def x_plate_sheet():
    return x_carriage_plate()


def x_carriage():
    """The X carriage: the printed plate and its three wheels: [(name, solid)]."""
    return [("X plate", x_carriage_plate())] + [(f"X wheel {i}", w) for i, w in enumerate(x_wheels())]


# ---------------------------------------------------------------- the pen carriage (no belt clamp now)

def pen_carriage():
    """The pen carriage, in the plate frame: the pen lift. It bolts to the front of the printed X plate
    with the four M3 tool head screws (from the back of the plate). The X belt clamps are on the plate,
    under the beam."""
    part = base()
    part -= head_screw_cuts()
    return part


# ---------------------------------------------------------------- the X idler fork (left model)

def x_idler_fork_raw(c=0.0):
    """The X idler fork at the middle of its travel (left model, before the mirror). A floor under the
    bottom run, two cheeks round the idler with the M5 axle hole, the back cheek 8 mm thick with the M3
    nut of the tension screw (slot open to the top). It sits in the pocket past the right beam end and
    slides along X. It prints on its floor."""
    ix, iz = S.XIDLER_X, S.BZ
    r = S.FORK_R
    y0, y1 = c + S.FORK_Y[0], c + S.FORK_Y[1]
    f0, f1 = S.FORK_FLOOR
    part = box(ix - r, ix + r, y0, y1, f0, f1)
    for ya, yb_ in ((y0, y0 + S.FORK_FRONT_T), (y1 - S.FORK_BACK_T, y1)):
        part += box(ix - r, ix + r, ya, yb_, f0, iz)
        # A pointed top, cut flat 1.3 mm over the round: 5 mm of material over the teardrop point of the axle hole.
        part += teardrop_y(2 * r, ix, iz, ya, yb_) & box(ix - r, ix + r, ya, yb_, f0, iz + r + 1.3)
    part -= teardrop_y(S.M5_CLEAR, ix, iz, y0 - 1, y1 + 1)
    sy, sz = S.FORK_SCREW
    part -= teardrop_x(S.M3_CLEAR, ix - r - 1, ix + r + 1, c + sy, sz)
    # The M3 nut slot, open to the bottom (the nut goes in before the fork goes on its seat), a 45 degree roof.
    nw, nt = S.M3_NUT_AF + 0.4, S.M3_NUT_T + 0.4
    xn = ix - r + S.FORK_NUT_X
    ztop = sz + S.M3_NUT_AF / 2 + 0.3
    prof = poly((c + sy - nw / 2, f0 - 1), (c + sy + nw / 2, f0 - 1), (c + sy + nw / 2, ztop), (c + sy, ztop + nw / 2),
                (c + sy - nw / 2, ztop))
    part -= extrude(Plane.YZ.offset(xn) * prof, nt, dir=PX)
    return part


def x_idler_fork(c=0.0, dx=0.0):
    return mirror_x(Pos(dx, c, 0) * _fin(("x_idler_fork",), lambda: x_idler_fork_raw(0.0), PZ))


def x_idler_fork_print():
    return _fin(("x_idler_fork",), lambda: x_idler_fork_raw(0.0), PZ)


# ---------------------------------------------------------------- the Y wheels (the inner wheel behind the beam)

def y_wheel_pos(c=0.0, preload=0.0):
    p = preload
    return [(S.YW_OUT_X + p, c - S.WHEEL_PITCH, S.YW_Z), (S.YW_OUT_X + p, c + S.WHEEL_PITCH, S.YW_Z),
            (S.YW_IN_X - p, c + S.YW_IN_DY, S.YW_Z)]


def y_wheel_stack(c=0.0):
    """The spacers, the bolts and the nuts of the three wheels of the left carriage (context), four
    items for each wheel: spacer, bolt head, nut, bolt. Outer wheels as before. Inner wheel: a socket
    head on the 12 mm boss, a spacer, the wheel, a nyloc nut under it."""
    out = []
    nt, e = S.NYLOC[1], 0.05
    r = S.SHANK["M5"] / 2
    zw0, zw1 = S.YW_Z - S.WHEEL_T / 2, S.YW_Z + S.WHEEL_T / 2
    for i, (x, y, z) in enumerate(y_wheel_pos(c)):
        if i < 2:
            ecc = i == S.YW_ECC
            h = S.YP_Z0 - zw1 - 2 * e
            sp = eccentric_real(h, 2.6) if ecc else spacer_real(S.WASHER[0], h, 2.6)
            out.append(("eccentric spacer" if ecc else "spacer", Pos(x, y, zw1 + e) * sp))
            out.append(("bolt head", Pos(x, y, zw0 - e) * socket_head("M5")))
            # Both outer wheels: an M5 x 35 up through the wheel, the spacer and the 6 mm boss, and a nyloc
            # nut on the boss. A nut cannot back out the way a screw in an insert can.
            steel, nylon = nyloc_real(S.NYLOC[0], nt, r + 0.1)
            out.append(("nut", Pos(x, y, S.YP_Z1 + S.INSERT_BOSS[1] + e) * (steel + nylon)))
            out.append(("bolt", Pos(x, y, zw0 - e) * shank("M5", S.OUT_AXLE_L)))
        else:
            zh = S.YP_Z0 + S.IN_BOSS
            sp = spacer_real(S.WASHER[0], S.YP_Z0 - zw1 - 2 * e, 2.6)
            out.append(("spacer", Pos(x, y, zw1 + e) * sp))
            out.append(("bolt head", Pos(x, y, zh + e) * Rot(180, 0, 0) * socket_head("M5")))
            steel, nylon = nyloc_real(S.NYLOC[0], nt, r + 0.1)
            out.append(("nut", Pos(x, y, zw0 - e) * Rot(180, 0, 0) * (steel + nylon)))
            out.append(("bolt", Pos(x, y, zh + e) * Rot(180, 0, 0) * shank("M5", S.IN_AXLE_L)))
    return out


def y_wheels(c=0.0, preload=0.0):
    return [Pos(x, y, z) * wheel() for x, y, z in y_wheel_pos(c, preload)]


# ---------------------------------------------------------------- the Y carriage (wheels and belt clamps only)

def y_clamp_block(c, front):
    """One clamp block of the upper Y belt run (left carriage): over the belt, a channel for the lower
    run under it, the clip pocket open to the top, the slit in the end wall."""
    x0, x1 = S.YCL_X
    z0 = S.YP_Z0
    if front:
        yw0, yw1 = c + S.YCL_FRONT[0], c + S.YCL_FRONT[1]
        yp1 = yw1 + S.CLIP_POCKET[0] + S.CLIP_LOOP
        y0, y1 = yw0, yp1 + 1.5
    else:
        yw0, yw1 = c + S.YCL_BACK[1], c + S.YCL_BACK[0]
        yp0 = yw0 - S.CLIP_POCKET[0] - S.CLIP_LOOP
        y0, y1 = yp0 - 1.5, yw1
    return box(x0, x1, y0, y1, z0, S.YCL_TOP)


def y_jaw_frame(c, front):
    """The pocket start (y, at the inner face of the end wall) and the direction along the belt into
    the pocket (+1 or -1) of a Y clamp block (left carriage)."""
    return (c + S.YCL_FRONT[1], 1) if front else (c + S.YCL_BACK[1], -1)


def y_jaw_axis(c, front):
    """The jaw screw of a Y clamp: the point on the jaw top (the screw goes down)."""
    st, sg = y_jaw_frame(c, front)
    return (S.YB_X, st + sg * S.JAW_SCREW_U, S.YB_HIGH + S.JAW_UNDER + S.JAW_T)


def y_clamp_cuts(c, front):
    """The jaw pocket of a Y clamp block, open to the top: the floor under the run, the ledge past the
    fold with the M3 insert, and the slit in the end wall (open to the top: the belt drops in)."""
    xb = S.YB_X
    hp = S.CLIP_POCKET[1] / 2
    zh = S.YB_HIGH
    st, sg = y_jaw_frame(c, front)

    def yr(u0, u1):
        a, b = st + sg * u0, st + sg * u1
        return min(a, b), max(a, b)

    uf = S.JAW_L + S.JAW_FOLD
    cut = box(xb - hp, xb + hp, *yr(0.0, uf), zh - S.BELT_T / 2, 200)
    cut += box(xb - hp, xb + hp, *yr(uf - 0.01, S.JAW_POCKET), zh + S.JAW_LEDGE, 200)
    if front:
        yw0, yw1 = c + S.YCL_FRONT[0], c + S.YCL_FRONT[1]
    else:
        yw0, yw1 = c + S.YCL_BACK[1], c + S.YCL_BACK[0]
    cut += box(xb - S.BELT_W / 2 - 0.5, xb + S.BELT_W / 2 + 0.5, min(yw0, yw1) - 1, max(yw0, yw1) + 1, zh - S.BELT_SLOT / 2, 200)
    x, y, _ = y_jaw_axis(c, front)
    zl = zh + S.JAW_LEDGE
    cut += Pos(x, y, zl - S.JAW_INSERT_DEPTH) * Cylinder(S.INSERT_M3["hole"] / 2, S.JAW_INSERT_DEPTH + 1, align=MINZ)
    return cut


def y_lower_channel(y0, y1):
    """The channel for the lower Y run under a part: straight walls, then a 45 degree roof."""
    ch0, ch1 = S.YB_X - 4.0, S.YB_X + 4.0
    zt = S.YB_LOW + S.BELT_T / 2 + 1.0
    ch = poly((ch0, S.RAIL_TOP_Z - 1), (ch1, S.RAIL_TOP_Z - 1), (ch1, zt), ((ch0 + ch1) / 2, zt + 4.0), (ch0, zt))
    return extrude(Plane.XZ.offset(-y0) * ch, y1 - y0, dir=(0, 1, 0))


def y_carriage(c=0.0, end="motor"):
    """The left Y carriage, centred at y = c: a flat 6 mm plate over the rail on three side wheels, two in
    the outer side slot, one in the inner side slot behind the beam (on a tongue). On the plate: the two
    clamp blocks of the upper Y belt run, a saddle under the beam end (the beam lies on it, one M5 through
    a short back wall into a T-nut in the back slot), and the Y endstop striker at the front edge.
    end="motor": the chain tab, the X motor wall behind the beam end, and the X endstop wall in front of
    the beam end. end="idler": the seat of the X idler fork past the beam end. The right carriage is the
    mirror image of the idler version. It prints flat, the plate on the bed."""
    motor = end == "motor"
    x0, t1 = S.XTOWER
    z0, z1 = S.YP_Z0, S.YP_Z1
    hy = S.YC_SADDLE_HALF_Y
    clr = S.CRADLE_CLR
    part = box(x0, S.YP_X1, c + S.YP_Y[0], c + S.YP_Y[1], z0, z1)
    # The clamp blocks over the belt, and the tongue to the inner wheel boss behind the beam.
    part += y_clamp_block(c, True) + y_clamp_block(c, False)
    yi = c + S.YW_IN_DY
    part += box(S.YCL_X[1] - 0.5, S.YW_IN_X, yi - S.YT_BOSS_R, yi + S.YT_BOSS_R, z0, z1)
    part += Pos(S.YW_IN_X, yi, z0) * Cylinder(S.YT_BOSS_R, S.IN_BOSS, align=MINZ)
    # The saddle under the beam, from the stop lip at the beam end to the inner face (the X hard stop).
    part += box(S.YC_STOP_X0, t1, c - hy, c + hy, z1 - 0.5, S.BEAM_Z0 - clr)
    part += box(S.YC_STOP_X0, S.BEAM_X0 - clr, c - hy, c + hy, z1 - 0.5, S.YC_STOP_TOP)
    # The back wall for the beam screw.
    wx0, wx1 = S.YC_BACK_WALL_X
    part += box(wx0, wx1, c + hy - 0.5, c + S.XTOWER_HALF_Y, z1 - 0.5, S.YC_BACK_WALL_TOP)
    if motor:
        # The X motor wall behind the beam end: the motor face on its back. Past the plate edge it stands
        # on a 45 degree underside. Next to the beam it stops under the beam.
        px = S.XM_X
        h = S.MOTOR / 2
        ya, yb_ = c + S.XM_WALL[0], c + S.XM_WALL[1]
        xe = S.BEAM_X0 - clr
        top = S.BZ + S.MOTOR / 2 + 0.5           # the full motor face: 4.7 mm of material over the top M3 holes
        prof = poly((x0, z1 - 0.5), (px - h, z1 - 0.5 + (x0 - (px - h))), (px - h, top), (xe, top), (xe, z1 - 0.5))
        part += extrude(Plane.XZ.offset(-ya) * prof, yb_ - ya, dir=(0, 1, 0))
        part += box(xe - 0.5, px + h, ya, yb_, z1 - 0.5, S.BEAM_Z0 - clr)
        # The chain tab, with two M3 pilots across it.
        ty0, ty1 = c + S.YCH_TAB_Y[0], c + S.YCH_TAB_Y[1]
        part += box(S.YCH_TAB_X0, x0 + 0.5, ty0, ty1, z0, S.YCH_TAB_Z1)
        for y in (ty0 + 5.5, ty1 - 5.5):
            part += teardrop_x(9.0, S.YCH_TAB_X0, S.YCH_TAB_X0 + 9.0, y, S.YCH_TAB_ZS) & box(S.YCH_TAB_X0, x0 + 1, ty0, ty1, z0, z0 + 30)
            part -= teardrop_x(S.SELF_TAP, S.YCH_TAB_X0 - 1, S.YCH_TAB_X0 + 9.0, y, S.YCH_TAB_ZS)
        # The X endstop wall in front of the beam end, and the standoff pillar of the board.
        sx0, sx1 = S.YC_XSW_WALL_X
        hs = es_holes_x()
        r = S.ES_STANDOFF_D / 2
        wtop = max(z for _, z in hs) + r
        part += box(sx0, sx1, c + S.YC_XSW_WALL_Y0, c - hy + 0.5, z1 - 0.5, wtop)
        yb = c + S.ES_X_BACK_DY
        ins = S.INSERT_M3
        # The two standoffs are one pillar from the plate up the front of the wall (no overhang in the print).
        hx0 = hs[0][0]
        hw = S.ES_PILLAR_HALF_X
        part += box(hx0 - hw, hx0 + hw, yb, c + S.YC_XSW_WALL_Y0 + 0.5, z1 - 0.5, wtop)
        for hx, hz in hs:
            part -= teardrop_y(ins["hole"], hx, hz, yb - 1, yb + ins["depth"])
        # A pocket for the plug pins under the board, with a pointed roof (no flat ceiling in the print).
        pins = es_parts("x", c)["body"] & box(-100, 100, yb - 0.01, yb + S.ES_STANDOFF, 0, 300)
        for pin in (pins.solids() if pins is not None and pins.volume > 0 else []):
            pb = pin.bounding_box()
            x0p, x1p = pb.min.X - 0.5, pb.max.X + 0.5
            zt = pb.max.Z + 0.5
            pk = poly((x0p, pb.min.Z - 0.5), (x1p, pb.min.Z - 0.5), (x1p, zt), ((x0p + x1p) / 2, zt + (x1p - x0p) / 2), (x0p, zt))
            part -= extrude(Plane.XZ.offset(-(yb - 1)) * pk, pb.max.Y + 0.5 - (yb - 1), dir=(0, 1, 0))
    else:
        # The seat of the X idler fork past the beam end: a block out to the end wall, on a 45 degree
        # underside past the plate edge.
        ix = S.XIDLER_X
        xe0, xe1 = ix - S.FORK_EW[1], ix - S.FORK_EW[0]
        ya, yb_ = c + S.FORK_Y[0] - S.FORK_CLR - 4.0, c + S.FORK_Y[1] + S.FORK_CLR + 4.0
        ztop = S.FORK_FLOOR[1] + 3.0
        # The 45 degree underside starts at the plate bottom: 3 mm or more of material under the tension screw.
        prof = poly((x0, z0), (xe0, z0 + (x0 - xe0)), (xe0, S.BZ + 4.0), (xe1, S.BZ + 4.0), (xe1, ztop), (x0, ztop))
        part += extrude(Plane.XZ.offset(-ya) * prof, yb_ - ya, dir=(0, 1, 0))
        # The block reaches in to the saddle: the end wall load goes into the plate and the saddle. Over the
        # eccentric boss it leaves room for the nut and the wrench.
        part += box(x0, S.YC_STOP_X0 + 0.5, ya, yb_, z1 - 0.5, ztop)
        ex, ey, _ = y_wheel_pos(c)[S.YW_ECC]
        part -= _zcyl(S.YC_ECC_CLEAR / 2, z1 + S.INSERT_BOSS[1], 300, ex, ey)
        # The stop at the back half of the beam end, beside the belt.
        part += box(S.YC_STOP_X0, S.BEAM_X0 - clr, c + S.XB_Y + S.BELT_W / 2 + 1.0, c + S.XTOWER_HALF_Y, z1 - 0.5, S.YC_BACK_WALL_TOP)
        part += box(S.YC_STOP_X0, wx0 + 0.5, c + hy - 0.5, c + S.XTOWER_HALF_Y, z1 - 0.5, S.YC_BACK_WALL_TOP)
    # The belt clamp cuts and the channel of the lower run.
    for front in (True, False):
        part -= y_clamp_cuts(c, front)
    part -= y_lower_channel(c + S.YP_Y[0] - 10, c + S.YP_Y[1] + 10)
    # The axle holes: the outer wheels (the back one eccentric), the inner wheel through its boss.
    for i, (x, y, _) in enumerate(y_wheel_pos(c)):
        if i < 2 and i == S.YW_ECC:
            part += Pos(x, y, z1 - 0.5) * Cylinder(S.ECC_BOSS_D / 2, S.INSERT_BOSS[1] + 0.5, align=MINZ)
            part -= _zcyl(S.ECC_HOLE / 2, z0 - 1, z1 + S.INSERT_BOSS[1] + 1, x, y)
        elif i < 2:
            # The front outer wheel: a 6 mm boss for the nyloc nut, an M5 clearance hole.
            bd, bh = S.INSERT_BOSS
            part += Pos(x, y, z1 - 0.5) * Cylinder(bd / 2, bh + 0.5, align=MINZ)
            part -= _zcyl(S.M5_CLEAR / 2, z0 - 1, z1 + bh + 1, x, y)
        else:
            part -= _zcyl(S.M5_CLEAR / 2, z0 - 1, z0 + S.IN_BOSS + 1, x, y)
    # The beam pocket, the hollow under the beam (a tunnel with a 45 degree roof), the beam screw.
    part -= box(S.BEAM_X0 - clr, t1 + 1, c - S.BEAM / 2 - clr, c + S.BEAM / 2 + clr, S.BEAM_Z0 - clr, 300)
    hv = S.YC_HOLLOW_HALF_Y
    zr = S.BEAM_Z0 - clr - S.YC_HOLLOW_ROOF
    part -= gable_slot_x(S.YC_HOLLOW_X0, t1 + 1, c, hv, z1, zr - hv)
    part -= teardrop_y(S.M5_CLEAR, S.BEAM_TNUT_X, S.BZ, c + S.BEAM / 2 - 1, c + S.XTOWER_HALF_Y + 1)
    # The X belt between the beam end and the pulley or the idler: a channel through the stop.
    yb = c + S.XB_Y
    hb = S.BELT_W / 2 + 0.6
    zc0, zc1 = S.XB_RUNS[0] - S.BELT_T / 2 - 1.0, S.XB_RUNS[1] + S.BELT_T / 2 + 1.0
    part -= gable_slot_x(S.BEAM_X0 - 6.0, S.BEAM_X0 + 1.0, yb, hb, zc0, zc1)
    if motor:
        px, py, pz = x_pulley_at(c)
        # The hub through the wall, the motor boss in its back face.
        part -= teardrop_y(S.PULLEY["hub_d"] + 1.0, px, pz, c + S.XM_WALL[0] - 1, c + S.XM_WALL[1] + 1)
        part -= teardrop_y(S.MOTOR_BOSS, px, pz, c + S.XM_WALL[1] - 2.5, c + S.XM_WALL[1] + 1)
        # Three M3 motor screws from the front of the wall (the fourth would sit over the beam end); a key
        # hole through the saddle in front of the inner one.
        for dx, dz in x_motor_screws():
            sx, sz = px + dx, pz + dz
            part -= teardrop_y(S.M3_CLEAR, sx, sz, c + S.XM_WALL[0] - 1, c + S.XM_WALL[1] + 1)
            part -= teardrop_y(S.M3_HEAD[0] + 1.0, sx, sz, c - S.XTOWER_HALF_Y - 1, c + S.XM_WALL[0] + S.XM_SCREW_CB)
    else:
        ix = S.XIDLER_X
        # The fork pocket: open to the top and to the outside; the floor carries the fork.
        r = S.FORK_R
        xa = ix - S.FORK_EW[0] + 0.01
        xb_ = ix + max(r, S.IDLER_R) + max(S.XIDLER_TRAVEL) + 0.5
        part -= box(xa, xb_, c + S.FORK_Y[0] - S.FORK_CLR, c + S.FORK_Y[1] + S.FORK_CLR, S.FORK_FLOOR[0] - S.FORK_CLR, 300)
        # Room for the head and the nut of the axle over the fork travel.
        hr = S.M5_HEAD[0] / 2 + 0.8
        part -= box(ix + min(S.XIDLER_TRAVEL) - hr, ix + max(S.XIDLER_TRAVEL) + hr, c + S.FORK_Y[0] - S.M5_HEAD[1] - 1.0,
                    c + S.FORK_Y[1] + S.NYLOC[1] + 1.0, S.BZ - hr, 300)
        # The tension screw through the end wall (the head on the outer face).
        sy, sz = S.FORK_SCREW
        part -= teardrop_x(S.M3_CLEAR, ix - S.FORK_EW[1] - 1, ix - S.FORK_EW[0] + 1, c + sy, sz)
    part += y_striker(c, end)
    return part


def x_motor_screws():
    """The three M3 screws of the X motor (dx, dz from the pulley axis): not the one over the beam end."""
    h = S.MOTOR_HOLES / 2
    return [(-h, -h), (-h, h), (h, -h)]


# ---------------------------------------------------------------- the Y drive: the motor at the back, the idler at the front (static)

def y_stepper(c=None):
    """The left Y motor behind the back bar (static): the body (shaft along +X) and the pulley."""
    h = S.MOTOR / 2
    xf = S.YM_FACE_X
    body = box(xf - S.MOTOR_L, xf, S.YM_Y - h, S.YM_Y + h, S.YB_AX - h, S.YB_AX + h)
    x0 = S.YB_X - S.PULLEY["teeth_w"] / 2 - S.PULLEY["flange_t"]      # the outer flange toward the motor, the hub to +x
    pulley = Pos(x0, S.YM_Y, S.YB_AX) * x_axis(gt2_pulley())
    return body, pulley


def y_idler(dy=0.0):
    """The left Y idler (20T, toothed) in front of the front bar, axle along X (static)."""
    h = S.TIDLER["h"]
    return Pos(S.YB_X - h / 2, S.YI_Y + dy, S.YB_AX) * x_axis(gt2_idler(toothed=True))


def y_omega_idlers(c=None):
    return [y_idler()]


def omega_points(c):
    return {"pulley": (S.YM_Y, S.YB_AX), "idler_front": (S.YI_Y, S.YB_AX), "idler_back": (S.YI_Y, S.YB_AX)}


def y_belt(c):
    """The left Y belt at gantry y = c (context): the lower run from the idler to the pulley, the two
    half wraps, the upper run from the idler to the front clamp and from the back clamp to the pulley.
    Flat: 6 wide (x), 1.4 thick (z)."""
    t, w = S.BELT_T, S.BELT_W
    x0, x1 = S.YB_X - w / 2, S.YB_X + w / 2
    yi, ym = S.YI_Y, S.YM_Y
    zl, zh, za = S.YB_LOW, S.YB_HIGH, S.YB_AX
    yf, yb = c + S.YCL_FRONT[0] + 0.5, c + S.YCL_BACK[0] - 0.5
    parts = [box(x0, x1, yi, ym, zl - t / 2, zl + t / 2), box(x0, x1, yi, yf, zh - t / 2, zh + t / 2),
             box(x0, x1, yb, ym, zh - t / 2, zh + t / 2)]
    r = S.BELT_RUN
    for y, s in ((yi, -1), (ym, 1)):
        ring = _xcyl(r + t / 2, x0, x1, y, za) - _xcyl(r - t / 2, x0 - 1, x1 + 1, y, za)
        a, b = sorted((y, y + s * (r + 2)))
        parts.append(ring & box(x0 - 1, x1 + 1, a, b, za - r - 2, za + r + 2))
    out = parts[0]
    for q in parts[1:]:
        out = out + q
    return out


def y_belt_ends(c=0.0):
    """The two folded ends of the upper run of the left Y belt in the clamp blocks of the carriage, and
    their printed jaws (context, gantry y = c): [(kind, solid)]."""
    out = []
    t, w = S.BELT_T, S.BELT_W
    x0, x1 = S.YB_X - w / 2, S.YB_X + w / 2
    zs = S.YB_HIGH
    for front in (True, False):
        st, sg = y_jaw_frame(c, front)

        def yb(u0, u1):
            a, b = st + sg * u0, st + sg * u1
            return min(a, b), max(a, b)

        belt = box(x0, x1, *yb(-(S.CLIP_WALL + 0.5), S.JAW_L), zs - t / 2, zs + t / 2)
        belt += box(x0, x1, *yb(S.JAW_L, S.JAW_L + t), zs - t / 2, zs + 1.5 * t)
        belt += box(x0, x1, *yb(0.3, S.JAW_L), zs + t / 2, zs + 1.5 * t)
        out.append(("belt", belt))
        jaw = box(S.YB_X - S.JAW_W / 2, S.YB_X + S.JAW_W / 2, *yb(0.2, S.JAW_POCKET - 0.2), zs + S.JAW_UNDER,
                  zs + S.JAW_UNDER + S.JAW_T)
        x, y, z = y_jaw_axis(c, front)
        jaw -= Pos(x, y, z - S.JAW_T - 1) * Cylinder(S.M3_CLEAR / 2, S.JAW_T + 2, align=MINZ)
        out.append(("clip", jaw))
    return out


def y_belt_folds(c=0.0):
    """The middle of the fold of the front and the back end of the upper run (y), at gantry y = c."""
    (f0, fs), (b0, bs) = y_jaw_frame(c, True), y_jaw_frame(c, False)
    return f0 + fs * (S.JAW_L + S.BELT_T / 2), b0 + bs * (S.JAW_L + S.BELT_T / 2)


def belt_jaw():
    """The printed jaw of a belt end, in its print orientation: the flat underside on the bed. The
    same jaw goes in all 6 clamp pockets."""
    jaw = box(0.0, S.JAW_LEN, -S.JAW_W / 2, S.JAW_W / 2, 0.0, S.JAW_T)
    return jaw - Pos(S.JAW_SCREW_U - 0.2, 0, -1) * Cylinder(S.M3_CLEAR / 2, S.JAW_T + 2, align=MINZ)


def y_motor_mount():
    """The left Y motor bracket on the back face of the back bar: a 6 mm plate for the motor face (the
    motor outside, the pulley inside), a wing on the bar face with two M5 into T-nuts in the face slot,
    and a floor between them. A pocket clears the head of the bar end screw. It prints on the motor face
    (+X up): the holes along Y have their point to +X."""
    xf, t = S.YM_FACE_X, S.YM_PLATE_T
    yb = S.FRAME_Y
    h = S.MOTOR / 2
    y1 = S.YM_Y + h + 1.0
    z0 = S.BAR_Z0
    zt = S.YB_AX + h + 1.0
    part = box(xf, xf + t, yb, y1, z0, zt)
    wx1 = S.YM_SCREWS_X[1] + 7.0
    part += box(xf, wx1, yb, yb + 6.0, z0, S.RAIL_TOP_Z - 1.0)      # 1 mm under the bar top: the belt passes over it
    part += box(xf, xf + 22.0, yb, y1, z0, z0 + 5.0)
    # A web between the motor plate and the wing, under the motor screw heads: the belt pulls the motor
    # toward the bar, and the web carries that bend at the corner.
    zw = S.YB_AX - S.MOTOR_HOLES / 2 - S.M3_HEAD[0] / 2 - 1.0
    web = poly((xf + t - 0.5, yb + 5.5), (xf + t + 13.0, yb + 5.5), (xf + t - 0.5, S.YM_Y))   # clear of the M5 head at x 46.5
    part += extrude(Plane.XY.offset(z0) * web, zw - z0, dir=PZ)
    # The motor: the boss through the plate (no bridge in the print), four M3 holes (the heads inside).
    part -= Pos(xf - 1, S.YM_Y, S.YB_AX) * x_axis(Cylinder(S.MOTOR_BOSS / 2, t + 2, align=MINZ))
    for dy in (-S.MOTOR_HOLES / 2, S.MOTOR_HOLES / 2):
        for dz in (-S.MOTOR_HOLES / 2, S.MOTOR_HOLES / 2):
            part -= Pos(xf - 1, S.YM_Y + dy, S.YB_AX + dz) * x_axis(Cylinder(S.M3_CLEAR / 2, t + 2, align=MINZ))
    zs = S.BAR_SLOT_Z[0]
    for x in S.YM_SCREWS_X:
        part -= hole_up(S.M5_CLEAR, (x, yb - 1, zs), (0, 1, 0), 8.0, (1, 0, 0))
    # The pocket over the bar end screw head: a 45 degree point to +X.
    hr = S.BAR_SCREW_HEAD[0] / 2 + 1.0
    xs = S.BAR_SCREW_X[1]
    pk = poly((xs - hr, zs - hr), (xs + hr, zs - hr), (xs + hr + hr, zs), (xs + hr, zs + hr), (xs - hr, zs + hr))
    part -= extrude(Plane.XZ.offset(-(yb - 1)) * pk, S.BAR_SCREW_HEAD[1] + 2.0, dir=(0, 1, 0))
    return part


def y_idler_fork_raw(dy=0.0):
    """The left Y idler fork (frame position, dy along its travel): a floor under the lower run, two
    cheeks round the idler with the M5 axle hole, the outer cheek 8 mm thick with the M3 nut of the
    tension screw (slot open to the top). It slides along Y on the arm of the front base. It prints on
    its floor."""
    yi, za = S.YI_Y + dy, S.YB_AX
    r = S.FORK_R
    x0, x1 = S.YFORK_X
    f0, f1 = S.YFORK_FLOOR
    hw = S.TIDLER["h"] / 2 + S.FORK_WASHER
    part = box(x0, x1, yi - r, yi + r, f0, f1)
    for xa, xb_ in ((x0, S.YB_X - hw), (S.YB_X + hw, x1)):
        part += box(xa, xb_, yi - r, yi + r, f0, za)
        # A pointed top, cut flat 1.3 mm over the round: 5 mm of material over the teardrop point of the axle hole.
        part += teardrop_x(2 * r, xa, xb_, yi, za) & box(xa, xb_, yi - r, yi + r, f0, za + r + 1.3)
    part -= teardrop_x(S.M5_CLEAR, x0 - 1, x1 + 1, yi, za)
    sx, sz = S.YFORK_SCREW
    part -= teardrop_y(S.M3_CLEAR, sx, sz, yi - r - 1, yi + r + 1)
    # The M3 nut slot, open to the bottom, a 45 degree roof.
    nw, nt = S.M3_NUT_AF + 0.4, S.M3_NUT_T + 0.4
    yn = yi - r + S.FORK_NUT_X
    ztop = sz + S.M3_NUT_AF / 2 + 0.3
    prof = poly((sx - nw / 2, f0 - 1), (sx + nw / 2, f0 - 1), (sx + nw / 2, ztop), (sx, ztop + nw / 2), (sx - nw / 2, ztop))
    part -= extrude(Plane.XZ.offset(-yn) * prof, nt, dir=(0, 1, 0))
    return part


def y_fork_frame():
    """The x of the fork guides and the lips, the end wall y range, the seat and the bracket bottom (z)."""
    fx0, fx1 = S.YFORK_X
    # The inner guide is 9 mm wide: a 3 mm ring of material round the M3 pilot of the lip screw. The outer
    # guide is 4 mm wide and has no screw (the bar end screw head is next to it): its lip only holds it down.
    gx0, gx1 = fx0 - S.FORK_CLR - 4.0, fx1 + S.FORK_CLR + 9.0
    ye0, ye1 = S.YI_Y - S.YFORK_EW[1], S.YI_Y - S.YFORK_EW[0]
    seat = S.YFORK_FLOOR[0] - S.FORK_CLR
    return fx0, fx1, gx0, gx1, ye0, ye1, seat, seat - 5.0


def y_lip_screws():
    """The M3 screw of the inner lip into the idler bracket (x, y): one for each bracket."""
    fx0, fx1, gx0, gx1, *_ = y_fork_frame()
    y = -S.YLIP[1] + 4.5        # 4.5 mm from the lip front: behind the idler axle head and nut
    return [((fx1 + S.FORK_CLR + gx1) / 2, y)]


def y_front_base(side="left"):
    """The front base of the left Y belt (frame position): on the front bar and the rail end, with the
    Y endstop board, two M5 counterbored holes into the top slot of the bar, a channel for the lower
    run, and two lips in front of the bar over the guides of the idler bracket (an M3 screw down through
    the inner lip). It prints on its bottom face."""
    z0, zt = S.RAIL_TOP_Z, S.YF_TOP
    x0, x1 = S.YF_X
    ch0, ch1 = S.YB_X - 7.5, S.YB_X + 7.5
    part = box(x0, x1, 0.0, S.BAR_D, z0, zt)
    part += box(x0, ch0, 0.0, S.YF_Y1, z0, zt)                     # under the endstop board, to y 35
    part += box(ch0, ch1, 0.0, S.YF_CH_Y1, z0, zt)                 # over the belt, to y 30
    for hx, hy in es_holes_y():
        part += (Pos(hx, hy, z0) * Cylinder(S.ES_STANDOFF_DY / 2, zt - z0 + S.ES_STANDOFF, align=MINZ)) & \
            box(x0 - 1, ch0 - 0.05, -5, S.YF_Y1 + 5, z0, zt + S.ES_STANDOFF)
    fx0, fx1, gx0, gx1, *_ = y_fork_frame()
    for xa, xb in ((gx0, fx0 - S.FORK_CLR), (fx1 + S.FORK_CLR, gx1)):
        part += box(xa, xb, -S.YLIP[1], 0.5, z0, z0 + S.YLIP[0])
    for x, y in y_lip_screws():
        part -= Pos(x, y, z0 - 1) * Cylinder(S.M3_CLEAR / 2, S.YLIP[0] + 2, align=MINZ)
    part -= y_lower_channel(-S.YLIP[1] - 1, S.YF_Y1 + 1)
    # The two M5 holes, counterbored from the top (the floor 6 mm).
    for x in S.YF_SCREWS_X:
        part -= Pos(x, S.BAR_D / 2, z0 - 1) * Cylinder(S.M5_CLEAR / 2, zt - z0 + 2, align=MINZ)
        part -= Pos(x, S.BAR_D / 2, z0 + S.ANCHOR_FLOOR) * Cylinder(S.M5_HEAD[0] / 2 + 0.5, zt, align=MINZ)
    # The two M3 heat-set inserts of the endstop board, from the top of the standoffs.
    ins = S.INSERT_M3
    for hx, hy in es_holes_y():
        part -= Pos(hx, hy, zt + S.ES_STANDOFF - ins["depth"]) * Cylinder(ins["hole"] / 2, ins["depth"] + 1, align=MINZ)
    return part if side == "left" else mirror_x(part)


def y_ear_screw():
    """The M5 screw of the ear of the left idler bracket: the point on the bar face (x, y, z)."""
    gx1 = y_fork_frame()[3]
    return (gx1 + S.YBRK_EAR_W / 2, 0.0, S.BAR_SLOT_Z[0])


def y_ear_cut():
    """The hole of the ear screw: the hole for the head and the key from the front face, the 45 degree
    cone seat of the countersunk head, and the clearance hole to the bar face."""
    x, _, z = y_ear_screw()
    ye0 = y_fork_frame()[4]
    d, k = S.CSK["M5"]
    yt = -S.YBRK_EAR_CLAMP                  # the head top
    r0, r1 = d / 2 + 0.2, S.M5_CLEAR / 2
    seat = _rev([(0, 0), (r0, 0), (r0, k - (r0 - r1)), (r1, k), (r1, S.YBRK_EAR_CLAMP + 1), (0, S.YBRK_EAR_CLAMP + 1)])
    cut = Location(Plane(origin=(x, yt, z), z_dir=(0, 1, 0))) * seat
    cut += _ycyl(r0, ye0 - 1, yt + 0.01, x, z)
    return cut


def y_idler_bracket(side="left"):
    """The idler bracket of the left Y belt in front of the front bar (frame position): the seat of the
    fork between two guides, and the end wall with the M3 tension screw (the head at the front). It
    leans on the front face of the bar (the belt pulls it back), and the two lips of the front base
    hold it (an M3 screw into the top of the inner guide). Pockets clear the bar end screw heads. It prints
    on its front face (the end wall on the bed)."""
    fx0, fx1, gx0, gx1, ye0, ye1, seat, za = y_fork_frame()
    zg = S.RAIL_TOP_Z                                              # the guides end under the lips
    part = box(gx0, gx1, ye0, 0.0, za, seat)
    part += box(gx0, fx0 - S.FORK_CLR, ye0, 0.0, za, zg)
    part += box(fx1 + S.FORK_CLR, gx1, ye0, 0.0, za, zg)
    part += box(gx0, gx1, ye0, ye1, za, S.YB_AX + 4.0)
    hr = S.BAR_SCREW_HEAD[0] / 2 + 0.5
    for xs in S.BAR_SCREW_X:
        part -= box(xs - hr, xs + hr, -S.BAR_SCREW_HEAD[1] - 1.0, 0.01, S.BAR_SLOT_Z[0] - hr, S.BAR_SLOT_Z[0] + hr)
    part -= box(fx0 - S.FORK_CLR, fx1 + S.FORK_CLR, ye1 - 0.01, 0.02, seat, 300)
    sx, sz = S.YFORK_SCREW
    part -= _ycyl(S.M3_CLEAR / 2, ye0 - 1, ye1 + 1, sx, sz)        # vertical in the print: round
    # The ear beside the inner guide: an M5 countersunk screw into a T-nut in the front face slot of the bar.
    part += box(gx1 - 0.01, gx1 + S.YBRK_EAR_W, ye0, 0.0, za, zg)
    part -= y_ear_cut()
    for x, y in y_lip_screws():
        part -= hole_up(S.SELF_TAP, (x, y, zg - 9.0), (0, 0, 1), 9.5, (0, 1, 0))
    return part if side == "left" else mirror_x(part)


_FINISHED = {}


def _edge_faces(part):
    """[(edge, face, face)] for each edge between two faces."""
    m = {}
    for f in part.faces():
        for e in f.edges():
            m.setdefault(e, []).append(f)
    return [(e, fl[0], fl[1]) for e, fl in m.items() if len(fl) == 2]


def _convex(part, e, f1, f2):
    """True if the edge e between f1 and f2 is an outside edge of the solid."""
    p = e.position_at(0.5)
    try:
        n1, n2 = f1.normal_at(p), f2.normal_at(p)
    except Exception:
        return False
    if abs(n1.dot(n2)) > 0.995:
        return False                       # a smooth or flat join
    q = p + (n1 - n2) * 0.05
    return not part.is_inside(q)


def _height(sh, upv):
    bb = sh.bounding_box()
    return max(Vector(x, y, z).dot(upv) for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y) for z in (bb.min.Z, bb.max.Z))


def _runs_into_wall(part, e, top_face, upv, vfaces):
    """True if an end of the edge e touches a face that goes on up past the top face: a wall that
    stands on this face. A chamfer there leaves a sliver face that does not mesh well."""
    h = top_face.center().dot(upv)
    for v in e.vertices():
        for f in vfaces.get(v, []):
            if f.geom_type.name != "PLANE" and _height(f, upv) > h + 0.01:
                return True
    return False


def _mesh_ok(shape):
    """True if the STL mesh of the shape is closed: each mesh edge has two triangles."""
    from build123d import export_stl
    import os, struct, tempfile
    fd, path = tempfile.mkstemp(suffix=".stl")
    os.close(fd)
    try:
        export_stl(shape, path, tolerance=0.004, angular_tolerance=0.05)
        data = open(path, "rb").read()
    finally:
        os.remove(path)
    n = struct.unpack("<I", data[80:84])[0]
    count = {}
    for i in range(n):
        o = 84 + i * 50 + 12
        v = [tuple(round(x, 4) for x in struct.unpack("<3f", data[o + 12 * k:o + 12 * k + 12])) for k in range(3)]
        for a_, b_ in ((v[0], v[1]), (v[1], v[2]), (v[2], v[0])):
            key = (a_, b_) if a_ < b_ else (b_, a_)
            count[key] = count.get(key, 0) + 1
    return all(c == 2 for c in count.values())


def _apply(part, edges, op, mesh_check=True):
    """Apply op (fillet or chamfer) to the edges. Split the set where the kernel fails or where the
    result does not mesh as a closed solid."""
    if not edges:
        return part, 0
    try:
        out = op(part, edges)
        sol = out.solids()
        if len(sol) == 1:
            out = sol[0]
        if len(sol) == 1 and out.is_valid and (not mesh_check or _mesh_ok(out)):
            return out, len(edges)
    except Exception:
        pass
    if len(edges) == 1:
        return part, 0
    h = len(edges) // 2
    part, a = _apply(part, edges[:h], op, mesh_check)
    # The edges of the second half are new objects after the first half changed the solid.
    keep = []
    def _mid(x):
        try:
            return x.position_at(0.5)
        except Exception:                  # a degenerate edge left by the first half
            return Vector(1e9, 1e9, 1e9)
    for e in edges[h:]:
        c = _mid(e)
        best = min(part.edges(), key=lambda x: (_mid(x) - c).length)
        if (_mid(best) - c).length < 1e-3 and abs(best.length - e.length) < 1e-3:
            keep.append(best)
    part, b = _apply(part, keep, op, mesh_check)
    return part, a + b


def finish(part, up, top=True):
    """The design finish of a printed part. up is the print up direction in the model frame. With
    top=False, the part gets the corner radius only (a part with a sliding fit on its top edges)."""
    from build123d import Solid
    upv = Vector(*up)
    want_top = top
    vert = []
    for e, f1, f2 in _edge_faces(part):
        if e.geom_type.name != "LINE" or e.length < 2.5:
            continue
        d = (e.position_at(1) - e.position_at(0)).normalized()
        if abs(d.dot(upv)) < 0.999:
            continue
        if f1.geom_type.name != "PLANE" or f2.geom_type.name != "PLANE":
            continue
        if _convex(part, e, f1, f2):
            vert.append(e)
    # Skip an edge that shares its line with another edge (a corner split in two by a step): the
    # fillet seam between the two does not mesh well.
    def _line(e):
        p = e.position_at(0.5)
        return tuple(round(v, 2) for v in (p - upv * p.dot(upv)))
    lines = {}
    for e in vert:
        lines.setdefault(_line(e), []).append(e)
    vert = [e for e in vert if len(lines[_line(e)]) == 1]
    part, nv = _apply(part, vert, lambda p, es: p.fillet(S.EDGE_R, es))
    vfaces = {}
    for f in part.faces():
        for v in f.vertices():
            vfaces.setdefault(v, []).append(f)
    top = []
    for e, f1, f2 in _edge_faces(part):
        tops = [f for f in (f1, f2) if f.geom_type.name == "PLANE" and f.normal_at(e.position_at(0.5)).dot(upv) > 0.999]
        if len(tops) != 1:
            continue
        other = f2 if tops[0] is f1 else f1
        if e.length < 1.0:
            continue
        # The side face must be a wall that stands up: a plane, or a cylinder on an axis along up.
        if other.geom_type.name == "PLANE":
            side_ok = abs(other.normal_at(e.position_at(0.5)).dot(upv)) < 0.2
        elif other.geom_type.name == "CYLINDER":
            side_ok = all(abs(other.normal_at(e.position_at(t)).dot(upv)) < 1e-6 for t in (0.0, 0.5, 1.0))
        else:
            side_ok = False
        if side_ok and _convex(part, e, f1, f2) and not _runs_into_wall(part, e, tops[0], upv, vfaces):
            top.append(e)
    part, nt = _apply(part, top if want_top else [], lambda p, es: p.chamfer(S.EDGE_CH, None, es), mesh_check=False)
    if not isinstance(part, Solid) and hasattr(part, "solids") and len(part.solids()) == 1:
        part = part.solids()[0]
    return part, nv, nt


def _fin(key, build, up, top=True):
    if key not in _FINISHED:
        part, nv, nt = finish(build(), up, top)
        _FINISHED[key] = part
        FINISH_LOG[key] = (nv, nt)
    return _FINISHED[key]


FINISH_LOG = {}


# The raw parts stay available as raw_<name>. The public names give the finished parts. Each finished
# part is made once at its base position and then moved.
raw_y_carriage, raw_y_front_base = y_carriage, y_front_base
raw_y_chain_anchor, raw_pen_carriage, raw_mast_foot = y_chain_anchor, pen_carriage, mast_foot
UP = {"y_carriage": PZ, "y_front_base": PZ, "y_chain_anchor": MY, "pen_carriage": MY, "mast_foot": PZ}


def y_carriage(c=0.0, end="motor"):
    out = Pos(0, c, 0) * _fin(("y_carriage", end), lambda: raw_y_carriage(0.0, end), UP["y_carriage"])
    if end == "idler":
        # The right carriage is the mirror image. A mirrored fillet does not mesh well, so mirror_x
        # gives the mirror of the raw part with its own finish.
        out._mirror_alt = lambda: Pos(0, c, 0) * _right_carriage()
    return out




def y_front_base(side="left"):
    return _fin(("y_front_base", side), lambda: raw_y_front_base(side), UP["y_front_base"])






def y_chain_anchor():
    return _fin(("y_chain_anchor",), raw_y_chain_anchor, UP["y_chain_anchor"])


def pen_carriage():
    # The rails of the pen slider are on the top face in the print: the corner radius only.
    return _fin(("pen_carriage",), raw_pen_carriage, UP["pen_carriage"], top=False)


def mast_foot():
    return _fin(("mast_foot",), raw_mast_foot, UP["mast_foot"])


raw_x_carriage_plate, raw_y_motor_mount, raw_y_idler_fork = x_carriage_plate, y_motor_mount, y_idler_fork_raw


def x_carriage_plate():
    # The plate prints upright (plate frame +Z up).
    return _fin(("x_carriage_plate",), raw_x_carriage_plate, PZ)


def y_motor_mount(side="left"):
    part = _fin(("y_motor_mount",), raw_y_motor_mount, PX)
    return part if side == "left" else mirror_x(part)


def y_idler_fork(dy=0.0, side="left"):
    part = Pos(0, dy, 0) * _fin(("y_idler_fork",), lambda: raw_y_idler_fork(0.0), PZ)
    return part if side == "left" else mirror_x(part)


raw_y_idler_bracket = y_idler_bracket


def y_idler_bracket(side="left"):
    part = _fin(("y_idler_bracket",), lambda: raw_y_idler_bracket("left"), (0, 1, 0))
    return part if side == "left" else mirror_x(part)


def y_idler_fork_print():
    return _fin(("y_idler_fork",), lambda: raw_y_idler_fork(0.0), PZ)


# ---------------------------------------------------------------- real hardware shapes
# Each shape is on the Z axis. A screw head is under Z = 0 (the bearing face at Z = 0), the shank
# goes up from Z = 0. A nut, a washer or an insert goes up from Z = 0.

def _rev(pts):
    """A solid of revolution about Z from a profile [(r, z)]."""
    return revolve(Plane.XZ * poly(*pts), Axis.Z)


def _hex_prism(af, z0, z1):
    from build123d import RegularPolygon
    return Pos(0, 0, z0) * extrude(RegularPolygon(af / math.sqrt(3), 6), z1 - z0, dir=PZ)


def socket_head(size):
    """ISO 4762 socket head: a chamfered cylinder with a hex socket, under Z = 0."""
    d, k = S.SOCKET[size]
    s, t = S.HEX_KEY[size]
    ch = 0.08 * d
    head = _rev([(0, -k), (d / 2 - ch, -k), (d / 2, -k + ch), (d / 2, 0), (0, 0)])
    return head - _hex_prism(s, -k - 0.1, -k + t) - Pos(0, 0, -k + t) * Cone(s / 2, 0.05, s * 0.29, align=MIN_Z_ONLY)


MIN_Z_ONLY = (Align.CENTER, Align.CENTER, Align.MIN)


def button_head(size):
    """ISO 7380 button head: a low dome with a hex socket, under Z = 0."""
    d, k = S.BUTTON[size]
    s, t = S.BUTTON_KEY[size]
    pts = [(0, -k)]
    for i in range(1, 7):
        a = i / 6
        pts.append((0.42 * d * math.sin(a * math.pi / 2), -k + (k - 0.35) * (1 - math.cos(a * math.pi / 2))))
    pts += [(d / 2, -0.35), (d / 2, 0), (0, 0)]
    head = _rev(pts)
    return head - _hex_prism(s, -k - 0.1, -k + t)


def pan_head(size):
    """A pan head with a cross recess, under Z = 0."""
    d, k = S.PAN[size]
    head = _rev([(0, -k), (0.4 * d, -k), (d / 2, -k + 0.4 * k), (d / 2, 0), (0, 0)])
    w = 0.12 * d
    return head - box(-0.3 * d, 0.3 * d, -w / 2, w / 2, -k - 0.1, -k + 0.5 * k) - box(-w / 2, w / 2, -0.3 * d, 0.3 * d, -k - 0.1, -k + 0.5 * k)


def csk_head(size):
    """ISO 10642 countersunk head with a hex socket: the top face at Z = 0, the 90 degree cone goes up
    into the part (+Z), the same way as the shank."""
    d, k = S.CSK[size]
    r = S.SHANK[size] / 2
    s_, t = S.CSK_KEY[size]
    head = _rev([(0, 0), (d / 2, 0), (d / 2, k - (d / 2 - r)), (r, k), (0, k)])
    return head - _hex_prism(s_, -0.1, t)


def shank(size, length):
    """The shank from Z = 0 to length, with a chamfered tip."""
    r = S.SHANK[size] / 2
    c = min(0.4 * r, length / 4)
    return _rev([(0, 0), (r, 0), (r, length - c), (r - c, length), (0, length)])


def hex_nut_real(af, m, bore):
    """ISO 4032 hex nut from Z = 0 to m, with the 30 degree chamfer on both faces."""
    rw, rc = 0.475 * af, af / math.sqrt(3) + 0.05
    h = (rc - rw) * math.tan(math.radians(30))
    body = _rev([(0, 0), (rw, 0), (rc, h), (rc, m - h), (rw, m), (0, m)]) & _hex_prism(af, -1, m + 1)
    return body - Pos(0, 0, -1) * Cylinder(bore, m + 2, align=MIN_Z_ONLY)


def nyloc_real(af, h, bore):
    """ISO 7040 nyloc nut from Z = 0 to h: (the steel body, the nylon ring). The hex part is at the
    bottom; the round collar on top holds the nylon ring."""
    m = S.NYLOC_HEX * h
    steel = hex_nut_real(af, m, bore)
    rc = 0.45 * af
    collar = _rev([(bore + 0.9, m - 0.1), (rc, m - 0.1), (rc, h - 0.6), (rc - 0.6, h), (bore + 0.9, h)])
    nylon = _rev([(bore, m + 0.2), (bore + 0.9, m + 0.2), (bore + 0.9, h - 0.25), (bore, h - 0.25)])
    return steel + collar, nylon


def washer_real(od, t, bore):
    return _rev([(bore, 0), (od / 2, 0), (od / 2, t), (bore, t)])


def spacer_real(od, h, bore):
    """A round aluminium spacer with small edge chamfers."""
    c = 0.3
    return _rev([(bore, 0), (od / 2 - c, 0), (od / 2, c), (od / 2, h - c), (od / 2 - c, h), (bore, h)])


def eccentric_real(h, bore):
    """The stock eccentric spacer, from Z = 0 to h, its bore on the Z axis: a hex body set off from the
    bore by the eccentric offset (the body turns the axle in its hole)."""
    e = S.ECC
    body = Pos(e["off"], 0, 0) * _hex_prism(e["af"], 0, h)
    rw, rc = 0.475 * e["af"], e["af"] / math.sqrt(3) + 0.05
    k = (rc - rw) * math.tan(math.radians(30))
    body &= Pos(e["off"], 0, 0) * _rev([(0, 0), (rw, 0), (rc, k), (rc, h - k), (rw, h), (0, h)])
    return body - Pos(0, 0, -1) * Cylinder(bore, h + 2, align=MIN_Z_ONLY)


def tnut_real():
    """An M5 drop-in (roll-in) T-nut for a 6 mm slot, on the Z axis, its top (the slot side) at Z = 0
    and the body below: a narrow ridge that sits in the slot opening, then a body with a round
    underside. Local X runs along the slot."""
    ln, w, t = S.TNUT
    ridge_w = S.SLOT_OPEN - 0.4
    r = w / 2
    # The section across the slot (y, z): the ridge, the shoulders, a round underside.
    pts = [(-ridge_w / 2, 0.0), (ridge_w / 2, 0.0), (ridge_w / 2, -1.2), (r, -1.2), (r, -2.2)]
    for i in range(1, 8):
        a = math.pi * i / 8
        pts.append((r * math.cos(a), -2.2 - (t - 2.2 + 0.6) * math.sin(a)))
    pts += [(-r, -2.2), (-r, -1.2), (-ridge_w / 2, -1.2)]
    body = extrude(Plane.YZ.offset(-ln / 2) * poly(*pts), ln, dir=PX)
    return body - Pos(0, 0, -t - 2) * Cylinder(S.SHANK["M5"] / 2 + 0.1, t + 4, align=MIN_Z_ONLY)


def insert_real(od, ln, bore):
    """A brass heat-set insert from Z = 0 to ln: two knurled bands and a plain band between them."""
    from build123d import Polygon as Pg
    n = 18
    pts = []
    for i in range(2 * n):
        a = math.pi * i / n
        rr = od / 2 if i % 2 == 0 else od / 2 - 0.35
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    star = Pg(*pts, align=None)
    b = ln * 0.4
    body = extrude(star, b) + Pos(0, 0, ln - b) * extrude(star, b)
    body += Cylinder(od / 2 - 0.45, ln, align=MIN_Z_ONLY)
    return body - Pos(0, 0, -1) * Cylinder(bore, ln + 2, align=MIN_Z_ONLY)


# ---------------------------------------------------------------- GT2 drive parts and V-wheels

def _gt2_disc(od, teeth, t, grow=0.0):
    """A GT2 toothed disc on the Z axis, from Z = 0 to t: the outside diameter od with one groove for
    each belt tooth (a round bottom and straight sides). grow > 0 makes the grooves larger."""
    r_out = od / 2
    rt = S.GT2_TOOTH_R + grow
    rc = r_out - S.GT2_TOOTH_H + S.GT2_TOOTH_R           # the centre of the round bottom of a groove
    disc = Cylinder(r_out, t, align=MIN_Z_ONLY)
    cut = None
    for k in range(teeth):
        a = 2 * math.pi * (k + 0.5) / teeth
        g = Pos(rc * math.cos(a), rc * math.sin(a), -1) * Cylinder(rt, t + 2, align=MIN_Z_ONLY)
        g += Rot(0, 0, math.degrees(a)) * box(rc, r_out + 1, -rt, rt, -1, t + 1)
        cut = g if cut is None else cut + g
    return disc - cut


def gt2_pulley(hub=True):
    """A GT2 20T pulley on the Z axis: the outer flange at Z = 0, the teeth, the inner flange, the hub
    with two M3 set screws at 90 degrees (one on the flat of the D shaft, at +X), and the 5 mm bore."""
    p = S.PULLEY
    ft, tw = p["flange_t"], p["teeth_w"]
    body = Cylinder(p["flange_d"] / 2, ft, align=MIN_Z_ONLY)
    body += Pos(0, 0, ft) * _gt2_disc(S.PULLEY_OD, S.PULLEY_TEETH, tw)
    body += Pos(0, 0, ft + tw) * Cylinder(p["flange_d"] / 2, ft, align=MIN_Z_ONLY)
    z_hub = 2 * ft + tw
    if hub:
        body += Pos(0, 0, z_hub) * _rev([(0, 0), (p["hub_d"] / 2, 0), (p["hub_d"] / 2, p["hub_l"] - 0.4),
                                         (p["hub_d"] / 2 - 0.4, p["hub_l"]), (0, p["hub_l"])])
        zs = z_hub + p["hub_l"] / 2
        for a in (0, 90):
            # The set screw hole and the set screw (cup point, hex socket), 0.8 mm under the hub surface.
            hole = Rot(0, 0, a) * Pos(0, 0, zs) * x_axis(Cylinder(1.5, p["hub_d"], align=MIN_Z_ONLY))
            body -= hole
            ss = Rot(0, 0, a) * Pos(0, 0, zs) * x_axis(Pos(0, 0, 2.5) * (Cylinder(1.45, p["hub_d"] / 2 - 2.5 - 0.8, align=MIN_Z_ONLY)
                                                                        - Pos(0, 0, p["hub_d"] / 2 - 2.5 - 1.8) * _hex_prism(1.5, 0, 1.1)))
            body += ss
    length = z_hub + (p["hub_l"] if hub else 0)
    return body - Pos(0, 0, -1) * Cylinder(p["bore"] / 2, length + 2, align=MIN_Z_ONLY)


def _bearing_face(z, out_r, in_r=2.5, s=1):
    """The face detail of a shielded bearing: a recessed shield ring between the races (cut)."""
    return Pos(0, 0, z - (0.25 if s > 0 else 0)) * (Cylinder(out_r - 0.8, 0.25, align=MIN_Z_ONLY)
                                                     - Cylinder(in_r + 1.1, 0.25, align=MIN_Z_ONLY))


def gt2_idler(toothed=True):
    """A GT2 idler for 6 mm belt on the Z axis, from Z = 0 to h: two flanges, a toothed (20T) or a
    smooth belt face, a 5 mm bore, and the shielded bearing faces."""
    t = S.TIDLER
    h, ft = t["h"], t["flange_t"]
    if toothed:
        mid = Pos(0, 0, ft) * _gt2_disc(S.PULLEY_OD, S.PULLEY_TEETH, h - 2 * ft)
        fd = t["flange_d"]
    else:
        mid = Pos(0, 0, ft) * Cylinder(S.SIDLER_R, h - 2 * ft, align=MIN_Z_ONLY)
        fd = 2 * S.SIDLER_FL
    body = Cylinder(fd / 2, ft, align=MIN_Z_ONLY) + mid + Pos(0, 0, h - ft) * Cylinder(fd / 2, ft, align=MIN_Z_ONLY)
    body -= _bearing_face(h, 5.0, s=1) + Pos(0, 0, 0.25) * _bearing_face(0.0, 5.0, s=-1)
    return body - Pos(0, 0, -1) * Cylinder(t["bore"] / 2, h + 2, align=MIN_Z_ONLY)


def gt2_belt_wrap(r_lo_deg, r_hi_deg, width):
    """The belt where it wraps a 20T pulley, on the Z axis (the pulley frame), from Z = 0 to width: the
    back and the land of the belt, and one tooth in each groove, between the two angles (degrees)."""
    land = S.PULLEY_OD / 2 + 0.05
    back = S.PULLEY_OD / 2 - S.GT2_TOOTH_H + 1.4
    ring = Cylinder(back, width, align=MIN_Z_ONLY) - Pos(0, 0, -1) * Cylinder(land, width + 2, align=MIN_Z_ONLY)
    rc = S.PULLEY_OD / 2 - S.GT2_TOOTH_H + S.GT2_TOOTH_R
    for k in range(S.PULLEY_TEETH):
        a = 360.0 * (k + 0.5) / S.PULLEY_TEETH
        if r_lo_deg - 1 <= a <= r_hi_deg + 1:
            ar = math.radians(a)
            ring += Pos(rc * math.cos(ar), rc * math.sin(ar), 0) * Cylinder(S.GT2_TOOTH_R - 0.05, width, align=MIN_Z_ONLY)
            ring += Rot(0, 0, a) * box(rc, land + 0.1, -(S.GT2_TOOTH_R - 0.05), S.GT2_TOOTH_R - 0.05, 0, width)
    return ring


def v_wheel_real():
    """The stock Creality (OpenBuilds solid) V-wheel on an axle along Z, centred on the origin, with
    its two 625 bearings: the POM body (flat faces, a short land, the 45 degree flanks, the flat tip of
    the slot-contact profile) and the bearing faces (inner race, shield, outer race)."""
    r_tip = S.WHEEL_D / 2
    h = S.WHEEL_T / 2
    r_land = 9.6                               # the faces go out to here, then the flanks begin
    y_land = r_tip + S.WHEEL_TIP - r_land       # the flank meets the land at this height
    rb = 8.0                                    # the bearing seat: 625 bearing, 16 mm outside
    pts = [(rb, -h), (r_land, -h), (r_land, -y_land), (r_tip, -S.WHEEL_TIP), (r_tip, S.WHEEL_TIP),
           (r_land, y_land), (r_land, h), (rb, h)]
    body = revolve(Plane.XZ * poly(*pts), Axis.Z)
    # Two 625 bearings (5 x 16 x 5) and the centre lip between them.
    brg = _rev([(S.WHEEL_BORE / 2, -h), (rb, -h), (rb, h), (S.WHEEL_BORE / 2, h)])
    brg -= Pos(0, 0, h - 0.25) * (Cylinder(7.2, 0.3, align=MIN_Z_ONLY) - Cylinder(3.6, 0.3, align=MIN_Z_ONLY))
    brg -= Pos(0, 0, -h - 0.05) * (Cylinder(7.2, 0.3, align=MIN_Z_ONLY) - Cylinder(3.6, 0.3, align=MIN_Z_ONLY))
    return body + brg


# ---------------------------------------------------------------- endstop boards

def es_local():
    """The Creality endstop board in its own frame (u, v, w): the body (board, switch, plug, pins),
    the lever, and the plug zone (the plug and the bend of its wires)."""
    e = S.ES
    pu, pv, pt = e["pcb"]
    body = box(0, pu, 0, pv, 0, pt)
    u0, u1, v0, v1, wt = e["switch"]
    body += box(u0, u1, v0, v1, pt, wt)
    _, pv0, pv1, ph = e["plug"]
    body += box(0.3, 6.0, pv0, pv1, pt, ph)                      # the plug header on the board
    body += box(5.7, 7.0, 6.6, 13.4, -e["pins"], 0.0)            # the plug pins under the board (photo, ESTIMATE)
    body += box(14.2, 15.8, 5.5, 16.0, -e["pins"], 0.0)          # the switch pins under the board (photo)
    for v in e["holes_v"]:
        body -= Pos(e["holes_u"], v, -5) * Cylinder(e["hole_d"] / 2, 10, align=MINZ)
    (a_u, a_v), (b_u, b_v), lw0, lw1 = e["lever"]
    ln = math.hypot(b_u - a_u, b_v - a_v)
    ang = math.degrees(math.atan2(b_v - a_v, b_u - a_u))
    lever = Pos(a_u, a_v, lw0) * Rot(0, 0, ang) * box(0, ln, -0.15, 0.15, 0, lw1 - lw0)
    zu0, zv0, zv1, zw = e["plug_zone"]
    plug = box(zu0, 0, zv0, zv1, pt, zw)
    return {"body": body, "lever": lever, "plug_zone": plug}


def es_loc(which, c=0.0):
    """The board location: "y_left", "y_right" (static, on the front bases) or "x" (on the front of the
    X endstop wall of the left carriage at gantry y = c, facing the front)."""
    zt = S.YF_TOP + S.ES_STANDOFF
    if which == "y_left":
        return Pos(S.ES_Y_ORIGIN[0], S.ES_Y_ORIGIN[1], zt) * Rot(0, 0, 90)
    if which == "y_right":
        return Pos(S.ES_Y_RIGHT_ORIGIN, S.ES_Y_ORIGIN[1], zt) * Rot(0, 0, 90)
    return Pos(S.ES_X_ORIGIN[0], c + S.ES_X_BACK_DY, S.ES_X_ORIGIN[1]) * Rot(90, 0, 0)


def es_point(which, uvw, c=0.0):
    from build123d import Vertex
    p = (es_loc(which, c) * Vertex(*uvw)).center()
    return (p.X, p.Y, p.Z)


def es_click(which, c=0.0):
    """The click point of the lever (frame)."""
    return es_point(which, S.ES["click"], c)


def es_parts(which, c=0.0):
    loc = es_loc(which, c)
    return {k: loc * v for k, v in es_local().items()}


def es_holes_y():
    """The two M3 holes of the left Y board (frame x, y). The right board holes are their mirror."""
    return [es_point("y_left", (S.ES["holes_u"], v, 0))[:2] for v in S.ES["holes_v"]]


def es_holes_x():
    """The two M3 holes of the X board (frame x, z), at gantry y = 0."""
    out = []
    for v in S.ES["holes_v"]:
        p = es_point("x", (S.ES["holes_u"], v, 0))
        out.append((p[0], p[2]))
    return out
