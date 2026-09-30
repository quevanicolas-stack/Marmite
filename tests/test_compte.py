"""Données venant du compte en ligne : elles peuvent arriver verrouillées en écriture (objets gelés).
Cocher un article, saisir un prix, cocher un repas doivent marcher quand même, et partir vers le compte."""
import asyncio, json, pathlib, sys
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
from playwright.async_api import async_playwright
MOCK = """
const gel = o => { if (o && typeof o === 'object') { Object.values(o).forEach(gel); Object.freeze(o); } return o; };
window.__doc = JSON.stringify({ version: 2, foyer: { achats: {}, payes: {}, prix: {}, magasins: {} },
  personnes: { nicolas: { coches: {}, remplacements: {}, pesees: [] }, aurelie: { coches: {}, remplacements: {}, pesees: [] } } });
window.claude = { use: async (n) => n === 'db' ? { doc: (p) => ({ get: async () => ({ exists: true, data: () => gel(JSON.parse(window.__doc)) }),
  set: async (d) => { window.__doc = JSON.stringify(d); } }) } : n === 'user' ? { id: async () => 'u1' } : null };
"""
async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script(MOCK)
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        await pg.goto(PAGE); await pg.wait_for_timeout(600)
        verif(await pg.evaluate("sync") == "compte", "compte non branché")
        await pg.tap("button.coche[data-coche]")
        verif(await pg.locator("button.coche[data-coche]").first.get_attribute("aria-pressed") == "true", "repas non coché")
        await pg.tap("#nav-barre button[data-vue='courses']")
        await pg.locator("button.check").nth(0).tap()
        verif(await pg.locator("button.check").nth(0).get_attribute("aria-pressed") == "true", "article non coché")
        await pg.fill("input[data-paye='c1-Poulet']", "30"); await pg.dispatch_event("input[data-paye='c1-Poulet']", "change")
        verif(await pg.evaluate("E.foyer.payes['c1-Poulet']") == 30, "prix payé non enregistré")
        await pg.tap("button[data-course='prix']")
        await pg.fill("input[data-prix-a='Bœuf']", "9.9"); await pg.dispatch_event("input[data-prix-a='Bœuf']", "change")
        verif(await pg.evaluate("E.foyer.prix['Bœuf'] && E.foyer.prix['Bœuf'].prix") == 9.9, "prix modifié non enregistré")
        await pg.wait_for_timeout(1200)
        doc = json.loads(await pg.evaluate("window.__doc"))
        verif(doc["foyer"]["payes"].get("c1-Poulet") == 30 and doc["foyer"]["prix"]["Bœuf"]["prix"] == 9.9, "modifications non envoyées au compte")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)
asyncio.run(main())
