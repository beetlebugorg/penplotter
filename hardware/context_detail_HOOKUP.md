# Hookup notes: the detailed bought parts

`context_detail.py` has detailed models of the bought parts. `export_context_detail.py` exports them.
This page tells the owner of `parts.py`, `model.py` and `make.sh` how to wire them in.

## What exists now

- `context_detail.py` returns a "kit" for each part: `{material: [solid, ...]}` in frame coordinates.
  `CD.kit_solid(kit)` joins a kit into one `Compound`. `CD.MATS` gives the colour of each material.
- `export_context_detail.py` writes:
  - `stl/detail/<group>_<material>.stl` and `stl/detail/manifest.json`. The sim reads them through
    `sim/web/wiring.js`. They are outside `stl/sim2`, so `make.sh` does not delete them.
  - `stl/sim2/<name>.stl` for the names in the table below: one-colour meshes with the stand-in names.
  - A clearance check against the printed parts and a trigger check for each endstop lever.
- The sim hides each sim2 mesh that the manifest names in `replaces`, so the two never show together.

## Wire it into make.sh

`model.py` deletes and rewrites `stl/sim2`. Do one of these:

1. Simple: add one line to `make.sh` after `model.py`:
   `uv run --no-project --with build123d python export_context_detail.py`
2. Or replace the stand-ins in the sim2 list of `model.py` (`items = [...]`, about line 1037):

| sim2 name | Stand-in today | Replace with (`import context_detail as CD`) | Group |
|---|---|---|---|
| `x_motor` | `P.x_motor(c0)` (box and pulley) | `CD.kit_solid(CD.x_motor(c0)[0])` plus the pulley part of `P.x_motor(c0)` | gantry |
| `y_stepper_left` | `P.y_stepper(c0)[0]` | `CD.kit_solid(CD.y_stepper_left(c0)[0])` | gantry |
| `y_stepper_right` | `P.mirror_x(P.y_stepper(c0)[0])` | `CD.kit_solid(CD.y_stepper_right(c0)[0])` | gantry |
| `y_endstops` | the two Y boards of `P.es_parts` | `CD.kit_solid(CD.merge(CD.y_endstop_left(c0)[0], CD.y_endstop_right(c0)[0]))` | static |
| `x_endstop` (new name) | the X board of `P.es_parts` | `CD.kit_solid(CD.x_endstop(c0, xp0)[0])` | gantry |
| `head_board` | the board items of `board_world("head", c0)` | `CD.kit_solid(CD.board("head", c0)[0])` | gantry |
| `base_board` | the board items of `board_world("base")` | `CD.kit_solid(CD.board("base")[0])` | static |
| `servo` | `t * P.servo_body()` | `CD.kit_solid(CD.servo(t)[0])` | carriage |
| `horn` | `t * P.horn(S.PEN_DOWN_DEG)` | no change: keep it, the pen-lift geometry depends on it | carriage |
| `pen` | `t * P.pen(...)` | no change | pen |
| (images) `t_ctrl_box`, `t_ctrl_lcd`, `t_ctrl_knob` | three boxes in `model.py` | `CD.ctrl_box()[0]`: one mesh for each material | — |

Run `export_context_detail.py` after `model.py` in either case: the sim reads `stl/detail/manifest.json`.

Keep these stand-ins for the fit check. The detail models are for the views:

- `P.brk_board(kind)`: it has the bend volumes over the used XH plugs and the cable stub.
- `P.servo_body()`: the pocket clearance check uses it. The detail servo is 12.2 mm wide, the stand-in 12.4 mm.

The STEP assembly (`cad/table-plotter-assembly.step`) can take the kits the same way, one child for
each material with `CD.MATS[mat][0]` as the colour.

## The endstop boards

The detail model uses your values and your placements. It reads `S.ES` (the board, the holes, the
switch, the lever, the click point, the plug and the plug zone) and places each board with
`P.es_loc(which, c)`. So it follows each change to the mounts. It adds these values from the photo
and estimates, in `CD.EB`: the switch screws 6.5 mm apart, the plunger at v 10.8, the plug 5.5 mm out
of the plug edge, a 0.4 mm lever strip.

- `CD.endstop(which, c, press)` returns `(kit, cable anchor, sim indicator, named values)`.
  `which` is `"x"`, `"y_left"` or `"y_right"`. The right board is not a mirror image.
- `CD.x_endstop(c0, xp0)`, `CD.y_endstop_left(c0)` and `CD.y_endstop_right(c0)` draw the lever at the
  home pose. `CD.trigger_press(which, c, xp)` finds how far the trigger face is past the click at home.
  Today it is 1.5 mm for all three boards (the overtravel of your design).
- The named values (also in `manifest.json` → `endstops`, frame coordinates): `holes`, `actuate` (the
  click point, `S.ES["click"]`), `actuate_dir` (the push direction, −u of the board), `normal` (the
  board normal), `press_at_home`.
- `endstop_board_local()` → `info["plug_zone"]` is `S.ES["plug_zone"]`. Keep the mounts out of it.
- The board has no LED: the LED, 10K, 1K and C104 pads are empty on the measured board. The sim lights
  the red plunger of the switch when the switch triggers.
- Keep `P.es_parts` for the fit check. Use `CD.kit_solid(CD.x_endstop(c0, xp0)[0])` and the two Y
  boards for the images and the sim.

## The cable anchors

`manifest.json` → `anchors` has each plug exit: the point, the direction, and the group
(`static`, `gantry` at `dy0`, `carriage` at `dx0`, `dy0`, `ctrl`). `wiring.js` routes the cables from
these points. If a part moves, the export moves its anchor.

## The static wires: slots, cover strips and the table trunk

`sim/web/wiring.js` routes the wires that do not move like this (frame mm):

| Wire | Route |
|---|---|
| Y1 endstop (3 mm) | It leaves the plug toward the front, goes round the front left corner (x −4) and under the rail, then runs in the **left rail bottom outer slot** (x 10) from y 34 to y 466. It leaves the slot at y 470, before the chain anchor T-nut (y 487–497). It runs on the table under the anchor arm, enters the **back bar bottom slot** (y 510) at x 22, and runs to x 60. It leaves the slot there, goes up beside the left Y motor bracket to the base board (x 71 to 112). |
| Y2 endstop (3 mm) | It goes round the front right corner (x 404) and runs in the **right rail bottom outer slot** (x 390) from y 34 to y 490. Then it crosses to the **back bar bottom slot** at x 384 and runs to x 74. It goes up to the base board as Y1 does. |
| Y1, Y2 stepper cables (4.5 mm) | These cables do not go in a slot: they are static only from the chain fixed end to the base board. They leave the chain along its axis (y 504), run on the table behind the frame at y 527 and 531.5 to x 56, rise at x 64–70 beside the left Y motor bracket, and go to the base board at y 551 and 556. |
| Head harness (9 mm) | It runs on the table: from the chain fixed end to y 545, then to x −100, forward to the box, and into gland 1. |
| Base harness (9 mm) | The plug points to +x. The harness makes a U turn at x 158 (before the pole foot at x 165) and runs on the table at y 556, under the base board, to x −110. Then it goes forward to the box and into gland 0. |

The trunk cables lie on 8 adhesive tie mounts (19 × 19 × 3 mm) with a cable tie each, at
(x, y): (−105, 380), (−105, 470), (−70, 545), (0, 529), (40, 529), (−30, 556), (40, 556), (120, 556).

### Free-slot check

The model's T-nuts (`fasteners.py`, static group) are:

- the front bar top slot: front bases;
- the back bar back face: Y motor brackets, base board (on standoffs, cable ties), pole foot;
- the left rail bottom outer slot: chain anchor, y 487–497.

The feet are under the rail inner bottom slots (x 30 and 370). The V-wheels run in the rail side slots,
and the Y belt runs over the rail inner top slot. The slot sections in use are free of T-nuts, screws
and feet:

- left rail bottom outer slot, y 34–466;
- right rail bottom outer slot, y 34–490;
- back bar bottom slot, x 22–60 and x 74–384.

The chain anchor arm covers the back bar bottom face at x −4 to 15. The cables stay clear of it.

The slot in the sim is the simplified V-slot profile, 4.5 mm deep. A 3 mm cable fits under a 1.5 mm strip
there. The real 2020/2040 slot is about 6.2 mm deep, so it has more room. A 4.5 mm stepper cable fits only in a
2040 slot. No stepper cable runs in a slot in this routing.

### BOM items (for `docs/bom.md`)

| Item | Qty | Note |
|---|---|---|
| Slot cover strip for 2020 V-slot, 6 mm, flexible PVC, black or grey | 2 m pack (uses 1.21 m) | Amazon search "2020 slot cover strip 6mm", about $8–12. Cut lengths: left rail bottom outer slot 428 mm (y 36–464), right rail bottom outer slot 452 mm (y 36–488), back bar bottom slot 29 mm (x 29–58) and 302 mm (x 76–378). Leave the gaps at the cable entries and exits. |
| Adhesive cable tie mounts, 19 × 19 mm | 8 (pack of 50) | On the table under the trunk, at the points above. |
| Cable ties, 2.5 mm | +12 | 8 at the mounts, 2 at the chain end combs, 2 spare (M25 has the pack). |

No printed clip channel is needed: no bundle runs along the outside of a bar.

### The drag chain ends

`wiring.js` draws the end links of the openable chain as brackets: two side walls 12 mm long, the bracket
wall (2 mm, `YCH_LINK_WALL`) with 2 × Ø3.2 holes on the anchor side, a lid bar and a tie comb 8 mm past the
opening.

- The fixed end link is at y 492–504, z 0–15 (centre z 7.5), x −63.5 to −36.5 (the plane at x −50). Its holes are at y 494.5 and 501.5, z 7.5: the two M3 × 10 into the anchor wall (x −36).
- The moving end link is centred on the tab (c + 26), with holes at c + 21.5 and c + 30.5.
- Both open to +y. The cables leave along the chain axis and are tied on the comb.
- The links fill the path from y 492 to 6 mm short of the moving end. There are 26 links at an 18.31 mm pitch (18 mm nominal, ESTIMATE).
- All the parts stay inside the 27 mm outer width. The lower run lies on the table (z 0 to 15).
- With R28 and a 15 mm link, the upper run lies 41 mm over the lower run. The tab holds it at z 63.5 (frame.json), so the upper run does not rest on the lower run.
