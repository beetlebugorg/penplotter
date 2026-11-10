# Electronics and wiring

The plotter uses the CR-10 V3 control box as it is: the Creality v2.5.2 mainboard (ATmega2560),
the onboard stepper drivers, the 350 W supply, and the LCD with the knob. The box stands on the
table beside the frame. The stock harness stays. The two small Creality boards at the ends of the
harness stand bare on nylon standoffs. You make no changes inside the box.

![The stock controller build on the table](../../hardware/build/img/t_variant-light.png)

## The parts

| Part | Job |
|---|---|
| Control box | Holds the mainboard and the 350 W supply. Connects to the computer with USB. |
| Creality v2.5.2 mainboard | ATmega2560 at 16 MHz with 8 KB of RAM. Runs the firmware. Drives the motors with its onboard drivers. |
| LCD with the knob | ST7920 display on the stock ribbon. Shows 4 text lines and a short menu. |
| Head board | Rides on the back face of the X beam. Connects the X motor, the X endstop and the pen servo. |
| Base board | Sits on the back face of the back bar. Connects the two Y motors and the two Y endstops. |
| Pen servo | SG90 or MG90S. Plugs into `BL_T` on the head board, through a pigtail and a 70 cm extension (or a lead that you make with S3 and S6). |

The mainboard has four drivers: X, Y, Z and E. The plotter uses X for the X motor, Y for the Y1
motor (left), and Z for the Y2 motor (right). The E driver is free. The hotend heater output
(`HEAT`, the MOSFET on D10, PB4) is not used. The firmware holds it off.

## The breakout boards

Each board stands bare on two 4 mm nylon M3 standoffs (BOM M38). A cable tie goes through each
board hole and its standoff, round the extrusion. The standoffs give room for the pins under the
board. The big plug points up.

| Board | Place | Notes |
|---|---|---|
| Head board | Back face of the X beam, from x = 96 mm | Rides with the gantry. The big header is at the top. |
| Base board | Back face of the back bar, from x = 71 mm | The standoffs stand on the face of the bar, beside the slot. |

> **Caution:** The two ties of the head board go round the beam. The X plate and its wheels pass
> that place. This question is open: `hardware/REVIEW.md` lists the options. Push the X plate by
> hand over the full travel before you power the motors.

## The cables

The motors do not move, so few cables move. No part stands tall over the frame.

- **Drag chain.** An openable drag chain (inner 10 × 20 mm, bend radius R28, about 506 mm long)
  lies beside the left rail, outside the frame. It carries only the head harness. A 10 × 15 mm
  chain is enough. Its lower run lies on the table. Its fixed end sits in `y_chain_anchor` at the
  back left corner. Its moving end bolts to a tab of the left carriage.
- **Y motor cables.** The Y motors stand behind the back bar. Their cables run on the table behind
  the frame to the base board. They do not move. If a stock cable is too short, use a 1.5 m
  stepper cable (BOM line M31).
- **Endstop wires.** The Y endstop wires run in the bottom outer slots of the rails and in the
  bottom slot of the back bar, under 6 mm slot cover strips. They do not move.
- **X motor.** The X motor plugs into the head board on the beam. Its cable does not move.
- **Servo loom.** The servo lead runs in a 1/2 inch split wire loom, 295 mm long. The loom hangs
  in a free loop behind the beam, 189 mm between the two ties. One tie goes through the slot at
  the top left of the X plate. The other tie holds the loom to the head harness cable, above the
  big plug of the head board.
- The control box stands left of the frame, clear of the chain.

> **Caution:** The board sizes come from photos. Measure the two boards before you place the
> standoffs (`hardware/MEASURE.md`, items 24 to 33). Start with the hole spacing.

## Make the servo pigtail and the extensions

The crimp kit (S3) has the housings, the terminals and the crimper. Use the 24 AWG silicone wire (S6).

| Cable | End 1 | End 2 |
|---|---|---|
| Servo pigtail (S4) | XH 5P housing, into `BL_T` | Dupont 3P housing with male pins, into the servo extension |
| Endstop extension (S5), 50 cm | XH 2P housing | XH 2R inline male housing |

To crimp a terminal:

1. Strip 2 mm of insulation.
2. Put the terminal in the die with the open side up. Use the 0.25 die for 24 to 26 AWG and the
   0.5 die for 22 AWG.
3. Put the wire in the terminal. The bare wire goes under the front tabs. The insulation goes
   under the rear tabs.
4. Close the crimper until the ratchet releases.
5. Pull on the wire. A good crimp does not move.
6. Push the terminal into the housing until it clicks. The latch tab of the terminal faces the
   window of the housing.

> **Caution:** Check the pin order of `BL_T` before you make the servo pigtail
> (`docs/wiring.md`). A wrong 5 V pin can damage the servo.

## Power-up checklist

Do these steps in this order. Each step protects the parts of the next one.

1. Check the voltage switch of the supply: 115 V for the US.
2. Check the plugs against the socket table below with the box off.
3. Push the X plate by hand over the full X travel. It must pass the head board ties.
4. Leave the servo disconnected. Turn on the box.
5. Measure the `BL_T` pins with a meter: 5 V from pin 2 to pin 1.
6. Turn off the box. Connect the servo.
7. Connect USB. Flash the firmware (`25-firmware`).
8. Send `M115`, then `M119`. Test each endstop by hand.
9. Test the motor directions with a short relative move (see "Motor directions" below).
10. Send `G28`.

Never connect or disconnect a motor while the box is on. A disconnected coil can destroy the
driver.

## Wiring reference

The sections below come from `docs/wiring.md`. The pin map is also in
`firmware/board/mega/pins.go`. The cable routes are in "The cables" above.

<!-- include: ../wiring.md#Safety rules -->

<!-- include: ../wiring.md#Block diagram -->

<!-- include: ../wiring.md#Board sockets -->

<!-- include: ../wiring.md#Pen servo on `BL_T` -->

<!-- include: ../wiring.md#Mainboard pin map -->

<!-- include: ../wiring.md#Motor current -->

<!-- include: ../wiring.md#Endstops -->

<!-- include: ../wiring.md#Motor directions -->

<!-- include: ../wiring.md#Homing and squaring -->
