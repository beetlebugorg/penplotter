#!/usr/bin/env python3
"""Print the print time, the filament, and the cost of each printed part, and the totals.
Reads build/filament.json and the CuraEngine slices in build/slice/. Run after make.sh.
Usage: python3 stats.py [--json]"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
PRICE_PER_KG = 19.99            # USD, PLA
COUNTS = {"y_idler_fork": 2}   # parts printed more than once: one part fits each place


def print_time(name):
    path = BUILD / "slice" / f"{name}.gcode"
    if not path.exists():
        return 0.0
    with path.open("rb") as fh:
        fh.seek(0, 2)
        fh.seek(max(0, fh.tell() - 20000))
        tail = fh.read().decode(errors="ignore")
    found = [l for l in tail.splitlines() if l.startswith(";TIME_ELAPSED:")]
    return float(found[-1].split(":")[1]) if found else 0.0


def stats():
    fil = json.loads((BUILD / "filament.json").read_text())
    rows = []
    for name, v in fil.items():
        k = COUNTS.get(name, 1)
        rows.append({"part": name, "count": k, "min": round(print_time(name) * k / 60),
                     "g": v["grams"] * k, "usd": round(v["grams"] * k / 1000 * PRICE_PER_KG, 2)})
    fit = [r for r in rows if r["part"].startswith("fit_")]
    real = [r for r in rows if not r["part"].startswith("fit_")]

    def tot(rs):
        return {"parts": sum(r["count"] for r in rs), "jobs": len(rs), "min": sum(r["min"] for r in rs),
                "g": sum(r["g"] for r in rs), "usd": round(sum(r["usd"] for r in rs), 2)}
    # The totals of the main build, and of the fit tests.
    total = {**tot(real), "fit_min": sum(r["min"] for r in fit), "fit_g": sum(r["g"] for r in fit)}
    return rows, total


if __name__ == "__main__":
    rows, total = stats()
    if "--json" in sys.argv:
        print(json.dumps({"rows": rows, "total": total}, indent=1))
    else:
        for r in rows:
            print(f"{r['part']:24s} x{r['count']}  {r['min'] // 60:2d} h {r['min'] % 60:02d}  {r['g']:5.0f} g  ${r['usd']:.2f}")
        t = total
        print(f"TOTAL, main build (no fit tests): {t['parts']} parts in {t['jobs']} jobs, {t['min'] // 60} h {t['min'] % 60:02d} min, "
              f"{t['g']} g, ${t['usd']:.2f}; fit tests {t['fit_min']} min, {t['fit_g']} g")
