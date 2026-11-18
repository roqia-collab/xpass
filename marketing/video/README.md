# Publicité XPASS — 30 s

- `xpass-pub-30s.mp4` : la vidéo finale (1920×1080, 30 i/s, H.264 + AAC).
- `ad.html` : l'animation. Ouvrez-la dans Chrome pour la voir tourner en boucle (sans le son).
- `soundtrack.js` → `soundtrack.wav` : musique et effets, composés par le script (aucun échantillon externe).
- `render.js` : filme `ad.html` image par image et assemble le MP4 avec la bande-son.
- `assets/` : photos (Unsplash, licence gratuite), logo, polices Syne et Manrope.

## Regénérer après une modification

Il faut Node, Google Chrome, et deux paquets npm (`playwright-core@1.48.2`, `ffmpeg-static@5.2.0`) :

```bash
npm install --no-save playwright-core@1.48.2 ffmpeg-static@5.2.0
node soundtrack.js
FFMPEG=node_modules/ffmpeg-static/ffmpeg.exe node render.js
```

Captures de contrôle à des instants précis : `node render.js --preview 2,12,27`.

## Minutage

| Temps | Scène |
|---|---|
| 0–3 s | Accroche « Votre ville est pleine de places libres. » |
| 3–9 s | Montage : sport, culture, beauté, sorties, ateliers, yoga — une ville par plan |
| 9–15 s | « Un seul pass. » — téléphone, crédits qui défilent |
| 15–20 s | Choisir · Réserver · Scanner (QR validé) |
| 20–25 s | Entreprises, puis commerçants |
| 25–30 s | Logo, accroche, appel à l'action |
