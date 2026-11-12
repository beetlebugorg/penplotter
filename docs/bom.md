# Bill of materials

The table plotter from a dismantled Creality CR-10 V3, after the hardware review (`hardware/REVIEW.md`).
The main build keeps the stock CR-10 V3 control box and its harness. The firmware is written in Go and built with TinyGo.
Prices checked: **2026-11-07**.

## How to read the prices

- The prices are approximate. Check the price and the stock before you buy.
- The links are product searches. Any shop that sells the same part is good.
- "est." means an estimate. The search result did not show a live price.
- The totals use the middle of each price range.

## Part 1: What to buy (stock controller build)

### Electronics

The control box, the mainboard, the drivers, the LCD and the harness come from the CR-10 V3. Buy only these parts:

| # | Item | Qty | Where to find (approx. price) | Notes |
|---|------|-----|-------------------------------|-------|
| S1 | Small servo, 180° (SG90 type) | 1 | [Search: SG90 servo](https://www.amazon.com/s?k=SG90+servo+180), about **$7**. An MG90S also fits ([search: MG90S servo](https://www.amazon.com/s?k=MG90S+servo), est. $9–11 for a 2-pack). | The pen lift. It plugs into `BL_T` on the head board. Not the 360° type. Do not use a large servo: the mainboard 5 V supply feeds it. |
| S2 | Servo extension cable, 70 cm (or make one) | 1 | [Search: servo extension 70cm](https://www.amazon.com/s?k=servo+extension+cable+70cm), est. $6 (pack) | The servo lead runs from `BL_T` of the head board through the servo loom (M33) to the servo on the pen carriage: about 45 cm (ESTIMATE from the model). A 50 or 70 cm extension fits. You can also make it with S3 and S6. |
| S3 | JST-XH (2.50 mm) and Dupont (2.54 mm) crimp kit with a ratcheting crimper | 1 | [Search: JST-XH Dupont crimp kit with ratcheting crimper](https://www.amazon.com/s?k=JST-XH+Dupont+crimp+kit+ratcheting+crimper), about **$30** | Makes S4 and S5. It has XH housings with 2 to 5 pins, 2R to 5R inline male housings, Dupont housings, terminals, and a 0.08–1.0 mm² (AWG 28–17) crimper. Use the S6 wire: the 1 m of ribbon cable in the kit is thin. |
| S6 | Hook-up wire, 24 AWG silicone, 6 colours × 10 ft | 1 | [Search: 24 AWG silicone wire 6 colors 10 ft](https://www.amazon.com/s?k=24+AWG+silicone+wire+6+colors+10ft), about **$10** | For S4 and S5. Black for GND, red for 5 V, one more colour for the signal. 24 AWG silicone fits the XH and Dupont terminals of S3. |
| S4 | JST XH 5-pin pigtail | 1 | Make it with S3. | From `BL_T` to the servo extension. The servo end is a 3-pin Dupont plug from S3. Three wires: GND, 5 V, signal (`docs/wiring.md`). |
| S5 | JST XH 2-pin extension, 50 cm | 0 to 2 | Make it with S3. | A 2P housing on one end and a 2R inline male housing on the other end. Only if a stock endstop cable does not reach the front base of its belt. |

### Mechanics

| # | Item | Qty | Where to find (approx. price) | Notes |
|---|------|-----|--------|-------|
| M18 | GT2 open timing belt: 2 mm pitch, 6 mm wide, glass fibre core, 5 m roll | 1 | [Search: GT2 belt 6mm 5m](https://www.amazon.com/s?k=GT2+timing+belt+6mm+5m), est. $8–10 | 2 Y belts and 1 X belt. Cut each belt about 80 mm longer than its length between the folds (the build guide PDF has the lengths). A printed belt jaw clamps each folded end. Each belt is a loop round a motor pulley and an idler, cut at the carriage. Not GT2-3M, not 9 or 10 mm wide, not a closed loop. The stock belts are too short now. |
| M19 | GT2 20 tooth pulley, 5 mm bore | 1 | [Search: GT2 20 tooth pulley 5 mm bore](https://www.amazon.com/s?k=GT2+20+tooth+pulley+5mm+bore), est. $7 (pack) | The second Y motor. The 2 stock pulleys are reused (X and Y1). 80 steps/mm stays. |
| M20 | GT2 20 tooth idler, **toothed**, 5 mm bore (ball bearings), 6 mm belt | 2 (3 if the stock X idler is not a 20T toothed idler) | [Search: GT2 20 tooth toothed idler 5 mm bore](https://www.amazon.com/s?k=GT2+20+tooth+idler+toothed+5mm+bore), est. $8 (pack) | One for each Y belt, in the fork in front of the front bar. The belt teeth run on it, so it is toothed (the runs stay parallel). The model uses 18 mm flanges and 8.5 mm width (ESTIMATE; `MEASURE.md` item 43). |
| M22 | M5 drop-in T-nuts for 2020/2040 | 17 | [Amazon search: M5 drop in T nut](https://www.amazon.com/s?k=M5+drop+in+T+nut+2020), est. $7 | Y front bases (4), Y motor brackets (4), Y idler brackets (2, in the front face slot of the front bar), the beam (2, one at each end in the back slot), Y chain anchor (1), camera pole foot (2), spare (2). The model has the 15 in use. Packs of 20 are common. |
| M23 | M3 socket head kit (6–30 mm), with nuts | 1 | [Search: M3 socket head screw kit](https://www.amazon.com/s?k=M3+socket+head+screw+kit+with+nuts), est. $14–16 | 21 × M3 × 10 (X motor 3, Y motors 8, Y chain end links 4, the 6 belt jaws into M3 inserts), 6 × M3 × 12 (pen carriage T1, T2, H1 and H2, 1 through the inner lip of each Y front base into its idler bracket), 6 × M3 × 8 (the endstop boards, into M3 inserts), 4 × M3 × 20 (the X and the two Y tension screws with nuts, the pen clamp screw with a nut), 1 × M3 × 16 with a nut (pole collar). |
| M24 | M5 socket head kit, with nuts | 1 | [Amazon search: M5 socket head screw kit](https://www.amazon.com/s?k=M5+socket+head+screw+kit), est. $12 | 13 × M5 × 12 (front bases 4, Y motor brackets 4, beam 2, Y chain anchor 1, pole foot 2), 3 × M5 × 30 (the 3 idler fork axles), 6 × M5 × 35 (outer Y wheels 4: front 2, back on the eccentric spacers 2; inner Y wheels 2), 3 × button head ISO 7380 for the X wheels: 1 × M5 × 30 (top left), 2 × M5 × 35 (top right on the eccentric, bottom). Most kits stop at 30 mm: buy the 35 mm screws separately if needed. |
| M25 | Cable ties, 2.5 mm | 1 pack | Any brand, est. $4 | 2 for each breakout board (4: through the board holes and round the extrusion), 1 at each end of the servo loom (2), the head cable on the beam (about 4), 8 at the M37 tie mounts, 2 at the chain end combs, 2 spare. |
| M26 | M6 × 16 socket head screw | 1 | Any source. Price not checked. | Camera pole into the pole foot (optional). |
| M27 | M5 nyloc nuts, M5 flat washers (small, 7.5 mm across) | 12 nuts, 6 small washers | [Amazon search: M5 nylon lock nut washer](https://www.amazon.com/s?k=M5+nylon+lock+nut+washer+assortment), est. $6 | The nuts: the 6 Y wheels, the 3 X wheels, the 3 idler forks. The washers are SMALL M5 washers (5.3 × 7.5 × 1): 6 in the idler forks (one each side of each idler). The fixed X wheels use stock 6 mm spacers now. |
| M28 | M3 heat-set inserts, brass, M3 × 5.7 mm (about 4.6 mm across) | 12 (buy a pack) | [Search: M3 heat set insert 5.7mm](https://www.amazon.com/s?k=M3+heat+set+insert+5.7mm), est. $8 (pack) | The 3 endstop boards (2 Y boards in the front bases, the X board on the X endstop wall of the left Y carriage): 6 inserts. The 6 belt jaws (2 in each Y carriage, 2 in the X plate, in the ledges of the clamp pockets): 6 inserts. Hole 4.0 mm, 7 mm deep (6.5 mm in the ledges). |
| M29 | 8 mm open-end wrench | 1 | [Search: 8mm wrench](https://www.amazon.com/s?k=8mm+open+end+wrench), est. $5 | Turns the eccentric spacers. Skip it if your CR-10 tool kit has one. |
| M30 | Not used. The printed belt jaws (`belt_jaw`, 6) replace the GT2 crimp clips. | 0 | | |
| M31 | Stepper motor cable, 1.5 m: JST XH 4-pin to PH2.0 6-pin | 0 to 2 | [Amazon search: stepper motor cable 1.5m XH2.54 4pin PH2.0 6pin](https://www.amazon.com/s?k=stepper+motor+cable+1.5m+xh2.54+4pin+ph2.0+6pin), est. $10 (pack) | Only if a stock cable is too short. The Y motors stand behind the back bar now: Y1 is about 0.4 m from the base board, Y2 about 0.8 m along the table behind the frame. They do not move. |
| M32 | Drag chain (cable carrier), **openable**, inner 10 × 20 mm (10 × 15 is enough now), bend radius R28, with end brackets | 1 m (use about 0.51 m) | [Search: openable drag chain 10x20 R28](https://www.amazon.com/s?k=openable+drag+chain+10x20+R28+1m), est. $12–15 | The head harness only (the Y motor cables are static now). Openable, because the big harness plug does not pass a closed link. The model reads the size and the radius from `YCH_*` in hardware/shape.py. |
| M33 | Split wire loom, 1/2 inch (12.7 mm) | 295 mm | **On hand**: no purchase. | The servo lead runs in it from the head board to the X plate. Cut it to 295 mm. The loop between the two ties is 189 mm long. One cable tie (M25) goes through the slot at the top left of the X plate. The other tie holds the loom to the head harness cable, above the big plug of the head board. |
| M34 | Not used. No wheel axle goes into an insert. Each axle has a nyloc nut (M27). | 0 | | |
| M35 | Soldering iron tip for M3 heat-set inserts | 1 | [Amazon search: heat set insert tip M5](https://www.amazon.com/s?k=heat+set+insert+tip+M5), est. $8–12 | Fits most 900M-style and pen-style irons. Check the thread of your iron first. 220 °C for PLA. Skip it if you have an insert tip; a plain conical tip also works with care. |
| M36 | Slot cover strip for 2020 V-slot, 6 mm, flexible PVC, black or grey | 2 m pack (uses 1.21 m) | [Search: 2020 slot cover strip 6mm](https://www.amazon.com/s?k=2020+slot+cover+strip+6mm), est. $8–12 | Holds the Y endstop wires in the slots. Cut lengths: left rail bottom outer slot 428 mm (y 36–464), right rail bottom outer slot 452 mm (y 36–488), back bar bottom slot 29 mm (x 29–58) and 302 mm (x 76–378). Leave the gaps at the cable entries and exits (`hardware/context_detail_HOOKUP.md`). |
| M38 | Nylon M3 standoffs, 4 mm long | 4 | [Search: nylon M3 standoff 4mm](https://www.amazon.com/s?k=nylon+M3+standoff+4mm). Price not checked. | Two under each breakout board (the head board on the beam, the base board on the back bar). A cable tie goes through each board hole and standoff, round the extrusion. |
| M37 | Adhesive cable tie mounts, 19 × 19 × 3 mm | 8 (pack of 50) | [Search: adhesive cable tie mounts 19mm](https://www.amazon.com/s?k=adhesive+cable+tie+mounts+19mm). Price not checked. | Hold the static cables on the table under the trunk, one cable tie at each mount. The positions are in `hardware/context_detail_HOOKUP.md`. M25 has the 12 extra cable ties. |
| M39 | M5 × 12 countersunk screw (ISO 10642) | 2 | Any source. Price not checked. | One through the ear of each Y idler bracket into a T-nut (M22) in the front face slot of the front bar. |

Twelve M3 heat-set inserts (M28). You need a soldering iron for them.

### Reused from the CR-10 V3

- The base frame (2 2020 bars, 2 2040 frame rails, the 4 rubber feet) and the 2020 X beam.
- The 3 V-wheels, the eccentric spacer and the two 6 mm spacers of the Creality X carriage plate. The stock X plate itself and its wheel bolts are not used now: a printed X plate replaces it.
- 6 free V-wheels with 4 × 6 mm spacers and 2 eccentric spacers (from the Z carriages and the bed carriage), for the Y carriages.
- The X idler wheel if it is a 20T toothed idler (otherwise use an M20 idler). The stock X belt is too short now (879 mm between the folds): cut the X belt from the roll (M18).
- The five NEMA 17 motors (on hand: two 42-34 and three 42-40). X: a 42-34 (213.4 g, measured): it rides on the gantry, so the shorter, lighter motor cuts the moving mass (73.3 g less than a 42-40). Y1 and Y2: 42-40 (286.7 g, measured); they stand still. Spares: one 42-40 and one 42-34.
- 3 endstop boards, 2 GT2 pulleys and 1 GT2 idler (the X idler).
- The control box: the Creality v2.5.2 mainboard, the 350 W supply, and the 12864 LCD with the knob.
- The stock harness with the head board and the base board, and the motor and endstop cables.

Spare parts after the build: the Z lead screw, the two uprights, the top bar, the bed, the stock Y belt, and the extruder and hot end.

### Plotting supplies

| Item | Source | Notes |
|---|---|---|
| Pens | [Search: Sakura Pigma Micron 05 6-pack](https://www.amazon.com/s?k=Sakura+Pigma+Micron+05+6+pack), about $16 | The pen slider holds one pen in its V bore. Round barrels 8 to 15 mm fit. |
| Blue painter's tape or a cutting mat | Any source | Holds the paper on the table. |

### Totals, stock controller build (estimates)

| Group | Lines | Subtotal |
|---|---|---|
| Servo | S1 | about **$7** |
| Electronics | S2, S3, S6 | about **$46** |
| Mechanics | M18–M25, M27–M29, M31, M32, M35, M36 | about **$128** ($122–136) |
| Printed parts (PLA) | 22 parts, see the build guide | **$8.12** |
| **Total** | | **about $189 before tax** ($183–197) |

The pens, the M37 tie mounts, the M38 standoffs and the M39 countersunk screws (price not checked) are not in the total. The servo loom (M33) is on hand. The camera (a USB webcam on a 590 mm camera pole) and its printed pole foot are optional and not in the total.

## Part 2: Reference facts

Each fact has a confidence label:
**Confirmed** (a source states it), **Likely** (several weak sources agree, or common knowledge), **Unknown** (measure it).

### Mainboard

- **Confirmed:** The CR-10 V3 (2020) mainboard is a Creality v2.5.2 with an ATmega2560. Source: the Klipper config `printer-creality-cr10-v3-2020.cfg` ([GitHub](https://github.com/Klipper3d/klipper/blob/master/config/printer-creality-cr10-v3-2020.cfg)).
- **Likely:** The stepper drivers on that board are TMC2208 in standalone mode. Some later units may have a different board revision. Read the silkscreen on your board.
- **Unknown:** Board size and hole spacing. No public drawing exists. Creality did not publish the V2 / V3 board files ([GitHub issue](https://github.com/Creality3DPrinting/CR10-V2/issues/6)). The board stays in the stock control box, so the build does not need them.

### LCD (12864 with knob)

- **Confirmed:** The controller is an ST7920 (Klipper `lcd_type: st7920` in the CR-10 V3 config).
- **Confirmed:** EXP1 pinout for the Creality single-ribbon 12864 (Klipper `sample-lcd.cfg`, section "128x64 Full Graphic Creality CR10 / ENDER 3 stockdisplay"; [GitHub](https://github.com/Klipper3d/klipper/blob/master/config/sample-lcd.cfg)):

| EXP1 pin | Signal | Direction | Note |
|----------|--------|-----------|------|
| 1 | BEEPER | to display | |
| 2 | BTN_ENC (knob click) | from display | Active low. Needs a pull-up. |
| 3 | BTN_EN1 (encoder A) | from display | Needs a pull-up. |
| 4 | — | | Not used by this display. |
| 5 | BTN_EN2 (encoder B) | from display | Needs a pull-up. |
| 6 | LCD SCK (ST7920 E / SCLK) | to display | |
| 7 | LCD CS (ST7920 RS) | to display | |
| 8 | LCD MOSI (ST7920 R/W / SID) | to display | |
| 9 | GND | | **Likely.** Check with a meter. |
| 10 | +5 V | | **Likely.** Check with a meter. |

- The display PCB calls this plug "EXP3". The mainboard calls it "EXP1".
- **Likely:** The encoder and click are plain switches to GND. Klipper turns on MCU pull-ups (`^`) on them. That suggests the display has no pull-ups of its own.
- The stock LCD stays on the stock ribbon to the mainboard. The pull-up and level shift checks are only for the Pico W firmware. This build does not use it. `docs/wiring.md` has them.

### Endstops

- **Confirmed:** Stock firmware treats X and Y endstops as triggered when the pin is high, with a pull-up (Klipper `endstop_pin: ^PE5` and `^PJ1`, no `!`).
- **Likely:** This means the switches are wired normally-closed (NC) to GND. The pin reads low when the switch is not pressed. It reads high when the switch is pressed or when a wire breaks. This is a safe failure mode.
- **Likely:** Each endstop is a mechanical microswitch with 2 wires (signal and GND). The plug at the control box is a 3-pin JST-XH (2.50 mm) with one pin empty.
- **Unknown:** Exact pin order on the plug. Check with a meter: switch released → near 0 Ω between the 2 wires.

### Stepper motors

- **Likely:** Creality 42-40 type (42 × 42 × 40 mm, 1.8°, about 0.4 N·m). Sellers list it for the CR-10 V3 Y axis.
- **Confirmed (measured):** a 42-34 is 213.4 g, a 42-40 is 286.7 g.
- **Uncertain:** Rated current. Most listings say 1.0 A per phase. Some say 1.5 A. **Read the label on each motor.** The onboard drivers keep the current setting of the printer.
- **Likely:** Connector at the motor is a 6-pin JST-PH (2.0 mm) with 4 wires. Connector at the board end is a 4-pin JST-XH (2.50 mm). Check your cables.
- **Confirmed:** X and Y use GT2 belts on 20-tooth pulleys. Klipper uses `rotation_distance: 40` with 16 microsteps. That gives 200 × 16 / 40 = **80 steps/mm** for X and Y at 1/16.
- **Confirmed:** Travel: `position_max: 300` for X and Y. Endstops at 0.

### Bed

- **Confirmed:** Print area 300 × 300 mm.
- **Likely:** Glass: carborundum glass, 310 × 320 mm, 4 mm thick. Some EU listings say 3 mm. **Measure your glass.** Sources: [3DJake](https://www.3djake.com/creality-3d-printers-spare-parts/carborundum-glass-plate?sai=7807), [Lemona listing for 3007020014](https://lemona.ee/en/carborundum-glass-plate-for-3d-printer-310-320-4-cr-10v2-cr-10spro-cr-10sprov2-cr-x-creality-3007020014.html).
- **Unknown:** Aluminium plate size and thickness. It is probably about 310 × 310 mm and about 3 mm thick.

### X carriage plate

- **Unknown:** No published drawing gives the hotend / Titan bolt pattern for the CR-10 V3 carriage.
- Measure the plate hole centres with calipers, or take the pattern from a CR-10 V3 carriage remix STEP file. Example: [CR-10 v3 and v2 X-Carriage for Voron Afterburner](https://printables.com/model/285188-cr-10-v3-and-v2-x-carriage-for-voron-afterburner-r).

### Control box power supply

- **Confirmed:** 24 V, 350 W, Mean Well brand per the CR-10 V3 manual ([manuals.plus](https://manuals.plus/asin/B07XYVD2C1)).
- **Unknown:** Exact model number. Read the PSU label.
- Set the input switch to 115 V for the US. Check this before first power-on.
- In the stock controller build, the supply stays in the control box and feeds the mainboard.

## Sources

- [Klipper CR-10 V3 config](https://github.com/Klipper3d/klipper/blob/master/config/printer-creality-cr10-v3-2020.cfg), [Klipper sample-lcd.cfg](https://github.com/Klipper3d/klipper/blob/master/config/sample-lcd.cfg).
- [Duet forum: 12864 level shifting, encoder is switches to GND](https://forum.duet3d.com/topic/15611/logic-level-shifter-for-12864-display-on-duet-2-wifi/45).
- [Creality CR-10 vs V2 vs V3 blog](https://www.creality.com/blog/creality-cr-10-vs-cr-10-v2-vs-cr-10-v3-3d-printer-what-are-the-differences).

