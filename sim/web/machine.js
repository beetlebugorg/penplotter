// The 3D view of the table pen plotter (built from CR-10 V3 parts).
//
// The plotter stands on a table. The paper lies on a cutting mat on the table
// and does not move. The gantry rides on two Y rails. The pen carriage rides
// on the gantry beam.
//
// Two coordinate frames:
//   Frame coordinates (mm): the origin is the front-left outer corner of the
//   frame, on the table top. X goes to the right, Y goes to the back, Z goes up.
//   Scene coordinates (three.js): Y is up. f2s() converts frame to scene.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { connect, decodeLcd, LCD_OFF, LCD_ON, beep, unlockAudio } from "./common.js";
import { initWiring, wiringBuild, wiringUpdate, wiringShowBox, hiddenParts } from "./wiring.js";

// ---------------------------------------------------------------------------
// Machine data. /stl/frame.json replaces these values when it loads.
// The values are the measured frame of the plotter.
const DEFAULT_CFG = {
  // X: the stock Creality X carriage plate on three V-wheels on a 2020 beam. Y: three V-wheels
  // on vertical axles in the side slots of each 2040 rail: two outside, one inside. The cross bars
  // are 2020. The moving cables run in a Y drag chain and a servo loom (chains).
  camera: {"pos": [200.0, 537.1, 616.0], "mast": {"box": [191.07, 528.15, 11.0, 208.93, 546.0, 601.0]}},
  bars: [{"name": "front bar", "box": [0.0, 0.0, 37.0, 400.0, 20.0, 57.0]}, {"name": "back bar", "box": [0.0, 500.0, 37.0, 400.0, 520.0, 57.0]}],
  rails: [{"name": "left rail", "box": [0.0, 20.0, 37.0, 40.0, 500.0, 57.0]}, {"name": "right rail", "box": [360.0, 20.0, 37.0, 400.0, 500.0, 57.0]}],
  feet: [[31.0, 37.5], [31.0, 482.5], [369.0, 37.5], [369.0, 482.5]],
  foot: {"d": 28.0, "h": 37.0},
  beam: {"box": [-7.5, 63.94, 88.63, 407.5, 83.94, 108.63], "profile": [20.0, 20.0]},
  x_motor: {"pos": [20.0, 55.34, 141.21], "shaft": "+y", "body_y": [-2.16, 37.84]},
  x_idler: {"pos": [383.0, 55.34, 141.21], "slot_x": 5.0},
  x_belt: {"y": 55.34, "z_runs": [134.5, 147.92], "clamped": "lower", "plane": "vertical loop in front of the X carriage plate; the axles point along y"},
  x_carriage: {"plate_front_y": 60.34, "box": [28.89, 60.34, 66.73, 125.57, 82.84, 143.3]},
  x_wheels: [[54.84, 73.94, 118.73], [99.44, 73.94, 118.73], [77.34, 73.94, 78.53]],
  y_wheels: [[[-10.1, 51.94, 47.0], [-10.1, 95.94, 47.0], [50.1, 73.94, 47.0]], [[410.1, 51.94, 47.0], [410.1, 95.94, 47.0], [349.9, 73.94, 47.0]]],
  y_wheel_axis: "z",
  home_pen: [69.49, 36.79],
  carriage_y0: 73.94,
  carriage_x0: 70.42,
  x_clamp: [30.42, 106.42],
  travel: [245.9, 391.8],
  pen_lift_mm: 6.95,
  paper_z: 0,
  // Y: each belt lies still on its rail, the ends on the bar faces; the motor and the omega loop ride on the Y carriage.
  y_belt: {"x": [31.5, 368.5], "z": 57.7, "w": 6.0, "t": 1.4, "ends": [7.0, 546.0], "end_z": 61.7, "clips": [[9.2, 27.2], [525.8, 543.8]], "omega": {"pulley": {"dy": 33.0, "z": 88.75, "r": 5.36}, "idlers": [{"dy": 20.09, "z": 66.5, "r": 6.1}, {"dy": 45.91, "z": 66.5, "r": 6.1}], "x": [27.25, 35.75], "wrap_deg": 180.0}, "motor": {"x": [49.0, 89.0], "dy": 33.0, "z": 88.75, "size": 42.3, "shaft": "-x on the left, +x on the right (mirror)"}},
  chains: [{"name": "y", "kind": "drag chain, openable", "inner_hw": [10.0, 20.0], "outer_hw": [15.0, 27.0], "bend_r": 28.0, "plane": {"type": "y-z", "x": -50.0}, "axis": "y", "bend_side": "-y (front)", "fixed": {"y": 492.0, "z": 7.5, "moves": "static"}, "moving": {"dy": 26.0, "z": 63.5, "moves": "gantry"}, "runs": 394.0, "end_link": 12.0, "bend_formula": "y_bend = (fixed_y + moving_y - runs) / 2"}, {"name": "x", "kind": "split wire loom, free slack loop (catenary)", "axis": "x", "d": 12.7, "length": 188.8, "plane": {"type": "x-z", "dy": 39.95}, "z": 141.85, "fixed": {"x": 119.5, "moves": "gantry"}, "moving": {"dx": -33.0, "moves": "carriage", "tie": {"dy": -20.25, "z": 126.0}}}],
  endstops: [{"name": "y1", "pos": [7.2, 35.0, 71.7]}, {"name": "y2", "pos": [392.8, 35.0, 71.7]}, {"name": "x", "pos": [28.0, 47.04, 106.0]}],
  parts: [],
};
let CFG = DEFAULT_CFG;

let PAPER_Z = 0; // top of the paper. frame.json can set it (paper_z).
const MAT = [610, 457, 1.5];
const PEN_LEN = 140;
const TABLE = { x0: -560, x1: 760, y0: -260, y1: 760, t: 32, legH: 720 };

// f2s converts frame coordinates to scene coordinates.
function f2s(x, y, z) {
  return new THREE.Vector3(x, z, -y);
}

// machineToFrame converts a machine position (mm from the home corner) to
// the frame position of the pen tip. Change this one function if the home
// corner of the machine changes.
function machineToFrame(x, y) {
  return [CFG.home_pen[0] + x, CFG.home_pen[1] + y];
}

// ---------------------------------------------------------------------------
// Renderer, scene and camera.
const view = document.getElementById("view");
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
view.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.7;

const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 5, 20000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
function homeView() {
  controls.target.copy(f2s(110, 250, 30));
  camera.position.copy(f2s(760, -820, 820));
  controls.update();
}
homeView();

// Lights.
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f99, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 2.3);
sun.position.copy(f2s(600, -500, 1400));
sun.target.position.copy(f2s(100, 260, 0));
scene.add(sun.target);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
Object.assign(sun.shadow.camera, { left: -800, right: 800, top: 800, bottom: -800, near: 200, far: 4000 });
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.5;
scene.add(sun);
const fill = new THREE.DirectionalLight(0xdfe8ff, 0.45);
fill.position.copy(f2s(-900, 900, 600));
scene.add(fill);

// Floor.
const floorMat = new THREE.MeshStandardMaterial({ roughness: 0.95 });
const floor = new THREE.Mesh(new THREE.CircleGeometry(6000, 64), floorMat);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -TABLE.t - TABLE.legH;
floor.receiveShadow = true;
scene.add(floor);
function applyTheme() {
  const dark = matchMedia("(prefers-color-scheme: dark)").matches;
  const bg = new THREE.Color(dark ? 0x1b1d21 : 0xe6e8eb);
  scene.background = bg;
  scene.fog = new THREE.Fog(bg, 3000, 7000);
  floorMat.color.copy(bg).multiplyScalar(dark ? 1.2 : 0.93);
}
applyTheme();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);

// ---------------------------------------------------------------------------
// Textures and materials.
function canvasTexture(w, h, draw, repeat = false) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = renderer.capabilities.getMaxAnisotropy();
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}
// Wood grain for the table top.
const woodTex = canvasTexture(1024, 512, (g, w, h) => {
  g.fillStyle = "#b98a5a";
  g.fillRect(0, 0, w, h);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 260; i++) {
    const y = rnd() * h;
    g.strokeStyle = `rgba(${90 + rnd() * 40},${55 + rnd() * 25},${25 + rnd() * 15},${0.08 + rnd() * 0.18})`;
    g.lineWidth = 1 + rnd() * 4;
    g.beginPath();
    g.moveTo(0, y);
    for (let x = 0; x <= w; x += 32) g.lineTo(x, y + Math.sin(x / 90 + i) * 5 + (rnd() - 0.5) * 2);
    g.stroke();
  }
  // Plank joints.
  g.fillStyle = "rgba(60,35,15,0.35)";
  for (let y = 0; y < h; y += 128) g.fillRect(0, y, w, 2);
});
// Cutting mat: light grey with a 10 mm grid and a 50 mm grid (2 px per mm).
const matTex = canvasTexture(MAT[0] * 2, MAT[1] * 2, (g, w, h) => {
  g.fillStyle = "#c9ced3";
  g.fillRect(0, 0, w, h);
  for (let mm = 0; mm <= MAT[0]; mm += 10) {
    g.fillStyle = mm % 50 === 0 ? "rgba(40,50,60,0.55)" : "rgba(40,50,60,0.22)";
    g.fillRect(mm * 2 - (mm % 50 === 0 ? 1 : 0.5), 0, mm % 50 === 0 ? 2 : 1, h);
  }
  for (let mm = 0; mm <= MAT[1]; mm += 10) {
    g.fillStyle = mm % 50 === 0 ? "rgba(40,50,60,0.55)" : "rgba(40,50,60,0.22)";
    g.fillRect(0, h - mm * 2 - (mm % 50 === 0 ? 1 : 0.5), w, mm % 50 === 0 ? 2 : 1);
  }
  g.fillStyle = "rgba(40,50,60,0.6)";
  g.font = "bold 14px sans-serif";
  for (let mm = 50; mm < MAT[0]; mm += 50) g.fillText(String(mm / 10), mm * 2 + 3, h - 6);
  for (let mm = 50; mm < MAT[1]; mm += 50) g.fillText(String(mm / 10), 6, h - mm * 2 - 4);
});

const M = {
  extrusion: new THREE.MeshStandardMaterial({ color: 0x1c1e21, metalness: 0.55, roughness: 0.42 }),
  alu: new THREE.MeshStandardMaterial({ color: 0xc3c7cc, metalness: 0.9, roughness: 0.32 }),
  aluDark: new THREE.MeshStandardMaterial({ color: 0x2b2e33, metalness: 0.7, roughness: 0.4 }),
  steel: new THREE.MeshStandardMaterial({ color: 0xd8dade, metalness: 1, roughness: 0.22 }),
  motor: new THREE.MeshStandardMaterial({ color: 0x17181a, metalness: 0.3, roughness: 0.55 }),
  pom: new THREE.MeshStandardMaterial({ color: 0x111214, metalness: 0, roughness: 0.5 }),
  rubber: new THREE.MeshStandardMaterial({ color: 0x2a2b2e, roughness: 0.95 }),
  wood: new THREE.MeshStandardMaterial({ map: woodTex, roughness: 0.7 }),
  woodSide: new THREE.MeshStandardMaterial({ color: 0x8e6239, roughness: 0.75 }),
  // The underside of the table top: a light see-through tint, so the view from below shows the plotter.
  woodUnder: new THREE.MeshStandardMaterial({ color: 0x8e6239, roughness: 0.75, transparent: true, opacity: 0.15, depthWrite: false }),
  hidden: new THREE.MeshBasicMaterial({ visible: false }),
  mat: new THREE.MeshStandardMaterial({ map: matTex, roughness: 0.85 }),
  paper: new THREE.MeshStandardMaterial({ color: 0xfbfbf6, roughness: 0.92 }),
  pla: new THREE.MeshStandardMaterial({ color: 0x7fb6e0, roughness: 0.6 }),
  plaDark: new THREE.MeshStandardMaterial({ color: 0x3a3d42, roughness: 0.65 }),
  servo: new THREE.MeshStandardMaterial({ color: 0x2d62c8, roughness: 0.5 }),
  servoHorn: new THREE.MeshStandardMaterial({ color: 0xf2f2f2, roughness: 0.5 }),
  pen: new THREE.MeshStandardMaterial({ color: 0x2341a8, roughness: 0.35, metalness: 0.1 }),
  penCap: new THREE.MeshStandardMaterial({ color: 0xf4f4f4, roughness: 0.4 }),
  boxSteel: new THREE.MeshStandardMaterial({ color: 0x25272b, metalness: 0.45, roughness: 0.5 }),
  switchOff: new THREE.MeshStandardMaterial({ color: 0x1f6f3a, roughness: 0.5 }),
  pcb: new THREE.MeshStandardMaterial({ color: 0x1a7a3a, roughness: 0.6 }),
  cable: new THREE.MeshStandardMaterial({ color: 0x141414, roughness: 0.55 }),
  cableRed: new THREE.MeshStandardMaterial({ color: 0xa0221c, roughness: 0.55 }),
  usb: new THREE.MeshStandardMaterial({ color: 0x9aa0a8, roughness: 0.6 }),
  white: new THREE.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.6 }),
};
// The see-through toggle (T) changes these materials.
const toolMats = [M.pla, M.plaDark, M.servo];

// Belt material: GT2 teeth (2 mm pitch) as a stripe texture. Each run gets its own texture.
function beltMaterial(len) {
  const t = canvasTexture(32, 8, (g) => {
    g.fillStyle = "#1a1a1a";
    g.fillRect(0, 0, 32, 8);
    g.fillStyle = "#3a3a3a";
    g.fillRect(0, 0, 14, 8);
  }, true);
  t.repeat.set(len / 2, 1);
  return new THREE.MeshStandardMaterial({ map: t, roughness: 0.8 });
}

// ---------------------------------------------------------------------------
// Geometry helpers. Unless a comment says otherwise, positions are frame coordinates.

// profileShape draws the cross-section of a V-slot extrusion (w x h mm)
// with a slot in the middle of each 20 mm face and a centre hole per cell.
function profileShape(w, h) {
  const s = new THREE.Shape();
  const hw = w / 2, hh = h / 2, sl = 3.1, dp = 4.5;
  const centers = (n) => Array.from({ length: Math.max(1, Math.round(n / 20)) }, (_, i) => -n / 2 + 10 + 20 * i);
  const pts = [[-hw, -hh]];
  for (const c of centers(w)) pts.push([c - sl, -hh], [c - sl + 1.5, -hh + dp], [c + sl - 1.5, -hh + dp], [c + sl, -hh]);
  pts.push([hw, -hh]);
  for (const c of centers(h)) pts.push([hw, c - sl], [hw - dp, c - sl + 1.5], [hw - dp, c + sl - 1.5], [hw, c + sl]);
  pts.push([hw, hh]);
  for (const c of centers(w).reverse()) pts.push([c + sl, hh], [c + sl - 1.5, hh - dp], [c - sl + 1.5, hh - dp], [c - sl, hh]);
  pts.push([-hw, hh]);
  for (const c of centers(h).reverse()) pts.push([-hw, c + sl], [-hw + dp, c + sl - 1.5], [-hw + dp, c - sl + 1.5], [-hw, c - sl]);
  s.moveTo(pts[0][0], pts[0][1]);
  for (const p of pts.slice(1)) s.lineTo(p[0], p[1]);
  s.closePath();
  for (const cx of centers(w))
    for (const cy of centers(h)) {
      const hole = new THREE.Path();
      hole.absarc(cx, cy, 2.1, 0, Math.PI * 2, true);
      s.holes.push(hole);
    }
  return s;
}

// extrusionBox makes a V-slot extrusion that fills a frame box [x0,y0,z0,x1,y1,z1].
// The longest side of the box is the long axis of the extrusion.
const geoCache = new Map();
const FRAME_AXES = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, -1), new THREE.Vector3(0, 1, 0)];
function extrusionBox(b) {
  const d = [b[3] - b[0], b[4] - b[1], b[5] - b[2]];
  const long = d.indexOf(Math.max(...d));
  const [a1, a2] = [0, 1, 2].filter((i) => i !== long);
  const w = d[a1], h = d[a2], len = d[long];
  const key = `${w}x${h}x${len}`;
  let g = geoCache.get(key);
  if (!g) {
    g = new THREE.ExtrudeGeometry(profileShape(w, h), { depth: len, bevelEnabled: false, curveSegments: 10 });
    g.translate(0, 0, -len / 2);
    g.computeVertexNormals();
    geoCache.set(key, g);
  }
  const m = new THREE.Mesh(g, M.extrusion);
  const bx = FRAME_AXES[a1].clone(), by = FRAME_AXES[a2].clone(), bz = FRAME_AXES[long].clone();
  const basis = new THREE.Matrix4().makeBasis(bx, by, bz);
  // Keep a right-handed basis. The profile is symmetric, so a flipped X looks the same.
  if (basis.determinant() < 0) basis.makeBasis(bx.negate(), by, bz);
  m.quaternion.setFromRotationMatrix(basis);
  m.position.copy(f2s((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2));
  return m;
}

// fbox makes a box from a frame box [x0,y0,z0,x1,y1,z1].
function fbox(b, mat) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(b[3] - b[0], b[5] - b[2], b[4] - b[1]), mat);
  m.position.copy(f2s((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2));
  return m;
}

// fcyl makes a cylinder. axis is the frame axis "x", "y" or "z". c is the centre.
function fcyl(r, len, mat, axis, c, segs = 24) {
  const g = new THREE.CylinderGeometry(r, r, len, segs);
  if (axis === "x") g.rotateZ(Math.PI / 2);
  if (axis === "y") g.rotateX(Math.PI / 2);
  const m = new THREE.Mesh(g, mat);
  m.position.copy(f2s(...c));
  return m;
}

// vWheel makes a stock Creality (OpenBuilds solid) V-wheel with its two 625 bearings. axis is the
// frame axis of the wheel. The geometries are shared by all wheels (9 wheels: 6 on Y, 3 on X).
// The profile: flat faces out to r 9.6, a short land, 45 degree flanks, a flat tip (OD 24.4, 10.2 wide).
const wheelGeo = new THREE.LatheGeometry(
  [[8, -5.1], [9.6, -5.1], [9.6, -3.1], [12.2, -0.5], [12.2, 0.5], [9.6, 3.1], [9.6, 5.1], [8, 5.1]].map(([r, y]) => new THREE.Vector2(r, y)),
  40,
);
// The bearing faces: the outer race, the shield (a little in from the face), the inner race.
const bearingGeo = new THREE.LatheGeometry(
  [[2.5, -5.1], [3.6, -5.1], [3.6, -4.85], [7.2, -4.85], [7.2, -5.1], [8, -5.1], [8, 5.1], [7.2, 5.1], [7.2, 4.85],
    [3.6, 4.85], [3.6, 5.1], [2.5, 5.1]].map(([r, y]) => new THREE.Vector2(r, y)),
  28,
);
function vWheel(axis, c) {
  const outer = new THREE.Group();
  const inner = new THREE.Group(); // turns about its own axis
  inner.add(new THREE.Mesh(wheelGeo, M.pom));
  inner.add(new THREE.Mesh(bearingGeo, M.steel));
  inner.add(new THREE.Mesh(new THREE.BoxGeometry(0.8, 10.4, 2.5), M.aluDark).translateX(10.6)); // a mark to show the turn
  outer.add(inner);
  if (axis === "x") outer.rotation.z = Math.PI / 2;
  if (axis === "y") outer.rotation.x = Math.PI / 2;
  outer.position.copy(f2s(...c));
  outer.userData.spin = inner;
  return outer;
}

// nema17 makes a 42 x 42 x 40 stepper motor with the shaft up (frame +Z).
// c is the centre of the body.
function nema17(c, len = 40) {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.BoxGeometry(42, len - 16, 42), M.motor));
  for (const s of [-1, 1]) {
    const cap = new THREE.Mesh(new THREE.BoxGeometry(42, 8, 42), M.aluDark);
    cap.position.y = s * (len / 2 - 4);
    g.add(cap);
  }
  const boss = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 2, 24), M.aluDark);
  boss.position.y = len / 2 + 1;
  g.add(boss);
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 22, 12), M.steel);
  shaft.position.y = len / 2 + 11;
  g.add(shaft);
  const conn = new THREE.Mesh(new THREE.BoxGeometry(16, 10, 6), M.white);
  conn.position.set(0, -len / 2 + 10, -24); // at the back (frame +Y)
  g.add(conn);
  g.position.copy(f2s(...c));
  return g;
}

// pulley makes a 20-tooth GT2 pulley or a smooth idler. axis is the frame
// axis of the pulley ("z" or "y"). The returned group has userData.spin, the part that turns.
function pulley(c, teeth = true, axis = "z") {
  const outer = new THREE.Group();
  const spin = new THREE.Group();
  const r = teeth ? 6.1 : 6.5;
  spin.add(new THREE.Mesh(new THREE.CylinderGeometry(r, r, 7, 20), M.alu));
  for (const s of [-1, 1]) {
    const f = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 1, 24), M.alu);
    f.position.y = s * 4;
    spin.add(f);
  }
  if (teeth) {
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 7, 24), M.alu);
    hub.position.y = -8;
    spin.add(hub);
  }
  const mark = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.2, 6), M.motor);
  mark.position.set(0, 4.6, 3.5);
  spin.add(mark);
  outer.add(spin);
  if (axis === "y") outer.rotation.x = Math.PI / 2; // the hub goes to frame +Y (toward the motor)
  if (axis === "x") outer.rotation.z = -Math.PI / 2;
  outer.position.copy(f2s(...c));
  outer.userData.spin = spin;
  return outer;
}

// endstop makes a switch on a small PCB. dir is the frame direction of the lever.
function endstop(c, dir) {
  const g = new THREE.Group();
  const mat = M.switchOff.clone();
  const pcb = new THREE.Mesh(new THREE.BoxGeometry(16, 2, 40), M.pcb);
  pcb.position.y = 1;
  g.add(pcb);
  const sw = new THREE.Mesh(new THREE.BoxGeometry(12, 7, 20), mat);
  sw.position.set(0, 5.5, 6);
  g.add(sw);
  const lever = new THREE.Mesh(new THREE.BoxGeometry(2, 1, 22), M.steel);
  lever.position.set(0, 9.5, 14);
  lever.rotation.x = 0.15;
  g.add(lever);
  // The lever points along local +Z. Turn it to the frame direction.
  g.rotation.y = { "-y": 0, "+y": Math.PI, "+x": Math.PI / 2, "-x": -Math.PI / 2 }[dir] ?? 0;
  g.position.copy(f2s(...c));
  g.userData.mat = mat;
  return g;
}

// beltRun makes one straight belt run between two frame points (along X or along Y).
// The belt stands on edge. With flat = true it lies flat (a vertical belt loop).
function beltRun(p0, p1, flat = false) {
  const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
  const alongX = Math.abs(p1[0] - p0[0]) > Math.abs(p1[1] - p0[1]);
  const mat = beltMaterial(len);
  const g = flat
    ? new THREE.BoxGeometry(len, 1.4, 6)
    : alongX ? new THREE.BoxGeometry(len, 6, 1.4) : new THREE.BoxGeometry(1.4, 6, len);
  const m = new THREE.Mesh(g, mat);
  m.position.copy(f2s((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, p0[2]));
  m.userData.tex = mat.map;
  return m;
}

// clampedRun makes the run of an open belt that a carriage clamps. It is two parts: from the
// fixed end a to the clamp, and from the clamp to the fixed end b. ax is 0 (frame X) or 1
// (frame Y). The clamp spans c0..c1 at home; update(d) moves it d mm along ax.
function clampedRun(a, b, ax, c0, c1, flat = false) {
  const g = flat
    ? ax === 0 ? new THREE.BoxGeometry(1, 1.4, 6) : new THREE.BoxGeometry(6, 1.4, 1)
    : ax === 0 ? new THREE.BoxGeometry(1, 6, 1.4) : new THREE.BoxGeometry(1.4, 6, 1);
  const parts = [0, 1].map(() => {
    const mat = beltMaterial(1);
    const m = new THREE.Mesh(g, mat);
    m.userData.tex = mat.map;
    return m;
  });
  const set = (m, u0, u1, d) => {
    const len = Math.max(0.01, u1 - u0);
    const p = [...a];
    p[ax] = (u0 + u1) / 2;
    m.position.copy(f2s(...p));
    if (ax === 0) m.scale.x = len;
    else m.scale.z = len;
    m.userData.tex.repeat.set(len / 2, 1);
    m.userData.tex.offset.x = d / 2;
  };
  const update = (d) => {
    set(parts[0], a[ax], c0 + d, d);
    set(parts[1], c1 + d, b[ax], d);
  };
  update(0);
  return { parts, update };
}

// beltSeg makes a straight flat belt between two frame points in any direction (width along frame X).
function beltSeg(p0, p1) {
  const a = f2s(...p0), b = f2s(...p1);
  const len = a.distanceTo(b);
  const mat = beltMaterial(len);
  const m = new THREE.Mesh(new THREE.BoxGeometry(6, 1.4, len), mat);
  m.position.copy(a).add(b).multiplyScalar(0.5);
  m.lookAt(b);
  return m;
}

// toothedWrapGeo makes the half loop of a GT2 belt (6 mm wide) around a 20T pulley: the back, and
// one tooth (2 mm pitch) in each groove on the inside. r is the radius under the belt (the tooth
// tips). The arc goes from angle 0 to PI in the XY plane, 6 mm deep along Z (centred). Shared by r.
const wrapGeos = new Map();
function toothedWrapGeo(r) {
  const key = r.toFixed(2);
  if (wrapGeos.has(key)) return wrapGeos.get(key);
  const back = r + 1.4, land = r + 0.75, tr = 0.555;
  const sh = new THREE.Shape();
  sh.moveTo(back, 0);
  sh.absarc(0, 0, back, 0, Math.PI, false);
  // The inside, back from PI to 0: the land with a round tooth every 18 degrees (20 teeth).
  sh.lineTo(-land, 0);
  const n = 20, steps = 48;
  for (let i = 0; i <= steps; i++) {
    const a = Math.PI - (Math.PI * i) / steps;
    const k = (a * n) / (2 * Math.PI) - 0.5; // tooth centres at (k + 0.5) * 18 degrees
    const d = Math.abs(k - Math.round(k)) * ((2 * Math.PI * (r + 0.5)) / n); // mm from the tooth centre
    const depth = d < tr ? Math.sqrt(tr * tr - d * d) * (0.75 / tr) : 0;
    const rr = land - depth;
    sh.lineTo(rr * Math.cos(a), rr * Math.sin(a));
  }
  sh.lineTo(back, 0);
  const g = new THREE.ExtrudeGeometry(sh, { depth: 6, bevelEnabled: false, curveSegments: 24 });
  g.translate(0, 0, -3);
  wrapGeos.set(key, g);
  return g;
}

// beltOver makes the half loop of a belt over the top of a pulley whose axle points along frame X.
function beltOver(c, r) {
  const m = new THREE.Mesh(toothedWrapGeo(r), M.motor);
  m.rotation.y = Math.PI / 2;
  m.position.copy(f2s(...c));
  return m;
}

// beltHalf makes the half loop of a flat belt round a pulley whose axle points along frame X, on the
// -y side (s = -1) or the +y side (s = +1) of the pulley.
function beltHalf(c, r, s) {
  const m = new THREE.Mesh(toothedWrapGeo(r), M.motor);
  m.rotation.y = Math.PI / 2;
  const holder = new THREE.Group();
  holder.add(m);
  holder.rotation.x = s < 0 ? Math.PI / 2 : -Math.PI / 2;
  holder.position.copy(f2s(...c));
  return holder;
}

// beltArc makes the half loop of a belt around a pulley. side is the frame
// direction from the pulley centre to the outside of the loop.
function beltArc(c, r, side, vertical = false) {
  const m = new THREE.Mesh(toothedWrapGeo(r), M.motor);
  if (vertical) {
    // The loop is in the frame XZ plane. The half torus bulges to scene +Y; turn it to the side.
    m.rotation.z = side === "-x" ? Math.PI / 2 : -Math.PI / 2;
    m.position.copy(f2s(...c));
    return m;
  }
  const ang = { "-y": 0, "+y": Math.PI, "+x": Math.PI / 2, "-x": -Math.PI / 2 }[side];
  // The torus lies in the XY plane. Lay it flat and turn it to the side.
  const holder = new THREE.Group();
  m.rotation.x = Math.PI / 2;
  holder.add(m);
  holder.rotation.y = ang;
  holder.position.copy(f2s(...c));
  return holder;
}

// ---------------------------------------------------------------------------
// Cables. A cable is a tube along a smooth curve through frame points.
function makeCable(points, mat = M.cable, radius = 2.4, parent = null) {
  const mesh = new THREE.Mesh(new THREE.BufferGeometry(), mat);
  mesh.castShadow = true;
  mesh.userData.radius = radius;
  setCable(mesh, points);
  (parent || machine).add(mesh);
  return mesh;
}
function setCable(mesh, points) {
  const rough = new THREE.CatmullRomCurve3(points.map((p) => f2s(...p)), false, "centripetal");
  const r = mesh.userData.radius;
  const n = Math.max(24, Math.round(rough.getLength() / 6));
  // Keep the cable on or above the table: the curve can dip between the points.
  const pts = rough.getSpacedPoints(n).map((v) => {
    v.y = Math.max(v.y, r + PAPER_Z - 0.1); // on the mat or above it
    return v;
  });
  const curve = new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.2);
  mesh.geometry.dispose();
  mesh.geometry = new THREE.TubeGeometry(curve, n, r, 8, false);
}

// ---------------------------------------------------------------------------
// The table, the cutting mat and the control pod do not change with frame.json.
// The table top is under the mat: tableGroup moves it with the paper height.
const tableGroup = new THREE.Group();
scene.add(tableGroup);
{
  const t = TABLE;
  const top = new THREE.Mesh(new THREE.BoxGeometry(t.x1 - t.x0, t.t, t.y1 - t.y0), [
    M.woodSide, M.woodSide, M.wood, M.woodUnder, M.woodSide, M.woodSide,
  ]);
  top.position.copy(f2s((t.x0 + t.x1) / 2, (t.y0 + t.y1) / 2, -t.t / 2));
  woodTex.repeat.set(1, 1);
  top.receiveShadow = top.castShadow = true;
  tableGroup.add(top);
  for (const x of [t.x0 + 50, t.x1 - 50])
    for (const y of [t.y0 + 50, t.y1 - 50]) {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(60, t.legH, 60), M.woodSide);
      leg.position.copy(f2s(x, y, -t.t - t.legH / 2));
      leg.castShadow = true;
      tableGroup.add(leg);
    }
}

// The LCD texture. The control pod shows it in the lid window.
const lcdData = new Uint8Array(128 * 64 * 4);
const lcdTex = new THREE.DataTexture(lcdData, 128, 64, THREE.RGBAFormat);
lcdTex.magFilter = THREE.NearestFilter;
lcdTex.minFilter = THREE.LinearFilter;
lcdTex.colorSpace = THREE.SRGBColorSpace;
function setLcdPixels(px, w, h) {
  if (w !== 128 || h !== 64) return;
  // The texture origin is the bottom-left corner, so the rows go in reverse order.
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const c = px[y * w + x] ? LCD_ON : LCD_OFF;
      const o = ((h - 1 - y) * w + x) * 4;
      lcdData[o] = c[0];
      lcdData[o + 1] = c[1];
      lcdData[o + 2] = c[2];
      lcdData[o + 3] = 255;
    }
  lcdTex.needsUpdate = true;
}
setLcdPixels(new Uint8Array(128 * 64), 128, 64);

// The control pod: a small printed desk console with the LCD and the knob in the
// sloped lid. Pod coordinates: the floor centre is the origin, Z is up, +Y goes to
// the back wall. The pod stands on the table, left of the front-left frame corner,
// with the back wall toward the frame.
const POD = {
  x: -135, // centre on the table, frame mm
  y: 110,
  facing: 90, // direction of the back wall: degrees from frame +X toward +Y
  w: 135,
  d: 98,
  hFront: 40,
  hBack: 60.8,
  lidTop: [0.2126, 53.48], // lid top surface: z = a * y + b (from pod_lid.stl)
  slope: (12 * Math.PI) / 180,
  lcd: [-10, 4], // window centre: x, and the distance toward the back along the slope
  knobX: 27, // knob centre: 37 mm right of the LCD board centre (x = -10)
  jack: [50, 49, 15],
};
const podGroup = new THREE.Group();
podGroup.position.copy(f2s(POD.x, POD.y, -1.6));
podGroup.rotation.y = ((POD.facing - 90) * Math.PI) / 180;
scene.add(podGroup);
const podMats = {
  base: new THREE.MeshStandardMaterial({ color: 0x3a3d42, roughness: 0.6 }),
  lid: new THREE.MeshStandardMaterial({ color: 0x7fb6e0, roughness: 0.6 }),
  knob: new THREE.MeshStandardMaterial({ color: 0x1a1b1e, roughness: 0.45 }),
};
// lidPoint returns a pod point on the lid top, t mm toward the back along the slope from y = 0.
function lidPoint(x, t, up = 0) {
  const y = t * Math.cos(POD.slope);
  const z = POD.lidTop[0] * y + POD.lidTop[1];
  return f2s(x, y - up * Math.sin(POD.slope), z + up * Math.cos(POD.slope));
}
// podBody holds the Pico W pod and its power brick. The stock board build shows the
// CR-10 V3 control box instead (ctrlBox).
const podBody = new THREE.Group();
podGroup.add(podBody);
const podShapes = new THREE.Group(); // the pod shell (drawn shapes)
podBody.add(podShapes);
{
  // Side profile in (pod y, pod z), extruded along pod X.
  const prism = (pts, mat) => {
    const sh = new THREE.Shape(pts.map(([y, z]) => new THREE.Vector2(y, z)));
    const g = new THREE.ExtrudeGeometry(sh, { depth: POD.w, bevelEnabled: false });
    g.translate(0, 0, -POD.w / 2);
    const m = new THREE.Mesh(g, mat);
    m.rotation.y = Math.PI / 2; // local X -> pod +Y, local Z -> pod X
    podShapes.add(m);
  };
  const h = POD.d / 2;
  prism([[-h, 0], [h, 0], [h, POD.hBack], [-h, POD.hFront]], podMats.base);
  const zl = (y) => POD.lidTop[0] * y + POD.lidTop[1];
  prism([[-h, POD.hFront], [h, POD.hBack], [h, zl(h)], [-h, zl(-h)]], podMats.lid);
  // Fallback knob.
  const knob = new THREE.Mesh(new THREE.CylinderGeometry(12, 12, 14, 32), podMats.knob);
  knob.position.copy(lidPoint(POD.knobX, POD.lcd[1] - 2, 7));
  knob.rotation.x = POD.slope;
  podShapes.add(knob);
  // A black frame around the LCD.
  const bezel = new THREE.Mesh(new THREE.BoxGeometry(80, 1, 48), M.rubber);
  bezel.position.copy(lidPoint(POD.lcd[0], POD.lcd[1], 0.2));
  bezel.rotation.x = POD.slope;
  podShapes.add(bezel);
}
// The live LCD in the lid window.
const podLcd = new THREE.Mesh(new THREE.PlaneGeometry(72, 40), new THREE.MeshBasicMaterial({ map: lcdTex, toneMapped: false }));
podLcd.rotation.x = -(Math.PI / 2 - POD.slope);
podLcd.position.copy(lidPoint(POD.lcd[0], POD.lcd[1], 0.8));
podBody.add(podLcd);
// Barrel jack on the back wall, the 24 V power brick on the table, and the cords.
{
  const jack = new THREE.Mesh(new THREE.CylinderGeometry(4, 4, 8, 16), M.steel);
  jack.geometry.rotateX(Math.PI / 2);
  jack.position.copy(f2s(POD.jack[0], POD.jack[1] + 3, POD.jack[2]));
  podBody.add(jack);
  const brick = new THREE.Mesh(new THREE.BoxGeometry(110, 32, 55), M.rubber);
  brick.position.copy(f2s(-140, 25, 16));
  brick.rotation.y = 0.3;
  podBody.add(brick);
  const label = new THREE.Mesh(new THREE.BoxGeometry(50, 0.4, 25), M.white);
  label.position.copy(f2s(-140, 25, 32.2));
  label.rotation.y = 0.3;
  podBody.add(label);
  const [jx, jy, jz] = POD.jack;
  makeCable([[jx, jy + 7, jz], [jx, jy + 22, 6], [jx - 60, jy + 50, 0], [-120, 70, 0], [-90, 45, 4], [-88, 40, 14]], M.cable, 2.2, podBody);
  makeCable([[-198, 30, 14], [-215, 40, 2], [-300, 20, 0], [-420, -60, 0], [-520, -120, 0]], M.cable, 3, podBody);
}
podBody.traverse((o) => {
  if (o.isMesh) o.castShadow = o.receiveShadow = true;
});
podLcd.castShadow = false;
// The stock CR-10 V3 control box beside the frame, as in hardware/model.py (frame mm:
// x -360 to -70, y 70 to 280, 85 mm high; the size is an ESTIMATE). The LCD and the knob
// are on the front face.
const ctrlBox = new THREE.Group();
ctrlBox.visible = false;
scene.add(ctrlBox);
{
  const bx0 = -360, by0 = 70, bw = 290, bd = 210, bh = 85;
  const body = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, bd), new THREE.MeshStandardMaterial({ color: 0x2b2d31, roughness: 0.5 }));
  body.position.copy(f2s(bx0 + bw / 2, by0 + bd / 2, bh / 2));
  ctrlBox.add(body);
  const bezel = new THREE.Mesh(new THREE.BoxGeometry(100, 52, 1), M.rubber);
  bezel.position.copy(f2s(bx0 + 90, by0 - 0.5, 44));
  ctrlBox.add(bezel);
  const lcd = new THREE.Mesh(new THREE.PlaneGeometry(72, 40), new THREE.MeshBasicMaterial({ map: lcdTex, toneMapped: false }));
  lcd.name = "ctrlLcd";
  lcd.position.copy(f2s(bx0 + 90, by0 - 1.2, 44));
  ctrlBox.add(lcd);
  const knob = new THREE.Mesh(new THREE.CylinderGeometry(9, 9, 14, 32), podMats.knob);
  knob.rotation.x = Math.PI / 2;
  knob.position.copy(f2s(bx0 + 175, by0 - 7, 44));
  ctrlBox.add(knob);
  makeCable([[bx0 + 20, by0 + bd, 20], [bx0 + 10, by0 + bd + 60, 0], [bx0 - 150, by0 + 150, 0]], M.cable, 3, ctrlBox);
  ctrlBox.traverse((o) => {
    if (o.isMesh && o !== lcd) o.castShadow = o.receiveShadow = true;
  });
}
initWiring({ f2s, ctrlBox, toolMats, CFG: () => CFG });

// showBoard shows the pod (Pico W) or the control box (stock board).
function showBoard(board) {
  const mega = board !== "pico";
  podBody.visible = !mega;
  ctrlBox.visible = mega;
  wiringShowBox(mega);
  ctrlBox.position.y = PAPER_Z - 0.1 - MAT[2];
}

// podPoint converts a pod point to frame coordinates.
function podPoint(px, py, pz) {
  podGroup.updateMatrixWorld(true);
  const v = f2s(px, py, pz).applyMatrix4(podGroup.matrixWorld);
  return [v.x, -v.z, v.y];
}
// podPort returns a frame point just behind the cable notch in the back wall.
// k is the position across the notch in mm (-16 to 16).
function podPort(k) {
  return podPoint(k, POD.d / 2 + 4, 6);
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Axis labels: X, Y and Z arrows at the front left corner of the frame (machine
// directions: X to the right, Y to the back, Z up), and the names of the two Y sides.
// The A key shows or hides them.
let axesOn = true;
const axisGroups = [];
function textSprite(text, color, size = 34) {
  const t = canvasTexture(256, 128, (g, w, h) => {
    g.font = "bold 84px system-ui, sans-serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.lineWidth = 10;
    g.strokeStyle = "rgba(0,0,0,0.75)";
    g.strokeText(text, w / 2, h / 2);
    g.fillStyle = color;
    g.fillText(text, w / 2, h / 2);
  });
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, toneMapped: false }));
  sp.scale.set(size * 2, size, 1);
  sp.renderOrder = 10;
  return sp;
}
function axisLabels(C) {
  const g = new THREE.Group();
  const W = Math.max(...C.bars.map((b) => b.box[3]));
  const o = [-45, -45, 0]; // frame mm, in front of and left of the frame corner
  const L = 130;
  const axes = [["X", [1, 0, 0], "#ff5a4f"], ["Y", [0, 1, 0], "#4fd06b"], ["Z", [0, 0, 1], "#4f9dff"]];
  for (const [name, d, col] of axes) {
    const dir = f2s(...d).normalize();
    const arrow = new THREE.ArrowHelper(dir, f2s(...o), L, new THREE.Color(col), 20, 11);
    arrow.traverse((m) => m.material && (m.material.depthTest = false, m.renderOrder = 9));
    g.add(arrow);
    const sp = textSprite(name + "+", col);
    sp.position.copy(f2s(o[0] + d[0] * (L + 24), o[1] + d[1] * (L + 24), o[2] + d[2] * (L + 24)));
    g.add(sp);
  }
  // The Y sides: Y1 (left motor) and Y2 (right motor), at the back of the frame rails.
  for (const [name, x] of [["Y1", 20], ["Y2", W - 20]]) {
    const sp = textSprite(name, "#4fd06b", 30);
    sp.position.copy(f2s(x, Math.max(...C.bars.map((b) => b.box[4])) + 25, 120));
    g.add(sp);
  }
  g.visible = axesOn;
  axisGroups.length = 0;
  axisGroups.push(g);
  return g;
}

// The machine. buildMachine() makes it from CFG. It runs again when frame.json loads.
let machine = new THREE.Group();
scene.add(machine);
let R = {}; // references to the moving parts

function buildMachine() {
  // The old machine goes away. Its geometry is small, and some of it is shared, so it is not disposed.
  scene.remove(machine);
  machine = new THREE.Group();
  scene.add(machine);
  R = { yWheels: [[], []], xWheels: [], belts: [], clamped: [], tagged: {} };
  const tag = (name, obj) => {
    (R.tagged[name] ||= []).push(obj);
    return obj;
  };
  const C = CFG;
  const W = Math.max(...C.bars.map((b) => b.box[3]));
  const cy = C.carriage_y0;
  const [hx, hy] = C.home_pen;
  PAPER_Z = C.paper_z ?? 0;
  podGroup.position.y = PAPER_Z - 0.1 - MAT[2]; // on the table top
  // The X guide has three layouts: an MGN12 rail on a 2020 beam (x_rail), two
  // steel rods (rods), or V-wheels on a 2020 beam (beam only).
  const linear = !!C.x_rail;
  const rods = !linear && C.rods && C.rods.length ? C.rods : null;
  // beam is the box around the X guide: the 2020 extrusion, or both rods.
  const beam = rods
    ? [Math.min(...rods.map((r) => r.box[0])), Math.min(...rods.map((r) => r.box[1])), Math.min(...rods.map((r) => r.box[2])),
       Math.max(...rods.map((r) => r.box[3])), Math.max(...rods.map((r) => r.box[4])), Math.max(...rods.map((r) => r.box[5]))]
    : C.beam.box;
  const bz = (beam[2] + beam[5]) / 2; // centre height of the X guide
  const railTop = Math.max(...C.rails.map((r) => r.box[5]));
  const mirror = (x) => W - x;

  // Frame: bars, rails, feet.
  for (const b of [...C.bars, ...C.rails]) machine.add(extrusionBox(b.box));
  if (C.feet_boxes) {
    // Printed feet under the bar ends, each with a rubber pad under it.
    for (const b of C.feet_boxes) machine.add(tag("feet", fbox(b, M.pla)));
    const pad = C.foot_pads || { d: 12.7, h: 3.5, centres: C.feet };
    for (const [x, y] of pad.centres) machine.add(tag("feet", fcyl(pad.d / 2, pad.h, M.rubber, "z", [x, y, pad.h / 2])));
  } else {
    for (const [x, y] of C.feet) {
      // The stock rubber feet (ESTIMATE size) with a soft lower edge.
      const r = C.foot.d / 2, c = Math.min(2, C.foot.h / 4);
      const g = new THREE.CylinderGeometry(r, r, C.foot.h - c, 40);
      g.translate(0, c / 2, 0);
      const f = new THREE.Group();
      f.add(new THREE.Mesh(g, M.rubber));
      const lip = new THREE.Mesh(new THREE.CylinderGeometry(r, r - c, c, 40), M.rubber);
      lip.position.y = -(C.foot.h - c) / 2;
      f.add(lip);
      f.position.copy(f2s(x, y, C.foot.h / 2));
      f.traverse((o) => { if (o.isMesh) o.castShadow = o.receiveShadow = true; });
      machine.add(tag("feet", f));
    }
  }
  machine.add(axisLabels(C));

  // Camera pole: a round tube in a printed foot behind the back bar, a USB webcam on top.
  const mast = C.camera && C.camera.mast && C.camera.mast.box;
  if (mast) {
    const [cx, cy] = [(mast[0] + mast[3]) / 2, (mast[1] + mast[4]) / 2];
    const r = (mast[3] - mast[0]) / 2;
    machine.add(tag("camera", fcyl(r, mast[5] - mast[2], M.alu, "z", [cx, cy, (mast[2] + mast[5]) / 2])));
    const cam = new THREE.Group();
    cam.add(fbox([cx - 30, cy - 12, mast[5], cx + 30, cy + 12, mast[5] + 30], M.motor));
    cam.add(fcyl(7, 4, M.steel, "y", [cx, cy - 13, mast[5] + 15]));
    machine.add(tag("camera", cam));
  }

  // Y drive. Two layouts:
  // - y_belt: each belt lies still on its rail. The motor rides on the Y carriage, and the belt
  //   loops up over an idler, around the motor pulley and over a second idler (an omega loop).
  // - y_motors: the motors stand at the back corners and pull a belt loop outside the frame.
  const YB = C.y_belt;
  const zBelt = YB ? (YB.z_runs ? YB.z_runs[1] : YB.z) : C.y_motors[0].pos[2];
  const beltXs = YB ? YB.x : C.y_belt_runs.map((r) => r[0]);
  R.yPulleys = [];
  R.yIdlers = [];
  if (YB && YB.pulley) {
    // Fixed Y motors (2026-11-09): each belt is a loop over its rail, flat (width along x), round the
    // motor pulley behind the back bar and the idler in front of the front bar. The lower run passes
    // over the rail; the carriage clamps the upper run (clamp_dy: the clamp faces from carriage_y0).
    const [zl, zh] = YB.z_runs, pu = YB.pulley, id = YB.idler, cd = YB.clamp_dy;
    YB.x.forEach((x, i) => {
      const upper = clampedRun([x, id.y, zh], [x, pu.y, zh], 1, cy + cd[0], cy + cd[1], true);
      const lower = beltRun([x, id.y, zl], [x, pu.y, zl], true);
      lower.rotation.y = Math.PI / 2;
      machine.add(...upper.parts, lower);
      R.clamped.push({ run: upper, axis: "y", side: i });
      R.belts.push({ mesh: lower, axis: "y", side: i, sign: -1 });
      machine.add(beltHalf([x, id.y, pu.z], (zh - zl) / 2 - 0.7, -1), beltHalf([x, pu.y, pu.z], (zh - zl) / 2 - 0.7, 1));
      if (!C.parts || !C.parts.length) {
        const pp = pulley([x, pu.y, pu.z], true, "x"), ip = pulley([x, id.y, id.z], true, "x");
        machine.add(tag("ypulleys", pp), tag("ypulleys", ip));
        R.yPulleys.push(pp);
        R.yIdlers.push(ip);
      }
    });
  } else if (YB) {
    const om = YB.omega, [i0, i1] = om.idlers;
    const zr = (YB.end_z + i0.z - i0.r - 0.7) / 2; // the run lies just above the rail top
    YB.x.forEach((x, i) => {
      const rail = clampedRun([x, YB.ends[0], zr], [x, YB.ends[1], zr], 1, cy + i0.dy, cy + i1.dy, true);
      machine.add(...rail.parts);
      R.clamped.push({ run: rail, axis: "y", side: i });
    });
  } else {
    // Motors and idlers with printed brackets at the corners, and the belt loops.
    C.y_motors.forEach((mo, i) => {
      const [x, y, zp] = mo.pos;
      const s = i === 0 ? -1 : 1; // -1 = left side, +1 = right side
      const bodyTop = zp - 17.5;
      machine.add(nema17([x, y, bodyTop - 20]));
      const p = pulley([x, y, zp]);
      machine.add(p);
      R.yPulleys.push(p);
      // Printed bracket: a top plate under the pulley and a flange behind the back bar.
      const backY = Math.max(...C.bars.map((b) => b.box[4]));
      const x0 = Math.min(x - 24, s < 0 ? x - 24 : W - 24), x1 = Math.max(x + 24, s < 0 ? 24 : x + 24);
      machine.add(tag("ymotorbracket", fbox([x0, backY, bodyTop, x1, y + 24, bodyTop + 5], M.pla)));
      machine.add(tag("ymotorbracket", fbox([s < 0 ? x - 24 : W - 24, backY, C.foot.h, s < 0 ? 24 : x + 24, backY + 5, bodyTop], M.pla)));
    });
    C.y_idlers.forEach((id, i) => {
      const [x, y, z] = id.pos;
      const s = i === 0 ? -1 : 1;
      const p = pulley([x, y, z], false);
      machine.add(p);
      R.yIdlers.push(p);
      machine.add(fcyl(2.5, 30, M.steel, "z", [x, y, z - 5], 12));
      const frontY = Math.min(...C.bars.map((b) => b.box[1]));
      const x0 = s < 0 ? x - 16 : W - 24, x1 = s < 0 ? 24 : x + 16;
      machine.add(tag("idlerbracket", fbox([x0, y - 14, z - 12, x1, frontY, z - 7], M.pla)));
      machine.add(tag("idlerbracket", fbox([x0, frontY - 5, C.foot.h, x1, frontY, z - 7], M.pla)));
    });
    C.y_belt_runs.forEach(([xin, xout], i) => {
      const y0 = C.y_idlers[i].pos[1], y1 = C.y_motors[i].pos[1];
      // The inner run is cut. Its two ends lock in the slots at the two ends of the carriage block.
      const yc = C.y_clamp || [-44, 36];
      const inner = clampedRun([xin, y0, zBelt], [xin, y1, zBelt], 1, cy + yc[0], cy + yc[1]);
      const outer = beltRun([xout, y0, zBelt], [xout, y1, zBelt]);
      machine.add(...inner.parts, outer);
      R.clamped.push({ run: inner, axis: "y", side: i });
      R.belts.push({ mesh: outer, axis: "y", side: i, sign: 1 });
      const xc = (xin + xout) / 2, r = Math.abs(xin - xout) / 2;
      machine.add(beltArc([xc, y0, zBelt], r, "-y"), beltArc([xc, y1, zBelt], r, "+y"));
    });
  }

  // Gantry: gantryPos moves with Y. gantrySkew turns the beam when Y1 and Y2 differ.
  // gantry holds the parts in frame coordinates at machine home.
  const gantryPos = new THREE.Group();
  const gantrySkew = new THREE.Group();
  const gantry = new THREE.Group();
  const pivot = f2s(20, cy, 0);
  gantrySkew.position.copy(pivot);
  gantry.position.copy(pivot).negate();
  gantrySkew.add(gantry);
  gantryPos.add(gantrySkew);
  machine.add(gantryPos);
  Object.assign(R, { gantryPos, gantrySkew, gantry, skewSpan: W - 40 });

  // The omega loop of each fixed Y belt rides on the carriage: over the front idler, around the
  // motor pulley, over the back idler. The motor, the pulley and the idlers come from the STL
  // files (y_stepper_*, y_pulleys_*); simple shapes stand in for them without the files.
  R.yMotorConn = [];
  if (YB && YB.pulley) {
    const mo = YB.motor;
    YB.x.forEach((x, i) => {
      const mx = i === 0 ? (mo.x[0] + mo.x[1]) / 2 : W - (mo.x[0] + mo.x[1]) / 2;
      R.yMotorConn.push([mx, mo.y, mo.z + 24]);
      if (C.parts && C.parts.length) return; // the STL files draw the motors
      const motor = nema17([0, 0, 0]);
      motor.rotation.z = (i === 0 ? 1 : -1) * Math.PI / 2;
      motor.position.copy(f2s(mx, mo.y, mo.z));
      machine.add(tag("ystepper", motor));
    });
  } else if (YB) {
    const om = YB.omega, [i0, i1] = om.idlers, pu = om.pulley, mo = YB.motor;
    YB.x.forEach((x, i) => {
      const yi0 = cy + i0.dy, yi1 = cy + i1.dy, yp = cy + pu.dy;
      const zl = i0.z - i0.r - 0.7; // the belt under the idlers
      gantry.add(
        beltSeg([x, yi0, zl], [x, yi0 + i0.r + 0.7, i0.z]),
        beltSeg([x, yi0 + i0.r + 0.7, i0.z], [x, yp - pu.r - 0.7, pu.z]),
        beltOver([x, yp, pu.z], pu.r),
        beltSeg([x, yp + pu.r + 0.7, pu.z], [x, yi1 - i1.r - 0.7, i1.z]),
        beltSeg([x, yi1 - i1.r - 0.7, i1.z], [x, yi1, zl]),
      );
      const s = i === 0 ? 1 : -1; // the motor stands inward of the belt
      const mx = i === 0 ? (mo.x[0] + mo.x[1]) / 2 : W - (mo.x[0] + mo.x[1]) / 2;
      const motor = nema17([0, 0, 0]);
      motor.rotation.z = s * Math.PI / 2; // the shaft points out to the belt
      motor.position.copy(f2s(mx, cy + mo.dy, mo.z));
      gantry.add(tag("ystepper", motor));
      for (const [yy, zz, rr, teeth] of [[yp, pu.z, pu.r, true], [yi0, i0.z, i0.r, false], [yi1, i1.z, i1.r, false]])
        gantry.add(tag("ypulleys", fcyl(rr, 7, teeth ? M.alu : M.steel, "x", [x, yy, zz])));
      // The motor plug: on the back face of the motor body.
      R.yMotorConn.push([mx, cy + mo.dy + 21, mo.z - 12]);
    });
  }

  // Y guides: MGN12 rails on top of the frame rails (y_rails), or V-wheels in the rail slots.
  const yRails = C.y_rails && C.y_rails.length ? C.y_rails : null;
  if (yRails)
    for (const yr of yRails) {
      const b = yr.box;
      machine.add(tag("yrail", fbox(b, M.steel)));
      // The MGN12H block on the rail moves with the gantry.
      const xc = (b[0] + b[3]) / 2;
      gantry.add(tag("yblock", fbox([xc - 13.5, cy - 22.5, b[5] - 4, xc + 13.5, cy + 22.5, b[5] + 5], M.steel)));
    }
  // Bottom of the Y carriage plate.
  const pz0 = yRails ? Math.max(...yRails.map((r) => r.box[5])) + 5 : railTop + 1;
  C.rails.forEach((r, i) => {
    const rx0 = r.box[0], rx1 = r.box[3], rc = (rx0 + rx1) / 2;
    const s = i === 0 ? -1 : 1;
    const beltX = beltXs[i];
    const plate = [Math.min(rx0 - 12, beltX - 6), cy - 40, pz0, Math.max(rx1 + 12, beltX + 6), cy + 40, pz0 + 8];
    gantry.add(tag("ycarriage", fbox(plate, M.pla)));
    // Beam block on the plate.
    gantry.add(tag("ycarriage", fbox([rc - 18, cy - 14, pz0 + 8, rc + 18, cy + 14, Math.max(beam[2], pz0 + 20)], M.pla)));
    // Belt clamp on the outer end of the plate.
    gantry.add(tag("ycarriage", fbox([beltX - 5, cy - 12, pz0 + 8, beltX + 5, cy + 12, zBelt + 5], M.pla)));
    if (yRails) return;
    // Three wheels in the side slots of the rail: two outside, one inside. frame.json gives
    // their centres (y_wheels); the old layout used fixed offsets.
    const wz = (r.box[2] + r.box[5]) / 2;
    const off = (rx1 - rx0) / 2 + 9.5;
    const ws = C.y_wheels && C.y_wheels[i]
      ? C.y_wheels[i]
      : [[s * off, -28], [s * off, 28], [-s * off, 0]].map(([dx, dy]) => [rc + dx, cy + dy, wz]);
    // y_wheel_axis "x": the wheels stand vertical and roll on the top and bottom faces.
    const wAxis = C.y_wheel_axis || "z";
    for (const [x, y, z] of ws) {
      const w = vWheel(wAxis, [x, y, z]);
      gantry.add(w);
      R.yWheels[i].push(w.userData.spin);
      if (wAxis === "z") gantry.add(fcyl(3.5, pz0 - (z + 5.5), M.alu, "z", [x, y, (z + 5.5 + pz0) / 2], 12));
    }
  });
  let xmY, xmZ, xr, zX, xBeltY;
  // wheelsX: V-wheels on the beam with the X drive of frame.json (x_motor, x_idler, x_belt).
  const wheelsX = !rods && !linear && !!C.x_motor;
  if (rods || linear || wheelsX) {
    if (rods)
      // X rods.
      rods.forEach((r) => {
        const b = r.box;
        gantry.add(tag("rod", fcyl(r.d / 2, b[3] - b[0], M.steel, "x", [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2], 20)));
      });
    else {
      // 2020 beam, with the MGN12 rail on its front face (linear) or the V-wheels of the plate.
      gantry.add(tag("beam", extrusionBox(beam)));
      if (linear) gantry.add(tag("xrail", fbox(C.x_rail.box, M.steel)));
    }
    // X motor behind the left tower, shaft to the front. x_motor.pos is the pulley centre.
    const [px0, py0, pz0] = C.x_motor.pos;
    const [ix, iy, iz] = C.x_idler.pos;
    // shaft "-y": the body is behind the pulley. shaft "+y": the body is in front, on the motor wall.
    const front = C.x_motor.shaft === "+y";
    const bodyDy = front ? -36 : 36;
    const motor = nema17([0, 0, 0]);
    motor.rotation.x = front ? -Math.PI / 2 : Math.PI / 2;
    motor.position.copy(f2s(px0, py0 + bodyDy, pz0));
    gantry.add(tag("xmotor", motor));
    const xp = pulley([px0, py0, pz0], true, "y");
    const xi = pulley([ix, iy, iz], false, "y");
    gantry.add(tag("xmotor", xp), tag("xidler", xi));
    gantry.add(tag("xidler", fcyl(2.5, 24, M.steel, "y", [ix, iy, iz], 12)));
    Object.assign(R, { xPulley: xp, xIdler: xi });
    const xb = C.x_belt;
    xr = xb ? (xb.z_runs[1] - xb.z_runs[0]) / 2 : 6.7;
    xmY = py0 + bodyDy;
    xmZ = pz0;
    zX = pz0;
    xBeltY = py0;
    // The belt loop is vertical. One run is clamped to the X carriage (x_belt.clamped, or the upper run).
    R.xClamped = xb && xb.clamped === "lower" ? "lower" : "upper";
    const lowerMoves = R.xClamped === "lower";
    // The clamped run is cut. Its ends lock in the slots at the ends of the clamp block of the pen
    // carriage (x_clamp, frame X at home).
    const xc = C.x_clamp || [(C.carriage_x0 ?? 70.42) - 40, (C.carriage_x0 ?? 70.42) + 36];
    const zc = lowerMoves ? -xr : xr;
    const cut = clampedRun([px0, py0, pz0 + zc], [ix, iy, iz + zc], 0, xc[0], xc[1], true);
    const free = beltRun([px0, py0, pz0 - zc], [ix, iy, iz - zc], true);
    gantry.add(...cut.parts, free);
    R.clamped.push({ run: cut, axis: "x" });
    R.belts.push({ mesh: free, axis: "x", sign: 1 });
    // xr is the centre of the belt; the wrap takes the radius under the belt (the tooth tips).
    gantry.add(beltArc([px0, py0, pz0], xr - 0.7, "-x", true), beltArc([ix, iy, iz], xr - 0.7, "+x", true));
    R.xmConn = [px0, py0 + bodyDy + (front ? -10 : 10), pz0 + 24];
  } else {
    // X beam (2020), the X motor behind its left end (shaft up), and the X idler.
    gantry.add(extrusionBox(beam));
    xmY = beam[4] + 5 + 21;
    xmZ = bz;
    zX = xmZ + 20 + 8;
    gantry.add(tag("xmotor", nema17([24, xmY, xmZ])));
    gantry.add(tag("xmotor", fbox([2, beam[4], xmZ + 20, 46, xmY + 22, xmZ + 24], M.pla)));
    const xp = pulley([24, xmY, zX]);
    const xi = pulley([W - 24, xmY, zX], false);
    gantry.add(tag("xmotor", xp), tag("xidler", xi));
    gantry.add(tag("xidler", fbox([W - 40, beam[4], xmZ + 18, W - 8, xmY + 14, xmZ + 22], M.pla)));
    gantry.add(tag("xidler", fcyl(2.5, 16, M.steel, "z", [W - 24, xmY, zX - 4], 12)));
    Object.assign(R, { xPulley: xp, xIdler: xi });
    xr = 6.1;
    xBeltY = xmY - xr;
    const xin = beltRun([24, xmY - xr, zX], [W - 24, xmY - xr, zX]);
    const xout = beltRun([24, xmY + xr, zX], [W - 24, xmY + xr, zX]);
    gantry.add(xin, xout);
    R.belts.push({ mesh: xin, axis: "x", sign: -1 }, { mesh: xout, axis: "x", sign: 1 });
    gantry.add(beltArc([24, xmY, zX], xr, "-x"), beltArc([W - 24, xmY, zX], xr, "+x"));
    R.xmConn = [24, xmY + 24, xmZ - 10];
  }

  // Endstops.
  R.stops = {};
  for (const e of C.endstops) {
    if (e.name === "x") {
      R.stops.x = endstop(e.pos, "+x");
      gantry.add(R.stops.x);
    } else {
      R.stops[e.name] = endstop(e.pos, "+y");
      machine.add(R.stops[e.name]);
    }
  }

  // X carriage: the Creality plate with the pen lift. carriage moves with X.
  const carriage = new THREE.Group();
  gantry.add(carriage);
  R.carriage = carriage;
  // plateY is the back face of the carriage plate.
  const plateY = linear ? C.x_rail.box[1] - 5 : rods ? beam[1] - 6
    : C.x_carriage ? C.x_carriage.plate_front_y + 6 : beam[1] - 12;
  if (linear) {
    // MGN12H block on the X rail, the printed carriage plate in front of it, and the belt clamp.
    const xr0 = C.x_rail.box, xzc = (xr0[2] + xr0[5]) / 2;
    carriage.add(tag("xblock", fbox([hx - 22.5, plateY, xzc - 13.5, hx + 22.5, xr0[1] + 4, xzc + 13.5], M.steel)));
    carriage.add(tag("xplate", fbox([hx - 36, plateY - 6, PAPER_Z + 56, hx + 36, plateY, zX + 4], M.pla)));
    // Arm from the top of the plate, over the beam, to the clamped belt run.
    const runZ = R.xClamped === "lower" ? zX - xr : zX + xr;
    carriage.add(tag("xplate", fbox([hx - 12, plateY - 6, runZ - 9, hx + 12, xBeltY + 5, runZ - 0.8], M.pla)));
    carriage.add(tag("xplate", fbox([hx - 12, xBeltY - 5, runZ + 0.8, hx + 12, xBeltY + 5, runZ + 4], M.pla)));
  } else if (rods) {
    // Printed carriage: a front plate, two LM10UU bearings on each rod, and a belt clamp at the back.
    carriage.add(tag("xplate", fbox([hx - 36, plateY - 6, beam[2] - 10, hx + 36, plateY, beam[5] + 10], M.pla)));
    for (const r of rods) {
      const rzc = (r.box[2] + r.box[5]) / 2, ryc = (r.box[1] + r.box[4]) / 2;
      for (const dx of [-18, 18]) {
        carriage.add(tag("bearings", fcyl(9.5, 29, M.steel, "x", [hx + dx, ryc, rzc], 24)));
        carriage.add(tag("xplate", fbox([hx + dx - 14, plateY, rzc - 12, hx + dx + 14, ryc, rzc + 12], M.pla)));
      }
    }
    carriage.add(tag("xplate", fbox([hx - 12, plateY, zX + xr + 0.7, hx + 12, xBeltY + 9, zX + xr + 7], M.pla)));
    carriage.add(tag("xplate", fbox([hx - 12, xBeltY + 4, zX + xr - 5, hx + 12, xBeltY + 9, zX + xr + 0.7], M.pla)));
  } else {
    // The stock Creality X carriage plate on three V-wheels.
    const xb = C.x_carriage && C.x_carriage.box;
    carriage.add(tag("xplate", fbox(xb ? [xb[0], plateY - 6, xb[2], xb[3], plateY, xb[5]]
      : [hx - 40, plateY - 6, bz - 42, hx + 40, plateY, bz + 42], M.aluDark)));
    const ws = C.x_wheels || [[-28, 21.5], [28, 21.5], [0, -21.5]].map(([dx, dz]) => [hx + dx, cy, bz + dz]);
    for (const [x, y, z] of ws) {
      const w = vWheel("y", [x, y, z]);
      carriage.add(w);
      R.xWheels.push(w.userData.spin);
      carriage.add(fcyl(3.5, y - 5.5 - plateY, M.alu, "y", [x, (y - 5.5 + plateY) / 2, z], 12));
    }
    if (!wheelsX) {
      // Belt arm: from the top of the plate, over the beam, to the inner X belt run.
      carriage.add(tag("xplate", fbox([hx - 15, plateY - 6, beam[5] + 14, hx + 15, xmY - xr + 4, beam[5] + 20], M.aluDark)));
      carriage.add(tag("xplate", fbox([hx - 15, xmY - xr - 6, zX - 5, hx + 15, xmY - xr - 1, beam[5] + 14], M.aluDark)));
    }
  }

  // Pen lift body on the front of the plate.
  const penY = hy;
  const bodyB = [hx - 28, penY + 5.5, PAPER_Z + 28, hx + 28, plateY - 6, bz + 30];
  carriage.add(tag("lift", fbox(bodyB, M.pla)));
  for (const dx of [-14, 14]) carriage.add(tag("lift", fcyl(1.5, bodyB[5] - 34, M.steel, "z", [hx + dx, penY + 3, (34 + bodyB[5]) / 2], 10)));
  // Servo on the right side of the body. The horn turns with the pen.
  const servo = new THREE.Group();
  servo.add(new THREE.Mesh(new THREE.BoxGeometry(12.5, 23, 23), M.servo));
  const ear = new THREE.Mesh(new THREE.BoxGeometry(12.5, 2.5, 32), M.servo);
  ear.position.y = 6;
  servo.add(ear);
  const horn = new THREE.Group();
  horn.position.set(-8, 4, -6);
  const hornBar = new THREE.Mesh(new THREE.BoxGeometry(1.6, 3.5, 20), M.servoHorn);
  hornBar.position.z = -8;
  horn.add(hornBar);
  servo.add(horn);
  servo.position.copy(f2s(hx + 36, penY + 8, bz + 4));
  carriage.add(tag("servo", servo));
  R.horn = horn;
  // The horn STL turns about the servo shaft (frame.json pen_lift). hornTurn is at the shaft and turns.
  // hornAt holds the mesh in frame coordinates. The shaft is along frame y (scene -z).
  const hornTurn = new THREE.Group();
  const hornAt = new THREE.Group();
  hornTurn.add(hornAt);
  carriage.add(hornTurn);
  if (C.pen_lift) {
    hornTurn.position.copy(f2s(...C.pen_lift.pivot));
    hornAt.position.copy(f2s(...C.pen_lift.pivot)).negate();
  }
  Object.assign(R, { hornTurn, hornAt });

  // The pen and its slider move up and down together.
  const pen = new THREE.Group();
  carriage.add(pen);
  R.pen = pen;
  pen.add(tag("slider", fbox([hx - 20, penY - 6, PAPER_Z + 44, hx + 20, penY + 5.5, PAPER_Z + 78], M.plaDark)));
  pen.add(tag("slider", fcyl(9, 18, M.plaDark, "z", [hx, penY, PAPER_Z + 61])));
  pen.add(tag("slider", fcyl(2, 10, M.steel, "y", [hx, penY - 12, PAPER_Z + 63], 10)));
  const P = (z) => f2s(hx, penY, PAPER_Z + z);
  const penPart = (geo, mat, z) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.copy(P(z));
    pen.add(tag("pen", m));
    return m;
  };
  penPart(new THREE.ConeGeometry(1.8, 8, 16), M.penCap, 4).rotation.x = Math.PI;
  penPart(new THREE.ConeGeometry(0.6, 2, 10), M.pen, 1).rotation.x = Math.PI;
  penPart(new THREE.CylinderGeometry(4.6, 2.2, 14, 24), M.penCap, 15);
  penPart(new THREE.CylinderGeometry(4.6, 4.6, PEN_LEN - 30, 24), M.penCap, 22 + (PEN_LEN - 30) / 2);
  penPart(new THREE.CylinderGeometry(4.9, 4.9, 26, 24), M.pen, PEN_LEN - 10);
  penPart(new THREE.BoxGeometry(2, 30, 1.6), M.pen, PEN_LEN - 14).position.z -= 5.4;

  // The cable carriers and the cables (wiring.js): the Y drag chain, the servo loom, the cables from plug
  // to plug, the cable ties, and the detailed bought parts.
  R.lastCable = null;
  wiringBuild({ machine, gantry, carriage, R, C });

  // Shadows.
  machine.traverse((o) => {
    if (o.isMesh) o.castShadow = o.receiveShadow = true;
  });

  buildPaper();
  loadParts();
}

// updateCables moves the chain, the loom and the cables that follow the gantry and the carriage (wiring.js).
function updateCables(x, y) {
  const key = `${x.toFixed(1)},${y.toFixed(1)},${shown.y2.toFixed(1)}`;
  if (key === R.lastCable) return;
  R.lastCable = key;
  wiringUpdate(x, y, shown.y2);
}

// ---------------------------------------------------------------------------
// Paper and ink. The paper lies on the mat, centred on the travel area.
// The ink canvas covers the travel area plus a margin. It does not move.
const PAPERS = { A4: [210, 297], Letter: [215.9, 279.4] };
let paperName = "Letter";
let matMesh, paperMesh, inkMesh;
const inkCanvas = document.createElement("canvas");
const inkCtx = inkCanvas.getContext("2d");
const inkTex = new THREE.CanvasTexture(inkCanvas);
inkTex.colorSpace = THREE.SRGBColorSpace;
inkTex.anisotropy = renderer.capabilities.getMaxAnisotropy();
const INK = { color: "#1b2c7a", width: 0.5, margin: 10 };
// Paper styles: the colour of the paper and of the ink.
const STYLES = {
  white: { paper: 0xfbfbf6, ink: "#1b2c7a" },
  blueprint: { paper: 0x1f4f8f, ink: "#f4f7ff" },
};
let styleName = "white";
try {
  const q = new URLSearchParams(location.search).get("style");
  const saved = q || localStorage.getItem("plotsim.style");
  if (saved && STYLES[saved]) styleName = saved;
} catch {}
let inkArea = null; // [x0, y0, x1, y1] in frame mm
let inkDirty = false, inkLastUpload = 0;
let inkLog = new Float32Array(1 << 16), inkCount = 0; // all segments, for a redraw

function travelCentre() {
  const [hx, hy] = CFG.home_pen;
  return [hx + CFG.travel[0] / 2, hy + CFG.travel[1] / 2];
}

function buildPaper() {
  const [cx, cy] = travelCentre();
  for (const m of [matMesh, paperMesh, inkMesh]) if (m) machine.remove(m);
  // The paper top is at PAPER_Z. The mat is under the paper. The table top is under the mat.
  // The mat has no bottom face, so the view from below sees through it.
  matMesh = new THREE.Mesh(new THREE.BoxGeometry(MAT[0], MAT[2], MAT[1]), [M.mat, M.mat, M.mat, M.hidden, M.mat, M.mat]);
  matMesh.position.copy(f2s(cx, cy, PAPER_Z - 0.1 - MAT[2] / 2));
  tableGroup.position.y = PAPER_Z - 0.1 - MAT[2];
  matMesh.receiveShadow = true;
  machine.add(matMesh);
  paperMesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), M.paper);
  paperMesh.rotation.x = -Math.PI / 2;
  paperMesh.position.copy(f2s(cx, cy, PAPER_Z));
  paperMesh.receiveShadow = true;
  machine.add(paperMesh);
  setPaper(paperName);

  const [hx, hy] = CFG.home_pen;
  const mg = INK.margin;
  inkArea = [hx - mg, hy - mg, hx + CFG.travel[0] + mg, hy + CFG.travel[1] + mg];
  const w = inkArea[2] - inkArea[0], h = inkArea[3] - inkArea[1];
  const s = 2048 / Math.max(w, h);
  inkCanvas.width = Math.round(w * s);
  inkCanvas.height = Math.round(h * s);
  inkTex.dispose();
  inkMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ map: inkTex, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }),
  );
  inkMesh.rotation.x = -Math.PI / 2;
  inkMesh.position.copy(f2s((inkArea[0] + inkArea[2]) / 2, (inkArea[1] + inkArea[3]) / 2, PAPER_Z + 0.15));
  inkMesh.renderOrder = 2;
  machine.add(inkMesh);
  redrawInk();
}

function setPaper(name) {
  paperName = name;
  const [w, h] = PAPERS[name];
  if (paperMesh) paperMesh.scale.set(w, h, 1);
  document.getElementById("paperA4").classList.toggle("on", name === "A4");
  document.getElementById("paperLetter").classList.toggle("on", name === "Letter");
  try {
    localStorage.setItem("plotsim.paper", name);
  } catch {}
}
try {
  const saved = localStorage.getItem("plotsim.paper");
  if (saved && PAPERS[saved]) paperName = saved;
} catch {}

function setStyle(name) {
  styleName = name;
  M.paper.color.setHex(STYLES[name].paper);
  INK.color = STYLES[name].ink;
  document.getElementById("paperBlue").classList.toggle("on", name === "blueprint");
  try {
    localStorage.setItem("plotsim.style", name);
  } catch {}
  if (inkArea) redrawInk();
}

function strokeSegs(segs, n) {
  if (!inkArea) return;
  const s = inkCanvas.width / (inkArea[2] - inkArea[0]);
  const g = inkCtx;
  g.strokeStyle = INK.color;
  g.lineWidth = INK.width * s;
  g.lineCap = "round";
  g.beginPath();
  for (let i = 0; i < n; i++) {
    const [fx0, fy0] = machineToFrame(segs[i * 4], segs[i * 4 + 1]);
    const [fx1, fy1] = machineToFrame(segs[i * 4 + 2], segs[i * 4 + 3]);
    g.moveTo((fx0 - inkArea[0]) * s, (inkArea[3] - fy0) * s);
    g.lineTo((fx1 - inkArea[0]) * s, (inkArea[3] - fy1) * s);
  }
  g.stroke();
  inkDirty = true;
}
function addInk(list) {
  const need = (inkCount + list.length) * 4;
  if (need > inkLog.length) {
    let size = inkLog.length;
    while (size < need) size *= 2;
    const bigger = new Float32Array(size);
    bigger.set(inkLog.subarray(0, inkCount * 4));
    inkLog = bigger;
  }
  const start = inkCount;
  for (const seg of list) inkLog.set(seg, 4 * inkCount++);
  strokeSegs(inkLog.subarray(start * 4), list.length);
}
function redrawInk() {
  inkCtx.clearRect(0, 0, inkCanvas.width, inkCanvas.height);
  strokeSegs(inkLog, inkCount);
  inkTex.needsUpdate = true;
}
function clearInk() {
  inkCount = 0;
  inkCtx.clearRect(0, 0, inkCanvas.width, inkCanvas.height);
  inkDirty = true;
}

// ---------------------------------------------------------------------------
// Printed parts from /stl/frame.json. The STL files are in frame coordinates
// (Z up), at machine home with the pen down. A part replaces the primitives of
// the same item. The item comes from words in the file name.
const ITEM_WORDS = [
  [/y_?stepper/i, "ystepper"],
  [/y_?pulleys/i, "ypulleys"],
  [/^beam/i, "beam"],
  [/x_?rail/i, "xrail"],
  [/y_?rail/i, "yrail"],
  [/x_?block/i, "xblock"],
  [/y_?block/i, "yblock"],
  [/x_?motor/i, "xmotor"],
  [/x_?idler/i, "xidler"],
  [/rod/i, "rod"],
  [/bearing/i, "bearings"],
  [/y_?carriage/i, "ycarriage"],
  [/motor_?(mount|bracket)|y_?motor/i, "ymotorbracket"],
  [/idler/i, "idlerbracket"],
  [/pen_?carriage/i, ["xplate", "lift"]],
  [/x_?carriage|carriage_?plate|x_?plate/i, "xplate"],
  [/pen_?lift|lift_?body/i, "lift"],
  [/slider|screw/i, "slider"],
  [/servo|horn/i, "servo"],
  [/^pen(_body)?\.stl$/i, "pen"],
  // Only a file of the feet replaces the drawn feet. mast_foot.stl is the camera pole base, not a foot.
  [/^(stock_)?(foot|feet)[_.]/i, "feet"],
  [/cable_?post/i, "cablepost"],
];
const loader = new STLLoader();
let partsToken = 0;
async function loadParts() {
  const token = ++partsToken;
  for (const p of CFG.parts || []) {
    // The beam STL is a plain box. The drawn beam has the 2020 V-slot profile, so keep it.
    if (/^beam/i.test(p.file.split("/").pop()) && CFG.beam) continue;
    let geo;
    try {
      const r = await fetch(`stl/${p.file}`);
      if (!r.ok) continue;
      geo = loader.parse(await r.arrayBuffer());
    } catch {
      continue;
    }
    if (token !== partsToken) return; // a newer build started
    geo.computeVertexNormals();
    const mat = new THREE.MeshStandardMaterial({ color: p.color || "#7fb6e0", roughness: 0.6 });
    if (p.moves !== "static") toolMats.push(mat);
    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = -Math.PI / 2; // frame (Z up) to scene (Y up)
    mesh.castShadow = mesh.receiveShadow = true;
    const parent = { static: machine, gantry: R.gantry, carriage: R.carriage, pen: R.pen, horn: R.hornAt }[p.moves] || machine;
    parent.add(mesh);
    const name = p.file.split("/").pop();
    mesh.name = name;
    if (hiddenParts.has(name.replace(/\.stl$/, ""))) mesh.visible = false; // a detail part (wiring.js) replaces it
    for (const [re, item] of ITEM_WORDS)
      if (re.test(name)) {
        for (const it of [].concat(item)) for (const o of R.tagged[it] || []) o.visible = false;
        break;
      }
    // The servo cable goes to the top of the printed servo.
    if (/servo/i.test(name)) {
      geo.computeBoundingBox();
      const bb = geo.boundingBox;
      R.servoAt = [(bb.min.x + bb.max.x) / 2, (bb.min.y + bb.max.y) / 2, bb.max.z];
      R.lastCable = null;
    }
  }
  if (seeThrough) setSeeThrough(true);
}

async function loadFrame() {
  try {
    const r = await fetch("stl/frame.json");
    if (!r.ok) return;
    const cfg = await r.json();
    CFG = { ...DEFAULT_CFG, ...cfg };
    // The X and Y guide keys come as one set. Do not mix the defaults with an older layout.
    const GUIDE = ["beam", "x_rail", "y_rails", "rods", "x_motor", "x_idler", "x_belt", "x_carriage", "x_wheels", "y_wheels", "y_wheel_axis", "chains"];
    if (GUIDE.some((k) => k in cfg)) for (const k of GUIDE) if (!(k in cfg)) delete CFG[k];
    // The Y drive keys come as one set too: y_belt, or y_motors with y_idlers and y_belt_runs.
    const YDRIVE = ["y_belt", "y_motors", "y_idlers", "y_belt_runs", "y_clamp"];
    if (YDRIVE.some((k) => k in cfg)) for (const k of YDRIVE) if (!(k in cfg)) delete CFG[k];
    buildMachine();
  } catch (e) {
    console.warn("frame.json:", e.message);
  }
}

// See-through tool head (T key).
let seeThrough = false;
function setSeeThrough(on) {
  seeThrough = on;
  for (const m of toolMats) {
    m.transparent = on;
    m.opacity = on ? 0.22 : 1;
    m.depthWrite = !on;
    m.needsUpdate = true;
  }
}

// ---------------------------------------------------------------------------
// State from the server.
const state = { x: 0, y: 0, y2: null, pen: 0, servo: 130, pen_up_deg: 130, pen_down_deg: 80, lift: null, over: false, en: false, homed: false, es: { x: false, y: false, y2: false }, busy: false, q: 0, line: "", done: 0, total: 0, speed: 1 };
const shown = { x: 0, y: 0, y2: 0, pen: 0, servo: 130 };
let machineInfo = {}; // the hello message: travel, bed, pen angles
let jobName = "";

const link = connect((m) => {
  switch (m.t) {
    case "hello":
      // A new connection starts with a clean sheet. The server sends all ink again after hello.
      clearInk();
      if (m.machine && m.machine.layout && m.machine.layout !== "table") console.warn("layout is not table:", m.machine.layout);
      showBoard(m.machine && m.machine.board);
      machineInfo = m.machine || {};
      break;
    case "state":
      Object.assign(state, m);
      state.over = !!m.over; // the server leaves out "over" when it is false
      if (m.es) state.es = { x: false, y: false, y2: false, ...m.es };
      break;
    case "ink":
      if (m.s && m.s.length) addInk(m.s);
      break;
    case "lcd":
      setLcdPixels(decodeLcd(m.bits), 128, 64);
      break;
    case "beep":
      beep(m.ms || 60);
      break;
  }
});

// ---------------------------------------------------------------------------
// UI.
const speeds = [1, 2, 5, 10, 50];
const speedBtns = speeds.map((x) => {
  const b = document.createElement("button");
  b.textContent = `${x}×`;
  b.onclick = () => link.send({ t: "speed", x });
  document.getElementById("speeds").appendChild(b);
  return b;
});
document.getElementById("home").onclick = () => link.send({ t: "line", text: "G28" });
document.getElementById("penup").onclick = () => link.send({ t: "line", text: "M5" });
document.getElementById("pendown").onclick = () => link.send({ t: "line", text: "M3" });

// The control panel: the jog pad and the servo slider.
// The jog pad sends absolute G0 moves. The target is the reported position plus the step, clamped to
// the travel. While moves are in the queue, the next step adds to the last target. The firmware clamps
// moves only after G28 (soft limits), and before G28 the position is not known. So the pad needs G28 first.
const ctl = document.getElementById("ctl");
const ctlKey = "plotsim.controls";
function showCtl(on) {
  ctl.hidden = !on;
  document.getElementById("ctlToggle").classList.toggle("on", on);
  try {
    localStorage.setItem(ctlKey, on ? "1" : "0");
  } catch {}
}
let ctlOn = true;
try {
  ctlOn = localStorage.getItem(ctlKey) !== "0";
} catch {}
showCtl(ctlOn);
document.getElementById("ctlToggle").onclick = () => showCtl(ctl.hidden);

const STEPS = [0.1, 1, 10, 50];
let jogStep = 10;
const stepBtns = STEPS.map((v) => {
  const b = document.createElement("button");
  b.textContent = String(v);
  b.title = `Jog ${v} mm`;
  b.onclick = () => setStep(v);
  document.getElementById("steps").appendChild(b);
  return b;
});
function setStep(v) {
  jogStep = v;
  stepBtns.forEach((b, i) => b.classList.toggle("on", STEPS[i] === v));
  document.getElementById("jogStep").textContent = `${v} mm`;
}
setStep(jogStep);

// travel returns the firmware travel (the hello message), or the default 245 x 390 mm.
function travel() {
  const t = machineInfo.travel;
  return t && t.length === 2 ? t : [245, 390];
}
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const jobActive = () => state.total > 0 && state.done < state.total;
const canJog = () => state.homed && !jobActive();
let jogTarget = null; // the last target sent, while the machine moves
function moveTo(x, y) {
  const [tx, ty] = travel();
  x = clamp(x, 0, tx);
  y = clamp(y, 0, ty);
  jogTarget = { x, y };
  // G90 in the same line: the move is absolute even if an earlier line set G91.
  link.send({ t: "line", text: `G90 G0 X${x.toFixed(3)} Y${y.toFixed(3)}` });
}
function jog(dx, dy) {
  if (!canJog()) return;
  const idle = !state.busy && !state.q;
  const base = !idle && jogTarget ? jogTarget : { x: state.x, y: state.y };
  moveTo(base.x + dx * jogStep, base.y + dy * jogStep);
}
for (const b of document.querySelectorAll("[data-jog]")) {
  const [dx, dy] = b.dataset.jog.split(",").map(Number);
  b.onclick = () => jog(dx, dy);
}
const gx = document.getElementById("gx");
const gy = document.getElementById("gy");
function goTo() {
  if (!canJog()) return;
  const x = parseFloat(gx.value);
  const y = parseFloat(gy.value);
  if (!Number.isFinite(x) && !Number.isFinite(y)) return;
  moveTo(Number.isFinite(x) ? x : state.x, Number.isFinite(y) ? y : state.y);
}
document.getElementById("go").onclick = goTo;
for (const i of [gx, gy]) i.addEventListener("keydown", (e) => e.key === "Enter" && goTo());

// The servo slider sends M280 P0 S<deg>. The server sends the lines in order, so a drag is safe.
const servoIn = document.getElementById("servo");
let servoDrag = 0; // the time of the last user input; the slider follows the servo after 1.5 s
let servoSent = 0;
let servoTimer = 0;
function sendServo() {
  clearTimeout(servoTimer);
  servoTimer = 0;
  servoSent = performance.now();
  link.send({ t: "line", text: `M280 P0 S${servoIn.value}` });
}
servoIn.addEventListener("input", () => {
  servoDrag = performance.now();
  // At most 8 lines each second while the slider moves. Each M280 waits 150 ms in the firmware.
  if (!servoTimer) servoTimer = setTimeout(sendServo, Math.max(0, 125 - (performance.now() - servoSent)));
});
servoIn.addEventListener("change", () => {
  servoDrag = performance.now();
  sendServo();
});
document.getElementById("freeHorn").onclick = () => link.send({ t: "freehorn" });

// The marks under the slider: the pen-up and pen-down angles (M281), the contact of the horn
// tip with the tab, and the slip zone (the tip goes past the end of the tab).
let marksKey = "";
function drawMarks() {
  const PL = CFG.pen_lift;
  const key = [state.pen_up_deg, state.pen_down_deg, PL && PL.contact_servo, PL && PL.slip_servo].join();
  if (key === marksKey) return;
  marksKey = key;
  const box = document.getElementById("marks");
  box.textContent = "";
  const at = (deg) => `${((100 * deg) / 180).toFixed(2)}%`;
  if (PL && PL.slip_servo < 180) {
    const z = document.createElement("div");
    z.className = "slip";
    z.style.left = at(PL.slip_servo);
    z.style.right = "0";
    z.title = `Above ${PL.slip_servo}°, the horn tip goes past the end of the tab. The slider falls.`;
    box.appendChild(z);
  }
  const mark = (deg, cls, text, title) => {
    const m = document.createElement("span");
    m.className = "m " + cls;
    m.style.left = at(deg);
    m.textContent = text;
    m.title = title;
    box.appendChild(m);
  };
  mark(state.pen_down_deg, "down", `D ${state.pen_down_deg}`, "Pen-down angle (M281 D)");
  mark(state.pen_up_deg, "up", `U ${state.pen_up_deg}`, "Pen-up angle (M281 U)");
  if (PL && PL.contact_servo) mark(PL.contact_servo, "", "", `The horn tip meets the tab at ${PL.contact_servo}°`);
}

function updateCtl(now) {
  const homed = state.homed;
  const job = jobActive();
  for (const b of document.querySelectorAll("[data-jog], #go")) b.disabled = !homed || job;
  gx.disabled = gy.disabled = !homed || job;
  servoIn.disabled = job;
  const note = document.getElementById("jogNote");
  note.textContent = job ? "Job running" : homed ? "" : "Home first";
  note.className = homed && !job ? "note" : "warn";
  const [tx, ty] = travel();
  gx.max = tx;
  gy.max = ty;
  if (document.activeElement !== gx && document.activeElement !== gy) {
    gx.placeholder = state.x.toFixed(1);
    gy.placeholder = state.y.toFixed(1);
  }
  // The slider follows the servo when the user does not move it.
  if (now - servoDrag > 1500 && document.activeElement !== servoIn) servoIn.value = Math.round(state.servo);
  drawMarks();
  const PL = CFG.pen_lift;
  const horn = state.servo - (PL ? PL.servo_level_deg : 90);
  const lift = state.lift ?? (PL && PL.lift_by_servo_deg ? liftAt(PL, state.servo) : null);
  document.getElementById("servoNow").textContent = `${state.servo.toFixed(0)}°`;
  let info = `Horn ${horn >= 0 ? "+" : ""}${horn.toFixed(0)}° from level`;
  if (lift != null) info += lift > 0.01 ? ` · pen up ${lift.toFixed(2)} mm` : " · pen on the paper";
  document.getElementById("servoInfo").textContent = info;
  document.getElementById("hornWarn").hidden = !state.over;
}

document.getElementById("paperA4").onclick = () => setPaper("A4");
document.getElementById("paperLetter").onclick = () => setPaper("Letter");
document.getElementById("paperBlue").onclick = () => setStyle(styleName === "blueprint" ? "white" : "blueprint");
setStyle(styleName);
document.getElementById("clear").onclick = () => {
  clearInk();
  link.send({ t: "paper", clear: true });
};
const fileInput = document.getElementById("file");
document.getElementById("upload").onclick = () => fileInput.click();
fileInput.onchange = () => {
  if (fileInput.files[0]) sendFile(fileInput.files[0]);
  fileInput.value = "";
};
async function sendFile(f) {
  jobName = f.name;
  link.send({ t: "gcode", name: f.name, text: await f.text() });
}
const drop = document.getElementById("drop");
let dragDepth = 0;
addEventListener("dragenter", (e) => {
  e.preventDefault();
  dragDepth++;
  drop.classList.add("show");
});
addEventListener("dragleave", () => {
  if (--dragDepth <= 0) {
    dragDepth = 0;
    drop.classList.remove("show");
  }
});
addEventListener("dragover", (e) => e.preventDefault());
addEventListener("drop", (e) => {
  e.preventDefault();
  dragDepth = 0;
  drop.classList.remove("show");
  if (e.dataTransfer.files[0]) sendFile(e.dataTransfer.files[0]);
});
addEventListener("pointerdown", unlockAudio);
addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT") return;
  if (e.key === "t" || e.key === "T") setSeeThrough(!seeThrough);
  if (e.key === "a" || e.key === "A") {
    axesOn = !axesOn;
    for (const g of axisGroups) g.visible = axesOn;
  }
  if (e.key === "f" || e.key === "F") frameBed();
  if (e.key === "h" || e.key === "H") homeView();
  if (e.key === "j" || e.key === "J") showCtl(ctl.hidden);
  const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] };
  if (arrows[e.key] && !ctl.hidden) {
    e.preventDefault();
    jog(...arrows[e.key]);
  }
});
// frameBed shows the paper from above and a little from the front.
function frameBed() {
  const [cx, cy] = travelCentre();
  controls.target.copy(f2s(cx, cy, 20));
  camera.position.copy(f2s(cx + 60, cy - 420, 640));
  controls.update();
}

const el = (id) => document.getElementById(id);
let lastUi = 0;
function updateUi(now) {
  if (now - lastUi < 100) return;
  lastUi = now;
  el("sx").textContent = state.x.toFixed(2);
  el("sy").textContent = state.y.toFixed(2);
  el("spen").textContent = state.lift != null ? (state.lift > 0.01 ? "up" : "down") : state.pen > 0.5 ? "down" : "up";
  el("shomed").textContent = state.homed ? "homed" : "not homed";
  el("sbusy").textContent = state.busy ? "busy" : "idle";
  el("dot").className = "dot " + (state.busy ? "busy" : state.homed ? "ok" : "");
  const pct = state.total ? (100 * state.done) / state.total : 0;
  el("fill").style.width = pct.toFixed(1) + "%";
  el("pname").textContent = state.total ? state.name || jobName || "Job" : "No job";
  el("pcount").textContent = state.total ? `${state.done} / ${state.total} lines · ${pct.toFixed(1)} %` : "";
  el("pline").textContent = state.line || "";
  el("pq").textContent = state.q ? `queue ${state.q}` : "";
  speedBtns.forEach((b, i) => b.classList.toggle("on", speeds[i] === state.speed));
  updateCtl(now);
}

// liftAt returns the slider lift in mm at a servo angle (frame.json pen_lift.lift_by_servo_deg).
// hardware/model.py makes the table from the horn and tab geometry. The sim server uses the same table.
function liftAt(PL, deg) {
  const t = PL.lift_by_servo_deg;
  const d = Math.max(0, Math.min(180, deg));
  const i = Math.min(179, Math.floor(d));
  const f = d - i;
  return t[i] * (1 - f) + t[i + 1] * f;
}

// ---------------------------------------------------------------------------
// Animation.
const PULLEY_R = 40 / (2 * Math.PI); // 20 teeth x 2 mm
function setStop(stop, on) {
  if (!stop) return;
  const u = stop.userData;
  u.mat.emissive.setHex(on ? 0xff2020 : 0x000000);
  u.mat.color.setHex(on ? u.ledOn ?? 0xd02020 : u.ledOff ?? 0x1f6f3a);
}
function animate(now) {
  requestAnimationFrame(animate);
  // Follow the server state. A small smoothing hides the gaps between messages.
  const y2 = state.y2 ?? state.y;
  shown.x += (state.x - shown.x) * 0.6;
  shown.y += (state.y - shown.y) * 0.6;
  shown.y2 += (y2 - shown.y2) * 0.6;
  shown.pen += (state.pen - shown.pen) * 0.35;
  shown.servo += (state.servo - shown.servo) * 0.35;
  const { x, y, pen } = shown;

  // Gantry: Y1 moves it, and the difference Y2 - Y1 turns the beam.
  R.gantryPos.position.z = -y;
  R.gantrySkew.rotation.y = Math.atan2(shown.y2 - y, R.skewSpan);
  R.carriage.position.x = x;
  // The pen lift: the horn turns to the servo angle. Its tip lifts the slider tab. The slider and
  // the pen fall by their weight and stop on the paper (lift 0). See frame.json pen_lift.
  const PL = CFG.pen_lift;
  if (PL && PL.lift_by_servo_deg) {
    R.hornTurn.rotation.z = -THREE.MathUtils.degToRad(shown.servo - PL.servo_level_deg - PL.stl_deg);
    R.pen.position.y = state.over ? 0 : liftAt(PL, shown.servo);
  } else {
    // No linkage data: the old drawing, from the 0..1 pen value.
    R.pen.position.y = (1 - pen) * CFG.pen_lift_mm;
    R.horn.rotation.x = -0.9 + pen * 1.2;
  }

  // Belts, pulleys and wheels turn with the motion.
  for (const c of R.clamped) c.run.update(c.axis === "x" ? x : c.side === 1 ? shown.y2 : y);
  for (const b of R.belts) {
    const d = b.axis === "x" ? x : b.side === 1 ? shown.y2 : y;
    b.mesh.userData.tex.offset.x = (b.sign * d) / 2;
  }
  R.yPulleys.forEach((p, i) => (p.userData.spin.rotation.y = (i ? shown.y2 : y) / PULLEY_R));
  R.yIdlers.forEach((p, i) => (p.userData.spin.rotation.y = (i ? shown.y2 : y) / 6.5));
  R.xPulley.userData.spin.rotation.y = x / PULLEY_R;
  R.xIdler.userData.spin.rotation.y = x / 6.5;
  R.yWheels.forEach((list, i) => list.forEach((w) => (w.rotation.y = (i ? shown.y2 : y) / 11.5)));
  for (const w of R.xWheels) w.rotation.y = x / 11.5;

  setStop(R.stops.x, state.es.x);
  setStop(R.stops.y1, state.es.y);
  setStop(R.stops.y2, state.es.y2);
  updateCables(x, y);

  // Upload the ink texture at most 20 times each second.
  if (inkDirty && now - inkLastUpload > 50) {
    inkTex.needsUpdate = true;
    inkDirty = false;
    inkLastUpload = now;
  }
  controls.update();
  renderer.render(scene, camera);
  updateUi(now);
}

buildMachine();
loadFrame();
requestAnimationFrame(animate);

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// A small hook for automatic tests.
window.plotsim = { state, scene, camera, controls, frameBed, homeView, setSeeThrough, f2s, renderer, get R() { return R; }, get CFG() { return CFG; } };
