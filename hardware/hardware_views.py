"""Write the hardware views of the Printdeck build: one exploded view for each group of printed
parts, with each heat-set insert, screw, nut, T-nut, spacer and wheel at its place.

Run from the hardware directory, after model.py:

    uv run --no-project --with build123d python hardware_views.py

The script writes the meshes to stl/hardware/<view>/, in frame coordinates (mm, Z up), at machine
home: the pose of stl/sim2/. It then writes the assemblies of the views into ../printdeck.yml,
between the two marker lines "# BEGIN hardware views" and "# END hardware views".

Each mesh file is one kind of item with one direction. In the exploded view, each item comes off
along its axis:

- a screw and a heat-set insert come out of their hole, the way they go in;
- an M3 nut comes up out of its trap;
- a nyloc nut, a T-nut, a spacer, a washer and a wheel come off the axis of their screw, away
  from the printed part.

The Printdeck generate step does not run this script. The meshes are committed files. Run it again
after a change to fasteners.py or to the parts.
"""
import json
import math
import os
import shutil
import struct
import sys

import fasteners as F
import parts as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stl", "hardware")
YML = os.path.join(HERE, "..", "printdeck.yml")
HEADER = b"penplotter hardware view, hardware/hardware_views.py".ljust(80, b" ")
BEGIN, END = "  # BEGIN hardware views", "  # END hardware views"

BRASS, STEEL, WHEEL, ACCENT = "#c9a23f", "#b8bcc2", "#1f1f22", "#7fb6e0"

# The views: the name, the printed parts (the Printdeck part, the sim2 mesh, the fastener part key),
# the bought parts to show, the wheels, and the description.
VIEWS = [
    ("left", "Y carriage, left: inserts and screws",
     [("Y carriage, left", "y_carriage_left", "y_carriage_left")],
     [], "y_left",
     "The left Y carriage with its hardware. Brass: the long M5 insert in the front outer wheel boss "
     "(press it in from the top), the two M3 inserts of the X endstop board, and one M3 insert in the "
     "ledge of each belt pocket. Move the explode slider to see each screw come out of its hole."),
    ("right", "Y carriage, right: inserts and screws",
     [("Y carriage, right", "y_carriage_right", "y_carriage_right"), ("X idler fork", "x_idler_fork", "x_idler_fork")],
     [], "y_right",
     "The right Y carriage and the X idler fork with their hardware. Brass: the long M5 insert in the "
     "front outer wheel boss (press it in from the top), and one M3 insert in the ledge of each belt "
     "pocket."),
    ("carriage", "X plate and pen carriage: inserts and screws",
     [("X plate", "x_carriage_plate", "x_carriage_plate"), ("Pen carriage", "pen_carriage", "pen_carriage"),
      ("Pen slider", "pen_slider", "pen_slider")],
     [("Servo", "servo", "#2f5da8")], "x",
     "The X plate, the pen carriage and the pen slider with their hardware. Brass: the long M5 insert "
     "in the bottom wheel boss of the X plate, and one M3 insert in the ledge of each belt pocket. The "
     "four M3 x 12 screws go from the back of the X plate into the pen carriage."),
    ("yfront", "Y front base, left: inserts and screws",
     [("Y front base, left", "y_front_left", "y_front_left"), ("Y idler bracket, left", "y_idler_bracket_left", "y_idler_bracket_left"),
      ("Y idler fork", "y_idler_fork_left", "y_idler_fork_left")],
     [], None,
     "The left front base, the idler bracket and the idler fork with their hardware. Brass: the two M3 "
     "inserts of the Y endstop board (press them in from the top). The M5 countersunk screw goes through "
     "the ear of the bracket into a T-nut in the front face slot of the bar. The right side is the mirror image."),
    ("ymotor", "Y motor bracket, left: screws",
     [("Y motor bracket, left", "y_motor_mount_left", "y_motor_mount_left")],
     [("Y motor", "y_stepper_left", "#202020")], None,
     "The left Y motor bracket with its screws and T-nuts. The right side is the mirror image."),
    ("anchor", "Y chain anchor: screws",
     [("Y chain anchor", "y_chain_anchor", "y_chain_anchor")], [], None,
     "The fixed end of the drag chain with its screws and T-nut."),
    ("foot", "Camera pole foot: screws",
     [("Camera pole foot", "mast_foot", "mast_foot")], [], None,
     "The camera pole foot with its screws, T-nuts and the collar nut."),
]

# The order of the items in a view. Printdeck moves the last item off first: the screws first,
# the inserts last.
ORDER = ["insert", "spacer", "eccentric", "washer", "wheel", "nut", "nyloc", "tnut", "clip", "screw"]


# ---------------------------------------------------------------- vectors

def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    n = math.sqrt(dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def neg(a):
    return (-a[0], -a[1], -a[2])


def centre(shape):
    c = shape.bounding_box().center()
    return (c.X, c.Y, c.Z)


def snap(d):
    """The direction rounded to 0.001, with -0.0 as 0."""
    return tuple(round(x, 3) + 0.0 for x in unit(d))


# ---------------------------------------------------------------- meshes

def q(v):
    return round(v, 4) + 0.0


def write_stl(path, shapes):
    """Write a binary STL of the shapes. The vertices are rounded to 0.0001 mm."""
    recs = []
    for s in shapes:
        verts, tris = s.tessellate(0.05, 0.3)
        pts = [(q(v.X), q(v.Y), q(v.Z)) for v in verts]
        for i, j, k in tris:
            a, b, c = pts[i], pts[j], pts[k]
            n = cross(sub(b, a), sub(c, a))
            ln = math.sqrt(dot(n, n))
            if ln < 1e-9:
                continue
            recs.append(struct.pack("<12fH", *(q(x / ln) for x in n), *a, *b, *c, 0))
    with open(path, "wb") as f:
        f.write(HEADER)
        f.write(struct.pack("<I", len(recs)))
        f.write(b"".join(recs))
    return len(recs)


# ---------------------------------------------------------------- directions

def axis_screw(f, screws):
    """The screw whose axis goes through the centre of the item f: (p, d, length), or None."""
    c = centre(f.solid)
    best = None
    for s in screws:
        p, d = s.meta["p"], unit(s.meta["d"])
        v = sub(c, p)
        t = dot(v, d)
        off = sub(v, tuple(x * t for x in d))
        r = math.sqrt(dot(off, off))
        if r < 1.5 and -60 < t < s.meta["length"] + 30 and (best is None or r < best[0]):
            best = (r, p, d)
    return best and best[1:]


def load_tris(path):
    """The triangles of a binary STL mesh."""
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack_from("<I", data, 80)[0]
    out = []
    for i in range(n):
        v = struct.unpack_from("<9f", data, 84 + i * 50 + 12)
        out.append((v[0:3], v[3:6], v[6:9]))
    return out


def ray_hits(o, d, tris, far=80.0):
    """True if the ray from o along d hits a triangle closer than far."""
    for a, b, c in tris:
        e1, e2 = sub(b, a), sub(c, a)
        h = cross(d, e2)
        det = dot(e1, h)
        if abs(det) < 1e-12:
            continue
        s = sub(o, a)
        u = dot(s, h) / det
        if u < 0 or u > 1:
            continue
        qv = cross(s, e1)
        v = dot(d, qv) / det
        if v < 0 or u + v > 1:
            continue
        t = dot(e2, qv) / det
        if 0.01 < t < far:
            return True
    return False


def direction(f, tris, screws):
    """The explode direction of the fastener f. tris are the triangles of the printed parts of the view."""
    if f.kind in ("screw", "insert") and "d" in f.meta:
        return snap(neg(f.meta["d"]))       # out of the hole, the way it goes in
    if f.kind == "nut":
        return (0.0, 0.0, 1.0)              # up out of its trap
    if f.kind == "clip":
        # A belt jaw: up out of a Y pocket, out of the back of an X pocket.
        return (0.0, 0.0, 1.0) if f.group == "gantry" else (0.0, 1.0, 0.0)
    c = centre(f.solid)
    if f.kind == "screw":
        # A screw with no axis data (the pen clamp screw): along its long side.
        bb = f.solid.bounding_box()
        size = (bb.size.X, bb.size.Y, bb.size.Z)
        k = size.index(max(size))
        a = tuple(1.0 if i == k else 0.0 for i in range(3))
        fallback = a
    else:
        hit = axis_screw(f, screws)
        if hit is None:
            return (0.0, 0.0, 1.0)
        a = hit[1]
        # A nut or a T-nut is at the far end of its screw. A spacer, a washer or a wheel is on the head side.
        fallback = a if f.kind in ("nyloc", "tnut") else neg(a)
    # The side with no printed part in the way. The rays start off the axis, clear of the screw hole.
    bb = f.solid.bounding_box()
    k = max(range(3), key=lambda i: abs(a[i]))
    r = 0.35 * min(x for i, x in enumerate((bb.size.X, bb.size.Y, bb.size.Z)) if i != k)
    u = unit(cross(a, (1.0, 0.0, 0.0) if k != 0 else (0.0, 1.0, 0.0)))
    w = cross(a, u)
    starts = [tuple(c[i] + r * (su * u[i] + sw * w[i]) for i in range(3)) for su, sw in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    free = [s for s in (a, neg(a)) if not any(ray_hits(o, s, tris) for o in starts)]
    return snap(free[0] if len(free) == 1 else fallback)


# ---------------------------------------------------------------- the views

def wheels(kind, c0, xp0):
    """The wheels of a view, as fastener-like records (kind "wheel")."""
    if kind == "y_left":
        ws = P.y_wheels(c0)
        part = "y_carriage_left"
    elif kind == "y_right":
        ws = [P.mirror_x(w) for w in P.y_wheels(c0)]
        part = "y_carriage_right"
    else:
        t = P.plate_offset(xp0, c0)
        ws = [t * w for w in P.x_wheels()]
        part = "x_carriage_plate"
    return [F.Fastener(f"wheel {i}", "V-wheel (stock)", "M5", "wheel", "", part, w) for i, w in enumerate(ws)]


def label(n, item):
    """The item name in the view, for example "2 x M3 x 8 socket head"."""
    return f"{n} x {item}" if n > 1 else item


def main():
    fr = json.load(open(os.path.join(HERE, "stl", "frame.json")))
    c0, xp0 = fr["carriage_y0"], fr["carriage_x0"]
    items, _ = F.build(c0, xp0)
    screws = [f for f in items if f.kind == "screw" and "d" in f.meta]
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    yml = []
    for key, title, printed, bought, wkind, desc in VIEWS:
        os.makedirs(os.path.join(OUT, key))
        yml += [f"  - name: {json.dumps(title)}", "    description: >-"]
        yml += wrap(desc, "      ")
        yml += ["    items:"]
        for pname, mesh, _ in printed:
            yml += [f"      - part: {pname}", f"        file: hardware/stl/sim2/{mesh}.stl"]
        for bname, mesh, col in bought:
            yml += [f"      - name: {json.dumps(bname)}", f"        file: hardware/stl/sim2/{mesh}.stl", f'        color: "{col}"']
        # The fasteners of the printed parts in the view, with their directions.
        groups = {}
        tris = [t for _, mesh, _ in printed for t in load_tris(os.path.join(HERE, "stl", "sim2", mesh + ".stl"))]
        for pname, mesh, fpart in printed:
            sel = [f for f in items if f.part == fpart and f.kind != "belt"]
            if wkind and fpart.startswith(("y_carriage", "x_carriage")):
                sel += wheels(wkind, c0, xp0)
            for f in sel:
                d = direction(f, tris, screws)
                g = groups.setdefault((ORDER.index(f.kind), f.item, d), [])
                g.append(f)
        last = None
        for (o, item, d), fs in sorted(groups.items()):
            kind = ORDER[o]
            name = label(len(fs), item)
            fn = slug(f"{kind}-{item}") + "-" + dcode(d) + ".stl"
            nf = write_stl(os.path.join(OUT, key, fn), [f.solid for f in fs])
            print(f"  stl/hardware/{key}/{fn}: {len(fs)} items, {nf} facets, {[f.name for f in fs]}")
            # Two neighbours with the same direction move as one unit in Printdeck. A tiny turn keeps
            # each kind apart.
            if last == d:
                d = tuple(round(x * 0.999, 4) + 0.0 for x in d) if kind != "screw" else d
            last = d
            col = BRASS if kind == "insert" else WHEEL if kind == "wheel" else ACCENT if kind == "clip" else STEEL
            yml += [f"      - name: {json.dumps(name)}", f"        file: hardware/stl/hardware/{key}/{fn}",
                    f'        color: "{col}"', f"        explode: [{', '.join(f'{x:g}' for x in d)}]"]
    patch_yml(yml)


def dcode(d):
    """A short name of a direction: "zp" is +Z, "yn" is -Y. Other directions get the numbers."""
    for k, ax in enumerate("xyz"):
        if abs(abs(d[k]) - 1) < 1e-6:
            return ax + ("p" if d[k] > 0 else "n")
    return "_".join(f"{x:+.3f}".replace("+", "p").replace("-", "n").replace(".", "") for x in d)


def slug(s):
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in s)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def wrap(text, indent, width=100):
    lines, cur = [], indent
    for w in text.split():
        if len(cur) + len(w) + 1 > width and cur.strip():
            lines.append(cur.rstrip())
            cur = indent
        cur += w + " "
    lines.append(cur.rstrip())
    return lines


def patch_yml(lines):
    """Put the view assemblies between the marker lines of printdeck.yml."""
    with open(YML) as f:
        text = f.read().split("\n")
    if BEGIN in text:
        a, b = text.index(BEGIN), text.index(END)
        text = text[:a] + text[b + 1:]
    else:
        a = len(text) - 1 if text[-1] == "" else len(text)
    text = text[:a] + [BEGIN] + lines + [END] + text[a:]
    with open(YML, "w") as f:
        f.write("\n".join(text))
    print(f"printdeck.yml: {len(VIEWS)} hardware views")


if __name__ == "__main__":
    sys.exit(main())
