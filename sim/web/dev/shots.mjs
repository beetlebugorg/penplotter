// Screenshot check: opens both pages in headless Chromium, prints the console
// errors, and writes PNG files. The server must run first (mock or plotsim).
//
//   node shots.mjs [base-url] [out-dir]
import { chromium } from "playwright-core";
import fs from "node:fs";

const base = process.argv[2] || "http://localhost:8090";
const out = process.argv[3] || "shots";
fs.mkdirSync(out, { recursive: true });

const exe = process.env.CHROMIUM || "/usr/bin/chromium";
const browser = await chromium.launch({
  executablePath: exe,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
let errors = 0;
async function open(path, w, h, scheme = "light") {
  const page = await browser.newPage({ viewport: { width: w, height: h }, colorScheme: scheme });
  page.on("console", (m) => {
    // The pages probe /stl/ for optional parts. A 404 there is normal.
    if (m.text().startsWith("Failed to load resource")) return;
    if (m.type() === "error" || m.type() === "warning") {
      console.log(`[${path}] ${m.type()}: ${m.text()}`);
      if (m.type() === "error") errors++;
    }
  });
  page.on("pageerror", (e) => {
    console.log(`[${path}] pageerror: ${e.message}`);
    errors++;
  });
  page.on("response", (r) => {
    if (r.status() >= 400 && !r.url().includes("/stl/")) {
      console.log(`[${path}] ${r.status()} ${r.url()}`);
      errors++;
    }
  });
  await page.goto(base + "/" + path, { waitUntil: "domcontentloaded" });
  return page;
}

// LCD page: status screen, then the menu after one push and two detents.
const lcd = await open("lcd.html", 520, 420);
await lcd.waitForTimeout(1200);
await lcd.screenshot({ path: `${out}/lcd-status.png` });
await lcd.keyboard.down("Enter");
await lcd.keyboard.up("Enter");
await lcd.keyboard.press("ArrowRight");
await lcd.keyboard.press("ArrowRight");
await lcd.click("summary");
await lcd.waitForTimeout(500);
await lcd.screenshot({ path: `${out}/lcd-menu.png` });
// Leave the menu on BACK.
await lcd.keyboard.press("ArrowLeft");
await lcd.keyboard.press("ArrowLeft");
await lcd.keyboard.down("Enter");
await lcd.keyboard.up("Enter");

// Machine page: run at 50x, then take a wide view and a close view.
const mach = await open("machine.html", 1400, 900);
await mach.waitForTimeout(3000);
await mach.click("text=50×");
await mach.waitForTimeout(Number(process.env.PLOT_MS || 9000));
await mach.screenshot({ path: `${out}/machine-wide.png` });
await mach.evaluate(() => window.plotsim.frameBed());
await mach.waitForTimeout(800);
await mach.screenshot({ path: `${out}/machine-bed.png` });
// Close view of the carriage, and a view from the back-left (Y motors, cables).
async function view(name, target, pos) {
  await mach.evaluate(([t, p]) => {
    const { camera, controls, f2s } = window.plotsim;
    controls.target.copy(f2s(...t));
    camera.position.copy(f2s(...p));
    controls.update();
  }, [target, pos]);
  await mach.waitForTimeout(500);
  await mach.screenshot({ path: `${out}/${name}.png` });
}
const st = await mach.evaluate(() => window.plotsim.state);
const px = 82.3 + st.x, py = 36.5 + st.y;
await view("machine-head", [px, py + 30, 70], [px + 260, py - 260, 260]);
await view("machine-back", [150, 400, 40], [-450, 1000, 520]);
await view("machine-pod", [-200, 80, 30], [-420, -170, 300]);
await mach.close();
const dark = await open("machine.html", 1000, 640, "dark");
await dark.waitForTimeout(3500);
await dark.screenshot({ path: `${out}/machine-dark.png` });

await browser.close();
console.log(errors ? `${errors} errors` : "no errors");
process.exit(errors ? 1 : 0);
