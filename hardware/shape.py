# Pen plotter parts for a CR-10 V3: all dimensions. Units are millimetres.
#
# The CR-10 V3 becomes a table pen plotter. The tool head is removed. The pen carriage bolts to
# the stock Creality X carriage plate with the four M3 holes of the tool head.
#
# - The pen carriage bolts to the front of the carriage plate. Four M3 screws go in from the rear,
#   through the plate, into pilot holes in the pen carriage. They cut their own thread.
# - A vertical dovetail rail on the pen carriage carries the slider. The slider holds the pen.
#   The slider and the pen fall on the rail by their weight. The weight is the pen force.
# - A hobby servo (SG90 or MG90S) sits in a pocket of the pen carriage. Its horn lifts a tab on
#   the slider. At the pen-down angle the horn is clear of the tab, so the pen rests on the paper.
# - A shelf at the bottom of the rail stops the slider when there is no paper or pen.
# - The pen goes in a vertical bore in the slider. An M3 screw pushes it into a 90 degree V.
#   Pens from 8 to 15 mm fit.
# - With the pen on the paper, the slider rests 3 mm above the shelf (HOVER).
#
# Plate frame: the frame of the carriage plate model (reference/carriage_plate_Bear.step).
#   X along the X axis of the printer (+X is the right side, seen from the front).
#   Z up.
#   Y to the rear. The front face of the plate sheet is at Y = 0. The pen carriage is at Y < 0.
#
# Print orientation:
#   pen_carriage: the back face (Y = 0) on the bed.
#   pen_slider: upright, Z up, the bottom face on the bed.
#   fit parts: flat.
#
# Sources: the hole positions come from an owner-made model of the carriage plate (the hole
# centres at the mid plane of the sheet). reference/SOURCES.md lists the two plate models. They
# agree to about 1 mm. Values marked ESTIMATE are not measured. MEASURE.md lists the measurements to take.

import math

# ---- The carriage plate ----
# The four tool head holes, [name, x, z]. T1 and T2 are slots 8.5 mm long in X, so the pen
# carriage can move 2.5 mm left or right. H1 and H2 are round holes.
HEAD_HOLES = [
    ("T1", 10.01, 59.78),
    ("T2", -5.40, 59.81),
    ("H2", 2.04, 44.82),
    ("H1", 22.37, 5.59),
]
HEAD_SCREW_DEPTH = 8.0           # pilot hole depth for the M3 x 10 head screws (2.5 mm plate, 7.5 mm thread)

# ---- Screws ----
M3_CLEAR = 3.4                   # clearance hole for M3
M3_NUT_AF = 5.5                  # M3 nut, across the flats
M3_NUT_T = 2.4                   # M3 nut, thickness
M2_PILOT = 1.8                   # hole for the M2 self-tapping screws of the servo and the switches

# ---- Drop: the rail, the shelf, the slider and the servo are this much lower than on the
# first design, so the pen reaches the table under the gantry ----
DROP = 46.0

# ---- The base ----
BASE_T = 8.0                     # thickness of the back layer (Y = 0 to -BASE_T)
BASE_R = 3.0                     # radius of the outline corners
KEEP_CLR = 0.5                   # gap between the outline and a wheel bolt head
# The outline of the back layer is the union of these rectangles [x0, x1, z0, z1], less the
# wheel bolt keep-outs. The front features stand only on the back layer, so the part prints
# with no support.
BASE_RECTS = [
    (-12.0, -0.5, -7.0 - DROP, 62.0),   # the spine behind the rail
    (-12.0, 20.0, 38.0, 62.0),   # the top band
    (14.0, 37.5, -2.0 - DROP, 42.0),    # the right arm: H1 and the servo
    (-20.5, 10.5, -7.0 - DROP, 0.0 - DROP),    # the shelf, at the bottom
]

# ---- The rail (a dovetail along Z on the front face of the base) ----
RAIL_X = -4.6                    # centre of the rail. The root stays on the back layer, clear of the wheel bolts.
RAIL_W0 = 7.5                    # width at the root (on the base face)
RAIL_D = 4.0                     # depth out of the base face
RAIL_ANGLE = 60.0                # angle of the sides to the base face
RAIL_TOP = 58.0                  # top end of the rail
DT_CLR = 0.25                    # gap between the rail and the slot, on each side
DT_GAP = 0.3                     # gap between the base face and the back face of the slider

# ---- The shelf: the stop at the bottom of the rail ----
SHELF_TOP = -3.0 - DROP                 # the slider rests here with no paper
SHELF_FRONT = -14.0              # front face of the shelf (Y). The pen passes in front of it.

# ---- The slider ----
HOVER = 3.0                      # with the pen on the paper, the slider is this far above the shelf
SLIDER_H = 40.0                  # height
SLIDER_Z0 = SHELF_TOP + HOVER    # the bottom of the slider at pen down (world Z)
SLIDER_BACK = -(BASE_T + DT_GAP) # back face of the slider (Y)
PEN_R = 8.0                      # radius of the round part of the bore. Pens up to 15 mm fit.
PEN_MIN, PEN_MAX = 8.0, 15.0     # the pen sizes the clamp holds
WALL_SLOT = 3.0                  # wall between the slot and the bore
WALL_FRONT = 7.5                 # wall in front of the bore
WALL_NUT = 8.0                   # wall at the left of the bore, with the nut slot
WALL_V = 3.0                     # wall at the right of the V
CLAMP_Z = 32.0                   # height of the clamp screw above the bottom of the slider
CLAMP_SCREW_L = 20.0             # M3 x 20 clamp screw

# ---- The servo (SG90; the MG90S has the same body) ----
SERVO_L = 22.8                   # body length, along Z. ESTIMATE (data sheet values)
SERVO_W = 12.4                   # body width, along X. ESTIMATE
SERVO_BELOW = 16.0               # body depth below the mounting tabs. ESTIMATE
SERVO_TAB_L = 32.2               # length over the two tabs. ESTIMATE
SERVO_TAB_T = 2.5                # thickness of the tabs. ESTIMATE
SERVO_TAB_HOLES = 27.8           # distance between the two tab holes. ESTIMATE
SERVO_TOP = 4.3                  # the case stands this far above the tabs. ESTIMATE
SERVO_SPLINE_H = 3.6             # the spline stands this far above the case. ESTIMATE
SERVO_SHAFT_END = 6.0            # from the end of the body to the centre of the shaft. ESTIMATE
SERVO_CLR = 0.3                  # gap around the body in the pocket
SHAFT_X, SHAFT_Z = 27.0, 18.0 - DROP    # the servo shaft. The shaft end of the body is at the bottom.
HORN_L = 14.0                    # from the shaft to the centre of the round end of the horn arm. ESTIMATE
HORN_TIP_R = 2.0                 # radius of the round end of the arm. ESTIMATE
HORN_T = 1.6                     # thickness of the arm. ESTIMATE
HORN_HUB = (7.0, 4.0)            # diameter and height of the horn hub. ESTIMATE
TOWER_X = (18.0, 35.5)           # the servo tower, in X
WIRE_SLOT = 4.0                  # slot for the servo wire, at the top end of the pocket

# The horn angles, in degrees above level. The arm points at the slider (to -X).
PEN_DOWN_DEG = -10.0
PEN_UP_DEG = 40.0
TAB_GAP = 1.0                    # gap between the horn and the tab at pen down

# ---- Derived values ----
RAIL_W1 = RAIL_W0 + 2 * RAIL_D / math.tan(math.radians(RAIL_ANGLE))   # width at the outer face
SERVO_FACE = -(BASE_T + SERVO_BELOW)          # the tabs rest on this face of the tower (Y)
SPLINE_TOP = SERVO_FACE - SERVO_TAB_T - SERVO_TOP - SERVO_SPLINE_H
HORN_Y = SPLINE_TOP - HORN_T / 2 - 0.4        # mid plane of the horn arm (Y). The arm is on the outer end of the hub.
BODY_Z0 = SHAFT_Z - SERVO_SHAFT_END           # bottom end of the servo body
BODY_Z1 = BODY_Z0 + SERVO_L                   # top end of the servo body
BODY_ZC = (BODY_Z0 + BODY_Z1) / 2
TOWER_Z = (BODY_Z0 - (SERVO_TAB_L - SERVO_L) / 2 - 2.0, BODY_Z1 + (SERVO_TAB_L - SERVO_L) / 2 + 1.0)

# The slider, in X: nut wall, bore, V, wall. The rail is at the middle.
SLIDER_W = WALL_NUT + 2 * PEN_R + (math.sqrt(2) - 1) * PEN_R + WALL_V
SLIDER_X0 = RAIL_X - SLIDER_W / 2
SLIDER_X1 = RAIL_X + SLIDER_W / 2
PEN_CX = SLIDER_X0 + WALL_NUT + PEN_R          # centre of the round part of the bore
V_X = PEN_CX + math.sqrt(2) * PEN_R            # the apex of the V
SLOT_FLOOR = SLIDER_BACK - RAIL_D - DT_CLR     # the floor of the dovetail slot (Y)
PEN_CY = SLOT_FLOOR - WALL_SLOT - PEN_R        # centre of the bore (Y)
SLIDER_FRONT = PEN_CY - PEN_R - WALL_FRONT     # front face of the slider (Y)


def horn_tip(deg):
    """The centre of the round end of the horn arm, [x, z], at an angle above level."""
    a = math.radians(deg)
    return SHAFT_X - HORN_L * math.cos(a), SHAFT_Z + HORN_L * math.sin(a)


def tip_c(deg):
    """z - x of the tip centre. The tab underside is a 45 degree line z - x = c."""
    x, z = horn_tip(deg)
    return z - x


# The tab: a 45 degree underside from the slider face to TAB_X1. At pen down, the underside
# line z - x = c is TAB_GAP from the round end of the horn.
TAB_X1 = SLIDER_X1 + 7.5
TAB_Y = (HORN_Y + 3.0, HORN_Y - 3.0)           # the tab spans the horn plane in Y
_c0 = tip_c(PEN_DOWN_DEG) + (HORN_TIP_R + TAB_GAP) * math.sqrt(2)
TAB_Z0 = _c0 + SLIDER_X1 - SLIDER_Z0           # underside at the slider face, above the slider bottom
TAB_TOP = 2.0                                  # flat band above the 45 degree part
# The lift of the pen at the pen-up angle. The tab first touches the horn at TAB_GAP.
LIFT = (tip_c(PEN_UP_DEG) - tip_c(PEN_DOWN_DEG)) - TAB_GAP * math.sqrt(2)

# ================================================================ the table plotter
# The base frame of the CR-10 V3 stands on the table. The table is the bed. The X beam spans
# the two long rails on two printed Y carriages. Each Y carriage wraps its rail from the outer side
# (a C shape) and runs on 3 stock V-wheels: 2 in the outer slot of the top face, 1 in the inner slot
# of the bottom face. Each side has a Y motor, a belt, and an endstop. The stock Creality X carriage
# plate runs on the beam on its own 3 V-wheels, as on the printer. The pen carriage bolts to the
# front of the plate.
#
# Frame coordinates: the origin is the front left outer corner of the frame, on the table.
# X to the right, Y to the back, Z up. Machine X = 0, Y = 0 is the home corner (front left).
# Measured: outside 400 x 520, inside 320 x 480, table to rail top 57.
# The long sides are 2040, laid flat. The front and back cross bars are 2020.
FRAME_X, FRAME_Y = 400.0, 520.0  # outside
BAR_D, BAR_H = 20.0, 20.0        # front and back bars: 2020
RAIL_W, RAIL_H = 40.0, 20.0      # long rails: 2040 flat
FOOT_H = 37.0                    # the rubber feet: table to the bottom of the bars and the rails. ESTIMATE:
                                 # 57 mm to the rail top (measured) less the 20 mm rail
RAIL_TOP_Z = FOOT_H + RAIL_H     # table to the top of the rails: 57 mm (measured)
BAR_Z0 = FOOT_H                  # bottom of the bars: the bar and the rail bottoms are in one plane. ESTIMATE
# The feet: four tapered rubber feet under the long rails. The back feet stop the bottom
# wheel of each Y carriage, so they set the back end of the Y travel.
FOOT_D = 28.0                    # diameter of the feet, at the top. ESTIMATE (photo)
FOOT_X = 31.0                    # foot centre from the outer face of the side: under the inner bottom slot. ESTIMATE (photo)
FOOT_Y = (37.5, FRAME_Y - 37.5)  # foot centres from the front of the frame. ESTIMATE (photo)
# Two screws go through the outer face of each bar into the centre holes of each 2040 end. Their
# heads stand on the outer face of the bar. ESTIMATE (photo): x from the outer face of the side.
BAR_SCREW_X = (10.0, 30.0)
BAR_SCREW_HEAD = (8.5, 5.0)      # M5 socket head: diameter, height. ESTIMATE
BAR_SLOT_Z = (BAR_Z0 + BAR_H / 2,)   # the one slot in the outer face of a 2020 bar
M5_CLEAR = 5.4

# ---- V-wheels (stock CR-10 wheels) ----
# The wheel is a lathe shape: flat faces out to the V, then two 45 degree flanks to a flat tip.
# A slot of the extrusion is a 90 degree V. The wheel touches the two flanks of the V.
WHEEL_D = 24.4                   # outside diameter, at the flat tip. ESTIMATE
WHEEL_T = 10.2                   # thickness. ESTIMATE
WHEEL_TIP = 0.5                  # the flanks meet this far outside the flat tip. ESTIMATE
WHEEL_BORE = 5.0                 # M5 axle
WHEEL_OFF = 10.1                 # from the face of the extrusion to the axle when the wheel sits in the slot. ESTIMATE
SLOT_V = 2 * (WHEEL_D / 2 + WHEEL_TIP - WHEEL_OFF)   # width of the slot V at the face (model value)
WHEEL_PRELOAD = 0.1              # the eccentric spacer pushes the wheel this far into the slot (fit check)
SPACER_H = 6.0                   # spacer between the carriage and a wheel (plain or eccentric). ESTIMATE
ECC_HOLE = 7.5                   # hole for the shank of the eccentric spacer. ESTIMATE (the CR-10 plate hole is 7.35)
ECC_RANGE = 0.8                  # the eccentric moves the axle this far each way. ESTIMATE
M5_HEAD = (8.5, 5.0)             # M5 socket head: diameter, height
M5_NUT = (9.2, 4.0)              # M5 nut, across the corners and thickness

# ---- Fasteners (context: the fit check, the screw lengths, the simulator) ----
# No heat-set inserts. The M2 and M3 screws in plastic cut their own thread in a pilot hole.
# The model draws each shank at about the core diameter of the thread, so a shank in a pilot hole
# does not touch the plastic. A shank that touches a printed part is a clash.
SHANK = {"M2": 1.6, "M3": 2.5, "M5": 4.2, "M6": 5.0}     # drawn shank diameter
SOCKET = {"M3": (5.5, 3.0), "M5": (8.5, 5.0), "M6": (10.0, 6.0)}   # socket head: diameter, height
BUTTON = {"M5": (9.5, 2.75)}     # ISO 7380 button head: diameter, height
PAN = {"M2": (3.8, 1.6)}         # pan head of the M2 self-tapping screws. ESTIMATE
NYLOC = (8.0, 5.0)               # M5 nyloc nut: across the flats, height
M3_NUT = (5.5, 2.4)              # M3 hex nut: across the flats, height
WASHER = (10.0, 1.0)             # M5 flat washer: outside diameter, thickness
IDLER_SPACER_D = 10.0            # the 6 mm spacers under the idlers: outside diameter
# The slots of the 2020 and 2040 extrusions, and the M5 drop-in T-nuts.
SLOT_LIP = 1.8                   # the lip each side of the slot opening. ESTIMATE
SLOT_DEPTH = 6.3                 # from the face to the core of the extrusion. A screw must not reach it. ESTIMATE
TNUT = (10.0, 9.5, 4.0)          # drop-in T-nut: length along the slot, width, thread length. ESTIMATE
TNUT_ENGAGE = 3.0                # the screw must go this far into the T-nut thread (about 4 turns)
SELF_TAP_ENGAGE = {"M2": 4.0, "M3": 6.0, "M5": 10.0}  # the least thread length of a self-tapping screw in plastic: 2 x d
MOTOR_THREAD = 4.5               # depth of the M3 threads in a NEMA17 face. ESTIMATE
MOTOR_ENGAGE = 2.5               # the least thread length in a motor face
BEAM_END_THREAD = 15.0           # the M5 thread in the centre hole of the beam end. ESTIMATE
BAR_SCREW_L = 30.0               # the stock screws through the bars into the 2040 ends. ESTIMATE
# Screw lengths. Each length passes the length check in model.py.
TNUT_SCREW_L = 12.0              # M5 into a T-nut through a 6 mm wall (brackets, beam, pole foot, feet)
BEAM_END_L = 16.0                # M5 through the tower into the beam end
TOP_AXLE_L = 30.0                # M5 axle of a top Y wheel
BOT_AXLE_L = 40.0                # M5 axle of a bottom Y wheel
YIDLER_AXLE_L = 30.0             # M5 axle of a Y idler
XIDLER_AXLE_L_OLD = 35.0         # M5 axle of the X idler (before the fork)
XMOTOR_SCREW_L = 10.0            # M3: the X motor through its 6 mm wall
YMOTOR_SCREW_L = 8.0             # M3: a Y motor through the 5 mm platform
COLLAR_SCREW_L = 16.0            # M3: the collar of the pole foot
SWITCH_SCREW_L = 12.0            # M2 x 12 self-tapping: an endstop switch (6.4 mm body) on its wall: 5.6 mm of thread
SERVO_SCREW_L = 8.0              # M2 self-tapping: the servo screws (in the servo bag). ESTIMATE

# ---- Y carriage (left; the right one is the mirror image about the centre of the frame) ----
# A C shape that wraps the rail from the outer side. The wheels stand vertical: the axles point
# along X. Two wheels run in the outer slot of the top face, one in front of and one behind the
# beam centre. One wheel runs in the inner slot of the bottom face, at the beam centre, on the
# eccentric spacer. The diagonal spread across the rail stops the roll of the carriage.
# Gantry frame: c is the frame y of the beam centre.
SLOT_OUT_X, SLOT_IN_X = 10.0, 30.0               # the two slots of the top and bottom faces (x)
WHEEL_PITCH = 22.0               # the two top wheels are this far in front of and behind the beam centre
YW_TOP_Z = RAIL_TOP_Z + WHEEL_OFF                # top wheel axles (z)
YW_BOT_Z = RAIL_TOP_Z - RAIL_H - WHEEL_OFF       # bottom wheel axle (z)
YC_X0 = -22.0                    # outer edge of the carriage plate and the tower
YC_Y = (-38.0, WHEEL_PITCH + 14.0)   # the side plate, from the beam centre (y)
SIDE_X1 = SLOT_OUT_X - WHEEL_T / 2 - SPACER_H    # inner face of the side plate: a spacer from the top wheels
SIDE_T = 6.0
SIDE_X0 = SIDE_X1 - SIDE_T                       # outer face of the side plate
LUG_T = 6.0                      # the two lugs that carry the bottom wheel axle
LUG_OUT = (SLOT_IN_X - WHEEL_T / 2 - SPACER_H - LUG_T, SLOT_IN_X - WHEEL_T / 2 - SPACER_H)   # outer lug: the eccentric hex is between it and the wheel
LUG_SHIM = 1.0                   # an M5 washer between the wheel and the inner lug
LUG_IN = (SLOT_IN_X + WHEEL_T / 2 + LUG_SHIM, SLOT_IN_X + WHEEL_T / 2 + LUG_SHIM + LUG_T)
LUG_HALF_Y = 12.0                # the lugs and the web, from the beam centre (y)
LUG_TOP = RAIL_TOP_Z - RAIL_H - 2.0              # 2 mm under the rail
WEB_Z = (5.0, 13.5)              # the web under the rail and under the bottom wheel. 5 mm above the table.
SIDE_TAPER_Z = RAIL_TOP_Z - RAIL_H   # below this the side plate is only as long as the web; above it, 45 degrees out
SHOULDER_Z = 60.0                # underside of the outer shoulder at the side plate; it rises 45 degrees outward
DECK_Z = RAIL_TOP_Z + 0.5        # underside of the parts over the rail at the side plate; it rises 45 degrees inward
WELL_CLR = 1.0                   # gap around a top wheel in its well
WELL_X1 = SLOT_OUT_X + WHEEL_T / 2 + 5.0         # the well holds the wheel and its nut

# ---- Y belts: outside the frame, in the outer shoulder of the carriage ----
# GT2 drive parts (stock CR-10 V3: 20 tooth pulleys, 5 mm bore; firmware 80 steps/mm = 200 x 16 / (20 x 2)).
PULLEY_TEETH = 20
GT2_PITCH = 2.0
GT2_PLD = 0.254                  # the pitch line is this far outside the pulley teeth
GT2_TOOTH_H = 0.75               # belt tooth height
GT2_TOOTH_R = 0.555              # belt tooth tip radius
PULLEY_PD = PULLEY_TEETH * GT2_PITCH / math.pi    # pitch diameter: 12.73 mm
PULLEY_OD = PULLEY_PD - 2 * GT2_PLD               # outside diameter of the teeth: 12.22 mm
PULLEY = {"flange_d": 16.0, "flange_t": 1.0, "teeth_w": 7.1, "hub_d": 13.0, "hub_l": 7.0, "bore": 5.0,
          "set_screw": "M3"}      # GT2 20T pulley for 6 mm belt, 16 mm long. ESTIMATE (common data sheet)
TIDLER = {"flange_d": 18.0, "flange_t": 1.0, "h": 8.5, "bore": 5.0}   # GT2 20T toothed idler, 5 mm bore
BELT_RUN = PULLEY_OD / 2 - GT2_TOOTH_H + 1.4 / 2   # from the axis to the centre of each belt run: teeth in the grooves
BELT_W = 6.0
BELT_Z = 80.0                    # centre of the belt (z): the belt slots pass over the key holes of the top wheel bolts
BELT_SLOT = 1.7                  # slot for the belt
BELT_T = 1.4                     # GT2 belt thickness over the teeth
# ---- Belt ends: each end folds back on itself, and a metal crimp clip closes it ----
# The belt goes through a slot in an end wall into a pocket. The clip on the folded end is larger
# than the slot, so the pull of the belt presses the clip on the wall. The clip is the OpenBuilds
# style "belt clamp, crimp style" for 6 mm GT2 belt: stamped steel, listed as 18 x 7 x 8 mm folded.
# The listings do not say which size is which. The pocket fits the clip both ways.
CLIP = (18.0, 8.0, 5.0)          # crimped clip: along the belt, across the belt width, thickness. ESTIMATE
CLIP_POCKET = (18.6, 8.6, 8.6)   # the pocket: along the belt, across the belt width, thickness
CLIP_WALL = 4.0                  # the end wall of a pocket in the X clamp block: the clip bears on it
CLIP_WALL_Y = 6.0                # the end wall of a pocket in a Y belt block (the slit cuts it in two)
CLIP_FRONT = 6.0                 # the front end wall of the Y belt block stands this far in front of the
                                 # carriage, in front of the X motor wall, so its slit opens to the top
CLIP_LOOP = 3.0                  # room for the fold of the belt beyond the clip
# The belts are crimped to length on the bench, then dropped in. The slits open to the top (Y) or
# to the front (X). The pockets open to the outer side (Y) or to the front (X).
XIDLER_SLOT = 5.0                # the X idler axle slot, this far each way in X: belt tension
XIDLER_X = 17.0                  # the X idler axle at the middle of its slot (x, mirrored to the right side)


# ---- The stock X carriage plate (plate frame, top of this file) ----
# The three wheels of the plate: [name, x, z]. The bottom wheel is on an eccentric spacer.
# From the reference model. The heads of the wheel bolts are on the front face.
X_WHEELS = [("top left", -15.58, 48.23), ("top right", 29.02, 48.23), ("bottom", 6.92, 7.73)]
X_BOLT_HEAD = (9.5, 2.9)         # wheel bolt head on the front face: diameter, height (reference model)
WHEEL_BOLTS = [(n, x, z, X_BOLT_HEAD[0] / 2) for n, x, z in X_WHEELS]   # keep-outs for the pen carriage
PLATE_SHEET = 2.5                # thickness of the plate sheet (reference model)
PLATE_FRONT = 13.6               # front face of the plate to the beam centre: sheet, spacer, half a wheel. ESTIMATE
X_BOLT_END = PLATE_FRONT + 10.0 - 0.5   # the wheel bolts end inside the back face of the beam (the head board is there)

# ---- The X beam: a 2020 extrusion on the two Y carriages ----
BEAM = 20.0
BEAM_L = 415.0                   # length of the X beam (measured)
BEAM_X0 = (FRAME_X - BEAM_L) / 2 # the beam is centred on the frame: it stands out 7.5 mm each side
CRADLE_CLR = 0.3                 # gap around the beam
PLATE_DZ = 70.5                  # plate frame z + PLATE_DZ = frame z. The pen reaches the table (DROP).
PLATE_BEAM_Z = X_WHEELS[0][2] - BEAM / 2 - WHEEL_OFF   # beam centre in the plate frame: the top wheels sit in the slot
BEAM_Z0 = PLATE_DZ + PLATE_BEAM_Z - BEAM / 2            # bottom of the beam (frame z)
XTOWER = (YC_X0, 28.0)           # the tower that holds the beam end (x). The X plate stops at its inner face.
XTOWER_HALF_Y = 16.0
XTOWER_TOP = BEAM_Z0 + BEAM + CRADLE_CLR + BEAM / 2 + CRADLE_CLR + 3.0   # above the pointed roof of the beam slot
BEAM_CB = (10.0, 8.0)            # counterbore for the M5 screw into the beam end: diameter, depth

# ---- The X drive ----
# The X belt is a vertical loop in front of the X plate. Its lower run is clamped in slots at the
# two ends of a block on the top of the pen carriage. The upper run goes back above the block.
# The X motor bolts to the front of a wall on the left Y carriage. Its shaft points back. The X
# idler turns on an M5 axle between the same wall and a post on the right Y carriage.
XBELT_GAP = 5.0                  # the belt centre is this far in front of the plate
XBELT_DY = -PLATE_FRONT - XBELT_GAP   # the belt plane, from the beam centre (y)
XBELT_ZL = 64.0                  # the lower run (plate frame z)
XCLAMP_Z = (57.0, 72.0)          # the clamp block on the pen carriage (plate frame z): it holds the two clip pockets
XCLAMP_X = (-40.0, 36.0)         # the clamp block (plate frame x)
XCLAMP_D = 10.0                  # the clamp block stands this far in front of the plate
XPULLEY_Z = PLATE_DZ + XBELT_ZL + BELT_RUN   # X pulley and idler axle (frame z)
XMOTOR_X = 20.0                  # X motor shaft and X idler axle (x)
XMWALL = (XBELT_DY - 17.5, XBELT_DY - 11.5)  # the motor wall, from the beam centre (y). The motor face is on its front.
XMWALL_X1 = XMOTOR_X + 31.0 / 2 + 4.5        # the wall reaches past the right motor screws (to x 40: the pen clamp screw comes to x 40.4)
XMWALL_TOP = XPULLEY_Z + 31.0 / 2 + 4.5      # 4.5 mm above the top motor screws (slice test: -4 min, -1 g)
XPOST = (XIDLER_X - 12.0, XMOTOR_X + 7.0)    # the idler post behind the idler (x): around the axle slot
XPOST_Y = (-PLATE_FRONT, -PLATE_FRONT + 6.0) # the idler post, from the beam centre (y)

# ---- Endstops: small microswitches, two M2 holes ----
SWITCH = (20.0, 6.4, 10.2)       # length, thickness, height of the body. ESTIMATE
SWITCH_HOLES = 9.5               # ESTIMATE
# X: on the back face of the motor wall, under the motor. The lever points to +X. A toe on the
# left end of the pen carriage pushes it.
XSW_X = (8.0, 28.0)              # the switch body (x)
XSW_Z = 106.0                    # the switch centre (frame z)
XTOE_X = (-40.0, -34.0)          # the toe on the pen carriage (plate frame x)
XTOE_Z = (XSW_Z - PLATE_DZ - 6.5, XSW_Z - PLATE_DZ + 5.5)   # (plate frame z)
XTOE_D = 14.0                    # the toe stands this far in front of the plate
XLEG_D = 3.5                     # the leg from the clamp block down to the toe
# Y: on the inner face of an arm of the idler bracket, outside the rail. The arm top is on the
# platform plane, so it prints on the bed. The front edge of the side plate of the carriage pushes
# the lever past the end of the arm.


# ---- Motors ----
MOTOR = 42.3                     # NEMA17
MOTOR_L = 40.0                   # body length
MOTOR_HOLES = 31.0
MOTOR_BOSS = 23.0
MOTOR_MASS = 286.7               # g, a 42-40 NEMA17 (the Y motors), measured
IDLER_H = 8.5                    # GT2 idler, with flanges. ESTIMATE
IDLER_SPACER = 6.0               # the spacer between the X idler and the wall

PEN_SIZE_SIM = 12.0

# ================================================================ review round 2
SELF_TAP = 2.8                   # pilot hole for an M3 screw that cuts its own thread in PLA

# ================================================================ camera pole
# The camera pole: a round aluminium tube with a USB webcam on its top end. Each end of the
# tube has an M6 thread. The pole stands on the table behind the centre of the back bar, in a
# printed foot (mast_foot). An M6 bolt goes up through the floor of the foot into the pole end. A
# split collar with one M3 screw takes up the play. Two M5 screws in T-nuts hold the foot on the
# slot of the back bar.
POLE_D = 17.85                   # outside diameter of the pole (measured)
POLE_L = 590.0                   # length of the pole
POLE_CLR = 0.15                  # gap around the pole in the socket, on each side
POLE_THREAD = 15.0               # depth of the M6 thread in the pole end. ESTIMATE
MAST_X = FRAME_X / 2             # centre of the pole (x)
MFOOT_PLATE = 6.0                # the plate on the back face of the back bar
MFOOT_WALL = 3.5                 # wall of the socket
MFOOT_FLOOR = 11.0               # floor under the pole: the M6 head in a counterbore, 4 mm of floor
MFOOT_TOP = 54.0                 # top of the foot (z); 3 mm under the bar top
MFOOT_HALF_X = 35.0              # the plate, each side of the pole (x); the bar screws are 25 mm out
POLE_R_OUT = POLE_D / 2 + POLE_CLR + MFOOT_WALL   # outside of the socket
POLE_Y = FRAME_Y + MFOOT_PLATE + POLE_R_OUT - 1.5 # centre of the pole (y); the socket wall merges with the plate
M6_HEAD = (10.0, 6.0)            # M6 socket head: diameter, height
M6_CLEAR = 6.5
M6_BOLT_L = 16.0                 # M6 x 16: 4 mm of floor, 12 mm into the pole thread
CAM_ABOVE = 15.0                 # the camera lens is this far above the top of the pole. ESTIMATE
POLE_Z0 = MFOOT_FLOOR            # bottom of the pole (z)
POLE_TOP = POLE_Z0 + POLE_L
CAM_Z = POLE_TOP + CAM_ABOVE

# ================================================================ the stock breakout boards
# The stock CR-10 V3 control box (Creality v2.5.2 board, PSU, LCD) stands on the table beside the
# frame. Its stock harness ends in two small breakout boards. Each board stands bare on two 4 mm nylon
# standoffs on an extrusion face. Two cable ties go through the board holes and round the extrusion.
#
# Board pose frame ("local"): z = 0 is the extrusion face, +z points away from it. The board edge
# opposite the big header is at x = 0, the header edge at +x. Local y is along the header.
#
# Board frame: u along the long edge, v across it. v = 0 is the edge opposite the big header.
# The board lies with v along local x and u along local y (y = U/2 - u).
#
# All board values are ESTIMATES from photos (+/- 2 mm). MEASURE.md lists them.

# Head board ("tool head breakout"). It rides on the back face of the X beam, near the left end.
HB_PCB = (47.0, 38.0)            # u (long edge, along the header), v. ESTIMATE
HB_HOLES_U = (8.0, 41.0)         # the two M3 holes, from the BL_T end (u). 33 mm apart. ESTIMATE
HB_HOLES_V = 21.0                # the hole line, from the edge opposite the header (v). ESTIMATE
HB_HDR_U = (3.0, 44.0)           # the 2x15 Micro-Fit plug body, along the edge (u). ESTIMATE
HB_PLUG_OUT = 3.0                # the plug body stands this far past the board edge. ESTIMATE
HB_PLUG_IN = 9.0                 # the plug body reaches this far onto the board from the edge. ESTIMATE
# Top-entry XH sockets: name, u0, u1, v0, v1. ESTIMATE (read from the photo).
HB_XH = [("BL_T", 1.0, 16.0, 0.0, 6.5), ("TH", 17.0, 24.0, 0.0, 6.5), ("HEAT", 16.5, 24.5, 10.0, 18.0),
         ("E", 25.0, 35.0, 10.0, 16.0), ("K_FAN", 25.0, 32.0, 0.0, 6.5), ("X", 25.0, 35.0, 17.0, 23.0),
         ("X-", 33.0, 40.0, 0.0, 6.5)]
HB_USED = ("X", "X-", "BL_T")    # the X motor, the X endstop, the pen servo (3-wire pigtail)

# Base board (the Y/Z breakout). It sits on the outer (back) face of the back bar.
BB_PCB = (41.0, 30.0)            # u, v. ESTIMATE
BB_HOLES_U = (3.15, 37.85)       # the two M3 holes (u), 34.7 mm apart. ESTIMATE
BB_HOLES_V = 16.0                # the hole line, from the JST edge (v). ESTIMATE
BB_HDR_U = (7.0, 34.0)           # the 2x8 Micro-Fit plug body (u). ESTIMATE
BB_PLUG_OUT = 25.0               # the plug body and latch stand this far past the board edge. ESTIMATE
BB_PLUG_IN = 7.0                 # the plug body reaches this far onto the board. ESTIMATE
BB_XH = [("Z-", 0.0, 7.0, 5.0, 12.5), ("Z1", 8.0, 15.0, 0.0, 12.5), ("Z2", 16.5, 23.5, 0.0, 12.5),
         ("Y", 25.0, 32.0, 0.0, 12.5), ("Y-", 33.5, 41.0, 3.5, 11.5)]
BB_USED = ("Y", "Z1", "Y-", "Z-")  # Y1 motor, Y2 motor, Y1 endstop, Y2 endstop

# Shared plug and wire sizes.
BRK_PCB_T = 1.6                  # board thickness
BRK_TAILS = 2.0                  # solder tails under the board. ESTIMATE
MF_PLUG_H = 10.0                 # Micro-Fit plug height above the board. ESTIMATE
MF_CABLE = 35.0                  # the round cable runs straight this far before it can bend. ESTIMATE
MF_CABLE_D = 9.0                 # cable diameter (head). ESTIMATE
XH_H = 17.0                      # mated XH plug height above the board. ESTIMATE
XH_BEND = 12.0                   # the wires need this much more height to bend. ESTIMATE

# The standoffs: the board back face is this far off the extrusion face.
BRD_STANDOFF = 4.0               # 4 mm nylon M3 standoff: the solder tails (2 mm) clear the extrusion
BRD_STANDOFF_D = 5.5             # its outside diameter. ESTIMATE

# Where they mount. The big plug points up. The hole line of each board is on the middle of the upper
# slot lip of the extrusion face, so the standoffs stand on the face (the slot opening is 6.2 mm).
BRD_LIP_DZ = (6.2 / 2 + 10.0) / 2    # the middle of the upper slot lip, above the centre of a 2020 face
HB_X0 = 96.0                     # the head board, left edge (frame x), on the back face of the beam
HB_Z0 = BEAM_Z0 + BEAM / 2 + BRD_LIP_DZ - HB_HOLES_V   # the head board, lower edge (frame z)
BB_X0 = 71.0                     # the base board, left edge (frame x), on the back face of the back bar
BB_Z0 = BAR_SLOT_Z[0] + BRD_LIP_DZ - BB_HOLES_V        # the base board, lower edge (frame z)

# The stock CR-10 V3 control box (the v2.5.2 board, the 350 W supply, the LCD and the knob). It stands
# on the table, left of the frame. Only the images use it. ESTIMATE: x (with the LCD on the front), y, z.
CTRL_BOX = (290.0, 210.0, 85.0)

# ---- Y drive: a fixed belt on each rail, and an omega drive on each Y carriage ----
# Each Y belt lies on the top face of its 2040 rail, over the inner top slot (the top wheels use the
# outer slot). Teeth down. The V of the slot (model value) is narrower than the 6 mm belt, so the
# belt lies on the slot lips, not in the slot. The two ends hold in crimp clips: in a tensioner at
# the front end, in an anchor at the back end. The Y motor rides on its carriage, behind the beam.
# The belt leaves the rail under a smooth idler, goes up and over the motor pulley (180 degrees of
# wrap), down under a second idler, and back onto the rail. Left side; the right is the mirror image.
YB_X = SLOT_IN_X + 1.5           # the belt centre (x): over the inner top slot of the rail. 1.5 mm inward, so
                                 # the button heads of the idler axles clear the bolt tips of the top wheels
YB_Z = RAIL_TOP_Z + BELT_T / 2   # the belt centre (z) on the rail top
SIDLER_R = 6.0                   # smooth (toothless) GT2 idler, 5 mm bore, 6 mm belt: belt face 12 mm across. ESTIMATE (retail value)
SIDLER_FL = 9.0                  # its flange radius: 18 mm across. ESTIMATE (retail value)
OMEGA_Y = 33.0                   # the motor pulley, from the beam centre (y): the motor is 0.85 mm behind the beam
OMEGA_PZ = 88.75                 # the motor pulley axis (z): the lower motor screws clear the idler bosses
OMEGA_IZ = RAIL_TOP_Z + 0.5 + SIDLER_FL                  # the idler axles (z): the flanges clear the rail top
OMEGA_IDY = BELT_RUN + SIDLER_R + BELT_T / 2           # the idlers, each side of the pulley (y): the belt runs vertical
OMEGA_X = (YB_X - IDLER_H / 2, YB_X + IDLER_H / 2)       # the idlers and the pulley teeth (x)
# The drive mount (y_drive): a plate for the motor face, an arm over the omega, and a back plate on
# the back face of the tower. It prints on the motor face.
DRV_PLATE_X = (YB_X + 11.5, YB_X + 17.5)   # the motor plate (x). The motor face is on its +x side
DRV_ARM_X0 = YB_X - 5.0          # the arm over the omega starts here (x)
DRV_BACK_X0 = -10.0              # the back plate on the tower, from here (x)
DRV_Y = (10.5, 55.0)             # the plate (y from the beam centre)
DRV_Z = (62.0, XTOWER_TOP)       # the plate (z)
DRV_ARM_Z0 = OMEGA_PZ + MOTOR / 2 + 0.6                  # the arm underside: over the motor
DRV_BACK_T = 5.0                 # the back plate thickness (y)
DRV_SCREWS_X = (0.0, 18.0)       # the two M3 screws into the tower back face (x)
DRV_BOSS_D = 7.0                 # the idler bosses: they touch the inner race through a washer
YAXLE_L = 20.0                   # the M5 idler axles: they cut their own thread in the plate
# The front end: a base on the front bar and the rail end (two M5 screws in the top slot of the bar),
# with the Y endstop, and a tensioner (a sled with the clip pocket) in a channel of the base. An M3
# screw through the front wall of the base pulls the sled forward.
YF_Y1 = 35.0                     # the base reaches this far back (y): the carriage plate comes to y 35.5
YF_X = (2.0, 52.5)               # the base on the bar (x)
YF_CH = (YB_X - 6.9, YB_X + 6.9)   # the channel for the sled (x); its walls are 1.5 mm (the pen clamp screw comes to x 40.4)
YF_WALL = 8.0                    # the front wall of the base (y), with the M3 counterbore
YF_TOP = RAIL_TOP_Z + 1.0 + CLIP_POCKET[2]               # the top of the base and the sled (z)
YF_SCREWS_X = (12.0, 44.5)       # the two M5 screws into the top slot of the front bar (x)
YS_SLED = (15.5, CLIP_POCKET[0] + CLIP_LOOP, 4.0)        # the sled: front block, pocket, back wall (y)
YS_TRAVEL = 3.5                  # the sled moves this far each way: a hand crimp error and the belt stretch
YF_Y0 = YF_Y1 - sum(YS_SLED) - 2 * YS_TRAVEL - 8.0   # the front of the base (y): 21 mm in front of the front bar
YS_CLR = 0.4                     # the gap around the sled in the channel
TENSION_SCREW_L = 20.0           # the M3 tension screw
# The back end: a block on the back face of the back bar (two M5 screws into T-nuts in the face
# slot). The belt runs over the bar top into the block. The omega idlers roll over the bar top.
YR_Y0 = FRAME_Y + 1.5            # the front of the clip wall, over the bar top (y): the back idler stops 0.8 mm short
YR_Y1 = YR_Y0 + CLIP_WALL + CLIP_POCKET[0] + CLIP_LOOP + 0.9   # the back of the block (y)
YR_X = (YB_X - 14.5, 66.0)        # the block (x): it reaches right, clear of the bar end screw heads, for 5 mm of material round each screw hole
YR_SCREWS_X = (45.0, 58.0)       # its two M5 screws (x): right of the bar end screw heads at x = 10 and 30
YR_Z0 = RAIL_TOP_Z - BAR_H       # the block reaches down the back face to the bar bottom
# The Y endstop: on the base, beside the rail slot. The front face of the X motor wall of the carriage
# pushes the lever.
YSW_X = (4.0, 4.0 + 6.4)         # the switch body (x): its thickness
YSW_Y1 = 35.0                    # the switch body ends here (y); the lever reaches about 3 mm further
ANCHOR_FLOOR = 6.0               # the floor under the M5 heads of the front base and the back anchor
ANCHOR_POCKET_FLOOR = 1.0        # the floor of the Y clip pockets, over the bar and rail tops
TENSION_Z = RAIL_TOP_Z + 4.0     # the M3 tension screw (z): under the belt that runs over the sled wall
M3_HEAD = SOCKET["M3"]
M5_PILOT = 4.3                   # pilot for an M5 screw that cuts its own thread (the idler axles). ESTIMATE

# ---- Y carriage on side wheels ----
# A 6 mm plate over the rail top. Three V-wheels on vertical axles run in the side slots of the flat
# 2040 rail: two in the outer side slot (22 mm in front of and behind the beam centre), one in the
# inner side slot at the beam centre. Nothing goes under the rail, so the feet do not limit the travel.
# The back outer wheel sits on the eccentric spacer. Outer wheels: the bolt head under the wheel, a
# spacer, the plate, a nyloc nut on top. Inner wheel: a button head in a counterbore of the tongue,
# a spacer, the wheel, a nyloc nut under it. The plate stays outside the belt (x < YB_X - 3). A tongue
# crosses over the belt in front of the X plate (a channel with a pointed roof) and runs back under the
# X plate to the inner wheel. It prints upright, the plate on the bed.
YW_Z = RAIL_TOP_Z - RAIL_H / 2   # the centre of the side slots and the wheels (z)
YW_OUT_X = -WHEEL_OFF            # the outer wheel axles (x)
YW_IN_X = RAIL_W + WHEEL_OFF     # the inner wheel axle (x)
YW_ECC = 1                       # the back outer wheel is on the eccentric spacer
YP_Z0 = YW_Z + WHEEL_T / 2 + SPACER_H   # the plate underside: a 6 mm spacer over the wheels
YP_T = 6.0
YP_Z1 = YP_Z0 + YP_T
YP_X1 = 28.0                     # the plate ends here (x), 0.5 mm outside the belt; the tower ends here too
YT_CROSS_Y1 = -17.0              # the crossing over the belt, from the X motor wall back to here (y from the beam centre)
YT_CROSS_TOP = 72.0              # its top (z): in front of the X plate there is room
YT_CH = (YB_X - 4.0, YB_X + 4.0) # the belt channel under the crossing (x)
YT_CH_Z = 62.5                   # the channel walls go up to here; then a 45 degree roof
YT_LEG_X = (38.0, 45.5)          # the leg under the X plate (x): the pen carriage comes to x = 49.9 (left) and 46.2 (right, mirrored)
YT_BOSS_R = 8.0                  # the boss around the inner axle
INNER_CB = (10.5, 3.0)           # the counterbore for the button head of the inner axle: diameter, depth
OUT_AXLE_L = 35.0                # M5 x 35: the eccentric wheel axle (wheel, spacer, plate, 6 mm boss, nut)
IN_AXLE_L = 30.0                 # M5 x 30 button head: the inner wheel axle

# ---- Moving cables (kept low: no post, no overhead loop) ----
# Y: one openable drag chain beside the left rail, outside the frame. It carries the head harness and
# the two Y motor cables (the right one runs along the back of the beam to the left carriage). The chain
# loops in a vertical plane: the lower run lies on the table, the upper run is bolted to the side of a
# tab on the left carriage plate, the bend is at the front. The fixed end sits in an anchor at the back
# left corner, where the cables go on to the control box and the base board. Change these values to
# use another chain.
YCH_INNER = (10.0, 20.0)         # inner height and width of the chain to buy
YCH_OUTER = (15.0, 27.0)         # outer height and width. ESTIMATE (measure the chain)
YCH_R = 28.0                     # bend radius at the centre line of the chain (R28)
YCH_OPEN = True                  # openable links: the big harness plug does not pass a bridge link
YCH_X = -50.0                    # the centre of the chain (x)
YCH_ZL = YCH_OUTER[0] / 2        # the centre of the lower run: on the table (z)
YCH_ZU = YCH_ZL + 2 * YCH_R      # the centre of the upper run (z)
YCH_TAB_Y = (16.0, 36.0)         # the tab on the left carriage plate for the moving end (y from the beam centre)
YCH_TAB_X0 = YCH_X + YCH_OUTER[1] / 2 + 0.5   # the outer face of the tab (x): the end link bolts to it
YCH_END = 12.0                   # length of an end link with its bracket (y). ESTIMATE
YCH_FIX_Y = 492.0                # the fixed end of the lower run (y): the back left corner
YCH_ANCHOR_Y = (480.0, 512.0)    # the anchor block on the table (y)
YCH_ARM_Y = (482.0, 494.0)       # its arm to the bottom outer slot of the rail (y); the back foot ends at x 16.5
# X: the servo lead on a thin band. The band values are in the "X band" block near the end of this file.
YCH_RUNS = 394.0                 # the two runs together (y): the fixed end to the moving end at the front of the travel
YCH_ARM_SCREWS = (492.0,)  # the two M5 screws of the anchor arm into the bottom outer slot of the rail (y)
YCH_LINK_WALL = 2.0              # the side wall of a chain end link (x), under the M3 heads. ESTIMATE

# ---------------------------------------------------------------------------
# The design language of the printed parts (parts.finish).
EDGE_R = 2.0     # one radius on each outside corner that stands up in the print
EDGE_CH = 0.6    # one chamfer on each outside edge of a top face in the print
ACCENT = "#E8772E"   # one colour for all printed parts
SLOT_OPEN = 6.2      # the slot opening of the 2020 bars. ESTIMATE (V-slot data sheet)

# ---------------------------------------------------------------------------
# One-piece omega carriage (the Y carriages were too complex). The drive mount is
# now part of the Y carriage: the motor bolts straight to it, the idlers run on M5 bolts in its bosses.
DRV_FLOOR_X0 = 38.0               # the floor under the motor plate, from the leg (x): clear of the idler flanges (35.75)
DRV_WEB_Y = (10.5, XTOWER_HALF_Y) # the web from the tower to the motor plate (y from the beam centre)
DRV_WEB_APEX = RAIL_TOP_Z + 0.5 + 2 * SIDLER_FL + 1.5   # the low point of its V underside (z): over the front idler flange
MOTOR_SCREWS = ((-1, 1), (1, 1))  # the two top M3 motor screws (sign of y, sign of z): the motor hangs on them; its boss locates it
# Heat-set inserts: the front outer wheel axle goes into an M5 insert in a boss on the plate (no nut
# in the narrow gap between the motor wall and the tower). M5 x 5.8 short insert (CNC Kitchen / Ruthex style).
INSERT_M5 = {"od": 7.0, "len": 9.5, "hole": 6.4, "depth": 10.5}   # long M5 insert: the screw goes through it
INSERT_BOSS = (14.0, 6.0)         # the boss around the insert: diameter, height above the plate (12 mm of support with the plate)
FRONT_AXLE_L = 30.0               # M5 x 30: the front outer wheel axle through the long insert

# ---------------------------------------------------------------------------
# Real hardware shapes (ISO 4762 socket head, ISO 7380 button head, ISO 4032 nut, ISO 7040 nyloc).
HEX_KEY = {"M3": (2.5, 1.3), "M5": (4.0, 2.5), "M6": (5.0, 3.0)}   # socket head: key size, socket depth
BUTTON_KEY = {"M5": (3.0, 1.3)}  # button head: key size, socket depth
NYLOC_HEX = 0.72                 # nyloc: the hex part, as a part of the height; the collar with the nylon ring is above
ECC = {"af": 11.0, "h": 6.0, "shank_d": 7.1, "off": 0.79}   # stock eccentric spacer: hex, height, shank, offset. ESTIMATE

# ---------------------------------------------------------------------------
# X idler fork (the X idler bolt had too little material round its hole). The 20T idler runs
# between the two cheeks of a printed fork, on an M5 x 30 bolt through both cheeks with a nyloc nut.
# The fork slides along X on the top of the right tower, between the carriage wall and a rail. An
# M3 x 25 screw through an end wall pulls the fork outward: that sets the X belt tension.
XIDLER_TRAVEL = (-4.0, 3.0)        # the fork travel from the middle (dx; -dx tightens the belt)
FORK_HOLE_WALL = 5.5               # material around the axle hole in each cheek, all directions
FORK_FRONT_T = 5.95                # the front cheek (it also guides on the carriage wall)
FORK_BACK_T = 5.0                  # the back cheek
FORK_WASHER = 1.0                  # an M5 washer each side of the idler
FORK_HALF_X = M5_CLEAR / 2 + FORK_HOLE_WALL      # the fork, each side of the axle (x)
FORK_Y = (XBELT_DY - IDLER_H / 2 - FORK_WASHER - FORK_FRONT_T, XBELT_DY + IDLER_H / 2 + FORK_WASHER + FORK_BACK_T)
FORK_Z0 = XTOWER_TOP               # it slides on the tower top
FORK_BASE_TOP = XPULLEY_Z - 9.0 - 1.0              # under the idler flange
FORK_TZ = FORK_Z0 + 6.0                           # the tension screw (z), in the tail
FORK_CLR = 0.3                     # the slide gap each side
FORK_TAIL = 14.0                  # the tail of the fork, outside the idler: it holds the tension screw and its nut
FORK_TAIL_H = 12.0                # its height: 3 mm of material round the M3 hole
FORK_EW_X1 = XIDLER_X + XIDLER_TRAVEL[0] - FORK_HALF_X - FORK_TAIL - 1.0   # the end wall for the tension screw (x)
FORK_EW_T = 5.0
XIDLER_AXLE_L = 30.0               # M5 x 30 through both cheeks: the same screw as the wheel axles
XTENSION_L = 20.0                  # M3 x 20 tension screw: it stays in the tail of the fork
DRV_BOSS_BIG = 16.0               # the omega idler bosses behind the shoulder: 5 mm of material round the M5 pilot
HOLE_WALL_K = 1.0                 # the hole check: material round each screw hole, 1 x d radially
HOLE_FILL_MIN = 0.85              # ... at least this part of that ring must be material (chamfers, edges)
YCH_TAB_Z1 = YP_Z0 + 10.0        # the chain tab: 10 mm thick, 3 mm of material round each M3 pilot
YCH_TAB_ZS = (YP_Z0 + YCH_TAB_Z1) / 2
YSW_TAB_T = 6.0                   # the switch tab on the front base: the M2 x 12 screw has 5.6 mm of thread
XSW_PILOT = 5.7                   # the X switch pilots in the motor wall
COLLAR_EAR = 11.0                 # the pole foot collar ears reach this far behind the socket (y)

# ---------------------------------------------------------------------------
# Endstops: the stock Creality endstop BOARDS (one board is measured). Board frame: u from the plug
# edge to the switch edge, v along the edges, w up from the back of the board (the parts side).
ES = {"pcb": (20.07, 20.05, 1.6),                               # measured (context_detail.EB)
      "holes_u": 3.26, "holes_v": (2.525, 17.525), "hole_d": 3.2,  # 2 x M3, 15 mm apart, 3.26 mm from the plug edge (measured)
      "plug": (-0.0, 4.0, 16.0, 7.5),                            # JST XH 3-pin: at u < 0 side, v 4..16, height (w)
      "plug_zone": (-20.0, 4.0, 16.0, 9.5),                       # the plug and the wire bend: u from -20 to 0, v, w top
      "switch": (14.27, 20.07, 4.7, 17.5, 8.1),                   # KW12 body 5.8 x 12.8 x 6.5: u0, u1, v0, v1, w top (EB)
      "lever": ((20.07, 17.5), (21.2, 0.3), 2.5, 5.5),            # the flat lever, pressed to the click: (u, v) to (u, v), w0, w1
      "click": (21.07, 2.0, 4.0),                                 # the trigger meets the lever here: 1.0 mm out (measured), 2 mm from the corner
      "pins": 2.5}                                                # pins and screw ends under the board
ES_OVERTRAVEL = (1.0, 2.0)        # the trigger goes this far past the click at the hard stop (ESTIMATE)
ES_STANDOFF = 4.0                 # standoffs under the board: room for the pins
ES_STANDOFF_D = 9.0               # 3 mm of material round an M3 pilot (X board), clear of the plug pins
INSERT_M3 = {"od": 4.6, "len": 5.7, "hole": 4.0, "depth": 7.0}   # M3 heat-set insert (CNC Kitchen / Ruthex style)
ES_SCREW_Y = 8.0                  # M3 x 8: a Y endstop board into its inserts
ES_SCREW_X = 10.0                 # M3 x 10: the X endstop board, self-tapping into the standoffs of the motor wall
ES_Y_ORIGIN = (22.5, 16.8)        # the left Y board: the corner (u 0, v 0) at frame x, y; v runs to -x
ES_Y_RIGHT_ORIGIN = 397.5         # the right Y board: the same rotation (a board is not mirror symmetric)
ES_X_ORIGIN = (10.85, 130.0)      # the X board on the back of the motor wall: the corner at frame x, z; v runs to -z
YSTRIKER = (0.5, 3.5)             # the striker meets the lever over this stretch of the board edge (v): clear of the switch body
YC_HOME = 73.94                  # the gantry y at the front stop (from the fit check; the strikers use it)
ES_STANDOFF_DY = 9.0              # the Y board standoffs round the M3 inserts
WASHER_SMALL = (7.5, 1.0)         # M5 washer, 7.5 mm across: it bears on the inner race of an idler only
INNER_BOSS_TOP = 66.2             # the inner wheel boss reaches up to here: 0.5 mm under the stock X plate
FORK_CHEEK_UP = 2.0               # the cheeks of the X idler fork reach this much higher than a round top
ECC_BOSS_D = 18.0                 # the boss round the eccentric hole: 5 mm of material round the 7.5 mm hole

# ================================================================ fixed motors, stock X belt path (2026-11-09)
# The X axis keeps the stock CR-10 V3 layout, with printed plates and a printed carriage. The Y motors
# are fixed, so the X axis stays light. The Y rail slot ends are closed by the 2020 bars: no belt goes
# through a slot end.
#
# X (the stock CR-10 path, read from the Creality CR-10 STEP model): the pulley axis lies along Y on
# the beam centre line, past the left beam end. The belt lies flat (its width along Y). One run lies in
# the channel of the TOP slot of the beam, one in the channel of the BOTTOM slot, 3.94 mm deep, under
# the V-wheel tips. The X carriage clamps the bottom run: at each end of the carriage the belt leaves
# the bottom slot at 45 degrees into a crimp clip pocket under the beam. The X motor stands behind the
# left beam end (shaft to the front), on a wall of the left Y carriage tower. A toothed 20T idler in a
# two-cheek fork sits past the right beam end. An M3 screw from outside the right end pulls the fork.
BZ = BEAM_Z0 + BEAM / 2          # the beam centre (frame z)
XB_DEPTH = BEAM / 2 - BELT_RUN   # the belt centre under the face of the top and bottom slots: 3.94 mm
XB_RUNS = (BZ - BELT_RUN, BZ + BELT_RUN)   # the bottom (clamped) run and the top (return) run (frame z)
XB_Y = 0.0                       # the belt centre (width along y), from the beam centre plane
SLOT_CH_W = 11.0                 # the slot channel of the 2020 beam, behind the lips: width. ESTIMATE (V-slot data sheet)
SLOT_CH_FLAT = 4.0               # ... the channel walls are straight to this depth, then 45 degrees to the core. ESTIMATE
WHEEL_TIP_DEPTH = WHEEL_D / 2 + WHEEL_TIP - WHEEL_OFF   # the wheel tip goes this far into its slot (model): 2.6 mm
XM_X = BEAM_X0 - 12.0            # the X pulley axis (frame x): 4.5 mm from the flange to the beam end
XM_FACE_DY = PULLEY["flange_t"] * 2 + PULLEY["teeth_w"] / 2 + PULLEY["hub_l"] + 0.5   # the motor face, behind the beam centre (y)
XM_WALL = (XM_FACE_DY - 7.2, XM_FACE_DY)  # the motor wall of the left tower (y from the beam centre): the face on its back
XM_SCREW_CB = 1.5                # the counterbore of the M3 motor screws in the front face of the wall
XI_X = FRAME_X + 21.0            # the X idler axis at the middle of its travel (frame x; 400 - 21 in the left model)
XIDLER_X = FRAME_X - XI_X        # ... in the left model (the right carriage is the mirror image): -21
XIDLER_TRAVEL = (-4.0, 2.5)      # the fork travel (left model dx; -dx goes outward and tightens the belt)
FORK_WASHER = 1.0                # an M5 washer each side of the idler
FORK_FRONT_T = 5.95              # the front cheek
FORK_BACK_T = 5.0                # the back cheek
FORK_Y = (XB_Y - TIDLER["h"] / 2 - FORK_WASHER - FORK_FRONT_T, XB_Y + TIDLER["h"] / 2 + FORK_WASHER + FORK_BACK_T)
FORK_R = M5_CLEAR / 2 + 5.5      # the cheek round the axle: 5.5 mm of material
FORK_FLOOR = (XB_RUNS[0] - BELT_T / 2 - 1.5 - 5.0, XB_RUNS[0] - BELT_T / 2 - 1.5)   # the floor under the bottom run (z)
FORK_TAIL = (BELT_RUN + BELT_T / 2 + 1.5, BELT_RUN + BELT_T / 2 + 1.5 + 8.0)   # the tail outside the belt wrap (from the axle, outward)
FORK_CLR = 0.3                   # the slide gap each side
FORK_EW = (FORK_TAIL[1] - XIDLER_TRAVEL[0] + 1.0, FORK_TAIL[1] - XIDLER_TRAVEL[0] + 6.0)   # the end wall (from the axle, outward)
XTENSION_L = 20.0                # M3 x 20 tension screw: through the end wall into the nut in the tail
XIDLER_AXLE_L = 30.0             # M5 x 30 through both cheeks
BEAM_TNUT_X = 14.0               # the M5 screw from the back of the tower into a T-nut in the back slot of the beam (frame x)
BEAM_STOP_T = 2.6                # the stop walls in each tower, against the beam end (x), beside the belt runs

# The printed X plate (plate frame, see the top of this file). It replaces the stock Creality plate:
# the same 3 V-wheels, the same 4 tool head holes for the pen carriage, the same front face (y 0). It
# prints upright. The eccentric moves to the top right wheel (reachable from above).
XP_T = 3.0                       # the plate (y 0 to XP_T): 0.6 mm in front of the beam face
PLATE_SHEET = XP_T               # the head screws start at the back of the plate
XP_X = (-41.92, 55.0)            # the plate ends (x): the left end is the hard stop at the left tower
XP_Z = (-3.6, 64.0)              # the plate (z)
X_WHEELS = [("top left", -15.58, 48.23), ("top right", 29.02, 48.23), ("bottom", 6.92, 7.73)]
X_ECC = 1                        # the top right wheel is on the eccentric spacer
XW_BOSS_R = 8.0                  # the wheel bosses
XW_BOSS_Y = {0: (-5.2, PLATE_FRONT - WHEEL_T / 2 - SPACER_H),  # the fixed top wheel: a stock 6 mm spacer, then the boss; the nut in front
             1: (-9.5, PLATE_FRONT - WHEEL_T / 2 - ECC["h"]),  # the eccentric top wheel: the hex between the boss and the wheel
             2: (-8.0, PLATE_FRONT - WHEEL_T / 2 - SPACER_H)}  # the bottom wheel: a stock 6 mm spacer; a long M5 insert in the front of the boss
XW_AXLE_L = {0: 30.0, 1: 35.0, 2: 25.0}   # M5 socket head axles, the head behind the wheel
X_TRIGGER = (-40.0, -33.0, 57.0, 72.0, 10.0)   # the X endstop trigger lug: x0, x1, z0, z1, depth in front of the plate
XCL_SLANT = 45.0                 # the belt leaves the bottom slot at this angle into the clip pocket
XCL_WALL_U = 12.6                # the clip wall starts this far along the slant from the slot exit point
XCL_BACK = PLATE_FRONT + 8.6     # the clamp blocks under the beam reach back to here (y); the pockets open to the back
KEEP_R = XW_BOSS_R + 0.5         # the pen carriage keeps this far from each wheel axle

# Y: fixed motors. Each Y belt is a loop over the inner top slot of its rail, flat (width along x). The
# lower run passes 1 mm over the rail top and the bar tops; the upper run is clamped by the carriage.
# The motor stands behind the back bar (a printed bracket on the back face, two T-nuts); a toothed 20T
# idler in a fork stands in front of the front bar (on the front base, with the Y endstop board).
YB_LOW = RAIL_TOP_Z + 1.0 + BELT_T / 2   # the lower run (z)
YB_HIGH = YB_LOW + 2 * BELT_RUN          # the upper run (z), clamped by the carriage
YB_AX = YB_LOW + BELT_RUN                # the pulley and idler axes (z)
YM_Y = FRAME_Y + 5.0 + 0.85 + MOTOR / 2  # the Y pulley axis (y): the motor clears the bar end screw heads
YM_FACE_X = YB_X - PULLEY["teeth_w"] / 2 - PULLEY["flange_t"] - 0.5 - 6.0   # the motor face (x); a 6 mm plate, the hub to +x
YM_PLATE_T = 6.0
YM_SCREWS_X = (46.5, 59.0)       # the two M5 screws of the motor bracket into T-nuts in the back face slot of the back bar
YI_Y = -12.0                     # the Y idler axis at the middle of its travel (y)
YIDLER_TRAVEL = (-4.0, 3.0)      # dy: -dy moves the fork forward and tightens the belt
YFORK_Y = (YI_Y - FORK_R, YI_Y + FORK_R)
YFORK_X = (YB_X - TIDLER["h"] / 2 - FORK_WASHER - 5.0, YB_X + TIDLER["h"] / 2 + FORK_WASHER + 5.0)  # cheeks 5 mm
YFORK_FLOOR = (YB_LOW - BELT_T / 2 - 1.0 - 5.0, YB_LOW - BELT_T / 2 - 1.0)
YFORK_TAIL = (BELT_RUN + BELT_T / 2 + 1.5, BELT_RUN + BELT_T / 2 + 1.5 + 7.0)   # in front of the belt wrap (from the axle)
YFORK_EW = (YFORK_TAIL[1] - YIDLER_TRAVEL[0] + 1.0, YFORK_TAIL[1] - YIDLER_TRAVEL[0] + 6.0)
YTENSION_L = 20.0
YCL_FRONT = (-42.0, -38.0)       # the front clamp block: the clip wall (y from the beam centre); the pocket behind it
YCL_BACK = (40.0, 36.0)          # the back clamp block: the clip wall; the pocket in front of it
YCL_X = (YB_X - 7.5, YB_X + 7.5) # the clamp blocks (x)
YCL_TOP = YB_HIGH + CLIP_POCKET[2] / 2 + 1.5   # the top of the clamp blocks (z)
YW_IN_DY = 18.0                  # the inner wheel, behind the beam centre: clear of the X plate (it reaches y +8.4)
IN_BOSS = 12.0                   # the inner wheel boss over the plate: 12 mm of support, the head on top
YF_X = (2.0, 52.5)               # the front base on the bar
YF_CH_Y1 = 30.0                  # the front base stops here over the belt (y): the front clamp block comes to 31.9 at home
# The pen carriage on the printed X plate: the clamp block of the old X belt is gone, so the spine and
# the top band reach up to z 66 (6 mm of material over the T1 and T2 holes). It keeps 0.5 mm from the
# wheel bosses of the plate (the bosses come forward through it).
BASE_RECTS = [
    (-12.0, -0.5, -7.0 - DROP, 66.0),   # the spine behind the rail
    (-12.0, 20.0, 38.0, 66.0),          # the top band
    (14.0, 37.5, -2.0 - DROP, 42.0),    # the right arm: H1 and the servo
    (-20.5, 10.5, -7.0 - DROP, 0.0 - DROP),    # the shelf, at the bottom
]
WHEEL_BOLTS = [(n, x, z, XW_BOSS_R) for n, x, z in X_WHEELS]   # keep-outs for the pen carriage: the bosses
HEAD_SCREW_L = {"T1": 12.0, "T2": 12.0, "H1": 12.0, "H2": 12.0}   # M3 from the back of the plate
XP_THICK = 5.0                   # the plate is 5 mm thick above and below the beam (y 0 to 5); 3 mm in front of the beam
PLATE_SHEET = XP_THICK           # the head screws start at the back of the plate
XP_Z = (-10.0, 64.0)             # the plate (z): the clamp blocks reach down to z -10 (1 mm over the Y belt)
ES_SCREW_X = 8.0                 # M3 x 8: the X endstop board into M3 heat-set inserts in its standoffs (as the Y boards)
XMWALL_TOP_MOTOR = 132.0         # the X switch wall (left): over the X board (z 110 to 130)
XMWALL_TOP_IDLER = 80.0          # the striker wall (right)
FORK_BACK_T = 8.0                # the back cheek of the X fork: it holds the M3 nut of the tension screw
FORK_Y = (XB_Y - TIDLER["h"] / 2 - FORK_WASHER - FORK_FRONT_T, XB_Y + TIDLER["h"] / 2 + FORK_WASHER + FORK_BACK_T)
FORK_SCREW = (XB_Y + TIDLER["h"] / 2 + FORK_WASHER + FORK_BACK_T / 2, BZ - 5.0)   # the tension screw (y, z): in the back cheek, under the axle
FORK_NUT_X = 1.5                 # the M3 nut slot starts this far in from the outer end of the cheek
FORK_EW = (FORK_R - XIDLER_TRAVEL[0] + 1.0, FORK_R - XIDLER_TRAVEL[0] + 6.0)   # the end wall (from the axle, outward)
XTENSION_L = 16.0                # M3 x 16: the tip stays in the cheek, beside the idler, over all the travel
YFORK_X = (YB_X - TIDLER["h"] / 2 - FORK_WASHER - 5.0, YB_X + TIDLER["h"] / 2 + FORK_WASHER + 8.0)   # the outer cheek 8 mm: the nut
YFORK_SCREW = (YB_X + TIDLER["h"] / 2 + FORK_WASHER + 4.0, YB_AX - 5.0)   # the Y tension screw (x, z)
YFORK_EW = (FORK_R - YIDLER_TRAVEL[0] + 1.0, FORK_R - YIDLER_TRAVEL[0] + 6.0)   # the end wall (in front of the axle)
YTENSION_L = 20.0
YP_Y = (-38.0, 40.0)             # the Y carriage plate (y from the beam centre): to the back of the back clamp block
IN_AXLE_L = 35.0                 # M5 x 35 socket head: the inner wheel axle (the head on the 12 mm boss)
FORK_FRONT_T = 5.0               # the front cheek of the X fork: the M5 x 30 axle stands 1.5 mm out of the nut
FORK_Y = (XB_Y - TIDLER["h"] / 2 - FORK_WASHER - FORK_FRONT_T, XB_Y + TIDLER["h"] / 2 + FORK_WASHER + FORK_BACK_T)
XTENSION_L = 20.0                # M3 x 20 X tension screw (the tip stays in the back cheek over all the travel)
XW_BOSS_RS = {0: 9.0, 1: 10.5, 2: 6.9}   # the wheel bosses (the bottom one round the long M5 insert: 3.7 mm wall)
WHEEL_BOLTS = [(n, x, z, XW_BOSS_RS[i]) for i, (n, x, z) in enumerate(X_WHEELS)]   # pen carriage keep-outs (teardrops)
IDLER_R = TIDLER["flange_d"] / 2  # the idler flange radius: the forks and the pockets clear it
FORK_FLOOR = (BZ - IDLER_R - 0.5 - 5.0, BZ - IDLER_R - 0.5)    # the X fork floor, under the idler flange
FORK_EW = (IDLER_R - XIDLER_TRAVEL[0] + 1.0, IDLER_R - XIDLER_TRAVEL[0] + 6.0)   # the end wall (from the axle, outward)
YFORK_FLOOR = (YB_AX - IDLER_R - 0.5 - 5.0, YB_AX - IDLER_R - 0.5)
YFORK_EW = (IDLER_R - YIDLER_TRAVEL[0] + 1.0, IDLER_R - YIDLER_TRAVEL[0] + 6.0)
X_TRIGGER_CH = 1.5                # the 45 degree chamfer on the lower left edge of the trigger lug: it clears the switch body
X_WHEELS = [("top left", -18.5, 48.23), ("top right", 29.02, 48.23), ("bottom", 6.92, 7.73)]   # the top left wheel 2.9 mm left of the stock place: its 9 mm boss clears the dovetail rail of the pen carriage
WHEEL_BOLTS = [(n, x, z, XW_BOSS_RS[i]) for i, (n, x, z) in enumerate(X_WHEELS)]
YI_Y = -17.0                     # the Y idler axis at the middle of its travel (y): the fork stays 0.8 mm in front of the bar end screw heads
# The tension screw and its nut sit low in the thick cheek of each fork, under the ring of material round the axle;
# the nut goes in from below (the fork floor is 10.5 mm thick).
FORK_FLOOR = (BZ - 20.0, BZ - IDLER_R - 0.5)
FORK_SCREW = (XB_Y + TIDLER["h"] / 2 + FORK_WASHER + FORK_BACK_T / 2, BZ - 14.0)
YFORK_FLOOR = (YB_AX - 20.0, YB_AX - IDLER_R - 0.5)
YFORK_SCREW = (YB_X + TIDLER["h"] / 2 + FORK_WASHER + 4.0, YB_AX - 14.0)
YCL_X = (YB_X - 7.5, XMWALL_X1)  # the clamp blocks (x): to the end of the front wall (the wall stands on the block)
YLIP = (4.0, 10.0)               # the two lips of the front base over the idler bracket: thickness (z), reach in front of the bar (y)
YBRK_SCREW_L = 12.0              # M3 x 12: each lip to the idler bracket (4 mm lip, 8 mm of thread)
X_TRIGGER_CH = 0.5                # the 45 degree chamfer on the lower left edge of the trigger lug: it clears the switch body

# ================================================================ X servo loom (2026-11-10)
# The servo lead (3 wires) runs in a split wire loom from the head board to the X plate. The loom hangs
# in a free slack loop behind the beam. One cable tie at each end holds it: at the fixed end to the head
# harness cable over the head board, at the moving end through a slot at the top left of the X plate.
# No printed holder carries it. From the moving end the loom goes up over the X plate top and back over
# the beam into the loop. The loop hangs in a plane behind the mated XH plugs of the head board; at the
# fixed tie the tie pulls the loom to the harness cable, above the XH plugs.
LOOM_D = 12.7                    # 1/2 inch split wire loom (on hand)
LOOM_Y = BEAM / 2 + BRD_STANDOFF + BRK_PCB_T + XH_H + LOOM_D / 2 + 1.0   # the loop plane, from the beam centre (y): behind the mated XH plugs of the head board
LOOM_Z = PLATE_DZ + XP_Z[1] + LOOM_D / 2 + 1.0   # the loom centre over the X plate top and at both loop ends (z)
LOOM_DX = -33.0                  # the moving end, from the X plate origin (x): the tie slot at the top left
LOOM_TIE = (-37.0, -31.0, 54.0, 57.0)   # the tie slot through the X plate: x0, x1, z0, z1 (plate frame)
LOOM_FIX_X = HB_X0 + HB_PCB[0] - sum(HB_HDR_U) / 2   # the fixed end (x): the tie round the head harness cable over the big plug
LOOM_MARGIN = 25.0               # slack over the longest chord of the loop
LOOM_FIX_DOWN = 30.0             # the servo lead from the fixed tie down to the BL_T socket of the head board (loom length)

# ================================================================ flat Y plates (2026-11-10)
# The build uses no stock plates. The printed plates keep the stock layouts, without the extra mounting
# points of the stock plates. Each Y carriage is a flat 6 mm plate, as
# the stock CR-10 Z carriage plate (CR-10 STEP: an aluminium plate 60 x 58.5 x 5.1 mm with R3 corners and
# three wheel holes in a triangle), with only the features this plotter uses. The wheel layout stays:
# outer wheels 44 mm apart, the inner wheel 18 mm behind the beam. On the plate:
# - the wheel bosses (the front outer insert boss, the eccentric boss, the inner wheel boss on a tongue),
# - the two clamp blocks of the Y belt,
# - a beam saddle: the beam lies on it, one M5 through a short back wall into a T-nut in the back slot,
# - the Y endstop striker at the front edge,
# - left: the chain tab, the X motor bracket (one wall), the X endstop wall in front of the beam end,
# - right: the seat of the X idler fork.
YC_SADDLE_HALF_Y = BEAM / 2 + CRADLE_CLR          # the saddle under the beam (y), each side of the beam centre
YC_STOP_X0 = BEAM_X0 - CRADLE_CLR - BEAM_STOP_T   # the stop lip at the beam end (x)
YC_STOP_TOP = XB_RUNS[0] - BELT_T / 2 - 1.5       # its top: 0.5 mm under the belt channel (z)
YC_BACK_WALL_X = (2.5, 22.0)                      # the back wall for the beam screw (x): right of the X motor body
YC_BACK_WALL_TOP = BEAM_Z0 + BEAM - 0.2           # 7.2 mm of material over the M5 hole (the audit wants 5 mm), under the beam top
YC_HOLLOW_X0 = 3.0               # the tunnel under the beam, from here to the inner face (x)
YC_HOLLOW_HALF_Y = YC_SADDLE_HALF_Y - 3.0         # 3 mm walls each side
YC_HOLLOW_ROOF = 3.0             # the floor under the beam at the ridge of the roof
YC_XSW_WALL_X = (7.0, XTOWER[1])                  # the X endstop wall in front of the beam end (x)
YC_XSW_WALL_Y0 = -16.0                            # its front face (y from the beam centre); its back is the saddle face
ES_X_ORIGIN = (10.85, 88.0)      # the X board corner (u 0, v 0) at frame x, z; v runs up, the board faces the front
ES_X_BACK_DY = YC_XSW_WALL_Y0 - ES_STANDOFF       # the board back face, from the beam centre (y)
YSTRIKER_D = 10.0                # the striker on the plate front edge: its depth (y)
# The trigger lug at the bottom left of the X plate, in front of the plate: x0, x1, z0, z1 (plate frame) at
# its tip, depth in front of the plate. Its underside rises at 45 degrees from the plate face; it clears the
# front clamp block of the Y belt. The part of the lug next to the plate starts at x0 + XLUG_NOTCH: the
# board edge is there.
X_TRIGGER = (-40.0, -33.0, 18.0, 21.0, 12.4)
XLUG_NOTCH = (1.0, 8.3)          # the notch at the plate face: x width, depth (y) from the plate face
YCL_X = (YB_X - 7.5, YB_X + 7.5)  # the clamp blocks (x): no front wall stands on them now
XP_TRAVEL = (70.42, 316.34)      # the X plate origin (x) at the two hard stops (from the fit check; the servo loom uses it)
# Two 42-34 and three 42-40 steppers are on hand. The X motor rides on the gantry: it is a 42-34 (shorter
# and lighter). The Y motors are static: 42-40.
XMOTOR_L = 34.0                  # 42-34 body length
XMOTOR_MASS = 213.4              # g, a 42-34 NEMA17 (the X motor), measured
PAPER_Z = 0.0                    # the paper top (z): the table is the bed
ES_PILLAR_HALF_X = 4.0           # the X board standoff pillar, each side of the hole line (x): 2 mm round the insert hole
YC_ECC_CLEAR = 19.0              # the room over the eccentric boss of the right plate: the nyloc nut and an 8 mm wrench
