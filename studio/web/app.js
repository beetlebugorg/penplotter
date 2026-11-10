// Plotstudio UI: scan, calibrate, place drawings on the bed, plot.
const $ = (id) => document.getElementById(id);
const api = async (path, opt = {}) => {
  const r = await fetch(path, opt);
  const ct = r.headers.get("content-type") || "";
  const body = ct.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new Error(body && body.error ? body.error : r.statusText);
  return body;
};
const post = (path, data) => api(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data ?? {}) });
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const store = {
  get(k, d) { try { const v = localStorage.getItem("plotstudio." + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("plotstudio." + k, JSON.stringify(v)); } catch {} },
};

let status = {};
let bedGeom = null;          // {px_per_mm, x0, y1, w, h, travel, ver}
let bedImg = null;
let items = store.get("items", []);
let sel = -1;
let pathPreview = null;      // [{x0,y0,x1,y1,draw}]
let tab = "bed";
let pens = [];               // the pen table: [{t, name, color}]
let colorPens = store.get("colorPens", {});   // line colour -> pen (the choices of the person)

// ---------------------------------------------------------------- pens and colours
// CIE L*a*b* of a #rrggbb colour, for the nearest pen (the same rule as the server).
function lab(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || ""); if (!m) return null;
  const v = parseInt(m[1], 16), c = [v >> 16 & 255, v >> 8 & 255, v & 255].map((x) => {
    x /= 255; return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
  const X = (0.4124 * c[0] + 0.3576 * c[1] + 0.1805 * c[2]) / 0.95047;
  const Y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  const Z = (0.0193 * c[0] + 0.1192 * c[1] + 0.9505 * c[2]) / 1.08883;
  const f = (t) => t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116;
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
}
function nearestPen(hex) {
  const a = lab(hex); if (!a) return 0;
  let best = Infinity, t = 0;
  for (const p of pens) { const b = lab(p.color); if (!b) continue;
    const d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2; if (d < best) { best = d; t = p.t; } }
  return t;
}
function layerPen(label) {
  const m = /^\s*(?:t|pen\s*|tool\s*)?(\d{1,2})\b/i.exec(label || ""); if (!m) return -1;
  const n = +m[1]; return n < 16 ? n : -1;
}
const penByT = (t) => pens.find((p) => p.t === t) || { t, name: "T" + t, color: "#2a3a9c" };
function lineColor(it, k) { return it.colors && it.colors.length ? (it.colors.length === 1 ? it.colors[0] : it.colors[k]) : "#000000"; }
function lineLayer(it, k) { return it.layers && it.layers.length ? (it.layers.length === 1 ? it.layers[0] : it.layers[k]) : ""; }
function penFor(color, layer) {
  if ($("optLayers").checked) { const p = layerPen(layer); if (p >= 0) return p; }
  if (colorPens[color] !== undefined) return colorPens[color];
  return nearestPen(color);
}
function usedColors() {
  const seen = new Map();
  for (const it of items) (it.colors && it.colors.length ? it.colors : ["#000000"]).forEach((c) => seen.set(c, (seen.get(c) || 0) + 1));
  return [...seen.keys()];
}
function swatch(c) { const s = document.createElement("span"); s.className = "sw"; s.style.background = c; return s; }
function renderPenMap() {
  const cols = usedColors(), box = $("penMap");
  if (!cols.length) { box.innerHTML = '<span class="muted small">Add a drawing to choose its pens.</span>'; return; }
  box.replaceChildren(...cols.map((c) => {
    const row = document.createElement("div"); row.className = "pm";
    const sel = document.createElement("select"); sel.setAttribute("aria-label", "Pen for " + c);
    for (const p of pens) { const o = document.createElement("option"); o.value = p.t; o.textContent = `T${p.t} ${p.name}`; sel.append(o); }
    sel.value = penFor(c, ""); sel.style.borderLeft = "10px solid " + penByT(+sel.value).color;
    sel.onchange = () => { colorPens[c] = +sel.value; store.set("colorPens", colorPens); renderPenMap(); pathPreview = null; drawBed(); };
    row.append(swatch(c), sel); return row;
  }));
}
// The extra fields of a pen: [key, placeholder, title].
const penFields = [["width", "w", "Line width, mm"]];
function renderPenTable() {
  const box = $("penTable"); box.replaceChildren();
  for (let t = 0; t < 16; t++) {
    const p = pens.find((x) => x.t === t) || { t, name: "", color: "#000000" };
    const lab_ = document.createElement("span"); lab_.textContent = "T" + t;
    const col = document.createElement("input"); col.type = "color"; col.value = p.color; col.dataset.t = t; col.className = "pcol";
    const name = document.createElement("input"); name.type = "text"; name.value = p.name; name.dataset.t = t; name.className = "pname";
    name.placeholder = "empty";
    const extra = document.createElement("div"); extra.className = "pextra"; extra.dataset.t = t;
    for (const [k, ph, title] of penFields) {
      const el = document.createElement("input"); el.type = "number"; el.step = "any"; el.placeholder = ph;
      el.title = title; el.setAttribute("aria-label", `T${t} ${title}`); el.dataset.k = k;
      el.value = p[k] ? p[k] : "";
      extra.append(el);
    }
    box.append(lab_, col, name, extra);
  }
}
async function loadPens() {
  try { pens = await api("api/pens"); } catch { pens = []; }
  renderPenTable(); renderPenMap(); drawBed();
}
$("btnPensSave").onclick = async () => {
  const out = [];
  document.querySelectorAll("#penTable .pname").forEach((n) => {
    const t = +n.dataset.t, c = document.querySelector(`#penTable .pcol[data-t="${t}"]`).value;
    if (!n.value.trim()) return;
    const p = { t, name: n.value.trim(), color: c };
    document.querySelectorAll(`#penTable .pextra[data-t="${t}"] [data-k]`).forEach((el) => {
      if (el.value === "") return;
      p[el.dataset.k] = +el.value;
    });
    out.push(p);
  });
  try { pens = await api("api/pens", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(out) });
    hint("The pen table is saved" + (status.link === "wifi" ? " on the plotter too." : ".")); renderPenTable(); renderPenMap(); drawBed(); }
  catch (e) { hint("Pens: " + e.message); }
};
$("btnPensReset").onclick = () => {
  const def = [["Black","#1a1a1a"],["Grey","#7a7a7a"],["Red","#d62828"],["Orange","#f77f00"],["Yellow","#f2c500"],["Light green","#7bc043"],
    ["Green","#1b7f3b"],["Teal","#16a3a3"],["Light blue","#4aa8e0"],["Blue","#1f4fbf"],["Navy","#14215e"],["Purple","#6a2c91"],
    ["Pink","#e05a9b"],["Brown","#7a4a24"],["Sepia","#5e4b3c"],["Gold","#b8902a"]];
  pens = def.map(([n, c], t) => ({ t, name: n + " 0.5", color: c, width: 0.5 })); renderPenTable();
  hint("Press Save to keep the default table.");
};
$("optLayers").checked = store.get("layerPens", true);
$("optLayers").onchange = () => { store.set("layerPens", $("optLayers").checked); renderPenMap(); pathPreview = null; drawBed(); };
$("optToolChange").onchange = () => { pathPreview = null; };

// ---------------------------------------------------------------- views (zoom and pan)
function makeView(canvas, draw) {
  const v = { canvas, s: 1, ox: 0, oy: 0, fit: true, draw, w: 0, h: 0 };
  const ro = new ResizeObserver(() => { v.fit = v.fit || !v.s; resize(v); });
  ro.observe(canvas);
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const k = Math.exp(-e.deltaY * 0.0015);
    const r = canvas.getBoundingClientRect();
    const mx = (e.clientX - r.left) * devicePixelRatio, my = (e.clientY - r.top) * devicePixelRatio;
    v.ox = mx - (mx - v.ox) * k; v.oy = my - (my - v.oy) * k; v.s *= k; v.fit = false;
    v.draw();
  }, { passive: false });
  return v;
}
function resize(v) {
  const r = v.canvas.getBoundingClientRect();
  v.canvas.width = Math.max(1, Math.round(r.width * devicePixelRatio));
  v.canvas.height = Math.max(1, Math.round(r.height * devicePixelRatio));
  v.draw();
}
function fitTo(v, w, h) {
  const cw = v.canvas.width, ch = v.canvas.height, pad = 24 * devicePixelRatio;
  v.s = Math.min((cw - 2 * pad) / w, (ch - 2 * pad) / h);
  v.ox = (cw - w * v.s) / 2; v.oy = (ch - h * v.s) / 2;
}
function evPos(v, e) {
  const r = v.canvas.getBoundingClientRect();
  return { x: (e.clientX - r.left) * devicePixelRatio, y: (e.clientY - r.top) * devicePixelRatio };
}

// ---------------------------------------------------------------- bed view
// World units are machine mm. Screen: x = ox + (X - x0) * s, y = oy + (y1 - Y) * s.
const bedV = makeView($("bed"), drawBed);
const travel = () => (status.travel || [216, 380]);
const geo = () => bedGeom || { x0: -15, y1: travel()[1] + 15, w: (travel()[0] + 30), h: (travel()[1] + 30), px_per_mm: 1 };
const toScr = (x, y) => [bedV.ox + (x - geo().x0) * bedV.s, bedV.oy + (geo().y1 - y) * bedV.s];
const toMm = (sx, sy) => [geo().x0 + (sx - bedV.ox) / bedV.s, geo().y1 - (sy - bedV.oy) / bedV.s];

function place(it) {
  const s = it.scale || 1, a = (it.angle || 0) * Math.PI / 180, c = Math.cos(a), sn = Math.sin(a);
  return it.lines.map((l) => l.map((p) => {
    const u = (p.x - it.w / 2) * s, v = -(p.y - it.h / 2) * s;
    return [it.x + c * u - sn * v, it.y + sn * u + c * v];
  }));
}
function corners(it) {
  const s = it.scale || 1, a = (it.angle || 0) * Math.PI / 180, c = Math.cos(a), sn = Math.sin(a);
  const hw = it.w * s / 2, hh = it.h * s / 2;
  return [[-hw, hh], [hw, hh], [hw, -hh], [-hw, -hh]].map(([u, v]) => [it.x + c * u - sn * v, it.y + sn * u + c * v]);
}
function rotHandle(it) {
  const s = it.scale || 1, a = (it.angle || 0) * Math.PI / 180;
  const d = it.h * s / 2 + 8 / (bedV.s / devicePixelRatio) * 2;
  return [it.x - Math.sin(a) * d, it.y + Math.cos(a) * d];
}

function drawBed() {
  const v = bedV, ctx = v.canvas.getContext("2d"), g = geo();
  const W = g.w / (bedGeom ? g.px_per_mm : 1), H = g.h / (bedGeom ? g.px_per_mm : 1);
  if (v.fit) fitTo(v, W, H);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, v.canvas.width, v.canvas.height);
  const [bx, by] = toScr(g.x0, g.y1);
  // With no scan, the bed is paper white in both themes, so the pen colours show as they print.
  if (bedImg) ctx.drawImage(bedImg, bx, by, W * v.s, H * v.s);
  else { ctx.fillStyle = "#f4f2ec"; ctx.fillRect(bx, by, W * v.s, H * v.s); }
  // Grid: 10 mm and 50 mm.
  const [tx, ty] = travel();
  ctx.lineWidth = 1;
  for (let x = 0; x <= tx + 0.01; x += 10) {
    ctx.strokeStyle = x % 50 === 0 ? "rgba(47,111,228,0.45)" : "rgba(47,111,228,0.16)";
    const [a, b] = toScr(x, 0), [, d] = toScr(x, ty);
    ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(a, d); ctx.stroke();
  }
  for (let y = 0; y <= ty + 0.01; y += 10) {
    ctx.strokeStyle = y % 50 === 0 ? "rgba(47,111,228,0.45)" : "rgba(47,111,228,0.16)";
    const [a, b] = toScr(0, y), [c] = toScr(tx, y);
    ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(c, b); ctx.stroke();
  }
  ctx.strokeStyle = css("--accent"); ctx.lineWidth = 2 * devicePixelRatio;
  { const [a, b] = toScr(0, ty), [c, d] = toScr(tx, 0); ctx.strokeRect(a, b, c - a, d - b); }
  // Home corner.
  { const [a, b] = toScr(0, 0); ctx.fillStyle = css("--accent"); ctx.beginPath(); ctx.arc(a, b, 5 * devicePixelRatio, 0, 7); ctx.fill();
    ctx.font = `${11 * devicePixelRatio}px system-ui`; ctx.fillText("0,0 home", a + 8 * devicePixelRatio, b - 6 * devicePixelRatio); }
  // Path preview: pen-up moves dashed.
  if (pathPreview && $("optPath").checked) {
    ctx.lineWidth = 1 * devicePixelRatio;
    for (const m of pathPreview) {
      if (m.draw) continue;
      ctx.strokeStyle = "rgba(210,59,47,0.7)"; ctx.setLineDash([4 * devicePixelRatio, 4 * devicePixelRatio]);
      const [a, b] = toScr(m.x0, m.y0), [c, d] = toScr(m.x1, m.y1);
      ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(c, d); ctx.stroke();
    }
    ctx.setLineDash([]);
  }
  // Items.
  items.forEach((it, i) => {
    ctx.lineWidth = Math.max(1, (i === sel ? 0.6 : 0.5) * v.s);
    ctx.lineJoin = ctx.lineCap = "round";
    // One path for each pen colour.
    const byPen = new Map();
    place(it).forEach((l, k) => {
      const t = pens.length ? penFor(lineColor(it, k), lineLayer(it, k)) : -1;
      if (!byPen.has(t)) byPen.set(t, []);
      byPen.get(t).push(l);
    });
    for (const [t, ls] of byPen) {
      ctx.strokeStyle = t < 0 ? "#2a3a9c" : penByT(t).color;
      ctx.beginPath();
      for (const l of ls) l.forEach(([x, y], k) => { const [a, b] = toScr(x, y); k ? ctx.lineTo(a, b) : ctx.moveTo(a, b); });
      ctx.stroke();
    }
    const out = outside(it);
    if (i === sel || out) {
      const cs = corners(it).map(([x, y]) => toScr(x, y));
      ctx.strokeStyle = out ? css("--warn") : css("--accent"); ctx.lineWidth = 1.5 * devicePixelRatio;
      ctx.setLineDash(i === sel ? [] : [5, 4]);
      ctx.beginPath(); cs.forEach(([a, b], k) => k ? ctx.lineTo(a, b) : ctx.moveTo(a, b)); ctx.closePath(); ctx.stroke();
      ctx.setLineDash([]);
      if (i === sel) {
        const hs = 5 * devicePixelRatio;
        ctx.fillStyle = css("--panel");
        for (const [a, b] of cs) { ctx.fillRect(a - hs, b - hs, 2 * hs, 2 * hs); ctx.strokeRect(a - hs, b - hs, 2 * hs, 2 * hs); }
        const [ra, rb] = toScr(...rotHandle(it));
        ctx.beginPath(); ctx.arc(ra, rb, hs, 0, 7); ctx.fill(); ctx.stroke();
      }
    }
  });
}

function outside(it) {
  const [tx, ty] = travel();
  return place(it).some((l) => l.some(([x, y]) => x < -1e-6 || y < -1e-6 || x > tx + 1e-6 || y > ty + 1e-6));
}

function inItem(it, x, y) {
  const s = it.scale || 1, a = -(it.angle || 0) * Math.PI / 180;
  const dx = x - it.x, dy = y - it.y;
  const u = dx * Math.cos(a) - dy * Math.sin(a), v = dx * Math.sin(a) + dy * Math.cos(a);
  return Math.abs(u) <= it.w * s / 2 + 1 && Math.abs(v) <= it.h * s / 2 + 1;
}

let drag = null;
bedV.canvas.addEventListener("pointerdown", (e) => {
  const p = evPos(bedV, e), [mx, my] = toMm(p.x, p.y);
  const near = (a, b) => Math.hypot(a[0] - p.x, a[1] - p.y) < 10 * devicePixelRatio;
  bedV.canvas.setPointerCapture(e.pointerId);
  if (sel >= 0) {
    const it = items[sel];
    if (near(toScr(...rotHandle(it)))) { drag = { kind: "rot", it }; return; }
    if (corners(it).some((c) => near(toScr(...c)))) { drag = { kind: "scale", it, d0: Math.hypot(mx - it.x, my - it.y), s0: it.scale || 1 }; return; }
  }
  for (let i = items.length - 1; i >= 0; i--) {
    if (inItem(items[i], mx, my)) { sel = i; drag = { kind: "move", it: items[i], dx: mx - items[i].x, dy: my - items[i].y }; showItem(); drawBed(); return; }
  }
  sel = -1; showItem();
  drag = { kind: "pan", sx: p.x, sy: p.y, ox: bedV.ox, oy: bedV.oy };
  drawBed();
});
bedV.canvas.addEventListener("pointermove", (e) => {
  if (!drag) return;
  const p = evPos(bedV, e), [mx, my] = toMm(p.x, p.y), snap = $("fSnap").checked, it = drag.it;
  if (drag.kind === "pan") { bedV.ox = drag.ox + p.x - drag.sx; bedV.oy = drag.oy + p.y - drag.sy; bedV.fit = false; }
  else if (drag.kind === "move") { it.x = mx - drag.dx; it.y = my - drag.dy; if (snap) { it.x = Math.round(it.x * 2) / 2; it.y = Math.round(it.y * 2) / 2; } }
  else if (drag.kind === "scale") { it.scale = Math.max(0.01, drag.s0 * Math.hypot(mx - it.x, my - it.y) / Math.max(drag.d0, 0.1)); if (snap) it.scale = Math.round(it.scale * 100) / 100; }
  else if (drag.kind === "rot") { let a = Math.atan2(my - it.y, mx - it.x) * 180 / Math.PI - 90; if (snap) a = Math.round(a / 5) * 5; it.angle = ((a % 360) + 540) % 360 - 180; }
  if (drag.kind !== "pan") { pathPreview = null; showItem(); }
  drawBed();
});
const endDrag = () => { if (drag && drag.kind !== "pan") save(); drag = null; };
bedV.canvas.addEventListener("pointerup", endDrag);
bedV.canvas.addEventListener("pointercancel", endDrag);
bedV.canvas.addEventListener("dblclick", () => { bedV.fit = true; drawBed(); });
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || sel < 0) return;
  const it = items[sel], step = e.shiftKey ? 5 : 0.5;
  const k = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }[e.key];
  if (k) { it.x += k[0]; it.y += k[1]; e.preventDefault(); }
  else if (e.key === "Delete" || e.key === "Backspace") { items.splice(sel, 1); sel = -1; e.preventDefault(); }
  else return;
  pathPreview = null; save(); showItem(); drawBed();
});

function save() { store.set("items", items); if (pens.length) renderPenMap(); }

function showItem() {
  const card = $("itemCard"), it = items[sel];
  card.classList.toggle("hidden", !it);
  if (!it) return;
  $("itemName").textContent = it.name || "";
  const s = it.scale || 1;
  for (const [id, v] of [["fX", it.x], ["fY", it.y], ["fW", it.w * s], ["fH", it.h * s], ["fA", it.angle || 0]]) {
    if (document.activeElement !== $(id)) $(id).value = (Math.round(v * 10) / 10).toString();
  }
}
for (const id of ["fX", "fY", "fW", "fH", "fA"]) {
  $(id).addEventListener("input", () => {
    const it = items[sel]; if (!it) return;
    const v = parseFloat($(id).value); if (!isFinite(v)) return;
    if (id === "fX") it.x = v; if (id === "fY") it.y = v; if (id === "fA") it.angle = v;
    if (id === "fW" && it.w > 0 && v > 0) it.scale = v / it.w;
    if (id === "fH" && it.h > 0 && v > 0) it.scale = v / it.h;
    pathPreview = null; save(); showItem(); drawBed();
  });
}
$("btnDel").onclick = () => { if (sel >= 0) { items.splice(sel, 1); sel = -1; save(); showItem(); drawBed(); } };
$("btnDup").onclick = () => { if (sel >= 0) { const c = structuredClone(items[sel]); c.x += 10; c.y -= 10; items.push(c); sel = items.length - 1; save(); showItem(); drawBed(); } };

function addItem(it, name) {
  if (!it.lines || !it.lines.length) { hint("The file has no lines to draw."); return; }
  const [tx, ty] = travel();
  it.name = name; it.scale = 1; it.angle = 0;
  // Fit large drawings into the travel.
  const k = Math.min(1, (tx - 10) / it.w, (ty - 10) / it.h);
  if (k < 1) it.scale = Math.floor(k * 100) / 100;
  it.x = tx / 2; it.y = ty / 2;
  items.push(it); sel = items.length - 1; pathPreview = null;
  save(); showItem(); setTab("bed"); drawBed();
}
async function addSVG(text, name) {
  try { addItem(await api("api/svg", { method: "POST", body: text }), name); }
  catch (e) { hint("SVG: " + e.message); }
}
$("fileSvg").onchange = async (e) => { for (const f of e.target.files) await addSVG(await f.text(), f.name.replace(/\.svg$/i, "")); e.target.value = ""; };
const stage = document.querySelector(".stage");
stage.addEventListener("dragover", (e) => { e.preventDefault(); $("drop").classList.remove("hidden"); });
stage.addEventListener("dragleave", () => $("drop").classList.add("hidden"));
stage.addEventListener("drop", async (e) => {
  e.preventDefault(); $("drop").classList.add("hidden");
  for (const f of e.dataTransfer.files) await addSVG(await f.text(), f.name.replace(/\.svg$/i, ""));
});

// ---------------------------------------------------------------- library and signature
async function loadLib() {
  try {
    const names = await api("api/library");
    $("lib").replaceChildren(...(names || []).map((n) => {
      const b = document.createElement("button"); b.textContent = n; b.title = "Add " + n;
      b.onclick = async () => addSVG(await (await fetch("api/library/" + encodeURIComponent(n))).text(), n);
      return b;
    }));
  } catch {}
}
const pad = $("sigPad"), pctx = pad.getContext("2d");
let strokes = [], cur = null;
function drawPad() {
  pctx.clearRect(0, 0, pad.width, pad.height);
  pctx.strokeStyle = "#ccd"; pctx.lineWidth = 2; pctx.beginPath(); pctx.moveTo(40, 230); pctx.lineTo(860, 230); pctx.stroke();
  pctx.strokeStyle = "#1a237e"; pctx.lineWidth = 4; pctx.lineJoin = pctx.lineCap = "round";
  for (const s of strokes) { pctx.beginPath(); s.forEach(([x, y], i) => i ? pctx.lineTo(x, y) : pctx.moveTo(x, y)); pctx.stroke(); }
}
const padPos = (e) => { const r = pad.getBoundingClientRect(); return [(e.clientX - r.left) * pad.width / r.width, (e.clientY - r.top) * pad.height / r.height]; };
pad.addEventListener("pointerdown", (e) => { pad.setPointerCapture(e.pointerId); cur = [padPos(e)]; strokes.push(cur); drawPad(); });
pad.addEventListener("pointermove", (e) => {
  if (!cur) return; const p = padPos(e), q = cur[cur.length - 1];
  if (Math.hypot(p[0] - q[0], p[1] - q[1]) > 2.5) { cur.push(p); drawPad(); }
});
pad.addEventListener("pointerup", () => { cur = null; });
function sigSVG() {
  // The pad is 900 x 300 px for 75 x 25 mm.
  const d = strokes.filter((s) => s.length > 1).map((s) => "M" + s.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(" L")).join(" ");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="75mm" height="25mm" viewBox="0 0 900 300"><path d="${d}" fill="none" stroke="black"/></svg>`;
}
$("btnSig").onclick = () => { drawPad(); $("sigDlg").showModal(); };
$("sigClear").onclick = () => { strokes = []; drawPad(); };
$("sigSave").onclick = async () => {
  try { await post("api/library", { name: $("sigName").value || "signature", svg: sigSVG() }); loadLib(); hint("Saved to the library."); }
  catch (e) { hint(e.message); }
};
$("sigAdd").onclick = async () => { $("sigDlg").close(); await addSVG(sigSVG(), $("sigName").value || "signature"); };

// ---------------------------------------------------------------- camera view and calibration
let camImg = null, camLive = false, cal = null; // cal: {points, pairs, i}
const camV = makeView($("cam"), drawCam);
function drawCam() {
  const v = camV, ctx = v.canvas.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, v.canvas.width, v.canvas.height);
  if (!camImg) return;
  if (v.fit) fitTo(v, camImg.naturalWidth, camImg.naturalHeight);
  ctx.drawImage(camImg, v.ox, v.oy, camImg.naturalWidth * v.s, camImg.naturalHeight * v.s);
  if (!cal) return;
  ctx.font = `bold ${13 * devicePixelRatio}px system-ui`;
  cal.pairs.forEach((p, i) => {
    const x = v.ox + p.px * v.s, y = v.oy + p.py * v.s, r = 7 * devicePixelRatio;
    ctx.strokeStyle = "#ff3b30"; ctx.lineWidth = 2 * devicePixelRatio;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 2 * r, y); ctx.lineTo(x + 2 * r, y); ctx.moveTo(x, y - 2 * r); ctx.lineTo(x, y + 2 * r); ctx.stroke();
    ctx.fillStyle = "#ff3b30"; ctx.fillText(String(i + 1), x + r + 3, y - r);
  });
}
let camDrag = null;
camV.canvas.addEventListener("pointerdown", (e) => {
  const p = evPos(camV, e);
  camDrag = { sx: p.x, sy: p.y, ox: camV.ox, oy: camV.oy, moved: false };
  camV.canvas.setPointerCapture(e.pointerId);
});
camV.canvas.addEventListener("pointermove", (e) => {
  if (!camDrag) return; const p = evPos(camV, e);
  if (Math.hypot(p.x - camDrag.sx, p.y - camDrag.sy) > 4) camDrag.moved = true;
  if (camDrag.moved) { camV.ox = camDrag.ox + p.x - camDrag.sx; camV.oy = camDrag.oy + p.y - camDrag.sy; camV.fit = false; drawCam(); }
});
camV.canvas.addEventListener("pointerup", async (e) => {
  const d = camDrag; camDrag = null;
  if (!d || d.moved || !cal || !camImg || cal.i >= cal.points.length) return;
  const p = evPos(camV, e);
  const px = (p.x - camV.ox) / camV.s, py = (p.y - camV.oy) / camV.s;
  let q = { px, py };
  try { q = await post("api/calib/refine", { px, py }); } catch {}
  const m = cal.points[cal.i];
  cal.pairs.push({ px: q.px, py: q.py, x: m.x, y: m.y }); cal.i++;
  calPrompt(); drawCam();
});
camV.canvas.addEventListener("dblclick", () => { camV.fit = true; drawCam(); });

function loadImage(url) {
  return new Promise((ok, bad) => { const im = new Image(); im.onload = () => ok(im); im.onerror = bad; im.src = url + (url.includes("?") ? "&" : "?") + "t=" + Date.now(); });
}
async function showScan() { try { camImg = await loadImage("api/scan.jpg"); drawCam(); } catch {} }

function calPrompt() {
  const rows = $("calRow");
  if (!cal) { rows.classList.add("hidden"); hint(""); return; }
  rows.classList.remove("hidden");
  if (cal.i < cal.points.length) {
    const m = cal.points[cal.i];
    hint(`Click mark ${cal.i + 1} of ${cal.points.length}: the dot at X ${m.x.toFixed(0)}, Y ${m.y.toFixed(0)} mm. Wheel zooms, drag pans.`);
  } else hint(`All ${cal.points.length} marks are set. Press Solve.`);
  $("calText").textContent = `${cal.pairs.length} of ${cal.points.length} marks`;
}

$("btnMark").onclick = async () => {
  try {
    await post("api/calib/mark", { grid: +$("calGrid").value });
    hint("The plotter homes and draws a dot at each point. Then press 2. Click marks.");
  } catch (e) { hint(e.message); }
};
$("btnClick").onclick = async () => {
  try {
    hint("Scanning…");
    await post("api/scan");
    const pts = await post("api/calib/points", { grid: +$("calGrid").value });
    cal = { points: pts, pairs: [], i: 0 };
    await showScan(); setTab("cam"); camV.fit = true; drawCam(); calPrompt();
  } catch (e) { hint("Scan: " + e.message); }
};
$("btnUndo").onclick = () => { if (cal && cal.i > 0) { cal.pairs.pop(); cal.i--; calPrompt(); drawCam(); } };
$("btnSolve").onclick = async () => {
  if (!cal) return;
  try {
    const c = await post("api/calib/solve", { pairs: cal.pairs, fit_k1: $("calLens").checked });
    const worst = Math.max(...c.errors_mm);
    cal = null; calPrompt();
    $("calText").textContent = `Calibrated: error ${c.rms_mm.toFixed(2)} mm (worst ${worst.toFixed(2)} mm), lens k1 ${c.lens.K1.toFixed(3)}.`;
    await loadBed(); setTab("bed");
  } catch (e) { hint("Solve: " + e.message); }
};

// ---------------------------------------------------------------- scan, live, focus
$("btnScan").onclick = async () => {
  try { hint("Scanning…"); $("btnScan").disabled = true; await post("api/scan"); hint(""); await loadBed(); await showScan(); }
  catch (e) { hint("Scan: " + e.message); }
  finally { $("btnScan").disabled = false; }
};
$("btnLive").onclick = () => {
  camLive = !camLive; $("btnLive").classList.toggle("on", camLive);
  if (camLive) { setTab("cam"); liveLoop(); } else showScan();
};
async function liveLoop() {
  while (camLive) {
    try { camImg = await loadImage("api/camera.jpg"); if (tab === "cam") drawCam(); } catch { await new Promise((r) => setTimeout(r, 1000)); }
    await new Promise((r) => setTimeout(r, 150));
  }
}
async function focus(req) {
  try {
    const f = req ? await post("api/focus", req) : await api("api/focus");
    $("focusRow").classList.toggle("hidden", !f.has);
    $("focusVal").textContent = f.has ? (f.auto ? "auto" : "fixed at " + f.pos) : "";
    $("btnFocusAuto").classList.toggle("on", !!f.auto); $("btnFocusLock").classList.toggle("on", f.has && !f.auto);
  } catch { $("focusRow").classList.add("hidden"); }
}
$("btnFocusAuto").onclick = () => focus({ auto: true });
$("btnFocusLock").onclick = () => focus({ auto: false });

async function loadBed() {
  try {
    bedGeom = await api("api/bed");
    bedImg = bedGeom.has_image ? await loadImage("api/bed.jpg") : null;
  } catch { bedImg = null; }
  bedV.fit = bedV.fit || !bedImg; drawBed();
}

// ---------------------------------------------------------------- plot
const plotReq = () => ({ items, feed: +$("feed").value, home: $("optHome").checked, park: $("optPark").checked,
  color_pens: colorPens, layer_pens: $("optLayers").checked, tool_change: $("optToolChange").checked });
const penText = (r) => r.pens && r.pens.length > 1 ? ` ${r.pens.length} pens (${r.pens.map((t) => "T" + t).join(", ")}), ${r.pen_changes} changes.` : "";
async function preview() {
  try {
    const r = await post("api/gcode", plotReq());
    const moves = []; let x = 0, y = 0, down = false;
    for (const l of r.gcode.split("\n")) {
      if (l.startsWith("M3")) down = true; else if (l.startsWith("M5")) down = false;
      const mx = /X(-?[\d.]+)/.exec(l), my = /Y(-?[\d.]+)/.exec(l);
      if ((l.startsWith("G0") || l.startsWith("G1")) && (mx || my)) {
        const nx = mx ? +mx[1] : x, ny = my ? +my[1] : y;
        moves.push({ x0: x, y0: y, x1: nx, y1: ny, draw: down }); x = nx; y = ny;
      }
    }
    pathPreview = moves;
    $("jobText").textContent = `${r.lines} strokes, ${r.draw_mm} mm drawn, ${r.travel_mm} mm pen-up, about ${Math.ceil(r.est_s / 60)} min.` + penText(r);
  } catch (e) { pathPreview = null; $("jobText").textContent = e.message; }
  drawBed();
}
$("optPath").onchange = () => { if ($("optPath").checked) preview(); else drawBed(); };
$("btnPlot").onclick = async () => {
  if (items.some(outside)) { hint("An item is outside the drawing area. Move it inside the blue frame."); return; }
  const running = status.job && (status.job.state === "running" || status.job.state === "paused");
  const req = { ...plotReq(), queue: running };
  try {
    const r = await post("api/plot", req);
    $("jobText").textContent = r.queued ? `Added to the queue. Start it when the paper is ready.` : `Plotting ${r.lines} strokes…` + penText(r);
  }
  catch (e) { hint("Plot: " + e.message); }
};
$("btnPause").onclick = async () => {
  const st = status.job && status.job.state;
  try { await post("api/job/" + (st === "paused" ? "resume" : "pause")); } catch (e) { hint(e.message); }
};
$("btnCancel").onclick = async () => { try { await post("api/job/cancel"); } catch (e) { hint(e.message); } };
$("btnHome").onclick = async () => {
  try { hint("Homing…"); await post("api/cmd", { lines: ["G28"] }); hint(""); } catch (e) { hint(e.message); }
};
$("btnPen").onclick = async () => { try { await post("api/cmd", { lines: ["M3", "G4 P600", "M5"] }); } catch (e) { hint(e.message); } };

// ---------------------------------------------------------------- status, log, tabs
let hintTimer = 0;
function hint(t) {
  $("hint").textContent = t || "";
  clearTimeout(hintTimer);
  if (t && !cal) hintTimer = setTimeout(() => { if (!cal) $("hint").textContent = ""; }, 8000);
}
function setTab(t) {
  tab = t;
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === t));
  $("bed").classList.toggle("hidden", t !== "bed"); $("cam").classList.toggle("hidden", t !== "cam");
  resize(t === "bed" ? bedV : camV);
}
document.querySelectorAll(".tabs button").forEach((b) => b.onclick = () => { setTab(b.dataset.tab); if (b.dataset.tab === "cam" && !camImg) showScan(); });

let lastBedVer = -1, logN = 0;
async function poll() {
  try {
    status = await api("api/status");
    const chip = (id, ok, text) => { const c = $(id); c.textContent = text; c.classList.toggle("ok", ok); c.classList.toggle("bad", !ok); };
    chip("chipPlotter", status.connected, status.connected ? (status.link === "wifi" ? "Wi-Fi " : "USB ") + status.port : "No plotter");
    if (document.activeElement !== $("plotAddr") && !$("plotAddr").value && status.port) $("plotAddr").value = status.port;
    { const alarm = (status.device && status.device.state === "alarm") || (status.job && /alarm/i.test(status.job.error || ""));
      $("btnAlarm").classList.toggle("hidden", !alarm); }
    { const d = status.device;
      $("plotText").textContent = !status.connected ? (status.port ? "Not connected. Plotstudio tries again every 3 s." : "Type an address, or press Find.")
        : d && d.state ? `${d.state.replace("_", " ")}${d.homed ? ", homed" : ", not homed"}, pen T${d.tool}${d.msg ? " — " + d.msg : ""}${d.error ? " — " + d.error : ""}`
        : status.link === "wifi" ? "Connected. Waiting for the status of the plotter." : "Connected by USB."; }
    chip("chipCamera", !!status.camera, status.camera ? "Camera" : "No camera");
    $("chipCamera").title = status.camera || "";
    chip("chipCalib", !!status.calib, status.calib ? `Calibrated ±${status.calib.rms_mm.toFixed(2)} mm` : "Not calibrated");
    const j = status.job;
    if (j) {
      $("bar").style.width = (j.total ? 100 * j.done / j.total : 0) + "%";
      $("hint").classList.toggle("prompt", j.pen_change !== undefined);
      if (j.pen_change !== undefined) {
        const p = penByT(j.pen_change);
        $("hint").textContent = `Pen change: load T${p.t} (${p.name}), then press the knob on the plotter.`;
        $("jobText").innerHTML = "";
        const d = document.createElement("div"); d.className = "prompt";
        d.append(swatch(p.color), ` Load pen T${p.t} (${p.name}), then press the knob on the plotter.`);
        $("jobText").append(d);
      } else if (j.state !== "done" || !$("jobText").textContent) $("jobText").textContent = `${j.name}: ${j.state}, ${j.done} / ${j.total} lines${j.error ? " — " + j.error : ""}`;
      $("btnPause").textContent = j.state === "paused" ? "Resume" : "Pause";
    }
    { const running = j && (j.state === "running" || j.state === "paused");
      $("btnPlot").textContent = running ? "Add to queue" : "Plot";
      const q = status.queue || [];
      $("queue").replaceChildren(...q.map((x) => {
        const row = document.createElement("div"); row.className = "q";
        const t = document.createElement("span"); t.textContent = `Next: ${x.name} (${x.stats.lines} strokes, about ${Math.ceil(x.stats.est_s / 60)} min)`;
        const s = document.createElement("button"); s.textContent = "Start"; s.disabled = running;
        s.onclick = async () => { try { await post(`api/queue/${x.id}/start`); } catch (e) { hint(e.message); } };
        const d = document.createElement("button"); d.textContent = "Remove";
        d.onclick = async () => { try { await api(`api/queue/${x.id}`, { method: "DELETE" }); } catch (e) { hint(e.message); } };
        row.append(t, s, d); return row;
      })); }
    if (status.bed_ver !== lastBedVer) { lastBedVer = status.bed_ver; loadBed(); }
    if (status.log_n > logN) {
      const lines = await api("api/log?after=" + logN);
      const el = $("log");
      for (const l of lines) { el.textContent += (l.dir === "tx" ? "→ " : l.dir === "rx" ? "← " : "• ") + l.text + "\n"; logN = l.n; }
      el.textContent = el.textContent.split("\n").slice(-200).join("\n");
      el.scrollTop = el.scrollHeight;
    }
  } catch {}
  setTimeout(poll, 700);
}

// ---------------------------------------------------------------- plotter link
$("btnConnect").onclick = async () => {
  const addr = $("plotAddr").value.trim(); if (!addr) { hint("Type a plotter address."); return; }
  $("plotText").textContent = "Connecting…";
  try { const r = await post("api/port", { path: addr }); store.set("plotter", addr); hint(`Connected (${r.link === "wifi" ? "Wi-Fi" : "USB"}).`); loadPens(); }
  catch (e) { $("plotText").textContent = e.message; }
};
$("btnAlarm").onclick = async () => {
  if (!confirm("Clear the alarm and home the plotter? Check that nothing blocks the gantry.")) return;
  try { await post("api/cmd", { lines: ["M999", "G28"] }); hint("The alarm is clear. The plotter is homed."); }
  catch (e) { hint("Alarm: " + e.message); }
};
$("btnFind").onclick = async () => {
  $("plotText").textContent = "Looking for plotters (2 s)…";
  const opts = [];
  try { for (const d of await api("api/discover")) opts.push([d.port === 23 ? d.host || d.ip : `${d.ip}:${d.port}`, `${d.name} (${d.ip}, Wi-Fi)`]); } catch {}
  try { for (const p of await api("api/devices")) opts.push([p, "USB"]); } catch {}
  $("plotList").replaceChildren(...opts.map(([v, l]) => { const o = document.createElement("option"); o.value = v; o.label = l; return o; }));
  $("plotText").textContent = opts.length ? `Found ${opts.length}: ${opts.map((o) => o[0]).join(", ")}. Pick one and press Connect.` : "No plotter found. Check that it is on and on the same network.";
  if (opts.length && !$("plotAddr").value) $("plotAddr").value = opts[0][0];
};
$("plotAddr").value = store.get("plotter", "");

showItem(); loadLib(); focus(); loadPens(); poll(); drawBed();
