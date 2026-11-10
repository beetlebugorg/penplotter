#!/usr/bin/env python3
"""Write samples/blueprint.gcode: a blueprint of the pen plotter, for a Letter sheet.

The sheet has a border, a title block, the top view of the plotter at 1:3 with dimension lines,
a section of a Y rail at 1:1, and notes. The text uses a Hershey single-stroke font.

Run: uv run --no-project --with Hershey-Fonts python samples/blueprint.py
"""

import math
import os

from HersheyFonts import HersheyFonts

HERE = os.path.dirname(os.path.abspath(__file__))

# The sheet on the machine: Letter portrait, centred in the travel (250 x 395 mm).
SHEET_W, SHEET_H = 200.0, 260.0          # the drawing area inside the paper margins
X0, Y0 = 25.0, 67.5                       # machine position of the lower left corner of the drawing area
FEED, TRAVEL = 3000, 6000

strokes = []                              # each stroke is a list of (x, y) in sheet mm


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
    n = n or max(16, int(2 * math.pi * r / 1.0))
    poly([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)], closed=True)


def dashed(x1, y1, x2, y2, dash=3.0, gap=1.5, dot=False):
    """A dashed line. dot=True gives a centre line (long dash, short dash)."""
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    pattern = [6.0, 1.2, 0.8, 1.2] if dot else [dash, gap]
    s, i = 0.0, 0
    while s < length:
        seg = min(pattern[i % len(pattern)], length - s)
        if i % 2 == 0:
            line(x1 + ux * s, y1 + uy * s, x1 + ux * (s + seg), y1 + uy * (s + seg))
        s += seg
        i += 1


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


def arrow(x, y, ux, uy, size=2.0):
    """An open arrow head at (x, y), pointing along (ux, uy)."""
    for s in (1, -1):
        a = math.atan2(uy, ux) + math.pi + s * math.radians(18)
        line(x, y, x + size * math.cos(a), y + size * math.sin(a))


def dim_h(x1, x2, y, label, ext_from=None, h=2.5):
    """A horizontal dimension at height y, with extension lines from ext_from."""
    if ext_from is not None:
        line(x1, ext_from, x1, y + (1.5 if y > ext_from else -1.5))
        line(x2, ext_from, x2, y + (1.5 if y > ext_from else -1.5))
    line(x1, y, x2, y)
    arrow(x1, y, -1, 0)
    arrow(x2, y, 1, 0)
    text(label, (x1 + x2) / 2, y + 1.2, h, align="center")


def dim_v(y1, y2, x, label, ext_from=None, h=2.5):
    if ext_from is not None:
        line(ext_from, y1, x + (1.5 if x > ext_from else -1.5), y1)
        line(ext_from, y2, x + (1.5 if x > ext_from else -1.5), y2)
    line(x, y1, x, y2)
    arrow(x, y1, 0, -1)
    arrow(x, y2, 0, 1)
    text(label, x - 1.2, (y1 + y2) / 2, h, angle=90, align="center")


# ---------------------------------------------------------------- sheet
rect(0, 0, SHEET_W, SHEET_H)
rect(4, 4, SHEET_W - 8, SHEET_H - 8)
for i in range(1, 4):                     # zone marks on the border
    line(4 + i * (SHEET_W - 8) / 4, 0, 4 + i * (SHEET_W - 8) / 4, 4)
    line(4 + i * (SHEET_W - 8) / 4, SHEET_H - 4, 4 + i * (SHEET_W - 8) / 4, SHEET_H)

# Title block, lower right.
tx, ty, tw, th = SHEET_W - 4 - 96, 4, 96, 34
rect(tx, ty, tw, th)
line(tx, ty + 22, tx + tw, ty + 22)
line(tx, ty + 11, tx + tw, ty + 11)
line(tx + 48, ty, tx + 48, ty + 11)
text("PEN PLOTTER", tx + 3, ty + 26, 5.0)
text("CR-10 V3 TABLE CONVERSION", tx + 3, ty + 14.5, 3.0)
text("SCALE 1:3", tx + 3, ty + 4, 2.6)
text("DWG PP-001  SHT 1/1", tx + 51, ty + 4, 2.6)

# ---------------------------------------------------------------- top view, 1:3
S = 1 / 3.0
OX, OY = 22.0, 70.0                       # sheet position of the frame origin (front left outer corner)


def P(x, y):
    return OX + x * S, OY + y * S


def frect(x0, y0, x1, y1):
    a, b = P(x0, y0)
    c, d = P(x1, y1)
    rect(a, b, c - a, d - b)


frect(0, 0, 400, 520)                     # frame, outside
frect(40, 20, 360, 500)                   # the opening
for x in (0, 360):                        # long rails, with the slot lines
    for sx in (10, 30):
        a, b = P(x + sx, 20)
        c, d = P(x + sx, 500)
        dashed(a, b, c, d, 2.0, 1.2)
for x in (4, 384):                        # MGN12 rails
    frect(x, 35, x + 12, 485)
cy = 300.0                                # the gantry, at Y = 300
frect(-7.5, cy - 10, 407.5, cy + 10)      # the 2020 beam
frect(0, cy - 18, 400, cy - 10)           # the X rail
for x0 in (-28, 356):                     # Y carriages
    frect(x0, cy - 30, x0 + 72, cy + 30)
frect(-1, cy + 21, 41, cy + 61)           # X motor
for mx in (-26, 426):                     # Y motors and idlers
    frect(mx - 21, 548 - 21, mx + 21, 548 + 21)
    circle(*P(mx, 548), 2.5)
    circle(*P(mx, -19), 3.0)
    a, b = P(mx - 6.7, -19)
    c, d = P(mx - 6.7, 548)
    dashed(a, b, c, d, 2.5, 1.5)
    a, b = P(mx + 6.7, -19)
    c, d = P(mx + 6.7, 548)
    dashed(a, b, c, d, 2.5, 1.5)
px = 200.0                                # the X carriage and the pen
frect(px - 28, cy - 29 - 6, px + 28, cy - 29)
frect(px - 20, cy - 29 - 45, px + 38, cy - 35)
circle(*P(px - 1, cy - 29 - 23.5), 2.0)
# Centre lines.
a, b = P(200, -10)
c, d = P(200, 530)
dashed(a, b, c, d, dot=True)
a, b = P(-35, cy)
c, d = P(435, cy)
dashed(a, b, c, d, dot=True)
# The travel of the pen, dashed.
hx, hy = 59.3, 36.4
a, b = P(hx, hy)
c, d = P(hx + 253, hy + 400)
for (p1, p2) in (((a, b), (c, b)), ((c, b), (c, d)), ((c, d), (a, d)), ((a, d), (a, b))):
    dashed(p1[0], p1[1], p2[0], p2[1], 2.0, 1.5)
text("TRAVEL 253 x 400", (a + c) / 2, d - 5, 2.4, align="center")
text("HOME", a + 1, b + 1.5, 2.0)
# Dimensions.
x_l, y_b = P(0, 0)
x_r, y_t = P(400, 520)
dim_h(x_l, x_r, y_b - 8, "400", ext_from=y_b)
xi1, yi1 = P(40, 20)
xi2, yi2 = P(360, 500)
dim_h(xi1, xi2, y_t + 6, "320", ext_from=yi2)
dim_v(y_b, y_t, x_l - 9, "520", ext_from=x_l)
dim_v(yi1, yi2, x_r + 6, "480", ext_from=xi2)
text("TOP VIEW", (x_l + x_r) / 2, y_t + 14, 3.2, align="center")

# ---------------------------------------------------------------- section A-A of a Y rail, 1:1
sx0, sy0 = 160.0, 150.0
rect(sx0, sy0, 40, 20)                    # 2040, flat
for cx in (sx0 + 10, sx0 + 30):
    rect(cx - 3, sy0 + 20 - 2, 6, 2)      # top slots
    rect(cx - 3, sy0, 6, 2)               # bottom slots
    circle(cx, sy0 + 10, 2.1)             # core holes
rect(sx0 + 4, sy0 + 20, 12, 8)            # MGN12 rail on the outer slot
rect(sx0 - 3.5, sy0 + 23, 27, 10)         # MGN12H block
rect(sx0 - 18, sy0 + 33, 50, 6)           # Y carriage plate (cut)
for i in range(10):                       # section hatch on the plate
    x = sx0 - 18 + 2 + i * 5
    line(x, sy0 + 33, x + 4, sy0 + 39)
dim_h(sx0, sx0 + 40, sy0 - 6, "40", ext_from=sy0)
dim_v(sy0, sy0 + 20, sx0 + 46, "20", ext_from=sx0 + 40)
text("SECTION A-A  1:1", sx0 + 7, sy0 + 46, 2.8, align="center")
text("Y RAIL", sx0 + 7, sy0 + 42, 2.2, align="center")

# ---------------------------------------------------------------- notes
nx, ny = 150.0, 118.0
text("NOTES", nx, ny, 3.0)
for i, s in enumerate(["1. DIMENSIONS IN MM.", "2. MGN12 RAILS, X AND Y.", "3. TWO Y MOTORS, SQUARED",
                       "   AT HOMING.", "4. PEN FORCE = SLIDER", "   WEIGHT."]):
    text(s, nx, ny - 5 - i * 4.2, 2.2)


# ---------------------------------------------------------------- G-code
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


def gcode():
    out = ["; blueprint of the pen plotter, Letter sheet", "G21", "G90", "M5", "G28"]
    for s in order(strokes):
        x, y = s[0]
        out.append(f"G0 X{X0 + x:.2f} Y{Y0 + y:.2f} F{TRAVEL}")
        out.append("M3")
        for x, y in s[1:]:
            out.append(f"G1 X{X0 + x:.2f} Y{Y0 + y:.2f} F{FEED}")
        out.append("M5")
    out += ["G0 X0 Y395", "M400"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    path = os.path.join(HERE, "blueprint.gcode")
    with open(path, "w") as fh:
        fh.write(gcode())
    print(f"wrote {path}: {len(strokes)} strokes")
