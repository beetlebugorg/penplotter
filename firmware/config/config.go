// Package config holds all the machine numbers of the pen plotter.
// Change the values here to match your machine.
package config

// Axes of the planner. Y2 is the second Y motor; it is a channel of the step executor only.
const (
	X  = 0
	Y  = 1
	Y2 = 2
)

// Layout: the frame stands on the table, and the paper lies on the table.
// The X beam rides on two Y carriages, one on each base rail.
// Each Y carriage has its own motor, belt and endstop (Y1 left, Y2 right).
// Home is X min (left) and Y min (front).
//
// Mechanics: GT2 belt, 20 tooth pulley, 1.8 degree motor, 1/16 microstep.
const (
	StepsPerMMX    = 80
	StepsPerMMY    = 80      // Y1 and Y2
	TravelX        = 245     // mm, from the home switch (V-wheels; the model allows 245.9)
	TravelY        = 390     // mm, from the home switch (the model gives 395.1: the inner Y wheel stops at the back bar)
	BedX           = TravelX // mm, the drawing area on the table
	BedY           = TravelY
	InvertDirY2    = true // the Y2 motor is a mirror of the Y1 motor
	Y2HomeOffsetMM = 0.0  // mm, Y2 moves this far after homing to square the beam (positive = away from the switch)
)

// StepsPerMM gives the steps per mm of each axis.
var StepsPerMM = [2]float32{StepsPerMMX, StepsPerMMY}

// Travel gives the travel of each axis in mm.
var Travel = [2]float32{TravelX, TravelY}

// Motion limits. Speeds are in mm/s, accelerations in mm/s².
const (
	RapidFeed    = 150  // speed of G0 moves
	DefaultFeed  = 50   // speed of G1 moves before the first F word
	JogFeed      = 60   // speed of moves from the LCD menu
	Accel        = 1500 // acceleration of all moves
	JunctionDev  = 0.02 // mm, corner tolerance of the look-ahead
	MinSpeed     = 1.0  // the segment preparation never goes slower
	ArcTolerance = 0.01 // mm, maximum chord error of G2/G3 lines
	ArcMaxSeg    = 1.0  // mm, maximum length of a G2/G3 line
	SoftLimits   = true // clamp moves to the travel after homing
	HardLimits   = true // stop all motion when a switch closes during a move toward it
)

// Step generation: TickHz, SegmentTick, MaxFeed and PlannerSize depend on the
// processor. See rate.go (Pico, simulator) and rate_avr.go (ATmega2560).

// Homing. Both axes home to the minimum end.
const (
	HomeFastFeed = 30 // mm/s
	HomeSlowFeed = 4  // mm/s
	HomeBackoff  = 3  // mm, move off the switch before the slow pass
	HomeClear    = 5  // mm, move off the switch if it is pressed at the start
	// The same polarity applies to all three switches (X, Y1, Y2).
	// The stock switches are normally closed to GND. With the pull-up the pin
	// reads HIGH when the switch opens, so HIGH means triggered.
	// Set it to false for normally open switches.
	EndstopTriggeredHigh = true
)

// Directions. Set to true if an axis moves the wrong way.
const (
	InvertDirX = false
	InvertDirY = false
)

// Pen servo. Angles are in degrees (0..180). 90 degrees puts the horn level.
// The pen lift needs the horn at -10 degrees for pen down and +40 degrees for pen up.
// The spline position of the horn moves both values. Tune them in the Pen setup menu.
const (
	PenUpDeg      = 130
	PenDownDeg    = 80
	PenSettleMs   = 150 // wait after each pen move
	ServoMinUs    = 500 // pulse width at 0 degrees
	ServoMaxUs    = 2500
	ServoPeriodUs = 20000
)

// User interface.
const (
	EncoderPulsesPerDetent = 4
	UIRefreshMs            = 100
	LongPressMs            = 800
)

// Version is the firmware version.
const Version = "0.1.0"
