# Parts and cost

This chapter lists what to buy, what to print, and what it costs. Prices are approximate and are from
2026-11-07. "est." marks an estimate.

The build keeps the stock CR-10 V3 control box and its harness. The plotter reuses the 9 stock
V-wheels with their spacers and eccentric spacers, the motors, the pulleys and the 4 stock rubber
feet. A printed X plate replaces the stock X carriage plate. The two Y carriages are printed flat
plates. You buy the belts, the toothed idlers, the screws, the T-nuts, the heat-set
inserts, a drag chain, nylon standoffs, a servo and a few cables. The belt jaws are printed. The
1/2 inch split wire loom for the servo lead is on hand.

## Printed parts

All parts print in PLA with 0.3 mm layers on a LulzBot TAZ Workhorse (SE tool head, 0.5 mm
nozzle, 2.85 mm filament). No part needs supports. The values come from CuraEngine slices with the
profiles in `hardware/cura/` (PLA at $19.99/kg). `hardware/stats.py` prints them.

| Part | Count | Print time | Filament | Cost |
|---|---|---|---|---|
| `y_carriage_left` | 1 | 3 h 52 min | 67 g | $1.34 |
| `y_carriage_right` | 1 | 3 h 38 min | 65 g | $1.30 |
| `x_carriage_plate` | 1 | 2 h 45 min | 50 g | $1.00 |
| `pen_carriage` | 1 | 2 h 10 min | 38 g | $0.76 |
| `pen_slider` | 1 | 54 min | 16 g | $0.32 |
| `y_motor_mount_left` | 1 | 1 h 08 min | 19 g | $0.38 |
| `y_motor_mount_right` | 1 | 1 h 08 min | 19 g | $0.38 |
| `y_front_left` | 1 | 42 min | 12 g | $0.24 |
| `y_front_right` | 1 | 42 min | 12 g | $0.24 |
| `y_idler_bracket_left` | 1 | 1 h 16 min | 23 g | $0.46 |
| `y_idler_bracket_right` | 1 | 1 h 16 min | 23 g | $0.46 |
| `y_idler_fork` | 2 | 50 min | 14 g | $0.28 |
| `x_idler_fork` | 1 | 25 min | 7 g | $0.14 |
| `belt_jaw` | 6 | 18 min | 6 g | $0.12 |
| `y_chain_anchor` | 1 | 40 min | 12 g | $0.24 |
| `mast_foot` (optional, the camera pole foot) | 1 | 1 h 23 min | 23 g | $0.46 |
| **Total, 22 parts in 16 print jobs** | | **23 h 08 min** | **406 g** | **$8.12** |
| `fit_rail` | 1 | 10 min | 3 g | $0.06 |
| `fit_slider` | 1 | 22 min | 6 g | $0.12 |
| `fit_wheel` | 1 | 17 min | 5 g | $0.10 |
| **Fit tests, 3 parts (print first)** | | **49 min** | **14 g** | **$0.28** |

The values for `y_idler_fork` are for both copies, and the values for `belt_jaw` are for all 6. The camera is a USB webcam on your own 590 mm
pole. The printed `mast_foot` holds the pole behind the back bar.

Before the simplification of 2026-11-10, the main build printed 27 parts in 30 h 28 min with
544 g of PLA ($10.88). `75-review-history` lists the changes.

## Fasteners

The hardware model has each screw, nut, washer, spacer, T-nut and insert of the
build (`hardware/fasteners.py`). The fit check moves them with the parts over the whole travel.
`hardware/model.py` checks the length of each screw. The M2 and M3 screws in plastic without an
insert cut their own thread. The list below is the model total. `docs/bom.md` has the kits.

| Fastener | Count | Where | BOM line |
|---|---|---|---|
| M5 drop-in T-nut | 15 (buy 17) | Front bases 4, Y motor brackets 4, Y idler brackets 2, beam 2, Y chain anchor 1, pole foot 2 | M22 |
| M5 × 12 socket head | 13 | Front bases 4, Y motor brackets 4, beam 2, Y chain anchor 1, pole foot 2 | M24 |
| M5 × 12 countersunk (ISO 10642) | 2 | Y idler brackets, through the ear into the front bar | M39 |
| M5 × 30 socket head | 5 | Front outer Y wheels 2 (into the inserts), idler fork axles 3 | M24 |
| M5 × 35 socket head | 4 | Back outer Y wheels on the eccentric spacers 2, inner Y wheels 2 | M24 |
| M5 × 25, M5 × 30, M5 × 35 button head (ISO 7380) | 1 each | X wheels: bottom (into the insert), top left, top right (eccentric) | M24 |
| M5 nyloc nut | 9 | Y wheels 4, top X wheels 2, idler forks 3 | M27 |
| M5 washer, small (7.5 mm across) | 6 | Idler forks, one each side of each idler | M27 |
| M5 heat-set insert, long (9.5 mm) | 3 | Front outer Y wheel axles 2, bottom X wheel axle 1 | M34 |
| M3 heat-set insert (5.7 mm) | 12 | Y endstop boards 4 (front bases), X endstop board 2 (left Y carriage), belt jaws 6 (Y carriages 4, X plate 2) | M28 |
| M3 × 8 socket head | 6 | The three endstop boards (all into inserts) | M23 |
| M3 × 10 socket head | 21 | X motor 3, Y motors 8, Y chain end links 4, belt jaws 6 (into inserts) | M23 |
| M3 × 12 socket head | 6 | Pen carriage 4 (T1, T2, H1, H2), front base lip into each Y idler bracket 2 | M23 |
| M3 × 16 socket head | 1 | Pole foot collar | M23 |
| M3 × 20 socket head | 4 | Tension screws 3 (X fork 1, Y forks 2), pen slider clamp 1 | M23 |
| M3 nut | 5 | Idler forks 3, pole foot collar 1, pen slider 1 | M23 |
| M6 × 16 socket head | 1 | The pole end in the pole foot | M26 |
| Nylon M3 standoff, 4 mm | 4 | Two under each breakout board | M38 |

The model also uses these stock parts: 8 M5 × 30 frame screws, 6 plain 6 mm wheel spacers, 3
eccentric spacers, and the 2 M2 × 8 servo screws from the servo bag. Count your plain spacers
first (`hardware/MEASURE.md`, item 62). The build needs 6: 4 on the Y carriages and 2 on the X plate.

The idlers are 3 toothed GT2 20T idlers with a 5 mm bore (M20): one in each Y fork and one in the X
fork. The moving cables need the openable drag chain (M32) and the 1/2 inch split wire loom (M33).

Notes on the screws:

- An M5 × 12 screw through a 6 mm wall puts 4 mm of thread in the T-nut. Its tip goes 6 mm into
  the 6.3 mm slot. The slot depth is an ESTIMATE.
- The M3 heads of the right Y motor bracket bear on PLA. At full torque the pressure is too high.
  Put an M3 washer under each head, or tighten by feel. The left bracket has the same joint.

## Cost summary

| Item | Value |
|---|---|
| Purchased parts | about $190 |
| Printed parts | $8.12 (22 parts) |
| Total before tax | about $198 |

The purchases are the servo about $7, the electronics about $46 and the mechanics about
$137. The pens, the tie mounts (M37), the standoffs (M38), the countersunk screws (M39) and the
camera are not in these totals. The servo loom (M33) is on hand.

## Bill of materials

The sections below come from `docs/bom.md`.

<!-- include: ../bom.md#How to read the prices -->

<!-- include: ../bom.md#Part 1: What to buy (stock controller build) -->

<!-- include: ../bom.md#Mainboard -->

<!-- include: ../bom.md#Stepper motors -->

<!-- include: ../bom.md#Control box power supply -->
