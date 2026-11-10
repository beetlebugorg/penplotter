#!/usr/bin/env python3
"""Fitness audit of the printed hardware: every joint, bolt and hole, from fasteners.py and the
part solids. Prints one row per check and "AUDIT: OK" or "AUDIT: FAIL (n)". Exit code 1 on FAIL.

Run from hardware/:
  uv run --no-project --python 3.12 --with build123d --with trimesh --with rtree --with scipy \
      --with embreex python audit/run.py [--no-fea] [--strict]

  --no-fea   skip the FEA (about 1 minute faster)
  --gate     only the FAILs of the structural checks fail the audit (GATE below); the tool access,
             fit and slicer FAILs are printed but do not stop the build
  --strict   a WARN also fails the audit

Output: audit/out/results.json, audit/out/fea_*.png, audit/report.md."""

import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
sys.path[:0] = [HERE, HW]
OUT = os.path.join(HERE, "out")

import numpy as np  # noqa: E402

import checks as C  # noqa: E402
import geo  # noqa: E402
import loads as LD  # noqa: E402
import rules as R  # noqa: E402

# The check groups that stop the build with --gate: hole meat, thread engagement, the screw clear
# of the part, the axles, the strength (hand calculations, pull-out) and the FEA.
GATE = ("0 the solid is valid", "1 ", "2 ", "3 screw clear", "5 ", "6 tear-out", "6/7", "7 ", "8 ")

FEA_PARTS = {"y_carriage_left": 5.0, "y_carriage_right": 5.0, "x_idler_fork": 1.6, "pen_carriage": 2.5,
             "x_carriage_plate": 2.5, "y_motor_mount_left": 2.5, "y_idler_fork_left": 1.6}


def log(msg):
    print(msg, flush=True)


def limits():
    """The gantry (c) and X plate (xp) travel, from build/parts.json of the last model.py run."""
    try:
        fr = json.load(open(os.path.join(HW, "build", "parts.json")))["frame"]
        return tuple(fr["c"]), tuple(fr["xp"])
    except Exception:  # noqa: BLE001
        return (74.0, 466.0), (70.0, 316.0)


# Parts that go on after the screws of the structure (ESTIMATE of the assembly order): the boards,
# their standoffs and their wires, the belts, the cable chain, the X band, the pen and the camera.
LATER = ("pcb", "tails", "plug", "cable", "board", "standoff", "xh", "belt", "chain", "x band", "pen", "camera", "wire")


def later(name, sc):
    n = name.lower()
    if sc.f.stock and sc.part.startswith("frame"):
        # The frame goes together first: only the bars, the rails and their screws are there.
        return not any(k in n for k in ("bar", "rail"))
    return any(k in n for k in LATER) and not n.startswith(sc.name.lower())


def moved(body, delta):
    if not np.any(delta):
        return body
    b = object.__new__(geo.Body)
    b.name, b.part, b.solid = body.name, body.part, None
    b.mesh = body.mesh.copy()
    b.mesh.apply_translation(delta)
    b.rays = geo.RayMeshIntersector(b.mesh)
    b.lo, b.hi = b.mesh.bounds
    return b


def main():
    t_start = time.time()
    os.makedirs(OUT, exist_ok=True)
    (c0, c1), (x0, x1) = limits()
    cm, xm = (c0 + c1) / 2, (x0 + x1) / 2
    log(f"audit: gantry y {cm:.0f}, X plate x {xm:.0f}; travel ends ({c0:.0f}, {x0:.0f}) and ({c1:.0f}, {x1:.0f})")
    items, joints, jmap = C.build_fasteners(cm, xm)
    screws = [C.Screw(f, joints.get(jmap.get(id(f)))) for f in items if f.kind == "screw"]
    screws = [s for s in screws if not (s.f.stock and s.f.part.startswith("X plate"))]
    C.attach_coaxial(screws, items)
    log(f"  {len(items)} fastener items, {len(screws)} screws, {len(joints)} joints ({time.time() - t_start:.0f} s)")
    printed, other = C.world_bodies(cm, xm)
    log(f"  {len(printed)} printed parts, {len(other)} other solids ({time.time() - t_start:.0f} s)")
    T = C.Table()
    parts_used = {f.part for f in items}
    for p in sorted(parts_used):
        if p not in printed and "stock" not in p and not p.startswith("frame"):
            T.add(p, "part solid", "0 the audit finds the part in the assembly", "not found", "found", "WARN",
                  "add the part name to geo.CTX_PART")
    for p, b in printed.items():
        ok = bool(b.solid.is_valid)
        b.valid = ok
        T.add(p, "part solid", "0 the solid is valid (OCC check)", "valid" if ok else "INVALID", "valid", "PASS" if ok else "FAIL",
              "" if ok else "repair the solid in parts.py (a bad boolean or fillet); STEP export and FEA skip it")
    # The print orientation of each part, from its STL.
    ups = {}
    for p, b in printed.items():
        up, err, stl = geo.print_up(b.mesh, p)
        if up is None:
            T.add(p, "print orientation", "6 STL found", "no STL", "stl/<part>.stl", "WARN")
            continue
        ups[p] = up
        st = "PASS" if err < 0.5 else "WARN"
        ax = "XYZ"[int(np.argmax(np.abs(up)))]
        T.add(p, "print orientation", "6 print +Z read from the STL", f"frame {'+' if up[np.argmax(np.abs(up))] > 0 else '-'}{ax} "
              f"(stl/{stl}.stl, fit {err:.2f} mm)", "fit < 0.5 mm", st)
    cura = C.read_cura()
    holes = C.check_holes(T, screws, printed, cura)
    log(f"  {len(holes)} screw holes in printed parts ({time.time() - t_start:.0f} s)")
    C.check_clash(T, screws, holes)
    C.check_joints(T, screws, joints)
    C.check_nut_seats(T, screws, holes)
    C.check_fits(T, items, screws, holes)
    C.part_walls(T, printed, cura)
    lc = LD.load_cases(printed, other)
    axle_fea = LD.check_axles(T, screws, holes, other, ups, lc)
    motor_fea = LD.check_motors(T, screws, holes, other, ups, lc)
    LD.check_pullout(T, screws, holes, ups)
    log(f"  hand calculations done ({time.time() - t_start:.0f} s)")
    # Check 4: tool access, with the whole assembly, at the middle and the two ends of the travel.
    group_of = {}
    import model as M
    for n, _ in M.ctx_static():
        group_of[n] = "static"
    for f in items:
        group_of[f.name] = f.group
    fbodies = [geo.Body(f.name, f.solid, None, tol=0.1) for f in items if f.kind not in ("belt",)]
    base = list(printed.values()) + other + fbodies
    carriage_names = {n for n, _ in M.ctx_carriage(xm, cm)}

    def grp(b):
        if b.name in group_of:
            return group_of[b.name]
        if b.name in carriage_names:
            return "carriage"
        return "gantry"
    groups = [grp(b) for b in base]
    by_pos = {}
    for (c, x) in ((cm, xm), (c0, x0), (c1, x1)):
        dg = {"static": np.zeros(3), "gantry": np.array([0, c - cm, 0.0]),
              "carriage": np.array([x - xm, c - cm, 0.0]), "pen": np.array([x - xm, c - cm, 0.0])}
        by_pos[f"gantry y {c:.0f}, X x {x:.0f}"] = (dg, [moved(b, dg[g]) for b, g in zip(base, groups)])
    acc = {}
    for sc in screws:
        best = (-1.0, None, None)
        for pos, (dg, bodies) in by_pos.items():
            p0 = sc.at(-sc.k - 0.05) + dg.get(sc.f.group, np.zeros(3))
            kd = R.KEY_D.get((sc.head, sc.size), 0.55 * sc.D)
            need = R.KEY_LEN.get(sc.size, 60.0)
            others = [b for b in bodies if b.name != sc.name and not later(b.name, sc)]
            free, who = geo.axial_free(others, p0, -sc.d, kd / 2, n=8, tmax=need + 5)
            if free > best[0]:
                best = (free, who, pos)
            if free >= need:
                break
        free, who, pos = best
        need = R.KEY_LEN.get(sc.size, 60.0)
        st = "PASS" if free >= need else ("WARN" if free >= R.KEY_SHORT else "FAIL")
        fix = ""
        if st == "WARN":
            fix = f"use the short arm of the key or a ball-end key (the straight line stops at the {who})"
        elif st == "FAIL":
            fix = f"open a key hole through the {who} on the screw axis, or fit this screw before the {who}"
        tool = "Phillips driver" if sc.head == "pan" else f"{sc.head} head key"
        T.add(sc.part, f"{sc.name} ({sc.f.item})", f"4 straight {tool} line from the head",
              f"{min(free, need):.0f} mm" + ("" if free >= need else f" (stop: {who}, at {pos})"), f">= {need:.0f} mm", st, fix)
        acc[sc.name] = (free, who, pos)
    log(f"  tool access done ({time.time() - t_start:.0f} s)")
    # Check 8: FEA.
    fea = {}
    if "--no-fea" not in sys.argv:
        spec = LD.fea_spec(screws, holes, printed, other, ups, lc, axle_fea, motor_fea, items)
        flagged = {r["part"] for r in T.rows if r["status"] == "FAIL" and r["check"].startswith(("5", "7")) and r["part"] in printed}
        todo = dict(FEA_PARTS)
        for p in sorted(flagged):
            todo.setdefault(p, 2.5)
        from build123d import export_step
        jparts = []
        for p, h in todo.items():
            if p in printed and not getattr(printed[p], "valid", True):
                T.add(p, "FEA", "8 FEA run", "skipped: the solid is invalid", "a valid solid", "WARN",
                      "repair the solid, then run the audit again")
                continue
            if p not in printed or p not in spec or not spec[p]["loads"] or not spec[p]["fix"]:
                T.add(p, "FEA", "8 FEA load set", "no loads or no fixtures found", "loads and fixtures", "WARN")
                continue
            step = os.path.join(OUT, f"{p}.step")
            export_step(printed[p].solid, step)
            jparts.append({"name": p, "step": step, "h": h, **spec[p]})
        js = {"E": R.PLA_E, "nu": R.PLA_NU, "pla_xy": R.PLA_XY, "pla_z": R.PLA_Z, "out": OUT, "parts": jparts}
        sp = os.path.join(OUT, "fea_spec.json")
        json.dump(js, open(sp, "w"), indent=1)
        cmd = ["uv", "run", "--no-project", "--python", "3.12", "--with", "gmsh", "--with", "scikit-fem", "--with", "matplotlib",
               "--with", "pyamg", "--with", "pypardiso", "--with", "scipy", "python", os.path.join(HERE, "fea.py"), sp]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        try:
            fea = json.load(open(os.path.join(OUT, "fea.json")))
        except Exception:  # noqa: BLE001
            T.add("FEA", "fea.py", "8 FEA run", "failed: " + (r.stderr or "")[-300:], "runs", "WARN")
        for p, res in fea.items():
            if "error" in res:
                T.add(p, "FEA", "8 FEA run", res["error"][:120], "runs", "WARN", "check the STEP file and the mesh size")
                continue
            sf = res["sf_vm"]
            T.add(p, "FEA", "8 max von Mises away from the fixtures", f"{res['vm_max_away']:.1f} MPa, SF {sf:.1f}",
                  f"SF >= 3 on {R.PLA_XY:.0f} MPa", R.status_sf(sf),
                  "" if sf >= 3 else "add material at the stress peak (see the PNG)")
            sfl = res["sf_layers"]
            T.add(p, "FEA", "8 max principal stress vs the layer strength",
                  f"{res['s1_crit']:.1f} MPa at |n.z| {res['s1_crit_zfrac']:.2f}, SF {sfl:.1f}",
                  f"SF >= 3 on {res['s1_crit_strength']:.0f} MPa", R.status_sf(sfl),
                  "" if sfl >= 3 else "turn the part on the bed or add material: the peak pulls the layers apart")
            for pr in res["probes"]:
                lim = pr.get("limit") or 0.05
                v = pr["max_disp"]
                st = "PASS" if v <= lim else ("WARN" if v <= 2 * lim else "FAIL")
                T.add(p, f"FEA probe: {pr['name']}", "8 deflection at the probe, operating loads (inertia, pen drag)",
                      f"{v * 1000:.2f} um (worst case {pr.get('worst_disp', float('nan')) * 1000:.0f} um)", f"<= {lim * 1000:.0f} um",
                      st, "" if st == "PASS" else "make the part stiffer near the probe (thicker section, ribs)")
            for ld in res["loads"]:
                if ld.get("facets", 0) == 0:
                    T.add(p, f"FEA load: {ld['name']}", "8 load faces found", "0 faces", "> 0", "WARN", "check the load region")
        log(f"  FEA done ({time.time() - t_start:.0f} s)")
    # The table.
    rows = T.rows
    n_fail = sum(r["status"] == "FAIL" for r in rows)
    n_warn = sum(r["status"] == "WARN" for r in rows)
    n_pass = sum(r["status"] == "PASS" for r in rows)
    w = (20, 46, 52, 44, 26)
    log("")
    log(f"{'PART':{w[0]}} {'FEATURE':{w[1]}} {'CHECK':{w[2]}} {'VALUE':{w[3]}} {'LIMIT':{w[4]}} RESULT")
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    for r in sorted(rows, key=lambda r: (r["part"], r["feature"], r["check"])):
        log(f"{r['part'][:w[0]]:{w[0]}} {r['feature'][:w[1]]:{w[1]}} {r['check'][:w[2]]:{w[2]}} {str(r['value'])[:w[3]]:{w[3]}} "
            f"{str(r['limit'])[:w[4]]:{w[4]}} {r['status']}")
    secs = time.time() - t_start
    json.dump({"rows": rows, "loads": {k: list(v) for k, v in lc.items()}, "fea": fea, "counts":
               {"PASS": n_pass, "WARN": n_warn, "FAIL": n_fail}, "seconds": round(secs), "position": [cm, xm],
               "access": {k: [v[0], v[1], v[2]] for k, v in acc.items()}},
              open(os.path.join(OUT, "results.json"), "w"), indent=1, default=str)
    import report
    report.write(os.path.join(OUT, "results.json"), os.path.join(HERE, "report.md"))
    log("")
    log(f"  {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL in {secs:.0f} s; report: audit/report.md")
    if "--gate" in sys.argv:
        gate = [r for r in rows if r["status"] == "FAIL" and r["check"].startswith(GATE)]
        log(f"  --gate: {len(gate)} FAIL in the gate checks; {n_fail - len(gate)} other FAIL do not stop the build")
        bad = len(gate)
    else:
        bad = n_fail + (n_warn if "--strict" in sys.argv else 0)
    log("AUDIT: OK" if bad == 0 else f"AUDIT: FAIL ({bad})")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
