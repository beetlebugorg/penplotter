"""Write audit/report.md from audit/out/results.json. run.py calls it after each run."""

import json
import os
import re
import sys

import rules as R

# The risk order of the check groups: loads and axles first, then the holes, the threads, the FEA,
# the seats, the layers, the tool access and the fits.
RISK = {"5": 0, "7": 1, "8": 2, "1": 3, "2": 4, "6/7": 5, "3": 6, "6": 7, "4": 8, "9": 9, "0": 10}

MEASURE = [
    "The GT2 belt tension (ESTIMATE 40 N per run). Measure it with a belt tension app or a spring scale.",
    "The holding torque of the Y and X motors (ESTIMATE 0.4 N m). Read it from the motor label or data sheet.",
    "The slot depth of the 2020 rails and bars (ESTIMATE 6.3 mm) and the lip (ESTIMATE 1.8 mm).",
    "The T-nut thread length (ESTIMATE 4 mm).",
    "The heat-set insert length and OD (shape.INSERT_M5). The rule for the boss: 1.5 x OD minimum, 2 x OD preferred.",
    "The inner race OD of the idler bearings (ESTIMATE 7.5 mm). A washer wider than the inner race rubs on the shield.",
    "The tightening torque that you use on screws into PLA (ESTIMATE: M3 0.5 N m, M5 1.5 N m).",
    "The PLA strength of your filament (ESTIMATE 50 MPa in XY, 25 MPa in Z). Print a test bar in each direction.",
]


def strip_side(s):
    return re.sub(r"\b(left|right) ", "", s).replace("_left", "").replace("_right", "")


def group_key(r):
    return (strip_side(r["part"]), re.sub(r"\(.*?\)", "", strip_side(r["feature"])).strip(), r["check"].split(" (")[0])


def esc(s):
    return str(s).replace("|", "/")


def write(results, path):
    d = json.load(open(results))
    rows = d["rows"]
    cnt = d["counts"]
    fails = [r for r in rows if r["status"] == "FAIL"]
    warns = [r for r in rows if r["status"] == "WARN"]

    def merged(rs):
        g = {}
        for r in rs:
            k = group_key(r)
            if k not in g:
                g[k] = {**r, "n": 0, "parts": set(), "names": []}
            g[k]["n"] += 1
            g[k]["parts"].add(r["part"])
            g[k]["names"].append(r["feature"])
        out = list(g.values())
        out.sort(key=lambda r: (RISK.get(r["check"].split(" ")[0], 9), r["part"]))
        return out

    L = []
    L.append("# Printed hardware fitness audit\n")
    L.append("This file is written by `audit/run.py`. Do not edit it by hand: run the audit again.\n")
    L.append(f"- Result: **{cnt['FAIL']} FAIL, {cnt['WARN']} WARN, {cnt['PASS']} PASS**, run time {d['seconds']} s.")
    L.append(f"- Assembly position for the geometry checks: gantry y {d['position'][0]:.0f}, X plate x {d['position'][1]:.0f}. "
             "The tool access check also tries the two ends of the travel.")
    L.append("- The audit reads `fasteners.py` (the Fastener and Joint lists) and the part solids of `parts.py`. "
             "It casts rays round each screw axis in each printed part. It does not use hand-entered hole data.\n")
    L.append("## How to read the checks\n")
    L.append("The number at the start of each check is its group:\n")
    L.append("1. Hole meat: the least material round the hole, radially, over the hole length (1 mm skipped at each end "
             "for the edge chamfers). Limit 1 x d. Open sectors are slots or holes that break out of a face.")
    L.append("2. Thread engagement: self-tapping >= 2 d, insert >= 1.5 d, nut >= 1 pitch past (2 for a nyloc), "
             "T-nut full thread, no tip that bottoms out. Each joint is also checked with `fasteners.check_joint`.")
    L.append("3. Head seating: the flat seat, the counterbore gap, the screw clear of the part, the preload on the PLA, "
             "a washer under a nut on PLA.")
    L.append("4. Tool access: a straight line along the axis for the key length, with the whole assembly in place.")
    L.append("5. Axles: one or two supports, the boss length for one support.")
    L.append("6. Layers: the load direction against the print Z axis (read from the STL). Z strength = 0.5 x XY (ESTIMATE).")
    L.append("7. Loads and strength: hand calculations at SF 3 on the PLA strength. SF 1.5 to 3 is WARN, below 1.5 is FAIL.")
    L.append("8. FEA: linear elastic, 10-node tetrahedra, solid PLA.")
    L.append("9. Fits: hole sizes and the clearances of `shape.py` against FDM values for a 0.5 mm nozzle.\n")

    L.append("## What to fix, ranked by risk\n")
    mf = merged(fails)
    if not mf:
        L.append("No FAIL.\n")
    for i, r in enumerate(mf, 1):
        n = f" ({r['n']} places)" if r["n"] > 1 else ""
        parts = ", ".join(sorted(r["parts"]))
        L.append(f"{i}. **{parts}: {esc(strip_side(r['feature']))}**{n}. {esc(r['check'])}: {esc(r['value'])} "
                 f"(limit {esc(r['limit'])}). Fix: {esc(r['fix']) or 'see the check'}.")
    L.append("")
    L.append("### Warnings\n")
    for r in merged(warns):
        n = f" ({r['n']} places)" if r["n"] > 1 else ""
        L.append(f"- {esc(', '.join(sorted(r['parts'])))}: {esc(strip_side(r['feature']))}{n}. {esc(r['check'])}: "
                 f"{esc(r['value'])} (limit {esc(r['limit'])}).{(' Fix: ' + esc(r['fix']) + '.') if r['fix'] else ''}")
    L.append("")

    L.append("## The X idler mount\n")
    xi = [r for r in rows if "fork" in r["part"] or "X idler" in r["feature"] or "X tension" in r["feature"]]
    if xi:
        L.append("| part | feature | check | value | limit | result |")
        L.append("|---|---|---|---|---|---|")
        for r in xi:
            L.append(f"| {esc(r['part'])} | {esc(r['feature'])} | {esc(r['check'])} | {esc(r['value'])} | {esc(r['limit'])} | "
                     f"{r['status']} |")
    L.append("")

    L.append("## Load cases\n")
    L.append("| case | value | unit | source |")
    L.append("|---|---|---|---|")
    for k, (v, u, src) in d["loads"].items():
        L.append(f"| {k} | {float(v):.3g} | {u} | {esc(src)} |")
    L.append("")
    L.append(f"Materials (ESTIMATE): PLA E {R.PLA_E:.0f} MPa, tensile {R.PLA_XY:.0f} MPa in XY and {R.PLA_Z:.0f} MPa in Z, "
             f"compressive {R.PLA_COMP:.0f} MPa, thread shear {R.PLA_SHEAR:.0f} MPa. Steel class 8.8 yield {R.STEEL_YIELD:.0f} MPa.\n")

    L.append("## FEA\n")
    fea = d.get("fea") or {}
    if not fea:
        L.append("The FEA did not run (`--no-fea`).\n")
    for p, res in fea.items():
        L.append(f"### {p}\n")
        if "error" in res:
            L.append(f"The FEA failed: {esc(res['error'])}\n")
            continue
        L.append(f"- Mesh: {res['tets']} tetrahedra, {res['dofs']} unknowns, {res['seconds']} s.")
        L.append(f"- Max von Mises away from the fixtures: **{res['vm_max_away']:.1f} MPa** "
                 f"(SF {res['sf_vm']:.1f} on {R.PLA_XY:.0f} MPa); at the fixture edges {res['vm_max']:.1f} MPa (a model peak).")
        L.append(f"- Worst principal stress against the layer strength: {res['s1_crit']:.1f} MPa, |n.z| "
                 f"{res['s1_crit_zfrac']:.2f}, strength {res['s1_crit_strength']:.0f} MPa, SF {res['sf_layers']:.1f}.")
        L.append(f"- Max displacement: {res['disp_max'] * 1000:.0f} um.")
        for pr in res["probes"]:
            L.append(f"- Deflection at {pr['name']}: {pr['max_disp'] * 1000:.2f} um under the operating loads (inertia at the "
                     f"firmware acceleration, pen drag; limit {pr['limit'] * 1000:.0f} um); "
                     f"{pr.get('worst_disp', float('nan')) * 1000:.0f} um under the worst case.")
        L.append("- Loads: " + "; ".join(f"{ld['name']} ({ld.get('facets', 0)} faces)" for ld in res["loads"]) + ".")
        L.append("- Fixtures: " + "; ".join(f"{fx['name']} ({fx['facets']} faces)" for fx in res["fixtures"]) + ".")
        L.append(f"\n![{p}](out/{res['png']})\n")

    L.append("## Values to measure or confirm\n")
    for m in MEASURE:
        L.append(f"- {m}")
    L.append("")

    L.append("## All results\n")
    L.append("<details><summary>The full table (one row per check)</summary>\n")
    L.append("| part | feature | check | value | limit | result | fix |")
    L.append("|---|---|---|---|---|---|---|")
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    for r in sorted(rows, key=lambda r: (order[r["status"]], r["part"], r["feature"])):
        L.append(f"| {esc(r['part'])} | {esc(r['feature'])} | {esc(r['check'])} | {esc(r['value'])} | {esc(r['limit'])} | "
                 f"{r['status']} | {esc(r['fix'])} |")
    L.append("\n</details>\n")
    with open(path, "w") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    write(sys.argv[1], sys.argv[2])
