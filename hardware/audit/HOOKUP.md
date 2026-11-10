# Hook the audit into make.sh

The audit lives in `hardware/audit/`. It reads `shape.py`, `parts.py`, `fasteners.py`,
`model.py`, `cura/make_profiles.py`, `stl/*.stl` and `build/parts.json`. It does not write to
these files. It writes only to `audit/out/` and `audit/report.md`.

## The line for make.sh

Add this line after the `model.py` step and the mesh check. The audit needs the STL files of
the current design, because it reads the print orientation from them.

```bash
uv run --no-project --python 3.12 --with build123d --with trimesh --with rtree --with scipy --with embreex python audit/run.py --gate | tee build/audit.log
```

Notes:

- `make.sh` has `set -euo pipefail`. A non-zero exit of `run.py` stops the build.
- Python 3.12 is necessary for `embreex` (the fast ray engine). Without it, the audit uses the
  slow ray engine of trimesh and takes about 5 minutes more.
- The FEA runs in a second uv environment (`gmsh`, `scikit-fem`, `pyamg`, `matplotlib`).
  `run.py` starts it. Add `--no-fea` for a fast run (about 1 minute).

## The failures that stop the build

With `--gate`, these FAIL rows stop the build:

| group | check | why it stops the build |
|---|---|---|
| 1 | hole meat below 1 x d round a thread, insert or axle hole; a thread hole that breaks out; the insert boss below 1.5 x OD | the thread or the axle tears out |
| 2 | thread engagement (self-tapping < 0.75 x 2 d, insert < 0.7 x 1.5 d, nut, T-nut), a tip that bottoms out | the joint strips or does not clamp |
| 3 | the screw solid cuts into the part (`3 screw clear of the part`) | the screw does not fit |
| 5 | a cantilever axle with a boss shorter than 2 x d | the axle tilts and the belt or wheel runs out of line |
| 6, 7 | a hand calculation with SF below 1.5 (bearing, tear-out, bending, clamped face, thread pull-out below SF 1) | the part breaks under the load cases |
| 8 | an FEA result with SF below 1.5, or a deflection above 2 x the limit at a probe | the part breaks or the pen moves |

These FAIL rows are printed and written to the report, but they do not stop the build:

- 4: tool access (the assembly order is an estimate; a screw can often go in earlier).
- 9: fits and hole sizes (a fit test print decides these).
- 3 preload (the builder sets the torque) and 6 slicer walls (the profile can change without a CAD change).

Without `--gate`, every FAIL stops the build. With `--strict`, every WARN stops it too.
