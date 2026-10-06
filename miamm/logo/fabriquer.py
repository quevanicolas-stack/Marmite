"""Fabrique les images de MIAMM à partir des trois PNG transparents fournis par Nico (06/10/2026) :
- logo-source.webp : le logo complet (le chef dans le badge rond aux couleurs de la DA, la marmite par-dessus les cercles,
  « miamm. » en bas) → logo-complet.png, logo-rond.png, badge embarqué dans la page (badge-192.txt, en-tête et gros
  bouton de l'accueil) et icônes de l'app (cloudflare/statique/) ;
- chef-courses-source.webp (le chef au caddie, onglet Courses) et chef-stock-source.webp (le chef au bocal et au
  bloc-notes, onglet Stock) → chef-courses.txt, chef-stock.txt.
Chaque image est recadrée au plus juste sur ses pixels visibles. Rendu par Chromium (Playwright) :
python3 miamm/logo/fabriquer.py"""
import asyncio, base64, pathlib
from playwright.async_api import async_playwright
ICI = pathlib.Path(__file__).resolve().parent
STATIQUE = ICI.parent.parent / "cloudflare" / "statique"
SOURCES = {"logo": "logo-source.webp", "caddie": "chef-courses-source.webp", "stock": "chef-stock-source.webp"}
PAGE = "<!doctype html><html><body style='margin:0'>" + "".join(
    f'<img id="{cle}" src="data:image/webp;base64,{base64.b64encode((ICI / f).read_bytes()).decode()}">' for cle, f in SOURCES.items()) + """
<script>
// recadrage au plus juste sur les pixels visibles
function rogner(img) {
  const t = document.createElement("canvas"); t.width = img.naturalWidth; t.height = img.naturalHeight;
  const x = t.getContext("2d"); x.drawImage(img, 0, 0);
  const d = x.getImageData(0, 0, t.width, t.height).data; let x0 = t.width, y0 = t.height, x1 = 0, y1 = 0;
  for (let j = 0; j < t.height; j++) for (let i = 0; i < t.width; i++) if (d[(j * t.width + i) * 4 + 3] > 24) { x0 = Math.min(x0, i); x1 = Math.max(x1, i); y0 = Math.min(y0, j); y1 = Math.max(y1, j); }
  const c = document.createElement("canvas"); c.width = x1 - x0 + 1; c.height = y1 - y0 + 1;
  c.getContext("2d").drawImage(t, x0, y0, c.width, c.height, 0, 0, c.width, c.height);
  return c;
}
// l'image posée dans un carré (ou une largeur donnée), avec une marge et un fond facultatif
function poser(src, w, h, marge, fond, type, qualite) {
  const c = document.createElement("canvas"); c.width = w; c.height = h; const x = c.getContext("2d");
  if (fond) { x.fillStyle = fond; x.fillRect(0, 0, w, h); }
  const k = Math.min((w * (1 - 2 * marge)) / src.width, (h * (1 - 2 * marge)) / src.height);
  const lw = src.width * k, lh = src.height * k;
  x.imageSmoothingQuality = "high";
  x.drawImage(src, (w - lw) / 2, (h - lh) / 2, lw, lh);
  return c.toDataURL(type || "image/png", qualite);
}
function largeur(src, l, type, qualite) { return poser(src, l, Math.round(src.height * l / src.width), 0, null, type, qualite); }
async function pret() { for (const i of document.images) await i.decode(); window.R = {}; for (const i of document.images) R[i.id] = rogner(i); return true; }
</script></body></html>"""

SORTIES = [
    # chemin, largeur, hauteur, marge, fond
    (ICI / "logo-rond.png", 1024, 1024, 0.02, None),
    (ICI / "logo-complet.png", 1024, 1024, 0.02, None),
    (STATIQUE / "icone-512.png", 512, 512, 0.04, "#FFFBF2"),
    (STATIQUE / "icone-192.png", 192, 192, 0.04, "#FFFBF2"),
    (STATIQUE / "apple-touch-icon.png", 180, 180, 0.04, "#FFFBF2"),
    (STATIQUE / "icone-512-masquable.png", 512, 512, 0.12, "#FFFBF2"),   # zone sûre des icônes Android
    (ICI / "badge-192.png", 192, 192, 0, None),
]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.set_content(PAGE); await pg.evaluate("pret()")
        for chemin, w, h, marge, fond in SORTIES:
            url = await pg.evaluate("([w, h, m, f]) => poser(R.logo, w, h, m, f)", [w, h, marge, fond])
            chemin.write_bytes(base64.b64decode(url.split(",", 1)[1]))
            print(chemin.relative_to(ICI.parent.parent), w, "×", h)
        # embarqués dans la page en WebP : le badge (net jusqu'à 150 px affichés sur un écran 2x), le caddie, le stock
        for nom, js in (("badge-192", "poser(R.logo, 320, 320, 0, null, 'image/webp', 0.86)"),
                        ("chef-courses", "largeur(R.caddie, 360, 'image/webp', 0.86)"),
                        ("chef-stock", "largeur(R.stock, 300, 'image/webp', 0.86)")):
            url = await pg.evaluate(js)
            (ICI / f"{nom}.txt").write_text(url)
            if nom != "badge-192": (ICI / f"{nom}.webp").write_bytes(base64.b64decode(url.split(",", 1)[1]))
            print(f"miamm/logo/{nom}.txt", len(url) // 1024, "Ko embarqués")
        await b.close()

asyncio.run(main())
