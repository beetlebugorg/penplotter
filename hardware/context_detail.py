"""Detailed models of the bought parts (context only, not printed).

The parts: the NEMA 17 steppers, the Creality endstop boards, the head board and the base board
with their connectors, the SG90/MG90S servo, and the CR-10 V3 control box.

Each public function returns a "kit": a dict {material: [solid, ...]} in frame coordinates (mm,
the origin at the front left outer corner of the frame on the table, X right, Y back, Z up).
kit_solid(kit) joins a kit into one Compound for the fit check or a one-colour STL.
The placements copy the stand-ins in parts.py. This module reads parts.py and shape.py. It does
not change them.

Sources (values without a source are marked ESTIMATE in the comments):
- NEMA 17: NEMA ICS 16 frame size 17 (42.3 mm square, 31.0 mm hole square, 22 mm pilot, 5 mm
  shaft). Creality 42-40 retail listings: 40 mm body, 5 mm D shaft, 20 to 24 mm long.
- Endstop: the stock Creality board, measured and read from photos: shape.ES (20 x 20 mm, 2 x M3
  holes 15.0 mm apart, 3.26 mm from the plug edge, the lever clicks 1.0 mm past the switch edge) and EB.
- JST XH (2.5 mm pitch) and PH (2.0 mm pitch) sockets: JST catalogue sizes.
- SG90: TowerPro data sheet (32.2 mm over the tabs, holes 27.8 mm apart, 2.5 mm tabs).
- Control box: the CTRL_BOX size and place in shape.py and model.py (ESTIMATE).
"""
import math

from build123d import (Align, Axis, Box, Circle, Compound, Cylinder, Location, Plane, Polygon, Pos, Rot,
                       Vector, extrude)

import parts as P
import shape as S

MINZ = (Align.CENTER, Align.CENTER, Align.MIN)
CTR = (Align.CENTER, Align.CENTER, Align.CENTER)

# The materials: colour, metalness, roughness. The sim reads them from stl/detail/manifest.json.
MATS = {
    "motor_cap": ("#1d1e21", 0.55, 0.42),     # black anodised end caps
    "motor_stack": ("#6f7378", 0.75, 0.38),   # the lamination stack
    "steel": ("#d4d6da", 1.0, 0.25),
    "label": ("#e9e9e4", 0.0, 0.7),
    "nylon": ("#efe9da", 0.0, 0.55),          # JST housings (natural nylon)
    "black_plastic": ("#17181a", 0.0, 0.5),
    "gold": ("#c9a23f", 1.0, 0.3),
    "pcb": ("#1f6b3a", 0.0, 0.6),
    "pcb_dark": ("#16181b", 0.0, 0.55),       # the endstop board (black solder mask, ESTIMATE)
    "smd": ("#2a2a2a", 0.2, 0.5),
    "smd_light": ("#b8a888", 0.1, 0.6),       # ceramic capacitors
    "plunger": ("#d0402a", 0.0, 0.45),        # the red plunger of the KW12 switch
    "switch": ("#1a1a1a", 0.0, 0.5),
    "servo": ("#2f5da8", 0.0, 0.5),
    "wire_brown": ("#5a3418", 0.0, 0.6),
    "wire_red": ("#b0221c", 0.0, 0.6),
    "wire_orange": ("#e07b1a", 0.0, 0.6),
    "box": ("#2b2d31", 0.45, 0.5),            # the control box sheet metal
    "box_vent": ("#0d0d0e", 0.0, 0.8),        # the dark inside behind the vents and the grille
    "rubber": ("#202124", 0.0, 0.9),
}

# ---------------------------------------------------------------- small helpers


def box(x0, x1, y0, y1, z0, z1):
    return P.box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1))


def zcyl(r, z0, z1, x=0.0, y=0.0, n=None):
    return Pos(x, y, min(z0, z1)) * Cylinder(r, abs(z1 - z0), align=MINZ)


def add(kit, mat, solid):
    kit.setdefault(mat, []).append(solid)
    return kit


def merge(*kits):
    out = {}
    for k in kits:
        for m, sl in k.items():
            out.setdefault(m, []).extend(sl)
    return out


def kit_solid(kit):
    """All solids of a kit in one Compound."""
    return Compound(children=[s for sl in kit.values() for s in sl])


def kit_move(kit, loc):
    return {m: [loc * s for s in sl] for m, sl in kit.items()}


def kit_mirror_x(kit):
    """The mirror image about the centre plane of the frame (as parts.mirror_x)."""
    return {m: [P.mirror_x(s) for s in sl] for m, sl in kit.items()}


class Frame:
    """A placement: origin o and the unit axes ex, ey, ez of the local frame in world coordinates.
    The axes can be left handed. Then the solid is mirrored in its local z first."""

    def __init__(self, o, ex, ey, ez=None):
        self.o, self.ex, self.ey = Vector(*o), Vector(*ex), Vector(*ey)
        rz = self.ex.cross(self.ey)
        self.ez = Vector(*ez) if ez is not None else rz
        self.flip = self.ez.dot(rz) < 0
        self.loc = Location(Plane(origin=self.o, x_dir=self.ex, z_dir=rz))

    def solid(self, s):
        if self.flip:
            s = s.mirror(Plane.XY)
        return self.loc * s

    def kit(self, kit):
        return {m: [self.solid(s) for s in sl] for m, sl in kit.items()}

    def pt(self, p):
        v = self.o + self.ex * p[0] + self.ey * p[1] + self.ez * p[2]
        return [round(v.X, 3), round(v.Y, 3), round(v.Z, 3)]

    def dir(self, d):
        v = self.ex * d[0] + self.ey * d[1] + self.ez * d[2]
        return [round(v.X, 4), round(v.Y, 4), round(v.Z, 4)]


def anchor(frame, p, d, moves, **kw):
    """A cable end: the point where the wires leave a plug, and the direction they leave in."""
    a = {"p": frame.pt(p), "d": frame.dir(d), "moves": moves}
    a.update(kw)
    return a


def mirror_anchor(a):
    b = dict(a)
    b["p"] = [round(S.FRAME_X - a["p"][0], 3), a["p"][1], a["p"][2]]
    b["d"] = [-a["d"][0], a["d"][1], a["d"][2]]
    return b


def chamfered_square(side, ch):
    """A square of the side length with 45 degree corner chamfers of the leg ch (centred, in XY)."""
    h = side / 2
    return Polygon((-h + ch, -h), (h - ch, -h), (h, -h + ch), (h, h - ch), (h - ch, h), (-h + ch, h),
                   (-h, h - ch), (-h, -h + ch), align=None)


def prism_z(face, z0, z1):
    return Pos(0, 0, z0) * extrude(face, z1 - z0)


# ---------------------------------------------------------------- JST connectors

XH_PITCH, PH_PITCH = 2.5, 2.0


def xh_len(n):
    """The length of an XH housing with n pins (JST: 2.5 (n - 1) + 4.9)."""
    return XH_PITCH * (n - 1) + 4.9


def xh_socket(n, mated=False, along="x"):
    """A top-entry JST XH socket (B?B-XH-A) on a board, the board top at z = 0, centred on the
    origin. The pin row runs along the local x (along="x") or y. Housing 5.75 wide, 7.0 high.
    With mated=True a plug (XHP) sits in it; the wires leave its top at z = 13.0 (ESTIMATE).
    Returns (kit, wire exit z)."""
    L, W, H = xh_len(n), 5.75, 7.0
    k = {}
    shell = box(-L / 2, L / 2, -W / 2, W / 2, 0, H) - box(-L / 2 + 0.8, L / 2 - 0.8, -W / 2 + 0.8, W / 2 - 1.3, 1.2, H + 1)
    shell -= box(-0.9, 0.9, W / 2 - 1.4, W / 2 + 1, 2.5, H + 1)    # the latch window
    add(k, "nylon", shell)
    x0 = -XH_PITCH * (n - 1) / 2
    for i in range(n):
        add(k, "gold", box(x0 + i * XH_PITCH - 0.32, x0 + i * XH_PITCH + 0.32, -0.57, 0.07, 1.2, 6.1))
    top = 0.0
    if mated:
        plug = box(-L / 2 + 0.85, L / 2 - 0.85, -W / 2 + 0.85, W / 2 - 1.35, 2.0, 13.0)
        plug -= box(-L / 2 + 0.85 - 1, L / 2 - 0.85 + 1, W / 2 - 3.0, W / 2 - 1.0, 9.0, 14.0)  # the step on the latch side
        add(k, "nylon", plug)
        add(k, "nylon", box(-0.8, 0.8, W / 2 - 1.35, W / 2 - 0.2, 4.0, 8.5))                # the latch tab
        top = 13.0
    if along == "y":
        k = kit_move(k, Rot(0, 0, 90))
    return k, top


def xh_side(n):
    """A side-entry JST XH socket (S?B-XH-A) on a board (board top at z = 0) with its plug: the mouth
    at x = 0 faces -x, the pin row along y, centred on y = 0. The body is 7.5 deep and 6.0 high
    (ESTIMATE from the JST drawing). The plug stands 9.5 mm out of the mouth; the wires leave it
    along -x. Returns (kit, wire exit x)."""
    L = xh_len(n)
    k = {}
    shell = box(0, 7.5, -L / 2, L / 2, 0, 6.0) - box(-1, 5.0, -L / 2 + 0.8, L / 2 - 0.8, 0.8, 5.2)
    add(k, "nylon", shell)
    y0 = -XH_PITCH * (n - 1) / 2
    for i in range(n):
        add(k, "gold", box(1.0, 7.0, y0 + i * XH_PITCH - 0.32, y0 + i * XH_PITCH + 0.32, 2.7, 3.34))
    plug = box(-9.5, 4.6, -L / 2 + 0.85, L / 2 - 0.85, 0.85, 5.15)
    plug -= box(-10, -6.5, -L / 2, L / 2, 4.2, 6)          # the step at the wire end
    add(k, "nylon", plug)
    add(k, "nylon", box(-4.0, 0.0, -0.8, 0.8, 5.15, 5.7))  # the latch
    return k, -9.5


def ph_socket_side(n):
    """A side-entry JST PH socket (S?B-PH-K) as it sits in a motor end cap: the mouth on the local
    +z face (z = 0), the body toward -z. Pin row along x. Size: 2.0 (n - 1) + 3.9 long, 4.5 high (y),
    6.0 deep (z) (JST catalogue values; the depth is an ESTIMATE)."""
    L, Hh, D = PH_PITCH * (n - 1) + 3.9, 4.5, 6.0
    k = {}
    shell = box(-L / 2, L / 2, -Hh / 2, Hh / 2, -D, 0) - box(-L / 2 + 0.6, L / 2 - 0.6, -Hh / 2 + 0.6, Hh / 2 - 0.9, -D + 1.0, 1)
    add(k, "nylon", shell)
    x0 = -PH_PITCH * (n - 1) / 2
    for i in range(n):
        add(k, "gold", box(x0 + i * PH_PITCH - 0.25, x0 + i * PH_PITCH + 0.25, -0.25, 0.25, -D + 1.0, -1.2))
    return k


def ph_plug(n, wires=4):
    """A PH housing (PHR-n) pushed into a PH socket with the mouth at z = 0: it reaches 4.5 mm
    into the socket and stands 5.5 mm out. The wires leave at z = 5.5. Returns (kit, z)."""
    L, Hh = PH_PITCH * (n - 1) + 3.0, 3.2
    k = {}
    add(k, "nylon", box(-L / 2, L / 2, -Hh / 2 - 0.2, Hh / 2 - 0.2, -4.5, 5.5))
    add(k, "nylon", box(-1.5, 1.5, Hh / 2 - 0.2, Hh / 2 + 0.5, -2.0, 4.0))     # the lock ramp
    return k, 5.5


# ---------------------------------------------------------------- NEMA 17 stepper

NEMA = dict(
    side=42.3,            # NEMA 17 (ICS 16)
    cap_ch=4.6,           # the chamfer leg of the end caps. ESTIMATE (photos)
    stack_side=42.0,      # the lamination stack is 0.15 mm inside the caps. ESTIMATE
    stack_ch=6.2,         # its corners are cut more. ESTIMATE
    L=40.0,               # the Creality 42-40 body length (retail listings)
    front=9.0,            # the front cap length. ESTIMATE
    back=10.0,            # the back cap length. ESTIMATE
    gap=0.4,              # the groove between a cap and the stack. ESTIMATE
    boss=(22.0, 2.0),     # the pilot boss: diameter, height (NEMA 17)
    holes=31.0,           # M3 holes on a 31 mm square (NEMA 17)
    hole_depth=4.5,       # MOTOR_THREAD in shape.py
    shaft=(5.0, 24.0),    # diameter, length from the boss face. ESTIMATE (listings: 20 to 24 mm)
    flat=(0.5, 15.0),     # the D flat: depth, length from the tip. ESTIMATE
)


def nema17_local(L=None):
    """A NEMA 17 (42-40, or 42-34 with L=34) in its own frame: the front face (without the boss) at z = 0, the body
    toward -z, the shaft along +z. The JST PH 6-pin socket is in the back cap, on the +y side face,
    with a PH plug in it. Returns (kit, plug anchor (p, d) in the local frame)."""
    n = NEMA
    L, f, b, g = L or n["L"], n["front"], n["back"], n["gap"]
    k = {}
    cap = chamfered_square(n["side"], n["cap_ch"])
    front = prism_z(cap, -f, 0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            front -= zcyl(1.25, -n["hole_depth"], 0.1, sx * n["holes"] / 2, sy * n["holes"] / 2)
    add(k, "motor_cap", front)
    stack = prism_z(chamfered_square(n["stack_side"], n["stack_ch"]), -(L - b), -f)
    # The groove at each joint: the stack ends are 0.4 mm smaller for the gap length.
    stack -= prism_z(chamfered_square(n["stack_side"] + 2, n["stack_ch"]) - chamfered_square(n["stack_side"] - 0.8, n["stack_ch"] + 0.4), -f - g, -f + 0.1)
    stack -= prism_z(chamfered_square(n["stack_side"] + 2, n["stack_ch"]) - chamfered_square(n["stack_side"] - 0.8, n["stack_ch"] + 0.4), -(L - b) - 0.1, -(L - b) + g)
    # The label recess on the -x side face of the stack (0.2 mm deep) and the label in it.
    lab = box(-n["stack_side"] / 2 - 1, -n["stack_side"] / 2 + 0.2, -15.0, 15.0, -(L - b) + 2.0, -f - 2.0)
    stack -= lab
    add(k, "motor_stack", stack)
    add(k, "label", box(-n["stack_side"] / 2 + 0.05, -n["stack_side"] / 2 + 0.2, -14.8, 14.8, -(L - b) + 2.2, -f - 2.2))
    back = prism_z(cap, -L, -(L - b))
    # The four long screws from the back: their heads sit in counterbores in the back face.
    for sx in (-1, 1):
        for sy in (-1, 1):
            back -= zcyl(2.9, -L - 0.1, -L + 2.0, sx * n["holes"] / 2, sy * n["holes"] / 2)
            add(k, "steel", zcyl(2.6, -L + 0.4, -L + 2.0, sx * n["holes"] / 2, sy * n["holes"] / 2))
    # The PH socket: in a pocket of the +y side face, its mouth flush with the face.
    zc = -L + b / 2 + 0.3
    back -= box(-7.4, 7.4, n["side"] / 2 - 6.4, n["side"] / 2 + 1, zc - 2.75, zc + 2.75)
    add(k, "motor_cap", back)
    sock = ph_socket_side(6)
    loc = Location(Plane(origin=(0, n["side"] / 2, zc), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    k = merge(k, kit_move(sock, loc))
    plug, ztop = ph_plug(6)
    k = merge(k, kit_move(plug, loc))
    # The pilot boss, the shaft with its D flat.
    add(k, "motor_cap", zcyl(n["boss"][0] / 2, 0, n["boss"][1]))
    d, sl = n["shaft"]
    shaft = zcyl(d / 2, n["boss"][1] - 0.5, n["boss"][1] + sl)
    shaft -= box(-d, d, d / 2 - n["flat"][0], d, n["boss"][1] + sl - n["flat"][1], n["boss"][1] + sl + 1)
    add(k, "steel", shaft)
    a_p = (0, n["side"] / 2 + ztop, zc)
    return k, (a_p, (0, 1, 0))


def x_motor(c):
    """The X motor at gantry y = c: behind the left beam end, the face on the back of the motor wall of
    the tower (y = c + XM_FACE_DY), the shaft to -Y, the axis on the pulley (x = XM_X, z = BZ;
    parts.x_motor). The PH socket faces up (+Z). A 42-34 (XMOTOR_L). Returns (kit, anchor)."""
    k, (ap, ad) = nema17_local(S.XMOTOR_L)
    fr = Frame((S.XM_X, c + S.XM_FACE_DY, S.BZ), (1, 0, 0), (0, 0, 1))
    return fr.kit(k), anchor(fr, ap, ad, "gantry", dy0=c)


def y_stepper_left(c):
    """The left Y motor (static now, fixed motors): behind the back bar, the face on the bracket plate
    (x = YM_FACE_X), the shaft to +X, the axis on the pulley (parts.y_stepper). The PH socket faces up
    (+Z). c is not used. Returns (kit, anchor)."""
    k, (ap, ad) = nema17_local()
    fr = Frame((S.YM_FACE_X, S.YM_Y, S.YB_AX), (0, 1, 0), (0, 0, 1))
    return fr.kit(k), anchor(fr, ap, ad, "static")


def y_stepper_right(c):
    k, a = y_stepper_left(c)
    return kit_mirror_x(k), mirror_anchor(a)


# ---------------------------------------------------------------- Creality endstop board
# The stock CR-10 V3 endstop board (3 in the plotter: X, Y1, Y2, all the same, none mirrored).
# The sizes come from shape.ES (measured on one board) and the
# placements from parts.es_loc, so this model and the printed mounts stay the same.
#
# The board frame (shape.ES): u from the plug edge (u = 0) to the switch edge, v along the edges,
# w up from the back of the board (the board is w 0 to 1.6; the parts are on top). The trigger pushes
# the lever along -u, in the plane of the board, at ES["click"].
#
# Values that shape.ES does not hold (from the photo, P, or estimates, E):
EB = dict(
    sw_holes=6.5,          # P: the two switch screws, 6.5 mm apart
    plunger_v=10.8,        # P: the red plunger on the outer face of the switch
    xh_out=5.5,            # P: the plug stands 5.5 mm past the plug edge
    lever_t=0.4,           # E: the lever strip thickness
)


def endstop_board_local(press=0.0):
    """The endstop board in the board frame of shape.ES. Returns (kit, info): info has the cable exit,
    the click point and its push direction, the holes, the plug zone and the sim indicator point."""
    e, x = S.ES, EB
    pu, pv, pt = e["pcb"]
    k = {}
    pcb = box(0, pu, 0, pv, 0, pt)
    for v in e["holes_v"]:
        pcb -= zcyl(e["hole_d"] / 2, -1, pt + 1, e["holes_u"], v)
    add(k, "pcb_dark", pcb)
    # The empty SMD pads (C104, 10K, LED, 1K): tinned pads, 0.05 mm high.
    for pu_, pv_ in ((6.8, 17.4), (9.4, 17.4), (6.8, 2.6), (9.4, 2.6)):
        for dv in (-0.8, 0.8):
            add(k, "steel", box(pu_ - 0.55, pu_ + 0.55, pv_ + dv - 0.45, pv_ + dv + 0.45, pt, pt + 0.05))
    # The KW12 switch: the body, the screw step, two screws, three terminals, the plunger.
    u0, u1, v0, v1, wt = e["switch"]
    body = box(u0, u1, v0, v1, pt, wt) - box(u0 - 1, u0 + 2.4, v0 + 1.2, v1 - 1.2, wt - 1.6, wt + 1)
    add(k, "switch", body)
    vc = (v0 + v1) / 2
    for hv in (vc - x["sw_holes"] / 2, vc + x["sw_holes"] / 2):
        add(k, "steel", zcyl(1.0, pt, wt - 1.0, u0 + 1.2, hv))
        add(k, "steel", zcyl(1.9, wt - 1.6, wt - 0.4, u0 + 1.2, hv))
    for tv in (v0 + 1.6, vc, v1 - 1.6):
        add(k, "steel", box(u0 - 2.2, u0 + 0.2, tv - 0.4, tv + 0.4, pt + 1.0, pt + 1.6))
        add(k, "steel", zcyl(0.9, pt, pt + 0.6, u0 - 2.4, tv))
    wm = (pt + wt) / 2
    add(k, "plunger", box(u1, u1 + 0.6, x["plunger_v"] - 0.7, x["plunger_v"] + 0.7, wm - 1.3, wm + 1.3))
    # The flat lever (shape.ES["lever"]): a strip from the pivot to the tip, with a pivot clip.
    (a_u, a_v), (b_u, b_v), lw0, lw1 = e["lever"]
    ln = math.hypot(b_u - a_u, b_v - a_v)
    # Draw the lever at the home pose: its outer face is at u = click - press - 0.2 (press: how far the
    # trigger is past the click at machine home). shape.ES["lever"] is the free position.
    cu = e["click"][0] - press - 0.2 - x["lever_t"]
    sgn = 1 if b_v >= a_v else -1
    ang = math.degrees(sgn * math.acos(max(-1.0, min(1.0, (cu - a_u) / ln))))
    add(k, "steel", Pos(a_u, a_v, lw0) * Rot(0, 0, ang) * box(0, ln, 0, x["lever_t"], 0, lw1 - lw0))
    add(k, "steel", box(a_u - 1.2, a_u + 0.5, a_v - 1.4, a_v + 0.2, lw0 - 0.3, lw1 + 0.3))
    # The JST XH 3-pin side-entry socket at the plug edge, and the plug in it (it enters along +u).
    _, pv0, pv1, ph = e["plug"]
    n, Lh = 3, xh_len(3)
    vc2 = (pv0 + pv1) / 2
    sock = box(-1.0, 6.0, vc2 - Lh / 2, vc2 + Lh / 2, pt, ph) - box(-2, 4.0, vc2 - Lh / 2 + 0.8, vc2 + Lh / 2 - 0.8, pt + 0.8, ph - 0.8)
    add(k, "nylon", sock)
    for i in range(n):
        pv_ = vc2 - XH_PITCH + i * XH_PITCH
        add(k, "gold", box(0.0, 5.0, pv_ - 0.32, pv_ + 0.32, pt + 2.7, pt + 3.34))
    plug = box(-x["xh_out"], 3.8, vc2 - Lh / 2 + 0.85, vc2 + Lh / 2 - 0.85, pt + 0.85, ph - 0.85)
    plug -= box(-x["xh_out"] - 1, -x["xh_out"] + 2.5, vc2 - Lh / 2, vc2 + Lh / 2, ph - 2.0, ph + 1)
    add(k, "nylon", plug)
    add(k, "nylon", box(-3.5, -1.0, vc2 - 0.8, vc2 + 0.8, ph - 0.85, ph - 0.3))
    info = {
        "holes": [(e["holes_u"], v, 0.0) for v in e["holes_v"]],
        "actuate": tuple(e["click"]), "actuate_dir": (-1, 0, 0),
        "wire_exit": (-x["xh_out"], vc2, pt + 3.0), "wire_dir": (-1, 0, 0),
        "plug_zone": tuple(e["plug_zone"]),
        "indicator": (u1 + 0.3, x["plunger_v"], wm),
    }
    return k, info


def _pt(loc, p):
    v = (loc * Pos(*p)).position
    return [round(v.X, 3), round(v.Y, 3), round(v.Z, 3)]


def _dir(loc, d):
    a, b = (loc * Pos(*d)).position, (loc * Pos(0, 0, 0)).position
    v = a - b
    return [round(v.X, 4), round(v.Y, 4), round(v.Z, 4)]


def trigger_press(which, c, xp):
    """How far the trigger face at machine home is past the click point (mm, along -u)."""
    click = P.es_click(which, c)
    if which == "x":
        t = P.plate_offset(xp, c) * P.x_carriage_plate()
        sl = t & box(click[0] - 6, click[0] + 6, click[1] - 1.5, click[1] + 1.5, click[2] - 1.5, click[2] + 1.5)
        return max(0.0, click[0] - sl.bounding_box().min.X) if sl is not None and sl.volume > 0 else 0.0
    car = P.y_carriage(c, "motor")
    if which == "y_right":
        car = P.mirror_x(P.y_carriage(c, "idler"))
    sl = car & box(click[0] - 1.25, click[0] + 1.25, click[1] - 6, click[1] + 6, click[2] - 1.5, click[2] + 1.5)
    return max(0.0, click[1] - sl.bounding_box().min.Y) if sl is not None and sl.volume > 0 else 0.0


def endstop(which, c=0.0, press=0.0):
    """One endstop board at parts.es_loc(which, c): which is "x" (gantry y = c), "y_left" or "y_right".
    Returns (kit, cable anchor, sim indicator, named frame values)."""
    loc = P.es_loc(which, c)
    k, info = endstop_board_local(press)
    moves = "gantry" if which == "x" else "static"
    extra = {"dy0": c} if which == "x" else {}
    a = {"p": _pt(loc, info["wire_exit"]), "d": _dir(loc, info["wire_dir"]), "moves": moves, **extra}
    ind = {"p": _pt(loc, info["indicator"]), "moves": moves, **extra}
    named = {"holes": [_pt(loc, h) for h in info["holes"]], "actuate": _pt(loc, info["actuate"]), "press_at_home": round(press, 2),
             "actuate_dir": _dir(loc, info["actuate_dir"]), "normal": _dir(loc, (0, 0, 1))}
    return kit_move(k, loc), a, ind, named


def x_endstop(c, xp=None):
    return endstop("x", c, trigger_press("x", c, xp) if xp is not None else 0.0)


def y_endstop_left(c_home=None):
    return endstop("y_left", 0.0, trigger_press("y_left", c_home, None) if c_home is not None else 0.0)


def y_endstop_right(c_home=None):
    return endstop("y_right", 0.0, trigger_press("y_right", c_home, None) if c_home is not None else 0.0)


# ---------------------------------------------------------------- the head board and the base board

# The pin count of each socket, from docs/wiring.md and the Creality harness (ESTIMATE where noted).
XH_PINS = {"BL_T": 5, "TH": 2, "HEAT": 2, "E": 4, "K_FAN": 2, "X": 4, "X-": 3,   # head board
           "Z-": 3, "Z1": 4, "Z2": 4, "Y": 4, "Y-": 3}                          # base board


def board_local(kind):
    """The head board or the base board with its connectors and its two nylon standoffs, in the pose
    frame of parts.brk (the same board outline, holes and connector boxes; no value in shape.py changes).
    Returns (kit, anchors in the pose frame: {name: (p, d)})."""
    d = P.brk(kind)
    xb0, zp, zt, V, U = d["xb0"], d["zp"], d["zt"], d["V"], d["U"]
    k = {}
    pcb = box(xb0, xb0 + V, -U / 2, U / 2, zp, zt)
    for x, y in d["holes"]:
        pcb -= zcyl(1.6, zp - 1, zt + 1, x, y)
        add(k, "nylon", zcyl(S.BRD_STANDOFF_D / 2, 0.0, zp, x, y) - zcyl(1.6, -1.0, zp + 1.0, x, y))
    add(k, "pcb", pcb)
    anchors = {}
    # The big harness connector at the +x edge: the right-angle header on the board and the plug in it.
    y0, y1 = P._yu(d, *d["hdr"])
    xh0 = xb0 + V - d["pin"]
    xe = xb0 + V + d["pout"]
    hdr = box(xh0, xh0 + 5.0, y0, y1, zt, zt + S.MF_PLUG_H + 0.4)
    add(k, "black_plastic", hdr)
    plug = box(xh0 + 5.0, xe, y0 + 0.4, y1 - 0.4, zt + 0.3, zt + S.MF_PLUG_H)
    # Ribs on the plug top, and the latch arm over the header.
    for i in range(int((y1 - y0 - 2) // 3)):
        yy = y0 + 1.6 + i * 3.0
        plug -= box(xe - 6.0, xe + 1, yy, yy + 1.2, zt + S.MF_PLUG_H - 0.6, zt + S.MF_PLUG_H + 1)
    add(k, "black_plastic", plug)
    ym = (y0 + y1) / 2
    add(k, "black_plastic", box(xh0 + 1.0, xh0 + 9.0, ym - 2.0, ym + 2.0, zt + S.MF_PLUG_H, zt + S.MF_PLUG_H + 1.6))
    anchors["harness"] = ((xe, ym, zt + S.MF_PLUG_H / 2), (1, 0, 0))
    # The XH sockets: a real housing for the pin count, centred on the box of the stand-in.
    for name, u0, u1, v0, v1 in d["xh"]:
        n = XH_PINS.get(name, 2)
        a, b = P._yu(d, u0, u1)
        cx, cy = xb0 + (v0 + v1) / 2, (a + b) / 2
        along = "y" if (u1 - u0) >= (v1 - v0) else "x"
        used = name in d["used"]
        sock, ztop = xh_socket(n, mated=used, along=along)
        k = merge(k, kit_move(sock, Pos(cx, cy, zt)))
        if used:
            anchors[name] = ((cx, cy, zt + ztop), (0, 0, 1))
    # Small parts (boxes): resistors, capacitors, a diode, ESTIMATE positions in the free areas.
    smd = [(xb0 + 3.0, -U / 2 + 3.0, 2.0, 1.25, 0.5), (xb0 + 3.0, -U / 2 + 6.0, 2.0, 1.25, 0.5),
           (xb0 + 12.0, U / 2 - 3.0, 3.5, 1.6, 1.1), (xb0 + 30.0 if V > 32 else xb0 + 22.0, U / 2 - 4.0, 2.0, 1.25, 0.6)]
    for i, (x, y, l, w, h) in enumerate(smd):
        add(k, "smd" if i % 2 == 0 else "smd_light", box(x - l / 2, x + l / 2, y - w / 2, y + w / 2, zt, zt + h))
    return k, anchors


def board(kind, c=None):
    """The board kit in frame coordinates (head: on the gantry at y = c; base: static) and its
    cable anchors (frame coordinates)."""
    k, an = board_local(kind)
    loc = P.brk_tf(kind, c)
    out = kit_move(k, loc)
    moves = "gantry" if kind == "head" else "static"
    anchors = {}
    for name, (p, dv) in an.items():
        pw = (loc * Pos(*p)).position
        dw = (loc * Pos(*dv)).position - (loc * Pos(0, 0, 0)).position
        a = {"p": [round(pw.X, 3), round(pw.Y, 3), round(pw.Z, 3)], "d": [round(dw.X, 4), round(dw.Y, 4), round(dw.Z, 4)], "moves": moves}
        if c is not None:
            a["dy0"] = c
        anchors[f"{kind}_{name}"] = a
    return out, anchors


# ---------------------------------------------------------------- the SG90 / MG90S servo

def servo_local():
    """The servo in the plate frame of the pen carriage (the same place as parts.servo_body).
    Case 22.8 x 12.2 mm, 16.0 mm under the tabs, the tabs 2.5 mm thick and 32.2 mm long with two
    2.0 mm holes 27.8 mm apart, the top case 4.3 mm, the output boss and a 21-tooth spline up to
    SPLINE_TOP. The 3-wire lead leaves the end face over the case bottom. Returns (kit, anchor)."""
    k = {}
    w = 12.2                                   # SG90 data sheet: 12.2 (the pocket uses 12.4)
    x0, x1 = S.SHAFT_X - w / 2, S.SHAFT_X + w / 2
    yb, yt = -S.BASE_T, S.SERVO_FACE           # the case bottom and the tab underside (y)
    yt2 = yt - S.SERVO_TAB_T
    y_case = yt2 - S.SERVO_TOP
    body = box(x0, x1, yb, yt, S.BODY_Z0, S.BODY_Z1)
    body = body.fillet(0.6, body.edges().filter_by(Axis.Y))
    add(k, "servo", body)
    tl = S.SERVO_TAB_L
    tabs = box(x0, x1, yt, yt2, S.BODY_ZC - tl / 2, S.BODY_ZC + tl / 2)
    for s in (-1, 1):
        zc = S.BODY_ZC + s * S.SERVO_TAB_HOLES / 2
        tabs -= Pos(S.SHAFT_X, yt + 1, zc) * Rot(90, 0, 0) * Cylinder(1.0, S.SERVO_TAB_T + 2, align=MINZ)
        tabs -= box(S.SHAFT_X - 0.5, S.SHAFT_X + 0.5, yt + 1, yt2 - 1, zc + s * 0.5, S.BODY_ZC + s * (tl / 2 + 1))
    add(k, "servo", tabs)
    # The top case: a 3 mm block and the round gear tower over the shaft (11.8 mm) with the small
    # boss of the second gear (6 mm) beside it.
    yt3 = yt2 - (S.SERVO_TOP - 1.3)
    add(k, "servo", box(x0, x1, yt2, yt3, S.BODY_Z0, S.BODY_Z1))
    tower = Pos(S.SHAFT_X, yt3, S.SHAFT_Z) * Rot(90, 0, 0) * Cylinder(5.9, 1.3, align=MINZ)
    tower += Pos(S.SHAFT_X, yt3, S.SHAFT_Z + 6.2) * Rot(90, 0, 0) * Cylinder(3.0, 1.3, align=MINZ)
    add(k, "servo", tower & box(x0, x1, yt3 + 0.1, y_case - 0.1, S.BODY_Z0, S.BODY_Z1))
    # The output: a boss (4.6 mm, 0.8 mm high), the 21-tooth spline (4.8 mm), the horn screw head.
    boss_h = 0.8
    add(k, "black_plastic", Pos(S.SHAFT_X, y_case, S.SHAFT_Z) * Rot(90, 0, 0) * Cylinder(2.3, boss_h, align=MINZ))
    n, ro, ri = 21, 2.4, 2.15
    pts = []
    for i in range(2 * n):
        r = ro if i % 2 == 0 else ri
        a = math.pi * i / n
        pts.append((r * math.cos(a), r * math.sin(a)))
    sh = S.SERVO_SPLINE_H - boss_h
    spline = extrude(Polygon(*pts, align=None), sh)
    spline -= Cylinder(0.9, sh + 1, align=MINZ)
    add(k, "black_plastic", Pos(S.SHAFT_X, y_case - boss_h, S.SHAFT_Z) * Rot(90, 0, 0) * spline)
    # The lead exit: a strain relief on the end face (z = BODY_Z1), near the case bottom, and the
    # three wires (brown GND, red 5 V, orange signal) 6 mm out of it.
    ye = yb - 3.4                              # 3.4 mm in from the case bottom: the pocket is open there
    add(k, "servo", box(S.SHAFT_X - 2.0, S.SHAFT_X + 2.0, yb - 2.4, yb - 4.4, S.BODY_Z1, S.BODY_Z1 + 1.5))
    for i, m in enumerate(("wire_brown", "wire_red", "wire_orange")):
        xw = S.SHAFT_X + (i - 1) * 1.1
        add(k, m, Pos(xw, ye, S.BODY_Z1 + 1.5) * Cylinder(0.52, 6.0, align=MINZ))
    a = ((S.SHAFT_X, ye, S.BODY_Z1 + 7.5), (0, 0, 1))
    return k, a


def servo(t):
    """The servo kit on the pen carriage (t: parts.plate_offset) and the lead anchor."""
    k, (p, dv) = servo_local()
    pw = (t * Pos(*p)).position
    return kit_move(k, t), {"p": [round(pw.X, 3), round(pw.Y, 3), round(pw.Z, 3)], "d": list(dv), "moves": "carriage",
                            "dx0": round(t.position.X, 3), "dy0": round(t.position.Y + S.PLATE_FRONT, 3)}


# ---------------------------------------------------------------- the CR-10 V3 control box

CTRL_X1 = -70.0                  # model.CTRL_X1: the right side of the box (x)
CTRL_Y0 = 70.0                   # the front of the box (y), as model.ctrl_box
CTRL_FEET = 3.0                  # rubber feet under the box. ESTIMATE
LCD_C = (-270.0, 44.0)           # the LCD window centre on the front (x, z), as the sim
KNOB_C = (-185.0, 44.0)          # the knob centre (x, z), as the sim


def ctrl_box():
    """The CR-10 V3 control box: a steel case with rounded vertical edges on 4 rubber feet, the LCD
    window with its bezel and the knob on the front, the SD slot and the USB socket on the left side,
    vent slots on the right side (toward the frame), the fan grille on the top, and on the back the
    IEC inlet with the power switch, the voltage switch and two cable glands.
    Size and place: shape.CTRL_BOX and model.CTRL_X1 (ESTIMATE). Returns (kit, anchors)."""
    W, D, H = S.CTRL_BOX
    x0, x1, y0, y1 = CTRL_X1 - W, CTRL_X1, CTRL_Y0, CTRL_Y0 + D
    z0, z1 = CTRL_FEET, H
    k = {}
    shell = box(x0, x1, y0, y1, z0, z1)
    shell = shell.fillet(6.0, shell.edges().filter_by(Axis.Z))
    shell = shell.fillet(1.5, shell.edges().group_by(Axis.Z)[-1])
    # The LCD window: a 1.5 mm recess for the bezel.
    lx, lz = LCD_C
    shell -= box(lx - 46, lx + 46, y0 - 1, y0 + 1.5, lz - 31, lz + 31)
    # The knob boss hole, the vent slots on the right side, the fan grille on the top.
    for i in range(12):
        z = 18 + i * 5.0
        if z + 2 > H - 10:
            break
        shell -= box(x1 - 2, x1 + 1, y0 + 40, y1 - 40, z, z + 2.2)
    gx, gy, gr = x0 + 0.62 * W, y0 + 0.55 * D, 30.0
    for r in (6.0, 12.0, 18.0, 24.0):
        ring = zcyl(r + 2.0, z1 - 2, z1 + 1, gx, gy) - zcyl(r, z1 - 3, z1 + 2, gx, gy)
        for a in (0, 90):
            ring -= Pos(gx, gy, z1) * Rot(0, 0, a) * Box(2 * r + 6, 2.5, 8)
        shell -= ring
    add(k, "box", shell)
    # The dark inside behind the vents and the grille.
    add(k, "box_vent", box(x1 - 3.0, x1 - 2.0, y0 + 38, y1 - 38, 16, H - 10))
    add(k, "box_vent", zcyl(gr - 1, z1 - 3.0, z1 - 2.0, gx, gy))
    # The fan behind the grille (a hub and 7 blades as flat boxes).
    add(k, "black_plastic", zcyl(8.0, z1 - 9.0, z1 - 3.2, gx, gy))
    for i in range(7):
        add(k, "black_plastic", Pos(gx, gy, z1 - 6.0) * Rot(0, 0, i * 360 / 7) * Rot(25, 0, 0) * box(8, 27, -4.5, 4.5, -0.5, 0.5))
    # The bezel and the LCD glass (the sim puts the live LCD texture on the glass).
    bez = box(lx - 45.5, lx + 45.5, y0 + 1.5, y0 + 0.2, lz - 30.5, lz + 30.5) - box(lx - 37, lx + 37, y0 - 1, y0 + 2, lz - 21, lz + 21)
    add(k, "black_plastic", bez)
    add(k, "box_vent", box(lx - 37, lx + 37, y0 + 1.5, y0 + 1.0, lz - 21, lz + 21))
    # The knob: a knurled cylinder (24 ribs) with a cap, on a short shaft.
    kx, kz = KNOB_C
    knob = Cylinder(9.0, 13.0, align=MINZ)
    for i in range(24):
        knob -= Pos(9.0 * math.cos(i * math.pi / 12), 9.0 * math.sin(i * math.pi / 12), 1.0) * Cylinder(0.6, 13, align=MINZ)
    knob += Pos(0, 0, 13.0) * Cylinder(8.0, 1.0, align=MINZ)
    add(k, "black_plastic", Pos(kx, y0 + 0.5, kz) * Rot(90, 0, 0) * knob)
    add(k, "steel", Pos(kx, y0 + 0.5, kz) * Rot(90, 0, 0) * Cylinder(3.0, 1.0, align=MINZ))
    # The left side: the SD slot and the USB socket (positions ESTIMATE).
    add(k, "box_vent", box(x0 - 0.3, x0 + 0.5, y0 + 25, y0 + 50, 20, 22.5))
    add(k, "steel", box(x0 - 0.4, x0 + 0.5, y0 + 60, y0 + 68, 19.5, 23.5))
    add(k, "box_vent", box(x0 - 0.5, x0 + 0.6, y0 + 61, y0 + 67, 20.5, 22.5))
    # The back: the IEC C14 inlet with the rocker switch (one module), the red voltage switch, and
    # two cable glands for the harness cables.
    ix = x0 + 45
    add(k, "black_plastic", box(ix - 24, ix + 24, y1, y1 + 2.0, 18, 46))
    add(k, "box_vent", box(ix - 20, ix - 4, y1 + 1.5, y1 + 2.2, 22, 33))
    for px in (-15.0, -9.0):
        add(k, "steel", box(ix + px - 0.9, ix + px + 0.9, y1 + 1.0, y1 + 2.1, 26.5, 30.5))
    add(k, "steel", box(ix - 12.9, ix - 11.1, y1 + 1.0, y1 + 2.1, 24.0, 26.0))
    add(k, "wire_red", box(ix + 4, ix + 20, y1 + 1.5, y1 + 4.0, 24, 40))           # the rocker switch
    add(k, "black_plastic", box(ix + 6, ix + 18, y1 + 3.5, y1 + 5.0, 26, 38))
    add(k, "wire_red", box(ix + 30, ix + 42, y1, y1 + 2.5, 30, 36))                # the voltage switch
    anchors = {}
    for i, gx2 in enumerate((x1 - 50.0, x1 - 30.0)):
        add(k, "black_plastic", Pos(gx2, y1, 40.0) * Rot(-90, 0, 0) * (Cylinder(7.0, 3.0, align=MINZ) + Pos(0, 0, 3) * Cylinder(5.5, 9.0, align=MINZ)))
        anchors[f"ctrl_gland{i}"] = {"p": [gx2, y1 + 12.0, 40.0], "d": [0, 1, 0], "moves": "ctrl"}
    anchors["ctrl_usb"] = {"p": [x0 - 1.0, y0 + 64.0, 21.5], "d": [-1, 0, 0], "moves": "ctrl"}
    anchors["ctrl_power"] = {"p": [ix - 12.0, y1 + 2.0, 28.0], "d": [0, 1, 0], "moves": "ctrl"}
    # Rubber feet.
    for fx in (x0 + 20, x1 - 20):
        for fy in (y0 + 20, y1 - 20):
            add(k, "rubber", zcyl(7.0, 0, z0 + 0.5, fx, fy))
    return k, anchors


def ctrl_lcd_glass():
    """The LCD glass: centre and size, for the live LCD texture of the sim (frame mm)."""
    return {"c": [LCD_C[0], CTRL_Y0 + 0.95, LCD_C[1]], "size": [72.0, 40.0]}


# ---------------------------------------------------------------- everything at machine home


def build_all(c0, xp0):
    """All kits and anchors at machine home (gantry y = c0, X plate at x = xp0, pen down).
    Returns {group: {name: kit}}, anchors, leds."""
    t = P.plate_offset(xp0, c0)
    xm, a_xm = x_motor(c0)
    yl, a_yl = y_stepper_left(c0)
    yr, a_yr = y_stepper_right(c0)
    xe, a_xe, l_xe, n_xe = x_endstop(c0, xp0)
    e1, a_e1, l_e1, n_e1 = y_endstop_left(c0)
    e2, a_e2, l_e2, n_e2 = y_endstop_right(c0)
    hb, a_hb = board("head", c0)
    bb, a_bb = board("base")
    sv, a_sv = servo(t)
    cb, a_cb = ctrl_box()
    groups = {
        "gantry": {"x_motor": xm, "x_endstop": xe, "head_board": hb},
        "static": {"y_endstops": merge(e1, e2), "base_board": bb, "y_stepper_left": yl, "y_stepper_right": yr},
        "carriage": {"servo": sv},
        "ctrl": {"ctrl_box": cb},
    }
    anchors = {"x_motor": a_xm, "y1_motor": a_yl, "y2_motor": a_yr, "x_endstop": a_xe, "y1_endstop": a_e1,
               "y2_endstop": a_e2, "servo": a_sv}
    anchors.update(a_hb)
    anchors.update(a_bb)
    anchors.update(a_cb)
    leds = {"x": l_xe, "y1": l_e1, "y2": l_e2}
    endstops = {"x": n_xe, "y1": n_e1, "y2": n_e2}
    return groups, anchors, leds, endstops
