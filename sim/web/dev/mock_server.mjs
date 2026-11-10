// Mock simulator server for the web pages. It serves sim/web, the STL files in
// hardware/stl, and a fake machine on the WebSocket /ws. It does not run the
// firmware. Use it to work on the pages without the Go backend.
//
//   cd sim/web/dev && npm install && node mock_server.mjs [port]
//
// Then open http://localhost:8090/lcd.html and http://localhost:8090/machine.html.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { WebSocketServer } from "ws";

const here = path.dirname(fileURLToPath(import.meta.url));
const WEB = path.resolve(here, "..");
const STL = path.resolve(here, "../../../hardware/stl");
const PORT = Number(process.argv[2] || 8090);

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".stl": "model/stl",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

const server = http.createServer((req, res) => {
  let url = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (url === "/") url = "/machine.html";
  let file;
  if (url.startsWith("/stl/")) file = path.join(STL, path.normalize(url.slice(5)));
  else file = path.join(WEB, path.normalize(url));
  if (!file.startsWith(WEB) && !file.startsWith(STL)) return notFound(res);
  fs.readFile(file, (err, data) => {
    if (err) return notFound(res);
    res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream", "cache-control": "no-store" });
    res.end(data);
  });
});
function notFound(res) {
  res.writeHead(404);
  res.end("not found");
}

// ---------------------------------------------------------------------------
// The fake machine.
const TRAVEL = [250, 395];
const m = {
  x: 108, y: 190, y2: 191.2, pen: 0, en: false, homed: false, es: { x: false, y: false, y2: false },
  busy: false, line: "", done: 0, total: 0, speed: 1,
};
let queue = []; // {kind:"move",x,y,f} | {kind:"pen",down} | {kind:"home"} | {kind:"line",text,idx}
let penTarget = 0;
let pendingInk = [];
let allInk = []; // all ink on the sheet, for new windows
let feed = 3000; // mm/min

function parseGcode(text) {
  const out = [];
  const lines = text.split(/\r?\n/);
  let x = null, y = null, f = null;
  let n = 0;
  for (const raw of lines) {
    const line = raw.replace(/;.*$/, "").replace(/\(.*?\)/g, "").trim();
    if (!line) continue;
    n++;
    out.push({ kind: "line", text: line, idx: n });
    const words = {};
    for (const w of line.toUpperCase().matchAll(/([A-Z])\s*(-?[\d.]+)/g)) words[w[1]] = Number(w[2]);
    if ("F" in words) f = words.F;
    if (words.G === 0 || words.G === 1) {
      if ("Z" in words) out.push({ kind: "pen", down: words.Z <= 0 });
      if ("X" in words || "Y" in words) {
        x = "X" in words ? words.X : x ?? m.x;
        y = "Y" in words ? words.Y : y ?? m.y;
        out.push({ kind: "move", x, y, f: words.G === 0 ? 6000 : f || feed });
      }
    } else if (words.G === 28) out.push({ kind: "home" });
    else if (words.M === 3) out.push({ kind: "pen", down: true });
    else if (words.M === 5) out.push({ kind: "pen", down: false });
    else if (words.M === 280 && "S" in words) out.push({ kind: "pen", down: words.S >= 45 });
  }
  return { cmds: out, total: n };
}

function demoGcode() {
  const g = ["G21", "G90", "G28", "M5"];
  const cx = 108, cy = 190;
  // Frame.
  const fr = [[15, 60], [201, 60], [201, 320], [15, 320], [15, 60]];
  g.push(`G0 X${fr[0][0]} Y${fr[0][1]}`, "M3");
  for (const p of fr.slice(1)) g.push(`G1 X${p[0]} Y${p[1]} F4000`);
  g.push("M5");
  // A rose curve.
  for (let k = 0; k < 3; k++) {
    const r0 = 70 - k * 18;
    let first = true;
    for (let i = 0; i <= 720; i++) {
      const t = (i / 720) * Math.PI * 2;
      const r = r0 * Math.cos(5 * t + k * 0.3);
      const x = (cx + r * Math.cos(t)).toFixed(2), y = (cy + 10 + r * Math.sin(t)).toFixed(2);
      if (first) {
        g.push(`G0 X${x} Y${y}`, "M3");
        first = false;
      } else g.push(`G1 X${x} Y${y} F5000`);
    }
    g.push("M5");
  }
  // Wave lines at the bottom.
  for (let j = 0; j < 6; j++) {
    g.push(`G0 X28 Y${75 + j * 6}`, "M3");
    for (let i = 0; i <= 160; i++) g.push(`G1 X${(28 + i).toFixed(1)} Y${(75 + j * 6 + 3 * Math.sin(i / 8 + j)).toFixed(2)} F6000`);
    g.push("M5");
  }
  g.push("G0 X108 Y370");
  return g.join("\n");
}

function startJob(text, name) {
  const { cmds, total } = parseGcode(text);
  queue = cmds;
  m.total = total;
  m.done = 0;
  m.busy = true;
  jobName = name;
  serial("rx", `; job ${name}: ${total} lines`);
}
let jobName = "";

function runLine(text) {
  serial("rx", text);
  const { cmds } = parseGcode(text);
  queue.push(...cmds.filter((c) => c.kind !== "line"));
  m.busy = true;
  serial("tx", "ok");
}

// step advances the machine by dt seconds.
function step(dt) {
  let budget = dt * m.speed;
  while (budget > 0 && queue.length) {
    const c = queue[0];
    if (c.kind === "line") {
      m.line = c.text;
      m.done = c.idx;
      queue.shift();
      continue;
    }
    if (c.kind === "pen") {
      penTarget = c.down ? 1 : 0;
      const d = Math.abs(m.pen - penTarget);
      const t = Math.min(budget, d / 6);
      m.pen += Math.sign(penTarget - m.pen) * t * 6;
      budget -= t;
      if (Math.abs(m.pen - penTarget) < 1e-3) {
        m.pen = penTarget;
        queue.shift();
      }
      continue;
    }
    if (c.kind === "home") {
      m.en = true;
      if (!c.phase) {
        c.phase = 1;
        penTarget = 0;
        m.pen = 0;
      }
      const v = 80;
      const dist = Math.hypot(m.x, m.y);
      const t = Math.min(budget, dist / v);
      if (dist > 1e-6) {
        m.x -= (m.x / dist) * v * t;
        m.y -= (m.y / dist) * v * t;
      }
      budget -= t;
      // The right side starts 1.2 mm behind the left side. Homing squares the gantry.
      m.y2 = m.y + 1.2 * Math.min(1, m.y / 20);
      m.es.x = m.x < 0.5;
      m.es.y = m.y < 0.5;
      m.es.y2 = m.y2 < 0.5;
      if (dist / v <= t + 1e-9) {
        m.x = 0;
        m.y = 0;
        m.y2 = 0;
        m.homed = true;
        queue.shift();
        setTimeout(() => (m.es = { x: false, y: false, y2: false }), 400);
      }
      continue;
    }
    if (c.kind === "move") {
      m.en = true;
      const tx = Math.max(0, Math.min(TRAVEL[0], c.x));
      const ty = Math.max(0, Math.min(TRAVEL[1], c.y));
      const v = c.f / 60;
      const dx = tx - m.x, dy = ty - m.y;
      const dist = Math.hypot(dx, dy);
      const t = Math.min(budget, dist / v);
      const x0 = m.x, y0 = m.y;
      if (dist > 1e-9) {
        m.x += (dx / dist) * v * t;
        m.y += (dy / dist) * v * t;
      }
      budget -= t;
      if (dist / v <= t + 1e-9) {
        m.x = tx;
        m.y = ty;
        queue.shift();
      }
      m.y2 = m.homed ? m.y : m.y + 1.2;
      if (m.pen > 0.99 && (m.x !== x0 || m.y !== y0)) pendingInk.push([r2(x0), r2(y0), r2(m.x), r2(m.y)]);
      continue;
    }
    queue.shift();
  }
  if (!queue.length && m.busy) {
    m.busy = false;
    if (m.total) beepAll(120);
  }
}
const r2 = (v) => Math.round(v * 100) / 100;

// ---------------------------------------------------------------------------
// The fake LCD: a 5 x 7 font, a status screen and a menu.
const FONT = {
  A: [14, 17, 17, 31, 17, 17, 17], B: [30, 17, 17, 30, 17, 17, 30], C: [14, 17, 16, 16, 16, 17, 14],
  D: [28, 18, 17, 17, 17, 18, 28], E: [31, 16, 16, 30, 16, 16, 31], F: [31, 16, 16, 30, 16, 16, 16],
  G: [14, 17, 16, 23, 17, 17, 15], H: [17, 17, 17, 31, 17, 17, 17], I: [14, 4, 4, 4, 4, 4, 14],
  J: [7, 2, 2, 2, 2, 18, 12], K: [17, 18, 20, 24, 20, 18, 17], L: [16, 16, 16, 16, 16, 16, 31],
  M: [17, 27, 21, 21, 17, 17, 17], N: [17, 17, 25, 21, 19, 17, 17], O: [14, 17, 17, 17, 17, 17, 14],
  P: [30, 17, 17, 30, 16, 16, 16], Q: [14, 17, 17, 17, 21, 18, 13], R: [30, 17, 17, 30, 20, 18, 17],
  S: [15, 16, 16, 14, 1, 1, 30], T: [31, 4, 4, 4, 4, 4, 4], U: [17, 17, 17, 17, 17, 17, 14],
  V: [17, 17, 17, 17, 17, 10, 4], W: [17, 17, 17, 21, 21, 21, 10], X: [17, 17, 10, 4, 10, 17, 17],
  Y: [17, 17, 10, 4, 4, 4, 4], Z: [31, 1, 2, 4, 8, 16, 31],
  0: [14, 17, 19, 21, 25, 17, 14], 1: [4, 12, 4, 4, 4, 4, 14], 2: [14, 17, 1, 2, 4, 8, 31],
  3: [31, 2, 4, 2, 1, 17, 14], 4: [2, 6, 10, 18, 31, 2, 2], 5: [31, 16, 30, 1, 1, 17, 14],
  6: [6, 8, 16, 30, 17, 17, 14], 7: [31, 1, 2, 4, 8, 8, 8], 8: [14, 17, 17, 14, 17, 17, 14],
  9: [14, 17, 17, 15, 1, 2, 12], " ": [0, 0, 0, 0, 0, 0, 0], ":": [0, 12, 12, 0, 12, 12, 0],
  ".": [0, 0, 0, 0, 0, 12, 12], "-": [0, 0, 0, 31, 0, 0, 0], ">": [8, 4, 2, 1, 2, 4, 8],
  "%": [24, 25, 2, 4, 8, 19, 3], "/": [0, 1, 2, 4, 8, 16, 0], "+": [0, 4, 4, 31, 4, 4, 0],
};
const fb = new Uint8Array(1024);
function clear() {
  fb.fill(0);
}
function pset(x, y, on = 1) {
  if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
  const i = y * 16 + (x >> 3), b = 0x80 >> (x & 7);
  if (on) fb[i] |= b;
  else fb[i] &= ~b;
}
function text(x, y, s, on = 1) {
  for (const ch of s.toUpperCase()) {
    const g = FONT[ch] || FONT[" "];
    for (let r = 0; r < 7; r++) for (let c = 0; c < 5; c++) if (g[r] & (16 >> c)) pset(x + c, y + r, on);
    x += 6;
  }
}
function rect(x, y, w, h, fillIt) {
  for (let i = 0; i < w; i++)
    for (let j = 0; j < h; j++) if (fillIt || i === 0 || j === 0 || i === w - 1 || j === h - 1) pset(x + i, y + j);
}
function invert(x, y, w, h) {
  for (let i = 0; i < w; i++)
    for (let j = 0; j < h; j++) {
      const xx = x + i, yy = y + j, idx = yy * 16 + (xx >> 3), b = 0x80 >> (xx & 7);
      fb[idx] ^= b;
    }
}

const MENU = ["BACK", "HOME XY", "PEN UP", "PEN DOWN", "PLOT DEMO", "DISABLE MOTORS"];
let screen = "status", cursor = 0;
function render() {
  clear();
  if (screen === "status") {
    text(2, 1, "PEN PLOTTER");
    text(86, 1, m.homed ? "HOMED" : "     ");
    for (let x = 0; x < 128; x++) pset(x, 10);
    text(2, 14, `X ${m.x.toFixed(1).padStart(5)}`);
    text(66, 14, `Y ${m.y.toFixed(1).padStart(5)}`);
    text(2, 24, `PEN ${m.pen > 0.5 ? "DOWN" : "UP"}`);
    text(66, 24, `SPEED ${m.speed}X`);
    const pct = m.total ? m.done / m.total : 0;
    rect(2, 35, 124, 8, false);
    rect(4, 37, Math.round(120 * pct), 4, true);
    text(2, 46, m.total ? `${(pct * 100).toFixed(1)}% ${m.busy ? "PLOTTING" : "DONE"}` : "IDLE");
    text(2, 56, "> PUSH FOR MENU");
  } else {
    text(2, 1, "MENU");
    for (let x = 0; x < 128; x++) pset(x, 10);
    const top = Math.max(0, Math.min(cursor - 2, MENU.length - 5));
    for (let i = 0; i < 5 && top + i < MENU.length; i++) {
      const row = top + i;
      text(8, 14 + i * 10, MENU[row]);
      if (row === cursor) invert(0, 13 + i * 10, 128, 9);
    }
  }
}
let lastLcd = "";
function sendLcd() {
  render();
  const b64 = Buffer.from(fb).toString("base64");
  if (b64 === lastLcd) return;
  lastLcd = b64;
  broadcast({ t: "lcd", bits: b64 });
}

function onEnc(d) {
  if (screen === "menu") cursor = Math.max(0, Math.min(MENU.length - 1, cursor + d));
}
function onClick() {
  beepAll(30);
  if (screen === "status") {
    screen = "menu";
    cursor = 0;
    return;
  }
  const item = MENU[cursor];
  screen = "status";
  if (item === "HOME XY") runLine("G28");
  else if (item === "PEN UP") runLine("M5");
  else if (item === "PEN DOWN") runLine("M3");
  else if (item === "PLOT DEMO") startJob(demoGcode(), "demo.gcode");
  else if (item === "DISABLE MOTORS") {
    m.en = false;
    m.homed = false;
  }
}

// ---------------------------------------------------------------------------
// WebSocket.
const wss = new WebSocketServer({ server, path: "/ws" });
function broadcast(obj) {
  const s = JSON.stringify(obj);
  for (const c of wss.clients) if (c.readyState === 1) c.send(s);
}
function serial(dir, text) {
  broadcast({ t: "serial", dir, text });
}
function beepAll(ms) {
  broadcast({ t: "beep", ms });
}

wss.on("connection", (ws) => {
  ws.send(JSON.stringify({
    t: "hello",
    machine: { layout: "table", travel: TRAVEL, steps_per_mm: [80, 80], pen_up_deg: 90, pen_down_deg: 30, lcd: [128, 64] },
  }));
  for (let i = 0; i < allInk.length; i += 5000) ws.send(JSON.stringify({ t: "ink", s: allInk.slice(i, i + 5000) }));
  render();
  ws.send(JSON.stringify({ t: "lcd", bits: Buffer.from(fb).toString("base64") }));
  ws.on("message", (data) => {
    let msg;
    try {
      msg = JSON.parse(data);
    } catch {
      return;
    }
    switch (msg.t) {
      case "enc":
        onEnc(msg.d);
        break;
      case "btn":
        if (msg.down) onClick();
        break;
      case "gcode":
        startJob(msg.text, msg.name);
        break;
      case "line":
        runLine(msg.text);
        break;
      case "speed":
        m.speed = msg.x;
        break;
      case "paper":
        if (msg.clear) allInk = [];
        break;
      case "reset":
        queue = [];
        Object.assign(m, { pen: 0, en: false, homed: false, busy: false, line: "", done: 0, total: 0 });
        serial("tx", "start");
        beepAll(80);
        break;
    }
  });
});

// Main loop: 60 Hz state, ink, and LCD at 10 Hz.
let last = performance.now();
let tick = 0;
setInterval(() => {
  const now = performance.now();
  step((now - last) / 1000);
  last = now;
  broadcast({ t: "state", ...m, name: jobName, q: queue.length });
  if (pendingInk.length) {
    broadcast({ t: "ink", s: pendingInk });
    allInk.push(...pendingInk);
    pendingInk = [];
  }
  if (++tick % 6 === 0) sendLcd();
}, 1000 / 60);

// Start the demo plot when the first client connects, if the flag is set.
if (process.env.DEMO) setTimeout(() => startJob(demoGcode(), "demo.gcode"), 500);

server.listen(PORT, () => console.log(`mock plotter on http://localhost:${PORT}/  (lcd.html, machine.html)`));
