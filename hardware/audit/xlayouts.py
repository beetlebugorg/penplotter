#!/usr/bin/env python3
"""The X carriage layouts (2026-11-09): FEA of the X plate with the pen carriage on it, for the layout
comparison in REVIEW.md. Each layout is the printed X plate and the pen carriage as one solid (the
one-piece layout is that solid; the two-part layout is bolted with 4 M3 screws, so the FEA is a little
stiffer than the real part). Fixed at the three wheel axles. Operating loads: the head inertia at the
firmware acceleration on the left belt clamp, the pen drag (1 N in X and in Y) on the slider rail. Worst
case: the stall tension on the clamps. Probe: the slider rail (the pen axis), limit 0.05 mm.

Run from hardware/:
  uv run --no-project --with build123d python audit/xlayouts.py build     (STEP files and the spec)
  uv run --no-project --python 3.12 --with gmsh --with scikit-fem --with matplotlib --with pyamg \
      --with pypardiso --with scipy python audit/fea.py audit/out/xlayouts/fea_spec.json
  uv run --no-project --with build123d python audit/xlayouts.py report"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
sys.path[:0] = [HERE, HW]
OUT = os.path.join(HERE, "out", "xlayouts")

import rules as R  # noqa: E402
import shape as S  # noqa: E402

# name: (description, top wheel x, plate thickness above/below the beam)
LAYOUTS = {
    "A_two_part": ("printed X plate + the pen carriage (two parts, 4 M3), top wheels 46.5 mm apart",
                   (-17.5, 29.02), 5.0),
    "B_wide_base": ("as A, top wheels 70 mm apart (x -27.0 and 43.0)", (-27.0, 43.0), 5.0),
    "C_one_piece": ("one printed part (plate and pen carriage merged), the same wheels", (-17.5, 29.02), 5.0),
}


def build():
    import importlib
    from build123d import export_step
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for name, (desc, (xl, xr), thick) in LAYOUTS.items():
        import parts as P
        S.X_WHEELS = [("top left", xl, 48.23), ("top right", xr, 48.23), ("bottom", 6.92, 7.73)]
        S.WHEEL_BOLTS = [(n, x, z, S.XW_BOSS_RS[i]) for i, (n, x, z) in enumerate(S.X_WHEELS)]
        S.XP_THICK = thick
        importlib.reload(P)
        plate = P.raw_x_carriage_plate()
        pen = P.raw_pen_carriage()
        solid = plate + pen
        if len(solid.solids()) > 1:
            solid = max(solid.solids(), key=lambda s: s.volume)
        step = os.path.join(OUT, f"{name}.step")
        export_step(solid, step)
        vol = {"plate": plate.volume, "pen": pen.volume}
        # Fixtures: the three wheel axle holes in the bosses.
        fix = []
        for i, (_, x, z) in enumerate(S.X_WHEELS):
            y0, y1 = S.XW_BOSS_Y[i]
            r = (S.ECC_HOLE if i == S.X_ECC else (S.INSERT_M5["hole"] if i == 2 else S.M5_CLEAR)) / 2 + 0.6
            fix.append({"type": "cyl", "p": [x, y0, z], "d": [0, 1, 0], "r": r, "s0": 0.0, "s1": y1 - y0, "dofs": [0, 1, 2],
                        "name": f"wheel axle {i}"})
        # The belt clamps: the clip pockets (left and right), the force on the clip wall along the slant.
        acc, _ = R.firmware_accel()
        m_head = (vol["plate"] + vol["pen"]) * R.PLA_DENSITY * 0.6 + 3 * 20.0 + 9.0 + 47.0 + 35.0 + 15.0
        f_acc = m_head * 1e-3 * acc * 1e-3
        r_p = S.PULLEY_PD / 2
        dt = R.MOTOR_TORQUE / (r_p * 1e-3) / 2
        t_hi, t_lo = R.BELT_T0 + dt, max(R.BELT_T0 - dt, 0.0)
        loads, op = [], []
        zb = S.XB_RUNS[0] - S.PLATE_DZ
        u = (P.XCL_POCKET_U[0] + P.XCL_POCKET_U[1]) / 2
        for side, sgn, t in (("left", -1, t_hi), ("right", 1, t_lo)):
            (x0, z0), e, n = P._xcl_frame(side)
            cx, cz = x0 + e[0] * u, z0 + e[1] * u
            reg = {"type": "box", "lo": [cx - 9, S.PLATE_FRONT - 5, cz - 9], "hi": [cx + 9, S.XCL_BACK, cz + 9]}
            loads.append({**reg, "F": [-e[0] * t, 0.0, -e[1] * t], "name": f"belt {side} clamp"})
            if side == "left":
                op.append({**reg, "F": [-e[0] * f_acc / abs(e[0]) * 1.0, 0.0, 0.0], "name": "head inertia"})
        rail = {"type": "box", "lo": [S.RAIL_X - 7, -S.BASE_T - S.RAIL_D - 1, S.SHELF_TOP], "hi": [S.RAIL_X + 7, -S.BASE_T + 0.5, S.RAIL_TOP]}
        loads.append({**rail, "F": [R.PEN_DRAG, R.PEN_DRAG, 0.0], "name": "pen drag"})
        op.append({**rail, "F": [R.PEN_DRAG, R.PEN_DRAG, 0.0], "name": "pen drag"})
        probes = [{**rail, "name": "slider rail (pen axis)", "limit": 0.05}]
        jobs.append({"name": name, "step": step, "h": 2.5, "fix": fix, "loads": loads, "op_loads": op, "probes": probes,
                     "up": [0, 0, 1] if name != "A_two_part" else [0, 0, 1], "desc": desc,
                     "volume_cm3": {k: round(v / 1000, 1) for k, v in vol.items()}, "m_head_g": round(m_head), "f_acc_N": round(f_acc, 2)})
    spec = {"E": R.PLA_E, "nu": R.PLA_NU, "pla_xy": R.PLA_XY, "pla_z": R.PLA_Z, "out": OUT, "parts": jobs}
    json.dump(spec, open(os.path.join(OUT, "fea_spec.json"), "w"), indent=1)
    print("wrote", os.path.join(OUT, "fea_spec.json"))


def report():
    spec = json.load(open(os.path.join(OUT, "fea_spec.json")))
    res = json.load(open(os.path.join(OUT, "fea.json")))
    for j in spec["parts"]:
        r = res.get(j["name"], {})
        pr = (r.get("probes") or [{}])[0]
        print(f"{j['name']}: {j['desc']}; volume {j['volume_cm3']}; head {j['m_head_g']} g; "
              f"rail deflection {pr.get('max_disp', float('nan')) * 1000:.1f} um operating, "
              f"{pr.get('worst_disp', float('nan')) * 1000:.0f} um worst; max von Mises {r.get('vm_max_away', float('nan')):.1f} MPa")


if __name__ == "__main__":
    {"build": build, "report": report}[sys.argv[1]]()
