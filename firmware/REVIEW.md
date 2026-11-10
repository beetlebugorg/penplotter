# Firmware review log

Each round reviews the firmware, fixes the findings, and runs the checks:
`go vet ./...`, `go test -race ./firmware/... ./sim/...`, and the two TinyGo builds
(`-target=pico` and `-target=pico-w`). The sizes are the `tinygo build -size short` numbers.

## Round 1: core review, settings in flash

Findings and changes:

1. **Long comments failed a job.** A `;` comment counted toward the 128-byte line limit, so a
   vpype or Inkscape header line gave "error:line too long". The port reader now drops the
   text after `;`. It still keeps the limit for the G-code part of a line.
2. **No hard limits.** Before homing, a move toward a switch could drive the carriage into the
   frame. The executor now checks the switches of the channels that move toward them. A switch
   that closes during such a move drops all segments and the controller goes to alarm
   ("hard limit X"). A switch that is closed at the start of the move does not count.
3. **A move to home tripped the limit.** Position 0 is the point where the switch closes, so a
   move back to 0 closed the switch. After homing, each channel has a floor of 1 mm: a switch
   that closes at or below it is the home position, not a crash. Motors off removes the floors.
4. **The emergency stop blocked the main loop.** It busy-waited for the step interrupt to drop
   its segments. The LCD, the ports and the tests stopped during the wait. It now sets a flag,
   and the main loop takes the position at the next pass after the interrupt is done.
5. **Settings were lost at power off.** The pen angles, the speed and (new) the pen table and
   the Wi-Fi network now live in `firmware/settings`: a fixed 1 KB record with a CRC32 and a
   version. The Pico keeps it in the last 4 KB erase block of the flash data area. The
   simulator keeps it in a file. Commands: `M500` save, `M501` load, `M502` defaults,
   `M503` report. Changes from the LCD and the network save automatically 3 s after the
   last change, when the machine is idle.
6. **A flash write stops the step interrupt.** The RP2040 runs code from flash (XIP). A flash
   erase turns XIP off, so the interrupt cannot run. The controller saves only when the
   machine is idle and no line waits. `M500` during motion waits for idle, then saves.
7. **The alarm state rejected harmless queries.** Only `M999`, `M114` and `M119` worked. Now
   `M105`, `M115`, `M503` and `M112` work too.
8. **An allocation in the settings encoder.** A map literal in the bool writer allocated on
   each call. It is a plain branch now. The step interrupt path has no allocations
   (`stepgen.Tick` uses integer math, fixed arrays and atomics only).

Open:

- The step interrupt runs from flash. A cache miss costs about 1 µs. At 40 kHz this gives a
  small jitter, but no lost steps (the tick re-arms from the timer, not from the ISR time).
  TinyGo has no stable attribute to put a function in RAM. Measure the jitter on the
  hardware with a logic analyser before a change.

Checks: `go vet` clean. `go test` passes (settings, controller, stepgen, planner, gcode, ui).
Pico H build: 75 580 bytes flash, 7 444 bytes RAM (before: 49 KB, 6.3 KB). The growth is the
settings, the CRC table, the ports, the pen table and the new menus.

## Round 2: several hosts, the network API, the simulator

Findings and changes:

1. **One host only.** The controller read lines from the USB serial port only. A network
   client could not send G-code. The controller now has up to 6 ports (`controller.Port`):
   USB, TCP clients, API commands and API jobs. Each port has its own line buffer.
2. **Two hosts could mix their lines.** One port owns the machine at a time. It takes the
   machine with its first motion or state line and keeps it until the machine is idle and the
   port is quiet for 2 s. Other ports get `error:busy, <owner> has the machine`. Queries
   (`M105`, `M114`, `M115`, `M119`, `M503`, `?`) and the safety lines `M112` and `M108` work
   from any port.
3. **A query during a waiting line took the reply of that line.** `M119` sent during `M400`
   moved the "ok" of `M400` to the wrong port and never answered `M119`. `exec` now takes over
   the reply port only for a wait that the line itself starts. A test covers it.
4. **The network API.** `firmware/netapi` serves `/api/status`, `/api/cmd`, `/api/job` and
   `/api/pens`, plus the HTTP framing and the TCP G-code bridge. It has no `net/http` and no
   reflection, so the Pico W and the simulator run the same code. Other goroutines reach the
   controller through a mailbox (`Controller.Do`) and a state copy that the controller makes
   every 20 ms (`Controller.API`).
5. **Simulator parity.** plotsim serves `/api/` with `netapi`, accepts G-code clients on
   `-tcp` (default `127.0.0.1:2323`) through the same bridge, and keeps the settings in a file
   (`-settings`). Its Wi-Fi reports "up" at the HTTP address.

Checks: `go vet` clean. `go test -race` passes, with new tests for the API job, status and
commands, busy answers while USB owns the machine, M112 from the network, the pen table and
the settings after a reset, and the TCP port.

## Round 3: Wi-Fi on the Pico W

Findings and changes:

1. **Pure-Go Wi-Fi works with TinyGo 0.44.** `github.com/soypat/cyw43439` v0.2.0 (the CYW43439
   chip on PIO0) and `github.com/soypat/lneto` v0.4.0 (Ethernet, IPv4, ARP, DHCP, TCP, mDNS)
   build for `-target=pico-w`. The Pico 2 W is not needed.
2. **The example code logs to the USB serial port.** That port carries G-code, so log lines
   would break a host. The board code sets up the chip and the stack itself, with no logger.
3. **The scheduler is cooperative.** The network runs in goroutines (frame pump, listener,
   one per HTTP request, one for the TCP client). The main loop calls `runtime.Gosched()`
   after each pass. The step interrupt does not depend on the scheduler.
4. **Services.** Port 80: the HTTP API. Port 23: G-code with "ok" flow control (one client).
   mDNS: `<hostname>.local` (default `penplotter.local`). DHCP, or a fixed address with
   `M552 P<ip>/<bits> G<gateway>`. The network restarts when the settings change and joins
   again when the link drops.
5. **Credentials.** `M587 S"network" P"password"` over USB, or the LCD Wi-Fi menu with a text
   editor on the knob. They live in the settings record in flash.
6. **GPIO25 is not the LED on the Pico W.** It is the chip select of the Wi-Fi chip. The Pico
   W build does not drive it; only the Pico H build blinks the LED.

Checks: `-target=pico-w` builds. Not tested on a real Pico W: this computer has no board.

## Round 4: pen table, pen changes, the automatic changer stub

Findings and changes:

1. **`T` words were ignored.** The pen table has 16 entries (T0 to T15) with a name and a
   colour, in flash. `T<n>` selects the pen for the next `M6`.
2. **Manual pen change.** `M6` lifts the pen, parks the carriage at the pen change position
   (default: the middle of X, the front), shows "PEN CHANGE / Load pen T3 / <name>" on the
   LCD, and beeps every 20 s. A knob click or `M108` from any port continues the job. `M6`
   with the pen that is already in the holder only answers an echo line.
3. **Automatic changer stub.** `controller.Changer` (Start, Poll) is the interface for a
   future changer. With `Changer` set to automatic and no changer on the board, `M6` answers
   an error. The pin map reserves GP13 (Z STEP), GP14 (Z DIR), GP15 (Z endstop) and GP26
   (gripper servo).
4. **LCD.** New Pens menu (pen in the holder, next pen, change now), Wi-Fi menu, and Save
   settings. The status screen shows the pen number and the IP address.
5. **API.** `GET/PUT /api/pens` read and change the table. The status has `tool`.

Checks: tests for the pen change (park, prompt, M108 from a second port, the job continues),
the pen errors, the prompt click on the UI, and the text editor.

## Round 5: robustness and parity

Findings and changes:

1. **The hard limit tripped at home** (also reported by the plotstudio track). Round 1 fixed it
   with a floor of 1 mm after homing. A test homes, moves away, and moves to 0,0 with no alarm.
   A second test drives into the X switch before homing and checks the alarm and that the
   carriage stops within 2 steps of the switch.
2. **API state names.** The status sent upper-case LCD words. The API now sends `idle`, `busy`,
   `homing`, `pen_change` and `alarm`. `pen` stays `up` or `down`.
3. **A boot note contained the word "error".** "settings: defaults (read error)" could make a
   host think that a line failed. It now reads "settings: defaults (none saved)".
4. **Allocations on the Pico H.** The API state copy ran every 20 ms on a board with no
   network. It now runs only with a network (or for tests).
5. **G-code from other tools.** A test runs vpype and Inkscape styles: `%`, `( )` comments,
   `G00`/`G01`, `M03 S1000`, `M05`, Z pen moves, lower case, `N` numbers with `*` checksums,
   `G4 P`, `M2`.
6. **Simulator parity.** A test runs `M6` in the simulator: the simulated LCD shows the prompt,
   and a click of the simulated knob ends the change.
7. **Test helpers.** The controller test helper counted the answers of earlier lines, so a
   second call returned at once. It now counts only new output.

Final numbers:

| Build | Flash | RAM (static) |
|---|---|---|
| Pico H (`-target=pico`) | 75 772 bytes | 7 444 bytes |
| Pico W (`-target=pico-w`) | 550 896 bytes | 9 584 bytes |

The Pico W uses about 30 KB more RAM at run time (TCP buffers and 4 goroutine stacks of 8 KB).
The RP2040 has 264 KB. The flash is 2 MB; the settings use the last 4 KB block.

Tests: 40 test functions in 8 packages. `go test -race ./firmware/... ./sim/...` passes three
times in a row.

Open issues:

- The Wi-Fi code is not tested on a real Pico W.
- The step interrupt runs from flash; measure the jitter with a logic analyser (round 1).
- The API has no password. Use it on a trusted network.
- `/api/job` answers when the lines are queued, not when the moves end. Poll the status.
- The automatic pen changer is an interface only.
