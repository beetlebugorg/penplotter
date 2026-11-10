; square.gcode: 40 mm square and a circle (quick test)
; Pen plotter test file. G0 travels, G1 draws, M3 pen down, M5 pen up.
G21 ; mm
G90 ; absolute
M5
G28
G1 F3000 ; draw at 50 mm/s
G0 X20.000 Y20.000
M3
G1 X60.000 Y20.000
G1 X60.000 Y60.000
G1 X20.000 Y60.000
G1 X20.000 Y20.000
M5
G0 X25.000 Y40.000
M3
G2 X25.000 Y40.000 I15 J0
M5
M5
G0 X0 Y0
M400
