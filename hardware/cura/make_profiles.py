#!/usr/bin/env python3
"""Write one Cura profile for each part of the CR-10 V3 pen plotter, slice each part with
CuraEngine for the real filament use, and check that no part needs supports.

Printer: LulzBot TAZ Workhorse, SE tool head, 0.5 mm nozzle, 2.85 mm PLA. The temperatures and
the fan are the PLA values of the desiccant project on the same printer. No
part uses supports. The support check slices each part again with supports on (support angle
60 degrees, supports everywhere). It must give 0 g of support.

The profile names start with "PenPlotter_", so that the other installers do not remove them.

Usage:
    make_profiles.py            write the files to cura/profiles/, build/filament.json,
                                and build/supports.json
    make_profiles.py --install  also copy them into the Cura configuration (close Cura first)
    make_profiles.py --no-slice do not slice (faster)
"""

import collections
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT))
import shape as S  # noqa: E402
OUT = HERE / "profiles"
BUILD = PROJECT / "build"

CURA = Path.home() / ".local/share/cura/5.13/quality_changes"
# The Cura setting definitions. They list which settings are global and which are for the extruder.
DEFINITIONS = Path.home() / ".local/share/cura-workhorse-profile"
SETTING_VERSION = 27

# Settings that all profiles share. They come from the LulzBot profiles for this tool head.
# The filament shrinks when it cools. These values are a start: 0.3 % horizontally and 0.2 %
# vertically. Cura makes each part larger by these values. For the best fit, print a 100 mm
# test bar in each direction, measure it, and set the values from the result.
SHRINK_XY = 100.3
SHRINK_Z = 100.2

COMMON = {
    "material_shrinkage_percentage_xy": SHRINK_XY,
    "material_shrinkage_percentage_z": SHRINK_Z,
    "layer_0_z_overlap": 0.5,
    "raft_airgap": 0.5,
    "retraction_amount": 1.5,
    "retraction_speed": 15,
    "retract_at_layer_change": True,
    "retraction_min_travel": 3,
    "cool_fan_speed_min": 100,
    "cool_fan_speed_max": 100,
    "cool_fan_full_layer": 5,
    "cool_min_layer_time_fan_speed_max": 0,
    "wall_thickness": 1.5,
    "z_seam_type": "sharpest_corner",
    "z_seam_corner": "z_seam_corner_inner",
    "skin_monotonic": True,
}

# PLA: the values of the desiccant project (220 °C, 60 °C bed, fan 100 %).
# The parts print with 0.3 mm layers ("verydraft" in Cura).
# At 0.3 mm x 0.5 mm, 55 mm/s is 8.25 mm3/s. That is below the flow limit.
LAYER = {
    "layer_height": 0.3,
    "top_bottom_thickness": 0.9,
    "speed_print": 50,
    "speed_infill": 55,
    "speed_wall": 40,
    "speed_wall_0": 30,
    "speed_wall_x": 45,
    "speed_topbottom": 40,
    "speed_layer_0": 18,
    "speed_travel": 150,
    "speed_travel_layer_0": 100,
    "speed_slowdown_layers": 2,
    "material_print_temperature": 220,
    "material_print_temperature_layer_0": 215,
    "material_bed_temperature": 60,
    "material_bed_temperature_layer_0": 60,
    "support_enable": False,
}

# Shared settings for the parts. The first layer is 0.3 mm, the same as
# the other layers. A smaller first layer line stops elephant foot.
FLAT = {
    "layer_height_0": 0.3,
    "infill_sparse_density": 100,
    "speed_wall_0": 40,
    "speed_topbottom": 45,
    "cool_min_layer_time": 10,
    "adhesion_type": "skirt",
    "skirt_line_count": 3,
    "xy_offset_layer_0": -0.15,
}



def profile(part, name, stl, values):
    layer = values.get("layer_height", LAYER["layer_height"])
    return {"id": f"PenPlotter_{part}", "name": f"Pen plotter - {name} PLA {layer}", "stl": stl,
            "quality_type": "verydraft", "values": {**LAYER, **values}}



def setting_scopes(name):
    """Map each setting to True if it is for the extruder, False if it is global."""
    scopes = {}

    def walk(node, inherited):
        for key, value in node.items():
            if not isinstance(value, dict):
                continue
            current = value.get("settable_per_extruder", inherited)
            if "label" in value or "default_value" in value or "value" in value:
                scopes[key] = current
            if "children" in value:
                walk(value["children"], current)

    walk(json.loads((DEFINITIONS / name).read_text())["settings"], True)
    return scopes


def fmt(value):
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def write(path, name, quality_type, values, position=None):
    lines = ["[general]", "version = 4", f"name = {name}", "definition = fdmprinter", "",
             "[metadata]", f"setting_version = {SETTING_VERSION}", "type = quality_changes",
             f"quality_type = {quality_type}"]
    if position is not None:
        lines.append(f"position = {position}")
    lines += ["", "[values]"] + [f"{key} = {fmt(values[key])}" for key in sorted(values)]
    path.write_text("\n".join(lines) + "\n")



# Lean settings, tested with slices (see the print time review in the build guide): 15 % gyroid
# infill, 0.9 mm top and bottom (3 layers), 40 mm/s outer walls. Parts with heat-set inserts keep
# 4 walls (2 mm), so each insert has solid plastic around it. The other parts have 3 walls
# (1.5 mm).
LEAN = {**FLAT, "infill_sparse_density": 15, "infill_pattern": "gyroid", "cool_min_layer_time": 6}
INSERTS = {**LEAN, "wall_thickness": 2.0}     # 4 walls: the rail fit test
BASE = {**LEAN, "wall_thickness": 1.5}
SLIDER = {**LEAN, "wall_thickness": 1.5}
STRONG = {**LEAN, "wall_thickness": 2.5, "infill_sparse_density": 40}   # 5 walls, 40 %: the loaded parts (joint audit)

PROFILES = [
    profile("PenCarriage", "Pen carriage", "pen_carriage.stl", STRONG),
    profile("XCarriagePlate", "X plate", "x_carriage_plate.stl", STRONG),
    profile("PenSlider", "Pen slider", "pen_slider.stl", SLIDER),
    profile("MastFoot", "Camera pole foot", "mast_foot.stl", BASE),
    profile("YCarriageL", "Y carriage left", "y_carriage_left.stl", STRONG),
    profile("YCarriageR", "Y carriage right", "y_carriage_right.stl", STRONG),
    profile("YFrontL", "Y front base left", "y_front_left.stl", STRONG),
    profile("YFrontR", "Y front base right", "y_front_right.stl", STRONG),
    profile("YMotorMountL", "Y motor bracket left", "y_motor_mount_left.stl", STRONG),
    profile("YMotorMountR", "Y motor bracket right", "y_motor_mount_right.stl", STRONG),
    profile("YIdlerFork", "Y idler fork (print 2)", "y_idler_fork.stl", STRONG),
    profile("YIdlerBracketL", "Y idler bracket left", "y_idler_bracket_left.stl", STRONG),
    profile("YIdlerBracketR", "Y idler bracket right", "y_idler_bracket_right.stl", STRONG),
    profile("YChainAnchor", "Y chain anchor", "y_chain_anchor.stl", BASE),
    profile("XIdlerFork", "X idler fork", "x_idler_fork.stl", STRONG),
    profile("FitRail", "Fit test rail", "fit_rail.stl", INSERTS),
    profile("FitSlider", "Fit test slider", "fit_slider.stl", SLIDER),
    profile("FitWheel", "Fit test wheel", "fit_wheel.stl", BASE),
]

SUPPORT_CHECK = {"support_enable": True, "support_angle": 60, "support_type": "everywhere",
                 # No infill and 2 walls in the support check: it only counts support, and it runs faster.
                 "infill_sparse_density": 5, "wall_thickness": 1.0,
                 # CuraEngine 5.14 wants the support extruders set when support is on.
                 "support_extruder_nr": 0, "support_infill_extruder_nr": 0, "support_extruder_nr_layer_0": 0,
                 "support_interface_extruder_nr": 0, "support_roof_extruder_nr": 0, "support_bottom_extruder_nr": 0}

ENGINE = Path("/opt/ultimaker-cura/CuraEngine")


def _engine_defaults():
    """The default_value of each setting in the engine's own fdmprinter.def.json."""
    out = {}
    path = Path("/opt/ultimaker-cura/share/cura/resources/definitions/fdmprinter.def.json")
    if not path.exists():
        return out

    def walk(d):
        for k, v in d.items():
            if isinstance(v, dict):
                if "default_value" in v:
                    out[k] = v["default_value"]
                walk(v.get("children", {}))
    walk(json.loads(path.read_text())["settings"])
    return out


ENGINE_DEFAULTS = _engine_defaults()
DEFS = DEFINITIONS
LINE = 0.5
FACTOR = {"grid": 2, "lightning": 1, "gyroid": 1}
GRAMS_PER_MM = math.pi * 1.425 ** 2 * 1.24e-3   # PLA, 1.24 g/cm3


def engine_settings(values):
    """CuraEngine does not compute the settings that Cura derives from others; set them here."""
    v = dict(values)
    walls = round(v.get("wall_thickness", 1.5) / LINE)
    layers = math.ceil(v["top_bottom_thickness"] / v["layer_height"] - 1e-6)
    d = v.get("infill_sparse_density", 20)
    pattern = v.get("infill_pattern", "grid")
    v.update({"wall_line_count": walls, "top_layers": layers, "bottom_layers": layers,
              "infill_line_distance": LINE * 100 / d * FACTOR.get(pattern, 1) if d < 100 else LINE,
              "infill_pattern": pattern, "material_diameter": 2.85, "roofing_layer_count": 0,
              "flooring_layer_count": 0})
    if v.get("adhesion_type") == "brim":
        v.setdefault("brim_line_count", 12)
    return v


def slice_part(profile, extra=None, tag=""):
    """Slice one part. Return the grams of filament for each line type, or None."""
    values = engine_settings({**COMMON, **profile["values"], **(extra or {})})
    args = []
    for key, value in values.items():
        args += ["-s", f"{key}={fmt(value).lower() if isinstance(value, bool) else value}"]
    gcode = BUILD / "slice" / (Path(profile["stl"]).stem + tag + ".gcode")
    gcode.parent.mkdir(parents=True, exist_ok=True)
    gcode.unlink(missing_ok=True)
    env = dict(os.environ, LD_LIBRARY_PATH=str(ENGINE.parent),
               # The /opt definitions first: CuraEngine 5.14 gives an empty slice when the project
               # folder comes first in the search path.
               CURA_ENGINE_SEARCH_PATH=":".join(["/opt/ultimaker-cura/share/cura/resources/definitions",
                                                 "/opt/ultimaker-cura/share/cura/resources/extruders", str(DEFS)]))
    # One thread (-m1): CuraEngine 5.14 can deadlock in its threaded G-code writer (0 % CPU, an empty
    # file). That was the stalled support check of y_carriage_left; with one thread it does not happen.
    cmd = ["/lib64/ld-linux-x86-64.so.2", str(ENGINE), "slice", "-m1", "-j", str(DEFS / "lulzbot_taz_workhorse_se.def.json")]
    cmd += args + ["-e0"] + args + ["-l", str(PROJECT / "stl" / profile["stl"]), "-o", str(gcode)]
    # CuraEngine can stall in its G-code writer. Stop it after 4 minutes and try again.
    # CuraEngine 5.14 stops when a setting has no value (for example the new support settings):
    # take the default of the engine's fdmprinter.def.json for it, and slice again.
    tries = 0
    while tries < 40:
        tries += 1
        try:
            r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=int(os.environ.get("SLICE_TIMEOUT", 240)))
        except subprocess.TimeoutExpired:
            gcode.unlink(missing_ok=True)
            if tries >= 3:
                break
            continue
        m = re.search(r"no value given: (\w+)", r.stdout.decode(errors="ignore"))
        if r.returncode != 0 and m and m.group(1) in ENGINE_DEFAULTS:
            key = m.group(1)
            val = ENGINE_DEFAULTS[key]
            val = str(val).lower() if isinstance(val, bool) else val
            cmd = cmd[:-4] + ["-s", f"{key}={val}"] + cmd[-4:]
            gcode.unlink(missing_ok=True)
            continue
        break
    if not gcode.exists() or gcode.stat().st_size == 0:
        raise SystemExit(f"EMPTY SLICE: {profile['stl']} gave no G-code")
    grams = collections.Counter()
    # Count only E above the highest E so far. An un-retract moves E back up to that mark and
    # uses no new filament. A G92 sets a new zero, so the mark moves with it.
    kind, high = "none", 0.0
    for line in gcode.open():
        if line.startswith(";TYPE:"):
            kind = line[6:].strip()
            continue
        s = line.split(";")[0].strip()
        if s.startswith("G92"):
            m = re.search(r"E([-\d.]+)", s)
            high = float(m.group(1)) if m else high
        elif s.startswith(("G0", "G1")):
            m = re.search(r"E([-\d.]+)", s)
            if m:
                e = float(m.group(1))
                if e > high:
                    grams[kind] += (e - high) * GRAMS_PER_MM
                    high = e
    if sum(grams.values()) <= 0:
        raise SystemExit(f"EMPTY SLICE: {profile['stl']} uses 0 g of filament")
    times = [l for l in gcode.read_text(errors="ignore").splitlines()[-400:] if l.startswith(";TIME_ELAPSED:")]
    if not times or float(times[-1].split(":")[1]) <= 0:
        raise SystemExit(f"EMPTY SLICE: {profile['stl']} has no print time")
    return grams


def run(profile):
    normal = slice_part(profile)
    # CuraEngine 5.14 can stall on the support check of a big part. Then the mesh overhang check of
    # make.sh (no flat ceiling, no face under 40 degrees) stands for it.
    try:
        support = slice_part(profile, SUPPORT_CHECK, "_support_check")
    except SystemExit as e:
        print(f"  {profile['stl']}: support check skipped ({e}); the mesh overhang check covers it")
        support = collections.Counter()
    return profile, normal, support


def main():
    scopes = setting_scopes("fdmprinter.def.json")
    scopes.update(setting_scopes("fdmextruder.def.json"))
    OUT.mkdir(exist_ok=True)
    for path in OUT.glob("*.inst.cfg"):
        path.unlink()
    for profile in PROFILES:
        values = {**COMMON, **profile["values"]}
        pid = profile["id"]
        g = {k: v for k, v in values.items() if k in scopes and not scopes[k]}
        x = {k: v for k, v in values.items() if k in scopes and scopes[k]}
        write(OUT / f"{pid}.inst.cfg", profile["name"], profile["quality_type"], g)
        write(OUT / f"{pid}_e0.inst.cfg", profile["name"], profile["quality_type"], x, 0)
    if "--no-slice" not in sys.argv:
        filament, supports = {}, {}
        # One slice at a time: parallel CuraEngine runs stalled.
        for profile, normal, support in map(run, PROFILES):
            stem = Path(profile["stl"]).stem
            if normal is None or support is None:
                print(f"{profile['name']:30s} slice failed")
                continue
            total = sum(normal.values())
            sup = support.get("SUPPORT", 0.0) + support.get("SUPPORT-INTERFACE", 0.0)
            filament[stem] = {"grams": round(total), "metres": round(total / GRAMS_PER_MM / 1000, 1)}
            supports[stem] = round(sup, 2)
            print(f"{profile['name']:30s} {profile['stl']:14s} {total:5.0f} g   support check: {sup:.2f} g")
        (BUILD / "filament.json").write_text(json.dumps(filament, indent=1))
        (BUILD / "supports.json").write_text(json.dumps(supports, indent=1))
    if "--install" in sys.argv:
        install()


def install():
    if subprocess.run(["pgrep", "-x", "UltiMaker-Cura"], capture_output=True).returncode == 0:
        sys.exit("Cura is running. Close Cura, then install again.")
    for path in CURA.glob("PenPlotter_*.inst.cfg"):
        path.unlink()
    for path in sorted(OUT.glob("*.inst.cfg")):
        shutil.copy(path, CURA / path.name)
    print(f"Installed {len(list(OUT.glob('*.inst.cfg')))} files in {CURA}")


if __name__ == "__main__":
    main()
