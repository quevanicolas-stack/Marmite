import asyncio, pathlib
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
import json
from playwright.async_api import async_playwright
MOCK = """
window.claude = { use: async (n) => {
  if (n !== 'sample') return null;
  const f = async () => ({text:''});
  f.json = async (input, opts) => { window.__prompt = input; return { plats: [
    { nom: 'Rougail poulet express', pourquoi: 'Utilise le poulet et les tomates en stock.', temps_min: 25,
      ingredients: [ {aliment:'Poulet', quantite: 300}, {aliment:'Tomates', quantite: 300}, {aliment:'Oignon', quantite: 80}, {aliment:'Riz', quantite: 150}, {aliment:'Huile', quantite: 15} ],
      etapes: ['Faire revenir', 'Mijoter 15 min'] },
    { nom: 'Omelette géante', pourquoi: 'Rapide.', temps_min: 15, ingredients: [ {aliment:'Œufs', quantite: 5}, {aliment:'Courgettes', quantite: 300}, {aliment:'Crème fraîche', quantite: 50} ], etapes: ['Battre', 'Cuire'] },
    { nom: 'Pâtes au thon', pourquoi: 'Plaisir.', temps_min: 20, ingredients: [ {aliment:'Pâtes', quantite: 250}, {aliment:'Mangue', quantite: 900} ], etapes: [] } ] }; };
  return f; } };
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script(MOCK)
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        await pg.goto(PAGE)
        await pg.wait_for_timeout(400)
        print("prévu N", await pg.evaluate("totalPrevu('nicolas')"), "A", await pg.evaluate("totalPrevu('aurelie')"))
        await pg.screenshot(path="/tmp/marmite_v2_jour_n.png")
        await pg.click("#qui-haut button[data-personne='aurelie']")
        await pg.wait_for_timeout(100)
        await pg.screenshot(path="/tmp/marmite_v2_jour_a.png", full_page=True)
        await pg.click("#theme-haut button")
        await pg.wait_for_timeout(100)
        await pg.screenshot(path="/tmp/marmite_v2_jour_a_dark.png")
        await pg.click("#theme-haut button")
        await pg.click("#qui-haut button[data-personne='nicolas']")
        # IA
        await pg.click("button[data-ia='din']")
        await pg.click("button[data-action='plus']")
        await pg.click("div[data-action='budget']")
        await pg.screenshot(path="/tmp/marmite_v2_ia_form.png")
        await pg.click("button[data-action='proposer']")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path="/tmp/marmite_v2_ia_res.png", full_page=False)
        pr = await pg.evaluate("window.__prompt")
        print(pr[:2200])
        await pg.click("button[data-choisir='0']")
        await pg.wait_for_timeout(100)
        print("remp N", await pg.evaluate("JSON.stringify(E.personnes.nicolas.remplacements)"))
        print("remp A", await pg.evaluate("JSON.stringify(E.personnes.aurelie.remplacements)"))
        await pg.screenshot(path="/tmp/marmite_v2_apres.png", full_page=True)
        for v in ["planning", "courses", "budget", "profil"]:
            await pg.click(f"#nav-barre button[data-vue='{v}']")
            await pg.wait_for_timeout(100)
            await pg.screenshot(path=f"/tmp/marmite_v2_{v}.png", full_page=True)
        pg2 = await b.new_page(viewport={"width": 1366, "height": 900})
        await pg2.route("**/fonts.g*/**", lambda r: r.abort())
        await pg2.goto(PAGE)
        await pg2.wait_for_timeout(300)
        await pg2.screenshot(path="/tmp/marmite_v2_desk.png")
        await pg2.click("#theme-rail button")
        await pg2.click("#nav-rail button[data-vue='budget']")
        await pg2.screenshot(path="/tmp/marmite_v2_desk_dark_budget.png")
        print("erreurs", errs)
        await b.close()
asyncio.run(main())
