"""Fabrique le logo de MIAMM à partir de la mascotte (miamm/logo/mascotte-source.jpg) :
le fond blanc est détouré, la mascotte est posée dans un badge rond aux couleurs de la DA (safran, paprika,
aubergine, crème), la tête dépassant du cercle façon cartoon. Sorties : logo-rond.png, logo-complet.png,
les icônes de l'app (cloudflare/statique/) et la petite version embarquée dans la page (miamm/logo/badge-192.txt).
Rendu par Chromium (Playwright) : python3 miamm/logo/fabriquer.py"""
import asyncio, base64, pathlib
from playwright.async_api import async_playwright
ICI = pathlib.Path(__file__).resolve().parent
STATIQUE = ICI.parent.parent / "cloudflare" / "statique"
SOURCE = base64.b64encode((ICI / "mascotte-source.jpg").read_bytes()).decode()

PAGE = """<!doctype html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&display=swap" rel="stylesheet">
</head><body style="margin:0"><img id="m" src="data:image/jpeg;base64,%s"><canvas id="c"></canvas>
<script>
const AUB = "#3B1F4A", SAF = "#F5B700", PAP = "#E4572E", BAS = "#7DB46C", CRE = "#FFFBF2";
// détourage : remplissage depuis les bords sur le blanc pur, bord adouci
function detourer(img) {
  const c = document.createElement("canvas"), w = c.width = img.naturalWidth, h = c.height = img.naturalHeight, x = c.getContext("2d");
  x.drawImage(img, 0, 0);
  const d = x.getImageData(0, 0, w, h), p = d.data, vu = new Uint8Array(w * h), pile = [];
  const blanc = i => p[i * 4] > 246 && p[i * 4 + 1] > 246 && p[i * 4 + 2] > 246;
  for (let i = 0; i < w; i++) { pile.push(i, (h - 1) * w + i); } for (let j = 0; j < h; j++) { pile.push(j * w, j * w + w - 1); }
  while (pile.length) {
    const i = pile.pop(); if (vu[i] || !blanc(i)) continue; vu[i] = 1;
    const a = i %% w, b = (i / w) | 0;
    if (a > 0) pile.push(i - 1); if (a < w - 1) pile.push(i + 1); if (b > 0) pile.push(i - w); if (b < h - 1) pile.push(i + w);
  }
  for (let i = 0; i < w * h; i++) {
    if (vu[i]) { p[i * 4 + 3] = 0; continue; }
    // bord : un pixel clair voisin du fond devient semi-transparent
    const a = i %% w, b = (i / w) | 0, voisin = (a > 0 && vu[i - 1]) || (a < w - 1 && vu[i + 1]) || (b > 0 && vu[i - w]) || (b < h - 1 && vu[i + w]);
    if (voisin) { const l = (p[i * 4] + p[i * 4 + 1] + p[i * 4 + 2]) / 3; if (l > 200) p[i * 4 + 3] = Math.max(0, 255 - (l - 200) * 4.6); }
  }
  x.putImageData(d, 0, 0);
  return c;
}
// badge : cercle safran cerné d'aubergine, assiette crème, anneau paprika ; la mascotte dépasse par le haut
function badge(x, cx, cy, r, mascotte) {
  x.save();
  x.lineWidth = r * 0.07; x.strokeStyle = AUB;
  x.beginPath(); x.arc(cx, cy, r, 0, 7); x.fillStyle = PAP; x.fill(); x.stroke();
  x.beginPath(); x.arc(cx, cy, r * 0.86, 0, 7); x.fillStyle = SAF; x.fill();
  x.lineWidth = r * 0.03; x.strokeStyle = CRE; x.globalAlpha = .9;
  x.beginPath(); x.arc(cx, cy, r * 0.72, 0, 7); x.stroke(); x.globalAlpha = 1;
  // petites pastilles, comme des grains de poivre autour de l'assiette
  [[-.62, -.5, BAS], [.66, -.42, CRE], [-.74, .2, CRE], [.7, .38, BAS]].forEach(([dx, dy, col]) => { x.beginPath(); x.arc(cx + dx * r, cy + dy * r, r * .045, 0, 7); x.fillStyle = col; x.fill(); });
  // la mascotte : dans le cercle, la tête en dépasse
  const t = r * 2.45, mx = cx - t / 2 + r * 0.02, my = cy - r * 1.5;
  x.save();
  // seule la tête dépasse du cercle (la vapeur et le reste restent dedans)
  x.beginPath(); x.arc(cx, cy, r * 0.93, 0, Math.PI * 2); x.rect(cx - r * 0.6, my - 10, r * 1.2, cy - r * 0.2 - my + 10); x.clip();
  x.shadowColor = "rgba(36,17,46,.28)"; x.shadowBlur = r * .05; x.shadowOffsetY = r * .02;
  x.drawImage(mascotte, mx, my, t, t);
  x.restore();
  // le bas du cercle repasse par-dessus pour un contour net
  x.lineWidth = r * 0.07; x.strokeStyle = AUB; x.beginPath(); x.arc(cx, cy, r, 0.08 * Math.PI, 0.92 * Math.PI); x.stroke();
  x.restore();
}
function rendre(w, h, opts) {
  const c = document.getElementById("c"); c.width = w; c.height = h; const x = c.getContext("2d");
  x.clearRect(0, 0, w, h);
  if (opts.fond) { x.fillStyle = opts.fond; x.fillRect(0, 0, w, h); }
  badge(x, opts.cx * w, opts.cy * h, opts.r * w, window.MASCOTTE);
  if (opts.texte) {
    x.font = `800 ${opts.texte * w}px "Bricolage Grotesque", sans-serif`; x.textAlign = "center"; x.textBaseline = "alphabetic";
    const y = opts.ty * h, mot = "miamm", lw = x.measureText(mot).width, pw = x.measureText(".").width;
    x.lineJoin = "round"; x.lineWidth = opts.texte * w * .16; x.strokeStyle = CRE;
    x.strokeText(mot + ".", w / 2, y);
    x.fillStyle = AUB; x.textAlign = "left"; const x0 = w / 2 - (lw + pw) / 2; x.fillText(mot, x0, y); x.fillStyle = PAP; x.fillText(".", x0 + lw, y);
  }
  return c.toDataURL("image/png");
}
async function pret() { await document.fonts.load('800 40px "Bricolage Grotesque"'); const m = document.getElementById("m"); await m.decode(); window.MASCOTTE = detourer(m); return document.fonts.check('800 40px "Bricolage Grotesque"'); }
</script></body></html>""" % SOURCE

SORTIES = [
    # nom, largeur, hauteur, options (proportions de la largeur / hauteur)
    (ICI / "logo-rond.png", 1024, 1024, {"cx": .5, "cy": .6, "r": .36}),
    (ICI / "logo-complet.png", 1024, 1200, {"cx": .5, "cy": .5, "r": .34, "texte": .17, "ty": .95}),
    (STATIQUE / "icone-512.png", 512, 512, {"cx": .5, "cy": .6, "r": .33, "fond": "#FFFBF2"}),
    (STATIQUE / "icone-192.png", 192, 192, {"cx": .5, "cy": .6, "r": .33, "fond": "#FFFBF2"}),
    (STATIQUE / "apple-touch-icon.png", 180, 180, {"cx": .5, "cy": .6, "r": .33, "fond": "#FFFBF2"}),
    (STATIQUE / "icone-512-masquable.png", 512, 512, {"cx": .5, "cy": .6, "r": .25, "fond": "#FFFBF2"}),
    (ICI / "badge-192.png", 192, 192, {"cx": .5, "cy": .6, "r": .34}),
]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.set_content(PAGE, wait_until="networkidle")
        police = await pg.evaluate("pret()")
        print("police Bricolage chargée :", police)
        for chemin, w, h, o in SORTIES:
            url = await pg.evaluate("([w, h, o]) => rendre(w, h, o)", [w, h, o])
            chemin.write_bytes(base64.b64decode(url.split(",", 1)[1]))
            print(chemin.relative_to(ICI.parent.parent), w, "×", h)
        await b.close()
    # version embarquée dans la page (data URI), pour l'en-tête
    (ICI / "badge-192.txt").write_text("data:image/png;base64," + base64.b64encode((ICI / "badge-192.png").read_bytes()).decode())

asyncio.run(main())
