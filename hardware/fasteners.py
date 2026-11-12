"""The fasteners of the main build (the stock controller build), as context geometry in frame
coordinates. model.py uses them in the fit check, checks each screw length, and exports them for
the simulator.

Each fastener is a Fastener: its BOM item, the group that moves it (static, gantry, carriage or
pen), the printed part that it holds, its solid, and the names of the context solids that it may
touch on purpose (a T-nut in the slot of a bar, a screw in the thread of a motor).
Each screw also has a Joint for the length check.

The heat-set inserts are items of kind "insert". The other M2 and M3 screws in plastic cut their
own thread in a pilot hole."""

import math
from dataclasses import dataclass, field

from build123d import Box, Cylinder, Location, Plane, Pos, Rot

import parts as P
import shape as S

MINZ = P.MINZ
JAW_ITEM = "belt jaw (printed)"


@dataclass
class Fastener:
    name: str          # unique name, for the clash report
    item: str          # the BOM item, for example "M5 x 12 socket head"
    size: str          # "M5", "M3", "M2", "M6"
    kind: str          # "screw", "nut", "nyloc", "tnut", "washer", "spacer", "eccentric"
    group: str         # what moves it: "static", "gantry", "carriage", "pen"
    part: str          # the printed part that it holds (for the count table)
    solid: object
    allow: tuple = ()  # context names (substrings) that it may touch
    stock: bool = False
    # The geometry for the audit: a screw has length, head, p (the bearing point) and d (the axis);
    # an insert has len, od, hole, depth, p and d.
    meta: dict = field(default_factory=dict)


@dataclass
class Joint:
    name: str
    item: str
    kind: str          # "tnut", "selftap", "tapped", "nut"
    length: float
    grip: float        # the thickness under the head (to the nut, for a nut joint)
    limit: float = 0.0 # selftap: the pilot depth; tapped: the thread depth; nut: the nut height
    size: str = "M5"
    count: int = 1
    result: dict = field(default_factory=dict)


def _along(solid, p, d, x=None):
    """A solid built on the Z axis, moved so that its +Z points along d from the point p."""
    pl = Plane(origin=p, x_dir=x, z_dir=d) if x else Plane(origin=p, z_dir=d)
    return Location(pl) * solid


def screw_solid(size, length, head="socket"):
    """A screw on the Z axis: the head under Z = 0, the shank from 0 to length. Real shapes: ISO 4762
    socket head with its hex socket, ISO 7380 button head, pan head with a cross recess."""
    h = {"socket": P.socket_head, "button": P.button_head, "pan": P.pan_head, "csk": P.csk_head}[head](size)
    return h + P.shank(size, length)


def nut_solid(size, nyloc=False):
    """ISO 4032 hex nut, or ISO 7040 nyloc nut with its collar and nylon ring."""
    if nyloc:
        steel, nylon = P.nyloc_real(S.NYLOC[0], S.NYLOC[1], S.SHANK[size] / 2 + 0.1)
        return steel + nylon
    af, t = S.M3_NUT
    return P.hex_nut_real(af, t, S.SHANK[size] / 2 + 0.1)


def ring(od, t, bore=2.65):
    return P.washer_real(od, t, bore)


def tnut_solid():
    """An M5 drop-in (roll-in) T-nut behind the lip: local X along the slot, Z along the screw. The
    ridge sits in the slot opening, the shoulders bear on the back of the lips."""
    return Pos(0, 0, S.SLOT_LIP) * Rot(180, 0, 0) * Pos(0, 0, 1.2) * P.tnut_real()


INSERT_ITEM = "M5 heat-set insert, 9.5 mm (long)"
INSERT_M3_ITEM = "M3 heat-set insert, 5.7 mm"
SMALL_WASHER_ITEM = "M5 washer, 7.5 mm across (small)"


def name_of(head, size, length):
    return f"{size} x {length:.0f} " + {"socket": "socket head", "button": "button head (ISO 7380)",
                                         "pan": "self-tapping", "csk": "countersunk (ISO 10642)"}[head]


class Builder:
    def __init__(self):
        self.items = []
        self.joints = {}

    def screw(self, name, size, length, head, p, d, group, part, allow=(), stock=False, x=None):
        item = name_of(head, size, length) + (" (stock)" if stock else "")
        self.items.append(Fastener(name, item, size, "screw", group, part, _along(screw_solid(size, length, head), p, d, x),
                                   tuple(allow), stock, {"length": length, "head": head, "p": tuple(p), "d": tuple(d)}))
        return item

    def add(self, name, item, size, kind, group, part, solid, allow=(), stock=False):
        self.items.append(Fastener(name, item, size, kind, group, part, solid, tuple(allow), stock))

    def joint(self, key, item, kind, length, grip, limit=0.0, size="M5", count=1):
        """One length check for each kind of joint; count the screws that share it."""
        key = key.replace("_left", "").replace("_right", "")
        if key in self.joints:
            self.joints[key].count += count
        else:
            self.joints[key] = Joint(key, item, kind, length, grip, limit, size, count)

    def mark(self):
        return len(self.items), {k: j.count for k, j in self.joints.items()}

    def mirror_since(self, mark):
        """Add the mirror image of the items added since mark, and count their joints twice."""
        start, before = mark
        for f in self.items[start:]:
            if "left" not in f.name:
                f.name = "left " + f.name
        self.items += [mirror(f) for f in self.items[start:]]
        for k, j in self.joints.items():
            j.count += j.count - before.get(k, 0)

    def tnut_screw(self, name, p, d, slot, group, part, clamp, length=None, head="socket", allow=("bar", "rail", "beam"),
                   washer=False):
        """An M5 screw through a wall of thickness clamp into a T-nut. p is the point on the face of
        the extrusion, d points into the extrusion, slot is the slot direction. washer=True puts
        an M5 washer under the head."""
        length = length or S.TNUT_SCREW_L
        px, py, pz = p
        dx, dy, dz = d
        w = S.WASHER[1] if washer else 0.0
        base = (px - dx * (clamp + w), py - dy * (clamp + w), pz - dz * (clamp + w))
        item = self.screw(name, "M5", length, head, base, d, group, part, allow)
        if washer:
            self.add(name + " washer", "M5 washer", "M5", "washer", group, part,
                     _along(Pos(0, 0, 0.05) * ring(S.WASHER[0], w - 0.1), base, d))
        self.add(name + " T-nut", "M5 drop-in T-nut", "M5", "tnut", group, part, _along(tnut_solid(), p, d, slot), allow)
        self.joint(f"{part}: M5 into a T-nut" + (", washer under the head" if washer else ""), item, "tnut", length, clamp + w)


def _tf_axis(loc, p, d):
    """The bearing point and the axis of a screw after the location loc."""
    from build123d import Vertex
    a = (loc * Vertex(*p)).center()
    b_ = (loc * Vertex(p[0] + d[0], p[1] + d[1], p[2] + d[2])).center()
    return {"p": (a.X, a.Y, a.Z), "d": (b_.X - a.X, b_.Y - a.Y, b_.Z - a.Z)}


def _mirror_meta(m):
    out = dict(m)
    if "p" in m:
        out["p"] = (S.FRAME_X - m["p"][0], m["p"][1], m["p"][2])
    if "d" in m:
        out["d"] = (-m["d"][0], m["d"][1], m["d"][2])
    return out


def mirror(f):
    """The mirror image of a fastener about the centre plane of the frame."""
    return Fastener(f.name.replace("left", "right"), f.item, f.size, f.kind, f.group, f.part.replace("left", "right"),
                    P.mirror_x(f.solid), f.allow, f.stock, _mirror_meta(f.meta))


# ---------------------------------------------------------------- static: frame, brackets, feet, pole foot

def static_items(b):
    z = S.BAR_SLOT_Z[0]
    # The bar end screws (stock): through each bar into the end holes of the 2040 rails.
    hd, hh = S.BAR_SCREW_HEAD
    for x in S.BAR_SCREW_X + tuple(S.FRAME_X - x for x in S.BAR_SCREW_X):
        for y, d in ((0.0, (0, 1, 0)), (S.FRAME_Y, (0, -1, 0))):
            b.screw(f"bar end screw x {x:.0f} y {y:.0f}", "M5", S.BAR_SCREW_L, "socket", (x, y, z), d, "static",
                    "frame (stock)", ("bar", "rail"), stock=True)
    b.joint("frame (stock): M5 through the bar into the rail end", name_of("socket", "M5", S.BAR_SCREW_L), "tapped",
            S.BAR_SCREW_L, S.BAR_D, S.BEAM_END_THREAD, count=8)
    mark = b.mark()
    # The front base (left): two M5 in T-nuts in the top slot of the front bar; the M3 tension screw
    # and its nut in the sled; the Y endstop screws.
    zt = S.RAIL_TOP_Z
    for x in S.YF_SCREWS_X:
        b.tnut_screw(f"Y front base screw x {x:.0f}", (x, S.BAR_D / 2, zt), (0, 0, -1), (1, 0, 0), "static",
                     "y_front_left", S.ANCHOR_FLOOR)
    # The Y motor bracket on the back face of the back bar: two M5 into T-nuts in the face slot, and
    # four M3 into the Y motor (the heads on the inner face of the motor plate).
    for x in S.YM_SCREWS_X:
        b.tnut_screw(f"Y motor bracket screw x {x:.0f}", (x, S.FRAME_Y, S.BAR_SLOT_Z[0]), (0, -1, 0), (1, 0, 0), "static",
                     "y_motor_mount_left", 6.0)
    xi = S.YM_FACE_X + S.YM_PLATE_T
    for dy in (-S.MOTOR_HOLES / 2, S.MOTOR_HOLES / 2):
        for dz in (-S.MOTOR_HOLES / 2, S.MOTOR_HOLES / 2):
            item = b.screw(f"Y motor screw {dy:+.0f} {dz:+.0f}", "M3", 10.0, "socket", (xi, S.YM_Y + dy, S.YB_AX + dz),
                           (-1, 0, 0), "static", "y_motor_mount_left", ("Y motor",))
            b.joint("y_motor_mount: M3 into the Y motor", item, "tapped", 10.0, S.YM_PLATE_T, S.MOTOR_THREAD, "M3")
    # The Y idler fork on the arm of the front base: the M5 x 30 axle through both cheeks (a washer each
    # side of the idler, a nyloc nut), and the M3 tension screw from the front through the end wall into
    # the nut in the outer cheek.
    yi, za = S.YI_Y, S.YB_AX
    x0, x1 = S.YFORK_X
    hw = S.TIDLER["h"] / 2
    b.screw("Y idler axle", "M5", S.XIDLER_AXLE_L, "socket", (x0, yi, za), (1, 0, 0), "static", "y_idler_fork_left",
            ("Y idler",))
    for k, xw in enumerate((S.YB_X - hw - S.FORK_WASHER + 0.05, S.YB_X + hw + 0.05)):
        b.add(f"Y idler washer {k}", SMALL_WASHER_ITEM, "M5", "washer", "static", "y_idler_fork_left",
              _along(ring(S.WASHER_SMALL[0], S.FORK_WASHER - 0.1), (xw, yi, za), (1, 0, 0)))
    b.add("Y idler nut", "M5 nyloc nut", "M5", "nyloc", "static", "y_idler_fork_left",
          _along(Pos(0, 0, 0.05) * nut_solid("M5", True), (x1, yi, za), (1, 0, 0)))
    b.joint("y_idler_fork: M5 Y idler axle through both cheeks (2 washers), nyloc nut", name_of("socket", "M5", S.XIDLER_AXLE_L),
            "nut", S.XIDLER_AXLE_L, x1 - x0, S.NYLOC[1])
    sx, sz = S.YFORK_SCREW
    ye0 = S.YI_Y - S.YFORK_EW[1]
    for k, (lx, ly) in enumerate(P.y_lip_screws()):
        it = b.screw(f"Y bracket screw {k}", "M3", S.YBRK_SCREW_L, "socket", (lx, ly, S.RAIL_TOP_Z + S.YLIP[0]), (0, 0, -1),
                     "static", "y_idler_bracket_left")
        b.joint("y_idler_bracket: M3 through a lip of the front base into the bracket", it, "selftap", S.YBRK_SCREW_L,
                S.YLIP[0], 9.0, "M3")
    # The ear of the bracket: an M5 x 12 countersunk screw into a T-nut in the front face slot of the bar.
    b.tnut_screw("Y bracket ear screw", P.y_ear_screw(), (0, 1, 0), (1, 0, 0), "static", "y_idler_bracket_left",
                 S.YBRK_EAR_CLAMP, length=S.YBRK_EAR_SCREW_L, head="csk")
    item = b.screw("Y tension screw", "M3", S.YTENSION_L, "socket", (sx, ye0, sz), (0, 1, 0), "static", "y_idler_bracket_left",
                   ("Y idler fork",))
    yn = S.YI_Y - S.FORK_R + S.FORK_NUT_X + 0.2
    b.add("Y tension nut", "M3 nut", "M3", "nut", "static", "y_idler_fork_left",
          _along(nut_solid("M3"), (sx, yn, sz), (0, 1, 0), (0, 0, 1)), ("Y idler fork",))
    b.joint("y_idler_bracket: M3 tension screw through the end wall into the nut of the fork (fork at the back end)", item, "nut",
            S.YTENSION_L, (yn + max(S.YIDLER_TRAVEL)) - ye0, S.M3_NUT[1], "M3")
    # The Y endstop board: two M3 x 8 through the board into M3 heat-set inserts in the standoffs.
    ins = S.INSERT_M3
    zs = S.YF_TOP + S.ES_STANDOFF                       # the standoff tops: the back of the board
    for k, (hx, hy) in enumerate(P.es_holes_y()):
        item = b.screw(f"Y switch screw {k}", "M3", S.ES_SCREW_Y, "socket", (hx, hy, zs + S.ES["pcb"][2]), (0, 0, -1),
                       "static", "y_front_left", ("Y switch",))
        b.add(f"Y switch insert {k}", INSERT_M3_ITEM, "M3", "insert", "static", "y_front_left",
              Pos(hx, hy, zs - ins["len"]) * P.insert_real(ins["od"], ins["len"] - 0.05, S.SHANK["M3"] / 2 + 0.05),
              ("Y front base",))
        b.items[-1].meta = {"size": "M3", "len": ins["len"], "od": ins["od"], "hole": ins["hole"], "depth": ins["depth"],
                            "p": (hx, hy, zs), "d": (0, 0, -1)}
    b.joint("y_front: M3 endstop board screw into a heat-set insert", name_of("socket", "M3", S.ES_SCREW_Y), "insert",
            S.ES_SCREW_Y, S.ES["pcb"][2], ins["len"], "M3", count=2)
    b.mirror_since(mark)
    # The Y chain (left side only): the anchor in the bottom outer slot of the rail, the two end links.
    zr = S.RAIL_TOP_Z - S.RAIL_H
    for y in S.YCH_ARM_SCREWS:
        b.tnut_screw(f"Y chain anchor screw y {y:.0f}", (S.SLOT_OUT_X, y, zr), (0, 0, 1), (0, 1, 0), "static",
                     "y_chain_anchor", S.ANCHOR_FLOOR)
    x1 = S.YCH_X + S.YCH_OUTER[1] / 2
    for y in (S.YCH_FIX_Y + 2.5, S.YCH_FIX_Y + S.YCH_END - 2.5):
        item = b.screw(f"Y chain fixed end screw y {y:.0f}", "M3", 10.0, "socket", (x1 - S.YCH_LINK_WALL, y, S.YCH_ZL), (1, 0, 0),
                       "static", "y_chain_anchor", ("Y chain",))
        b.joint("y_chain: M3 through an end link into the anchor or the carriage tab", item, "selftap", 10.0, S.YCH_LINK_WALL,
                9.0, "M3")
    # The camera pole foot: two M5 in T-nuts in the back bar, the M6 screw into the pole, the collar screw.
    for dx in (-25.0, 25.0):
        b.tnut_screw(f"pole foot screw {dx:+.0f}", (S.MAST_X + dx, S.FRAME_Y, z), (0, -1, 0), (1, 0, 0), "static",
                     "mast_foot", S.MFOOT_PLATE)
    zh = S.MFOOT_FLOOR - 4.0                     # the head top on the cone of the counterbore: 4 mm of floor
    item = b.screw("pole screw", "M6", S.M6_BOLT_L, "socket", (S.MAST_X, S.POLE_Y, zh), (0, 0, 1), "static", "mast_foot", ("pole",))
    b.joint("mast_foot: M6 into the pole end", item, "tapped", S.M6_BOLT_L, S.MFOOT_FLOOR - zh, S.POLE_THREAD, "M6")
    ro = S.POLE_R_OUT
    ey0, ey1 = S.POLE_Y + ro - 2.0, S.POLE_Y + ro + S.COLLAR_EAR
    ys, zs = (ey0 + ey1) / 2, (S.MFOOT_FLOOR + S.MFOOT_TOP) / 2
    x0 = S.MAST_X - 6.8
    item = b.screw("pole collar screw", "M3", S.COLLAR_SCREW_L, "socket", (x0, ys, zs), (1, 0, 0), "static", "mast_foot")
    xn = S.MAST_X + 3.6 - S.M3_NUT[1] / 2
    b.add("pole collar nut", "M3 nut", "M3", "nut", "static", "mast_foot",
          _along(Pos(0, 0, 0.05) * nut_solid("M3"), (xn, ys, zs), (1, 0, 0)))
    b.joint("mast_foot: M3 collar screw, M3 nut", item, "nut", S.COLLAR_SCREW_L, xn - x0, S.M3_NUT[1], "M3")


# ---------------------------------------------------------------- gantry: Y carriages, beam, X motor, X idler

def gantry_items(b, c):
    mark = b.mark()
    # The wheels: bolts, spacers, washers, nuts (parts.y_wheel_stack). Each bolt carries its head.
    kinds = {"spacer": ("M5 spacer, 6 mm (stock)", "spacer", True), "eccentric spacer": ("eccentric spacer (stock)", "eccentric", True),
             "washer": ("M5 washer", "washer", False), "nut": ("M5 nyloc nut", "nyloc", False),
             "insert": (INSERT_ITEM, "insert", False)}
    head = None
    for i, (n, sh) in enumerate(P.y_wheel_stack(c)):
        if n == "bolt head":
            head = sh
        elif n == "bolt":
            w = i // 4
            if w >= 2:
                item = name_of("socket", "M5", S.IN_AXLE_L)
            else:
                item = name_of("socket", "M5", S.OUT_AXLE_L)
            b.add(f"Y wheel bolt {i}", item, "M5", "screw", "gantry", "y_carriage_left", sh + head, ("Y wheel",))
            x_, y_, _ = P.y_wheel_pos(c)[w]
            if w >= 2:
                b.items[-1].meta = {"length": S.IN_AXLE_L, "head": "socket", "p": (x_, y_, S.YP_Z0 + S.IN_BOSS), "d": (0, 0, -1)}
            else:
                ln = S.OUT_AXLE_L
                b.items[-1].meta = {"length": ln, "head": "socket", "p": (x_, y_, S.YW_Z - S.WHEEL_T / 2), "d": (0, 0, 1)}
        else:
            it, kd, st = kinds[n]
            allow = ("Y wheel", "Y carriage") if n == "insert" else ("Y wheel",)
            b.add(f"Y wheel {n} {i}", it, "M5", kd, "gantry", "y_carriage_left", sh, allow, st)
            if n == "insert":
                ins = S.INSERT_M5
                x_, y_, _ = P.y_wheel_pos(c)[i // 4]
                b.items[-1].meta = {"size": "M5", "len": ins["len"], "od": ins["od"], "hole": ins["hole"], "depth": ins["depth"],
                                    "p": (x_, y_, S.YP_Z1 + S.INSERT_BOSS[1]), "d": (0, 0, -1)}
    b.joint("y_carriage: M5 outer wheel axle (head under the wheel), nyloc nut on the 6 mm boss", name_of("socket", "M5", S.OUT_AXLE_L),
            "nut", S.OUT_AXLE_L, S.WHEEL_T + S.SPACER_H + S.YP_T + S.INSERT_BOSS[1], S.NYLOC[1], count=2)
    b.joint("y_carriage: M5 inner wheel axle (head on the 12 mm boss), nyloc nut under the wheel",
            name_of("socket", "M5", S.IN_AXLE_L), "nut", S.IN_AXLE_L, S.IN_BOSS + S.SPACER_H + S.WHEEL_T, S.NYLOC[1])
    bc = S.BZ
    # The upper run of the Y belt: its two folded ends and their printed jaws in the clamp blocks. An M3
    # x 10 through each jaw into an M3 insert in the ledge of the pocket.
    for i, (k, sh) in enumerate(P.y_belt_ends(c)):
        end = "front" if i < 2 else "back"
        if k == "clip":
            b.add(f"Y belt jaw {end}", JAW_ITEM, "M3", "clip", "gantry", "y_carriage_left", sh, ("Y belt", "jaw screw"))
            x, y, z = P.y_jaw_axis(c, end == "front")
            jaw_screw(b, f"Y belt jaw screw {end}", (x, y, z), (0, 0, -1), "gantry", "y_carriage_left")
        else:
            b.add(f"Y belt end {end}", "belt end", "GT2", "belt", "gantry", "y_carriage_left", sh, ("Y belt", "belt jaw"))
    b.mirror_since(mark)
    # The beam: one M5 through the back wall of each saddle into a T-nut in the back slot of the beam.
    for side, x in (("left", S.BEAM_TNUT_X), ("right", S.FRAME_X - S.BEAM_TNUT_X)):
        b.tnut_screw(f"{side} beam screw", (x, c + S.BEAM / 2, bc), (0, -1, 0), (1, 0, 0), "gantry", f"y_carriage_{side}",
                     S.XTOWER_HALF_Y - S.BEAM / 2, allow=("beam",))
    # The X motor: three M3 from the front of its wall into the motor face (the heads in counterbores).
    px, py, pz = P.x_pulley_at(c)
    y0 = c + S.XM_WALL[0] + S.XM_SCREW_CB
    for dx, dz in P.x_motor_screws():
        item = b.screw(f"left X motor screw {dx:+.0f} {dz:+.0f}", "M3", S.XMOTOR_SCREW_L, "socket", (px + dx, y0, pz + dz),
                       (0, 1, 0), "gantry", "y_carriage_left", ("X motor",))
        b.joint("y_carriage_left: M3 into the X motor", item, "tapped", S.XMOTOR_SCREW_L, S.XM_WALL[1] - y0 + c,
                S.MOTOR_THREAD, "M3")
    # The moving end of the Y chain on the tab of the left carriage plate: two M3 through the end link.
    x1 = S.YCH_X + S.YCH_OUTER[1] / 2
    ty0, ty1 = c + S.YCH_TAB_Y[0], c + S.YCH_TAB_Y[1]
    for y in (ty0 + 5.5, ty1 - 5.5):
        item = b.screw(f"left Y chain moving end screw {y - c:.0f}", "M3", 10.0, "socket", (x1 - S.YCH_LINK_WALL, y,
                       S.YCH_TAB_ZS), (1, 0, 0), "gantry", "y_carriage_left", ("Y chain",))
        b.joint("y_chain: M3 through an end link into the anchor or the carriage tab", item, "selftap", 10.0,
                S.YCH_LINK_WALL, 9.0, "M3")
    # The X endstop board on its two standoffs: M3 x 8 from the front through the board into M3 heat-set
    # inserts.
    ys = c + S.ES_X_BACK_DY
    ins = S.INSERT_M3
    for k, (hx, hz) in enumerate(P.es_holes_x()):
        b.screw(f"left X switch screw {k}", "M3", S.ES_SCREW_X, "socket", (hx, ys - S.ES["pcb"][2], hz), (0, 1, 0),
                "gantry", "y_carriage_left", ("X switch",))
        b.add(f"left X switch insert {k}", INSERT_M3_ITEM, "M3", "insert", "gantry", "y_carriage_left",
              _along(P.insert_real(ins["od"], ins["len"] - 0.05, S.SHANK["M3"] / 2 + 0.05), (hx, ys, hz), (0, 1, 0)),
              ("Y carriage",))
        b.items[-1].meta = {"size": "M3", "len": ins["len"], "od": ins["od"], "hole": ins["hole"], "depth": ins["depth"],
                            "p": (hx, ys, hz), "d": (0, 1, 0)}
    b.joint("y_carriage_left: M3 X endstop board screw into a heat-set insert", name_of("socket", "M3", S.ES_SCREW_X), "insert",
            S.ES_SCREW_X, S.ES["pcb"][2], ins["len"], "M3", count=2)
    # The X idler past the right beam end: in the fork, an M5 x 30 from the front through the front cheek,
    # a washer, the idler, a washer, the back cheek, a nyloc nut. The M3 x 20 tension screw goes from
    # outside through the end wall into the nut in the back cheek. Built at the left position, then mirrored.
    x, z = S.XIDLER_X, S.BZ
    y0, y1 = c + S.FORK_Y[0], c + S.FORK_Y[1]
    yi0 = c + S.XB_Y - S.IDLER_H / 2
    sy, sz = S.FORK_SCREW
    xe = x - S.FORK_EW[1]
    xn = x - S.FORK_R + S.FORK_NUT_X + 0.2
    xi = [Fastener("X idler axle", name_of("socket", "M5", S.XIDLER_AXLE_L), "M5", "screw", "gantry", "x_idler_fork",
                   _along(screw_solid("M5", S.XIDLER_AXLE_L), (x, y0, z), (0, 1, 0)), ("X idler",),
                   meta={"length": S.XIDLER_AXLE_L, "head": "socket", "p": (x, y0, z), "d": (0, 1, 0)}),
          Fastener("X idler washer 0", SMALL_WASHER_ITEM, "M5", "washer", "gantry", "x_idler_fork",
                   _along(ring(S.WASHER_SMALL[0], S.FORK_WASHER - 0.1), (x, yi0 - S.FORK_WASHER + 0.05, z), (0, 1, 0))),
          Fastener("X idler washer 1", SMALL_WASHER_ITEM, "M5", "washer", "gantry", "x_idler_fork",
                   _along(ring(S.WASHER_SMALL[0], S.FORK_WASHER - 0.1), (x, yi0 + S.IDLER_H + 0.05, z), (0, 1, 0))),
          Fastener("X idler nut", "M5 nyloc nut", "M5", "nyloc", "gantry", "x_idler_fork",
                   _along(Pos(0, 0, 0.05) * nut_solid("M5", True), (x, y1, z), (0, 1, 0))),
          Fastener("X tension screw", name_of("socket", "M3", S.XTENSION_L), "M3", "screw", "gantry", "y_carriage_right",
                   _along(screw_solid("M3", S.XTENSION_L), (xe, c + sy, sz), (1, 0, 0)), ("X idler fork",),
                   meta={"length": S.XTENSION_L, "head": "socket", "p": (xe, c + sy, sz), "d": (1, 0, 0)}),
          Fastener("X tension nut", "M3 nut", "M3", "nut", "gantry", "x_idler_fork",
                   _along(nut_solid("M3"), (xn, c + sy, sz), (1, 0, 0), (0, 0, 1)), ("X idler fork",))]
    for f in xi:
        f.solid = P.mirror_x(f.solid)
        f.meta = _mirror_meta(f.meta)
        b.items.append(f)
    b.joint("x_idler_fork: M5 X idler axle through both cheeks (2 washers), nyloc nut", xi[0].item, "nut", S.XIDLER_AXLE_L,
            y1 - y0, S.NYLOC[1])
    b.joint("y_carriage_right: M3 X belt tension screw through the end wall into the nut in the fork (fork at the slack end)",
            xi[4].item, "nut", S.XTENSION_L, (xn + max(S.XIDLER_TRAVEL)) - xe, S.M3_NUT[1], "M3")


# ---------------------------------------------------------------- carriage and pen: in the plate frame, then moved

def jaw_screw(b, name, top, d, group, part, t=None):
    """The M3 x 10 screw of a belt jaw (the head on the jaw top at top, d into the clamp) and its M3
    insert in the ledge under the jaw. t moves both from the plate frame to the frame."""
    ins = S.INSERT_M3
    gap = S.JAW_UNDER - S.JAW_LEDGE
    ledge = tuple(top[k] + d[k] * (S.JAW_T + gap) for k in range(3))
    item = b.screw(name, "M3", S.JAW_SCREW_L, "socket", top, d, group, part, ("belt jaw",))
    sc = b.items[-1]
    b.add(name.replace("screw", "insert"), INSERT_M3_ITEM, "M3", "insert", group, part,
          _along(P.insert_real(ins["od"], ins["len"] - 0.05, S.SHANK["M3"] / 2 + 0.05), ledge, d), ("Y carriage", "X plate"))
    b.items[-1].meta = {"size": "M3", "len": ins["len"], "od": ins["od"], "hole": ins["hole"],
                        "depth": S.JAW_INSERT_DEPTH, "p": ledge, "d": d}
    if t is not None:
        for f in (sc, b.items[-1]):
            f.solid = t * f.solid
            f.meta.update(_tf_axis(t, f.meta["p"], f.meta["d"]))
    b.joint("belt jaw: M3 through the jaw into a heat-set insert in the ledge", item, "insert", S.JAW_SCREW_L,
            S.JAW_T + gap, ins["len"], "M3")


def carriage_items(b, t):
    """The head screws, the servo screws and the X wheel axles, moved by t (plate frame to frame)."""
    for i, (n, x, z) in enumerate(S.HEAD_HOLES):
        ln = S.HEAD_SCREW_L[n]
        y0 = S.PLATE_SHEET
        item = b.screw(f"head screw {n}", "M3", ln, "socket", (0, 0, 0), (0, -1, 0), "carriage", "x_carriage_plate")
        b.items[-1].solid = t * _along(screw_solid("M3", ln), (x, y0, z), (0, -1, 0))
        b.items[-1].meta.update(_tf_axis(t, (x, y0, z), (0, -1, 0)))
        b.joint("pen_carriage: M3 from the back of the X plate", item,
                "selftap", ln, y0, S.HEAD_SCREW_DEPTH, "M3")
    y_tab = S.SERVO_FACE - S.SERVO_TAB_T
    for dz in (-S.SERVO_TAB_HOLES / 2, S.SERVO_TAB_HOLES / 2):
        item = b.screw(f"servo screw {dz:+.0f}", "M2", S.SERVO_SCREW_L, "pan", (0, 0, 0), (0, 1, 0), "carriage", "pen_carriage",
                       ("servo",), stock=True)
        item = b.items[-1].item = item.replace("(stock)", "(stock, in the servo bag)")
        b.items[-1].solid = t * _along(screw_solid("M2", S.SERVO_SCREW_L, "pan"), (S.SHAFT_X, y_tab, S.BODY_ZC + dz), (0, 1, 0))
        b.joint("pen_carriage: M2 servo screw (in the servo bag)", item, "selftap", S.SERVO_SCREW_L, S.SERVO_TAB_T, 8.0, "M2")
    # The X wheel axles: the head behind the wheel, the axle forward through the wheel and the boss.
    yw = S.PLATE_FRONT + S.WHEEL_T / 2 + 0.05           # the back face of a wheel
    zc = [w.bounding_box().center().Z for w in P.x_wheels()]
    for i, (n, x, zh) in enumerate(S.X_WHEELS):
        # The axle sits in its hole. The eccentric axle follows the wheel (the spacer offsets it).
        z = zc[i] if i == S.X_ECC else zh
        ln = S.XW_AXLE_L[i]
        y0, y1 = S.XW_BOSS_Y[i]
        # Button heads: a low head behind the wheel keeps clear of the back face of the beam (the head
        # board is there).
        item = b.screw(f"X wheel axle {n}", "M5", ln, "button", (0, 0, 0), (0, -1, 0), "carriage", "x_carriage_plate",
                       ("X wheel",))
        b.items[-1].solid = t * _along(screw_solid("M5", ln, "button"), (x, yw, z), (0, -1, 0))
        b.items[-1].meta.update(_tf_axis(t, (x, yw, z), (0, -1, 0)))
        stack = S.WHEEL_T + (yw - S.PLATE_FRONT - S.WHEEL_T / 2)
        if i == S.X_ECC:
            sp = P.eccentric_real(S.ECC["h"] - 0.1, 2.6)
            b.add(f"X wheel eccentric {n}", "eccentric spacer (stock)", "M5", "eccentric", "carriage", "x_carriage_plate",
                  t * _along(sp, (x, y1 + 0.05, z), (0, 1, 0)), ("X wheel",), stock=True)
        else:
            # A stock 6 mm spacer (10 mm across) between the wheel and the boss face, as on the stock plate.
            b.add(f"X wheel spacer {n}", "M5 spacer, 6 mm (stock)", "M5", "spacer", "carriage", "x_carriage_plate",
                  t * _along(P.spacer_real(S.WASHER[0], S.SPACER_H - 0.1, 2.6), (x, y1 + 0.05, z), (0, 1, 0)), ("X wheel",),
                  stock=True)
        b.add(f"X wheel nut {n}", "M5 nyloc nut", "M5", "nyloc", "carriage", "x_carriage_plate",
              t * _along(nut_solid("M5", True), (x, y0 - 0.05, z), (0, -1, 0)))
        b.joint(f"x_carriage_plate: M5 {'eccentric top' if i == S.X_ECC else n} wheel axle (head behind the wheel), "
                "nyloc nut in front", item, "nut", ln, yw - y0, S.NYLOC[1])


def x_belt_items(b, t):
    """The two X belt ends and their printed jaws in the clamp blocks of the X plate, each with an M3 x 10
    from under the jaw into an M3 insert in the ledge."""
    for i, (k, sh) in enumerate(P.x_belt_ends()):
        end = "left" if i < 2 else "right"
        if k == "clip":
            b.add(f"X belt jaw {end}", JAW_ITEM, "M3", "clip", "carriage", "x_carriage_plate", t * sh, ("X belt", "jaw screw"))
            top, d = P.x_jaw_axis(end)
            jaw_screw(b, f"X belt jaw screw {end}", top, d, "carriage", "x_carriage_plate", t)
        else:
            # The belt end starts in the bottom slot of the beam (the beam model is a solid box).
            b.add(f"X belt end {end}", "belt end", "GT2", "belt", "carriage", "x_carriage_plate", t * sh,
                  ("X belt", "beam", "belt jaw"))


def pen_items(b, t):
    """The clamp screw and its nut in the slider, at pen down."""
    sc, _ = P.clamp_screw(S.PEN_SIZE_SIM)
    b.add("pen clamp screw", name_of("socket", "M3", S.CLAMP_SCREW_L), "M3", "screw", "pen", "pen_slider", t * sc, ("pen",))
    nut_x = S.SLIDER_X0 + S.WALL_NUT / 2 - S.M3_NUT[1] / 2
    nut = _along(nut_solid("M3"), (nut_x, S.PEN_CY, S.SLIDER_Z0 + S.CLAMP_Z), (1, 0, 0), (0, 0, 1))
    b.add("pen clamp nut", "M3 nut", "M3", "nut", "pen", "pen_slider", t * nut)


# ---------------------------------------------------------------- the whole set

def build(c, xp):
    """All the fasteners, with the gantry at y = c and the X plate at x = xp: (items, joints)."""
    b = Builder()
    static_items(b)
    gantry_items(b, c)
    t = P.plate_offset(xp, c)
    carriage_items(b, t)
    x_belt_items(b, t)
    pen_items(b, t)
    return b.items, list(b.joints.values())


def by_group(items, group):
    return [f for f in items if f.group == group]


def check_joint(j):
    """The length check of one joint: the thread length and what is left. Returns (ok, text)."""
    past = j.length - j.grip
    if j.kind == "tnut":
        eng = min(past - S.SLOT_LIP, S.TNUT[2])
        ok = eng >= S.TNUT_ENGAGE and past <= S.SLOT_DEPTH
        txt = f"{eng:.1f} mm in the T-nut, tip {past:.1f} mm into the slot (slot depth {S.SLOT_DEPTH})"
    elif j.kind == "selftap":
        ok = S.SELF_TAP_ENGAGE[j.size] <= past <= j.limit
        txt = f"{past:.1f} mm of thread in a {j.limit:.1f} mm pilot (at least {S.SELF_TAP_ENGAGE[j.size]:.0f})"
    elif j.kind == "insert":
        ok = 0.7 * j.limit <= past <= j.limit + 3.0          # the hole is open past the insert
        txt = f"{past:.1f} mm of thread in a {j.limit:.1f} mm heat-set insert"
    elif j.kind == "tapped":
        lo = S.MOTOR_ENGAGE if j.size == "M3" else 5.0
        ok = lo <= past <= j.limit
        txt = f"{past:.1f} mm of thread in a {j.limit:.1f} mm thread (at least {lo:.1f})"
    else:
        out = past - j.limit
        ok = out >= 1.0
        txt = f"stands {out:.1f} mm out of the nut (at least 1)"
    j.result = {"ok": ok, "text": txt}
    return ok, txt


def counts(items):
    """The fastener counts by BOM item (the stock items are apart), and by printed part."""
    by_item, by_part = {}, {}
    for f in items:
        if f.kind == "belt":
            continue
        key = f.item
        by_item[key] = by_item.get(key, 0) + 1
        by_part.setdefault(f.part, {})
        by_part[f.part][key] = by_part[f.part].get(key, 0) + 1
    return by_item, by_part
