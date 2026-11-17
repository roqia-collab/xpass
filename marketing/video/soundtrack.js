// Bande-son originale de la publicité XPASS (30 s, 120 BPM, la mineur).
// Entièrement synthétisée ici : aucun échantillon externe, donc aucun droit à céder.
// Les effets sont calés sur les temps de ad.html.
//   node soundtrack.js  ->  soundtrack.wav (44,1 kHz, stéréo, 16 bits)
const fs = require("fs");
const path = require("path");

const SR = 44100, DUR = 30, N = SR * DUR;
const L = new Float32Array(N), R = new Float32Array(N);
const music = { L: new Float32Array(N), R: new Float32Array(N) }; // bus soumis au « pompage »
const BEAT = 0.5;

// ---------- outils ----------
let seed = 1234;
const noise = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2147483648 - 1; };
const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
const idx = (t) => Math.floor(t * SR);
function add(bus, t0, buf, gain = 1, pan = 0) {
  const s = idx(t0), gl = gain * Math.cos((pan + 1) * Math.PI / 4), gr = gain * Math.sin((pan + 1) * Math.PI / 4);
  for (let i = 0; i < buf.length && s + i < N; i++) { if (s + i < 0) continue; bus.L[s + i] += buf[i] * gl; bus.R[s + i] += buf[i] * gr; }
}
const out = { L, R };
// Filtre à variables d'état (passe-bas / passe-bande / passe-haut).
function svf() { let lo = 0, bp = 0; return (x, fc, q = 0.7) => { const f = 2 * Math.sin(Math.PI * Math.min(fc, SR / 6) / SR); const hp = x - lo - bp / q * 1; bp += f * hp; lo += f * bp; return { lo, bp, hp }; }; }
const saw = (ph) => 2 * (ph - Math.floor(ph + 0.5));

// ---------- instruments ----------
function kick(len = 0.42) {
  const n = idx(len), b = new Float32Array(n); let ph = 0;
  for (let i = 0; i < n; i++) { const t = i / SR; const f = 45 + 110 * Math.exp(-t * 28); ph += f / SR; b[i] = Math.sin(2 * Math.PI * ph) * Math.exp(-t * 7) + (t < 0.004 ? noise() * 0.4 : 0); }
  return b;
}
function clap() {
  const n = idx(0.25), b = new Float32Array(n), f = svf();
  for (let i = 0; i < n; i++) { const t = i / SR; const env = (t < 0.03 ? (Math.floor(t / 0.01) % 2 ? 0.6 : 1) : 1) * Math.exp(-t * 18); b[i] = f(noise(), 1500, 1.2).bp * env * 2.2; }
  return b;
}
function hat(open = false) {
  const n = idx(open ? 0.22 : 0.06), b = new Float32Array(n), f = svf();
  for (let i = 0; i < n; i++) { const t = i / SR; b[i] = f(noise(), 9000, 0.8).hp * Math.exp(-t * (open ? 14 : 70)); }
  return b;
}
function bassNote(m, len) {
  const n = idx(len), b = new Float32Array(n), f = svf(); let ph = 0, ph2 = 0; const fr = mtof(m);
  for (let i = 0; i < n; i++) { const t = i / SR; ph += fr / SR; ph2 += fr * 1.005 / SR;
    const env = Math.min(1, t / 0.005) * Math.exp(-t * 3) * (t > len - 0.02 ? (len - t) / 0.02 : 1);
    b[i] = f((saw(ph) + saw(ph2)) * 0.5 + Math.sin(2 * Math.PI * ph) * 0.6, 220 + 900 * Math.exp(-t * 12), 0.9).lo * env; }
  return b;
}
function pad(notes, len) {
  const n = idx(len), b = new Float32Array(n), f = svf(); const ph = notes.flatMap(() => [0, 0, 0]);
  for (let i = 0; i < n; i++) { const t = i / SR; let x = 0;
    notes.forEach((m, k) => [-0.12, 0, 0.11].forEach((d, j) => { const p = k * 3 + j; ph[p] += mtof(m + d) / SR; x += saw(ph[p]); }));
    const env = Math.min(1, t / 0.35) * Math.min(1, (len - t) / 0.4);
    b[i] = f(x / (notes.length * 3), 1400 + 500 * Math.sin(t * 1.3), 0.8).lo * env; }
  return b;
}
function pluck(m, len = 0.3, bright = 3500) {
  const n = idx(len), b = new Float32Array(n), f = svf(); let ph = 0, ph2 = 0; const fr = mtof(m);
  for (let i = 0; i < n; i++) { const t = i / SR; ph += fr / SR; ph2 += fr * 2.003 / SR;
    b[i] = f(saw(ph) * 0.7 + Math.sin(2 * Math.PI * ph2) * 0.3, 300 + bright * Math.exp(-t * 18), 1.1).lo * Math.exp(-t * 9); }
  return b;
}
function whoosh(len = 0.45, from = 400, to = 6000) {
  const n = idx(len), b = new Float32Array(n), f = svf();
  for (let i = 0; i < n; i++) { const k = i / n; const fc = from * Math.pow(to / from, k); b[i] = f(noise(), fc, 2).bp * Math.sin(Math.PI * k) ** 2 * 1.6; }
  return b;
}
function riser(len) {
  const n = idx(len), b = new Float32Array(n), f = svf(); let ph = 0;
  for (let i = 0; i < n; i++) { const k = i / n; ph += (200 + 1400 * k * k) / SR;
    b[i] = (f(noise(), 300 + 9000 * k * k, 1.5).bp * 0.9 + Math.sin(2 * Math.PI * ph) * 0.15) * k * k; }
  return b;
}
function impact(len = 2.2) {
  const n = idx(len), b = new Float32Array(n), f = svf(); let ph = 0;
  for (let i = 0; i < n; i++) { const t = i / SR; ph += (32 + 70 * Math.exp(-t * 9)) / SR;
    b[i] = Math.sin(2 * Math.PI * ph) * Math.exp(-t * 2.2) * 1.1 + f(noise(), 2500 * Math.exp(-t * 3) + 200, 0.7).lo * Math.exp(-t * 4) * 0.8; }
  return b;
}
function chime(m, len = 1.4) {
  const n = idx(len), b = new Float32Array(n);
  for (let i = 0; i < n; i++) { const t = i / SR; const f0 = mtof(m);
    b[i] = (Math.sin(2 * Math.PI * f0 * t) + 0.5 * Math.sin(2 * Math.PI * f0 * 2.76 * t) * Math.exp(-t * 4) + 0.25 * Math.sin(2 * Math.PI * f0 * 5.4 * t) * Math.exp(-t * 8)) * Math.exp(-t * 3) * Math.min(1, t / 0.002); }
  return b;
}
function blip(fr, len = 0.08) {
  const n = idx(len), b = new Float32Array(n);
  for (let i = 0; i < n; i++) { const t = i / SR; b[i] = Math.sign(Math.sin(2 * Math.PI * fr * t)) * 0.35 * Math.exp(-t * 30); }
  return b;
}
function pop(len = 0.12) {
  const n = idx(len), b = new Float32Array(n); let ph = 0;
  for (let i = 0; i < n; i++) { const t = i / SR; ph += (900 * Math.exp(-t * 30) + 300) / SR; b[i] = Math.sin(2 * Math.PI * ph) * Math.exp(-t * 35); }
  return b;
}

// ---------- arrangement ----------
const CHORDS = [ // une mesure (2 s) chacune : la m, fa, do, sol
  { pad: [57, 60, 64], bass: 33, arp: [69, 72, 76, 81] },
  { pad: [57, 60, 65], bass: 29, arp: [65, 69, 72, 77] },
  { pad: [55, 60, 64], bass: 36, arp: [67, 72, 76, 79] },
  { pad: [55, 59, 62], bass: 31, arp: [67, 71, 74, 79] },
];
const chordAt = (t) => CHORDS[Math.floor(t / 2) % 4];

// Nappe continue (intro douce, puis tout le long, plus discrète).
for (let bar = 0; bar < 15; bar++) {
  const t = bar * 2; const c = chordAt(t);
  add(music, t, pad(c.pad, 2.05), t < 3 ? 0.55 : 0.32, 0);
}
// Batterie et basse : de 3 s à 25 s pleine, puis demi-temps jusqu'à la fin.
const kicks = [];
for (let b = 0; b < 60; b++) {
  const t = b * BEAT;
  if (t >= 3 && t < 25) {
    // Respiration avant chaque nouvelle scène : on coupe le dernier temps.
    if ([8.5, 14.5, 19.5, 24.5].includes(t)) continue;
    kicks.push(t); add(out, t, kick(), 0.95);
    if (b % 2 === 1) add(music, t, clap(), 0.42, 0.05);
    add(music, t + BEAT / 2, hat(b % 4 === 3), 0.18, 0.3);
    add(music, t + BEAT / 4, hat(), 0.07, -0.3); add(music, t + 3 * BEAT / 4, hat(), 0.07, -0.3);
    const c = chordAt(t);
    add(music, t, bassNote(c.bass, 0.22), 0.55); add(music, t + 0.25, bassNote(c.bass + 12, 0.2), 0.35);
  }
  if (t >= 25 && t < 29) { if (b % 2 === 0) { kicks.push(t); add(out, t, kick(0.6), 0.8); } }
}
// Arpège en doubles croches (montage et fin), mélodie pincée (scènes 3 à 5).
for (let s = 0; s < 240; s++) {
  const t = s * 0.125; const c = chordAt(t);
  if ((t >= 3 && t < 9) || (t >= 20 && t < 24.5)) add(music, t, pluck(c.arp[s % 4], 0.22, 2500), 0.16, s % 2 ? 0.45 : -0.45);
}
const HOOK = [0, null, 2, 1, null, 3, 2, null]; // croches, indices dans l'arpège
for (let e = 0; e < 60; e++) {
  const t = e * 0.25; if (!((t >= 9 && t < 14.5) || (t >= 15 && t < 19.5))) continue;
  const k = HOOK[e % 8]; if (k === null) continue;
  add(music, t, pluck(chordAt(t).arp[k] + 12, 0.35, 4500), 0.2, 0.15);
}
// Accord final tenu.
add(music, 25, pad([57, 60, 64, 69], 5), 0.6);
add(music, 25, pluck(81, 1.2, 6000), 0.25);

// ---------- effets calés sur l'image ----------
add(out, 0.25, pop(), 0.35); add(out, 0.55, pop(), 0.3);
add(out, 1.5, riser(1.5), 0.5);
[3, 9, 15, 20, 25].forEach((t) => add(out, t, impact(t === 25 ? 3.5 : 1.8), t === 25 ? 0.9 : 0.6));
[4, 5, 6, 7, 8].forEach((t, i) => add(out, t - 0.15, whoosh(0.4), 0.55, i % 2 ? 0.5 : -0.5));
add(out, 8.6, riser(0.4), 0.35); add(out, 14.4, riser(0.6), 0.4); add(out, 19.2, riser(0.8), 0.45); add(out, 23.8, riser(1.2), 0.5);
add(out, 8.95, whoosh(0.5, 300, 4000), 0.6, 0.6); // aplat orange
for (let i = 0; i < 20; i++) add(out, 9.9 + i * 0.08, blip(1800 + i * 60, 0.03), 0.12, 0.4); // compteur de crédits
[10.6, 10.8, 11.2, 11.4, 11.6, 12.3].forEach((t, i) => add(out, t, pop(), 0.3, i % 2 ? 0.3 : -0.3));
[15.5, 15.9, 16.3].forEach((t, i) => add(out, t - 0.1, whoosh(0.45, 600, 5000), 0.5, -0.5 + i * 0.5));
add(out, 17.1, pop(), 0.35);
for (let i = 0; i < 8; i++) add(out, 17.6 + i * 0.175, blip(i % 2 ? 2400 : 2000, 0.05), 0.12); // scanner
add(out, 19.0, chime(88), 0.35); add(out, 19.08, chime(93), 0.3); // validé
add(out, 20 - 0.1, whoosh(0.6, 300, 3000), 0.5); add(out, 22.4, whoosh(0.6, 500, 6000), 0.55, 0.5);
add(out, 25.2, chime(81, 2.5), 0.3); add(out, 27, pop(), 0.3); add(out, 27.2, pop(), 0.3);

// ---------- mixage ----------
// Compression « pompée » : la musique se retire à chaque grosse caisse.
for (let i = 0; i < N; i++) {
  const t = i / SR; let since = 1;
  for (let k = kicks.length - 1; k >= 0; k--) { if (kicks[k] <= t) { since = t - kicks[k]; break; } }
  const duck = 1 - 0.55 * Math.exp(-since / 0.11);
  L[i] += music.L[i] * duck; R[i] += music.R[i] * duck;
}
// Écho stéréo léger (3/16 de temps) sur l'ensemble, pour l'espace.
const d = idx(0.1875 * 2);
for (let i = d; i < N; i++) { L[i] += R[i - d] * 0.18; R[i] += L[i - d] * 0.18; }
// Fondu final, saturation douce, normalisation à -1 dBFS.
let peak = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR; const fade = t > 29.2 ? Math.max(0, (30 - t) / 0.8) : 1;
  L[i] = Math.tanh(L[i] * 0.9) * fade; R[i] = Math.tanh(R[i] * 0.9) * fade;
  peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
}
const gain = 0.89 / peak;
const wav = Buffer.alloc(44 + N * 4);
wav.write("RIFF", 0); wav.writeUInt32LE(36 + N * 4, 4); wav.write("WAVE", 8); wav.write("fmt ", 12);
wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(2, 22); wav.writeUInt32LE(SR, 24);
wav.writeUInt32LE(SR * 4, 28); wav.writeUInt16LE(4, 32); wav.writeUInt16LE(16, 34); wav.write("data", 36); wav.writeUInt32LE(N * 4, 40);
for (let i = 0; i < N; i++) { wav.writeInt16LE(Math.round(L[i] * gain * 32767), 44 + i * 4); wav.writeInt16LE(Math.round(R[i] * gain * 32767), 46 + i * 4); }
fs.writeFileSync(path.join(__dirname, "soundtrack.wav"), wav);
console.log("soundtrack.wav", (wav.length / 1e6).toFixed(1), "Mo");
