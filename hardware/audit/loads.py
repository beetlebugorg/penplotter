"""Checks 5, 6 and 7: the load cases, the axles and bosses, the motor screws, the thread pull-out,
the layer orientation, and the FEA load set of each critical part."""

import math

import numpy as np

import geo
import rules as R
import shape as S
from checks import STEP, fmt, is_axle


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def perp(v, d):
    v = np.asarray(v, float)
    return v - (v @ d) * d


def centre(body):
    return (body.lo + body.hi) / 2


def load_cases(printed, other):
    """The load cases, with their values and sources: a dict of name -> (value, unit, source)."""
    acc, src = R.firmware_accel()
    r_p = S.PULLEY_PD / 2 if hasattr(S, "PULLEY_PD") else 6.366
    t0 = R.BELT_T0
    dt = R.MOTOR_TORQUE / (r_p * 1e-3) / 2
    # The moving masses. Printed parts: the volume x density x 0.6 (ESTIMATE: walls and 15 % infill).
    vol = {n: b.solid.volume for n, b in printed.items()}
    gantry_print = sum(v for n, v in vol.items() if n.startswith(("y_carriage", "x_idler_fork")))
    head_print = sum(v for n, v in vol.items() if n in ("pen_carriage", "pen_slider", "x_carriage_plate"))
    beam_l = getattr(S, "BEAM_L", 335.0)
    m_head = head_print * R.PLA_DENSITY * 0.6 + R.X_PLATE_MASS + 9.0 + 15.0   # + servo 9 g, pen 15 g (ESTIMATE)
    # Fixed Y motors (2026-11-09): only the X motor rides on the gantry.
    m_gantry = gantry_print * R.PLA_DENSITY * 0.6 + 1 * S.XMOTOR_MASS + beam_l * R.BEAM_MASS_PER_MM + m_head
    lc = {
        "belt_t0": (t0, "N per run", "ESTIMATE: GT2 6 mm static tension, 20 to 40 N typical; the upper value"),
        "accel": (acc, "mm/s2", f"firmware Accel, {src}"),
        "m_head": (m_head, "g", "printed head parts x 0.6 (infill) + X wheels and axles %.0f g + servo 9 g + pen 15 g (ESTIMATE)" % R.X_PLATE_MASS),
        "m_gantry": (m_gantry, "g", "printed gantry parts x 0.6 + the X motor (42-34, measured) %.0f g + beam %.0f mm x 0.49 g/mm + head (ESTIMATE)"
                     % (S.XMOTOR_MASS, beam_l)),
        "f_acc_head": (m_head * 1e-3 * acc * 1e-3, "N", "m_head x accel"),
        "f_acc_gantry": (m_gantry * 1e-3 * acc * 1e-3, "N", "m_gantry x accel (both Y belts)"),
        "torque": (R.MOTOR_TORQUE, "N m", "ESTIMATE: 40 mm NEMA17 holding torque"),
        "pulley_r": (r_p, "mm", "GT2 20T pitch radius (shape.PULLEY_PD / 2)"),
        "f_stall": (R.MOTOR_TORQUE / (r_p * 1e-3), "N", "torque / pulley radius: the belt force when the axis is blocked"),
        "dt_stall": (dt, "N", "half of f_stall on each run (equal run stiffness, ESTIMATE)"),
        "t_max": (t0 + dt, "N", "belt_t0 + dt_stall: the highest run tension"),
        "servo": (R.SERVO_TORQUE / (S.HORN_L * 1e-3), "N", "SG90 stall 0.18 N m (ESTIMATE) / horn %.0f mm" % S.HORN_L),
        "hand": (R.HAND_PUSH, "N", "ESTIMATE: an accidental push on the gantry by hand"),
        "pen_drag": (R.PEN_DRAG, "N", "ESTIMATE: pen friction on paper"),
        "wheel": (R.WHEEL_PRELOAD + m_gantry * 1e-3 * R.G / 6 + R.HAND_PUSH / 3, "N",
                  "eccentric preload 30 N (ESTIMATE) + gantry weight / 6 wheels + hand push / 3"),
    }
    return lc


def find_body(bodies, keys, p, d, tol=4.0, s_range=(-15.0, 60.0)):
    best = None
    for b in bodies:
        n = b.name.lower()
        if not any(k.lower() in n for k in keys):
            continue
        s = float((centre(b) - p) @ d)
        if not s_range[0] <= s <= s_range[1]:
            continue
        dist = geo.dist_to_axis(centre(b), p, d)
        if dist < tol and (best is None or dist < best[0]):
            best = (dist, b)
    return best[1] if best else None


def nearest(bodies, key, p):
    cands = [b for b in bodies if key.lower() in b.name.lower()]
    if not cands:
        return None
    return min(cands, key=lambda b: np.linalg.norm(centre(b) - p))


def axle_load(sc, other, lc):
    """The force on the axle: (magnitude N, unit direction, source text, rotating body)."""
    keys = [a for a in sc.f.allow]
    rot = find_body(other, keys, sc.p, sc.d, s_range=(-sc.k - 2, sc.L + 2))
    if rot is None:
        return None
    c = centre(rot)
    name = rot.name.lower()
    tmax = lc["t_max"][0]
    if "y idler" in name:
        pul = nearest(other, "Y pulley", c)
        dy = np.sign(centre(pul)[1] - c[1]) if pul is not None else 1.0
        return 2 * tmax, np.array([0, dy, 0.0]), "2 x t_max (180 deg wrap, both runs to the motor)", rot
    if "x idler" in name:
        mot = nearest(other, "X motor", c)
        dirn = unit(perp(centre(mot) - c, sc.d)) if mot is not None else np.array([-1.0, 0, 0])
        return 2 * tmax, dirn, "2 x t_max (180 deg wrap)", rot
    if "idler" in name:
        pul = nearest(other, "Y pulley", c)
        if pul is None:
            return math.sqrt(2) * tmax, np.array([0, 0, 1.0]), "sqrt(2) x t_max", rot
        pc = centre(pul)
        dy = np.sign(c[1] - pc[1])
        dz = np.sign(pc[2] - c[2])
        dirn = unit(np.array([0, dy, dz]))
        return math.sqrt(2) * tmax, dirn, "sqrt(2) x t_max (90 deg wrap: one run along the rail, one to the pulley)", rot
    if "wheel" in name:
        rail = nearest(other, "rail", c)
        dz = np.sign(centre(rail)[2] - c[2]) if rail is not None else -1.0
        return lc["wheel"][0], np.array([0, 0, dz or -1.0]), "wheel load (preload + weight + push)", rot
    return None


def clamped_rows(T, sc, pname, feat, F, lever, s0, s1, s_load, b_len, d):
    """A cantilever axle. Two models:
    - clamped: the nut (or the insert, or the self-tapping thread) clamps the stack (spacer, washer,
      inner race) on the face of the support. The moment F x lever makes a contact pressure on
      the face under the stack, on top of the preload. The joint must not open.
    - loose: the joint has lost its preload. The axle bears on the hole as a pin in a socket:
      p = F / (d b) x (1 + 6 a / b)."""
    face = s0 if s_load < s0 else s1
    stack = [cx for cx in sc.coax if cx["kind"] in ("spacer", "washer", "eccentric", "nut", "nyloc", "insert")
             and min(abs(cx["s1"] - face), abs(cx["s0"] - face)) < 1.0]
    p_loose = F / (d * b_len) * (1 + 6 * lever / b_len)
    sf_l = R.PLA_COMP / max(p_loose, 1e-6)
    T.add(pname, feat, f"7 PLA bearing, loose joint model ({F:.0f} N at {lever:.1f} mm)", f"{p_loose:.1f} MPa, SF {sf_l:.1f}",
          f"SF >= 3 on {R.PLA_COMP:.0f} MPa (WARN only)", "PASS" if sf_l >= R.SF else "WARN",
          "" if sf_l >= R.SF else "keep the nut tight (thread locker or nyloc); a longer boss lowers this stress")
    if not stack:
        return
    D = 2 * max(cx["r"] for cx in stack)
    dh = d + 0.5
    if sc.kind == "selftap":
        pre = R.TORQUE_SNUG.get(sc.size, 1.0) * R.SELFTAP_TORQUE_K / (R.NUT_FACTOR_SELFTAP * d * 1e-3)
    else:
        pre = R.TORQUE_SNUG.get(sc.size, 1.0) / (R.NUT_FACTOR * d * 1e-3)
    A = math.pi / 4 * (D ** 2 - dh ** 2)
    W = math.pi * (D ** 4 - dh ** 4) / (32 * D)
    M = F * lever
    p_pre, p_m = pre / A, M / W
    sf = R.PLA_COMP / (p_pre + p_m)
    st = R.status_sf(sf)
    T.add(pname, feat, f"7 PLA face under the clamped stack ({D:.1f} mm, preload {pre:.0f} N)",
          f"{p_pre + p_m:.1f} MPa ({p_pre:.1f} preload + {p_m:.1f} moment), SF {sf:.1f}", f"SF >= 3 on {R.PLA_COMP:.0f} MPa",
          st, "" if st == "PASS" else f"put a {math.ceil(D * 1.5):.0f} mm washer on the face, or lower the torque")
    st = "PASS" if p_m * R.SF_PRE <= p_pre else ("WARN" if p_m <= p_pre else "FAIL")
    T.add(pname, feat, "7 clamped stack does not open under the moment", f"moment {p_m:.1f} MPa vs preload {p_pre:.1f} MPa",
          f"moment <= preload / {R.SF_PRE:.0f}", st, "" if st == "PASS" else "a wider spacer face or a second support")


def check_axles(T, screws, holes, other, ups, lc):
    """Check 5 (axles and bosses) and the axle part of checks 6 and 7. Returns the FEA loads."""
    fea = []
    for sc in screws:
        if not is_axle(sc):
            continue
        ld = axle_load(sc, other, lc)
        feat = f"{sc.name} ({sc.f.item})"
        if ld is None:
            T.add(sc.part, feat, "5 axle load", "no rotating part found on the axis", "-", "WARN")
            continue
        F, dirn, src, rot = ld
        s_load = float((centre(rot) - sc.p) @ sc.d)
        sup = []
        for (sn, pname), h in holes.items():
            if sn != sc.name:
                continue
            for sp in h.spans:
                sup.append((sp[0], sp[1], pname, h))
        if not sup:
            T.add(sc.part, feat, "5 axle supports", "no printed support found", ">= 1", "WARN")
            continue
        left = [x for x in sup if x[1] <= s_load + 0.5]
        right = [x for x in sup if x[0] >= s_load - 0.5]
        two = bool(left) and bool(right)
        d = R.NOMINAL[sc.size]
        stock = sc.f.stock
        yld = 340.0 if stock else R.STEEL_YIELD
        if two:
            a_sp = max(left, key=lambda x: x[1])
            b_sp = min(right, key=lambda x: x[0])
            ca, cb = (a_sp[0] + a_sp[1]) / 2, (b_sp[0] + b_sp[1]) / 2
            L = cb - ca
            a, b = s_load - ca, cb - s_load
            M = F * a * b / L
            shares = [(a_sp, F * b / L), (b_sp, F * a / L)]
            T.add(sc.part, feat, "5 axle supports", f"two supports ({a_sp[2]} / {b_sp[2]}), span {L:.1f} mm", "2 or a boss >= 2 d",
                  "PASS")
            lever = 0.0
        else:
            sp = max(sup, key=lambda x: x[1] - x[0]) if not left else max(left, key=lambda x: x[1])
            if not left:
                sp = min(right, key=lambda x: x[0])
            blen = sum(x[1] - x[0] for x in (left or right))
            lever = abs(s_load - (sp[1] if left else sp[0]))
            M = F * lever
            shares = [(sp, F)]
            st = "PASS" if blen >= 2 * d else "FAIL"
            T.add(sc.part, feat, "5 axle supports (cantilever)", f"one support, boss {blen:.1f} mm, lever {lever:.1f} mm",
                  f"boss >= {2 * d:.0f} mm (2 d)", st,
                  "" if st == "PASS" else f"make the boss {2 * d + 2:.0f} mm long, or add a second cheek on the other side of the "
                                          f"{rot.name}")
        sig = 32 * M / (math.pi * R.ROOT_D[sc.size] ** 3)
        sf = yld / max(sig, 1e-6)
        T.add(sc.part, feat, f"7 axle bending ({F:.0f} N, {src})", f"{sig:.0f} MPa, SF {sf:.1f}",
              f"SF >= 3 on {yld:.0f} MPa ({'class 4.8' if stock else 'class 8.8'})", "PASS" if sf >= 3 else
              ("WARN" if sf >= 1.5 else "FAIL"), "" if sf >= 3 else "add a second support")
        for (s0, s1, pname, h), Ri in shares:
            b_len = s1 - s0
            up = ups.get(pname)
            zf = abs(float(dirn @ up)) if up is not None else 0.0
            if two:
                p = Ri / (d * b_len)
                sf = R.PLA_COMP / max(p, 1e-6)
                st = R.status_sf(sf)
                T.add(pname, feat, f"7 PLA bearing at the axle hole ({Ri:.0f} N)", f"{p:.1f} MPa, SF {sf:.1f}",
                      f"SF >= 3 on {R.PLA_COMP:.0f} MPa", st,
                      "" if st == "PASS" else f"make the cheek {math.ceil(b_len * R.SF / max(sf, 0.1)):.0f} mm thick")
            else:
                clamped_rows(T, sc, pname, feat, F, lever, s0, s1, s_load, b_len, d)
            # The tear-out of the ligament in the load direction (check 6: the layers).
            e = h.meat_toward((s0, s1), dirn)
            if math.isnan(e) or e <= 0:
                continue
            sig_t = Ri / (2 * e * b_len)
            strength = R.pla_strength(zf)
            sf = strength / max(sig_t, 1e-6)
            st = R.status_sf(sf)
            T.add(pname, feat, f"6 tear-out toward the load ({'Z' if zf > 0.7 else 'XY' if zf < 0.3 else 'mixed'} layers, "
                               f"|F.z| {zf:.2f})", f"{sig_t:.1f} MPa on {e:.1f} mm, SF {sf:.1f}",
                  f"SF >= 3 on {strength:.0f} MPa", st,
                  "" if st == "PASS" else f"add {math.ceil(e * (R.SF / max(sf, 0.1) - 1)):.0f} mm of material toward the load")
            fea.append({"part": pname, "kind": "axle", "name": sc.name, "p": h.sc.p.tolist(), "d": h.sc.d.tolist(),
                        "r": float(h.hole_d((s0, s1)) / 2 + 0.6),
                        "s0": s0, "s1": s1, "F": (dirn * Ri).tolist(), "half": True})
    return fea


def check_motors(T, screws, holes, other, ups, lc):
    """The motor screws: the shear from the belt and the torque, as bearing on the PLA."""
    fea = []
    groups = {}
    for sc in screws:
        keys = [a for a in sc.f.allow if "motor" in a.lower()]
        if keys:
            groups.setdefault((keys[0], sc.part), []).append(sc)
    for (key, part), scs in groups.items():
        mot = nearest(other, key, scs[0].p)
        if mot is None:
            continue
        mc = centre(mot)
        n = len(scs)
        if "x motor" in key.lower():
            idl = nearest(other, "X idler", mc)
            F = 2 * lc["t_max"][0]
            dirn = unit(perp(centre(idl) - mc, scs[0].d)) if idl is not None else np.array([1.0, 0, 0])
            src = "2 x t_max toward the X idler"
        elif "y motor" in key.lower():
            # Fixed Y motors: both runs go to the idler at the front (180 degree wrap).
            F = 2 * lc["t_max"][0]
            dirn = np.array([0, -1.0, 0])
            src = "2 x t_max toward the Y idler (180 deg wrap)"
        else:
            pul = nearest(other, "Y pulley" if not key.lower().startswith("right") else "right Y pulley", mc)
            idl = [b for b in other if "idler" in b.name.lower() and "x idler" not in b.name.lower()
                   and np.linalg.norm(centre(b) - mc) < 80]
            F = 2 * lc["belt_t0"][0]
            if pul is not None and idl:
                mid = np.mean([centre(b) for b in idl], axis=0)
                dirn = unit(perp(mid - centre(pul), scs[0].d))
            else:
                dirn = np.array([0, 0, -1.0])
            src = "2 x belt_t0 at the pulley (180 deg wrap)"
        tq = lc["torque"][0] * 1e3
        for sc in scs:
            r = geo.dist_to_axis(sc.p, mc, scs[0].d) or 21.9
            V = F / n + tq / (n * r)
            for (sn, pname), h in holes.items():
                if sn != sc.name or not h.spans:
                    continue
                sp = max(h.spans, key=lambda x: x[1] - x[0])
                t = sp[1] - sp[0]
                p = V / (R.NOMINAL[sc.size] * t)
                sf = R.PLA_COMP / p
                st = R.status_sf(sf)
                T.add(pname, f"{sc.name} ({sc.f.item})", f"7 motor screw bearing on the PLA ({V:.0f} N: {src} / {n} + torque)",
                      f"{p:.1f} MPa, SF {sf:.1f}", "SF >= 3", st, "" if st == "PASS" else "use a thicker plate or more screws")
                fea.append({"part": pname, "kind": "motor", "name": sc.name, "p": sc.p.tolist(), "d": sc.d.tolist(),
                            "r": R.NOMINAL[sc.size] / 2 + 1.0, "s0": sp[0], "s1": sp[1], "F": (dirn * F / n).tolist(),
                            "half": True})
    return fea


def check_pullout(T, screws, holes, ups):
    """Self-tapping threads in PLA: the pull-out strength against the preload (checks 6 and 7)."""
    for (sn, pname), h in holes.items():
        sc = h.sc
        if sc.kind != "selftap":
            continue
        for sp in h.spans:
            from checks import role_of
            if role_of(sc, h, sp) != "thread":
                continue
            k = (h.s >= sp[0]) & (h.s < sc.L - 0.3) & (h.r_in.min(axis=1) < sc.dn / 2 - 0.05)
            le = k.sum() * STEP
            if le <= 0:
                continue
            up = ups.get(pname)
            zf = abs(float(sc.d @ up)) if up is not None else 0.0
            tau = R.PLA_SHEAR * R.pla_strength(zf) / R.PLA_XY
            cap = math.pi * sc.dn * le * 0.6 * tau
            tq = R.TORQUE_SNUG.get(sc.size, 0.5) * R.SELFTAP_TORQUE_K
            pre = tq / (R.NUT_FACTOR_SELFTAP * sc.dn * 1e-3)
            sf = cap / pre
            st = R.status_pre(sf)
            tmax = tq * sf / R.SF_PRE
            T.add(pname, f"{sc.name} ({sc.f.item})",
                  f"6/7 thread pull-out ({'across' if zf > 0.7 else 'along' if zf < 0.3 else 'oblique to'} the layers) at {tq:.2f} N m",
                  f"capacity {cap:.0f} N vs preload {pre:.0f} N, SF {sf:.1f}", f"SF >= {R.SF_PRE:.0f} (preload)", st,
                  "" if st == "PASS" else f"tighten to {tmax:.2f} N m at most, or use a heat-set insert")


def fea_spec(screws, holes, printed, other, ups, lc, axle_fea, motor_fea, items):
    """The FEA set: for each critical part, the fixtures, the loads and the probe regions."""
    parts = {}

    def get(p):
        return parts.setdefault(p, {"fix": [], "loads": [], "probes": []})

    for f in axle_fea + motor_fea:
        if f["part"] not in printed or "wheel" in f["name"].lower():
            continue
        get(f["part"])["loads"].append({"type": "cyl", **{k: f[k] for k in ("p", "d", "r", "s0", "s1", "F", "half")},
                                        "name": f["name"]})
    for (sn, pname), h in holes.items():
        sc = h.sc
        if pname not in parts:
            continue
        for sp in h.spans:
            if "Y wheel" in sc.f.allow or any("wheel" in a.lower() for a in sc.f.allow):
                parts[pname]["fix"].append({"type": "cyl", "p": sc.p.tolist(), "d": sc.d.tolist(),
                                            "r": float(sc.dn / 2 + 2.0), "s0": sp[0], "s1": sp[1], "dofs": [0, 1, 2],
                                            "name": sc.name})
    # The X belt tension screw of the idler fork: the fork pulls the end wall toward the motor.
    tmax = lc["t_max"][0]
    for (sn, pname), h in holes.items():
        sc = h.sc
        if "fork" not in " ".join(sc.f.allow).lower() or not h.spans:
            continue
        sp = h.spans[0]
        mot = nearest(other, "X motor", sc.p)
        dirn = unit(perp(centre(mot) - sc.p, np.array([0, 1.0, 0]))) if mot is not None else -sc.d
        reg = {"type": "cyl", "p": sc.p.tolist(), "d": sc.d.tolist(), "r": sc.D / 2 + 0.5, "s0": sp[0] - 0.5, "s1": sp[1],
               "name": sc.name}
        if pname.startswith("y_carriage"):
            get(pname)["loads"].append({**reg, "F": (dirn * 2 * tmax).tolist(), "half": False})
        elif pname == "x_idler_fork" or pname.startswith("y_idler_fork"):
            nut = [cx for cx in sc.coax if cx["kind"] == "nut"]
            if nut:
                get(pname)["fix"].append({"type": "cyl", "p": sc.p.tolist(), "d": sc.d.tolist(), "r": nut[0]["r"] + 1.0,
                                          "s0": nut[0]["s0"] - 0.6, "s1": nut[0]["s1"] + 0.6, "dofs": [0, 1, 2],
                                          "name": "X tension nut"})
    for fk in [k for k in parts if k == "x_idler_fork" or k.startswith("y_idler_fork")]:
        b = printed[fk]
        parts[fk]["fix"].append({"type": "box", "lo": [b.lo[0] - 1, b.lo[1] - 1, b.lo[2] - 0.2],
                                 "hi": [b.hi[0] + 1, b.hi[1] + 1, b.lo[2] + 0.3], "dofs": [2],
                                 "name": "fork sits on its seat"})
    # The Y motor brackets: fixed at the two M5 screws into the back bar. The belt pulls the motor toward the
    # bar, so the face on the bar bears (Y only).
    for mm in [k for k in parts if k.startswith("y_motor_mount")]:
        b = printed[mm]
        parts[mm]["fix"].append({"type": "box", "lo": [b.lo[0] - 1, b.lo[1] - 0.2, b.lo[2] - 1],
                                 "hi": [b.hi[0] + 1, b.lo[1] + 0.3, b.hi[2] + 1], "dofs": [1],
                                 "name": "the bracket face on the back bar"})
    for (sn, pname), h in holes.items():
        if pname.startswith("y_motor_mount") and pname in parts and "bracket screw" in sn and h.spans:
            for sp in h.spans:
                parts[pname]["fix"].append({"type": "cyl", "p": h.sc.p.tolist(), "d": h.sc.d.tolist(),
                                            "r": float(h.sc.dn / 2 + 2.0), "s0": sp[0], "s1": sp[1], "dofs": [0, 1, 2],
                                            "name": sn})
    # The beam end: a hand push in Y, half on each tower, at the beam end screw.
    for (sn, pname), h in holes.items():
        sc = h.sc
        if ("beam end" in sc.name or "beam screw" in sc.name) and pname in parts and h.spans:
            sp = h.spans[0]
            get(pname)["loads"].append({"type": "cyl", "p": sc.p.tolist(), "d": sc.d.tolist(), "r": 10.5, "s0": sp[0],
                                        "s1": sp[1] + 25, "F": [0.0, lc["hand"][0] / 2, 0.0], "half": False,
                                        "name": "hand push on the beam"})
            get(pname)["probes"].append({"type": "cyl", "p": sc.p.tolist(), "d": sc.d.tolist(), "r": 12.0, "s0": sp[0],
                                         "s1": sp[1] + 25, "name": "beam end", "limit": 0.05})
            # The operating load for the accuracy: the inertia of the beam and the head at the
            # firmware acceleration, half on each tower, in Y.
            m_bh = (getattr(S, "BEAM_L", 335.0) * R.BEAM_MASS_PER_MM + lc["m_head"][0]) * 1e-3
            get(pname).setdefault("op_loads", []).append(
                {"type": "cyl", "p": sc.p.tolist(), "d": sc.d.tolist(), "r": 10.5, "s0": sp[0], "s1": sp[1] + 25,
                 "F": [0.0, m_bh * lc["accel"][0] * 1e-3 / 2, 0.0], "name": "beam and head inertia"})
    # The pen carriage: fixed at its screws from the X plate; the X belt ends; the pen drag.
    if "pen_carriage" in printed:
        pc = get("pen_carriage")
        for (sn, pname), h in holes.items():
            if pname == "pen_carriage" and h.sc.name.startswith("head screw") and h.spans:
                for sp in h.spans:
                    pc["fix"].append({"type": "cyl", "p": h.sc.p.tolist(), "d": h.sc.d.tolist(), "r": h.sc.dn / 2 + 1.0,
                                      "s0": sp[0], "s1": sp[1], "dofs": [0, 1, 2], "name": h.sc.name})
        clips = []
        xs = [f for f in clips if f.kind == "clip"]
        if xs:
            cx = np.mean([[f.solid.bounding_box().center().X] for f in xs])
            for f in xs:
                bb = f.solid.bounding_box()
                side = -1.0 if bb.center().X < cx else 1.0
                tension = tmax if side < 0 else lc["belt_t0"][0] - lc["dt_stall"][0]
                reg = {"type": "box", "lo": [bb.min.X - 1.0, bb.min.Y - 1.0, bb.min.Z - 1.0],
                       "hi": [bb.max.X + 1.0, bb.max.Y + 1.0, bb.max.Z + 1.0]}
                pc["loads"].append({**reg, "F": [side * tension, 0.0, 0.0], "name": f.name})
                if side < 0:
                    # Operating: the belt accelerates the head (the net belt force on one clip).
                    pc.setdefault("op_loads", []).append({**reg, "F": [-lc["f_acc_head"][0], 0.0, 0.0],
                                                          "name": "head inertia"})
        # The pen drag on the slider rail (the rail is the pen axis).
        import numpy as _np
        lo = _np.array([S.RAIL_X - 7, -S.BASE_T - S.RAIL_D - 1, S.SHELF_TOP]) + 0.0
        hi = _np.array([S.RAIL_X + 7, -S.BASE_T + 0.5, S.RAIL_TOP]) + 0.0
        sl = printed.get("pen_carriage")
        if sl is not None:
            # The pen carriage solid is in frame coordinates: move the rail box with it.
            off = sl.lo - _np.array([-20.5, -24.0, -53.0])
            lo, hi = lo + off, hi + off
            pc["loads"].append({"type": "box", "lo": lo.tolist(), "hi": hi.tolist(), "F": [lc["pen_drag"][0], 0.0, 0.0],
                                "name": "pen drag on the rail"})
            pc["probes"].append({"type": "box", "lo": lo.tolist(), "hi": hi.tolist(), "name": "pen rail", "limit": 0.05})
            pc.setdefault("op_loads", []).append({"type": "box", "lo": lo.tolist(), "hi": hi.tolist(),
                                                  "F": [lc["pen_drag"][0], 0.0, 0.0], "name": "pen drag"})
    # The printed X plate (2026-11-09): fixed at its three wheel axles (above). The belt pulls each clip
    # along the 45 degree slant toward the beam slot. The pen carriage loads come in at the head screws.
    if "x_carriage_plate" in printed:
        xc = get("x_carriage_plate")
        clips = [f for f in items if f.part == "x_carriage_plate" and f.kind == "clip"]
        if clips:
            cx = np.mean([f.solid.bounding_box().center().X for f in clips])
            for f in clips:
                bb = f.solid.bounding_box()
                side = -1.0 if bb.center().X < cx else 1.0
                tension = tmax if side < 0 else max(lc["belt_t0"][0] - lc["dt_stall"][0], 0.0)
                d = np.array([side * 0.7071, 0.0, 0.7071])          # toward the slot exit
                reg = {"type": "box", "lo": [bb.min.X - 1.5, bb.min.Y - 1.5, bb.min.Z - 1.5],
                       "hi": [bb.max.X + 1.5, bb.max.Y + 1.5, bb.max.Z + 1.5]}
                xc["loads"].append({**reg, "F": (d * tension).tolist(), "name": f.name})
                if side < 0:
                    xc.setdefault("op_loads", []).append({**reg, "F": [-lc["f_acc_head"][0], 0.0, 0.0], "name": "head inertia"})
        heads = [(sn, h) for (sn, pname), h in holes.items() if pname == "x_carriage_plate" and sn.startswith("head screw") and h.spans]
        for sn, h in heads:
            sp = h.spans[0]
            reg = {"type": "cyl", "p": h.sc.p.tolist(), "d": h.sc.d.tolist(), "r": h.sc.dn / 2 + 1.0, "s0": sp[0], "s1": sp[1]}
            f = [lc["pen_drag"][0] / len(heads), lc["pen_drag"][0] / len(heads), 0.0]
            xc["loads"].append({**reg, "F": f, "name": f"pen drag at {sn}"})
            xc.setdefault("op_loads", []).append({**reg, "F": f, "name": f"pen drag at {sn}"})
            xc["probes"].append({**reg, "r": h.sc.dn / 2 + 3.0, "name": f"pen carriage seat ({sn})", "limit": 0.05})
    # The wheel axle fixtures of the parts that got their loads after the first fixture pass (the X plate,
    # the right Y carriage: its only load is the X tension screw now).
    for (sn, pname), h in holes.items():
        sc = h.sc
        if pname not in parts or any(fx["type"] == "cyl" and "wheel" in fx["name"].lower() for fx in parts[pname]["fix"]):
            continue
        if any("wheel" in a.lower() for a in sc.f.allow):
            for sp in h.spans:
                parts[pname].setdefault("late_fix", []).append({"type": "cyl", "p": sc.p.tolist(), "d": sc.d.tolist(),
                                                                "r": float(sc.dn / 2 + 2.0), "s0": sp[0], "s1": sp[1],
                                                                "dofs": [0, 1, 2], "name": sc.name})
    for v in parts.values():
        v["fix"] += v.pop("late_fix", [])
    for p, v in parts.items():
        v["up"] = ups.get(p).tolist() if ups.get(p) is not None else [0, 0, 1.0]
    return parts
