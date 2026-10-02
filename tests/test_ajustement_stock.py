import asyncio, pathlib
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        await pg.add_init_script("try { localStorage.setItem('marmite-tickets', 'manuel'); } catch (e) {}")   # ticket non reporté (testé dans test_achats.py)
        # jour 1 du plan (1er octobre), comme les autres tests : le test dépend des repas de ce jour-là
        await pg.add_init_script("{ const V = Date; const t = new V(2026, 9, 1, 12).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        await pg.click("button[data-ed='ouvrir'][data-k='des']")
        # yaourt 125 -> 100 en tapant, chocolat 10 -> 15 avec +
        await pg.fill("#t-des input[data-ed-q='0']", "100")
        await pg.dispatch_event("#t-des input[data-ed-q='0']", "input")
        print("infos", await pg.inner_text("#ed-infos"))
        await pg.click("#t-des button[data-ed='plus'][data-i='1']")
        await pg.select_option("#ed-ajout", "Bananes")
        await pg.click("#t-des button[data-ed='ajouter']")
        await pg.locator("#t-des").screenshot(path="/tmp/marmite_v3_edition.png")
        await pg.click("#t-des button[data-ed='suppr'][data-i='2']")
        await pg.click("#t-des button[data-ed='enregistrer']")
        print(await pg.evaluate("JSON.stringify(E.personnes.nicolas.remplacements)"))
        await pg.locator("#t-des").screenshot(path="/tmp/marmite_v3_ajuste.png")
        # remettre les quantités du plan => doit supprimer le remplacement
        await pg.click("button[data-ed='ouvrir'][data-k='dej']")
        await pg.click("#t-dej button[data-ed='plus'][data-i='0']"); await pg.click("#t-dej button[data-ed='moins'][data-i='0']")
        await pg.click("#t-dej button[data-ed='enregistrer']")
        print("dej remplacé ?", await pg.evaluate("!!E.personnes.nicolas.remplacements['d1-dej']"))
        await pg.click("#nav-barre button[data-vue='courses']")
        await pg.click("button[data-course='stock']")
        await pg.screenshot(path="/tmp/marmite_v3_stock.png", full_page=True)
        print("chocolat fin", await pg.evaluate("stockBrut(22)['Chocolat noir']"), "plan", await pg.evaluate("stockBrut(22,true)['Chocolat noir']"))
        print("erreurs", errs)
        await b.close()
asyncio.run(main())
