# Printed hardware fitness audit

This file is written by `audit/run.py`. Do not edit it by hand: run the audit again.

- Result: **6 FAIL, 67 WARN, 472 PASS**, run time 134 s.
- Assembly position for the geometry checks: gantry y 271, X plate x 193. The tool access check also tries the two ends of the travel.
- The audit reads `fasteners.py` (the Fastener and Joint lists) and the part solids of `parts.py`. It casts rays round each screw axis in each printed part. It does not use hand-entered hole data.

## How to read the checks

The number at the start of each check is its group:

1. Hole meat: the least material round the hole, radially, over the hole length (1 mm skipped at each end for the edge chamfers). Limit 1 x d. Open sectors are slots or holes that break out of a face.
2. Thread engagement: self-tapping >= 2 d, insert >= 1.5 d, nut >= 1 pitch past (2 for a nyloc), T-nut full thread, no tip that bottoms out. Each joint is also checked with `fasteners.check_joint`.
3. Head seating: the flat seat, the counterbore gap, the screw clear of the part, the preload on the PLA, a washer under a nut on PLA.
4. Tool access: a straight line along the axis for the key length, with the whole assembly in place.
5. Axles: one or two supports, the boss length for one support.
6. Layers: the load direction against the print Z axis (read from the STL). Z strength = 0.5 x XY (ESTIMATE).
7. Loads and strength: hand calculations at SF 3 on the PLA strength. SF 1.5 to 3 is WARN, below 1.5 is FAIL.
8. FEA: linear elastic, 10-node tetrahedra, solid PLA.
9. Fits: hole sizes and the clearances of `shape.py` against FDM values for a 0.5 mm nozzle.

## What to fix, ranked by risk

1. **y_motor_mount_right: Y motor screw -16 -16 (M3 x 10 socket head)**. 3 preload on the PLA under the socket head at 0.40 N m: 93 MPa, SF 0.5 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.11 N m at most, or put a washer under the head (M3 washer).
2. **y_motor_mount_right: Y motor screw -16 +16 (M3 x 10 socket head)**. 3 preload on the PLA under the socket head at 0.40 N m: 93 MPa, SF 0.5 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.11 N m at most, or put a washer under the head (M3 washer).
3. **y_motor_mount_right: Y motor screw +16 -16 (M3 x 10 socket head)**. 3 preload on the PLA under the socket head at 0.40 N m: 93 MPa, SF 0.5 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.11 N m at most, or put a washer under the head (M3 washer).
4. **y_motor_mount_right: Y motor screw +16 +16 (M3 x 10 socket head)**. 3 preload on the PLA under the socket head at 0.40 N m: 93 MPa, SF 0.5 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.11 N m at most, or put a washer under the head (M3 washer).
5. **y_motor_mount_left, y_motor_mount_right: Y motor screw -16 -16 (M3 x 10 socket head)** (2 places). 4 straight socket head key line from the head: 13 mm (stop: left Y motor bracket screw x 46, at gantry y 271, X x 193) (limit >= 60 mm). Fix: open a key hole through the left Y motor bracket screw x 46 on the screw axis, or fit this screw before the left Y motor bracket screw x 46.

### Warnings

- y_carriage_left, y_carriage_right: Y wheel bolt 3 (M5 x 30 socket head) (2 places). 7 PLA face under the clamped stack (10.0 mm, preload 1200 N): 26.7 MPa (21.9 preload + 4.8 moment), SF 1.9 (limit SF >= 3 on 50 MPa). Fix: put a 15 mm washer on the face, or lower the torque.
- y_carriage_left, y_carriage_right: Y wheel bolt 11 (M5 x 35 socket head) (2 places). 7 PLA face under the clamped stack (10.0 mm, preload 1200 N): 26.6 MPa (21.9 preload + 4.7 moment), SF 1.9 (limit SF >= 3 on 50 MPa). Fix: put a 15 mm washer on the face, or lower the torque.
- mast_foot: pole foot screw -25 (M5 x 12 socket head). 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm): 3.2 mm at s 1.5 (limit >= 5.0 mm). Fix: add material: make the boss 15 mm OD round the hole, or move the hole 1.8 mm away from the edge.
- mast_foot: pole foot screw +25 (M5 x 12 socket head). 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm): 3.2 mm at s 4.0 (limit >= 5.0 mm). Fix: add material: make the boss 15 mm OD round the hole, or move the hole 1.8 mm away from the edge.
- x_carriage_plate: head screw T1 (M3 x 12 socket head). 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm): 1.8 mm at s 1.5 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 1.2 mm away from the edge.
- x_carriage_plate: head screw T2 (M3 x 12 socket head). 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm): 1.8 mm at s 1.5 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 1.2 mm away from the edge.
- x_carriage_plate: X wheel axle bottom (M5 x 25 button head (ISO 7380)). 1 hole wall closed (insert): slot or pocket, 15 deg open (limit 0 deg open).
- x_carriage_plate: X wheel axle bottom (M5 x 25 button head (ISO 7380)). 1 insert boss diameter (material OD round the insert): 12.8 mm (wall 3.2) (limit >= 10.5 (1.5 x OD 7.0); 14 preferred). Fix: make the boss 14 mm OD.
- x_idler_fork: X tension screw (M3 x 20 socket head). 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm): 2.1 mm at s 12.0 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 0.9 mm away from the edge.
- y_carriage_left, y_carriage_right: Y wheel bolt 3 (M5 x 30 socket head) (2 places). 1 insert boss diameter (material OD round the insert): 14.0 mm (wall 3.8) (limit >= 10.5 (1.5 x OD 7.0); 14 preferred). Fix: make the boss 14 mm OD.
- y_carriage_left: X motor screw -16 -16 (M3 x 10 socket head). 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm): 2.9 mm at s 1.0 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 0.1 mm away from the edge.
- y_carriage_left: X motor screw +16 -16 (M3 x 10 socket head). 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm): 2.8 mm at s 1.0 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 0.2 mm away from the edge.
- y_carriage_right: X tension screw (M3 x 20 socket head). 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm): 2.8 mm at s 1.5 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 0.2 mm away from the edge.
- y_chain_anchor: Y chain anchor screw y 492 (M5 x 12 socket head). 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm): 4.9 mm at s 1.0 (limit >= 5.0 mm). Fix: add material: make the boss 15 mm OD round the hole, or move the hole 0.1 mm away from the edge.
- y_front_left, y_front_right: Y bracket screw 0 (M3 x 12 socket head) (2 places). 1 meat round the clearance hole (s 0.5..4.5, 4.0 mm): 2.8 mm at s 1.5 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 0.2 mm away from the edge.
- y_front_left, y_front_right: Y switch screw 0 (M3 x 8 socket head) (2 places). 1 insert boss diameter (material OD round the insert): 7.5 mm (wall 1.8) (limit >= 6.9 (1.5 x OD 4.6); 9 preferred). Fix: make the boss 9 mm OD.
- y_front_left, y_front_right: Y switch screw 1 (M3 x 8 socket head) (2 places). 1 insert boss diameter (material OD round the insert): 7.1 mm (wall 1.6) (limit >= 6.9 (1.5 x OD 4.6); 9 preferred). Fix: make the boss 9 mm OD.
- y_idler_fork_left, y_idler_fork_right: Y tension screw (M3 x 20 socket head) (2 places). 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm): 2.1 mm at s 12.0 (limit >= 3.0 mm). Fix: add material: make the boss 9 mm OD round the hole, or move the hole 0.9 mm away from the edge.
- y_motor_mount_left, y_motor_mount_right: Y motor bracket screw x 46 (M5 x 12 socket head) (2 places). 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm): 3.3 mm at s 1.5 (limit >= 5.0 mm). Fix: add material: make the boss 15 mm OD round the hole, or move the hole 1.7 mm away from the edge.
- y_motor_mount_left, y_motor_mount_right: Y motor bracket screw x 59 (M5 x 12 socket head) (2 places). 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm): 3.2 mm at s 5.0 (limit >= 5.0 mm). Fix: add material: make the boss 15 mm OD round the hole, or move the hole 1.8 mm away from the edge.
- pen_slider: pen clamp screw (M3 x 20 socket head). 2 joint data: no Joint in fasteners.py (limit a Joint). Fix: add a Joint for this screw.
- x_carriage_plate: X wheel axle bottom (M5 x 25 button head (ISO 7380)). 2 thread in the insert: 7.4 mm (insert 9.5 mm long) (limit >= 7.5 mm (1.5 d)). Fix: use a long insert (M5 x 9 mm or more) and a screw that passes through it.
- x_carriage_plate: X wheel axle top (M5 x 30 button head (ISO 7380)). 2 screw past the M5 nyloc nut: 1.0 mm (limit >= 1.6 mm). Fix: use a screw 31 mm long or more.
- x_idler_fork: X idler axle (M5 x 30 socket head). 2 screw past the M5 nyloc nut: 1.4 mm (limit >= 1.6 mm). Fix: use a screw 31 mm long or more.
- y_idler_fork_left, y_idler_fork_right: Y idler axle (M5 x 30 socket head) (2 places). 2 screw past the M5 nyloc nut: 1.5 mm (limit >= 1.6 mm). Fix: use a screw 31 mm long or more.
- pen_carriage: head screw T1 (M3 x 12 socket head). 6/7 thread pull-out (across the layers) at 0.30 N m: capacity 459 N vs preload 333 N, SF 1.4 (limit SF >= 2 (preload)). Fix: tighten to 0.21 N m at most, or use a heat-set insert.
- pen_carriage: head screw T2 (M3 x 12 socket head). 6/7 thread pull-out (across the layers) at 0.30 N m: capacity 459 N vs preload 333 N, SF 1.4 (limit SF >= 2 (preload)). Fix: tighten to 0.21 N m at most, or use a heat-set insert.
- pen_carriage: head screw H2 (M3 x 12 socket head). 6/7 thread pull-out (across the layers) at 0.30 N m: capacity 459 N vs preload 333 N, SF 1.4 (limit SF >= 2 (preload)). Fix: tighten to 0.21 N m at most, or use a heat-set insert.
- pen_carriage: head screw H1 (M3 x 12 socket head). 6/7 thread pull-out (across the layers) at 0.30 N m: capacity 459 N vs preload 333 N, SF 1.4 (limit SF >= 2 (preload)). Fix: tighten to 0.21 N m at most, or use a heat-set insert.
- mast_foot: pole collar screw (M3 x 16 socket head). 3 preload on the PLA under the socket head at 0.40 N m: 45 MPa, SF 1.1 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.22 N m at most, or put a washer under the head (M3 washer).
- x_carriage_plate: X wheel axle top left: M5 nyloc nut. 3 washer under the nut on PLA: no washer (limit a washer). Fix: put an M5 washer under the nut.
- x_carriage_plate: X wheel axle top right: M5 nyloc nut. 3 washer under the nut on PLA: no washer (limit a washer). Fix: put an M5 washer under the nut.
- x_idler_fork: X idler axle (M5 x 30 socket head). 3 preload on the PLA under the socket head at 1.20 N m: 35 MPa, SF 1.4 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.85 N m at most, or put a washer under the head (M5 washer).
- y_carriage_left: X motor screw -16 -16 (M3 x 10 socket head). 3 preload on the PLA under the socket head at 0.40 N m: 45 MPa, SF 1.1 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.22 N m at most, or put a washer under the head (M3 washer).
- y_carriage_left: X motor screw -16 +16 (M3 x 10 socket head). 3 preload on the PLA under the socket head at 0.40 N m: 45 MPa, SF 1.1 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.22 N m at most, or put a washer under the head (M3 washer).
- y_carriage_left: X motor screw +16 -16 (M3 x 10 socket head). 3 preload on the PLA under the socket head at 0.40 N m: 45 MPa, SF 1.1 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.22 N m at most, or put a washer under the head (M3 washer).
- y_carriage_left, y_carriage_right: Y wheel bolt 7: M5 nyloc nut (2 places). 3 washer under the nut on PLA: no washer (limit a washer). Fix: put an M5 washer under the nut.
- y_chain_anchor: Y chain anchor screw y 492 (M5 x 12 socket head). 3 preload on the PLA under the socket head at 1.20 N m: 35 MPa, SF 1.4 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.85 N m at most, or put a washer under the head (M5 washer).
- y_idler_bracket_left, y_idler_bracket_right: Y tension screw (M3 x 20 socket head) (2 places). 3 preload on the PLA under the socket head at 0.40 N m: 45 MPa, SF 1.1 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.22 N m at most, or put a washer under the head (M3 washer).
- y_idler_fork_left: Y idler axle (M5 x 30 socket head). 3 preload on the PLA under the socket head at 1.20 N m: 35 MPa, SF 1.4 (limit SF >= 2 (50 MPa ESTIMATE)). Fix: tighten to 0.85 N m at most, or put a washer under the head (M5 washer).
- y_idler_fork_left, y_idler_fork_right: Y idler axle: M5 nyloc nut (2 places). 3 washer under the nut on PLA: no washer (limit a washer). Fix: put an M5 washer under the nut.
- mast_foot: slicer profile. 6 solid ring round holes (walls) / infill: 1.5 mm walls, 15 % infill (limit >= 2.0 mm walls or >= 40 % infill on loaded parts). Fix: set 5 walls (2.5 mm) and 40 % infill for the loaded parts.
- pen_slider: slicer profile. 6 solid ring round holes (walls) / infill: 1.5 mm walls, 15 % infill (limit >= 2.0 mm walls or >= 40 % infill on loaded parts). Fix: set 5 walls (2.5 mm) and 40 % infill for the loaded parts.
- x_carriage_plate: print orientation. 6 print +Z read from the STL: frame +Z (stl/x_carriage_plate.stl, fit 0.56 mm) (limit fit < 0.5 mm).
- y_carriage_left, y_carriage_right: print orientation (2 places). 6 print +Z read from the STL: frame +Z (stl/y_carriage_left.stl, fit 0.61 mm) (limit fit < 0.5 mm).
- y_chain_anchor: slicer profile. 6 solid ring round holes (walls) / infill: 1.5 mm walls, 15 % infill (limit >= 2.0 mm walls or >= 40 % infill on loaded parts). Fix: set 5 walls (2.5 mm) and 40 % infill for the loaded parts.
- shape.py: POLE_CLR (gap around the pole in the socket, on each side). 9 gap fit, gap each side: 0.15 mm (limit 0.3..5.0 mm). Fix: set POLE_CLR to 0.45 mm and print a fit test.
- x_carriage_plate: head screw T1 (M3 x 12 socket head). 9 pilot hole diameter (self-tapping): 3.40 mm (limit 2.34..2.85 mm). Fix: make the pilot 2.5 mm.
- x_carriage_plate: head screw T2 (M3 x 12 socket head). 9 pilot hole diameter (self-tapping): 3.40 mm (limit 2.34..2.85 mm). Fix: make the pilot 2.5 mm.
- x_carriage_plate: head screw H2 (M3 x 12 socket head). 9 pilot hole diameter (self-tapping): 3.40 mm (limit 2.34..2.85 mm). Fix: make the pilot 2.5 mm.
- x_carriage_plate: head screw H1 (M3 x 12 socket head). 9 pilot hole diameter (self-tapping): 3.40 mm (limit 2.34..2.85 mm). Fix: make the pilot 2.5 mm.
- y_front_left, y_front_right: Y bracket screw 0 (M3 x 12 socket head) (2 places). 9 pilot hole diameter (self-tapping): 3.40 mm (limit 2.34..2.85 mm). Fix: make the pilot 2.5 mm.

## The X idler mount

| part | feature | check | value | limit | result |
|---|---|---|---|---|---|
| y_idler_fork_left | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |
| y_idler_fork_right | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |
| x_idler_fork | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |
| y_idler_fork_left | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_idler_fork.stl, fit 0.20 mm) | fit < 0.5 mm | PASS |
| y_idler_fork_right | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_idler_fork.stl, fit 0.20 mm) | fit < 0.5 mm | PASS |
| x_idler_fork | print orientation | 6 print +Z read from the STL | frame +Z (stl/x_idler_fork.stl, fit 0.20 mm) | fit < 0.5 mm | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 0.0..5.0, 5.0 mm) | 5.2 mm at s 1.0 | >= 5.0 mm | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 15.5..23.5, 8.0 mm) | 5.2 mm at s 16.5 | >= 5.0 mm | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 3 flat seat under the socket head (8.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 3 preload on the PLA under the socket head at 1.20 N m | 35 MPa, SF 1.4 | SF >= 2 (50 MPa ESTIMATE) | WARN |
| y_idler_fork_left | left Y tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm) | 2.1 mm at s 12.0 | >= 3.0 mm | WARN |
| y_idler_fork_left | left Y tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 0.5..5.5, 5.0 mm) | 5.2 mm at s 4.0 | >= 5.0 mm | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 16.0..24.0, 8.0 mm) | 5.2 mm at s 22.5 | >= 5.0 mm | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |
| y_idler_fork_right | right Y tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm) | 2.1 mm at s 12.0 | >= 3.0 mm | WARN |
| y_idler_fork_right | right Y tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 0.0..5.0, 5.0 mm) | 5.2 mm at s 1.0 | >= 5.0 mm | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 15.5..23.5, 8.0 mm) | 5.2 mm at s 16.5 | >= 5.0 mm | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 3 flat seat under the socket head (8.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 3 preload on the PLA under the socket head at 1.20 N m | 35 MPa, SF 1.4 | SF >= 2 (50 MPa ESTIMATE) | WARN |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm) | 2.8 mm at s 1.5 | >= 3.0 mm | WARN |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |
| x_idler_fork | X tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm) | 2.1 mm at s 12.0 | >= 3.0 mm | WARN |
| x_idler_fork | X tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |
| y_idler_fork_left | y_idler_fork: M5 Y idler axle through both cheeks (2 washers), nyloc nut | 2 model.py length check (cross-check) | stands 1.5 mm out of the nut (at least 1) | model.py rule | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 2 screw past the M5 nyloc nut | 1.5 mm | >= 1.6 mm | WARN |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 2 screw past the M5 nyloc nut | 1.4 mm | >= 1.6 mm | WARN |
| x_idler_fork | x_idler_fork: M5 X idler axle through both cheeks (2 washers), nyloc nut | 2 model.py length check (cross-check) | stands 1.5 mm out of the nut (at least 1) | model.py rule | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 2 screw past the M5 nyloc nut | 1.4 mm | >= 1.6 mm | WARN |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 2 screw past the M3 nut | 5.1 mm | >= 0.5 mm | PASS |
| y_idler_fork_left | left Y idler axle: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN |
| y_idler_fork_left | left Y tension screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |
| y_idler_fork_right | right Y idler axle: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN |
| y_idler_fork_right | right Y tension screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |
| x_idler_fork | X tension screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |
| y_idler_fork_left | left Y idler axle: M5 washer, 7.5 mm across (small) | 9 washer touches only the inner race of the idler | washer OD 7.5 mm | <= 8.7 mm (625 inner race, ESTIMATE) | PASS |
| y_idler_fork_right | right Y idler axle: M5 washer, 7.5 mm across (small) | 9 washer touches only the inner race of the idler | washer OD 7.5 mm | <= 8.7 mm (625 inner race, ESTIMATE) | PASS |
| x_idler_fork | X idler axle: M5 washer, 7.5 mm across (small) | 9 washer touches only the inner race of the idler | washer OD 7.5 mm | <= 8.7 mm (625 inner race, ESTIMATE) | PASS |
| y_idler_fork_left | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |
| y_idler_fork_right | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |
| x_idler_fork | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 5 axle supports | two supports (y_idler_fork_left / y_idler_fork_left), span 17.0 mm | 2 or a boss >= 2 d | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 7 axle bending (143 N, 2 x t_max (180 deg wrap, both runs to the motor)) | 95 MPa, SF 6.8 | SF >= 3 on 640 MPa (class 8.8) | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (78 N) | 3.1 MPa, SF 16.1 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 1.4 MPa on 5.5 mm, SF 35.4 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (65 N) | 1.6 MPa, SF 30.7 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 0.7 MPa on 5.5 mm, SF 67.6 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 5 axle supports | two supports (y_idler_fork_right / y_idler_fork_right), span 17.0 mm | 2 or a boss >= 2 d | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 7 axle bending (143 N, 2 x t_max (180 deg wrap, both runs to the motor)) | 93 MPa, SF 6.9 | SF >= 3 on 640 MPa (class 8.8) | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (82 N) | 3.3 MPa, SF 15.3 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 1.5 MPa on 5.5 mm, SF 33.6 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (61 N) | 1.5 MPa, SF 32.8 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 0.7 MPa on 5.5 mm, SF 72.2 | SF >= 3 on 50 MPa | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 5 axle supports | two supports (x_idler_fork / x_idler_fork), span 17.0 mm | 2 or a boss >= 2 d | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 7 axle bending (143 N, 2 x t_max (180 deg wrap)) | 95 MPa, SF 6.8 | SF >= 3 on 640 MPa (class 8.8) | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (78 N) | 3.1 MPa, SF 16.1 | SF >= 3 on 50 MPa | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 1.4 MPa on 5.5 mm, SF 35.4 | SF >= 3 on 50 MPa | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (65 N) | 1.6 MPa, SF 30.7 | SF >= 3 on 50 MPa | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 0.7 MPa on 5.5 mm, SF 67.6 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |
| x_idler_fork | FEA | 8 max von Mises away from the fixtures | 7.0 MPa, SF 7.1 | SF >= 3 on 50 MPa | PASS |
| x_idler_fork | FEA | 8 max principal stress vs the layer strength | 6.4 MPa at /n.z/ 0.90, SF 4.2 | SF >= 3 on 27 MPa | PASS |
| y_idler_fork_left | FEA | 8 max von Mises away from the fixtures | 7.4 MPa, SF 6.7 | SF >= 3 on 50 MPa | PASS |
| y_idler_fork_left | FEA | 8 max principal stress vs the layer strength | 6.1 MPa at /n.z/ 0.94, SF 4.3 | SF >= 3 on 26 MPa | PASS |

## Load cases

| case | value | unit | source |
|---|---|---|---|
| belt_t0 | 40 | N per run | ESTIMATE: GT2 6 mm static tension, 20 to 40 N typical; the upper value |
| accel | 1.5e+03 | mm/s2 | firmware Accel, firmware/config/config.go |
| m_head | 167 | g | printed head parts x 0.6 (infill) + X wheels and axles 60 g + servo 9 g + pen 15 g (ESTIMATE) |
| m_gantry | 694 | g | printed gantry parts x 0.6 + the X motor (42-34, measured) 213 g + beam 415 mm x 0.49 g/mm + head (ESTIMATE) |
| f_acc_head | 0.25 | N | m_head x accel |
| f_acc_gantry | 1.04 | N | m_gantry x accel (both Y belts) |
| torque | 0.4 | N m | ESTIMATE: 40 mm NEMA17 holding torque |
| pulley_r | 6.37 | mm | GT2 20T pitch radius (shape.PULLEY_PD / 2) |
| f_stall | 62.8 | N | torque / pulley radius: the belt force when the axis is blocked |
| dt_stall | 31.4 | N | half of f_stall on each run (equal run stiffness, ESTIMATE) |
| t_max | 71.4 | N | belt_t0 + dt_stall: the highest run tension |
| servo | 12.9 | N | SG90 stall 0.18 N m (ESTIMATE) / horn 14 mm |
| hand | 20 | N | ESTIMATE: an accidental push on the gantry by hand |
| pen_drag | 1 | N | ESTIMATE: pen friction on paper |
| wheel | 37.8 | N | eccentric preload 30 N (ESTIMATE) + gantry weight / 6 wheels + hand push / 3 |

Materials (ESTIMATE): PLA E 3500 MPa, tensile 50 MPa in XY and 25 MPa in Z, compressive 50 MPa, thread shear 25 MPa. Steel class 8.8 yield 640 MPa.

## FEA

### y_carriage_left

- Mesh: 19444 tetrahedra, 111807 unknowns, 13.8 s.
- Max von Mises away from the fixtures: **9.9 MPa** (SF 5.1 on 50 MPa); at the fixture edges 9.9 MPa (a model peak).
- Worst principal stress against the layer strength: 7.3 MPa, |n.z| 0.60, strength 35 MPa, SF 4.7.
- Max displacement: 246 um.
- Deflection at beam end: 0.49 um under the operating loads (inertia at the firmware acceleration, pen drag; limit 50 um); 110 um under the worst case.
- Loads: left X motor screw -16 -16 (49 faces); left X motor screw -16 +16 (48 faces); left X motor screw +16 -16 (51 faces); hand push on the beam (555 faces).
- Fixtures: left Y wheel bolt 3 (142 faces); left Y wheel bolt 7 (79 faces); left Y wheel bolt 11 (123 faces).

![y_carriage_left](out/fea_y_carriage_left.png)

### y_carriage_right

- Mesh: 13394 tetrahedra, 78993 unknowns, 9.4 s.
- Max von Mises away from the fixtures: **9.2 MPa** (SF 5.4 on 50 MPa); at the fixture edges 9.2 MPa (a model peak).
- Worst principal stress against the layer strength: 8.5 MPa, |n.z| 0.97, strength 26 MPa, SF 3.0.
- Max displacement: 167 um.
- Deflection at beam end: 0.56 um under the operating loads (inertia at the firmware acceleration, pen drag; limit 50 um); 54 um under the worst case.
- Loads: X tension screw (83 faces); hand push on the beam (255 faces).
- Fixtures: right Y wheel bolt 3 (142 faces); right Y wheel bolt 7 (80 faces); right Y wheel bolt 11 (123 faces).

![y_carriage_right](out/fea_y_carriage_right.png)

### x_idler_fork

- Mesh: 11335 tetrahedra, 58233 unknowns, 5.9 s.
- Max von Mises away from the fixtures: **7.0 MPa** (SF 7.1 on 50 MPa); at the fixture edges 8.7 MPa (a model peak).
- Worst principal stress against the layer strength: 6.4 MPa, |n.z| 0.90, strength 27 MPa, SF 4.2.
- Max displacement: 91 um.
- Loads: X idler axle (67 faces); X idler axle (77 faces).
- Fixtures: X tension nut (191 faces); fork sits on its seat (378 faces).

![x_idler_fork](out/fea_x_idler_fork.png)

### pen_carriage

- Mesh: 25332 tetrahedra, 131853 unknowns, 13.9 s.
- Max von Mises away from the fixtures: **0.3 MPa** (SF 163.1 on 50 MPa); at the fixture edges 0.3 MPa (a model peak).
- Worst principal stress against the layer strength: 0.2 MPa, |n.z| 0.04, strength 50 MPa, SF 326.3.
- Max displacement: 23 um.
- Deflection at pen rail: 21.49 um under the operating loads (inertia at the firmware acceleration, pen drag; limit 50 um); 21 um under the worst case.
- Loads: pen drag on the rail (1213 faces).
- Fixtures: head screw T1 (116 faces); head screw T2 (116 faces); head screw H2 (116 faces); head screw H1 (116 faces).

![pen_carriage](out/fea_pen_carriage.png)

### x_carriage_plate

- Mesh: 25502 tetrahedra, 141714 unknowns, 15.2 s.
- Max von Mises away from the fixtures: **4.6 MPa** (SF 10.9 on 50 MPa); at the fixture edges 4.6 MPa (a model peak).
- Worst principal stress against the layer strength: 3.9 MPa, |n.z| 0.70, strength 32 MPa, SF 8.2.
- Max displacement: 119 um.
- Deflection at pen carriage seat (head screw T1): 0.57 um under the operating loads (inertia at the firmware acceleration, pen drag; limit 50 um); 1 um under the worst case.
- Deflection at pen carriage seat (head screw T2): 0.45 um under the operating loads (inertia at the firmware acceleration, pen drag; limit 50 um); 1 um under the worst case.
- Deflection at pen carriage seat (head screw H2): 0.23 um under the operating loads (inertia at the firmware acceleration, pen drag; limit 50 um); 1 um under the worst case.
- Deflection at pen carriage seat (head screw H1): 0.21 um under the operating loads (inertia at the firmware acceleration, pen drag; limit 50 um); 2 um under the worst case.
- Loads: X belt clip left (420 faces); X belt clip right (416 faces); pen drag at head screw T1 (75 faces); pen drag at head screw T2 (72 faces); pen drag at head screw H2 (67 faces); pen drag at head screw H1 (70 faces).
- Fixtures: X wheel axle top left (164 faces); X wheel axle top right (148 faces); X wheel axle bottom (142 faces).

![x_carriage_plate](out/fea_x_carriage_plate.png)

### y_motor_mount_left

- Mesh: 11742 tetrahedra, 64254 unknowns, 5.5 s.
- Max von Mises away from the fixtures: **2.0 MPa** (SF 24.6 on 50 MPa); at the fixture edges 2.0 MPa (a model peak).
- Worst principal stress against the layer strength: 1.5 MPa, |n.z| 0.43, strength 40 MPa, SF 27.2.
- Max displacement: 16 um.
- Loads: left Y motor screw -16 -16 (50 faces); left Y motor screw -16 +16 (52 faces); left Y motor screw +16 -16 (51 faces); left Y motor screw +16 +16 (50 faces).
- Fixtures: the bracket face on the back bar (526 faces); left Y motor bracket screw x 46 (110 faces); left Y motor bracket screw x 59 (109 faces).

![y_motor_mount_left](out/fea_y_motor_mount_left.png)

### y_idler_fork_left

- Mesh: 11337 tetrahedra, 58338 unknowns, 5.8 s.
- Max von Mises away from the fixtures: **7.4 MPa** (SF 6.7 on 50 MPa); at the fixture edges 9.6 MPa (a model peak).
- Worst principal stress against the layer strength: 6.1 MPa, |n.z| 0.94, strength 26 MPa, SF 4.3.
- Max displacement: 91 um.
- Loads: left Y idler axle (63 faces); left Y idler axle (83 faces).
- Fixtures: X tension nut (193 faces); fork sits on its seat (380 faces).

![y_idler_fork_left](out/fea_y_idler_fork_left.png)

## Values to measure or confirm

- The GT2 belt tension (ESTIMATE 40 N per run). Measure it with a belt tension app or a spring scale.
- The holding torque of the Y and X motors (ESTIMATE 0.4 N m). Read it from the motor label or data sheet.
- The slot depth of the 2020 rails and bars (ESTIMATE 6.3 mm) and the lip (ESTIMATE 1.8 mm).
- The T-nut thread length (ESTIMATE 4 mm).
- The heat-set insert length and OD (shape.INSERT_M5). The rule for the boss: 1.5 x OD minimum, 2 x OD preferred.
- The inner race OD of the idler bearings (ESTIMATE 7.5 mm). A washer wider than the inner race rubs on the shield.
- The tightening torque that you use on screws into PLA (ESTIMATE: M3 0.5 N m, M5 1.5 N m).
- The PLA strength of your filament (ESTIMATE 50 MPa in XY, 25 MPa in Z). Print a test bar in each direction.

## All results

<details><summary>The full table (one row per check)</summary>

| part | feature | check | value | limit | result | fix |
|---|---|---|---|---|---|---|
| y_motor_mount_left | left Y motor screw -16 -16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 13 mm (stop: left Y motor bracket screw x 46, at gantry y 271, X x 193) | >= 60 mm | FAIL | open a key hole through the left Y motor bracket screw x 46 on the screw axis, or fit this screw before the left Y motor bracket screw x 46 |
| y_motor_mount_right | right Y motor screw +16 +16 (M3 x 10 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 93 MPa, SF 0.5 | SF >= 2 (50 MPa ESTIMATE) | FAIL | tighten to 0.11 N m at most, or put a washer under the head (M3 washer) |
| y_motor_mount_right | right Y motor screw +16 -16 (M3 x 10 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 93 MPa, SF 0.5 | SF >= 2 (50 MPa ESTIMATE) | FAIL | tighten to 0.11 N m at most, or put a washer under the head (M3 washer) |
| y_motor_mount_right | right Y motor screw -16 +16 (M3 x 10 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 93 MPa, SF 0.5 | SF >= 2 (50 MPa ESTIMATE) | FAIL | tighten to 0.11 N m at most, or put a washer under the head (M3 washer) |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 93 MPa, SF 0.5 | SF >= 2 (50 MPa ESTIMATE) | FAIL | tighten to 0.11 N m at most, or put a washer under the head (M3 washer) |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 13 mm (stop: right Y motor bracket screw x 46, at gantry y 271, X x 193) | >= 60 mm | FAIL | open a key hole through the right Y motor bracket screw x 46 on the screw axis, or fit this screw before the right Y motor bracket screw x 46 |
| mast_foot | pole collar screw (M3 x 16 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 45 MPa, SF 1.1 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.22 N m at most, or put a washer under the head (M3 washer) |
| mast_foot | pole foot screw +25 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 3.2 mm at s 4.0 | >= 5.0 mm | WARN | add material: make the boss 15 mm OD round the hole, or move the hole 1.8 mm away from the edge |
| mast_foot | pole foot screw -25 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 3.2 mm at s 1.5 | >= 5.0 mm | WARN | add material: make the boss 15 mm OD round the hole, or move the hole 1.8 mm away from the edge |
| mast_foot | slicer profile | 6 solid ring round holes (walls) / infill | 1.5 mm walls, 15 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | WARN | set 5 walls (2.5 mm) and 40 % infill for the loaded parts |
| pen_carriage | head screw H1 (M3 x 12 socket head) | 6/7 thread pull-out (across the layers) at 0.30 N m | capacity 459 N vs preload 333 N, SF 1.4 | SF >= 2 (preload) | WARN | tighten to 0.21 N m at most, or use a heat-set insert |
| pen_carriage | head screw H2 (M3 x 12 socket head) | 6/7 thread pull-out (across the layers) at 0.30 N m | capacity 459 N vs preload 333 N, SF 1.4 | SF >= 2 (preload) | WARN | tighten to 0.21 N m at most, or use a heat-set insert |
| pen_carriage | head screw T1 (M3 x 12 socket head) | 6/7 thread pull-out (across the layers) at 0.30 N m | capacity 459 N vs preload 333 N, SF 1.4 | SF >= 2 (preload) | WARN | tighten to 0.21 N m at most, or use a heat-set insert |
| pen_carriage | head screw T2 (M3 x 12 socket head) | 6/7 thread pull-out (across the layers) at 0.30 N m | capacity 459 N vs preload 333 N, SF 1.4 | SF >= 2 (preload) | WARN | tighten to 0.21 N m at most, or use a heat-set insert |
| pen_slider | pen clamp screw (M3 x 20 socket head) | 2 joint data | no Joint in fasteners.py | a Joint | WARN | add a Joint for this screw |
| pen_slider | slicer profile | 6 solid ring round holes (walls) / infill | 1.5 mm walls, 15 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | WARN | set 5 walls (2.5 mm) and 40 % infill for the loaded parts |
| shape.py | POLE_CLR (gap around the pole in the socket, on each side) | 9 gap fit, gap each side | 0.15 mm | 0.3..5.0 mm | WARN | set POLE_CLR to 0.45 mm and print a fit test |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 1 hole wall closed (insert) | slot or pocket, 15 deg open | 0 deg open | WARN |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 1 insert boss diameter (material OD round the insert) | 12.8 mm (wall 3.2) | >= 10.5 (1.5 x OD 7.0); 14 preferred | WARN | make the boss 14 mm OD |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 2 thread in the insert | 7.4 mm (insert 9.5 mm long) | >= 7.5 mm (1.5 d) | WARN | use a long insert (M5 x 9 mm or more) and a screw that passes through it |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 2 screw past the M5 nyloc nut | 1.0 mm | >= 1.6 mm | WARN | use a screw 31 mm long or more |
| x_carriage_plate | X wheel axle top left: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN | put an M5 washer under the nut |
| x_carriage_plate | X wheel axle top right: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN | put an M5 washer under the nut |
| x_carriage_plate | head screw H1 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 3.40 mm | 2.34..2.85 mm | WARN | make the pilot 2.5 mm |
| x_carriage_plate | head screw H2 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 3.40 mm | 2.34..2.85 mm | WARN | make the pilot 2.5 mm |
| x_carriage_plate | head screw T1 (M3 x 12 socket head) | 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm) | 1.8 mm at s 1.5 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 1.2 mm away from the edge |
| x_carriage_plate | head screw T1 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 3.40 mm | 2.34..2.85 mm | WARN | make the pilot 2.5 mm |
| x_carriage_plate | head screw T2 (M3 x 12 socket head) | 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm) | 1.8 mm at s 1.5 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 1.2 mm away from the edge |
| x_carriage_plate | head screw T2 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 3.40 mm | 2.34..2.85 mm | WARN | make the pilot 2.5 mm |
| x_carriage_plate | print orientation | 6 print +Z read from the STL | frame +Z (stl/x_carriage_plate.stl, fit 0.56 mm) | fit < 0.5 mm | WARN |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 3 preload on the PLA under the socket head at 1.20 N m | 35 MPa, SF 1.4 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.85 N m at most, or put a washer under the head (M5 washer) |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 2 screw past the M5 nyloc nut | 1.4 mm | >= 1.6 mm | WARN | use a screw 31 mm long or more |
| x_idler_fork | X tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm) | 2.1 mm at s 12.0 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.9 mm away from the edge |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 2.8 mm at s 1.0 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.2 mm away from the edge |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 45 MPa, SF 1.1 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.22 N m at most, or put a washer under the head (M3 washer) |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 45 MPa, SF 1.1 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.22 N m at most, or put a washer under the head (M3 washer) |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 2.9 mm at s 1.0 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.1 mm away from the edge |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 45 MPa, SF 1.1 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.22 N m at most, or put a washer under the head (M3 washer) |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 7 PLA face under the clamped stack (10.0 mm, preload 1200 N) | 26.6 MPa (21.9 preload + 4.7 moment), SF 1.9 | SF >= 3 on 50 MPa | WARN | put a 15 mm washer on the face, or lower the torque |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 1 insert boss diameter (material OD round the insert) | 14.0 mm (wall 3.8) | >= 10.5 (1.5 x OD 7.0); 14 preferred | WARN | make the boss 14 mm OD |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 7 PLA face under the clamped stack (10.0 mm, preload 1200 N) | 26.7 MPa (21.9 preload + 4.8 moment), SF 1.9 | SF >= 3 on 50 MPa | WARN | put a 15 mm washer on the face, or lower the torque |
| y_carriage_left | left Y wheel bolt 7: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN | put an M5 washer under the nut |
| y_carriage_left | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_carriage_left.stl, fit 0.61 mm) | fit < 0.5 mm | WARN |  |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm) | 2.8 mm at s 1.5 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.2 mm away from the edge |
| y_carriage_right | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_carriage_right.stl, fit 0.58 mm) | fit < 0.5 mm | WARN |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 7 PLA face under the clamped stack (10.0 mm, preload 1200 N) | 26.6 MPa (21.9 preload + 4.7 moment), SF 1.9 | SF >= 3 on 50 MPa | WARN | put a 15 mm washer on the face, or lower the torque |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 1 insert boss diameter (material OD round the insert) | 14.0 mm (wall 3.8) | >= 10.5 (1.5 x OD 7.0); 14 preferred | WARN | make the boss 14 mm OD |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 7 PLA face under the clamped stack (10.0 mm, preload 1200 N) | 26.7 MPa (21.9 preload + 4.8 moment), SF 1.9 | SF >= 3 on 50 MPa | WARN | put a 15 mm washer on the face, or lower the torque |
| y_carriage_right | right Y wheel bolt 7: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN | put an M5 washer under the nut |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 4.9 mm at s 1.0 | >= 5.0 mm | WARN | add material: make the boss 15 mm OD round the hole, or move the hole 0.1 mm away from the edge |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 3 preload on the PLA under the socket head at 1.20 N m | 35 MPa, SF 1.4 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.85 N m at most, or put a washer under the head (M5 washer) |
| y_chain_anchor | slicer profile | 6 solid ring round holes (walls) / infill | 1.5 mm walls, 15 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | WARN | set 5 walls (2.5 mm) and 40 % infill for the loaded parts |
| y_front_left | left Y bracket screw 0 (M3 x 12 socket head) | 1 meat round the clearance hole (s 0.5..4.5, 4.0 mm) | 2.8 mm at s 1.5 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.2 mm away from the edge |
| y_front_left | left Y bracket screw 0 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 3.40 mm | 2.34..2.85 mm | WARN | make the pilot 2.5 mm |
| y_front_left | left Y switch screw 0 (M3 x 8 socket head) | 1 insert boss diameter (material OD round the insert) | 7.5 mm (wall 1.8) | >= 6.9 (1.5 x OD 4.6); 9 preferred | WARN | make the boss 9 mm OD |
| y_front_left | left Y switch screw 1 (M3 x 8 socket head) | 1 insert boss diameter (material OD round the insert) | 7.1 mm (wall 1.6) | >= 6.9 (1.5 x OD 4.6); 9 preferred | WARN | make the boss 9 mm OD |
| y_front_right | right Y bracket screw 0 (M3 x 12 socket head) | 1 meat round the clearance hole (s 0.5..4.5, 4.0 mm) | 2.8 mm at s 1.5 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.2 mm away from the edge |
| y_front_right | right Y bracket screw 0 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 3.40 mm | 2.34..2.85 mm | WARN | make the pilot 2.5 mm |
| y_front_right | right Y switch screw 0 (M3 x 8 socket head) | 1 insert boss diameter (material OD round the insert) | 7.5 mm (wall 1.8) | >= 6.9 (1.5 x OD 4.6); 9 preferred | WARN | make the boss 9 mm OD |
| y_front_right | right Y switch screw 1 (M3 x 8 socket head) | 1 insert boss diameter (material OD round the insert) | 7.1 mm (wall 1.6) | >= 6.9 (1.5 x OD 4.6); 9 preferred | WARN | make the boss 9 mm OD |
| y_idler_bracket_left | left Y tension screw (M3 x 20 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 45 MPa, SF 1.1 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.22 N m at most, or put a washer under the head (M3 washer) |
| y_idler_bracket_right | right Y tension screw (M3 x 20 socket head) | 3 preload on the PLA under the socket head at 0.40 N m | 45 MPa, SF 1.1 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.22 N m at most, or put a washer under the head (M3 washer) |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 3 preload on the PLA under the socket head at 1.20 N m | 35 MPa, SF 1.4 | SF >= 2 (50 MPa ESTIMATE) | WARN | tighten to 0.85 N m at most, or put a washer under the head (M5 washer) |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 2 screw past the M5 nyloc nut | 1.5 mm | >= 1.6 mm | WARN | use a screw 31 mm long or more |
| y_idler_fork_left | left Y idler axle: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN | put an M5 washer under the nut |
| y_idler_fork_left | left Y tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm) | 2.1 mm at s 12.0 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.9 mm away from the edge |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 2 screw past the M5 nyloc nut | 1.4 mm | >= 1.6 mm | WARN | use a screw 31 mm long or more |
| y_idler_fork_right | right Y idler axle: M5 nyloc nut | 3 washer under the nut on PLA | no washer | a washer | WARN | put an M5 washer under the nut |
| y_idler_fork_right | right Y tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 11.0..20.5, 9.5 mm) | 2.1 mm at s 12.0 | >= 3.0 mm | WARN | add material: make the boss 9 mm OD round the hole, or move the hole 0.9 mm away from the edge |
| y_motor_mount_left | left Y motor bracket screw x 46 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 3.3 mm at s 1.5 | >= 5.0 mm | WARN | add material: make the boss 15 mm OD round the hole, or move the hole 1.7 mm away from the edge |
| y_motor_mount_left | left Y motor bracket screw x 59 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 3.2 mm at s 5.0 | >= 5.0 mm | WARN | add material: make the boss 15 mm OD round the hole, or move the hole 1.8 mm away from the edge |
| y_motor_mount_right | right Y motor bracket screw x 46 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 3.3 mm at s 1.5 | >= 5.0 mm | WARN | add material: make the boss 15 mm OD round the hole, or move the hole 1.7 mm away from the edge |
| y_motor_mount_right | right Y motor bracket screw x 59 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 3.2 mm at s 3.0 | >= 5.0 mm | WARN | add material: make the boss 15 mm OD round the hole, or move the hole 1.8 mm away from the edge |
| frame (stock) | bar end screw x 10 y 0 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| frame (stock) | bar end screw x 10 y 520 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| frame (stock) | bar end screw x 30 y 0 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| frame (stock) | bar end screw x 30 y 520 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| frame (stock) | bar end screw x 370 y 0 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| frame (stock) | bar end screw x 370 y 520 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| frame (stock) | bar end screw x 390 y 0 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| frame (stock) | bar end screw x 390 y 520 (M5 x 30 socket head (stock)) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| mast_foot | mast_foot: M3 collar screw, M3 nut | 2 model.py length check (cross-check) | stands 4.4 mm out of the nut (at least 1) | model.py rule | PASS |  |
| mast_foot | mast_foot: M5 into a T-nut | 2 model.py length check (cross-check) | 4.0 mm in the T-nut, tip 6.0 mm into the slot (slot depth 6.3) | model.py rule | PASS |  |
| mast_foot | mast_foot: M6 into the pole end | 2 model.py length check (cross-check) | 12.0 mm of thread in a 15.0 mm thread (at least 5.0) | model.py rule | PASS |  |
| mast_foot | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| mast_foot | pole collar screw (M3 x 16 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 4.5 mm at s 1.0 | >= 3.0 mm | PASS |  |
| mast_foot | pole collar screw (M3 x 16 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| mast_foot | pole collar screw (M3 x 16 socket head) | 1 meat round the clearance hole (s 8.0..14.0, 6.0 mm) | 4.6 mm at s 12.5 | >= 3.0 mm | PASS |  |
| mast_foot | pole collar screw (M3 x 16 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| mast_foot | pole collar screw (M3 x 16 socket head) | 3 flat seat under the socket head (5.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| mast_foot | pole collar screw (M3 x 16 socket head) | 2 screw past the M3 nut | 4.3 mm | >= 0.5 mm | PASS |  |
| mast_foot | pole collar screw (M3 x 16 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| mast_foot | pole collar screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |  |
| mast_foot | pole foot screw +25 (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| mast_foot | pole foot screw +25 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| mast_foot | pole foot screw +25 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| mast_foot | pole foot screw +25 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| mast_foot | pole foot screw -25 (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| mast_foot | pole foot screw -25 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| mast_foot | pole foot screw -25 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| mast_foot | pole foot screw -25 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| mast_foot | pole screw (M6 x 16 socket head) | 1 meat round the clearance hole (s 0.5..4.0, 3.5 mm) | 9.1 mm at s 1.5 | >= 6.0 mm | PASS |  |
| mast_foot | pole screw (M6 x 16 socket head) | 9 clearance hole diameter | 6.50 mm | 6.2..7.2 (ISO 273 6.6) | PASS |  |
| mast_foot | pole screw (M6 x 16 socket head) | 2 thread in the metal part | 12.0 mm of 15.0 | 4.8..15.0 mm | PASS |  |
| mast_foot | pole screw (M6 x 16 socket head) | 4 straight socket head key line from the head | 80 mm | >= 80 mm | PASS |  |
| mast_foot | print orientation | 6 print +Z read from the STL | frame +Z (stl/mast_foot.stl, fit 0.46 mm) | fit < 0.5 mm | PASS |  |
| pen_carriage | FEA | 8 max von Mises away from the fixtures | 0.3 MPa, SF 163.1 | SF >= 3 on 50 MPa | PASS |  |
| pen_carriage | FEA | 8 max principal stress vs the layer strength | 0.2 MPa at /n.z/ 0.04, SF 326.3 | SF >= 3 on 50 MPa | PASS |  |
| pen_carriage | FEA probe: pen rail | 8 deflection at the probe, operating loads (inertia, pen drag) | 21.49 um (worst case 21 um) | <= 50 um | PASS |  |
| pen_carriage | head screw H1 (M3 x 12 socket head) | 1 meat round the thread hole (s 5.5..12.5, 7.0 mm) | 6.9 mm at s 6.5 | >= 3.0 mm | PASS |  |
| pen_carriage | head screw H1 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| pen_carriage | head screw H1 (M3 x 12 socket head) | 2 self-tap thread length (geometry) | 6.0 mm; joint data: 7.0 mm past the grip, pilot 8.0 | >= 6.0 mm (2 d) | PASS |  |
| pen_carriage | head screw H1 (M3 x 12 socket head) | 2 tip does not bottom out | pilot free inf mm past the tip | >= 0.5 mm | PASS |  |
| pen_carriage | head screw H2 (M3 x 12 socket head) | 1 meat round the thread hole (s 5.5..12.5, 7.0 mm) | 5.4 mm at s 6.5 | >= 3.0 mm | PASS |  |
| pen_carriage | head screw H2 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| pen_carriage | head screw H2 (M3 x 12 socket head) | 2 self-tap thread length (geometry) | 6.0 mm; joint data: 7.0 mm past the grip, pilot 8.0 | >= 6.0 mm (2 d) | PASS |  |
| pen_carriage | head screw H2 (M3 x 12 socket head) | 2 tip does not bottom out | pilot free inf mm past the tip | >= 0.5 mm | PASS |  |
| pen_carriage | head screw T1 (M3 x 12 socket head) | 1 meat round the thread hole (s 5.5..12.5, 7.0 mm) | 4.8 mm at s 6.5 | >= 3.0 mm | PASS |  |
| pen_carriage | head screw T1 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| pen_carriage | head screw T1 (M3 x 12 socket head) | 2 self-tap thread length (geometry) | 6.0 mm; joint data: 7.0 mm past the grip, pilot 8.0 | >= 6.0 mm (2 d) | PASS |  |
| pen_carriage | head screw T1 (M3 x 12 socket head) | 2 tip does not bottom out | pilot free inf mm past the tip | >= 0.5 mm | PASS |  |
| pen_carriage | head screw T2 (M3 x 12 socket head) | 1 meat round the thread hole (s 5.5..12.5, 7.0 mm) | 4.8 mm at s 6.5 | >= 3.0 mm | PASS |  |
| pen_carriage | head screw T2 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| pen_carriage | head screw T2 (M3 x 12 socket head) | 2 self-tap thread length (geometry) | 6.0 mm; joint data: 7.0 mm past the grip, pilot 8.0 | >= 6.0 mm (2 d) | PASS |  |
| pen_carriage | head screw T2 (M3 x 12 socket head) | 2 tip does not bottom out | pilot free inf mm past the tip | >= 0.5 mm | PASS |  |
| pen_carriage | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| pen_carriage | pen_carriage: M2 servo screw (in the servo bag) | 2 model.py length check (cross-check) | 5.5 mm of thread in a 8.0 mm pilot (at least 4) | model.py rule | PASS |  |
| pen_carriage | print orientation | 6 print +Z read from the STL | frame -Y (stl/pen_carriage.stl, fit 0.45 mm) | fit < 0.5 mm | PASS |  |
| pen_carriage | servo screw +14 (M2 x 8 self-tapping (stock, in the servo bag)) | 4 straight Phillips driver line from the head | 60 mm | >= 60 mm | PASS |  |
| pen_carriage | servo screw -14 (M2 x 8 self-tapping (stock, in the servo bag)) | 4 straight Phillips driver line from the head | 60 mm | >= 60 mm | PASS |  |
| pen_carriage | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| pen_slider | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| pen_slider | pen clamp screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 7.5..16.0, 8.5 mm) | 5.6 mm at s 8.5 | >= 3.0 mm | PASS |  |
| pen_slider | pen clamp screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| pen_slider | pen clamp screw (M3 x 20 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| pen_slider | pen clamp screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |  |
| pen_slider | print orientation | 6 print +Z read from the STL | frame +Z (stl/pen_slider.stl, fit 0.34 mm) | fit < 0.5 mm | PASS |  |
| shape.py | CRADLE_CLR (gap around the beam) | 9 gap fit, gap each side | 0.30 mm | 0.3..5.0 mm | PASS |  |
| shape.py | DT_CLR (gap between the rail and the slot, on each side) | 9 slide fit, gap each side | 0.25 mm | 0.2..0.4 mm | PASS |  |
| shape.py | FORK_CLR (the slide gap each side) | 9 slide fit, gap each side | 0.30 mm | 0.2..0.4 mm | PASS |  |
| shape.py | FORK_CLR (the slide gap each side) | 9 slide fit, gap each side | 0.30 mm | 0.2..0.4 mm | PASS |  |
| shape.py | KEEP_CLR (gap between the outline and a wheel bolt head) | 9 gap fit, gap each side | 0.50 mm | 0.3..5.0 mm | PASS |  |
| shape.py | SERVO_CLR (gap around the body in the pocket) | 9 gap fit, gap each side | 0.30 mm | 0.3..5.0 mm | PASS |  |
| shape.py | WELL_CLR (gap around a top wheel in its well) | 9 gap fit, gap each side | 1.00 mm | 0.3..5.0 mm | PASS |  |
| shape.py | YS_CLR (the gap around the sled in the channel) | 9 slide fit, gap each side | 0.40 mm | 0.2..0.4 mm | PASS |  |
| x_carriage_plate | FEA | 8 max von Mises away from the fixtures | 4.6 MPa, SF 10.9 | SF >= 3 on 50 MPa | PASS |  |
| x_carriage_plate | FEA | 8 max principal stress vs the layer strength | 3.9 MPa at /n.z/ 0.70, SF 8.2 | SF >= 3 on 32 MPa | PASS |  |
| x_carriage_plate | FEA probe: pen carriage seat (head screw H1) | 8 deflection at the probe, operating loads (inertia, pen drag) | 0.21 um (worst case 2 um) | <= 50 um | PASS |  |
| x_carriage_plate | FEA probe: pen carriage seat (head screw H2) | 8 deflection at the probe, operating loads (inertia, pen drag) | 0.23 um (worst case 1 um) | <= 50 um | PASS |  |
| x_carriage_plate | FEA probe: pen carriage seat (head screw T1) | 8 deflection at the probe, operating loads (inertia, pen drag) | 0.57 um (worst case 1 um) | <= 50 um | PASS |  |
| x_carriage_plate | FEA probe: pen carriage seat (head screw T2) | 8 deflection at the probe, operating loads (inertia, pen drag) | 0.45 um (worst case 1 um) | <= 50 um | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 1 meat round the insert hole (s 14.2..25.2, 11.0 mm) | 12.0 mm at s 16.8 | >= 5.0 mm | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 1 insert hole depth | 13.0 mm | >= 10.5 (insert 9.5 + 1) | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 2 tip does not bottom out past the insert | tip -1.7 mm past the insert | free hole past the insert | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 5 axle supports (cantilever) | one support, boss 11.0 mm, lever 9.1 mm | boss >= 10 mm (2 d) | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 54 MPa, SF 11.9 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 7 PLA bearing, loose joint model (38 N at 9.1 mm) | 4.1 MPa, SF 12.2 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.1 MPa on 14.5 mm, SF 211.4 | SF >= 3 on 25 MPa | PASS |  |
| x_carriage_plate | X wheel axle bottom (M5 x 25 button head (ISO 7380)) | 4 straight button head key line from the head | 70 mm | >= 70 mm | PASS |  |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 1 meat round the axle hole (s 14.2..24.2, 10.0 mm) | 5.2 mm at s 19.2 | >= 5.0 mm | PASS |  |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 5 axle supports (cantilever) | one support, boss 10.0 mm, lever 9.1 mm | boss >= 10 mm (2 d) | PASS |  |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 54 MPa, SF 11.9 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 7 PLA bearing, loose joint model (38 N at 9.1 mm) | 4.9 MPa, SF 10.2 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.2 MPa on 11.2 mm, SF 148.5 | SF >= 3 on 25 MPa | PASS |  |
| x_carriage_plate | X wheel axle top left (M5 x 30 button head (ISO 7380)) | 4 straight button head key line from the head | 70 mm | >= 70 mm | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 1 meat round the axle hole (s 16.8..28.8, 12.0 mm) | 5.2 mm at s 19.2 | >= 5.0 mm | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 2 screw past the M5 nyloc nut | 1.7 mm | >= 1.6 mm | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 5 axle supports (cantilever) | one support, boss 12.0 mm, lever 11.6 mm | boss >= 10 mm (2 d) | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 69 MPa, SF 9.3 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 7 PLA bearing, loose joint model (38 N at 11.6 mm) | 4.3 MPa, SF 11.7 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 7 PLA face under the clamped stack (14.3 mm, preload 1200 N) | 10.4 MPa (8.8 preload + 1.6 moment), SF 4.8 | SF >= 3 on 50 MPa | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 7 clamped stack does not open under the moment | moment 1.6 MPa vs preload 8.8 MPa | moment <= preload / 2 | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.1 MPa on 12.1 mm, SF 192.1 | SF >= 3 on 25 MPa | PASS |  |
| x_carriage_plate | X wheel axle top right (M5 x 35 button head (ISO 7380)) | 4 straight button head key line from the head | 70 mm | >= 70 mm | PASS |  |
| x_carriage_plate | head screw H1 (M3 x 12 socket head) | 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm) | 8.6 mm at s 1.5 | >= 3.0 mm | PASS |  |
| x_carriage_plate | head screw H1 (M3 x 12 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| x_carriage_plate | head screw H2 (M3 x 12 socket head) | 1 meat round the clearance hole (s 0.5..5.5, 5.0 mm) | 4.0 mm at s 1.5 | >= 3.0 mm | PASS |  |
| x_carriage_plate | head screw H2 (M3 x 12 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| x_carriage_plate | head screw T1 (M3 x 12 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| x_carriage_plate | head screw T2 (M3 x 12 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| x_carriage_plate | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| x_carriage_plate | pen_carriage: M3 from the back of the X plate | 2 model.py length check (cross-check) | 7.0 mm of thread in a 8.0 mm pilot (at least 6) | model.py rule | PASS |  |
| x_carriage_plate | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| x_carriage_plate | x_carriage_plate: M5 bottom wheel axle (head behind the wheel) into a heat-set insert in the boss | 2 model.py length check (cross-check) | 7.8 mm of thread in a 9.5 mm heat-set insert | model.py rule | PASS |  |
| x_carriage_plate | x_carriage_plate: M5 eccentric top wheel axle (head behind the wheel), nyloc nut in front | 2 model.py length check (cross-check) | stands 1.8 mm out of the nut (at least 1) | model.py rule | PASS |  |
| x_carriage_plate | x_carriage_plate: M5 top wheel axle (head behind the wheel), nyloc nut in front | 2 model.py length check (cross-check) | stands 1.1 mm out of the nut (at least 1) | model.py rule | PASS |  |
| x_idler_fork | FEA | 8 max von Mises away from the fixtures | 7.0 MPa, SF 7.1 | SF >= 3 on 50 MPa | PASS |  |
| x_idler_fork | FEA | 8 max principal stress vs the layer strength | 6.4 MPa at /n.z/ 0.90, SF 4.2 | SF >= 3 on 27 MPa | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 0.0..5.0, 5.0 mm) | 5.2 mm at s 1.0 | >= 5.0 mm | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 15.5..23.5, 8.0 mm) | 5.2 mm at s 16.5 | >= 5.0 mm | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 3 flat seat under the socket head (8.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 5 axle supports | two supports (x_idler_fork / x_idler_fork), span 17.0 mm | 2 or a boss >= 2 d | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 7 axle bending (143 N, 2 x t_max (180 deg wrap)) | 95 MPa, SF 6.8 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (78 N) | 3.1 MPa, SF 16.1 | SF >= 3 on 50 MPa | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 1.4 MPa on 5.5 mm, SF 35.4 | SF >= 3 on 50 MPa | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (65 N) | 1.6 MPa, SF 30.7 | SF >= 3 on 50 MPa | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 0.7 MPa on 5.5 mm, SF 67.6 | SF >= 3 on 50 MPa | PASS |  |
| x_idler_fork | X idler axle (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| x_idler_fork | X idler axle: M5 washer, 7.5 mm across (small) | 9 washer touches only the inner race of the idler | washer OD 7.5 mm | <= 8.7 mm (625 inner race, ESTIMATE) | PASS |  |
| x_idler_fork | X tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| x_idler_fork | X tension screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |  |
| x_idler_fork | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| x_idler_fork | print orientation | 6 print +Z read from the STL | frame +Z (stl/x_idler_fork.stl, fit 0.20 mm) | fit < 0.5 mm | PASS |  |
| x_idler_fork | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| x_idler_fork | x_idler_fork: M5 X idler axle through both cheeks (2 washers), nyloc nut | 2 model.py length check (cross-check) | stands 1.5 mm out of the nut (at least 1) | model.py rule | PASS |  |
| y_carriage | M5 heat-set insert hole 6.4 for OD 7.0 | 9 insert hole / OD | 0.91 | 0.85..0.95 (insert maker data, ESTIMATE) | PASS |  |
| y_carriage | eccentric spacer shank in ECC_HOLE | 9 slide fit (turns by hand) | 0.20 mm each side | 0.15..0.4 mm | PASS |  |
| y_carriage_left | FEA | 8 max von Mises away from the fixtures | 9.9 MPa, SF 5.1 | SF >= 3 on 50 MPa | PASS |  |
| y_carriage_left | FEA | 8 max principal stress vs the layer strength | 7.3 MPa at /n.z/ 0.60, SF 4.7 | SF >= 3 on 35 MPa | PASS |  |
| y_carriage_left | FEA probe: beam end | 8 deflection at the probe, operating loads (inertia, pen drag) | 0.49 um (worst case 110 um) | <= 50 um | PASS |  |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 3 flat seat under the socket head (5.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 3 counterbore round the head (gap each side) | 0.50 mm | >= 0.25 mm (FDM holes print small) | PASS |  |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 2 thread in the metal part | 4.3 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (54 N: 2 x t_max toward the X idler / 3 + torque) | 3.0 MPa, SF 16.8 | SF >= 3 | PASS |  |
| y_carriage_left | left X motor screw +16 -16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 3.7 mm at s 1.0 | >= 3.0 mm | PASS |  |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 3 flat seat under the socket head (5.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 3 counterbore round the head (gap each side) | 0.50 mm | >= 0.25 mm (FDM holes print small) | PASS |  |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 2 thread in the metal part | 4.3 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (54 N: 2 x t_max toward the X idler / 3 + torque) | 3.0 MPa, SF 16.8 | SF >= 3 | PASS |  |
| y_carriage_left | left X motor screw -16 +16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 3 flat seat under the socket head (5.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 3 counterbore round the head (gap each side) | 0.50 mm | >= 0.25 mm (FDM holes print small) | PASS |  |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 2 thread in the metal part | 4.3 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (54 N: 2 x t_max toward the X idler / 3 + torque) | 3.0 MPa, SF 16.8 | SF >= 3 | PASS |  |
| y_carriage_left | left X motor screw -16 -16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_left | left X switch screw 0 (M3 x 8 socket head) | 1 meat round the insert hole (s 2.0..8.5, 6.5 mm) | inf mm | >= 3.0 mm | PASS |  |
| y_carriage_left | left X switch screw 0 (M3 x 8 socket head) | 1 insert boss diameter (material OD round the insert) | 10.1 mm (wall 2.0) | >= 6.9 (1.5 x OD 4.6); 9 preferred | PASS |  |
| y_carriage_left | left X switch screw 0 (M3 x 8 socket head) | 1 insert hole depth | 7.0 mm | >= 6.7 (insert 5.7 + 1) | PASS |  |
| y_carriage_left | left X switch screw 0 (M3 x 8 socket head) | 2 thread in the insert | 5.6 mm (insert 5.7 mm long) | >= 4.5 mm (1.5 d) | PASS |  |
| y_carriage_left | left X switch screw 0 (M3 x 8 socket head) | 2 tip does not bottom out past the insert | tip +0.8 mm past the insert | free hole past the insert | PASS |  |
| y_carriage_left | left X switch screw 0 (M3 x 8 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_left | left X switch screw 1 (M3 x 8 socket head) | 1 meat round the insert hole (s 5.0..8.5, 3.5 mm) | inf mm | >= 3.0 mm | PASS |  |
| y_carriage_left | left X switch screw 1 (M3 x 8 socket head) | 1 insert boss diameter (material OD round the insert) | 10.5 mm (wall 1.5) | >= 6.9 (1.5 x OD 4.6); 9 preferred | PASS |  |
| y_carriage_left | left X switch screw 1 (M3 x 8 socket head) | 1 insert hole depth | 6.5 mm | >= 6.7 (insert 5.7 + 1) | PASS |  |
| y_carriage_left | left X switch screw 1 (M3 x 8 socket head) | 2 thread in the insert | 5.6 mm (insert 5.7 mm long) | >= 4.5 mm (1.5 d) | PASS |  |
| y_carriage_left | left X switch screw 1 (M3 x 8 socket head) | 2 tip does not bottom out past the insert | tip +0.8 mm past the insert | free hole past the insert | PASS |  |
| y_carriage_left | left X switch screw 1 (M3 x 8 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 22 (M3 x 10 socket head) | 1 meat round the thread hole (s 2.5..10.5, 8.0 mm) | 3.6 mm at s 3.5 | >= 3.0 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 22 (M3 x 10 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 22 (M3 x 10 socket head) | 2 self-tap thread length (geometry) | 7.0 mm; joint data: 8.0 mm past the grip, pilot 9.0 | >= 6.0 mm (2 d) | PASS |  |
| y_carriage_left | left Y chain moving end screw 22 (M3 x 10 socket head) | 2 tip does not bottom out | pilot free 2.0 mm past the tip | >= 0.5 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 22 (M3 x 10 socket head) | 6/7 thread pull-out (along the layers) at 0.30 N m | capacity 1060 N vs preload 333 N, SF 3.2 | SF >= 2 (preload) | PASS |  |
| y_carriage_left | left Y chain moving end screw 22 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 30 (M3 x 10 socket head) | 1 meat round the thread hole (s 2.5..10.5, 8.0 mm) | 3.6 mm at s 3.5 | >= 3.0 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 30 (M3 x 10 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 30 (M3 x 10 socket head) | 2 self-tap thread length (geometry) | 7.0 mm; joint data: 8.0 mm past the grip, pilot 9.0 | >= 6.0 mm (2 d) | PASS |  |
| y_carriage_left | left Y chain moving end screw 30 (M3 x 10 socket head) | 2 tip does not bottom out | pilot free 2.0 mm past the tip | >= 0.5 mm | PASS |  |
| y_carriage_left | left Y chain moving end screw 30 (M3 x 10 socket head) | 6/7 thread pull-out (along the layers) at 0.30 N m | capacity 1060 N vs preload 333 N, SF 3.2 | SF >= 2 (preload) | PASS |  |
| y_carriage_left | left Y chain moving end screw 30 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 1 meat round the axle hole (s 0.5..12.0, 11.5 mm) | 5.3 mm at s 6.0 | >= 5.0 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 2 screw past the M5 nyloc nut | 1.8 mm | >= 1.6 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 5 axle supports (cantilever) | one support, boss 11.5 mm, lever 11.1 mm | boss >= 10 mm (2 d) | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 66 MPa, SF 9.7 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 7 PLA bearing, loose joint model (38 N at 11.1 mm) | 4.5 MPa, SF 11.2 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 7 clamped stack does not open under the moment | moment 4.7 MPa vs preload 21.9 MPa | moment <= preload / 2 | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.3 MPa on 5.3 mm, SF 80.6 | SF >= 3 on 25 MPa | PASS |  |
| y_carriage_left | left Y wheel bolt 11 (M5 x 35 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 1 meat round the insert hole (s 16.5..28.5, 12.0 mm) | 8.7 mm at s 18.0 | >= 5.0 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 1 insert hole depth | 15.5 mm | >= 10.5 (insert 9.5 + 1) | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 2 thread in the insert | 9.5 mm (insert 9.5 mm long) | >= 7.5 mm (1.5 d) | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 2 tip does not bottom out past the insert | tip +1.9 mm past the insert | free hole past the insert | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 5 axle supports (cantilever) | one support, boss 12.0 mm, lever 11.4 mm | boss >= 10 mm (2 d) | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 68 MPa, SF 9.5 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 7 PLA bearing, loose joint model (38 N at 11.4 mm) | 4.2 MPa, SF 11.8 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 7 clamped stack does not open under the moment | moment 4.8 MPa vs preload 21.9 MPa | moment <= preload / 2 | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.1 MPa on 19.8 mm, SF 314.3 | SF >= 3 on 25 MPa | PASS |  |
| y_carriage_left | left Y wheel bolt 3 (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 1 meat round the axle hole (s 16.5..28.5, 12.0 mm) | 5.2 mm at s 22.5 | >= 5.0 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 2 screw past the M5 nyloc nut | 1.8 mm | >= 1.6 mm | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 5 axle supports (cantilever) | one support, boss 12.0 mm, lever 11.4 mm | boss >= 10 mm (2 d) | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 68 MPa, SF 9.5 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 7 PLA bearing, loose joint model (38 N at 11.4 mm) | 4.2 MPa, SF 11.8 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 7 PLA face under the clamped stack (14.3 mm, preload 1200 N) | 10.3 MPa (8.8 preload + 1.5 moment), SF 4.8 | SF >= 3 on 50 MPa | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 7 clamped stack does not open under the moment | moment 1.5 MPa vs preload 8.8 MPa | moment <= preload / 2 | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.3 MPa on 5.2 mm, SF 83.2 | SF >= 3 on 25 MPa | PASS |  |
| y_carriage_left | left Y wheel bolt 7 (M5 x 35 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_left | left beam screw (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.0, 5.5 mm) | 5.1 mm at s 4.5 | >= 5.0 mm | PASS |  |
| y_carriage_left | left beam screw (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_carriage_left | left beam screw (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_carriage_left | left beam screw (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_carriage_left | left beam screw (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_left | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_carriage_left | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_carriage_left | y_carriage: M3 X endstop board screw into a heat-set insert | 2 model.py length check (cross-check) | 6.4 mm of thread in a 5.7 mm heat-set insert | model.py rule | PASS |  |
| y_carriage_left | y_carriage: M3 into the X motor | 2 model.py length check (cross-check) | 4.3 mm of thread in a 4.5 mm thread (at least 2.5) | model.py rule | PASS |  |
| y_carriage_left | y_carriage: M5 eccentric wheel axle (head under the wheel), nyloc nut on the 6 mm boss | 2 model.py length check (cross-check) | stands 1.8 mm out of the nut (at least 1) | model.py rule | PASS |  |
| y_carriage_left | y_carriage: M5 front wheel axle (head under the wheel) into a heat-set insert in the plate | 2 model.py length check (cross-check) | 11.3 mm of thread in a 9.5 mm heat-set insert | model.py rule | PASS |  |
| y_carriage_left | y_carriage: M5 into a T-nut | 2 model.py length check (cross-check) | 4.0 mm in the T-nut, tip 6.0 mm into the slot (slot depth 6.3) | model.py rule | PASS |  |
| y_carriage_right | FEA | 8 max von Mises away from the fixtures | 9.2 MPa, SF 5.4 | SF >= 3 on 50 MPa | PASS |  |
| y_carriage_right | FEA | 8 max principal stress vs the layer strength | 8.5 MPa at /n.z/ 0.97, SF 3.0 | SF >= 3 on 26 MPa | PASS |  |
| y_carriage_right | FEA probe: beam end | 8 deflection at the probe, operating loads (inertia, pen drag) | 0.56 um (worst case 54 um) | <= 50 um | PASS |  |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 2 screw past the M3 nut | 5.1 mm | >= 0.5 mm | PASS |  |
| y_carriage_right | X tension screw (M3 x 20 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_carriage_right | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 1 meat round the axle hole (s 0.5..12.0, 11.5 mm) | 5.3 mm at s 6.0 | >= 5.0 mm | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 2 screw past the M5 nyloc nut | 1.8 mm | >= 1.6 mm | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 5 axle supports (cantilever) | one support, boss 11.5 mm, lever 11.1 mm | boss >= 10 mm (2 d) | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 66 MPa, SF 9.7 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 7 PLA bearing, loose joint model (38 N at 11.1 mm) | 4.5 MPa, SF 11.2 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 7 clamped stack does not open under the moment | moment 4.7 MPa vs preload 21.9 MPa | moment <= preload / 2 | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.3 MPa on 5.3 mm, SF 80.6 | SF >= 3 on 25 MPa | PASS |  |
| y_carriage_right | right Y wheel bolt 11 (M5 x 35 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 1 meat round the insert hole (s 16.5..28.5, 12.0 mm) | 8.7 mm at s 18.0 | >= 5.0 mm | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 1 insert hole depth | 15.5 mm | >= 10.5 (insert 9.5 + 1) | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 2 thread in the insert | 9.5 mm (insert 9.5 mm long) | >= 7.5 mm (1.5 d) | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 2 tip does not bottom out past the insert | tip +1.9 mm past the insert | free hole past the insert | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 5 axle supports (cantilever) | one support, boss 12.0 mm, lever 11.4 mm | boss >= 10 mm (2 d) | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 68 MPa, SF 9.5 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 7 PLA bearing, loose joint model (38 N at 11.4 mm) | 4.2 MPa, SF 11.8 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 7 clamped stack does not open under the moment | moment 4.8 MPa vs preload 21.9 MPa | moment <= preload / 2 | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.1 MPa on 19.8 mm, SF 314.3 | SF >= 3 on 25 MPa | PASS |  |
| y_carriage_right | right Y wheel bolt 3 (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 1 meat round the axle hole (s 16.5..28.5, 12.0 mm) | 5.2 mm at s 22.5 | >= 5.0 mm | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 2 screw past the M5 nyloc nut | 1.8 mm | >= 1.6 mm | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 5 axle supports (cantilever) | one support, boss 12.0 mm, lever 11.4 mm | boss >= 10 mm (2 d) | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 7 axle bending (38 N, wheel load (preload + weight + push)) | 68 MPa, SF 9.5 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 7 PLA bearing, loose joint model (38 N at 11.4 mm) | 4.2 MPa, SF 11.8 | SF >= 3 on 50 MPa (WARN only) | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 7 PLA face under the clamped stack (14.3 mm, preload 1200 N) | 10.3 MPa (8.8 preload + 1.5 moment), SF 4.8 | SF >= 3 on 50 MPa | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 7 clamped stack does not open under the moment | moment 1.5 MPa vs preload 8.8 MPa | moment <= preload / 2 | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 6 tear-out toward the load (Z layers, /F.z/ 1.00) | 0.3 MPa on 5.3 mm, SF 83.3 | SF >= 3 on 25 MPa | PASS |  |
| y_carriage_right | right Y wheel bolt 7 (M5 x 35 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_right | right beam screw (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.0, 5.5 mm) | 5.1 mm at s 4.5 | >= 5.0 mm | PASS |  |
| y_carriage_right | right beam screw (M5 x 12 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_carriage_right | right beam screw (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_carriage_right | right beam screw (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_carriage_right | right beam screw (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_carriage_right | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_carriage_right | y_carriage: M3 X belt tension screw through the end wall into the nut in the fork (fork at the slack end) | 2 model.py length check (cross-check) | stands 2.6 mm out of the nut (at least 1) | model.py rule | PASS |  |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 3 flat seat under the socket head (8.5 mm) | 94 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 3 counterbore round the head (gap each side) | 0.25 mm | >= 0.25 mm (FDM holes print small) | PASS |  |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_chain_anchor | Y chain anchor screw y 492 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 494 (M3 x 10 socket head) | 1 meat round the thread hole (s 2.5..10.5, 8.0 mm) | 3.6 mm at s 3.5 | >= 3.0 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 494 (M3 x 10 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 494 (M3 x 10 socket head) | 2 self-tap thread length (geometry) | 7.0 mm; joint data: 8.0 mm past the grip, pilot 9.0 | >= 6.0 mm (2 d) | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 494 (M3 x 10 socket head) | 2 tip does not bottom out | pilot free 2.0 mm past the tip | >= 0.5 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 494 (M3 x 10 socket head) | 6/7 thread pull-out (along the layers) at 0.30 N m | capacity 1060 N vs preload 333 N, SF 3.2 | SF >= 2 (preload) | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 494 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 502 (M3 x 10 socket head) | 1 meat round the thread hole (s 2.5..10.5, 8.0 mm) | 3.6 mm at s 3.5 | >= 3.0 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 502 (M3 x 10 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 502 (M3 x 10 socket head) | 2 self-tap thread length (geometry) | 7.0 mm; joint data: 8.0 mm past the grip, pilot 9.0 | >= 6.0 mm (2 d) | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 502 (M3 x 10 socket head) | 2 tip does not bottom out | pilot free 2.0 mm past the tip | >= 0.5 mm | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 502 (M3 x 10 socket head) | 6/7 thread pull-out (along the layers) at 0.30 N m | capacity 1060 N vs preload 333 N, SF 3.2 | SF >= 2 (preload) | PASS |  |
| y_chain_anchor | Y chain fixed end screw y 502 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_chain_anchor | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_chain_anchor | print orientation | 6 print +Z read from the STL | frame -Y (stl/y_chain_anchor.stl, fit 0.29 mm) | fit < 0.5 mm | PASS |  |
| y_chain_anchor | y_chain: M3 through an end link into the anchor or the carriage tab | 2 model.py length check (cross-check) | 8.0 mm of thread in a 9.0 mm pilot (at least 6) | model.py rule | PASS |  |
| y_chain_anchor | y_chain_anchor: M5 into a T-nut | 2 model.py length check (cross-check) | 4.0 mm in the T-nut, tip 6.0 mm into the slot (slot depth 6.3) | model.py rule | PASS |  |
| y_front_left | left Y front base screw x 12 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 7.3 mm at s 5.0 | >= 5.0 mm | PASS |  |
| y_front_left | left Y front base screw x 12 (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_front_left | left Y front base screw x 12 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_front_left | left Y front base screw x 12 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_front_left | left Y front base screw x 12 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_front_left | left Y front base screw x 44 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 5.3 mm at s 1.5 | >= 5.0 mm | PASS |  |
| y_front_left | left Y front base screw x 44 (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_front_left | left Y front base screw x 44 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_front_left | left Y front base screw x 44 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_front_left | left Y front base screw x 44 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_front_left | left Y switch screw 0 (M3 x 8 socket head) | 1 meat round the insert hole (s 2.0..8.5, 6.5 mm) | inf mm | >= 3.0 mm | PASS |  |
| y_front_left | left Y switch screw 0 (M3 x 8 socket head) | 1 insert hole depth | 7.0 mm | >= 6.7 (insert 5.7 + 1) | PASS |  |
| y_front_left | left Y switch screw 0 (M3 x 8 socket head) | 2 thread in the insert | 5.7 mm (insert 5.7 mm long) | >= 4.5 mm (1.5 d) | PASS |  |
| y_front_left | left Y switch screw 0 (M3 x 8 socket head) | 2 tip does not bottom out past the insert | tip +0.7 mm past the insert | free hole past the insert | PASS |  |
| y_front_left | left Y switch screw 0 (M3 x 8 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_front_left | left Y switch screw 1 (M3 x 8 socket head) | 1 meat round the insert hole (s 2.0..8.5, 6.5 mm) | inf mm | >= 3.0 mm | PASS |  |
| y_front_left | left Y switch screw 1 (M3 x 8 socket head) | 1 insert hole depth | 7.0 mm | >= 6.7 (insert 5.7 + 1) | PASS |  |
| y_front_left | left Y switch screw 1 (M3 x 8 socket head) | 2 thread in the insert | 5.7 mm (insert 5.7 mm long) | >= 4.5 mm (1.5 d) | PASS |  |
| y_front_left | left Y switch screw 1 (M3 x 8 socket head) | 2 tip does not bottom out past the insert | tip +0.7 mm past the insert | free hole past the insert | PASS |  |
| y_front_left | left Y switch screw 1 (M3 x 8 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_front_left | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_front_left | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_front_left.stl, fit 0.27 mm) | fit < 0.5 mm | PASS |  |
| y_front_left | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_front_left | y_front: M3 endstop board screw into a heat-set insert | 2 model.py length check (cross-check) | 6.4 mm of thread in a 5.7 mm heat-set insert | model.py rule | PASS |  |
| y_front_left | y_front: M5 into a T-nut | 2 model.py length check (cross-check) | 4.0 mm in the T-nut, tip 6.0 mm into the slot (slot depth 6.3) | model.py rule | PASS |  |
| y_front_right | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_front_right | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_front_right.stl, fit 0.27 mm) | fit < 0.5 mm | PASS |  |
| y_front_right | right Y front base screw x 12 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 7.3 mm at s 2.0 | >= 5.0 mm | PASS |  |
| y_front_right | right Y front base screw x 12 (M5 x 12 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_front_right | right Y front base screw x 12 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_front_right | right Y front base screw x 12 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_front_right | right Y front base screw x 12 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_front_right | right Y front base screw x 44 (M5 x 12 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 5.3 mm at s 1.5 | >= 5.0 mm | PASS |  |
| y_front_right | right Y front base screw x 44 (M5 x 12 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_front_right | right Y front base screw x 44 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_front_right | right Y front base screw x 44 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_front_right | right Y front base screw x 44 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_front_right | right Y switch screw 0 (M3 x 8 socket head) | 1 meat round the insert hole (s 2.0..8.5, 6.5 mm) | inf mm | >= 3.0 mm | PASS |  |
| y_front_right | right Y switch screw 0 (M3 x 8 socket head) | 1 insert hole depth | 7.0 mm | >= 6.7 (insert 5.7 + 1) | PASS |  |
| y_front_right | right Y switch screw 0 (M3 x 8 socket head) | 2 thread in the insert | 5.7 mm (insert 5.7 mm long) | >= 4.5 mm (1.5 d) | PASS |  |
| y_front_right | right Y switch screw 0 (M3 x 8 socket head) | 2 tip does not bottom out past the insert | tip +0.7 mm past the insert | free hole past the insert | PASS |  |
| y_front_right | right Y switch screw 0 (M3 x 8 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_front_right | right Y switch screw 1 (M3 x 8 socket head) | 1 meat round the insert hole (s 2.0..8.5, 6.5 mm) | inf mm | >= 3.0 mm | PASS |  |
| y_front_right | right Y switch screw 1 (M3 x 8 socket head) | 1 insert hole depth | 7.0 mm | >= 6.7 (insert 5.7 + 1) | PASS |  |
| y_front_right | right Y switch screw 1 (M3 x 8 socket head) | 2 thread in the insert | 5.7 mm (insert 5.7 mm long) | >= 4.5 mm (1.5 d) | PASS |  |
| y_front_right | right Y switch screw 1 (M3 x 8 socket head) | 2 tip does not bottom out past the insert | tip +0.7 mm past the insert | free hole past the insert | PASS |  |
| y_front_right | right Y switch screw 1 (M3 x 8 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_front_right | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_idler_bracket_left | left Y bracket screw 0 (M3 x 12 socket head) | 1 meat round the thread hole (s 4.5..12.5, 8.0 mm) | 3.0 mm at s 5.5 | >= 3.0 mm | PASS |  |
| y_idler_bracket_left | left Y bracket screw 0 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| y_idler_bracket_left | left Y bracket screw 0 (M3 x 12 socket head) | 2 self-tap thread length (geometry) | 7.0 mm; joint data: 8.0 mm past the grip, pilot 9.0 | >= 6.0 mm (2 d) | PASS |  |
| y_idler_bracket_left | left Y bracket screw 0 (M3 x 12 socket head) | 2 tip does not bottom out | pilot free 1.5 mm past the tip | >= 0.5 mm | PASS |  |
| y_idler_bracket_left | left Y bracket screw 0 (M3 x 12 socket head) | 6/7 thread pull-out (along the layers) at 0.30 N m | capacity 1060 N vs preload 333 N, SF 3.2 | SF >= 2 (preload) | PASS |  |
| y_idler_bracket_left | left Y bracket screw 0 (M3 x 12 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_idler_bracket_left | left Y tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 0.0..5.0, 5.0 mm) | 9.6 mm at s 1.0 | >= 3.0 mm | PASS |  |
| y_idler_bracket_left | left Y tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_idler_bracket_left | left Y tension screw (M3 x 20 socket head) | 3 flat seat under the socket head (5.5 mm) | 100 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_idler_bracket_left | left Y tension screw (M3 x 20 socket head) | 2 screw past the M3 nut | 5.1 mm | >= 0.5 mm | PASS |  |
| y_idler_bracket_left | left Y tension screw (M3 x 20 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_idler_bracket_left | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_idler_bracket_left | print orientation | 6 print +Z read from the STL | frame +Y (stl/y_idler_bracket_left.stl, fit 0.29 mm) | fit < 0.5 mm | PASS |  |
| y_idler_bracket_left | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_idler_bracket_left | y_idler_bracket: M3 tension screw through the end wall into the nut of the fork (fork at the back end) | 2 model.py length check (cross-check) | stands 2.1 mm out of the nut (at least 1) | model.py rule | PASS |  |
| y_idler_bracket_left | y_idler_bracket: M3 through a lip of the front base into the bracket | 2 model.py length check (cross-check) | 8.0 mm of thread in a 9.0 mm pilot (at least 6) | model.py rule | PASS |  |
| y_idler_bracket_right | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_idler_bracket_right | print orientation | 6 print +Z read from the STL | frame +Y (stl/y_idler_bracket_right.stl, fit 0.29 mm) | fit < 0.5 mm | PASS |  |
| y_idler_bracket_right | right Y bracket screw 0 (M3 x 12 socket head) | 1 meat round the thread hole (s 4.5..12.5, 8.0 mm) | 3.0 mm at s 5.5 | >= 3.0 mm | PASS |  |
| y_idler_bracket_right | right Y bracket screw 0 (M3 x 12 socket head) | 9 pilot hole diameter (self-tapping) | 2.80 mm | 2.34..2.85 mm | PASS |  |
| y_idler_bracket_right | right Y bracket screw 0 (M3 x 12 socket head) | 2 self-tap thread length (geometry) | 7.0 mm; joint data: 8.0 mm past the grip, pilot 9.0 | >= 6.0 mm (2 d) | PASS |  |
| y_idler_bracket_right | right Y bracket screw 0 (M3 x 12 socket head) | 2 tip does not bottom out | pilot free 1.5 mm past the tip | >= 0.5 mm | PASS |  |
| y_idler_bracket_right | right Y bracket screw 0 (M3 x 12 socket head) | 6/7 thread pull-out (along the layers) at 0.30 N m | capacity 1060 N vs preload 333 N, SF 3.2 | SF >= 2 (preload) | PASS |  |
| y_idler_bracket_right | right Y bracket screw 0 (M3 x 12 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_idler_bracket_right | right Y tension screw (M3 x 20 socket head) | 1 meat round the clearance hole (s 0.0..5.0, 5.0 mm) | 9.6 mm at s 1.0 | >= 3.0 mm | PASS |  |
| y_idler_bracket_right | right Y tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_idler_bracket_right | right Y tension screw (M3 x 20 socket head) | 3 flat seat under the socket head (5.5 mm) | 100 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_idler_bracket_right | right Y tension screw (M3 x 20 socket head) | 2 screw past the M3 nut | 5.1 mm | >= 0.5 mm | PASS |  |
| y_idler_bracket_right | right Y tension screw (M3 x 20 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_idler_bracket_right | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_idler_fork_left | FEA | 8 max von Mises away from the fixtures | 7.4 MPa, SF 6.7 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_left | FEA | 8 max principal stress vs the layer strength | 6.1 MPa at /n.z/ 0.94, SF 4.3 | SF >= 3 on 26 MPa | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 0.0..5.0, 5.0 mm) | 5.2 mm at s 1.0 | >= 5.0 mm | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 15.5..23.5, 8.0 mm) | 5.2 mm at s 16.5 | >= 5.0 mm | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 3 flat seat under the socket head (8.5 mm) | 95 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 5 axle supports | two supports (y_idler_fork_left / y_idler_fork_left), span 17.0 mm | 2 or a boss >= 2 d | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 7 axle bending (143 N, 2 x t_max (180 deg wrap, both runs to the motor)) | 95 MPa, SF 6.8 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (78 N) | 3.1 MPa, SF 16.1 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 1.4 MPa on 5.5 mm, SF 35.4 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (65 N) | 1.6 MPa, SF 30.7 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 0.7 MPa on 5.5 mm, SF 67.6 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_left | left Y idler axle (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_idler_fork_left | left Y idler axle: M5 washer, 7.5 mm across (small) | 9 washer touches only the inner race of the idler | washer OD 7.5 mm | <= 8.7 mm (625 inner race, ESTIMATE) | PASS |  |
| y_idler_fork_left | left Y tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_idler_fork_left | left Y tension screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |  |
| y_idler_fork_left | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_idler_fork_left | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_idler_fork.stl, fit 0.20 mm) | fit < 0.5 mm | PASS |  |
| y_idler_fork_left | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_idler_fork_left | y_idler_fork: M5 Y idler axle through both cheeks (2 washers), nyloc nut | 2 model.py length check (cross-check) | stands 1.5 mm out of the nut (at least 1) | model.py rule | PASS |  |
| y_idler_fork_right | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_idler_fork_right | print orientation | 6 print +Z read from the STL | frame +Z (stl/y_idler_fork.stl, fit 0.20 mm) | fit < 0.5 mm | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 0.5..5.5, 5.0 mm) | 5.2 mm at s 4.0 | >= 5.0 mm | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 1 meat round the axle hole (s 16.0..24.0, 8.0 mm) | 5.2 mm at s 22.5 | >= 5.0 mm | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 5 axle supports | two supports (y_idler_fork_right / y_idler_fork_right), span 17.0 mm | 2 or a boss >= 2 d | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 7 axle bending (143 N, 2 x t_max (180 deg wrap, both runs to the motor)) | 93 MPa, SF 6.9 | SF >= 3 on 640 MPa (class 8.8) | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (82 N) | 3.3 MPa, SF 15.3 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 1.5 MPa on 5.5 mm, SF 33.6 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 7 PLA bearing at the axle hole (61 N) | 1.5 MPa, SF 32.8 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 6 tear-out toward the load (XY layers, /F.z/ 0.00) | 0.7 MPa on 5.5 mm, SF 72.2 | SF >= 3 on 50 MPa | PASS |  |
| y_idler_fork_right | right Y idler axle (M5 x 30 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_idler_fork_right | right Y idler axle: M5 washer, 7.5 mm across (small) | 9 washer touches only the inner race of the idler | washer OD 7.5 mm | <= 8.7 mm (625 inner race, ESTIMATE) | PASS |  |
| y_idler_fork_right | right Y tension screw (M3 x 20 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_idler_fork_right | right Y tension screw: M3 nut | 3 nut in a nut trap | captured | - | PASS |  |
| y_idler_fork_right | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_motor_mount_left | FEA | 8 max von Mises away from the fixtures | 2.0 MPa, SF 24.6 | SF >= 3 on 50 MPa | PASS |  |
| y_motor_mount_left | FEA | 8 max principal stress vs the layer strength | 1.5 MPa at /n.z/ 0.43, SF 27.2 | SF >= 3 on 40 MPa | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 46 (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 46 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 46 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 46 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 59 (M5 x 12 socket head) | 9 clearance hole diameter | 5.40 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 59 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 59 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_motor_mount_left | left Y motor bracket screw x 59 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_motor_mount_left | left Y motor screw +16 +16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 5.0 mm at s 5.0 | >= 3.0 mm | PASS |  |
| y_motor_mount_left | left Y motor screw +16 +16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_left | left Y motor screw +16 +16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_left | left Y motor screw +16 +16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_left | left Y motor screw +16 +16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_motor_mount_left | left Y motor screw +16 -16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 5.0 mm at s 5.0 | >= 3.0 mm | PASS |  |
| y_motor_mount_left | left Y motor screw +16 -16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_left | left Y motor screw +16 -16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_left | left Y motor screw +16 -16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_left | left Y motor screw +16 -16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_motor_mount_left | left Y motor screw -16 +16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 5.0 mm at s 5.0 | >= 3.0 mm | PASS |  |
| y_motor_mount_left | left Y motor screw -16 +16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_left | left Y motor screw -16 +16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_left | left Y motor screw -16 +16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_left | left Y motor screw -16 +16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_motor_mount_left | left Y motor screw -16 -16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.5..6.5, 6.0 mm) | 3.8 mm at s 1.5 | >= 3.0 mm | PASS |  |
| y_motor_mount_left | left Y motor screw -16 -16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_left | left Y motor screw -16 -16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_left | left Y motor screw -16 -16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_left | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_motor_mount_left | print orientation | 6 print +Z read from the STL | frame +X (stl/y_motor_mount_left.stl, fit 0.33 mm) | fit < 0.5 mm | PASS |  |
| y_motor_mount_left | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |
| y_motor_mount_left | y_motor_mount: M3 into the Y motor | 2 model.py length check (cross-check) | 4.0 mm of thread in a 4.5 mm thread (at least 2.5) | model.py rule | PASS |  |
| y_motor_mount_left | y_motor_mount: M5 into a T-nut | 2 model.py length check (cross-check) | 4.0 mm in the T-nut, tip 6.0 mm into the slot (slot depth 6.3) | model.py rule | PASS |  |
| y_motor_mount_right | part solid | 0 the solid is valid (OCC check) | valid | valid | PASS |  |
| y_motor_mount_right | print orientation | 6 print +Z read from the STL | frame -X (stl/y_motor_mount_right.stl, fit 0.33 mm) | fit < 0.5 mm | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 46 (M5 x 12 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 46 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 46 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 46 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 59 (M5 x 12 socket head) | 9 clearance hole diameter | 5.39 mm | 5.2..6.2 (ISO 273 5.5) | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 59 (M5 x 12 socket head) | 2 screw through the full T-nut thread | 4.0 of 4.0 mm | 4.0 mm | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 59 (M5 x 12 socket head) | 2 tip clear of the slot bottom | tip 6.0 mm in | <= 6.3 mm (ESTIMATE) | PASS |  |
| y_motor_mount_right | right Y motor bracket screw x 59 (M5 x 12 socket head) | 4 straight socket head key line from the head | 70 mm | >= 70 mm | PASS |  |
| y_motor_mount_right | right Y motor screw +16 +16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 5.0 mm at s 1.0 | >= 3.0 mm | PASS |  |
| y_motor_mount_right | right Y motor screw +16 +16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_right | right Y motor screw +16 +16 (M3 x 10 socket head) | 3 flat seat under the socket head (5.5 mm) | 100 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_motor_mount_right | right Y motor screw +16 +16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_right | right Y motor screw +16 +16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_right | right Y motor screw +16 +16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_motor_mount_right | right Y motor screw +16 -16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 5.0 mm at s 1.0 | >= 3.0 mm | PASS |  |
| y_motor_mount_right | right Y motor screw +16 -16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_right | right Y motor screw +16 -16 (M3 x 10 socket head) | 3 flat seat under the socket head (5.5 mm) | 100 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_motor_mount_right | right Y motor screw +16 -16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_right | right Y motor screw +16 -16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_right | right Y motor screw +16 -16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_motor_mount_right | right Y motor screw -16 +16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 5.0 mm at s 1.0 | >= 3.0 mm | PASS |  |
| y_motor_mount_right | right Y motor screw -16 +16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_right | right Y motor screw -16 +16 (M3 x 10 socket head) | 3 flat seat under the socket head (5.5 mm) | 100 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_motor_mount_right | right Y motor screw -16 +16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_right | right Y motor screw -16 +16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_right | right Y motor screw -16 +16 (M3 x 10 socket head) | 4 straight socket head key line from the head | 60 mm | >= 60 mm | PASS |  |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 1 meat round the clearance hole (s 0.0..6.0, 6.0 mm) | 3.8 mm at s 1.0 | >= 3.0 mm | PASS |  |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 9 clearance hole diameter | 3.40 mm | 3.2..4.2 (ISO 273 3.4) | PASS |  |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 3 flat seat under the socket head (5.5 mm) | 100 % bears, 0 % above the seat | >= 90 %, 0 % above | PASS |  |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 3 counterbore round the head (gap each side) | 1.00 mm | >= 0.25 mm (FDM holes print small) | PASS |  |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 2 thread in the metal part | 4.0 mm of 4.5 | 2.5..4.5 mm | PASS |  |
| y_motor_mount_right | right Y motor screw -16 -16 (M3 x 10 socket head) | 7 motor screw bearing on the PLA (40 N: 2 x t_max toward the Y idler (180 deg wrap) / 4 + torque) | 2.2 MPa, SF 22.3 | SF >= 3 | PASS |  |
| y_motor_mount_right | slicer profile | 6 solid ring round holes (walls) / infill | 2.5 mm walls, 40 % infill | >= 2.0 mm walls or >= 40 % infill on loaded parts | PASS |  |

</details>
