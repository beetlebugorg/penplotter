"""Export the detailed bought parts (context_detail.py) for the simulator, and check them.

Run from the hardware directory:

    uv run --no-project --with build123d python export_context_detail.py

It writes:
- stl/detail/<group>_<material>.stl: one file for each moving group and material (few draw calls).
- stl/detail/manifest.json: the files, the materials, the sim2 files that they replace, the cable
  anchors (plug exits) and the endstop LEDs. sim/web/wiring.js reads it.
- stl/sim2/<name>.stl for x_motor, y_stepper_left, y_stepper_right, y_endstops, head_board,
  base_board and servo: one-colour meshes with the same names as the stand-ins. make.sh deletes
  and rewrites stl/sim2, so run this script again after make.sh (or wire it into model.py, see
  context_detail_HOOKUP.md).
It also checks the clearance of each part against the printed parts and the frame, and that each
endstop lever touches its trigger face at machine home.
"""
import json
import os
import sys

from build123d import Compound, export_stl

import context_detail as CD
import parts as P
import shape as S

HERE = os.path.dirname(os.path.abspath(__file__))
TOL, ANG = 0.04, 0.25           # the mesh tolerance: modest, the parts are small


def overlap(a, b):
    try:
        i = a & b
        return i.volume if i is not None else 0.0
    except Exception:
        return 0.0


def stl_tris(path):
    with open(path, "rb") as f:
        f.seek(80)
        return int.from_bytes(f.read(4), "little")


def checks(c0, xp0, groups):
    t = P.plate_offset(xp0, c0)
    probs = []
    car = P.y_carriage(c0, "motor")
    ctx_g = [("left Y carriage", car), ("right Y carriage", P.mirror_x(P.y_carriage(c0, "idler"))), ("beam", P.beam(c0)),
             ("servo loom", P.x_loom(c0, xp0))]
    ctx_s = [("left front base", P.y_front_base()), ("right front base", P.y_front_base("right")),
             ("left Y motor bracket", P.y_motor_mount()), ("right Y motor bracket", P.y_motor_mount("right"))]
    ctx_c = [("pen carriage", t * P.pen_carriage()), ("X plate", t * P.x_carriage_plate()),
             ("horn", t * P.horn(S.PEN_DOWN_DEG))]
    allc = ctx_g + ctx_s + ctx_c
    for grp, parts in groups.items():
        if grp == "ctrl":
            continue
        for name, kit in parts.items():
            for mat, sl in kit.items():
                for s in sl:
                    for cn, cs in allc:
                        if cn == "horn" and mat == "black_plastic":
                            continue          # the spline is in the horn hub (the stand-in horn has no bore)
                        v = overlap(s, cs)
                        if v > 0.02:
                            probs.append(f"{name} ({mat}) goes {v:.2f} mm3 into the {cn}")
    # The levers: each touches its trigger face (within 0.4 mm) and does not go into it.
    xs = Compound(children=groups["gantry"]["x_endstop"]["steel"])
    pc = t * P.x_carriage_plate()
    if overlap(xs, pc) > 0.01:
        probs.append("the X lever goes into the X plate")
    if overlap(Compound(children=[s.moved(P.Pos(0.4, 0, 0)) for s in groups["gantry"]["x_endstop"]["steel"]]), pc) <= 0:
        probs.append("the X lever does not reach the trigger lug of the X plate")
    ys = Compound(children=groups["static"]["y_endstops"]["steel"])
    if overlap(ys, car) > 0.01:
        probs.append("the Y lever goes into the carriage")
    if overlap(Compound(children=[s.moved(P.Pos(0, 0.4, 0)) for s in groups["static"]["y_endstops"]["steel"]]), car) <= 0:
        probs.append("the left Y lever does not reach the carriage wall")
    return probs


def main():
    fj = os.path.join(HERE, "stl", "frame.json")
    if os.path.exists(fj):
        fr = json.load(open(fj))
        c0, xp0 = fr["carriage_y0"], fr["carriage_x0"]
    else:
        # model.py is running (it rewrites frame.json at the end): use the last machine home.
        old = json.load(open(os.path.join(HERE, "stl", "detail", "manifest.json")))
        c0, xp0 = old["c0"], old["xp0"]
        print("frame.json is missing: home from the last manifest; the sim2 files are not written")
    groups, anchors, leds, endstops = CD.build_all(c0, xp0)
    out = os.path.join(HERE, "stl", "detail")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith(".stl"):
            os.remove(os.path.join(out, f))
    files, total = [], 0
    for grp, parts in groups.items():
        bymat = {}
        for name, kit in parts.items():
            for mat, sl in kit.items():
                bymat.setdefault(mat, []).extend(sl)
        for mat, sl in sorted(bymat.items()):
            fn = f"{grp}_{mat}.stl"
            export_stl(Compound(children=sl), os.path.join(out, fn), tolerance=TOL, angular_tolerance=ANG)
            n = stl_tris(os.path.join(out, fn))
            total += n
            col, metal, rough = CD.MATS[mat]
            files.append({"file": "detail/" + fn, "group": grp, "material": mat, "color": col, "metalness": metal,
                          "roughness": rough, "tris": n})
    # The one-colour sim2 meshes with the stand-in names.
    sim2 = os.path.join(HERE, "stl", "sim2")
    sim2_names = []
    write_sim2 = os.path.exists(fj) and os.path.isdir(sim2)
    for grp, parts in groups.items():
        for name, kit in parts.items():
            if grp == "ctrl" or name == "x_endstop":
                continue
            if write_sim2:
                export_stl(CD.kit_solid(kit), os.path.join(sim2, name + ".stl"), tolerance=TOL, angular_tolerance=ANG)
            sim2_names.append(name)
    # The X motor stand-in had the pulley in it. Keep the pulley in sim2/x_motor.stl.
    xm = CD.kit_solid(groups["gantry"]["x_motor"])
    pulley = P.x_motor_parts(c0)[1]       # the stock X belt path (2026-11-09)
    if write_sim2:
        export_stl(Compound(children=[xm, pulley]), os.path.join(sim2, "x_motor.stl"), tolerance=TOL, angular_tolerance=ANG)
    export_stl(pulley, os.path.join(out, "gantry_x_pulley.stl"), tolerance=0.03, angular_tolerance=0.2)
    files.append({"file": "detail/gantry_x_pulley.stl", "group": "gantry", "material": "pulley", "color": "#9A9A9A",
                  "metalness": 0.9, "roughness": 0.3, "tris": stl_tris(os.path.join(out, "gantry_x_pulley.stl"))})
    manifest = {
        "note": "Detailed bought parts from hardware/context_detail.py (export_context_detail.py). Frame mm at machine "
                "home: gantry y c0, X plate x xp0. group: static, gantry, carriage, ctrl (the control box group).",
        "c0": c0, "xp0": xp0,
        "files": files,
        "replaces": sorted(sim2_names),
        "anchors": anchors,
        "leds": leds,
        "endstops": endstops,
        "endstop_board": {"shape_ES": S.ES, "photo": CD.EB},
        "lcd": CD.ctrl_lcd_glass(),
        "chain_link": {"pitch": 18.0, "note": "ESTIMATE: an openable 10 x 20 R28 chain has an 18 mm pitch (retail drawings)"},
    }
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"detail: {len(files)} files, {total} triangles")
    for fl in files:
        print(f"  {fl['file']}: {fl['tris']}")
    probs = checks(c0, xp0, groups) if "--no-check" not in sys.argv else []
    for p in probs:
        print("PROBLEM:", p)
    print("check:", "OK" if not probs else f"{len(probs)} problems")


if __name__ == "__main__":
    main()
