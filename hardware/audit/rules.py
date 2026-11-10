"""The limits, the materials and the load cases of the audit. Each assumed value has the word
ESTIMATE and a short source note."""

import math
import os
import re

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- screws
NOMINAL = {"M2": 2.0, "M2.5": 2.5, "M3": 3.0, "M4": 4.0, "M5": 5.0, "M6": 6.0}
PITCH = {"M2": 0.4, "M2.5": 0.45, "M3": 0.5, "M4": 0.7, "M5": 0.8, "M6": 1.0}           # ISO 261 coarse
ROOT_D = {"M2": 1.567, "M3": 2.387, "M5": 4.019, "M6": 4.773}                            # ISO 724 d3
STRESS_AREA = {"M2": 2.07, "M3": 5.03, "M5": 14.2, "M6": 20.1}                           # ISO 898-1, mm2
CLEAR_ISO = {"M2": 2.4, "M3": 3.4, "M5": 5.5, "M6": 6.6}                                 # ISO 273 medium
STEEL_YIELD = 640.0     # MPa, property class 8.8 (ISO 898-1). Class 4.8 stock bolts: 340 MPa.

# 1. Hole meat: the material round each hole, radially, as a multiple of d.
MEAT_K = 1.0            # the design rule: M2 >= 2, M3 >= 3, M5 >= 5 mm
MEAT_CLEAR_FAIL_K = 0.5 # a clearance hole (the screw does not thread into it) fails below 0.5 d
INSERT_BOSS_K = 1.5     # heat-set insert: the boss (material outside diameter) >= 1.5 x the insert OD
INSERT_BOSS_GOOD_K = 2.0  # ESTIMATE: insert makers ask for a boss of about 2 x OD. Below that: WARN.
INSERT_DEPTH_EXTRA = 1.0  # the insert hole is at least the insert length + 1 mm deep

# 2. Thread engagement.
SELFTAP_K = 2.0         # self-tapping or thread-cutting screw in PLA: >= 2 x d
INSERT_ENGAGE_K = 1.5   # into a heat-set insert: >= 1.5 x d (limited by the insert length)
NUT_PASS_PITCH = 1.0    # a screw stands out of a nut by >= 1 pitch
NYLOC_PASS_PITCH = 2.0  # ESTIMATE: a nyloc needs 2 threads past the nylon ring to lock (maker data, ISO 7040 practice)

# 3. Head seating.
SEAT_MIN = 0.90         # the fraction of the head annulus that bears on material
SEAT_FAIL = 0.60
TORQUE_SNUG = {"M2": 0.15, "M3": 0.4, "M5": 1.2, "M6": 2.0}   # N m. ESTIMATE: snug by hand with an L key on plastic
NUT_FACTOR = 0.2        # T = K F d, K = 0.2 for dry steel (VDI 2230 typical)
NUT_FACTOR_SELFTAP = 0.3  # ESTIMATE: a thread-forming screw in plastic has more thread friction
SELFTAP_TORQUE_K = 0.75   # ESTIMATE: a self-tapping screw in PLA gets 0.75 x the snug torque
# Preload is a set value, not an outside load: SF >= 2 PASS, 1 to 2 WARN, below 1 FAIL.
SF_PRE = 2.0

# 4. Tool access: the hex key (or the driver) length, from the head out.
KEY_LEN = {"M2": 60.0, "M3": 60.0, "M5": 70.0, "M6": 80.0}     # mm. The design rule (M5 70, M3 60)
KEY_SHORT = 18.0        # mm. ESTIMATE: the short arm of an L key; with less than this, the screw is not reachable
# The key across the corners (socket head key, ISO 2936) or a Phillips #0/#1 driver for the pan heads.
KEY_D = {("socket", "M3"): 2.9, ("socket", "M5"): 4.6, ("socket", "M6"): 5.8, ("button", "M5"): 3.5,
         ("pan", "M2"): 4.0, ("socket", "M2"): 1.7}

# ---------------------------------------------------------------- PLA (printed), all ESTIMATE
PLA_E = 3500.0          # MPa. ESTIMATE: PLA data sheets 3.0 to 3.6 GPa (solid)
PLA_NU = 0.35
PLA_XY = 50.0           # MPa tensile in the layer plane. ESTIMATE (data sheets 50 to 60)
PLA_Z = 25.0            # MPa tensile across the layers. ESTIMATE (about 0.5 x XY)
PLA_COMP = 50.0         # MPa compressive yield, printed. ESTIMATE (solid PLA 60 to 90; printed parts lower)
PLA_SHEAR = 25.0        # MPa thread shear in PLA. ESTIMATE (about 0.5 x tensile)
PLA_DENSITY = 1.24e-3   # g/mm3
SF = 3.0                # the safety factor on the PLA strength (the design rule)
SF_WARN = 1.5           # below 3 and at or above 1.5: WARN; below 1.5: FAIL


def pla_strength(zfrac):
    """The tensile strength for a stress at an angle to the layers: zfrac = |cos| of the angle
    between the stress direction and the print Z axis. An elliptical blend of XY and Z."""
    c = max(0.0, min(1.0, zfrac))
    s = math.sqrt(1 - c * c)
    return 1.0 / math.sqrt((s / PLA_XY) ** 2 + (c / PLA_Z) ** 2)


def status_pre(sf):
    return "PASS" if sf >= SF_PRE else ("WARN" if sf >= 1.0 else "FAIL")


def status_sf(sf):
    return "PASS" if sf >= SF else ("WARN" if sf >= SF_WARN else "FAIL")


# ---------------------------------------------------------------- fits (0.5 mm nozzle, FDM)
# A vertical hole prints about 0.2 to 0.3 mm small; a horizontal teardrop hole about 0.1 to 0.2.
# ESTIMATE: the usual values for a 0.5 mm nozzle at 0.3 mm layers.
FDM_HOLE_SHRINK = 0.25
FIT_CLASSES = {          # gap per side, mm (min, max). ESTIMATE: printer user guides for a 0.5 mm nozzle
    "press": (0.0, 0.15),
    "push": (0.1, 0.2),
    "slide": (0.2, 0.4),
    "gap": (0.3, 5.0),
}


def shape_clearances():
    """The *_CLR values of shape.py with their comments: [(name, value, comment)]."""
    out = []
    pat = re.compile(r"^([A-Z0-9_]*CLR)\s*=\s*([0-9.]+)\s*#\s*(.*)$")
    with open(os.path.join(HW, "shape.py")) as fh:
        for line in fh:
            m = pat.match(line.strip())
            if m:
                out.append((m.group(1), float(m.group(2)), m.group(3)))
    return out


def fit_class(comment, name):
    c = (comment + " " + name).lower()
    if "press" in c:
        return "press"
    if "push" in c:
        return "push"
    if "slide" in c or "slid" in c or "slot" in c or "channel" in c or "groove" in c or "sled" in c:
        return "slide"
    return "gap"


# ---------------------------------------------------------------- loads
G = 9.81
BELT_T0 = 40.0          # N per run, static. ESTIMATE: GT2 6 mm, 20 to 40 N typical; the upper value
MOTOR_TORQUE = 0.40     # N m. ESTIMATE: a 40 mm NEMA17 holding torque
SERVO_TORQUE = 0.18     # N m. ESTIMATE: SG90 stall, 1.8 kg cm at 4.8 V (data sheet)
HAND_PUSH = 20.0        # N. ESTIMATE: an accidental push on the gantry by hand
PEN_DRAG = 1.0          # N. ESTIMATE: the friction of a felt pen on paper at about 0.5 N of pen weight, times 2
WHEEL_PRELOAD = 30.0    # N per wheel. ESTIMATE: the eccentric preload of a V-wheel, set by hand
X_PLATE_MASS = 60.0     # g. ESTIMATE: the 3 X wheels with their M5 axles, nuts, the eccentric and the insert (the X plate is printed now)
BEAM_MASS_PER_MM = 0.49 # g/mm. ESTIMATE: 2020 V-slot, about 0.49 kg/m (data sheets)


def firmware_accel():
    """The max acceleration of the firmware (mm/s2), from firmware/config/config.go."""
    path = os.path.join(os.path.dirname(HW), "firmware", "config", "config.go")
    try:
        with open(path) as fh:
            m = re.search(r"\bAccel\s*=\s*([0-9.]+)", fh.read())
            return float(m.group(1)), "firmware/config/config.go"
    except Exception:  # noqa: BLE001
        pass
    return 1500.0, "ESTIMATE (config.go not read)"
