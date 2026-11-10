// The wiring of the 3D view: the detailed bought parts, the cables, the Y drag chain and the servo loom.
//
// - The detailed bought parts (motors, endstop boards, the two adapter boards, the servo, the control
//   box) come from stl/detail/manifest.json (hardware/export_context_detail.py). One STL for each
//   moving group and material. They replace the one-colour sim2 stand-ins that the manifest names.
// - The drag chain has real links (InstancedMesh). Each link keeps its place along the chain, so the
//   chain flexes link by link with the true pitch.
// - The servo lead runs in a 1/2 inch split wire loom: a free slack loop (catenary) behind the beam,
//   with one cable tie at each end (frame.json chains, axis x).
// - The cables run from plug to plug (the anchors of the manifest). A path is a set of straight lines
//   with a circular arc at each corner. The arc radius is the minimum bend radius of the cable.
//
// All positions are frame coordinates (mm): X right, Y to the back, Z up. f2s() converts to the scene.
import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

let A = null; // the API of machine.js: f2s, getters for the groups, the materials
let manifest = null;
let manifestP = null;
export const hiddenParts = new Set(); // sim2 file names (without .stl) that the detail meshes replace
const geoCache = new Map();
const loader = new STLLoader();

// initWiring starts the manifest download. machine.js calls it once.
export function initWiring(api) {
  A = api;
  manifestP = fetch("stl/detail/manifest.json")
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null)
    .then((m) => {
      manifest = m;
      if (m) for (const n of m.replaces || []) hiddenParts.add(n);
      return m;
    });
}

// ---------------------------------------------------------------------------
// Geometry helpers.

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const f2s = (p) => A.f2s(p[0], p[1], p[2]);
const add3 = (p, d, k = 1) => [p[0] + d[0] * k, p[1] + d[1] * k, p[2] + d[2] * k];

// fillet makes a smooth path: straight lines with a circular arc of radius r at each corner. The arc
// gets smaller where two corners are close. The points are frame points; the result is Vector3 (frame).
function fillet(points, r, seg = 7) {
  const P = points.map((p) => V(p[0], p[1], p[2]));
  const out = [P[0].clone()];
  let prevEnd = P[0].clone();
  for (let i = 1; i < P.length - 1; i++) {
    const a = P[i].clone().sub(prevEnd), b = P[i + 1].clone().sub(P[i]);
    const la = a.length(), lb = b.length();
    if (la < 1e-6 || lb < 1e-6) continue;
    const d0 = a.divideScalar(la), d1 = b.divideScalar(lb);
    const th = Math.acos(Math.min(1, Math.max(-1, d0.dot(d1))));
    if (th < 1e-3) {
      out.push(P[i].clone());
      prevEnd = P[i].clone();
      continue;
    }
    let t = r * Math.tan(th / 2);
    const tmax = Math.min(la, lb / 2);
    if (t > tmax) t = tmax;
    const rr = t / Math.tan(th / 2);
    const A0 = P[i].clone().addScaledVector(d0, -t);
    const u = d1.clone().addScaledVector(d0, -d0.dot(d1)).normalize(); // toward the arc centre
    const C = A0.clone().addScaledVector(u, rr);
    const m = Math.max(2, Math.ceil((seg * th) / (Math.PI / 2)));
    for (let k = 0; k <= m; k++) {
      const ph = (th * k) / m;
      out.push(C.clone().addScaledVector(u, -rr * Math.cos(ph)).addScaledVector(d0, rr * Math.sin(ph)));
    }
    prevEnd = out[out.length - 1].clone();
  }
  out.push(P[P.length - 1].clone());
  return out;
}

// resample returns n points spaced evenly along the polyline pts.
function resample(pts, n) {
  const L = [0];
  for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
  const total = L[L.length - 1];
  const out = [];
  let j = 1;
  for (let k = 0; k < n; k++) {
    const s = (total * k) / (n - 1);
    while (j < pts.length - 1 && L[j] < s) j++;
    const seg = L[j] - L[j - 1] || 1;
    out.push(pts[j - 1].clone().lerp(pts[j], (s - L[j - 1]) / seg));
  }
  return { pts: out, total };
}

// Cross-section profiles: a list of loops; each loop is a list of [u, v] (u along N, v along B).
function circle(r, n, cu = 0, cv = 0) {
  return Array.from({ length: n }, (_, i) => [cu + r * Math.cos((2 * Math.PI * i) / n), cv + r * Math.sin((2 * Math.PI * i) / n)]);
}
const PROFILE = {
  round: (r) => [circle(r, r > 3 ? 10 : 7)],
  flat3: () => [circle(0.55, 6, 0, -1.1), circle(0.55, 6, 0, 0), circle(0.55, 6, 0, 1.1)], // the servo lead: 3 x 1.1 mm
  strip: (w, t) => [[[-t / 2, -w / 2], [t / 2, -w / 2], [t / 2, w / 2], [-t / 2, w / 2]]],
};

// Sweep: a tube of a profile along n path points. The geometry keeps its size, so an update only
// writes the positions.
class Sweep {
  constructor(profile, n, colors = null, upHint = null) {
    this.loops = profile;
    this.n = n;
    this.up = upHint; // frame vector: N follows it (flat cables lie with their width across it)
    const perRing = profile.reduce((a, l) => a + l.length, 0);
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(perRing * n * 3), 3));
    const idx = [];
    let base = 0;
    for (const loop of profile) {
      const m = loop.length;
      for (let i = 0; i < n - 1; i++)
        for (let k = 0; k < m; k++) {
          const a = i * perRing + base + k, b = i * perRing + base + ((k + 1) % m);
          const c = a + perRing, d = b + perRing;
          idx.push(a, c, b, b, c, d);
        }
      base += m;
    }
    g.setIndex(idx);
    if (colors) {
      // colors: one colour for each loop.
      const col = new Float32Array(perRing * n * 3);
      for (let i = 0; i < n; i++) {
        let o = 0;
        profile.forEach((loop, li) => {
          const c = new THREE.Color(colors[li]);
          for (let k = 0; k < loop.length; k++, o++) col.set([c.r, c.g, c.b], (i * perRing + o) * 3);
        });
      }
      g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    }
    this.geo = g;
    this.perRing = perRing;
  }
  // set writes the tube along the frame points pts (exactly n Vector3 in frame coordinates).
  set(pts) {
    const pos = this.geo.attributes.position.array;
    const n = pts.length;
    let N = null;
    for (let i = 0; i < n; i++) {
      const T = (i === 0 ? pts[1].clone().sub(pts[0]) : i === n - 1 ? pts[n - 1].clone().sub(pts[n - 2]) : pts[i + 1].clone().sub(pts[i - 1])).normalize();
      if (this.up) {
        const h = this.up.clone().addScaledVector(T, -this.up.dot(T));
        if (h.lengthSq() > 1e-4) N = h.normalize();
      }
      if (!N) {
        const h = Math.abs(T.z) < 0.9 ? V(0, 0, 1) : V(1, 0, 0);
        N = h.addScaledVector(T, -h.dot(T)).normalize();
      } else {
        N.addScaledVector(T, -N.dot(T)); // parallel transport
        if (N.lengthSq() < 1e-8) N = (Math.abs(T.z) < 0.9 ? V(0, 0, 1) : V(1, 0, 0)).addScaledVector(T, -T.z);
        N.normalize();
      }
      const B = T.clone().cross(N);
      let o = 0;
      for (const loop of this.loops)
        for (const [u, v] of loop) {
          const p = pts[i];
          const s = f2s([p.x + N.x * u + B.x * v, p.y + N.y * u + B.y * v, p.z + N.z * u + B.z * v]);
          pos.set([s.x, s.y, s.z], (i * this.perRing + o++) * 3);
        }
    }
    this.geo.attributes.position.needsUpdate = true;
    this.geo.computeVertexNormals();
    this.geo.computeBoundingSphere();
  }
}

// ---------------------------------------------------------------------------
// Instanced small parts: cable ties and the chain links.

// tieGeo: a cable tie as a flat ring (1 mm across the ring at scale 1, 2.5 mm wide) with its head.
function tieGeo() {
  const ring = new THREE.CylinderGeometry(1, 1, 2.5, 14, 1, true);
  const inner = new THREE.CylinderGeometry(0.9, 0.9, 2.5, 14, 1, true);
  inner.scale(-1, 1, 1); // the inside faces point in
  const head = new THREE.BoxGeometry(0.9, 3.4, 0.9);
  head.translate(1.25, 0, 0);
  const g = mergeGeometries([ring.toNonIndexed(), inner.toNonIndexed(), head.toNonIndexed()]);
  g.rotateZ(Math.PI / 2); // the ring axis along local X (the cable direction)
  return g;
}

// linkGeo: one link of an openable 10 x 20 drag chain, outer h x w, pitch p. Local X along the chain
// (pivot to pivot), Y across the bend (+Y = the lid side), Z across the chain. Each side has an outer
// half plate (+X half) and an inner half plate (-X half) that goes inside the next link, a pivot
// boss, and the bend stops. A bar closes the bottom and the openable lid bar closes the top.
function linkGeo(h, w, p) {
  const parts = [];
  const plate = (x0, x1, z, t) => {
    const s = new THREE.Shape();
    const r = h / 2;
    s.moveTo(x0, -r);
    s.lineTo(x1, -r);
    s.absarc(x1, 0, r, -Math.PI / 2, Math.PI / 2, false);
    s.lineTo(x0, r);
    s.lineTo(x0, -r);
    const g = new THREE.ExtrudeGeometry(s, { depth: t, bevelEnabled: false, curveSegments: 6 });
    g.translate(0, 0, z);
    return g;
  };
  const t = 2.0;
  for (const side of [-1, 1]) {
    const e = 0.8;                                          // the bosses and the stops stand 0.8 mm out
    const zo = side > 0 ? w / 2 - e - t : -w / 2 + e;       // the outer plate
    const zi = side > 0 ? w / 2 - e - 2 * t - 0.2 : -w / 2 + e + t + 0.2; // the inner plate (inside the next link)
    parts.push(plate(0, p / 2, zo, t));
    const pi = new THREE.ExtrudeGeometry((() => {
      const s = new THREE.Shape();
      const r = h / 2 - 0.6;
      s.moveTo(0, -r);
      s.lineTo(-p / 2, -r);
      s.absarc(-p / 2, 0, r, -Math.PI / 2, (3 * Math.PI) / 2 - Math.PI, true);
      s.lineTo(0, r);
      s.lineTo(0, -r);
      return s;
    })(), { depth: t, bevelEnabled: false, curveSegments: 6 });
    pi.translate(0, 0, zi);
    parts.push(pi);
    // The pivot boss on the outer face at the +X pivot, and the bend stop block.
    const boss = new THREE.CylinderGeometry(2.6, 2.6, 0.8, 12);
    boss.rotateX(Math.PI / 2);
    boss.translate(p / 2, 0, side > 0 ? w / 2 - 0.4 : -w / 2 + 0.4);
    parts.push(boss);
    const stop = new THREE.BoxGeometry(2.2, 2.0, 0.8);
    stop.translate(p / 2 - 4.5, -h / 2 + 2.2, side > 0 ? w / 2 - 0.4 : -w / 2 + 0.4);
    parts.push(stop);
  }
  const bottom = new THREE.BoxGeometry(6, 2.2, w - 2 * t - 1.6);
  bottom.translate(p / 4, -h / 2 + 1.1, 0);
  parts.push(bottom);
  const lid = new THREE.BoxGeometry(6, 2.2, w - 1.6);
  lid.translate(p / 4, h / 2 - 1.1, 0);
  parts.push(lid);
  const hinge = new THREE.CylinderGeometry(1.0, 1.0, w - 0.4, 8);
  hinge.rotateX(Math.PI / 2);
  hinge.translate(p / 4 - 3.0, h / 2 - 1.1, 0);
  parts.push(hinge);
  return mergeGeometries(parts.map((g) => (g.index ? g.toNonIndexed() : g)));
}

// ---------------------------------------------------------------------------
// The carrier paths (frame.json "chains"): two straight runs and a half circle.

function carrierPath(ch, x, y) {
  const C = A.CFG();
  const cy = C.carriage_y0 + y;
  const f = ch.fixed, m = ch.moving;
  const isY = ch.plane.type === "y-z";
  const e = isY
    ? { fa: f.moves === "gantry" ? cy + f.dy : f.y, fb: f.z, ma: cy + m.dy, mb: m.z }
    : { fa: f.x, fb: cy + f.dy, ma: C.carriage_x0 + x + m.dx, mb: cy + m.dy };
  const r = ch.bend_r;
  const sgn = /^\+/.test(ch.bend_side) ? 1 : -1;
  const ab = sgn > 0 ? (ch.runs + e.fa + e.ma) / 2 : (e.fa + e.ma - ch.runs) / 2;
  const bc = (e.fb + e.mb) / 2;
  const L1 = Math.abs(ab - e.fa), arc = Math.PI * r, L2 = Math.abs(e.ma - ab);
  // at(s): the plane point (a, b), the tangent (ta, tb) and the outward normal (oa, ob) at s from the fixed end.
  const at = (s) => {
    if (s <= L1) return [e.fa + sgn * s, e.fb, sgn, 0, 0, Math.sign(e.fb - bc)];
    s -= L1;
    if (s <= arc) {
      const ph = s / r;
      const a = ab + sgn * r * Math.sin(ph), b = bc + (e.fb - bc) * Math.cos(ph);
      return [a, b, sgn * Math.cos(ph), (-(e.fb - bc) / r) * Math.sin(ph), (a - ab) / r, (b - bc) / r];
    }
    s -= arc;
    return [ab - sgn * Math.min(s, L2), e.mb, -sgn, 0, 0, Math.sign(e.mb - bc)];
  };
  const pl = ch.plane;
  const zc = isY ? 0 : (pl.z[0] + pl.z[1]) / 2;
  // toFrame: a plane point with an offset (k across the bend plane: frame x for Y, frame z for X).
  const toFrame = (a, b, k = 0) => (isY ? [pl.x + k, a, b] : [a, b, zc + k]);
  return { e, at, toFrame, total: L1 + arc + L2, isY, sgn };
}

// ---------------------------------------------------------------------------
// The wiring of one machine build.

let W = null; // the current build
let token = 0;

// wiringBuild makes the chain, the loom, the detail parts and the cables. machine.js calls it at the
// end of buildMachine. ctx: { machine, gantry, carriage, R, C }.
export function wiringBuild(ctx) {
  const my = ++token;
  W = { ctx, ready: false, cables: [], ties: [], chainY: null, chainX: null, statics: new THREE.Group(), boxSide: new THREE.Group() };
  ctx.machine.add(W.statics);
  W.statics.add(W.boxSide);
  const chains = ctx.C.chains || [];
  const chY = chains.find((c) => c.axis === "y"), chX = chains.find((c) => c.name === "x");
  if (chY) W.chainY = makeChain(chY, ctx.machine);
  if (chX) W.chainX = makeLoom(chX, ctx.machine);
  W.tieMesh = new THREE.InstancedMesh(tieGeo(), new THREE.MeshStandardMaterial({ color: 0x18191b, roughness: 0.55 }), 64);
  W.tieMesh.count = 0;
  W.tieMesh.frustumCulled = false;
  W.tieMesh.castShadow = true;
  ctx.machine.add(W.tieMesh);
  manifestP.then((m) => {
    if (my !== token || !m) return;
    loadDetail(m, ctx, my);
    makeCables(m, ctx);
    W.ready = true;
    W.last = null;
  });
  return W;
}

// wiringShowBox shows the cables at the control box (the stock board) or hides them (the Pico pod).
export function wiringShowBox(on) {
  if (W) W.boxSide.visible = on;
}

async function loadDetail(m, ctx, my) {
  const R = ctx.R;
  const parents = { static: ctx.machine, gantry: R.gantry, carriage: R.carriage, ctrl: A.ctrlBox };
  for (const f of m.files) {
    let g = geoCache.get(f.file);
    if (!g) {
      try {
        const r = await fetch(`stl/${f.file}`);
        if (!r.ok) continue;
        g = loader.parse(await r.arrayBuffer());
        g.computeVertexNormals();
        geoCache.set(f.file, g);
      } catch {
        continue;
      }
    }
    if (my !== token) return;
    const mat = new THREE.MeshStandardMaterial({ color: f.color, metalness: f.metalness, roughness: f.roughness });
    if (f.group === "carriage") A.toolMats.push(mat);
    const mesh = new THREE.Mesh(g, mat);
    mesh.name = "detail:" + f.file;
    mesh.rotation.x = -Math.PI / 2; // frame (Z up) to scene (Y up)
    mesh.castShadow = mesh.receiveShadow = true;
    (parents[f.group] || ctx.machine).add(mesh);
  }
  // Hide the one-colour stand-ins (sim2) and the drawn parts that the detail replaces.
  ctx.machine.traverse((o) => {
    if (o.isMesh && hiddenParts.has((o.name || "").replace(/\.stl$/, ""))) o.visible = false;
  });
  for (const k of ["x", "y1", "y2"]) {
    const st = R.stops && R.stops[k];
    const led = m.leds && m.leds[k];
    if (!st || !led) continue;
    st.children.forEach((c) => (c.visible = false));
    // The trigger indicator of the sim: the red plunger of the switch glows when the switch triggers.
    // (The LED pads of the real board are empty.)
    const mat = new THREE.MeshStandardMaterial({ color: 0xd0402a, emissive: 0x000000, roughness: 0.45 });
    const s = new THREE.Mesh(new THREE.SphereGeometry(0.8, 10, 6), mat);
    s.position.copy(f2s(led.p));
    (led.moves === "gantry" ? R.gantry : ctx.machine).add(s);
    st.userData.mat = mat;
    st.userData.ledOn = 0xff3020;
    st.userData.ledOff = 0xd0402a;
  }
  A.ctrlBox.children.forEach((c) => {
    if (c.name === "ctrlLcd") {
      const L = m.lcd;
      if (L) c.position.copy(f2s([L.c[0], L.c[1] - 0.05, L.c[2]]));
    } else if (!c.name.startsWith("detail:")) c.visible = false;
  });
}

// ---------------------------------------------------------------------------
// The drag chain and the servo loom.

// endLinkGeo: the end link of the chain with its mounting bracket. Local X from 0 (the chain side) to
// L (the opening), Y across the bend (the lid side +Y), Z across the chain. The +Z side wall is the
// bracket plate: it lies on the anchor (or the carriage tab) with 2 holes for the M3 screws at holes
// (local x). The bottom has a comb for cable ties, 8 mm past the opening.
function endLinkGeo(h, w, L, holes) {
  const parts = [];
  const plate = (z, t, withHoles) => {
    const s = new THREE.Shape();
    s.moveTo(0, -h / 2);
    s.lineTo(L, -h / 2);
    s.lineTo(L, h / 2);
    s.lineTo(0, h / 2);
    s.lineTo(0, -h / 2);
    if (withHoles)
      for (const hx of holes) {
        const hp = new THREE.Path();
        hp.absarc(hx, 0, 1.6, 0, Math.PI * 2, true);
        s.holes.push(hp);
      }
    const g = new THREE.ExtrudeGeometry(s, { depth: t, bevelEnabled: false, curveSegments: 10 });
    g.translate(0, 0, z);
    return g;
  };
  parts.push(plate(w / 2 - 2.0, 2.0, true));      // the bracket side (2 mm wall, YCH_LINK_WALL)
  parts.push(plate(-w / 2, 2.0, false));
  const bottom = new THREE.BoxGeometry(L + 8, 2.0, w - 4);
  bottom.translate((L + 8) / 2, -h / 2 + 1.0, 0);
  parts.push(bottom);
  for (const zc of [-(w - 4) / 2 + 2, (w - 4) / 2 - 2]) { // the comb teeth for the cable ties
    const tooth = new THREE.BoxGeometry(5, 3.0, 2.0);
    tooth.translate(L + 5.5, -h / 2 + 3.5, zc);
    parts.push(tooth);
  }
  const lid = new THREE.BoxGeometry(5, 2.0, w - 4);
  lid.translate(L - 3.5, h / 2 - 1.0, 0);
  parts.push(lid);
  return mergeGeometries(parts.map((g) => (g.index ? g.toNonIndexed() : g)));
}

// makeChain: the links (InstancedMesh) and the two end links. The links fill the path from the fixed
// end (s = 0, y = fixed.y) to 6 mm short of the moving end (the moving end link is centred on it). The
// pitch is set so that a whole number of links fills this length (18 mm nominal, ESTIMATE).
function makeChain(ch, parent) {
  const pitch0 = (manifest && manifest.chain_link && manifest.chain_link.pitch) || 18;
  const [h, w] = ch.outer_hw;
  const el = ch.end_link || 12;
  const body = ch.runs + Math.PI * ch.bend_r - el / 2;
  const n = Math.round(body / pitch0);
  const pitch = body / n;
  const mat = new THREE.MeshStandardMaterial({ color: 0x1b1b1e, roughness: 0.62 });
  const mesh = new THREE.InstancedMesh(linkGeo(h, w, pitch), mat, n);
  mesh.castShadow = mesh.receiveShadow = true;
  mesh.frustumCulled = false;
  parent.add(mesh);
  // The screw positions (shape.py and fasteners.py): fixed end 2.5 and 9.5 mm from the link start
  // (y 494.5 and 501.5), moving end 1.5 and 10.5 mm (the tab screws at YCH_TAB_Y + 5.5 and - 5.5).
  const fixedEnd = new THREE.Mesh(endLinkGeo(h, w, el, [2.5, el - 2.5]), mat);
  const movingEnd = new THREE.Mesh(endLinkGeo(h, w, el, [1.5, el - 1.5]), mat);
  for (const e of [fixedEnd, movingEnd]) {
    e.matrixAutoUpdate = false;
    e.castShadow = e.receiveShadow = true;
  }
  parent.add(fixedEnd, movingEnd);
  return { ch, mesh, n, pitch, h, w, fixedEnd, movingEnd, el, body };
}

// placeBasis puts an object at frame point p with local X along t, local Z along o (frame vectors).
const _m = new THREE.Matrix4();
function basisMatrix(p, t, o) {
  const T = f2s(t).normalize(), O = f2s(o).normalize();
  const N = O.clone().cross(T).normalize();
  const O2 = T.clone().cross(N);
  _m.makeBasis(T, N, O2);
  _m.setPosition(f2s(p));
  return _m;
}

function updateChain(c, x, y) {
  const path = carrierPath(c.ch, x, y);
  const o = path.isY ? [1, 0, 0] : [0, 0, 1];
  const pt = (s) => {
    const q = path.at(Math.min(Math.max(s, 0), path.total));
    return V(...path.toFrame(q[0], q[1]));
  };
  // Link i spans s = i p to (i + 1) p from the fixed end. Its pivots stay on the path, so the chain
  // bends link by link (a polygon round the bend).
  for (let i = 0; i < c.n; i++) {
    const a = pt(i * c.pitch), b = pt((i + 1) * c.pitch);
    const t = b.clone().sub(a);
    const mid = a.clone().add(b).multiplyScalar(0.5);
    c.mesh.setMatrixAt(i, basisMatrix([mid.x, mid.y, mid.z], [t.x, t.y, t.z], o));
  }
  c.mesh.instanceMatrix.needsUpdate = true;
  // The end links: both open to +y (the fixed end at fixed.y .. fixed.y + el, the moving end centred
  // on the tab, ma - el/2 .. ma + el/2).
  const e = path.e;
  if (path.isY) {
    c.fixedEnd.matrix.copy(basisMatrix(path.toFrame(e.fa, e.fb), [0, 1, 0], o));
    c.movingEnd.matrix.copy(basisMatrix(path.toFrame(e.ma - c.el / 2, e.mb), [0, 1, 0], o));
    c.fixedEnd.matrixWorldNeedsUpdate = c.movingEnd.matrixWorldNeedsUpdate = true;
  }
  return path;
}

// catenary returns the parameter a and the sag of a cable of length ln hanging between two points at
// the same height, s apart (as hardware/parts.py catenary). A chord near 0 gives a U of two strands.
function catenary(s, ln) {
  if (s < 0.5) return [0, ln / 2];
  if (ln <= s) return [Infinity, 0];
  let lo = 1e-3, hi = 1e7;
  for (let i = 0; i < 200; i++) {
    const a = Math.sqrt(lo * hi);
    if (2 * a * Math.sinh(Math.min(s / (2 * a), 700)) > ln) lo = a;
    else hi = a;
  }
  const a = Math.sqrt(lo * hi);
  return [a, a * (Math.cosh(s / (2 * a)) - 1)];
}

// loomPoints: the centre line of the servo loom at machine x, y (as hardware/parts.py x_loom_points):
// the tie on the front of the X plate, up, back over the beam to the loop plane, the catenary to the
// fixed end at the head harness cable.
function loomPoints(ch, x, y, n = 48) {
  const C = A.CFG();
  const cy = C.carriage_y0 + y;
  const xm = C.carriage_x0 + x + ch.moving.dx, xf = ch.fixed.x;
  const yl = cy + ch.plane.dy, zt = ch.z;
  const yt = cy + ch.moving.tie.dy, zt0 = ch.moving.tie.z;
  const pts = [V(xm, yt, zt0), V(xm, yt, zt), V(xm, yl, zt)];
  const s = Math.abs(xf - xm);
  const [a, sag] = catenary(s, ch.length);
  if (a === 0) {
    pts.push(V(xm, yl, zt - sag), V(xf + 0.5, yl, zt - sag), V(xf + 0.5, yl, zt));
    return pts;
  }
  const xc = (xm + xf) / 2;
  for (let i = 1; i <= n; i++) {
    const px = xm + ((xf - xm) * i) / n;
    const z = Number.isFinite(a) ? zt - sag + a * (Math.cosh((px - xc) / a) - 1) : zt;
    pts.push(V(px, yl, z));
  }
  return pts;
}

function makeLoom(ch, parent) {
  const n = 120;
  const sweep = new Sweep(PROFILE.round(ch.d / 2), n, null, null);
  const mat = new THREE.MeshStandardMaterial({ color: 0x111113, roughness: 0.7 });
  const mesh = new THREE.Mesh(sweep.geo, mat);
  mesh.name = "servo loom";
  mesh.castShadow = true;
  mesh.frustumCulled = false;
  parent.add(mesh);
  return { ch, sweep, mesh, n, pts: [] };
}

function updateLoom(b, x, y) {
  const raw = loomPoints(b.ch, x, y);
  const { pts } = resample(fillet(raw.map((p) => [p.x, p.y, p.z]), b.ch.d), b.n);
  b.pts = pts;
  b.sweep.set(pts);
}

// ---------------------------------------------------------------------------
// The cables.

// A cable: name, material, profile, fillet radius, and route(x, y) that returns frame points.
function addCable(spec, parent) {
  const prof = spec.flat ? PROFILE.flat3() : PROFILE.round(spec.r);
  const sweep = new Sweep(prof, spec.n || 140, spec.flat ? [0x5a3418, 0xb0221c, 0xe07b1a] : null, spec.up || null);
  const mat = spec.flat
    ? new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6 })
    : new THREE.MeshStandardMaterial({ color: spec.color ?? 0x141414, roughness: 0.55 });
  const mesh = new THREE.Mesh(sweep.geo, mat);
  mesh.castShadow = true;
  mesh.frustumCulled = false;
  mesh.name = "cable:" + spec.name;
  (parent || W.ctx.machine).add(mesh);
  const c = { ...spec, sweep, mesh, pts: [] };
  W.cables.push(c);
  return c;
}

function updateCable(c, x, y, y2) {
  const raw = c.route(x, y, y2);
  const f = fillet(raw, c.bend);
  // Keep the cable on or above the table.
  for (const p of f) p.z = Math.max(p.z, c.flat ? 0.6 : c.r);
  const { pts } = resample(f, c.sweep.n);
  c.pts = pts;
  c.sweep.set(pts);
}

// Anchor helpers: an anchor point and a point d mm out of the plug, at the current x, y.
function an(m, name) {
  return m.anchors[name];
}
function apos(a, x, y, out = 0) {
  const p = add3(a.p, a.d, out);
  if (a.moves === "gantry") return [p[0], p[1] + y, p[2]];
  if (a.moves === "carriage") return [p[0] + x, p[1] + y, p[2]];
  return p;
}

function makeCables(m, ctx) {
  const C = ctx.C;
  const c0 = m.c0;
  const g = (yy) => (dy) => yy + c0 + dy; // gantry y from the beam centre
  const chY = W.chainY;
  const chX = W.chainX;
  const BZ = 82; // the bundle behind the gantry (z)

  // In-chain points of a cable: the chain path from the fixed end (s = 0) to the moving end, with an
  // offset k across the chain (frame x) and j across the bend plane. The cables stay in the 10 x 20 bore.
  const inChain = (x, y, k, j = 0) => {
    const path = carrierPath(chY.ch, x, y);
    const out = [];
    const n = Math.ceil(path.total / 8);
    for (let i = 0; i <= n; i++) {
      const q = path.at((path.total * i) / n);
      out.push(path.toFrame(q[0] + q[4] * j, q[1] + q[5] * j, k));
    }
    return { out, path };
  };
  // The chain ends: both end links open to +y. The cables leave along the chain axis through the
  // opening, over the tie comb, and bend after it.
  const el = chY.el;
  const fixedOut = (k, d) => [chY.ch.plane.x + k, chY.ch.fixed.y + el + d, chY.ch.fixed.z];
  const movingOut = (y, k, d) => [chY.ch.plane.x + k, c0 + y + chY.ch.moving.dy + el / 2 + d, chY.ch.moving.z];
  // The lanes in the bore (frame x offset from the chain centre): the harness on the outer side, the
  // two stepper cables on the frame side. So the harness turns to the box and the stepper cables turn
  // to the base board without a crossing.
  const LANE = { harness: -5.4, y1: 1.8, y2: 6.4 };
  // The table trunk (static): the cables from the box go back along the table at x -100 (head harness)
  // and x -110 (base harness), then along the back of the frame. The stepper cables run from the chain
  // to the base board at y 527 and 531.5. Each cable lies on adhesive tie mounts (3 mm).
  const TM = 3.0;

  // --- The head harness (9 mm): the control box, the table trunk, the chain, the gantry, the head board.
  const hh = an(m, "head_harness");
  addCable({
    name: "head harness", r: 4.5, bend: 30, n: 190, color: 0x161616,
    route: (x, y) => {
      const G = g(y);
      const ch = inChain(x, y, LANE.harness).out;
      const box = an(m, "ctrl_gland1");
      const z = 4.5 + TM;
      return [
        apos(box, x, y), apos(box, x, y, 14), [-100, 335, z], [-100, 545, z], [-50 + LANE.harness, 545, z],
        fixedOut(LANE.harness, 14), fixedOut(LANE.harness, 0), ...ch,
        movingOut(y, LANE.harness, 0), movingOut(y, LANE.harness, 16), [-55, G(68), 70], [-30, G(68), 74], [124, G(66), 78], [124, G(66), 162],
        [hh.p[0], G(hh.p[1] - c0), 162], apos(hh, x, y, 30), apos(hh, x, y),
      ];
    },
  });
  // --- The Y motor cables (4.5 mm, static since 2026-11-09: the Y motors stand behind the back bar).
  // From the base board window down behind the bar, along the table behind the frame (y 562, on tie
  // mounts), up beside each motor and over its top to the PH socket. They do not go in the chain.
  const yBase = { 0: an(m, "base_Y"), 1: an(m, "base_Z1") };
  const yMot = { 0: an(m, "y1_motor"), 1: an(m, "y2_motor") };
  for (const i of [0, 1]) {
    const b = yBase[i], mo = yMot[i];
    const z = 2.25 + TM;
    const xs = i === 0 ? -26 : 426;          // beside the motor body, outside the frame line
    const route = () => [
      apos(b, 0, 0), apos(b, 0, 0, 3), [b.p[0] - 7, 551 + 5 * i, b.p[2]], [70, 551 + 5 * i, b.p[2]], [70, 562 + 3 * i, 24],
      [70, 562 + 3 * i, z], [xs, 562 + 3 * i, z], [xs, 562 + 3 * i, 96], [mo.p[0], mo.p[1], 96],
      apos(mo, 0, 0, 6), apos(mo, 0, 0),
    ];
    const c = addCable({ name: i === 0 ? "Y1 motor" : "Y2 motor", r: 2.25, bend: 16, n: 160, color: 0x1a1a1a, static: true, route });
    W.statics.add(c.mesh);
  }
  // --- The X motor cable (4.5 mm) and the X endstop cable (3 mm): from the head board down behind the
  // beam, behind the left carriage. The motor cable goes up to the motor top. The endstop cable goes up
  // over the beam end and down the front to the board on the X endstop wall.
  const xm = an(m, "x_motor"), hx = an(m, "head_X"), xe = an(m, "x_endstop"), hxe = an(m, "head_X-");
  const headDown = (a, x, y, dz) => {
    const G = g(y);
    return [apos(a, x, y), apos(a, x, y, 4), [a.p[0], G(42), a.p[2] - 8], [a.p[0], G(43), 70 - dz], [96, G(60 + dz / 2), 70 - dz]];
  };
  addCable({
    name: "X motor", r: 2.25, bend: 14, n: 130, color: 0x1a1a1a,
    route: (x, y) => {
      const G = g(y);
      // The X motor stands behind the left beam end: up behind the carriage, to its top.
      return [...headDown(hx, x, y, 0), [32, G(60), 72], [32, G(60), 128], [12, G(xm.p[1] - c0), 128],
        [xm.p[0], G(xm.p[1] - c0), 128], apos(xm, x, y, 4), apos(xm, x, y)];
    },
  });
  addCable({
    name: "X endstop", r: 1.5, bend: 8, n: 130, color: 0xa0221c,
    route: (x, y) => {
      const G = g(y);
      return [...headDown(hxe, x, y, -3), [35, G(63), 73], [35, G(63), 126], [-2, G(20), 126], [-2, G(-24), 126],
        [-12, G(xe.p[1] - c0), xe.p[2] + 6], apos(xe, x, y, 4), apos(xe, x, y)];
    },
  });
  // --- The servo lead (flat, 3 wires): from BL_T up to the fixed tie of the loom, in the loom (the loom
  // hides it), from the moving tie on the front of the X plate to the servo.
  const bl = an(m, "head_BL_T"), sv = an(m, "servo");
  const lead = addCable({
    name: "servo lead", flat: true, bend: 6, n: 240, up: V(0, 0, 1),
    route: (x, y) => {
      const G = g(y);
      const lp = loomPoints(chX.ch, x, y).map((p) => [p.x, p.y, p.z]).reverse();
      const f0 = lp[0], f1 = lp[lp.length - 1];
      return [
        apos(bl, x, y), apos(bl, x, y, 4), [bl.p[0], G(30), f0[2] - 10], [f0[0], f0[1], f0[2] - 4], ...lp,
        [f1[0], f1[1], f1[2] - 6], [sv.p[0] + x, G(sv.p[1] - c0 - 0.6), f1[2] - 6],
        apos(sv, x, y, 4), apos(sv, x, y),
      ];
    },
  });
  W.lead = lead;
  // --- The Y endstop cables (3 mm, static), in the frame slots under slot cover strips:
  // - From the plug they go round the outside of the front corner (x -4 or 404) and under the rail.
  // - They run in the bottom outer slot of the rail (x 10 or 390): free of T-nuts (the chain anchor
  //   T-nut at y 487-497 is past the Y1 exit).
  // - Y1 leaves its slot at y 470 (before the anchor arm), passes under the arm on the table, and goes
  //   up into the bottom slot of the back bar at x 22. Y2 leaves its slot at the rail end (y 494) and
  //   goes into the same back bar slot at x 384.
  // - Both leave the back bar slot at x 62 to 70 and go up behind the bar to the base board.
  const SZ = 40.1; // the cable centre in a bottom slot, 3.1 mm in from the slot face (z 37), over the 1.5 mm strip
  const yEnd = [[an(m, "y1_endstop"), an(m, "base_Y-")], [an(m, "y2_endstop"), an(m, "base_Z-")]];
  yEnd.forEach(([e, b], i) => {
    const sx = i === 0 ? -4 : 404, slot = i === 0 ? 10 : 390;
    const route = () => {
      const front = [apos(e, 0, 0), apos(e, 0, 0, 6), [e.p[0], -24, 74], [sx, -27, 60], [sx, 25, 35.2], [slot, 27, 35.2], [slot, 34, SZ]];
      const mid = i === 0
        ? [[slot, 466, SZ], [slot, 472, 34], [slot, 476, 1.5], [slot, 508, 1.5], [21, 510, 30], [22, 510, 35], [27, 510, SZ], [60, 510, SZ], [64, 510, 35]]
        : [[slot, 490, SZ], [slot, 496, 35], [388, 503, 35], [384, 510, 35.5], [380, 510, SZ], [74, 510, SZ], [70, 510, 35]];
      const back = [[70, 528, 24], [70, 559 + 2.5 * i, 30], [70, 559 + 2.5 * i, b.p[2]], [b.p[0] - 7, 559 + 2.5 * i, b.p[2]], apos(b, 0, 0, 3), apos(b, 0, 0)];
      return [...front, ...mid, ...back];
    };
    const c = addCable({ name: i === 0 ? "Y1 endstop" : "Y2 endstop", r: 1.5, bend: 6, n: 220, color: 0xa0221c, static: true, route });
    W.statics.add(c.mesh);
  });
  // The slot cover strips (6 mm flexible PVC, flush with the slot face): [x0, y0, z0, x1, y1, z1].
  const STRIPS = [
    [7, 36, 37, 13, 464, 38.5],        // left rail, bottom outer slot (x 10): y 36 to 464
    [387, 36, 37, 393, 488, 38.5],     // right rail, bottom outer slot (x 390): y 36 to 488
    [29, 507, 37, 58, 513, 38.5],      // back bar, bottom slot (y 510): x 29 to 58 (Y1)
    [76, 507, 37, 378, 513, 38.5],     // back bar, bottom slot: x 76 to 378 (Y2)
  ];
  W.strips = STRIPS;
  const smat = new THREE.MeshStandardMaterial({ color: 0x4a4e55, roughness: 0.7 });
  for (const sb of STRIPS) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(sb[3] - sb[0], sb[5] - sb[2], sb[4] - sb[1]), smat);
    mesh.position.copy(f2s([(sb[0] + sb[3]) / 2, (sb[1] + sb[4]) / 2, (sb[2] + sb[5]) / 2]));
    mesh.name = "strip";
    mesh.receiveShadow = true;
    W.statics.add(mesh);
  }
  // --- The base harness (9 mm): the base board plug, a U turn before the pole foot, along the table
  // behind the frame (y 556, under the base board), forward along x -110 to the box.
  const bh = an(m, "base_harness"), g0 = an(m, "ctrl_gland0");
  const base = addCable({
    name: "base harness", r: 4.5, bend: 26, n: 160, color: 0x161616, static: true,
    route: () => [apos(bh, 0, 0), apos(bh, 0, 0, 12), [158, 536, 34], [158, 556, 4.5 + TM], [100, 556, 4.5 + TM],
      [-110, 556, 4.5 + TM], [-110, 330, 4.5 + TM], apos(g0, 0, 0, 14), apos(g0, 0, 0)],
  });
  W.boxSide.add(base.mesh);
  // The adhesive tie mounts on the table (19 x 19 x 3 mm) and the ties round the trunk: [x, y, dir, r].
  const MOUNTS = [[-105, 380, "y", 10.5], [-105, 470, "y", 10.5], [-70, 545, "x", 5.4], [-10, 562, "x", 5.6],
    [250, 565, "x", 5.6], [-30, 556, "x", 5.4], [40, 556, "x", 5.4], [120, 556, "x", 5.4]];
  W.mounts = MOUNTS;
  const mm = new THREE.InstancedMesh(new THREE.BoxGeometry(19, TM, 19), new THREE.MeshStandardMaterial({ color: 0xd9d9d4, roughness: 0.6 }), MOUNTS.length);
  MOUNTS.forEach(([mx, my], k) => mm.setMatrixAt(k, new THREE.Matrix4().makeTranslation(f2s([mx, my, TM / 2]))));
  mm.receiveShadow = true;
  W.statics.add(mm);
  W.staticTies = MOUNTS.map(([mx, my, d, r]) => {
    const zc = d === "y" ? 4.5 + TM : r === 5.6 ? 2.25 + TM : 4.5 + TM;
    return [V(mx, my, zc), d === "y" ? V(0, 1, 0) : V(1, 0, 0), r];
  });
  // --- USB and the power cord at the control box.
  const usb = an(m, "ctrl_usb"), pw = an(m, "ctrl_power");
  const u = addCable({ name: "USB", r: 2.0, bend: 20, n: 80, color: 0x2a2c30, static: true,
    route: () => [apos(usb, 0, 0, 22), apos(usb, 0, 0, 34), [-430, 130, 2], [-520, 60, 2], [-552, 40, 2], [-566, 36, -30], [-566, 36, -200]] });
  const p = addCable({ name: "power", r: 3.5, bend: 30, n: 80, color: 0x101010, static: true,
    route: () => [apos(pw, 0, 0, 34), apos(pw, 0, 0, 48), [-330, 420, 3.5], [-400, 640, 3.5], [-420, 752, 3.5], [-424, 768, -30], [-424, 768, -200]] });
  W.boxSide.add(u.mesh, p.mesh);
  // The plugs at the box: the micro USB plug and the IEC C13 plug (simple shapes).
  const plugMat = new THREE.MeshStandardMaterial({ color: 0x1c1d20, roughness: 0.5 });
  const up = new THREE.Mesh(new THREE.BoxGeometry(22, 7, 11), plugMat);
  up.position.copy(f2s(apos(usb, 0, 0, 11)));
  const pp = new THREE.Mesh(new THREE.BoxGeometry(24, 34, 30), plugMat);
  pp.position.copy(f2s(apos(pw, 0, 0, 17)));
  W.boxSide.add(up, pp);
  W.boxSide.visible = A.ctrlBox.visible;
  // The Dupont junction of the servo pigtail and the extension: two housings on the lead.
  const dmat = new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.5 });
  W.dupont = new THREE.Mesh(new THREE.BoxGeometry(28, 2.6, 7.8), dmat);
  W.dupont.castShadow = true;
  ctx.machine.add(W.dupont);
}

// The ties: where the docs say to tie (the two loom ends, the chain ends, the bundle behind the
// gantry, the cables at the box).
function placeTies(x, y) {
  const list = [];
  const C = A.CFG();
  const c0 = C.carriage_y0;
  const tieAt = (cable, s, r) => {
    const pts = cable.pts;
    if (!pts.length) return;
    const i = Math.min(pts.length - 2, Math.max(0, Math.round(s * (pts.length - 1))));
    list.push([pts[i], pts[i + 1].clone().sub(pts[i]), r]);
  };
  const byName = Object.fromEntries(W.cables.map((c) => [c.name, c]));
  // The servo loom: one tie at each end (the moving tie through the slot of the X plate, the fixed tie
  // round the loom and the head harness cable).
  if (W.chainX && W.chainX.pts.length) {
    const pts = W.chainX.pts, r = W.chainX.ch.d / 2 + 0.6;
    for (const i of [2, pts.length - 4]) list.push([pts[i], pts[i + 1].clone().sub(pts[i]), r]);
  }
  // The bundle behind the gantry: Y1 and Y2 over the servo lead, and the X cables on the carriage.
  for (const [name, ss, r] of [["Y2 motor", [0.62, 0.66, 0.7, 0.74], 3.6], ["X motor", [0.42, 0.55], 2.9], ["X endstop", [0.5], 2.2],
    ["Y1 motor", [0.7], 2.9]])
    if (byName[name]) for (const s of ss) tieAt(byName[name], s, r);
  for (const t of W.staticTies || []) list.push(t);
  // The chain ends: one tie on the comb of each end link round the cables.
  if (W.chainY) {
    const ch = W.chainY.ch, cy = C.carriage_y0 + y;
    list.push([V(ch.plane.x, ch.fixed.y + W.chainY.el + 5.5, ch.fixed.z), V(0, 1, 0), [10.5, 5.0]]);
    list.push([V(ch.plane.x, cy + ch.moving.dy + W.chainY.el / 2 + 5.5, ch.moving.z), V(0, 1, 0), [10.5, 5.0]]);
  }
  const M = W.tieMesh;
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
  let n = 0;
  for (const [p, t, r] of list) {
    if (n >= M.instanceMatrix.count) break;
    const T = f2s([t.x, t.y, t.z]).normalize();
    q.setFromUnitVectors(V(1, 0, 0), T);
    if (Array.isArray(r)) sc.set(1, r[1], r[0]); // a flat loop (the chain end: 20 mm wide, 10 mm high)
    else sc.set(1, r, r);
    m.compose(f2s([p.x, p.y, p.z]), q, sc);
    M.setMatrixAt(n++, m);
  }
  M.count = n;
  M.instanceMatrix.needsUpdate = true;
}

// wiringUpdate moves the chain, the loom, the cables and the ties to machine x, y (y2: the Y2 side).
export function wiringUpdate(x, y, y2) {
  if (!W) return;
  if (W.chainY) updateChain(W.chainY, x, y);
  if (W.chainX) updateLoom(W.chainX, x, y);
  if (!W.ready) return;
  for (const c of W.cables) {
    if (c.static && c.done) continue;
    updateCable(c, x, y, y2 ?? y);
    c.done = true;
  }
  if (W.lead && W.lead.pts.length) {
    // The Dupont junction: 120 mm along the lead from BL_T.
    const pts = W.lead.pts;
    const i = Math.round(0.14 * (pts.length - 1));
    const T = pts[i + 1].clone().sub(pts[i]);
    W.dupont.position.copy(f2s([pts[i].x, pts[i].y, pts[i].z]));
    W.dupont.quaternion.setFromUnitVectors(V(1, 0, 0), f2s([T.x, T.y, T.z]).normalize());
  }
  placeTies(x, y);
}

// For tests: the cables and their points.
if (typeof window !== "undefined") window.__wiring = () => W;
