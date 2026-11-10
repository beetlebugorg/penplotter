"""The checks of the audit: hole meat, thread engagement, head seating, tool access, axles,
layer orientation, loads and strength, and fits. Each check adds rows to a list:
{part, feature, check, value, limit, status, fix}."""

import math

import numpy as np

import geo
import rules as R

import fasteners as F
import model as M
import parts as P
import shape as S

STEP = 0.5          # mm between depths on the screw axis
N_ANG = 24          # directions round the axis
EDGE = 1.0          # mm: skip this much at each end of a hole (the edge chamfers of the finish)


# ---------------------------------------------------------------- the fastener data

class AuditBuilder(F.Builder):
    """The Builder of fasteners.py, with a record of the joint of each screw."""

    def __init__(self):
        super().__init__()
        self.jmap = {}
        self._mark = 0

    def joint(self, key, item, kind, length, grip, limit=0.0, size="M5", count=1):
        super().joint(key, item, kind, length, grip, limit, size, count)
        k = key.replace("_left", "").replace("_right", "")
        for f in self.items[self._mark:]:
            if f.kind == "screw" and id(f) not in self.jmap and f.item == item:
                self.jmap[id(f)] = k
        if all(id(f) in self.jmap for f in self.items[self._mark:] if f.kind == "screw"):
            self._mark = len(self.items)

    def mirror_since(self, mark):
        n0 = len(self.items)
        start = mark[0]
        super().mirror_since(mark)
        for a, b in zip(self.items[start:n0], self.items[n0:]):
            if id(a) in self.jmap:
                self.jmap[id(b)] = self.jmap[id(a)]
        if all(id(f) in self.jmap for f in self.items[self._mark:] if f.kind == "screw"):
            self._mark = len(self.items)


def build_fasteners(c, xp):
    old = F.Builder
    F.Builder = AuditBuilder
    try:
        b = AuditBuilder()
        F.static_items(b)
        F.gantry_items(b, c)
        t = P.plate_offset(xp, c)
        F.carriage_items(b, t)
        F.x_belt_items(b, t)
        F.pen_items(b, t)
    finally:
        F.Builder = old
    return b.items, b.joints, b.jmap


def head_dims(size, head):
    if head == "socket" and size in S.SOCKET:
        return S.SOCKET[size]
    if head == "button" and size in getattr(S, "BUTTON", {}):
        return S.BUTTON[size]
    if head == "pan" and size in getattr(S, "PAN", {}):
        return S.PAN[size]
    return None


class Screw:
    """One screw: the axis from the head bearing face (s = 0) into the joint (s > 0)."""

    def __init__(self, f, joint):
        self.f, self.joint = f, joint
        self.name, self.size, self.part = f.name, f.size, f.part
        self.dn = R.NOMINAL.get(f.size, 5.0)
        m = f.meta or {}
        if "p" in m and "d" in m:
            self.p = np.array(m["p"], float)
            self.d = np.array(m["d"], float) / np.linalg.norm(m["d"])
            self.L = float(m.get("length", 0) or self._len())
            self.head = m.get("head", "socket")
        else:
            self._from_geometry()
        hd = head_dims(self.size, self.head)
        if hd is None:
            hd = self._head_geometry()
        self.D, self.k = hd
        self.coax = []

    def _len(self):
        return geo.extent_along(self.f.solid, self.p, self.d)[1]

    def _from_geometry(self):
        r_sh = S.SHANK.get(self.size, self.dn * 0.84) / 2
        _, pa, da, fsh = geo.cyl_axis(self.f.solid, r_sh)
        big = geo.cyl_axis(self.f.solid, 99.0)
        da = da / np.linalg.norm(da)
        ch = np.array(tuple(big[3].center()))
        cs = np.array(tuple(fsh.center()))
        if (ch - pa) @ da > (cs - pa) @ da:
            da = -da
        s0, _ = geo.extent_along(fsh, pa, da)
        self.p = pa + s0 * da
        self.d = da
        self.L = geo.extent_along(self.f.solid, self.p, self.d)[1]
        self.head = "button" if big[0] > 4.5 else "socket"

    def _head_geometry(self):
        big = geo.cyl_axis(self.f.solid, 99.0)
        lo, _ = geo.extent_along(self.f.solid, self.p, self.d)
        return 2 * big[0], -lo

    def at(self, s):
        return self.p + s * self.d

    @property
    def kind(self):
        return self.joint.kind if self.joint else "?"


def attach_coaxial(screws, items):
    others = [g for g in items if g.kind not in ("screw", "belt", "clip")]
    for g in others:
        bb = g.solid.bounding_box()
        g._c = np.array([bb.center().X, bb.center().Y, bb.center().Z])
        g._lo = np.array([bb.min.X, bb.min.Y, bb.min.Z])
        g._hi = np.array([bb.max.X, bb.max.Y, bb.max.Z])
    for sc in screws:
        a, b = sc.at(-sc.k - 3), sc.at(sc.L + 3)
        lo, hi = np.minimum(a, b) - 8, np.maximum(a, b) + 8
        for g in others:
            if np.any(g._hi < lo) or np.any(g._lo > hi):
                continue
            if geo.dist_to_axis(g._c, sc.p, sc.d) > 1.6:
                continue
            s0, s1 = geo.extent_along(g.solid, sc.p, sc.d)
            if s1 < -sc.k - 2 or s0 > sc.L + 2:
                continue
            pts = np.array([(v.X, v.Y, v.Z) for v in g.solid.vertices()])
            w = pts - sc.p
            r = np.linalg.norm(w - np.outer(w @ sc.d, sc.d), axis=1).max() if len(pts) else 0.0
            sc.coax.append({"kind": g.kind, "name": g.name, "item": g.item, "s0": s0, "s1": s1, "r": r, "f": g})


# ---------------------------------------------------------------- the world

def world_bodies(c, xp):
    """The printed parts (by part name) and the other solids, in frame coordinates."""
    ctx = M.ctx_static() + M.ctx_gantry(c) + M.ctx_carriage(xp, c)
    printed, other = {}, []
    for n, sh in ctx:
        if n in geo.CTX_PART:
            printed[geo.CTX_PART[n]] = geo.Body(n, sh, geo.CTX_PART[n], tol=0.02)
        else:
            other.append(geo.Body(n, sh, None, tol=0.08))
    return printed, other


# ---------------------------------------------------------------- the rows

class Table:
    def __init__(self):
        self.rows = []

    def add(self, part, feature, check, value, limit, status, fix="", note=""):
        self.rows.append({"part": part, "feature": feature, "check": check, "value": value, "limit": limit,
                          "status": status, "fix": fix, "note": note})


def fmt(x, n=1):
    return "inf" if x is None or (isinstance(x, float) and math.isinf(x)) else f"{x:.{n}f}"


# ---------------------------------------------------------------- the hole profile

class Hole:
    """The profile of one screw in one printed part: the spans where the part is round the axis,
    the meat, the open sectors, and the role of each span."""

    def __init__(self, sc, body):
        self.sc, self.body = sc, body
        self.s = np.arange(-sc.k - 1.0, sc.L + 3.0 + 1e-6, STEP)
        rmax = 3 * sc.dn + 8.0
        self.r_in, self.r_out, self.inside, self.ang = geo.radial_profile(body, sc.p, sc.d, self.s, N_ANG, rmax)
        self.rmax = rmax
        self.lim = np.full(len(self.s), sc.dn / 2 + 1.5)
        self.pocket = np.zeros(len(self.s), bool)
        for cx in sc.coax:
            if cx["kind"] in ("nut", "nyloc", "insert", "eccentric", "spacer", "washer", "tnut"):
                k = (self.s >= cx["s0"] - 0.3) & (self.s <= cx["s1"] + 0.3)
                self.lim[k] = np.maximum(self.lim[k], cx["r"] + 0.8)
                self.pocket[k] = True
            if cx["kind"] == "eccentric":
                # The shank of the eccentric spacer fills the hole past the hex: the hole is sized for the
                # shank (a teardrop of ECC_HOLE), not for the screw.
                k = self.s >= cx["s0"] - 0.3
                self.lim[k] = np.maximum(self.lim[k], S.ECC_HOLE / 2 * math.sqrt(2) + 0.3)
        rmin = self.r_in.min(axis=1)
        shank = (self.s >= 0) & (self.s <= sc.L)
        self.inpart = shank & (rmin <= self.lim)
        self.spans = self._spans()

    def _spans(self):
        out, cur = [], None
        for i, ok in enumerate(self.inpart):
            if ok and cur is None:
                cur = [i, i]
            elif ok:
                cur[1] = i
            elif cur is not None:
                out.append(cur)
                cur = None
        if cur is not None:
            out.append(cur)
        return [(self.s[a], self.s[b] + STEP) for a, b in out]

    def span_idx(self, span, edge=EDGE):
        a, b = span
        k = (self.s >= a + edge) & (self.s <= b - STEP - edge + 1e-9) & self.inpart
        if not k.any():
            k = (self.s >= a) & (self.s < b) & self.inpart
        return np.where(k)[0]

    def meat(self, span, pockets=False):
        """The least meat over the span (depth, angle) and the largest open sector."""
        idx = [i for i in self.span_idx(span) if pockets or not self.pocket[i]]
        best = (math.inf, None, None)
        open_deg, open_kind = 0.0, ""
        for i in idx:
            closed = self.r_in[i] <= self.lim[i]
            with np.errstate(invalid="ignore"):
                meat = np.where(closed, self.r_out[i] - self.r_in[i], math.inf)
            j = int(np.argmin(meat))
            if meat[j] < best[0]:
                best = (float(meat[j]), float(self.s[i]), float(math.degrees(self.ang[j])))
            n_open = int((~closed).sum())
            if n_open * 360.0 / N_ANG > open_deg:
                open_deg = n_open * 360.0 / N_ANG
                far = self.r_in[i][~closed]
                open_kind = "breaks out" if np.isinf(far).any() else "slot or pocket"
        return best, open_deg, open_kind

    def hole_d(self, span):
        idx = [i for i in self.span_idx(span) if not self.pocket[i]]
        if not idx:
            return math.nan
        r = self.r_in[idx]
        r = np.where(r <= self.lim[idx][:, None], r, np.inf)
        return 2 * float(np.median(r.min(axis=1)))

    def meat_toward(self, span, vec):
        """The meat in the direction nearest to vec (in the plane of the hole)."""
        d, u, v = geo.basis(self.sc.d)
        a = math.atan2(vec @ v, vec @ u)
        j = int(np.argmin(np.abs(((self.ang - a) + math.pi) % (2 * math.pi) - math.pi)))
        idx = [i for i in self.span_idx(span) if not self.pocket[i]]
        if not idx:
            return math.nan
        m = self.r_out[idx, j] - self.r_in[idx, j]
        return float(np.min(np.where(np.isfinite(m), m, self.rmax)))


# ---------------------------------------------------------------- the checks

def is_axle(sc):
    """A screw that carries a turning part (an idler or a wheel) on its shank."""
    return any(a.lower().endswith(("idler", "wheel")) for a in sc.f.allow)


def role_of(sc, hole, span):
    a, b = span
    for cx in sc.coax:
        if cx["kind"] == "insert" and cx["s1"] > a and cx["s0"] < b:
            return "insert"
    if is_axle(sc):
        return "axle"
    tip_in = a - 0.1 <= sc.L <= b + 0.6
    if sc.kind == "selftap" and tip_in:
        return "thread"
    if sc.kind == "selftap" and b >= sc.L - 1.0:
        return "thread"
    return "clearance"


def check_holes(T, screws, printed, cura):
    """Checks 1, 2 (self-tapping and inserts), 3 (head seating) and 9 (hole sizes)."""
    holes = {}
    for sc in screws:
        if sc.f.stock and not any(k in sc.part for k in printed):
            continue
        a, b = sc.at(-sc.k - 2), sc.at(sc.L + 3)
        pad = 3 * sc.dn + 8
        lo, hi = np.minimum(a, b) - pad, np.maximum(a, b) + pad
        for pname, body in printed.items():
            if not body.near(lo, hi):
                continue
            h = Hole(sc, body)
            if not h.spans and not (h.inside[(h.s >= -sc.k) & (h.s <= 0)]).any():
                # also a head pocket with no shank span: keep it for the seat check
                if not ((h.s < 0) & (h.r_in.min(axis=1) < sc.D / 2 + 3)).any():
                    continue
            holes[(sc.name, pname)] = h
            meat_rows(T, sc, h, pname, cura)
    return holes


def meat_rows(T, sc, h, pname, cura):
    d = sc.dn
    feat = f"{sc.name} ({sc.f.item})"
    for span in h.spans:
        role = role_of(sc, h, span)
        (m, sd, ang), open_deg, open_kind = h.meat(span)
        L = span[1] - span[0]
        need = R.MEAT_K * d
        if role == "clearance":
            st = "PASS" if m >= need - 0.05 else ("WARN" if m >= R.MEAT_CLEAR_FAIL_K * d else "FAIL")
        else:
            st = "PASS" if m >= need - 0.05 else "FAIL"
        fix = ""
        if st != "PASS":
            fix = (f"add material: make the boss {2 * (h.hole_d(span) / 2 + need):.0f} mm OD round the hole, "
                   f"or move the hole {need - m:.1f} mm away from the edge")
        T.add(pname, feat, f"1 meat round the {role} hole (s {span[0]:.1f}..{span[1]:.1f}, {L:.1f} mm)",
              f"{fmt(m)} mm" + (f" at s {sd:.1f}" if sd is not None else ""), f">= {need:.1f} mm", st, fix)
        if open_deg > 0:
            stt = "FAIL" if (role != "clearance" or open_kind == "breaks out") and open_deg >= 30 else "WARN"
            T.add(pname, feat, f"1 hole wall closed ({role})", f"{open_kind}, {open_deg:.0f} deg open", "0 deg open", stt,
                  "close the wall round the hole, or give the slot a second support (a cheek on the other side)"
                  if stt == "FAIL" else "")
        # The hole size (fit, check 9).
        hd = h.hole_d(span)
        if not math.isnan(hd):
            if role in ("clearance", "axle") and sc.kind != "selftap" and not any(cx["kind"] == "eccentric" for cx in sc.coax):
                lo_, hi_ = d + 0.2, d + 1.2
                st = "PASS" if lo_ <= hd <= hi_ else ("FAIL" if hd < d else "WARN")
                T.add(pname, feat, "9 clearance hole diameter", f"{hd:.2f} mm", f"{lo_:.1f}..{hi_:.1f} (ISO 273 {R.CLEAR_ISO.get(sc.size, 0)})",
                      st, f"make the hole {R.CLEAR_ISO.get(sc.size, d + 0.4):.1f} mm" if st != "PASS" else "")
            elif role == "thread" or sc.kind == "selftap":
                lo_, hi_ = 0.78 * d, 0.95 * d
                st = "PASS" if lo_ - 0.02 <= hd <= hi_ + 0.02 else "WARN"
                T.add(pname, feat, "9 pilot hole diameter (self-tapping)", f"{hd:.2f} mm", f"{lo_:.2f}..{hi_:.2f} mm", st,
                      f"make the pilot {0.85 * d:.1f} mm" if st != "PASS" else "")
        if role == "thread" or (role == "axle" and sc.kind == "selftap" and span[1] >= sc.L - 1.0):
            thread_rows(T, sc, h, span, pname, feat)
        if role == "insert":
            insert_rows(T, sc, h, span, pname, feat)
    seat_rows(T, sc, h, pname, feat)


def thread_rows(T, sc, h, span, pname, feat):
    d = sc.dn
    tip = sc.L - min(0.4 * S.SHANK.get(sc.size, 0.84 * d) / 2, sc.L / 4)
    k = (h.s >= span[0]) & (h.s < min(span[1], tip)) & (h.r_in.min(axis=1) < d / 2 - 0.05)
    eng = k.sum() * STEP
    need = R.SELFTAP_K * d
    jtxt = ""
    if sc.joint:
        past = sc.joint.length - sc.joint.grip
        jtxt = f"; joint data: {past:.1f} mm past the grip, pilot {sc.joint.limit:.1f}"
    st = "PASS" if eng >= need else ("WARN" if eng >= 0.75 * need else "FAIL")
    fix = ""
    if st != "PASS":
        fix = (f"use a {sc.size} screw {math.ceil((sc.L + need - eng) / 2) * 2:.0f} mm long and a pilot {need + 1:.0f} mm deep, "
               f"or a heat-set insert")
    T.add(pname, feat, "2 self-tap thread length (geometry)", f"{eng:.1f} mm{jtxt}", f">= {need:.1f} mm (2 d)", st, fix)
    # Bottoming: the axis point is in solid plastic before the tip.
    solid = h.inside & (h.s > span[0]) & (h.s <= sc.L - 0.25)
    beyond = h.s[(h.s > sc.L) & h.inside]
    free = (beyond.min() - sc.L) if len(beyond) else math.inf
    if solid.any():
        T.add(pname, feat, "2 tip does not bottom out", f"solid from s {h.s[solid].min():.1f}", f"pilot >= {sc.L:.1f} + 0.5",
              "FAIL", f"deepen the pilot to {sc.L + 1:.0f} mm")
    else:
        T.add(pname, feat, "2 tip does not bottom out", f"pilot free {fmt(free)} mm past the tip", ">= 0.5 mm",
              "PASS" if free >= 0.5 else "WARN", "" if free >= 0.5 else f"deepen the pilot by {1 - free:.1f} mm")


def insert_rows(T, sc, h, span, pname, feat):
    ins = [cx for cx in sc.coax if cx["kind"] == "insert"][0]
    meta = getattr(ins["f"], "meta", {}) or {}
    spec = getattr(S, "INSERT_M5", {}) if sc.size == "M5" else {}
    od = meta.get("od", spec.get("od", 2 * ins["r"]))
    ln = meta.get("len", spec.get("len", ins["s1"] - ins["s0"]))
    # The boss: the material round the insert pocket.
    k = (h.s >= ins["s0"] + 0.3) & (h.s <= ins["s1"] - 0.3)
    idx = np.where(k)[0]
    m = math.inf
    for i in idx:
        closed = h.r_in[i] <= ins["r"] + 1.0
        if closed.any():
            m = min(m, float(np.min(np.where(closed, h.r_out[i] - h.r_in[i], math.inf))))
    hole_r = float(np.median(h.r_in[idx].min(axis=1))) if len(idx) else od / 2
    boss = 2 * (hole_r + m)
    need = R.INSERT_BOSS_K * od
    good = R.INSERT_BOSS_GOOD_K * od
    st = "PASS" if boss >= good else ("WARN" if boss >= need else "FAIL")
    T.add(pname, feat, "1 insert boss diameter (material OD round the insert)", f"{boss:.1f} mm (wall {m:.1f})",
          f">= {need:.1f} (1.5 x OD {od}); {good:.0f} preferred", st,
          f"make the boss {good:.0f} mm OD" if st != "PASS" else "")
    # The hole depth: from the open end of the pocket to its floor.
    big = h.r_in.min(axis=1) >= min(hole_r, od / 2) - 0.4
    kk = np.where(big & (h.s >= ins["s0"] - 3) & (h.s <= ins["s1"] + 6) & (h.r_in.min(axis=1) < h.rmax))[0]
    depth = (kk.max() - kk.min() + 1) * STEP if len(kk) else 0.0
    st = "PASS" if depth >= ln + R.INSERT_DEPTH_EXTRA - 0.25 else "WARN"
    T.add(pname, feat, "1 insert hole depth", f"{depth:.1f} mm", f">= {ln + R.INSERT_DEPTH_EXTRA:.1f} (insert {ln} + 1)", st,
          f"deepen the insert hole to {ln + 1.5:.1f} mm" if st != "PASS" else "")
    # Engagement in the insert.
    tip = sc.L - 0.4
    eng = max(0.0, min(tip, ins["s1"]) - max(0.0, ins["s0"]))
    need = R.INSERT_ENGAGE_K * sc.dn
    st = "PASS" if eng >= need else ("WARN" if eng >= 0.7 * need else "FAIL")
    T.add(pname, feat, "2 thread in the insert", f"{eng:.1f} mm (insert {ln} mm long)", f">= {need:.1f} mm (1.5 d)", st,
          f"use a long insert ({sc.size} x {math.ceil(need + 1):.0f} mm or more) and a screw that passes through it"
          if st != "PASS" else "")
    past = sc.L - ins["s1"]
    solid = h.inside & (h.s > ins["s1"]) & (h.s <= sc.L)
    st = "FAIL" if solid.any() else "PASS"
    T.add(pname, feat, "2 tip does not bottom out past the insert", f"tip {past:+.1f} mm past the insert", "free hole past the insert",
          st, "deepen the hole past the insert" if st == "FAIL" else "")


def seat_rows(T, sc, h, pname, feat):
    """Head seating on this printed part: the flat seat under the head or the washer, the
    counterbore, and the preload on the PLA."""
    w = [cx for cx in sc.coax if cx["kind"] == "washer" and -0.3 <= cx["s0"] <= 0.5]
    s_seat = w[0]["s1"] if w else 0.0
    R_seat = w[0]["r"] if w else sc.D / 2
    i = int(np.argmin(np.abs(h.s - (s_seat + STEP / 2))))
    if not (h.inpart[i] or h.inside[i]):
        return False
    # Points in the annulus under the seat, 0.3 mm deep.
    d, u, v = geo.basis(sc.d)
    r0 = max(float(np.min(h.r_in[i])), sc.dn / 2) + 0.1
    if r0 >= R_seat - 0.1:
        return False
    pts = []
    for r in np.linspace(r0, R_seat - 0.1, 4):
        for a in np.linspace(0, 2 * math.pi, 24, endpoint=False):
            pts.append(sc.at(s_seat + 0.3) + r * (math.cos(a) * u + math.sin(a) * v))
    below = h.body.inside(np.array(pts)).mean()
    pts_up = [p - 0.6 * d for p in pts]
    above = h.body.inside(np.array(pts_up)).mean()
    what = "washer" if w else f"{sc.head} head"
    st = "PASS" if below >= R.SEAT_MIN and above < 0.02 else ("WARN" if below >= R.SEAT_FAIL and above < 0.1 else "FAIL")
    T.add(pname, f"{sc.name} ({sc.f.item})", f"3 flat seat under the {what} ({2 * R_seat:.1f} mm)",
          f"{below * 100:.0f} % bears, {above * 100:.0f} % above the seat", f">= {R.SEAT_MIN * 100:.0f} %, 0 % above", st,
          "" if st == "PASS" else f"make a flat spot face {2 * R_seat + 1:.0f} mm across, square to the screw")
    # The counterbore round the head.
    j = int(np.argmin(np.abs(h.s - (-0.25))))
    rr = h.r_in[j]
    if np.isfinite(rr).any() and rr.min() < sc.D / 2 + 3 and not w:
        gap = float(rr.min()) - sc.D / 2
        st = "PASS" if gap >= 0.25 else ("WARN" if gap >= 0 else "FAIL")
        T.add(pname, f"{sc.name} ({sc.f.item})", "3 counterbore round the head (gap each side)", f"{gap:.2f} mm",
              ">= 0.25 mm (FDM holes print small)", st,
              "" if st == "PASS" else f"make the counterbore {sc.D + 1.0:.1f} mm")
        hk = h.s[(h.s >= -sc.k) & (h.s < 0)]
        if len(hk):
            pass
    # Preload on the PLA under the head or the washer.
    tq = R.TORQUE_SNUG.get(sc.size, 1.0)
    k = R.NUT_FACTOR
    if sc.kind == "selftap":
        tq *= R.SELFTAP_TORQUE_K
        k = R.NUT_FACTOR_SELFTAP
    Fp = tq / (k * sc.dn * 1e-3)
    r_h = max(float(np.min(h.r_in[i])), sc.dn / 2)
    area = math.pi * (R_seat ** 2 - r_h ** 2)
    p = Fp / max(area, 1e-6)
    sf = R.PLA_COMP / p
    st = R.status_pre(sf)
    tmax = tq * sf / R.SF_PRE
    T.add(pname, f"{sc.name} ({sc.f.item})", f"3 preload on the PLA under the {what} at {tq:.2f} N m",
          f"{p:.0f} MPa, SF {sf:.1f}", f"SF >= {R.SF_PRE:.0f} ({R.PLA_COMP:.0f} MPa ESTIMATE)", st,
          "" if st == "PASS" else (f"tighten to {tmax:.2f} N m at most" +
                                   ("" if w else f", or put a washer under the head ({sc.size} washer)")))
    return True


def check_nut_seats(T, screws, holes):
    """A nyloc or a nut on PLA with no washer: flag it."""
    for sc in screws:
        for cx in sc.coax:
            if cx["kind"] not in ("nyloc", "nut"):
                continue
            wash = [w for w in sc.coax if w["kind"] == "washer" and abs(w["s1"] - cx["s0"]) < 0.6]
            for (sn, pname), h in holes.items():
                if sn != sc.name:
                    continue
                s = cx["s0"] - 0.3
                i = int(np.argmin(np.abs(h.s - s)))
                if not h.inpart[i] or h.pocket[i] and h.r_in[i].min() > cx["r"]:
                    continue
                # Is the nut in a pocket (a nut trap) of this part? Then it is captured.
                trap = h.pocket[(h.s >= cx["s0"]) & (h.s <= cx["s1"])]
                mid = int(np.argmin(np.abs(h.s - (cx["s0"] + cx["s1"]) / 2)))
                captured = bool((h.r_in[mid] < cx["r"] + 1.5).mean() >= 0.5)
                if captured:
                    T.add(pname, f"{sc.name}: {cx['item']}", "3 nut in a nut trap", "captured", "-", "PASS")
                    continue
                st = "PASS" if wash else "WARN"
                T.add(pname, f"{sc.name}: {cx['item']}", "3 washer under the nut on PLA", "washer" if wash else "no washer",
                      "a washer", st, "" if wash else f"put an {sc.size} washer under the nut")


def check_joints(T, screws, joints):
    """Check 2 for the nut, T-nut, insert and tapped joints, from the joint data and the solids.
    Cross-check with fasteners.check_joint (the check of model.py)."""
    seen = set()
    for sc in screws:
        j = sc.joint
        feat = f"{sc.name} ({sc.f.item})"
        if j is None:
            if not sc.f.stock:
                T.add(sc.part, feat, "2 joint data", "no Joint in fasteners.py", "a Joint", "WARN", "add a Joint for this screw")
            continue
        if j.name not in seen:
            seen.add(j.name)
            ok, txt = F.check_joint(j)
            T.add(sc.part, j.name, "2 model.py length check (cross-check)", txt, "model.py rule", "PASS" if ok else "FAIL",
                  "" if ok else "change the screw length (see model.py)")
        pitch = R.PITCH.get(sc.size, 0.8)
        if j.kind == "nut":
            nuts = [cx for cx in sc.coax if cx["kind"] in ("nut", "nyloc")]
            if not nuts:
                T.add(sc.part, feat, "2 nut on the axis", "no nut found", "a nut", "WARN")
                continue
            n = max(nuts, key=lambda cx: cx["s1"])
            out = sc.L - n["s1"]
            need = (R.NYLOC_PASS_PITCH if n["kind"] == "nyloc" else R.NUT_PASS_PITCH) * pitch
            st = "PASS" if out >= need else ("WARN" if out >= 0 else "FAIL")
            T.add(sc.part, feat, f"2 screw past the {n['item']}", f"{out:.1f} mm", f">= {need:.1f} mm", st,
                  "" if st == "PASS" else f"use a screw {math.ceil(sc.L + need - out):.0f} mm long or more")
        elif j.kind == "tnut":
            past = j.length - j.grip
            eng = min(past - S.SLOT_LIP, S.TNUT[2])
            st = "PASS" if eng >= S.TNUT[2] - 0.05 else ("WARN" if eng >= S.TNUT_ENGAGE else "FAIL")
            T.add(sc.part, feat, "2 screw through the full T-nut thread", f"{eng:.1f} of {S.TNUT[2]:.1f} mm",
                  f"{S.TNUT[2]:.1f} mm", st, "" if st == "PASS" else f"use M5 x {math.ceil(j.grip + S.SLOT_LIP + S.TNUT[2]):.0f}")
            st = "PASS" if past <= S.SLOT_DEPTH else "FAIL"
            T.add(sc.part, feat, "2 tip clear of the slot bottom", f"tip {past:.1f} mm in", f"<= {S.SLOT_DEPTH} mm (ESTIMATE)",
                  st, "" if st == "PASS" else f"use M5 x {math.floor(j.grip + S.SLOT_DEPTH):.0f}")
        elif j.kind == "tapped":
            past = j.length - j.grip
            need = 0.8 * sc.dn if sc.size != "M3" else S.MOTOR_ENGAGE
            st = "PASS" if need <= past <= j.limit else "FAIL"
            T.add(sc.part, feat, "2 thread in the metal part", f"{past:.1f} mm of {j.limit:.1f}", f"{need:.1f}..{j.limit:.1f} mm",
                  st, "" if st == "PASS" else "change the screw length")


def check_fits(T, items, screws, holes):
    """Check 9: the clearances of shape.py, and the eccentric spacer and the insert holes."""
    for name, val, comment in R.shape_clearances():
        cls = R.fit_class(comment, name)
        lo, hi = R.FIT_CLASSES[cls]
        st = "PASS" if lo <= val <= hi else "WARN"
        T.add("shape.py", f"{name} ({comment[:60]})", f"9 {cls} fit, gap each side", f"{val:.2f} mm", f"{lo}..{hi} mm", st,
              "" if st == "PASS" else f"set {name} to {(lo + min(hi, lo + 0.3)) / 2:.2f} mm and print a fit test")
    # The eccentric spacer: it must turn in its hole.
    if hasattr(S, "ECC_HOLE") and hasattr(S, "ECC"):
        gap = (S.ECC_HOLE - S.ECC["shank_d"]) / 2
        st = "PASS" if 0.15 <= gap <= 0.4 else "WARN"
        T.add("y_carriage", "eccentric spacer shank in ECC_HOLE", "9 slide fit (turns by hand)", f"{gap:.2f} mm each side",
              "0.15..0.4 mm", st, "" if st == "PASS" else "set ECC_HOLE to shank + 0.5 mm")
    if hasattr(S, "INSERT_M5"):
        ins = S.INSERT_M5
        r = ins["hole"] / ins["od"]
        st = "PASS" if 0.85 <= r <= 0.95 else "WARN"
        T.add("y_carriage", f"M5 heat-set insert hole {ins['hole']} for OD {ins['od']}", "9 insert hole / OD",
              f"{r:.2f}", "0.85..0.95 (insert maker data, ESTIMATE)", st)
    # The idler bosses: a washer or a boss must touch only the inner race of the idler bearing.
    rb = 7.5 / 2   # ESTIMATE: the inner race OD of a 625 bearing (5 x 16 x 5) is about 7.5 to 8 mm
    for sc in screws:
        if not any("idler" in a.lower() for a in sc.f.allow):
            continue
        for cx in sc.coax:
            if cx["kind"] == "washer":
                st = "PASS" if cx["r"] <= rb + 0.6 else "WARN"
                T.add(sc.part, f"{sc.name}: {cx['item']}", "9 washer touches only the inner race of the idler",
                      f"washer OD {2 * cx['r']:.1f} mm", f"<= {2 * rb + 1.2:.1f} mm (625 inner race, ESTIMATE)", st,
                      "" if st == "PASS" else "use a 5 x 8 x 1 shim or a printed shoulder of 7 mm OD; check the idler has its own shoulder")
                break


def part_walls(T, printed, cura):
    """The solid ring round each hole is the wall thickness of the slicer profile; the rest is infill."""
    for pname in printed:
        prof = cura.get(pname) or cura.get(pname.replace("_left", "").replace("_right", ""))
        if not prof:
            T.add(pname, "slicer profile", "6 walls and infill", "no profile found", "a profile", "WARN",
                  "add a profile in cura/make_profiles.py")
            continue
        wt, inf = prof.get("wall_thickness", 1.5), prof.get("infill_sparse_density", 20)
        st = "PASS" if wt >= 2.0 or inf >= 40 else "WARN"
        T.add(pname, "slicer profile", "6 solid ring round holes (walls) / infill", f"{wt:.1f} mm walls, {inf} % infill",
              ">= 2.0 mm walls or >= 40 % infill on loaded parts", st,
              "" if st == "PASS" else "set 5 walls (2.5 mm) and 40 % infill for the loaded parts")


def read_cura():
    """The walls and infill of each part from cura/make_profiles.py (by STL name)."""
    import importlib.util
    import os
    path = os.path.join(geo.HW, "cura", "make_profiles.py")
    spec = importlib.util.spec_from_file_location("audit_make_profiles", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for p in mod.PROFILES:
        v = {**mod.COMMON, **p["values"]}
        out[p["stl"][:-4]] = v
    # The left and right copies share the profile of their STL.
    for k in list(out):
        out.setdefault(k + "_left", out[k])
        out.setdefault(k + "_right", out[k])
    return out


def check_clash(T, screws, holes):
    """The screw solid must not cut into the printed part (a head in a wall, a shank in the plastic)."""
    for (sn, pname), h in holes.items():
        sc = h.sc
        try:
            common = sc.f.solid & h.body.solid
            v = 0.0 if common is None else common.volume
        except Exception:  # noqa: BLE001
            continue
        if v > 0.2:
            T.add(pname, f"{sc.name} ({sc.f.item})", "3 screw clear of the part (head and shank)", f"{v:.1f} mm3 overlap",
                  "0 mm3", "FAIL", "open the counterbore or move the wall clear of the head")
