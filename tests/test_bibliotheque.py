"""Bibliothèque de 100 plats et leurs variantes : visibles dans « Changer » à la préparation du mois,
choisies comme n'importe quel plat ; produits exclus dans Profil : plus aucun plat qui en contient."""
import asyncio, pathlib, sys
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
from playwright.async_api import async_playwright

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        await pg.add_init_script("try { localStorage.setItem('marmite-tickets', 'manuel'); } catch (e) {}")
        await pg.add_init_script("{ const V = Date; const t = new V(2026, 9, 20, 12).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)

        n = await pg.evaluate("recettesListe().filter(r => r.repas.includes('dej') || r.repas.includes('din')).length")
        verif(n >= 280, f"{n} plats possibles seulement")

        # 1. exclure le poulet et la mozzarella râpée dans Profil
        await pg.click("#nav-barre button[data-vue='profil']")
        for a in ("Poulet", "Mozzarella râpée"):
            await pg.select_option("#ajout-exclu", a)
            await pg.click("button[data-action='exclure']")
        verif(await pg.evaluate("JSON.stringify(E.foyer.exclus)") == '["Poulet","Mozzarella râpée"]', "exclusions non enregistrées")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Profil déborde")

        # 2. le chef prépare novembre sans ces produits
        await pg.click("#nav-barre button[data-vue='planning']")
        await pg.click("button[data-generer='mois']")
        trouves = await pg.evaluate("""gen.res.mois.plan.flatMap(j => j.meals.filter(m => m.k !== 'pdj')
            .flatMap(m => m.items.nicolas.filter(([a]) => a === 'Poulet' || a === 'Mozzarella râpée').map(([a]) => j.d + m.k + ' ' + a)))""")
        verif(not trouves, f"produits exclus dans le mois : {trouves[:5]}")
        verif(await pg.evaluate("gen.res.bilan.recettesUtilisees") >= 40, "trop peu de plats différents dans le mois")

        # 3. « Changer » montre les variantes ; on en choisit une
        await pg.click("button[data-changer='5-din']")
        await pg.fill("#choix-q", "gratin de pommes de terre"); await pg.dispatch_event("#choix-q", "input")
        liste = await pg.inner_text("#choix-liste")
        verif("(emmental)" in liste and "(sans fromage)" in liste, "variantes du gratin absentes de la liste")
        verif("(mozzarella)" not in liste, "la variante à la mozzarella (exclue) est proposée")
        await pg.click("button[data-choix-id='gratin-de-pommes-de-terre-au-jambon-mozzarella~emmental-rape']")
        r = await pg.evaluate("""(() => { const m = gen.res.mois.plan.find(j => j.d === 5).meals.find(x => x.k === 'din');
            return { recette: m.recette, nom: m.plat.nicolas, emmental: m.items.nicolas.some(([a]) => a === 'Emmental râpé'),
                     courses: gen.res.mois.courses.some(c => c.items.some(i => i.a === 'Emmental râpé')) }; })()""")
        verif(r["recette"].endswith("~emmental-rape") and "emmental" in r["nom"] and r["emmental"], f"variante non appliquée : {r}")
        verif(r["courses"], "l'emmental n'est pas dans les courses")

        # 4. ne plus exclure le poulet
        await pg.click("#nav-barre button[data-vue='profil']")
        await pg.click("button[data-exclu-retirer='Poulet']")
        verif(await pg.evaluate("JSON.stringify(E.foyer.exclus)") == '["Mozzarella râpée"]', "le poulet est encore exclu")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
