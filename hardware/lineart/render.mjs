// Pen plotter parts: the line-art images for the build instructions, in the style of the
// beetlebug.org explode viewer. Uses three.js in headless Chromium.
// Run from the project folder after model.py: node lineart/render.mjs [shot ...]
// Output: build/img/raw/<shot>-light.png and <shot>-dark.png, with a transparent background.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const HERE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const RAW = path.join(HERE, "build", "img", "raw");
const MANIFEST = JSON.parse(fs.readFileSync(path.join(HERE, "build", "manifest.json"), "utf8"));

// Fill type for each material: printed, bought, dark, or clear.
const FINISH = { petg: "print", extrusion: "dark", plate: "buy", servo: "dark", horn: "buy", pen: "dark", steel: "buy" };
const LABEL = {
  plate: "X plate + wheels", pen_lift: "Pen carriage", pen_slider: "Slider", servo: "Servo", horn_down: "Horn",
  pen: "Pen", screw: "M3 x 20", up: "",
  yl_rail: "", yl_car: "Y carriage", yl_wtop: "2 outer wheels", yl_wbot: "Inner wheel",
  t_fast: "", t_clips: "", t_belts: "", t_cables: "", xclip: "Crimp clip", xbelt: "Folded belt end",
  yd_frame: "", yd_mount: "Y motor bracket", yd_motor: "Y motor", yd_omega: "Pulley", yd_belt: "", yd_screws: "2 x M5 x 12 + 4 x M3 x 10",
  ya_frame: "", ya_base: "Front base", ya_bracket: "Idler bracket", ya_sled: "Idler fork", ya_idler: "20T idler", ya_switch: "Y endstop",
  ya_clip: "M5 x 30 axle, M3 x 20 tension screw", ya_belt: "",
  xp_plate: "X plate", xp_wheels: "", xm_car: "Left Y carriage", xm_beam: "", xm_motor: "X motor", xm_pulley: "20T pulley",
  xm_belt: "", xm_screws: "3 x M3 x 10, 1 x M5 x 12", xf_beam: "", xf_belt: "",
};
const YL = ["yl_rail", "yl_car", "yl_wtop", "yl_wbot"];

const PRINTED = ["pen_carriage", "pen_slider", "mast_foot",
  "y_carriage_left", "y_carriage_right", "y_front_left", "y_front_right", "x_carriage_plate",
  "y_motor_mount_left", "y_motor_mount_right", "y_idler_fork", "y_idler_bracket_left", "y_idler_bracket_right", "y_chain_anchor", "x_idler_fork", "fit_rail", "fit_slider", "fit_wheel"];
const FRONT = [0.7, -1.6, 0.55];      // from the front right, a little above
const FRONT_FLAT = [0.12, -1, 0.08];  // nearly straight from the front
const REAR = [0.9, 1.5, 0.6];         // from the rear right
const PRINT_VIEW = [1, -1.2, 0.9];
const HEAD = ["pen_lift", "pen_slider", "servo", "horn_down", "pen", "screw"];

// name: { show, focus, explode {group: offset}, camera, labels {group: label} }.
// The table plotter: the stock controller build, with the bare breakout boards and the stock control box.
const TABLE = ["t_frame", "t_wheels", "t_ycar", "t_brackets", "t_beam", "t_motors", "t_head", "t_mast", "t_boards", "t_box", "t_fast", "t_clips", "t_belts", "t_cables"];
const NOLAB = Object.fromEntries(TABLE.map((g) => [g, ""]));
const SHOTS = {
  table: { show: TABLE, focus: ["t_ycar", "t_head", "t_beam"], explode: {}, camera: [0.9, -1.3, 0.9], labels: NOLAB },
  // The name t_rails stays: the docs use it. It now shows the V-wheels under the Y carriages.
  t_rails: { show: ["t_frame", "t_wheels", "t_ycar"], focus: ["t_wheels", "t_ycar"], explode: { t_ycar: [0, 0, 70], t_wheels: [0, 0, 35] },
    camera: [0.9, -1.3, 0.9], labels: { t_frame: "", t_wheels: "V-wheel + spacer", t_ycar: "Y carriage" } },
  t_ycar: { show: ["t_frame", "t_wheels", "t_ycar"], focus: ["t_ycar"], explode: { t_ycar: [0, -90, 0], t_wheels: [0, -90, 0] },
    camera: [0.9, -1.3, 0.9], labels: { t_frame: "", t_wheels: "", t_ycar: "Y carriage" } },
  // The Y belt ends and the endstops (mesh group t_brackets: front bases, tensioners, back anchors, switches).
  t_yends: { show: ["t_frame", "t_wheels", "t_ycar", "t_brackets", "t_motors", "t_belts", "t_clips"], focus: ["t_brackets"],
    explode: { t_brackets: [0, 0, 40] }, camera: [0.9, -1.3, 0.9],
    labels: { t_frame: "", t_wheels: "", t_ycar: "", t_motors: "", t_belts: "", t_clips: "", t_brackets: "Belt ends + endstops" } },
  // The fixed Y belts on the rails: the front bases with the tensioners, the omega drives on the
  // carriages, the back anchors. From the front left.
  ybelt: { show: ["t_frame", "t_wheels", "t_ycar", "t_brackets", "t_motors", "t_belts", "t_clips"],
    focus: ["t_belts", "t_brackets"], explode: {}, camera: [-1.0, -1.1, 0.75],
    labels: { t_frame: "", t_wheels: "", t_ycar: "", t_clips: "", t_brackets: "", t_motors: "", t_belts: "Fixed Y belt" } },
  t_beam: { show: ["t_frame", "t_wheels", "t_ycar", "t_brackets", "t_beam", "t_head", "t_motors", "t_belts"], focus: ["t_beam", "t_head"],
    explode: { t_beam: [0, 0, 70], t_head: [0, 0, 70] }, camera: [0.9, -1.3, 0.9],
    labels: { t_belts: "", t_clips: "", t_frame: "", t_wheels: "", t_ycar: "", t_brackets: "", t_beam: "Beam + X carriage", t_head: "", t_motors: "" } },
  t_mast: { show: ["t_frame", "t_wheels", "t_ycar", "t_brackets", "t_beam", "t_motors", "t_head", "t_mast", "t_belts", "t_clips"], focus: ["t_mast"],
    explode: {}, camera: [0.9, -1.6, 0.7],
    labels: { t_belts: "", t_clips: "", t_frame: "", t_wheels: "", t_ycar: "", t_brackets: "", t_beam: "", t_motors: "", t_head: "", t_mast: "Camera pole" } },
  t_head: { show: ["t_frame", "t_wheels", "t_ycar", "t_brackets", "t_beam", "t_motors", "t_head", "t_belts", "t_clips"], focus: ["t_head", "t_motors"],
    explode: {}, camera: [0.9, -1.3, 0.9],
    labels: { t_belts: "", t_clips: "", t_frame: "", t_wheels: "", t_ycar: "", t_brackets: "", t_beam: "", t_motors: "", t_head: "" } },
  // The belt ends: the folded end and its crimp clip come out of the pocket to the outside.
  xclip: { show: ["xp_plate", "xp_wheels", "xclip", "xbelt"], focus: ["xp_plate", "xclip", "xbelt"],
    explode: { xclip: [0, 40, 0], xbelt: [0, 22, 0] }, camera: [0.8, 1.5, -0.35] },
  cables: { show: TABLE, focus: ["t_cables", "t_ycar"], explode: {}, camera: [-1.0, -1.25, 0.85],
    labels: { ...NOLAB, t_cables: "Y drag chain + servo loom" } },
  ydrive: { show: ["yd_frame", "yd_mount", "yd_motor", "yd_omega", "yd_belt", "yd_screws"],
    focus: ["yd_mount", "yd_motor", "yd_omega"], explode: { yd_motor: [-60, 0, 0], yd_screws: [0, 25, 0] },
    camera: [-0.9, 1.3, 0.8] },
  xmotor: { show: ["xm_car", "xm_beam", "xm_motor", "xm_pulley", "xm_belt", "xm_screws"],
    focus: ["xm_car", "xm_motor", "xm_pulley"], explode: { xm_motor: [0, 60, 0] }, camera: [-1.0, 1.1, 0.7] },
  xfork: { show: ["xf_car", "xf_beam", "xf_belt", "xf_fork", "xf_idler", "xf_axle", "xf_tension"], focus: ["xf_fork", "xf_idler", "xf_axle", "xf_tension"],
    explode: { xf_fork: [0, 0, 40], xf_idler: [0, 0, 40], xf_axle: [0, -30, 40], xf_tension: [25, 0, 0] }, camera: [0.9, -1.3, 0.7],
    labels: { xf_car: "Right Y carriage", xf_fork: "Idler fork", xf_idler: "20T idler", xf_axle: "M5 x 30, 2 washers, nyloc", xf_tension: "M3 x 20 + nut" } },
  yfront: { show: ["ya_frame", "ya_base", "ya_bracket", "ya_sled", "ya_idler", "ya_switch", "ya_clip", "ya_belt"],
    focus: ["ya_base", "ya_sled", "ya_idler"], explode: { ya_sled: [0, 0, 35], ya_idler: [0, 0, 35], ya_clip: [0, 0, 35] },
    camera: [0.9, -1.2, 0.9] },
  // The left Y carriage on its rail, seen from the front left: the C shape around the rail.
  ywheel: { show: YL, focus: YL, explode: { yl_car: [-90, 0, 0] },
    camera: [0.55, -1.4, 0.3] },
  ywheel_on: { show: YL, focus: YL, explode: {}, camera: [0.55, -1.4, 0.3], labels: { yl_wtop: "", yl_wbot: "", yl_car: "" } },
  // The breakout boards and the control box, from the back left. The name stays t_variant: the docs use it.
  t_variant: { show: TABLE, focus: ["t_boards", "t_ycar", "t_box"], explode: {}, camera: [-0.9, 1.5, 0.9],
    labels: { ...NOLAB, t_boards: "Breakout boards", t_box: "Control box" } },
  // The two bare breakout boards on their standoffs: the head board on the beam, the base board on the back bar.
  t_boards: { show: ["t_frame", "t_wheels", "t_ycar", "t_beam", "t_motors", "t_head", "t_boards", "t_belts", "t_cables"],
    focus: ["t_boards"], explode: {}, camera: [-0.5, 1.5, 0.8],
    labels: { t_frame: "", t_wheels: "", t_ycar: "", t_beam: "", t_motors: "", t_head: "", t_belts: "", t_cables: "", t_boards: "" } },
  table_corner: { show: TABLE, focus: ["t_ycar", "t_head"], explode: {}, camera: [-1.1, -0.9, 0.7], labels: NOLAB },
  hero: { show: ["plate", ...HEAD], focus: ["pen_lift", "pen_slider"], explode: {}, camera: FRONT,
    labels: { plate: "", screw: "", horn_down: "" } },
  inserts: { show: ["pen_lift"], focus: ["pen_lift"], explode: {}, camera: REAR, labels: { pen_lift: "" } },
  mount: { show: ["plate", "pen_lift"], focus: ["pen_lift"],
    explode: { pen_lift: [0, -45, 0] }, camera: REAR },
  servo: { show: ["plate", "pen_lift", "servo", "horn_down"], focus: ["servo", "horn_down"],
    explode: { servo: [0, -40, 0], horn_down: [0, -70, 0] }, camera: FRONT },
  slider: { show: ["plate", "pen_lift", "servo", "horn_down", "pen_slider"], focus: ["pen_slider"],
    explode: { pen_slider: [0, 0, 75] }, camera: FRONT, labels: { horn_down: "" } },
  pen: { show: ["plate", ...HEAD], focus: ["pen", "screw"], explode: { pen: [0, 0, -70], screw: [-30, 0, 0] },
    camera: FRONT, labels: { horn_down: "" } },
  down: { show: ["plate", ...HEAD], focus: ["horn_down", "pen_slider"], explode: {}, camera: FRONT_FLAT,
    labels: { plate: "", screw: "", pen: "", servo: "" } },
  up: { show: ["plate", "pen_lift", "servo", "up"], focus: ["up"], explode: {}, camera: FRONT_FLAT,
    labels: { plate: "", servo: "", pen_lift: "" } },
};

const SIZE = 2800;                    // pixels; the images are about 170 mm wide in the PDF (400 dpi)
const LABEL_PX = 60;                  // the label text, in pixels
const LINE_PX = 2.8;                  // the edge lines, in pixels

function shotParts(spec) {
  return MANIFEST.parts.filter((p) => spec.show.includes(p.group)).map((p) => ({
    url: `/build/mesh/${p.file}`,
    finish: FINISH[p.material] ?? "buy",
    label: spec.labels?.[p.group] ?? LABEL[p.group],
    focus: spec.focus.includes(p.group),
    offset: spec.explode[p.group],
  }));
}

function jobs() {
  const out = Object.entries(SHOTS).map(([name, spec]) => [name, { parts: shotParts(spec), camera: spec.camera }]);
  // Each printed part in its print orientation, from its STL file.
  for (const p of PRINTED) {
    out.push([`part_${p}`, { parts: [{ url: `/stl/${p}.stl`, finish: "print" }], camera: PRINT_VIEW }]);
  }
  return out;
}

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".stl": "model/stl" };

function serve() {
  const server = http.createServer((req, res) => {
    const file = path.join(HERE, decodeURIComponent(new URL(req.url, "http://x").pathname));
    if (!file.startsWith(HERE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404).end();
      return;
    }
    res.writeHead(200, { "content-type": TYPES[path.extname(file)] ?? "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}

async function main() {
  const only = process.argv.slice(2);
  fs.mkdirSync(RAW, { recursive: true });
  const server = await serve();
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROMIUM ?? "/usr/bin/chromium",
    args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-sandbox"],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: SIZE, height: SIZE, deviceScaleFactor: 1 });
    page.on("pageerror", (e) => console.error("page error:", e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/lineart/page.html`);
    await page.waitForFunction("window.pageReady === true");
    for (const [name, shot] of jobs()) {
      if (only.length && !only.includes(name)) continue;
      for (const theme of ["light", "dark"]) {
        await page.evaluate((s, t) => window.renderShot(s, t), { ...shot, size: SIZE, labelPx: LABEL_PX, linePx: LINE_PX }, theme);
        const file = path.join(RAW, `${name}-${theme}.png`);
        await (await page.$("#view")).screenshot({ path: file, omitBackground: true });
        console.log("wrote", path.relative(HERE, file));
      }
    }
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
