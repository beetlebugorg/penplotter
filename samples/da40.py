#!/usr/bin/env python3
"""Write samples/da40.gcode and samples/da40.svg: a three-view blueprint of a 2010 Diamond DA40 XLS
with the air conditioning condenser scoop under the belly, for a Letter sheet.

The views are the top view, the left side view and the front view at 1:65, with dimension lines and
a title block. The published values are the span (11.94 m), the length (8.06 m), the height
(1.97 m) and the wing area (13.54 m2). All other shapes are estimates from photos and are
approximate. The A/C scoop is drawn retracted, with the open position dashed.

Put the Letter sheet in portrait with its lower left corner at machine X 14.5, Y 20.
The drawing stays below machine Y 290, out of the pen rack area.

Run: uv run --no-project --with Hershey-Fonts python samples/da40.py
"""

import math
import os

from HersheyFonts import HersheyFonts

HERE = os.path.dirname(os.path.abspath(__file__))

SHEET_W, SHEET_H = 200.0, 260.0          # the drawing area inside the paper margins
X0, Y0 = 22.5, 29.7                       # machine position of the lower left corner of the drawing area
FEED, TRAVEL = 3000, 6000                 # mm/min
S = 1000.0 / 65.0                         # sheet mm for each aircraft metre (1:65)

strokes = []                              # each stroke is a list of (x, y) in sheet mm


# ---------------------------------------------------------------- drawing helpers
def line(x1, y1, x2, y2):
    strokes.append([(x1, y1), (x2, y2)])


def poly(pts, closed=False):
    pts = list(pts)
    if closed:
        pts.append(pts[0])
    strokes.append(pts)


def rect(x, y, w, h):
    poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], closed=True)


def circle(cx, cy, r, n=None):
    n = n or max(16, int(2 * math.pi * r / 0.8))
    poly([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)], closed=True)


def dashed_poly(pts, dash=1.6, gap=1.0, dot=False):
    """A dashed polyline. dot=True gives a centre line (long dash, short dash)."""
    pattern = [5.0, 1.0, 0.7, 1.0] if dot else [dash, gap]
    i, left = 0, pattern[0]
    cur = [pts[0]]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        s = 0.0
        while seg - s > 1e-9:
            step = min(left, seg - s)
            s += step
            left -= step
            p = (x1 + (x2 - x1) * s / seg, y1 + (y2 - y1) * s / seg)
            if i % 2 == 0:
                cur.append(p)
            if left <= 1e-9:
                if i % 2 == 0 and len(cur) > 1:
                    strokes.append(cur)
                i += 1
                left = pattern[i % len(pattern)]
                cur = [p]
    if i % 2 == 0 and len(cur) > 1:
        strokes.append(cur)


def smooth(pts, n=8):
    """A Catmull-Rom curve through the points."""
    if len(pts) < 3:
        return list(pts)
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1])
    return out


FONT = HersheyFonts()
FONT.load_default_font("futural")


def text(s, x, y, h=3.0, angle=0.0, align="left"):
    """Single-stroke text. h is the cap height in mm."""
    FONT.normalize_rendering(h)
    segs = list(FONT.lines_for_text(s))
    if not segs:
        return
    width = max(max(a[0], b[0]) for a, b in segs)
    dx = {"left": 0.0, "center": -width / 2, "right": -width}[align]
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    cur = None
    for (ax, ay), (bx, by) in segs:
        ax += dx
        bx += dx
        p = (x + ax * ca - ay * sa, y + ax * sa + ay * ca)
        q = (x + bx * ca - by * sa, y + bx * sa + by * ca)
        if cur and math.hypot(cur[-1][0] - p[0], cur[-1][1] - p[1]) < 1e-6:
            cur.append(q)
        else:
            cur = [p, q]
            strokes.append(cur)


def arrow(x, y, ux, uy, size=1.8):
    """A closed arrow head at (x, y), pointing along (ux, uy)."""
    a = math.atan2(uy, ux) + math.pi
    l = (x + size * math.cos(a + math.radians(16)), y + size * math.sin(a + math.radians(16)))
    r = (x + size * math.cos(a - math.radians(16)), y + size * math.sin(a - math.radians(16)))
    poly([l, (x, y), r, l])


def dim_h(x1, x2, y, label, ext_from=None, h=2.2, tx=None):
    """A horizontal dimension at height y, with extension lines from ext_from."""
    if ext_from is not None:
        e = 1.2 if y > ext_from else -1.2
        line(x1, ext_from + (0.8 if y > ext_from else -0.8), x1, y + e)
        line(x2, ext_from + (0.8 if y > ext_from else -0.8), x2, y + e)
    line(x1, y, x2, y)
    arrow(x1, y, -1, 0)
    arrow(x2, y, 1, 0)
    text(label, (x1 + x2) / 2 if tx is None else tx, y + 1.0, h, align="center")


def dim_v(y1, y2, x, label, ext_from=None, h=2.2):
    if ext_from is not None:
        e = 1.2 if x > ext_from else -1.2
        line(ext_from + (0.8 if x > ext_from else -0.8), y1, x + e, y1)
        line(ext_from + (0.8 if x > ext_from else -0.8), y2, x + e, y2)
    line(x, y1, x, y2)
    arrow(x, y1, 0, -1)
    arrow(x, y2, 0, 1)
    text(label, x + 1.0 + h, (y1 + y2) / 2, h, angle=90, align="center")


def mirror(pts):
    """The right half (y >= 0) of an outline, closed with its mirror image."""
    return list(pts) + [(x, -y) for x, y in reversed(pts)]


# ---------------------------------------------------------------- sheet and title block
rect(0, 0, SHEET_W, SHEET_H)
rect(4, 4, SHEET_W - 8, SHEET_H - 8)
for i in range(1, 4):                     # zone marks on the border
    zx = 4 + i * (SHEET_W - 8) / 4
    line(zx, 0, zx, 4)
    line(zx, SHEET_H - 4, zx, SHEET_H)
for i in range(1, 5):
    zy = 4 + i * (SHEET_H - 8) / 5
    line(0, zy, 4, zy)
    line(SHEET_W - 4, zy, SHEET_W, zy)

tb_y = 30.0                               # the top of the title block
line(4, tb_y, SHEET_W - 4, tb_y)
line(4, 17, SHEET_W - 4, 17)
line(136, 4, 136, 17)
line(136, 17, 136, tb_y)
text("DIAMOND DA40 XLS  (2010)", 8, 21.5, 4.6)
text("THREE-VIEW", 140, 24.5, 2.4)
text("WITH A/C SCOOP", 140, 20.0, 2.4)
text("SPAN 11.94 M   LENGTH 8.06 M   HEIGHT 1.97 M   WING 13.54 M2", 8, 11.5, 2.1)
text("SHAPES APPROXIMATE. NOT FOR CONSTRUCTION.", 8, 6.5, 2.1)
text("SCALE 1:65", 140, 11.5, 2.2)
text("DWG DA40-AC  SHT 1/1", 140, 6.5, 2.2)

# ---------------------------------------------------------------- the aircraft (metres)
# x: aft from the spinner tip. y: to the right wing. z: up from the ground.
LEN, SPAN, HEIGHT = 8.06, 11.94, 1.97
HALF = SPAN / 2

# Fuselage half width in the top view.
FUS_TOP = [(0.0, 0.0), (0.06, 0.09), (0.18, 0.15), (0.35, 0.18), (0.42, 0.30), (0.8, 0.45), (1.2, 0.53),
           (1.6, 0.58), (2.2, 0.61), (2.9, 0.61), (3.5, 0.57), (4.3, 0.45), (5.3, 0.31), (6.3, 0.19),
           (7.1, 0.12), (7.7, 0.07), (7.95, 0.0)]
# Wing (right half): root at the fuselage side, slight taper, small winglet.
W_ROOT_Y, W_ROOT_LE, W_ROOT_TE = 0.60, 1.95, 3.37
W_TIP_LE, W_TIP_TE = 2.07, 2.92
DIHEDRAL = math.radians(5.0)
# Horizontal tail on top of the fin (T-tail).
HT_HALF, HT_ROOT_LE, HT_ROOT_TE, HT_TIP_LE, HT_TIP_TE = 1.53, 7.25, 7.97, 7.42, 7.92
HT_Z = 1.95
PROP_R, PROP_Z = 0.90, 1.15               # MT 3-blade propeller, about 1.8 m
TRACK, MAIN_X, NOSE_X = 2.97, 2.95, 0.95
# A/C condenser scoop under the belly, behind the wing.
AC_X0, AC_X1, AC_HW = 3.55, 4.40, 0.20


def wing_le(y):
    return W_ROOT_LE + (W_TIP_LE - W_ROOT_LE) * (y - W_ROOT_Y) / (HALF - W_ROOT_Y)


def wing_te(y):
    return W_ROOT_TE + (W_TIP_TE - W_ROOT_TE) * (y - W_ROOT_Y) / (HALF - W_ROOT_Y)


def ht_le(y):
    return HT_ROOT_LE + (HT_TIP_LE - HT_ROOT_LE) * y / HT_HALF


def ht_te(y):
    return HT_ROOT_TE + (HT_TIP_TE - HT_ROOT_TE) * y / HT_HALF


# ---------------------------------------------------------------- top view (nose up)
TOP_NOSE_Y = 250.0


def TP(x, y):
    return 100.0 + y * S, TOP_NOSE_Y - x * S


def tpoly(pts, closed=False):
    poly([TP(*p) for p in pts], closed)


def tdash(pts, **kw):
    dashed_poly([TP(*p) for p in pts], **kw)


fus = smooth(FUS_TOP)
tpoly(mirror(fus), closed=True)
tpoly([(0.35, -0.18), (0.35, 0.18)])                 # spinner joint
tpoly([(1.45, -0.57), (1.45, 0.57)])                 # cowl joint
# Propeller blade, edge on.
tpoly([(0.30, -PROP_R), (0.27, -0.2), (0.27, 0.2), (0.30, PROP_R), (0.34, 0.2), (0.34, -0.2), (0.30, -PROP_R)])
# Canopy and rear window.
can = smooth([(1.52, 0.0), (1.62, 0.36), (1.95, 0.52), (2.6, 0.55), (3.3, 0.50), (3.68, 0.30), (3.78, 0.0)])
tpoly(mirror(can), closed=True)
tpoly([(2.85, -0.545), (2.85, 0.545)])
tpoly([(3.30, -0.50), (3.30, 0.50)])
for sgn in (1, -1):
    # Wing outline with a rounded tip and a small winglet.
    tip = [(wing_le(HALF - 0.08), HALF - 0.08), (W_TIP_LE + 0.06, HALF - 0.01), (W_TIP_LE + 0.25, HALF),
           (W_TIP_TE - 0.05, HALF), (W_TIP_TE, HALF - 0.05)]
    pts = [(W_ROOT_LE, W_ROOT_Y)] + tip + [(W_ROOT_TE, W_ROOT_Y)]
    tpoly([(x, sgn * y) for x, y in pts])
    # Flap and aileron: hinge line at 76 % of the chord.
    def hinge(y):
        return wing_le(y) + 0.76 * (wing_te(y) - wing_le(y))
    for y0, y1 in ((W_ROOT_Y + 0.02, 3.45), (3.55, 5.55)):
        tpoly([(wing_te(y0), sgn * y0), (hinge(y0), sgn * y0), (hinge(y1), sgn * y1), (wing_te(y1), sgn * y1)])
    tpoly([(wing_te(3.50), sgn * 3.50), (hinge(3.50), sgn * 3.50)])
    # Main wheel fairing, under the wing (hidden).
    tdash([(MAIN_X - 0.36, sgn * (TRACK / 2 - 0.10)), (MAIN_X + 0.40, sgn * (TRACK / 2 - 0.10)),
           (MAIN_X + 0.40, sgn * (TRACK / 2 + 0.10)), (MAIN_X - 0.36, sgn * (TRACK / 2 + 0.10)),
           (MAIN_X - 0.36, sgn * (TRACK / 2 - 0.10))])
    # Horizontal tail and elevator hinge.
    tpoly([(x, sgn * y) for x, y in [(HT_ROOT_LE, 0.07), (ht_le(HT_HALF - 0.05), HT_HALF - 0.05), (HT_TIP_LE + 0.08, HT_HALF),
                                     (HT_TIP_TE - 0.04, HT_HALF), (ht_te(HT_HALF), HT_HALF - 0.04), (HT_ROOT_TE, 0.07)]])
    tpoly([(ht_le(y) + 0.62 * (ht_te(y) - ht_le(y)), sgn * y) for y in (0.10, HT_HALF - 0.04)])
tpoly([(HT_ROOT_LE, -0.07), (HT_ROOT_LE - 0.05, 0.0), (HT_ROOT_LE, 0.07)])
tpoly([(HT_ROOT_TE, -0.05), (LEN, 0.0), (HT_ROOT_TE, 0.05)])  # rudder behind the elevator
# A/C scoop under the belly (hidden).
tdash([(AC_X0, -AC_HW), (AC_X1, -AC_HW * 0.7), (AC_X1, AC_HW * 0.7), (AC_X0, AC_HW), (AC_X0, -AC_HW)])
# Centre line.
dashed_poly([TP(-0.15, 0), TP(LEN + 0.15, 0)], dot=True)
# Span dimension, under the wing tips.
tl, tt = TP(W_TIP_TE, -HALF)
tr, _ = TP(W_TIP_TE, HALF)
dim_h(tl, tr, TP(W_ROOT_TE, 0)[1] - 5.0, "11.94 M  (39 FT 2 IN)", ext_from=tt, tx=150.0)
text("TOP VIEW", 8.0, 132.0, 3.0)

# ---------------------------------------------------------------- left side view (nose left)
SIDE_GROUND = 87.0
SIDE_NOSE_X = 100.0 - LEN * S / 2


def SP(x, z):
    return SIDE_NOSE_X + x * S, SIDE_GROUND + z * S


def spoly(pts, closed=False):
    poly([SP(*p) for p in pts], closed)


def sdash(pts, **kw):
    dashed_poly([SP(*p) for p in pts], **kw)


top_line = smooth([(0.0, 1.14), (0.08, 1.25), (0.35, 1.31), (0.7, 1.37), (1.1, 1.41), (1.5, 1.43), (1.95, 1.62),
                   (2.45, 1.72), (3.0, 1.72), (3.55, 1.61), (3.9, 1.47), (4.7, 1.36), (5.7, 1.26), (6.6, 1.20)])
bot_line = smooth([(0.0, 1.14), (0.08, 1.03), (0.35, 0.97), (0.5, 0.87), (0.9, 0.72), (1.3, 0.62), (1.8, 0.57),
                   (3.4, 0.57), (4.4, 0.68), (5.6, 0.86), (6.8, 1.02), (7.6, 1.12), (7.92, 1.15)])
spoly(top_line)
spoly(bot_line)
# Fin and rudder.
spoly([(6.6, 1.20), (7.36, 1.92)])
spoly([(7.97, 1.93), (8.03, 1.40), (LEN, 1.22), (7.92, 1.15)])
spoly([(7.80, 1.92), (7.76, 1.16)])                  # rudder hinge
# Horizontal tail, edge on.
spoly(smooth([(7.25, HT_Z - 0.005), (7.33, 1.965), (7.6, 1.97), (7.97, 1.955)]) +
      smooth([(7.97, 1.945), (7.6, 1.925), (7.33, 1.928), (7.25, HT_Z - 0.005)]))
# Joints, canopy frame, windows.
spoly([(0.35, 0.97), (0.35, 1.31)])
spoly([(1.45, 0.61), (1.45, 1.43)])
spoly([(1.50, 1.42), (3.85, 1.42)])                  # canopy sill
spoly([(2.85, 1.42), (2.85, 1.72)])                  # front canopy to rear window
spoly(smooth([(3.05, 1.45), (3.05, 1.66), (3.40, 1.63), (3.65, 1.52), (3.65, 1.45), (3.05, 1.45)], 4))
spoly(smooth([(0.55, 0.86), (0.62, 0.80), (0.80, 0.78)], 4))  # cowl inlet
# Propeller blade, edge on, and spinner.
spoly([(0.30, PROP_Z - PROP_R), (0.27, PROP_Z - 0.2), (0.27, PROP_Z + 0.2), (0.30, PROP_Z + PROP_R),
       (0.34, PROP_Z + 0.2), (0.34, PROP_Z - 0.2), (0.30, PROP_Z - PROP_R)])
# Wing root section.
spoly(smooth([(W_ROOT_LE, 0.65), (2.05, 0.72), (2.4, 0.77), (2.8, 0.76), (W_ROOT_TE, 0.68)]) +
      smooth([(W_ROOT_TE, 0.67), (2.8, 0.62), (2.3, 0.60), (2.02, 0.61), (W_ROOT_LE, 0.65)]))
# Main gear: wheel fairing, wheel (hidden), spring leg.
mx, mr = MAIN_X, 0.19
spoly(smooth([(mx - 0.38, 0.20), (mx - 0.30, 0.34), (mx - 0.05, 0.42), (mx + 0.25, 0.37), (mx + 0.42, 0.24),
              (mx + 0.25, 0.08), (mx - 0.05, 0.03), (mx - 0.30, 0.08), (mx - 0.38, 0.20)], 5))
sdash([(mx + mr * math.cos(a / 24 * 2 * math.pi), mr + mr * math.sin(a / 24 * 2 * math.pi)) for a in range(25)])
spoly([(mx - 0.04, 0.42), (mx - 0.22, 0.59)])
spoly([(mx + 0.06, 0.41), (mx - 0.12, 0.58)])
# Nose gear.
nx, nr = NOSE_X, 0.17
spoly(smooth([(nx - 0.28, 0.18), (nx - 0.20, 0.31), (nx, 0.37), (nx + 0.22, 0.32), (nx + 0.30, 0.20),
              (nx + 0.18, 0.06), (nx, 0.02), (nx - 0.20, 0.06), (nx - 0.28, 0.18)], 5))
sdash([(nx + nr * math.cos(a / 24 * 2 * math.pi), nr + nr * math.sin(a / 24 * 2 * math.pi)) for a in range(25)])
spoly([(nx - 0.03, 0.37), (nx - 0.03, 0.69)])
spoly([(nx + 0.04, 0.36), (nx + 0.04, 0.70)])
# A/C condenser scoop: retracted (solid) and open (dashed).
spoly(smooth([(AC_X0, 0.585), (AC_X0 + 0.04, 0.50), (3.9, 0.49), (4.2, 0.53), (AC_X1, 0.675)], 5))
spoly([(AC_X0 + 0.04, 0.50), (AC_X0 + 0.07, 0.585)])   # intake lip
sdash([(AC_X0 + 0.04, 0.50), (AC_X0 + 0.02, 0.40), (3.9, 0.41), (4.25, 0.50), (AC_X1, 0.675)])
# Callout to the scoop.
ax_, az_ = SP(3.95, 0.47)
line(ax_, az_, ax_ + 9, az_ - 1.5)
circle(ax_, az_, 0.4, 8)
text("A/C CONDENSER SCOOP", ax_ + 10, az_ - 1.0, 2.0)
text("(DASHED: OPEN)", ax_ + 10, az_ - 4.6, 1.8)
# Ground line and prop axis.
dashed_poly([SP(-0.2, 0), SP(LEN + 0.25, 0)], dash=4.0, gap=1.2)
dashed_poly([SP(-0.25, PROP_Z), SP(1.0, PROP_Z)], dot=True)
# Length and height dimensions.
nl, ng = SP(0, 0)
nr_, _ = SP(LEN, 0)
dim_h(nl, nr_, ng - 7.0, "8.06 M  (26 FT 5 IN)", ext_from=ng)
hx, hz = SP(LEN, HEIGHT)
dim_v(ng, hz, hx + 8.0, "1.97 M", ext_from=hx)
line(hx + 0.8, ng, hx + 9.2, ng)                      # lower extension line from the ground
text("LEFT SIDE VIEW", 8.0, 113.0, 3.0)

# ---------------------------------------------------------------- front view
FRONT_GROUND = 40.0


def FP(y, z):
    return 100.0 + y * S, FRONT_GROUND + z * S


def fpoly(pts, closed=False):
    poly([FP(*p) for p in pts], closed)


def fdash(pts, **kw):
    dashed_poly([FP(*p) for p in pts], **kw)


sec = smooth([(0.0, 1.72), (0.33, 1.67), (0.52, 1.50), (0.60, 1.30), (0.61, 1.05), (0.56, 0.76), (0.41, 0.60), (0.0, 0.57)])
fpoly(sec + [(-y, z) for y, z in reversed(sec)])
fpoly(smooth([(-0.47, 1.42), (-0.30, 1.48), (0.0, 1.50), (0.30, 1.48), (0.47, 1.42)], 4))  # canopy sill
cowl = smooth([(0.0, 1.43), (0.36, 1.36), (0.47, 1.12), (0.42, 0.84), (0.25, 0.70), (0.0, 0.68)])
fpoly(cowl + [(-y, z) for y, z in reversed(cowl)])
fpoly([(0.17 * math.cos(a / 24 * 2 * math.pi), PROP_Z + 0.17 * math.sin(a / 24 * 2 * math.pi)) for a in range(25)])
fdash([(PROP_R * math.cos(a / 72 * 2 * math.pi), PROP_Z + PROP_R * math.sin(a / 72 * 2 * math.pi)) for a in range(73)], dash=2.0, gap=1.2)
for k in range(3):                         # three blades, edge on
    a = math.radians(90 + 120 * k)
    ca_, sa_ = math.cos(a), math.sin(a)
    blade = [(0.17, 0.0), (0.30, 0.05), (PROP_R, 0.015), (PROP_R, -0.015), (0.30, -0.04), (0.17, 0.0)]
    fpoly([(r * ca_ - w * sa_, PROP_Z + r * sa_ + w * ca_) for r, w in blade])
for sgn in (1, -1):
    tip_low = 0.62 + (HALF - W_ROOT_Y) * math.tan(DIHEDRAL)
    wing = [(W_ROOT_Y, 0.75), (HALF - 0.06, tip_low + 0.08), (HALF - 0.02, tip_low + 0.24), (HALF + 0.01, tip_low + 0.25),
            (HALF + 0.02, tip_low + 0.05), (HALF - 0.02, tip_low), (W_ROOT_Y, 0.62)]
    fpoly([(sgn * y, z) for y, z in wing])
    # Main gear spring leg and wheel fairing.
    wy = sgn * TRACK / 2
    fpoly([(sgn * 0.50, 0.63), (wy - sgn * 0.06, 0.36)])
    fpoly([(sgn * 0.50, 0.58), (wy - sgn * 0.06, 0.30)])
    fpoly(smooth([(wy - 0.10, 0.20), (wy - 0.09, 0.36), (wy, 0.42), (wy + 0.09, 0.36), (wy + 0.10, 0.20),
                  (wy + 0.08, 0.06), (wy, 0.03), (wy - 0.08, 0.06), (wy - 0.10, 0.20)], 4))
    # Horizontal tail.
    fpoly([(sgn * 0.05, 1.93), (sgn * HT_HALF, 1.935), (sgn * (HT_HALF + 0.01), 1.955), (sgn * 0.05, 1.97)])
fpoly([(-0.04, 1.72), (-0.04, 1.93)])                 # fin above the canopy
fpoly([(0.04, 1.72), (0.04, 1.93)])
fpoly(smooth([(-0.09, 0.18), (-0.08, 0.32), (0.0, 0.37), (0.08, 0.32), (0.09, 0.18), (0.07, 0.05), (0.0, 0.02),
              (-0.07, 0.05), (-0.09, 0.18)], 4))      # nose wheel fairing
fpoly([(-0.03, 0.37), (-0.03, 0.68)])
fpoly([(0.03, 0.37), (0.03, 0.68)])
# A/C scoop, front on: the intake opening under the belly.
fpoly([(-AC_HW, 0.585), (-AC_HW, 0.50), (AC_HW, 0.50), (AC_HW, 0.585)])
fpoly([(-AC_HW + 0.04, 0.575), (-AC_HW + 0.04, 0.53), (AC_HW - 0.04, 0.53), (AC_HW - 0.04, 0.575)])
dashed_poly([FP(-HALF - 0.3, 0), FP(HALF + 0.3, 0)], dash=4.0, gap=1.2)
dashed_poly([FP(0, -0.15), FP(0, 2.15)], dot=True)
text("FRONT VIEW", 8.0, 68.0, 3.0)
text("PROP 1.80 M", FP(1.0, 1.50)[0], FP(1.0, 1.50)[1], 1.8)


# ---------------------------------------------------------------- G-code and SVG
def order(strokes):
    """Greedy nearest stroke, reversing a stroke when its end is nearer."""
    left = [s for s in strokes if len(s) >= 2]
    out, pos = [], (0.0, 0.0)
    while left:
        best, bi, rev = None, 0, False
        for i, s in enumerate(left):
            for r, p in ((False, s[0]), (True, s[-1])):
                d = (p[0] - pos[0]) ** 2 + (p[1] - pos[1]) ** 2
                if best is None or d < best:
                    best, bi, rev = d, i, r
        s = left.pop(bi)
        s = s[::-1] if rev else s
        out.append(s)
        pos = s[-1]
    return out


def dedupe(s):
    out = [s[0]]
    for p in s[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= 0.02:
            out.append(p)
    return out


def gcode(ordered):
    draw = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for s in ordered for a, b in zip(s, s[1:]))
    travel, pos = 0.0, (0.0, 0.0)
    for s in ordered:
        travel += math.hypot(s[0][0] - pos[0], s[0][1] - pos[1])
        pos = s[-1]
    minutes = draw / FEED + travel / TRAVEL + len(ordered) * 2 * 0.15 / 60
    out = ["; Diamond DA40 XLS (2010) with A/C scoop, three-view at 1:65, Letter sheet",
           f"; Letter portrait, lower left corner at X{X0 - 8:.1f} Y{Y0 - 9.7:.1f}. Drawing {SHEET_W:.0f} x {SHEET_H:.0f} mm.",
           f"; {len(ordered)} strokes, {draw / 1000:.2f} m of line, about {minutes:.0f} min.",
           "G21", "G90", "M5", "G28"]
    n = len(ordered)
    for i, s in enumerate(ordered):
        if i % max(1, n // 20) == 0:
            out.append(f"M73 P{100 * i // n}")
        x, y = s[0]
        out.append(f"G0 X{X0 + x:.2f} Y{Y0 + y:.2f}")
        out.append("M3")
        for j, (x, y) in enumerate(s[1:]):
            out.append(f"G1 X{X0 + x:.2f} Y{Y0 + y:.2f}" + (f" F{FEED}" if j == 0 else ""))
        out.append("M5")
    out += ["M73 P100", f"G0 X{X0:.1f} Y330", "M400"]
    return "\n".join(out) + "\n", draw, minutes


def svg(ordered):
    w, h = SHEET_W + 16, SHEET_H + 19.4
    body = "".join('<polyline points="' + " ".join(f"{x + 8:.2f},{h - (y + 9.7):.2f}" for x, y in s) + '"/>' for s in ordered)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 4:.0f}" height="{h * 4:.0f}" viewBox="0 0 {w:.1f} {h:.1f}">'
            f'<rect width="100%" height="100%" fill="#1d4f91"/>'
            f'<g fill="none" stroke="#eef4ff" stroke-width="0.3" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>\n')


if __name__ == "__main__":
    ordered = order([dedupe(s) for s in strokes])
    ordered = [s for s in ordered if len(s) >= 2]
    xs = [p[0] for s in ordered for p in s]
    ys = [p[1] for s in ordered for p in s]
    assert min(xs) >= -0.01 and max(xs) <= SHEET_W + 0.01 and min(ys) >= -0.01 and max(ys) <= SHEET_H + 0.01, "outside the sheet"
    code, draw, minutes = gcode(ordered)
    with open(os.path.join(HERE, "da40.gcode"), "w") as fh:
        fh.write(code)
    with open(os.path.join(HERE, "da40.svg"), "w") as fh:
        fh.write(svg(ordered))
    print(f"wrote samples/da40.gcode and samples/da40.svg: {len(ordered)} strokes, {draw / 1000:.2f} m, about {minutes:.0f} min")
    print(f"machine X {X0 + min(xs):.1f}..{X0 + max(xs):.1f}, Y {Y0 + min(ys):.1f}..{Y0 + max(ys):.1f}")
