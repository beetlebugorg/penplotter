// Shared code for the two simulator pages: the WebSocket link and the LCD decoder.

// connect opens the WebSocket at /ws and opens it again when it closes.
// onMessage gets each JSON object from the server.
// The function returns an object with send(obj).
export function connect(onMessage, onStatus = () => {}) {
  const url = new URL("ws", location.href).href.replace(/^http/, "ws"); // relative, so the page also works under a prefix
  let ws = null;
  let delay = 500;
  const banner = makeBanner();

  function open() {
    ws = new WebSocket(url);
    ws.onopen = () => {
      delay = 500;
      banner.hidden = true;
      onStatus(true);
    };
    ws.onmessage = (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      onMessage(msg);
    };
    ws.onclose = () => {
      banner.hidden = false;
      onStatus(false);
      setTimeout(open, delay);
      delay = Math.min(delay * 2, 4000);
    };
    ws.onerror = () => ws.close();
  }
  open();

  return {
    send(obj) {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
    },
  };
}

function makeBanner() {
  const el = document.createElement("div");
  el.className = "ws-banner";
  el.textContent = "Disconnected from the simulator. Trying again…";
  el.hidden = true;
  document.body.appendChild(el);
  return el;
}

// decodeLcd converts the base64 framebuffer (128 x 64, 16 bytes per row,
// MSB = leftmost pixel) to a Uint8Array with one byte per pixel (0 or 1).
export function decodeLcd(b64, w = 128, h = 64) {
  const raw = atob(b64);
  const px = new Uint8Array(w * h);
  const stride = w / 8;
  for (let y = 0; y < h; y++) {
    for (let bx = 0; bx < stride; bx++) {
      const b = raw.charCodeAt(y * stride + bx);
      for (let i = 0; i < 8; i++) px[y * w + bx * 8 + i] = (b >> (7 - i)) & 1;
    }
  }
  return px;
}

// LCD colours of the Creality 12864 display: white pixels on a blue backlight.
// LCD_BG is the thin line between pixels. It is a little darker than LCD_OFF.
export const LCD_BG = [27, 72, 204];
export const LCD_OFF = [30, 78, 214];
export const LCD_ON = [235, 242, 255];

// drawLcd draws the pixels into a 2D canvas context. scale is the size of
// one LCD pixel in canvas pixels. gap is the dark line between pixels.
export function drawLcd(ctx, px, w, h, scale, gap) {
  const img = ctx.createImageData(w * scale, h * scale);
  const d = img.data;
  const W = w * scale;
  for (let y = 0; y < h * scale; y++) {
    const ly = (y / scale) | 0;
    const gy = y % scale >= scale - gap;
    for (let x = 0; x < W; x++) {
      const lx = (x / scale) | 0;
      const gx = x % scale >= scale - gap;
      const on = px[ly * w + lx];
      let c = on ? LCD_ON : LCD_OFF;
      if (gx || gy) c = LCD_BG;
      const o = (y * W + x) * 4;
      d[o] = c[0];
      d[o + 1] = c[1];
      d[o + 2] = c[2];
      d[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
}

// Beeper: a short square-wave tone. The browser starts audio only after
// the first user input, so the context starts on the first click or key.
let audio = null;
export function unlockAudio() {
  if (!audio) {
    try {
      audio = new AudioContext();
    } catch {
      audio = null;
    }
  }
  if (audio && audio.state === "suspended") audio.resume();
}
export function beep(ms = 60, freq = 2700) {
  if (!audio || audio.state !== "running") return;
  const o = audio.createOscillator();
  const g = audio.createGain();
  o.type = "square";
  o.frequency.value = freq;
  g.gain.value = 0.04;
  o.connect(g).connect(audio.destination);
  const t = audio.currentTime;
  o.start(t);
  o.stop(t + ms / 1000);
}
