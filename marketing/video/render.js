// Rendu de ad.html en MP4 : chaque image est figée avec seek(t), capturée,
// puis envoyée à ffmpeg. La bande-son (soundtrack.wav) est ajoutée si présente.
//   node render.js [--preview 0,4,10,...]   (captures PNG de contrôle)
const { chromium } = require(process.env.PW_CORE || "playwright-core");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

const FPS = 30, DURATION = 30, W = 1920, H = 1080;
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const FFMPEG = process.env.FFMPEG || "ffmpeg";
const here = __dirname;
const url = pathToFileURL(path.join(here, "ad.html")).href + "?render";

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, args: ["--allow-file-access-from-files"] });
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.goto(url, { waitUntil: "load" });
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); });

  const previewArg = process.argv.indexOf("--preview");
  if (previewArg > -1) {
    const times = process.argv[previewArg + 1].split(",").map(Number);
    fs.mkdirSync(path.join(here, "preview"), { recursive: true });
    for (const t of times) {
      await page.evaluate((t) => window.seek(t), t);
      await page.screenshot({ path: path.join(here, "preview", `t${String(t).padStart(5, "0")}.jpg`), type: "jpeg", quality: 80 });
    }
    await browser.close();
    return;
  }

  const audio = path.join(here, "soundtrack.wav");
  const out = path.join(here, "xpass-pub-30s.mp4");
  const args = ["-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-"];
  if (fs.existsSync(audio)) args.push("-i", audio, "-c:a", "aac", "-b:a", "192k", "-shortest");
  args.push("-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out);
  const ff = spawn(FFMPEG, args, { stdio: ["pipe", "ignore", "inherit"] });

  const total = FPS * DURATION;
  for (let i = 0; i < total; i++) {
    await page.evaluate((t) => window.seek(t), i / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (i % 90 === 0) process.stdout.write(`image ${i}/${total}\n`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on("close", r));
  await browser.close();
  console.log("OK", out);
})();
