#!/usr/bin/env python3
"""Write samples/accord.gcode and samples/accord.svg: line art, front three-quarter view of a stock 1999 Honda Accord
sedan (6th generation), for a Letter sheet.

The script builds a simple 3D model of the car: a body lofted from cross sections, wheels and
mirrors. It draws the feature lines and the outlines of the model in a perspective view from the
front right, and removes the hidden parts with a depth buffer. The overall sizes are the published values (length 4796 mm, width
1785 mm, height 1445 mm, wheelbase 2715 mm, 195/65R15 tyres). The shapes are estimates.

The drawing is landscape, turned on a portrait Letter sheet. Put the sheet with its lower left
corner at machine X 14.5, Y 20. The bottom of the drawing is at the right edge of the sheet (the
high X side). The drawing stays below machine Y 290, out of the pen rack area.

Run: uv run --no-project --with Hershey-Fonts --with numpy python samples/accord.py
"""

import math
import os

import numpy as np
from HersheyFonts import HersheyFonts

HERE = os.path.dirname(os.path.abspath(__file__))

PAGE_W, PAGE_H = 260.0, 200.0             # the landscape drawing area
X0, Y0 = 22.5, 29.7                       # machine position of the drawing area (portrait)
FEED = 3000                               # mm/min

# ---------------------------------------------------------------- the car (mm)
# x: from the front bumper to the rear. y: + to the right side of the car. z: up from the ground.
L = 4796.0
XF, XR = 945.0, 945.0 + 2715.0            # front and rear axle
RT = 317.0                                # tyre radius, 195/65R15
TW = 195.0                                # tyre width
TRACK = 1545.0
ARCH_Z, ARCH_R = 335.0, 362.0             # wheel arch centre height and radius
X_COWL, X_ROOF0, X_ROOF1, X_DECK = 1300.0, 2090.0, 3080.0, 3830.0


def tab(pairs):
    xs, ys = zip(*pairs)
    return lambda x: float(np.interp(x, xs, ys))


z_bot = tab([(0, 300), (90, 240), (400, 228), (4600, 232), (4720, 270), (L, 330)])
z_crease = tab([(0, 560), (90, 600), (400, 655), (900, 730), (1300, 790), (3800, 820), (4650, 830), (L, 800)])
z_sh = tab([(0, 745), (110, 790), (400, 830), (1300, 950), (2000, 972), (3000, 992), (3700, 1018),
            (3850, 1035), (4650, 1048), (4740, 1040), (L, 985)])
w_max = tab([(0, 540), (40, 680), (120, 775), (250, 838), (450, 875), (900, 890), (3700, 892), (4500, 886),
             (4680, 858), (4750, 815), (L, 735)])


def z_top_c(x):
    """The height of the top surface at the centre line."""
    if x <= X_COWL:
        return z_sh(x) + 40
    if x <= X_ROOF0:                       # windshield, a little convex
        t = (x - X_COWL) / (X_ROOF0 - X_COWL)
        a, b = z_sh(X_COWL) + 40, 1438.0
        return a + (b - a) * (1 - (1 - t) ** 1.35)
    if x <= X_ROOF1:                       # roof
        t = (x - X_ROOF0) / (X_ROOF1 - X_ROOF0)
        return 1438.0 + 7.0 * math.sin(math.pi * t)
    if x <= X_DECK:                        # rear window, convex
        t = (x - X_ROOF1) / (X_DECK - X_ROOF1)
        a, b = 1438.0, z_sh(X_DECK) + 22
        return a + (b - a) * t ** 1.4
    return z_sh(x) + 22


def crown(x):
    if X_COWL < x < X_DECK:
        t = min(1.0, (x - X_COWL) / 300.0, (X_DECK - x) / 300.0)
        return 25.0 + 15.0 * t
    return 25.0 if x <= X_COWL else 14.0


def w_top(x):
    """Half width of the top edge: the A-pillar, the roof edge, the C-pillar."""
    if x <= X_COWL:
        return 0.80 * (w_max(x) - 22)
    if x <= X_ROOF0:
        t = (x - X_COWL) / (X_ROOF0 - X_COWL)
        return 0.80 * (w_max(X_COWL) - 22) + (655.0 - 0.80 * (w_max(X_COWL) - 22)) * t
    if x <= X_ROOF1:
        return 655.0
    if x <= X_DECK:
        t = (x - X_ROOF1) / (X_DECK - X_ROOF1)
        return 655.0 + (0.82 * (w_max(X_DECK) - 22) - 655.0) * t
    return 0.82 * (w_max(x) - 22)


def quad(p0, c, p1, n, end=False):
    out = []
    for k in range(n + (1 if end else 0)):
        t = k / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]))
    return out


def half_section(x):
    """The right half of the cross section at x: (y, z) points from the bottom centre to the top
    centre, and the indices of the feature points P0 (rocker) to P4 (top edge)."""
    zb, z1, z2, wm = z_bot(x), z_crease(x), z_sh(x), w_max(x)
    wb, w2 = wm - 60, wm - 22
    z3, w3 = z2 + 8, w2 - 28
    zc, w4 = z_top_c(x), w_top(x)
    z4 = zc - crown(x)
    pts, idx = [], {}
    pts += [(wb * k / 3, zb) for k in range(3)]
    idx["P0"] = len(pts)
    pts += quad((wb, zb), (wm, zb + 0.25 * (z1 - zb)), (wm, z1), 12)
    idx["P1"] = len(pts)
    pts += [(wm + (w2 - wm) * k / 4, z1 + (z2 - z1) * k / 4) for k in range(4)]
    idx["P2"] = len(pts)
    pts += quad((w2, z2), (w2 - 4, z3), (w3, z3), 3)
    idx["P3"] = len(pts)
    pts += quad((w3, z3), (w3 - 0.30 * (w3 - w4), z3 + 0.65 * (z4 - z3)), (w4, z4), 10)
    idx["P4"] = len(pts)
    pts += quad((w4, z4), (w4 * 0.5, zc), (0, zc), 10, end=True)
    return pts, idx


def lean(x, z):
    """Moves the nose and the tail a little: the faces lean back at the top and under at the bottom."""
    f = max(0.0, 1 - x / 260.0)
    r = max(0.0, 1 - (L - x) / 260.0)
    dx = f * (45 * min(1, max(0, (z - 450) / 320)) + 35 * min(1, max(0, (360 - z) / 110)))
    dx -= r * (60 * min(1, max(0, (z - 760) / 260)) + 30 * min(1, max(0, (400 - z) / 100)))
    return x + dx


# Stations: dense at the ends.
XS = np.concatenate([np.linspace(0, 300, 31), np.linspace(300, 4500, 211)[1:], np.linspace(4500, L, 31)[1:]])
_, IDX = half_section(1000.0)
NH = len(half_section(1000.0)[0])          # points in a half section
# The full ring: the right half, then the left half (mirror) back to the bottom centre.
RING = [(j, 1) for j in range(NH)] + [(j, -1) for j in range(NH - 2, 0, -1)]
NR = len(RING)

V = np.zeros((len(XS), NR, 3))
for i, x in enumerate(XS):
    hp, _ = half_section(x)
    for k, (j, s) in enumerate(RING):
        y, z = hp[j]
        V[i, k] = (lean(x, z), s * y, z)


def ring_index(j, side):
    """The ring index of half-section point j on the side (+1 right, -1 left)."""
    if side > 0 or j == 0 or j == NH - 1:
        return j
    return NR - j


def in_arch(x, y, z, grow=0.0):
    if abs(y) < 500:
        return False
    for xa in (XF, XR):
        if (x - xa) ** 2 + (z - ARCH_Z) ** 2 < (ARCH_R + grow) ** 2:
            return True
    return False


# Body triangles, without the wheel arches.
body_tris = []
for i in range(len(XS) - 1):
    for k in range(NR):
        a, b = V[i, k], V[i, (k + 1) % NR]
        c, d = V[i + 1, (k + 1) % NR], V[i + 1, k]
        for t in ((a, b, c), (a, c, d)):
            if all(in_arch(*p) for p in t):
                continue
            body_tris.append(t)
for i in (0, len(XS) - 1):                 # the end caps
    cen = V[i].mean(axis=0)
    for k in range(NR):
        body_tris.append((cen, V[i, k], V[i, (k + 1) % NR]))


# ---------------------------------------------------------------- wheels and mirrors
def ellipse(cu, cv, ru, rv, n=40, a0=0.0, a1=2 * math.pi):
    return [(cu + ru * math.cos(a0 + (a1 - a0) * k / n), cv + rv * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def rrect(u0, v0, u1, v1, r):
    pts = []
    for cu, cv, a in ((u1 - r, v0 + r, -90), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)):
        pts += ellipse(cu, cv, r, r, 6, math.radians(a), math.radians(a + 90))
    return pts + [pts[0]]


def wheel_tris(xa, side):
    yo = side * (TRACK / 2 + TW / 2)       # outer face
    yi = side * (TRACK / 2 - TW / 2)
    yr = yo - side * 28                    # the rim face, set in
    n = 72
    th = [2 * math.pi * k / n for k in range(n + 1)]

    def P(r, y, t):
        return np.array((xa + r * math.cos(t), y, RT + r * math.sin(t)))
    tris = []
    rings = [(RT - 16, yo), (RT, yo - side * 16), (RT, yi + side * 16), (RT - 16, yi)]
    for (r1, y1), (r2, y2) in zip(rings, rings[1:]):
        for a, b in zip(th, th[1:]):
            tris += [(P(r1, y1, a), P(r1, y1, b), P(r2, y2, b)), (P(r1, y1, a), P(r2, y2, b), P(r2, y2, a))]
    for (r1, y1), (r2, y2) in (((RT - 16, yo), (197, yo)), ((197, yo), (197, yr)), ((RT - 16, yi), (150, yi))):
        for a, b in zip(th, th[1:]):
            tris += [(P(r1, y1, a), P(r1, y1, b), P(r2, y2, b)), (P(r1, y1, a), P(r2, y2, b), P(r2, y2, a))]
    c = np.array((xa, yr, RT))
    for a, b in zip(th, th[1:]):
        tris.append((c, P(197, yr, a), P(197, yr, b)))
    return tris


def mirror_grid(side):
    """The door mirror: rounded profiles (x, z) lofted out from the door. Returns a grid
    (stations, ring, 3)."""
    prof = rrect(1360, 975, 1500, 1080, 34)[:-1]
    cx, cz = 1430, 1027
    out = []
    for y, s, dx in ((838, 0.45, 30), (870, 0.75, 14), (905, 0.95, 4), (960, 1.0, 0), (995, 0.97, 4), (1012, 0.85, 10)):
        out.append([(cx + dx + s * (u - cx), side * y, cz + s * (v - cz)) for u, v in prof])
    return np.array(out)


all_tris = list(body_tris)
MIRRORS = []
lines3d = []                               # 3D polylines (lists of np arrays)
for side in (1, -1):
    for xa in (XF, XR):
        all_tris += wheel_tris(xa, side)
    G = mirror_grid(side)
    MIRRORS.append(G)
    for i in range(len(G) - 1):
        for k in range(len(G[0])):
            a, b, c, d = G[i, k], G[i, (k + 1) % len(G[0])], G[i + 1, (k + 1) % len(G[0])], G[i + 1, k]
            all_tris += [(a, b, c), (a, c, d)]
    cen = G[-1].mean(axis=0)
    all_tris += [(cen, G[-1][k], G[-1][(k + 1) % len(G[0])]) for k in range(len(G[0]))]
    lines3d.append(list(G[-1]) + [G[-1][0]])


# ---------------------------------------------------------------- rasteriser
def raster(uvw, res):
    """Maximum w for each (u, v) pixel. uvw: (T, 3, 3) triangles. Returns the grid and its origin."""
    u0, v0 = uvw[:, :, 0].min() - 2 * res, uvw[:, :, 1].min() - 2 * res
    nu = int((uvw[:, :, 0].max() - u0) / res) + 3
    nv = int((uvw[:, :, 1].max() - v0) / res) + 3
    zb = np.full((nv, nu), -np.inf)
    for tri in uvw:
        pu, pv, pw = (tri[:, 0] - u0) / res, (tri[:, 1] - v0) / res, tri[:, 2]
        i0, i1 = int(math.floor(pu.min())), int(math.ceil(pu.max()))
        j0, j1 = int(math.floor(pv.min())), int(math.ceil(pv.max()))
        den = (pv[1] - pv[2]) * (pu[0] - pu[2]) + (pu[2] - pu[1]) * (pv[0] - pv[2])
        if abs(den) < 1e-9:
            continue
        gu, gv = np.meshgrid(np.arange(i0, i1 + 1) + 0.5, np.arange(j0, j1 + 1) + 0.5)
        a = ((pv[1] - pv[2]) * (gu - pu[2]) + (pu[2] - pu[1]) * (gv - pv[2])) / den
        b = ((pv[2] - pv[0]) * (gu - pu[2]) + (pu[0] - pu[2]) * (gv - pv[2])) / den
        c = 1 - a - b
        m = (a >= -0.02) & (b >= -0.02) & (c >= -0.02)
        if not m.any():
            continue
        w = a * pw[0] + b * pw[1] + c * pw[2]
        sub = zb[j0:j1 + 1, i0:i1 + 1]
        np.maximum(sub, np.where(m, w, -np.inf), out=sub)
    return zb, u0, v0


class Map:
    """A depth map of the body along one axis, for putting 2D feature lines on the surface."""

    def __init__(self, tris, u, v, w, sw, res=5.0):
        T = np.array(tris)
        self.u, self.v, self.w, self.sw = u, v, w, sw
        uvw = np.stack([T[:, :, u], T[:, :, v], sw * T[:, :, w]], axis=2)
        self.zb, self.u0, self.v0 = raster(uvw, res)
        self.res = res

    def lift(self, pts2d):
        """3D points for (u, v) points. A point with no surface is None."""
        out, zb = [], self.zb
        for pu, pv in pts2d:
            fi = (pu - self.u0) / self.res - 0.5
            fj = (pv - self.v0) / self.res - 0.5
            i, j = int(math.floor(fi)), int(math.floor(fj))
            if not (0 <= j < zb.shape[0] - 1 and 0 <= i < zb.shape[1] - 1):
                out.append(None)
                continue
            q = zb[j:j + 2, i:i + 2]
            if np.isfinite(q).all():
                a, b = fi - i, fj - j
                w = (q[0, 0] * (1 - a) + q[0, 1] * a) * (1 - b) + (q[1, 0] * (1 - a) + q[1, 1] * a) * b
            else:
                w = zb[int(round(fj)), int(round(fi))]
                if not np.isfinite(w):
                    out.append(None)
                    continue
            p = [0.0, 0.0, 0.0]
            p[self.u], p[self.v], p[self.w] = pu, pv, self.sw * w
            out.append(np.array(p))
        return out


def densify2(pts, step=6.0):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
    return out


def add_lifted(m, pts2d, closed=False):
    pts2d = list(pts2d) + ([pts2d[0]] if closed else [])
    cur = []
    for p in m.lift(densify2(pts2d)):
        if p is None:
            if len(cur) > 1:
                lines3d.append(cur)
            cur = []
        else:
            cur.append(p)
    if len(cur) > 1:
        lines3d.append(cur)


SIDE = Map(body_tris, 0, 2, 1, -1)         # seen from the left (-y): (x, z) -> y
FRONT = Map(body_tris, 1, 2, 0, -1)        # seen from the front (-x): (y, z) -> x
TOP = Map(body_tris, 0, 1, 2, 1)           # seen from above: (x, y) -> z


# ---------------------------------------------------------------- camera
# A perspective view from the front right, from a little above head height, like a photo.
TARGET = np.array((2250.0, 0.0, 560.0))
BEARING = math.radians(36.0)               # from straight ahead of the car, toward its right side
DIST, CAM_Z = 7600.0, 2500.0
CAM = TARGET + np.array((-DIST * math.cos(BEARING), DIST * math.sin(BEARING), 0.0))
CAM[2] = CAM_Z
FWD = (TARGET - CAM) / np.linalg.norm(TARGET - CAM)
RGT = np.cross(FWD, (0.0, 0.0, 1.0))
RGT /= np.linalg.norm(RGT)
UP = np.cross(RGT, FWD)
FOC = DIST                                 # screen units are about mm at the target


def project(p):
    d = p - CAM
    dep = d @ FWD
    return FOC * (d @ RGT) / dep, FOC * (d @ UP) / dep, dep


# ---------------------------------------------------------------- feature lines
def section_line(j, side, x0=0.0, x1=L):
    """A line along the body through half-section point j. It stops at the wheel arches."""
    k = ring_index(j, side)
    out, cur = [], []
    for i in range(len(XS)):
        p = V[i, k]
        if x0 <= XS[i] <= x1 and not in_arch(*p, grow=6):
            cur.append(p)
        else:
            if len(cur) > 1:
                out.append(cur)
            cur = []
    if len(cur) > 1:
        out.append(cur)
    return out


for side in (1, -1):
    lines3d.extend(section_line(IDX["P0"], side, 1200, 3500))     # rocker
    lines3d.extend(section_line(IDX["P1"], side, 60, L - 40))     # body side crease
    lines3d.extend(section_line(IDX["P2"], side, 420, L))              # shoulder
    lines3d.extend(section_line(IDX["P3"], side, 110, 4705))      # hood seam, belt, trunk seam
    lines3d.extend(section_line(IDX["P4"], side, X_COWL, X_DECK))  # A-pillar, roof edge, C-pillar
for i in (len(XS) - 1,):                                            # the outline of the tail
    lines3d.append([V[i, k] for k in range(NR)] + [V[i, 0]])


def cross_line(x, j0):
    """The top of the section at x, from half-section point j0 on the left to j0 on the right."""
    i = int(np.argmin(abs(XS - x)))
    ks = [ring_index(j, -1) for j in range(j0, NH)] + [ring_index(j, 1) for j in range(NH - 2, j0 - 1, -1)]
    return [V[i, k] for k in ks]


# Outlines: the edges between the quads that face the camera and the quads that face away.
def outlines(G, gone=None):
    n = G.shape[1]
    A_, B_ = G[:-1], np.roll(G, -1, axis=1)[:-1]
    C_, D_ = np.roll(G, -1, axis=1)[1:], G[1:]
    qc = (A_ + B_ + C_ + D_) / 4
    face = np.einsum("ijk,ijk->ij", np.cross(C_ - A_, D_ - B_), CAM - qc) > 0
    if gone is None:
        gone = np.zeros(face.shape, bool)
    adj = {}

    def link(p, q):
        adj.setdefault(p, []).append(q)
        adj.setdefault(q, []).append(p)
    for i in range(len(G) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            if face[i, k] != face[i, k2] and not (gone[i, k] or gone[i, k2]):
                link((i, k2), (i + 1, k2))
            if i + 1 < len(G) - 1 and face[i, k] != face[i + 1, k] and not (gone[i, k] or gone[i + 1, k]):
                link((i + 1, k), (i + 1, k2))
    seen, res = set(), []
    for start in sorted(adj, key=lambda p: len(adj[p]) == 2):
        for nxt in adj[start]:
            if (start, nxt) in seen:
                continue
            chain, p, q = [start], start, nxt
            while True:
                seen.add((p, q))
                seen.add((q, p))
                chain.append(q)
                if len(adj[q]) != 2:
                    break
                r = adj[q][0] if adj[q][0] != p else adj[q][1]
                if (q, r) in seen:
                    break
                p, q = q, r
            if len(chain) >= 3:
                P = np.array([G[i, k] for i, k in chain])
                S_ = P.copy()
                for j in range(2, len(P) - 2):
                    S_[j] = P[j - 2:j + 3].mean(axis=0)
                res.append(list(S_))
    return res


GONE = np.array([[in_arch(*V[i, k]) or in_arch(*V[i, (k + 1) % NR]) for k in range(NR)] for i in range(len(XS))])
sil3d = outlines(V, GONE[:-1] | GONE[1:])
for G in MIRRORS:
    sil3d.extend(outlines(G))

lines3d.append(cross_line(X_COWL, IDX["P3"]))          # the cowl: rear edge of the hood
lines3d.append(cross_line(X_DECK + 15, IDX["P3"]))     # the front edge of the trunk lid
lines3d.append(cross_line(4705, IDX["P3"]))            # the rear edge of the trunk lid

# Glass on the top: windshield and rear window, set in from the pillars.
for xa_, xb_ in ((X_COWL + 45, X_ROOF0 - 35), (X_ROOF1 + 40, X_DECK - 35)):
    xs_ = np.linspace(xa_, xb_, 30)
    right = [(x, w_top(x) - 50) for x in xs_]
    left = [(x, -(w_top(x) - 50)) for x in xs_[::-1]]
    add_lifted(TOP, right + left, closed=True)
add_lifted(TOP, rrect(2180, -430, 2820, 430, 45))                    # sunroof
# Wipers, parked at the bottom of the windshield.
add_lifted(TOP, [(X_COWL + 60, -600), (X_COWL + 95, 60)])
add_lifted(TOP, [(X_COWL + 60, -20), (X_COWL + 95, 620)])

# Side (both sides, the far side is mostly hidden): windows, doors, arches, handles, lights.
for side in (-1, 1):
    S = Map(body_tris, 0, 2, 1, side) if side == 1 else SIDE

    def zt(x):
        return z_top_c(x) - crown(x)

    zbelt = lambda x: z_sh(x) + 22
    # Front door glass: under the A-pillar and the roof edge, to the B-pillar.
    xs_ = [x for x in np.linspace(X_COWL + 60, 2520, 60) if zt(x) - 50 > zbelt(x) + 10]
    add_lifted(S, [(xs_[0], zbelt(xs_[0]))] + [(x, zt(x) - 50) for x in xs_] + [(2520, zbelt(2520)), (xs_[0], zbelt(xs_[0]))])
    # Rear door glass with the division bar, and the fixed glass behind it.
    xs_ = np.linspace(2610, 3330, 40)
    add_lifted(S, [(2610, zbelt(2610))] + [(x, zt(x) - 50) for x in xs_] + [(3470, zbelt(3470)), (2610, zbelt(2610))])
    add_lifted(S, [(3215, zt(3215) - 50), (3215, zbelt(3215))])
    add_lifted(S, [(3240, zt(3240) - 50), (3240, zbelt(3240))])
    # B-pillar edges above the belt.
    add_lifted(S, [(2545, z_sh(2545) + 10), (2545, zt(2545) - 12)])
    add_lifted(S, [(2585, z_sh(2585) + 10), (2585, zt(2585) - 12)])
    # Door seams.
    add_lifted(S, [(1330, z_bot(1330) + 25), (1300, 760), (1290, z_sh(1290) - 6)])        # front door, front edge
    add_lifted(S, [(2565, z_bot(2565) + 25), (2565, z_sh(2565) - 6)])                      # between the doors
    d = math.sqrt((ARCH_R + 30) ** 2 - (XR - 3430) ** 2)
    a0 = math.atan2(d, 3430 - XR)
    arc = [(XR + (ARCH_R + 30) * math.cos(a), ARCH_Z + (ARCH_R + 30) * math.sin(a))
           for a in np.linspace(a0, math.radians(185), 20)]
    add_lifted(S, [(3440, z_sh(3440) - 6), (3430, ARCH_Z + d)] + arc)                    # rear door, rear edge
    add_lifted(S, [(1330, z_bot(1330) + 30), (3260, z_bot(3260) + 30)])                  # door bottoms
    # Wheel arches: the lip, and the arch line.
    for xa in (XF, XR):
        r = ARCH_R + 14
        lo = math.asin(max(-1, (z_bot(xa) + 5 - ARCH_Z) / r))
        add_lifted(S, ellipse(xa, ARCH_Z, r, r, 60, lo, math.pi - lo))
        r = ARCH_R + 42
        add_lifted(S, ellipse(xa, ARCH_Z, r, r, 60, lo + 0.08, math.pi - lo - 0.08))
    # Body side moldings on the doors.
    for z in (468, 500):
        add_lifted(S, [(1345, z), (2552, z)])
        add_lifted(S, [(2578, z), (3290, z)])
    # Door handles.
    for x in (2330, 3260):
        add_lifted(S, rrect(x, 845, x + 140, 880, 12))
    # Bumper seams, front and rear, along the side.
    add_lifted(S, [(XF - ARCH_R - 40, 600), (300, 615), (60, 628)])
    add_lifted(S, [(XR + ARCH_R + 40, 630), (4500, 650), (4760, 665)])
    # Side markers.
    add_lifted(S, rrect(4520, 600, 4620, 628, 8))
    # Tail light wrap on the rear quarter.
    add_lifted(S, [(4560, 1000), (4700, 995), (4770, 960), (4785, 830), (4610, 830), (4560, 1000)])
    add_lifted(S, [(4600, 900), (4775, 900)])

# Front: headlights, grille, emblem, bumper.
TB = np.array(body_tris)
TA, TE1, TE2 = TB[:, 0], TB[:, 1] - TB[:, 0], TB[:, 2] - TB[:, 0]


def cast(o, d):
    """The first point where the ray o + t d (t > 0) meets the body, or None."""
    pv = np.cross(d, TE2)
    det = np.einsum("ij,ij->i", TE1, pv)
    ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    tv = o - TA
    u = np.einsum("ij,ij->i", tv, pv) * inv
    q = np.cross(tv, TE1)
    v = (q @ d) * inv
    t = np.einsum("ij,ij->i", TE2, q) * inv
    m = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1)
    if not m.any():
        return None
    return o + d * t[m].min()


def add_wrap(pts, side, closed=False):
    """A line on the front corner. pts: (angle in degrees from straight ahead, z). The ray starts
    on the centre line at x 900 and turns to the side of the car."""
    pts = list(pts) + ([pts[0]] if closed else [])
    line = []
    for a, z in densify2([(a * 14.0, z) for a, z in pts], 5.0):
        r = math.radians(a / 14.0)
        p = cast(np.array((900.0, 0.0, z)), np.array((-math.cos(r), side * math.sin(r), 0.0)))
        if p is not None:
            line.append(p)
    if len(line) > 1:
        lines3d.append(line)


for s in (1, -1):
    # The lamp: narrow at the grille, tall at the corner, around the corner onto the fender.
    add_wrap([(21.5, 690), (30, 676), (42, 664), (50, 658), (55, 664), (57.5, 700), (56, 752),
              (51, 784), (43, 786), (31, 766), (21.5, 745)], s, closed=True)
    add_wrap([(31, 690), (43, 678), (51, 673), (56.5, 684)], s)        # the amber strip
    add_wrap([(29, 702), (29, 760)], s)                                 # the inner end of the reflector
add_lifted(FRONT, rrect(-310, 656, 310, 724, 14))                       # grille
for z in (679, 701):
    add_lifted(FRONT, [(-300, z), (-58, z)])
    add_lifted(FRONT, [(58, z), (300, z)])
add_lifted(FRONT, ellipse(0, 690, 50, 28, 30))                          # emblem
for p in ([(-20, 676), (-20, 704)], [(20, 676), (20, 704)], [(-20, 690), (20, 690)]):
    add_lifted(FRONT, p)
add_lifted(FRONT, [(-880, 630), (880, 630)])                            # bumper top seam
add_lifted(FRONT, rrect(-430, 335, 430, 440, 30))                       # lower air intake
add_lifted(FRONT, [(-420, 388), (420, 388)])
add_lifted(FRONT, rrect(-160, 455, 160, 605, 8))                        # licence plate

# Wheels: tyre, rim and spokes.
for side in (1, -1):
    for xa in (XF, XR):
        yo = side * (TRACK / 2 + TW / 2)
        yi = side * (TRACK / 2 - TW / 2)
        yr = yo - side * 28

        def W(r, y, a):
            return np.array((xa + r * math.cos(a), y, RT + r * math.sin(a)))
        n = 120
        ang = [2 * math.pi * k / n for k in range(n + 1)]
        lines3d.append([W(RT - 6, yo - side * 6, a) for a in ang])        # tyre shoulder
        lines3d.append([W(RT - 6, yi + side * 6, a) for a in ang])
        lines3d.append([W(197, yo, a) for a in ang])                      # rim lip
        lines3d.append([W(182, yr, a) for a in ang])
        d = np.array((xa, yo, RT)) - CAM                                  # the tread outline, seen from the camera
        a = math.atan2(d[0], -d[2])
        for b in (a, a + math.pi):
            lines3d.append([W(RT, yo - side * 10, b), W(RT, yi + side * 10, b)])
        lines3d.append([W(58, yr, a) for a in ang])                       # centre cap
        for pl in ([(-14, -22), (-14, 22)], [(14, -22), (14, 22)], [(-14, 0), (14, 0)]):
            lines3d.append([np.array((xa - side * u, yr, RT + v)) for u, v in pl])
        for k in range(5):                                                # the windows between the spokes
            a = 2 * math.pi * k / 5 + math.pi / 2 + math.pi / 5
            out = [W(170, yr, a + t) for t in np.linspace(-0.40, 0.40, 14)]
            inn = [W(84, yr, a + t) for t in np.linspace(0.22, -0.22, 8)]
            lines3d.append(out + inn + [out[0]])

# ---------------------------------------------------------------- hidden lines
RES = 3.0
T = np.array(all_tris)
TD = T - CAM
TDEP = TD @ FWD
ZB, SU0, SV0 = raster(np.stack([FOC * (TD @ RGT) / TDEP, FOC * (TD @ UP) / TDEP, -TDEP], axis=2), RES)
EPS = 22.0


def visible(p, outline=False):
    """An outline lies where the surface turns away from the camera, so the depth of its own pixel
    is not reliable: it stays visible unless a neighbour pixel in front of it covers it."""
    u, v, dep = project(p)
    i = int((u - SU0) / RES)
    j = int((v - SV0) / RES)
    zb = ZB[max(0, j - 1):j + 2, max(0, i - 1):i + 2]
    if outline:
        return -dep >= zb.min() - EPS
    return -dep >= zb.min() - EPS and -dep >= ZB[j, i] - EPS


def densify3(pts, step=5.0):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return out


runs = []
for pl, ol in [(q, False) for q in lines3d] + [(q, True) for q in sil3d]:
    cur = []
    for p in densify3([np.asarray(q, float) for q in pl]):
        if visible(p, ol):
            u, v, _ = project(p)
            cur.append((u, v))
        else:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
    if len(cur) > 1:
        runs.append(cur)

# ---------------------------------------------------------------- page
FONT = HersheyFonts()
FONT.load_default_font("futural")
strokes = []


def text(s, x, y, h=3.0, align="left"):
    FONT.normalize_rendering(h)
    segs = list(FONT.lines_for_text(s))
    width = max(max(a[0], b[0]) for a, b in segs)
    dx = {"left": 0.0, "center": -width / 2, "right": -width}[align]
    cur = None
    for (ax, ay), (bx, by) in segs:
        p, q = (x + ax + dx, y + ay), (x + bx + dx, y + by)
        if cur and math.hypot(cur[-1][0] - p[0], cur[-1][1] - p[1]) < 1e-6:
            cur.append(q)
        else:
            cur = [p, q]
            strokes.append(cur)


allp = np.array([p for r in runs for p in r])
mnx, mny = allp.min(axis=0)
mxx, mxy = allp.max(axis=0)
box = (12.0, 34.0, PAGE_W - 12.0, PAGE_H - 10.0)
sc = min((box[2] - box[0]) / (mxx - mnx), (box[3] - box[1]) / (mxy - mny))
ox = (box[0] + box[2]) / 2 - sc * (mnx + mxx) / 2
oy = (box[1] + box[3]) / 2 - sc * (mny + mxy) / 2
for r in runs:
    pts = [(ox + sc * u, oy + sc * v) for u, v in r]
    if sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])) >= 1.0:
        strokes.append(pts)

strokes.append([(0, 0), (PAGE_W, 0), (PAGE_W, PAGE_H), (0, PAGE_H), (0, 0)])
text("1999 HONDA ACCORD SEDAN", PAGE_W / 2, 16.0, 4.2, align="center")
text("FRONT THREE-QUARTER VIEW   -   LENGTH 4796 MM   WIDTH 1785 MM   HEIGHT 1445 MM   WHEELBASE 2715 MM", PAGE_W / 2, 9.0, 2.0, align="center")


# ---------------------------------------------------------------- output
def simplify(s, tol=0.03):
    """Douglas-Peucker: drops the points that are within tol mm of the simplified line."""
    if len(s) < 3:
        return s
    a, b = s[0], s[-1]
    ux, uy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(ux, uy)
    if n == 0:
        d = [math.hypot(p[0] - a[0], p[1] - a[1]) for p in s[1:-1]]
    else:
        d = [abs((p[0] - a[0]) * uy - (p[1] - a[1]) * ux) / n for p in s[1:-1]]
    i = int(np.argmax(d))
    if d[i] <= tol:
        return [a, b]
    return simplify(s[:i + 2], tol)[:-1] + simplify(s[i + 1:], tol)


def order(strokes):
    left = [s for s in strokes if len(s) >= 2]
    out, pos = [], (PAGE_W, 0.0)
    while left:
        best, bi, rev = None, 0, False
        for i, s in enumerate(left):
            for r, p in ((False, s[0]), (True, s[-1])):
                d = (p[0] - pos[0]) ** 2 + (p[1] - pos[1]) ** 2
                if best is None or d < best:
                    best, bi, rev = d, i, r
        s = left.pop(bi)
        s = s[::-1] if rev else s
        if out and math.hypot(out[-1][-1][0] - s[0][0], out[-1][-1][1] - s[0][1]) < 0.05:
            out[-1] = out[-1] + s[1:]
        else:
            out.append(s)
        pos = out[-1][-1]
    return out


def machine(p):
    """Page (landscape) to machine (portrait sheet): the page bottom is at the high X side."""
    return X0 + (PAGE_H - p[1]), Y0 + p[0]


if __name__ == "__main__":
    ordered = order([simplify(s) for s in strokes])
    draw = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for s in ordered for a, b in zip(s, s[1:]))
    travel, pos = 0.0, (PAGE_W, 0.0)
    for s in ordered:
        travel += math.hypot(s[0][0] - pos[0], s[0][1] - pos[1])
        pos = s[-1]
    minutes = draw / FEED + travel / 9000 + len(ordered) * 2 * 0.15 / 60
    out = ["; 1999 Honda Accord sedan, line art, front three-quarter view, Letter sheet",
           "; Letter portrait, lower left corner at X14.5 Y20. The drawing bottom is at the high X edge.",
           f"; {len(ordered)} strokes, {draw / 1000:.2f} m of line, about {minutes:.0f} min.",
           "G21", "G90", "M5", "G28"]
    n = len(ordered)
    for i, s in enumerate(ordered):
        if i % max(1, n // 20) == 0:
            out.append(f"M73 P{100 * i // n}")
        x, y = machine(s[0])
        out.append(f"G0 X{x:.2f} Y{y:.2f}")
        out.append("M3")
        for j, p in enumerate(s[1:]):
            x, y = machine(p)
            out.append(f"G1 X{x:.2f} Y{y:.2f}" + (f" F{FEED}" if j == 0 else ""))
        out.append("M5")
    out += ["M73 P100", f"G0 X{X0:.1f} Y330", "M400"]
    with open(os.path.join(HERE, "accord.gcode"), "w") as fh:
        fh.write("\n".join(out) + "\n")
    w, h = PAGE_W + 19.4, PAGE_H + 16
    body = "".join('<polyline points="' + " ".join(f"{x + 9.7:.2f},{h - (y + 8):.2f}" for x, y in s) + '"/>' for s in ordered)
    with open(os.path.join(HERE, "accord.svg"), "w") as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 5:.0f}" height="{h * 5:.0f}" viewBox="0 0 {w:.1f} {h:.1f}">'
                 f'<rect width="100%" height="100%" fill="#fff"/><g fill="none" stroke="#111" stroke-width="0.25" '
                 f'stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>\n')
    mx = [machine(p) for s in ordered for p in s]
    print(f"wrote samples/accord.gcode and samples/accord.svg: {n} strokes, {draw / 1000:.2f} m, about {minutes:.0f} min, scale 1:{1 / sc:.1f}")
    print(f"machine X {min(p[0] for p in mx):.1f}..{max(p[0] for p in mx):.1f}, Y {min(p[1] for p in mx):.1f}..{max(p[1] for p in mx):.1f}")
