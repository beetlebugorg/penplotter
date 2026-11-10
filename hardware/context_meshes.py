"""Write the context meshes of the plotter that the simulator draws from frame.json.

Run from the hardware directory:

    python context_meshes.py

The simulator (sim/web/machine.js, sim/web/wiring.js) draws these parts at run time from
stl/frame.json. The Printdeck assembly needs them as STL files. This script writes them to
stl/context/, in frame coordinates (mm, Z up), at machine home, the pose of stl/sim2/:

- static: frame.stl, feet.stl, y_belts.stl, drag_chain_fixed.stl, camera_pole.stl, webcam.stl,
  control_box.stl
- gantry: x_beam.stl, y_wheels.stl, x_belt.stl, x_endstop.stl, drag_chain_moving.stl,
  servo_loom.stl
- carriage: x_wheels.stl

The script uses only the Python standard library. The output bytes are the same on each run and
on each computer: the coordinates are rounded to 0.0001 mm, the facet order is fixed, and the
header has no date. x_endstop.stl is a crop of the committed meshes in stl/detail/.
"""
import json
import math
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stl", "context")
HEADER = b"penplotter context mesh, hardware/context_meshes.py".ljust(80, b" ")


# ---------------------------------------------------------------------------
# Vectors.

def add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    n = math.sqrt(dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def at(o, axes, u, v, w):
    """The point o + u axes[0] + v axes[1] + w axes[2]."""
    return add(add(add(o, axes[0], u), axes[1], v), axes[2], w)


# ---------------------------------------------------------------------------
# Closed solids. A solid is a list of triangles. close() turns all the triangles of a solid
# when its signed volume is negative, so that the normals point out.

def close(tris):
    vol = sum(dot(a, cross(b, c)) for a, b, c in tris)
    return tris if vol >= 0 else [(a, c, b) for a, b, c in tris]


def quad(a, b, c, d):
    return [(a, b, c), (a, c, d)]


def obox(o, axes, lo, hi):
    """A box with the local ranges lo..hi along the three axes, at origin o."""
    p = [at(o, axes, x, y, z) for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return close([t for a, b, c, d in faces for t in quad(p[a], p[b], p[c], p[d])])


FRAME = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def box(b):
    """A box from a frame box [x0, y0, z0, x1, y1, z1]."""
    return obox((0.0, 0.0, 0.0), FRAME, b[:3], b[3:])


AXES = {"x": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
        "y": ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        "z": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))}


def lathe(profile, c, axis, n=32):
    """A solid of revolution. profile is a closed loop of (radius, height) points. The axis of
    revolution is the frame axis "x", "y" or "z" through c."""
    ax = AXES[axis]
    ring = [(math.cos(2 * math.pi * j / n), math.sin(2 * math.pi * j / n)) for j in range(n)]
    pt = lambda r, h, j: at(c, ax, r * ring[j % n][0], r * ring[j % n][1], h)
    tris = []
    for k in range(len(profile)):
        (r0, h0), (r1, h1) = profile[k], profile[(k + 1) % len(profile)]
        for j in range(n):
            tris += quad(pt(r0, h0, j), pt(r1, h1, j), pt(r1, h1, j + 1), pt(r0, h0, j + 1))
    return close(tris)


def cyl(r, length, c, axis, n=24):
    return lathe([(0.0, -length / 2), (r, -length / 2), (r, length / 2), (0.0, length / 2)], c, axis, n)


# ---------------------------------------------------------------------------
# The V-slot extrusions, as machine.js profileShape: a slot in the middle of each 20 mm face
# and a centre hole in each 20 mm cell.

SLOT_W, SLOT_D, HOLE_R = 3.1, 4.5, 2.1


def cells(n):
    return [-n / 2 + 10 + 20 * i for i in range(max(1, round(n / 20)))]


def outline(u0, v0, u1, v1, slots, marks=()):
    """The CCW outline of the rectangle u0..u1, v0..v1 with slots. slots: the slot centres on
    each face, in the order bottom, right, top, left. marks: the u of extra points on the bottom
    and the top face (the cell edges of a 2040), so that the walls and the caps share the edges."""
    sl, dp = SLOT_W, SLOT_D
    bottom, right, top, left = slots

    def face(slot_at, mark_at, ends, inward):
        """The points along one face from ends[0] to ends[1]. inward(c, d) is the point at c
        along the face and at the depth d into the profile."""
        k = 1 if ends[1] > ends[0] else -1
        pts = []
        for c, slot in sorted([(c, True) for c in slot_at] + [(m, False) for m in mark_at], reverse=k < 0):
            if slot:
                pts += [inward(c - k * sl, 0), inward(c - k * (sl - 1.5), dp),
                        inward(c + k * (sl - 1.5), dp), inward(c + k * sl, 0)]
            else:
                pts.append(inward(c, 0))
        return pts

    pts = [(u0, v0)]
    pts += face(bottom, marks, (u0, u1), lambda c, d: (c, v0 + d))
    pts.append((u1, v0))
    pts += face(right, (), (v0, v1), lambda c, d: (u1 - d, c))
    pts.append((u1, v1))
    pts += face(top, marks, (u1, u0), lambda c, d: (c, v1 - d))
    pts.append((u0, v1))
    pts += face(left, (), (v1, v0), lambda c, d: (u0 + d, c))
    return pts


def ring_cap(outer, c, r, n=16):
    """The cap between a CCW loop that is star-shaped about c and a hole of radius r at c.
    The hole has n points and one more point on the ray to each loop point. Each wedge
    between two rays is a fan from its first loop point. Returns the hole loop (CCW) and the
    CCW 2D triangles."""
    ang = lambda p: math.atan2(p[1] - c[1], p[0] - c[0]) % (2 * math.pi)
    k0 = min(range(len(outer)), key=lambda i: ang(outer[i]))
    O = outer[k0:] + outer[:k0]
    oa = [ang(p) for p in O]
    ha = sorted(set([round(2 * math.pi * j / n, 12) for j in range(n)] + [round(a, 12) for a in oa]))
    H = [(c[0] + r * math.cos(a), c[1] + r * math.sin(a)) for a in ha]
    hp = {a: i for i, a in enumerate(ha)}
    tris = []
    for k in range(len(O)):
        a0, a1 = round(oa[k], 12), round(oa[(k + 1) % len(O)], 12)
        i0, i1 = hp[a0], hp[a1]
        tris.append((O[k], O[(k + 1) % len(O)], H[i1]))
        i = i1
        while i != i0:
            j = (i - 1) % len(H)
            tris.append((O[k], H[i], H[j]))
            i = j
    return H, tris


def extrusion(b):
    """A V-slot extrusion that fills the frame box b. The longest side is the long axis, as
    machine.js extrusionBox."""
    d = [b[3] - b[0], b[4] - b[1], b[5] - b[2]]
    long = d.index(max(d))
    a1, a2 = [i for i in range(3) if i != long]
    w, h, length = d[a1], d[a2], d[long]
    u, v, s = FRAME[a1], FRAME[a2], FRAME[long]
    if dot(cross(u, v), s) < 0:
        u = (-u[0], -u[1], -u[2])  # keep a right-handed basis; the profile is symmetric
    o = add(((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2), s, -length / 2)
    axes = (u, v, s)
    P = lambda p, z: at(o, axes, p[0], p[1], z)
    cu, cv = cells(w), cells(h)
    assert len(cv) == 1, "the profile has one row of cells (2020, 2040)"
    y = cv[0]
    tris = []

    def walls(loop):
        for i in range(len(loop)):
            p, q = loop[i], loop[(i + 1) % len(loop)]
            tris.extend(quad(P(p, 0), P(q, 0), P(q, length), P(p, length)))

    walls(outline(-w / 2, -h / 2, w / 2, h / 2, (cu, cv, cu, cv), [x + 10 for x in cu[:-1]]))
    for i, x in enumerate(cu):
        cell = outline(x - 10, y - 10, x + 10, y + 10,
                       ([x], [y] if i == len(cu) - 1 else [], [x], [y] if i == 0 else []))
        hole, cap = ring_cap(cell, (x, y), HOLE_R)
        walls(list(reversed(hole)))
        for t in cap:
            tris.append((P(t[0], length), P(t[1], length), P(t[2], length)))
            tris.append((P(t[0], 0), P(t[2], 0), P(t[1], 0)))
    return close(tris)


# ---------------------------------------------------------------------------
# The belts. A belt is 6 mm wide and 1.4 mm thick (frame.json y_belt w, t).

BELT_T = 1.4


def belt_wrap(c, r, ep, eq, ew, width=6.0, steps=96):
    """The half loop of a GT2 belt round a 20T pulley, as machine.js toothedWrapGeo. r is the
    radius of the tooth tips. The loop goes from c + ep to c - ep round the side eq. ew is the
    axle direction. The inside has one round tooth in each groove (2 mm pitch)."""
    back, land, tr, n = r + BELT_T, r + 0.75, 0.555, 20
    axes = (ep, eq, ew)
    outer, inner = [], []
    for i in range(steps + 1):
        a = math.pi * i / steps
        k = a * n / (2 * math.pi) - 0.5
        d = abs(k - round(k)) * (2 * math.pi * (r + 0.5) / n)
        rr = land - (math.sqrt(tr * tr - d * d) * (0.75 / tr) if d < tr else 0.0)
        outer.append((back * math.cos(a), back * math.sin(a)))
        inner.append((rr * math.cos(a), rr * math.sin(a)))
    P = lambda p, z: at(c, axes, p[0], p[1], z)
    h = width / 2
    tris = []
    for i in range(steps):
        o0, o1, i0, i1 = outer[i], outer[i + 1], inner[i], inner[i + 1]
        tris += quad(P(o0, -h), P(o1, -h), P(o1, h), P(o0, h))
        tris += quad(P(i0, -h), P(i0, h), P(i1, h), P(i1, -h))
        tris += quad(P(i0, h), P(o0, h), P(o1, h), P(i1, h))
        tris += quad(P(i0, -h), P(i1, -h), P(o1, -h), P(o0, -h))
    for o_, i_ in ((outer[0], inner[0]), (outer[-1], inner[-1])):
        tris += quad(P(i_, -h), P(o_, -h), P(o_, h), P(i_, h))
    return close(tris)


def y_belts(J):
    """The two Y belt loops (machine.js, fixed Y motors): a flat loop over each rail, round the
    motor pulley behind the back bar and the idler in front of the front bar. The carriage
    clamps the upper run between clamp_dy[0] and clamp_dy[1] from carriage_y0."""
    YB = J["y_belt"]
    zl, zh = YB["z_runs"]
    pu, idl, cd = YB["pulley"], YB["idler"], YB["clamp_dy"]
    cy = J["carriage_y0"]
    r = (zh - zl) / 2 - BELT_T / 2
    w, t = YB["w"] / 2, BELT_T / 2
    tris = []
    for x in YB["x"]:
        for z, spans in ((zl, [(idl["y"], pu["y"])]), (zh, [(idl["y"], cy + cd[0]), (cy + cd[1], pu["y"])])):
            for y0, y1 in spans:
                tris += box([x - w, y0, z - t, x + w, y1, z + t])
        X = (1.0, 0.0, 0.0)
        tris += belt_wrap((x, idl["y"], pu["z"]), r, (0.0, 0.0, 1.0), (0.0, -1.0, 0.0), X, YB["w"])
        tris += belt_wrap((x, pu["y"], pu["z"]), r, (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), X, YB["w"])
    return tris


def x_belt(J):
    """The X belt loop in the x-z plane (machine.js wheelsX): round the X pulley and the X idler.
    The X plate clamps the lower run between x_clamp[0] and x_clamp[1]."""
    XB = J["x_belt"]
    p, i = J["x_motor"]["pos"], J["x_idler"]["pos"]
    xr = (XB["z_runs"][1] - XB["z_runs"][0]) / 2
    xc = J["x_clamp"]
    y, w, t = p[1], J["y_belt"]["w"] / 2, BELT_T / 2
    cut = -xr if XB["clamped"] == "lower" else xr
    tris = []
    for z, spans in ((p[2] + cut, [(p[0], xc[0]), (xc[1], i[0])]), (p[2] - cut, [(p[0], i[0])])):
        for x0, x1 in spans:
            tris += box([x0, y - w, z - t, x1, y + w, z + t])
    Y = (0.0, 1.0, 0.0)
    tris += belt_wrap(tuple(p), xr - t, (0.0, 0.0, 1.0), (-1.0, 0.0, 0.0), Y)
    tris += belt_wrap(tuple(i), xr - t, (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), Y)
    return tris


# ---------------------------------------------------------------------------
# The stock V-wheels (machine.js vWheel): OD 24.4, 10.2 wide, 45 degree flanks, the bearing
# faces with the shield a little in, and the 5 mm bore. With the spacer to the carriage plate.

WHEEL = [(2.5, -5.1), (3.6, -5.1), (3.6, -4.85), (7.2, -4.85), (7.2, -5.1), (9.6, -5.1), (9.6, -3.1),
         (12.2, -0.5), (12.2, 0.5), (9.6, 3.1), (9.6, 5.1), (7.2, 5.1), (7.2, 4.85), (3.6, 4.85),
         (3.6, 5.1), (2.5, 5.1)]


def y_wheels(J):
    """Three wheels on vertical axles in the side slots of each rail, and the spacer from the
    wheel to the bottom of the Y carriage plate (the rail top + 1 mm)."""
    pz0 = max(r["box"][5] for r in J["rails"]) + 1
    tris = []
    for side in J["y_wheels"]:
        for x, y, z in side:
            tris += lathe(WHEEL, (x, y, z), J["wheel"]["axis_y"], 32)
            z0 = z + 5.5
            tris += cyl(3.5, pz0 - z0, (x, y, (z0 + pz0) / 2), "z", 16)
    return tris


def x_wheels(J):
    """Three wheels on the X plate on the beam, and the spacer to the back face of the plate."""
    plate_y = J["x_carriage"]["plate_front_y"] + 6
    tris = []
    for x, y, z in J["x_wheels"]:
        tris += lathe(WHEEL, (x, y, z), J["wheel"]["axis_x"], 32)
        y0 = y - 5.5
        tris += cyl(3.5, y0 - plate_y, (x, (y0 + plate_y) / 2, z), "y", 16)
    return tris


# ---------------------------------------------------------------------------
# The frame: the 2020 cross bars, the 2040 rails, the stock rubber feet, and the 2020 X beam.

def frame(J):
    return [t for b in J["bars"] + J["rails"] for t in extrusion(b["box"])]


def feet(J):
    """The stock rubber feet (machine.js): a cylinder with a 2 mm soft lower edge."""
    r, h = J["foot"]["d"] / 2, J["foot"]["h"]
    c = min(2.0, h / 4)
    prof = [(0.0, 0.0), (r - c, 0.0), (r, c), (r, h), (0.0, h)]
    return [t for x, y in J["feet"] for t in lathe(prof, (x, y, 0.0), "z", 40)]


# ---------------------------------------------------------------------------
# The camera pole and the webcam (machine.js): a round tube in the printed foot behind the
# back bar, and a USB webcam on its top end.

def camera(J):
    m = J["camera"]["mast"]["box"]
    cx, cy = (m[0] + m[3]) / 2, (m[1] + m[4]) / 2
    pole = cyl((m[3] - m[0]) / 2, m[5] - m[2], (cx, cy, (m[2] + m[5]) / 2), "z", 32)
    cam = box([cx - 30, cy - 12, m[5], cx + 30, cy + 12, m[5] + 30])
    cam += cyl(7, 4, (cx, cy - 13, m[5] + 15), "y", 24)
    return pole, cam


# ---------------------------------------------------------------------------
# The stock CR-10 V3 control box beside the frame (machine.js ctrlBox): x -360 to -70,
# y 70 to 280, 85 mm high (ESTIMATE), with the LCD bezel and the knob on the front face.

def control_box():
    x0, y0, w, d, h = -360.0, 70.0, 290.0, 210.0, 85.0
    tris = box([x0, y0, 0.0, x0 + w, y0 + d, h])
    tris += box([x0 + 40, y0 - 1, 44 - 26, x0 + 140, y0, 44 + 26])
    tris += cyl(9, 14, (x0 + 175, y0 - 7, 44.0), "y", 32)
    return tris


# ---------------------------------------------------------------------------
# The Y drag chain (wiring.js carrierPath, makeChain, updateChain) at machine home: a lower run
# on the table from the fixed end, a half circle, and an upper run to the left Y carriage.

def chain_path(ch, J):
    cy = J["carriage_y0"]
    f, m = ch["fixed"], ch["moving"]
    fa, fb, ma, mb = f["y"], f["z"], cy + m["dy"], m["z"]
    r = ch["bend_r"]
    sgn = 1 if ch["bend_side"].startswith("+") else -1
    ab = (ch["runs"] + fa + ma) / 2 if sgn > 0 else (fa + ma - ch["runs"]) / 2
    bc = (fb + mb) / 2
    L1, arc, L2 = abs(ab - fa), math.pi * r, abs(ma - ab)
    x = ch["plane"]["x"]

    def pt(s):
        s = min(max(s, 0.0), L1 + arc + L2)
        if s <= L1:
            return (x, fa + sgn * s, fb)
        s -= L1
        if s <= arc:
            ph = s / r
            return (x, ab + sgn * r * math.sin(ph), bc + (fb - bc) * math.cos(ph))
        s -= arc
        return (x, ab - sgn * min(s, L2), mb)

    return pt, L1, (x, fa, fb), (x, ma, mb)


def chain_link(a, b, h, w):
    """One link between the pivots a and b (wiring.js linkGeo, as boxes): the outer half plates,
    the inner half plates, the bottom bar and the lid bar. Local X along the link, Y across the
    bend, Z across the chain (frame x)."""
    T = unit(sub(b, a))
    N = unit(cross((1.0, 0.0, 0.0), T))
    Z = cross(T, N)
    p = math.sqrt(dot(sub(b, a), sub(b, a)))
    o = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
    axes = (T, N, Z)
    tris = []
    e, t = 0.8, 2.0
    for s in (-1, 1):
        zo = w / 2 - e - t if s > 0 else -w / 2 + e
        zi = w / 2 - e - 2 * t - 0.2 if s > 0 else -w / 2 + e + t + 0.2
        tris += obox(o, axes, (0.0, -h / 2, zo), (p / 2, h / 2, zo + t))
        tris += obox(o, axes, (-p / 2, -h / 2 + 0.6, zi), (0.0, h / 2 - 0.6, zi + t))
    bw, lw = (w - 2 * t - 1.6) / 2, (w - 1.6) / 2
    tris += obox(o, axes, (p / 4 - 3, -h / 2, -bw), (p / 4 + 3, -h / 2 + 2.2, bw))
    tris += obox(o, axes, (p / 4 - 3, h / 2 - 2.2, -lw), (p / 4 + 3, h / 2, lw))
    return tris


def chain_end(o, h, w, L):
    """An end link with its bracket (wiring.js endLinkGeo, as boxes). Local X along frame +y from
    0 to L, Y up (frame z), Z across the chain (frame x)."""
    axes = ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
    tris = obox(o, axes, (0.0, -h / 2, w / 2 - 2), (L, h / 2, w / 2))
    tris += obox(o, axes, (0.0, -h / 2, -w / 2), (L, h / 2, -w / 2 + 2))
    tris += obox(o, axes, (0.0, -h / 2, -(w - 4) / 2), (L + 8, -h / 2 + 2, (w - 4) / 2))
    for zc in (-(w - 4) / 2 + 2, (w - 4) / 2 - 2):
        tris += obox(o, axes, (L + 3, -h / 2 + 2, zc - 1), (L + 8, -h / 2 + 5, zc + 1))
    tris += obox(o, axes, (L - 6, h / 2 - 2, -(w - 4) / 2), (L - 1, h / 2, (w - 4) / 2))
    return tris


def drag_chain(J):
    """Returns (fixed, moving): the links on the lower run with the fixed end link, and the
    links round the bend and on the upper run with the moving end link."""
    ch = next(c for c in J["chains"] if c["axis"] == "y")
    h, w = ch["outer_hw"]
    el = ch.get("end_link", 12)
    body = ch["runs"] + math.pi * ch["bend_r"] - el / 2
    n = round(body / 18.0)  # 18 mm nominal pitch (stl/detail/manifest.json chain_link)
    pitch = body / n
    pt, L1, fixed_end, moving_end = chain_path(ch, J)
    fixed, moving = chain_end(fixed_end, h, w, el), chain_end(add(moving_end, (0.0, -el / 2, 0.0)), h, w, el)
    for i in range(n):
        link = chain_link(pt(i * pitch), pt((i + 1) * pitch), h, w)
        (fixed if (i + 0.5) * pitch <= L1 else moving).extend(link)
    return fixed, moving


# ---------------------------------------------------------------------------
# The servo loom (wiring.js loomPoints, fillet, resample, Sweep): a 1/2 inch split loom from the
# tie on the front of the X plate, up, back over the beam, and a free slack loop (catenary) to
# the tie on the head harness cable.

def catenary(s, ln):
    if s < 0.5:
        return 0.0, ln / 2
    if ln <= s:
        return math.inf, 0.0
    lo, hi = 1e-3, 1e7
    for _ in range(200):
        a = math.sqrt(lo * hi)
        if 2 * a * math.sinh(min(s / (2 * a), 700)) > ln:
            lo = a
        else:
            hi = a
    a = math.sqrt(lo * hi)
    return a, a * (math.cosh(s / (2 * a)) - 1)


def loom_points(ch, J, n=48):
    cy = J["carriage_y0"]
    xm, xf = J["carriage_x0"] + ch["moving"]["dx"], ch["fixed"]["x"]
    yl, zt = cy + ch["plane"]["dy"], ch["z"]
    yt, zt0 = cy + ch["moving"]["tie"]["dy"], ch["moving"]["tie"]["z"]
    pts = [(xm, yt, zt0), (xm, yt, zt), (xm, yl, zt)]
    a, sag = catenary(abs(xf - xm), ch["length"])
    if a == 0:
        return pts + [(xm, yl, zt - sag), (xf + 0.5, yl, zt - sag), (xf + 0.5, yl, zt)]
    xc = (xm + xf) / 2
    for i in range(1, n + 1):
        px = xm + (xf - xm) * i / n
        z = zt - sag + a * (math.cosh((px - xc) / a) - 1) if math.isfinite(a) else zt
        pts.append((px, yl, z))
    return pts


def fillet(P, r, seg=7):
    out = [P[0]]
    prev = P[0]
    for i in range(1, len(P) - 1):
        a, b = sub(P[i], prev), sub(P[i + 1], P[i])
        la, lb = math.sqrt(dot(a, a)), math.sqrt(dot(b, b))
        if la < 1e-6 or lb < 1e-6:
            continue
        d0, d1 = (a[0] / la, a[1] / la, a[2] / la), (b[0] / lb, b[1] / lb, b[2] / lb)
        th = math.acos(min(1.0, max(-1.0, dot(d0, d1))))
        if th < 1e-3:
            out.append(P[i])
            prev = P[i]
            continue
        t = min(r * math.tan(th / 2), la, lb / 2)
        rr = t / math.tan(th / 2)
        A0 = add(P[i], d0, -t)
        u = unit(add(d1, d0, -dot(d0, d1)))
        C = add(A0, u, rr)
        m = max(2, math.ceil(seg * th / (math.pi / 2)))
        for k in range(m + 1):
            ph = th * k / m
            out.append(add(add(C, u, -rr * math.cos(ph)), d0, rr * math.sin(ph)))
        prev = out[-1]
    out.append(P[-1])
    return out


def resample(pts, n):
    L = [0.0]
    for i in range(1, len(pts)):
        d = sub(pts[i], pts[i - 1])
        L.append(L[-1] + math.sqrt(dot(d, d)))
    out, j = [], 1
    for k in range(n):
        s = L[-1] * k / (n - 1)
        while j < len(pts) - 1 and L[j] < s:
            j += 1
        seg = (L[j] - L[j - 1]) or 1.0
        f = (s - L[j - 1]) / seg
        out.append(add(pts[j - 1], sub(pts[j], pts[j - 1]), f))
    return out


def sweep(pts, r, sides=10):
    """A closed tube of radius r along pts, with parallel transport of the frame (wiring.js
    Sweep) and flat end caps."""
    n = len(pts)
    rings, N = [], None
    for i in range(n):
        T = unit(sub(pts[min(i + 1, n - 1)], pts[max(i - 1, 0)]))
        if N is None:
            h = (0.0, 0.0, 1.0) if abs(T[2]) < 0.9 else (1.0, 0.0, 0.0)
            N = unit(add(h, T, -dot(h, T)))
        else:
            N = add(N, T, -dot(N, T))
            N = unit(N) if dot(N, N) > 1e-8 else unit(add((0.0, 0.0, 1.0), T, -T[2]))
        B = cross(T, N)
        rings.append([add(add(pts[i], N, r * math.cos(2 * math.pi * k / sides)), B, r * math.sin(2 * math.pi * k / sides))
                      for k in range(sides)])
    tris = []
    for i in range(n - 1):
        for k in range(sides):
            k1 = (k + 1) % sides
            tris += quad(rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k])
    for k in range(sides):
        k1 = (k + 1) % sides
        tris.append((pts[0], rings[0][k1], rings[0][k]))
        tris.append((pts[-1], rings[-1][k], rings[-1][k1]))
    return close(tris)


def servo_loom(J):
    ch = next(c for c in J["chains"] if c["name"] == "x")
    pts = resample(fillet(loom_points(ch, J), ch["d"]), 120)
    return sweep(pts, ch["d"] / 2, 10)


# ---------------------------------------------------------------------------
# The X endstop board on the X endstop wall of the left Y carriage. sim2 has the Y endstops
# only. The detail meshes (stl/detail/gantry_*.stl, export_context_detail.py) have the board.
# x_endstop() keeps the triangles inside the box round it.

X_ENDSTOP_BOX = (0.0, 35.0, 80.0, 45.0, 62.0, 115.0)
X_ENDSTOP_FILES = ("gantry_pcb_dark", "gantry_switch", "gantry_plunger", "gantry_nylon", "gantry_gold", "gantry_steel")


def read_stl(path):
    b = open(path, "rb").read()
    n = struct.unpack_from("<I", b, 80)[0]
    return [tuple(struct.unpack_from("<3f", b, 84 + i * 50 + 12 + k * 12) for k in range(3)) for i in range(n)]


def x_endstop():
    lo, hi = X_ENDSTOP_BOX[:3], X_ENDSTOP_BOX[3:]
    inside = lambda v: all(lo[a] < v[a] < hi[a] for a in range(3))
    tris = []
    for name in X_ENDSTOP_FILES:
        tris += [t for t in read_stl(os.path.join(HERE, "stl", "detail", name + ".stl")) if all(inside(v) for v in t)]
    return tris


# ---------------------------------------------------------------------------
# Output.

def q(v):
    return round(v, 4) + 0.0  # + 0.0 turns -0.0 into 0.0


def write_stl(name, tris):
    """Write a binary STL. The vertices are rounded to 0.0001 mm. Degenerate facets are left out."""
    recs = []
    for t in tris:
        a, b, c = (tuple(q(x) for x in v) for v in t)
        n = cross(sub(b, a), sub(c, a))
        ln = math.sqrt(dot(n, n))
        if ln < 1e-9:
            continue
        recs.append(struct.pack("<12fH", *(q(x / ln) for x in n), *a, *b, *c, 0))
    path = os.path.join(OUT, name)
    with open(path, "wb") as f:
        f.write(HEADER)
        f.write(struct.pack("<I", len(recs)))
        f.write(b"".join(recs))
    print(f"  stl/context/{name}: {len(recs)} facets")


def main():
    J = json.load(open(os.path.join(HERE, "stl", "frame.json")))
    os.makedirs(OUT, exist_ok=True)
    pole, cam = camera(J)
    chain_fixed, chain_moving = drag_chain(J)
    # The static parts.
    write_stl("frame.stl", frame(J))
    write_stl("feet.stl", feet(J))
    write_stl("y_belts.stl", y_belts(J))
    write_stl("drag_chain_fixed.stl", chain_fixed)
    write_stl("camera_pole.stl", pole)
    write_stl("webcam.stl", cam)
    write_stl("control_box.stl", control_box())
    # The gantry.
    write_stl("x_beam.stl", extrusion(J["beam"]["box"]))
    write_stl("y_wheels.stl", y_wheels(J))
    write_stl("x_belt.stl", x_belt(J))
    write_stl("x_endstop.stl", x_endstop())
    write_stl("drag_chain_moving.stl", chain_moving)
    write_stl("servo_loom.stl", servo_loom(J))
    # The carriage.
    write_stl("x_wheels.stl", x_wheels(J))


if __name__ == "__main__":
    main()
