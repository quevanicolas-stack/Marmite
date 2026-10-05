"""Planning : « Le chef prépare votre mois ». En début de mois, le chef propose le planning et les courses de chaque
semaine pour le budget choisi ; valider fait passer l'app au nouveau mois et archive le précédent, qu'on peut rouvrir."""
import asyncio, pathlib, sys
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
from playwright.async_api import async_playwright

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844})
        await ctx.add_init_script("{ const V = Date; const t = new V(2026, 9, 20, 12).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        pg = await ctx.new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        await pg.add_init_script("try { localStorage.setItem('marmite-tickets', 'manuel'); } catch (e) {}")   # ticket non reporté (testé dans test_achats.py)
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        # octobre suivi : une coche, un article acheté
        await pg.evaluate("E.personnes.nicolas.coches['d2-dej'] = true; E.foyer.achats['c1-Poulet'] = true; sauver(); rendre();")
        await pg.click("#nav-barre button[data-vue='planning']")
        await pg.click("button[data-generer='mois']")
        g = await pg.evaluate("({ debut: gen.debut, jours: gen.jours, budget: gen.budget, courses: gen.res.mois.courses.map(c => c.date), jours2: gen.res.mois.plan.length, achats: gen.res.bilan.cout.achats })")
        verif(g["debut"] == "2026-11-01" and g["jours"] == 30 and g["jours2"] == 30, f"mois proposé : {g}")
        verif(g["budget"] == 500, f"budget par défaut : {g['budget']} (350 € pour 21 jours → 500 € pour 30)")
        verif(g["courses"] == ["2026-11-03", "2026-11-10", "2026-11-17", "2026-11-24"], f"courses de la semaine : {g['courses']}")
        texte = await pg.inner_text("main")
        verif("À acheter chaque semaine" in texte and "Course 4" in texte, "tableau des courses par semaine absent")
        await pg.screenshot(path="/tmp/marmite_mois.png", full_page=True)

        # changer un repas : toucher le déjeuner du 5, chercher, filtrer, choisir steak frites
        avant = await pg.evaluate("Moteur.grilleDuMois(gen.res.mois)")
        await pg.click("button[data-changer='5-dej']")
        verif("Changer le déjeuner" in await pg.inner_text("#couche"), "feuille de choix absente")
        await pg.click("button[data-choix-filtre='plaisir']")
        noms = await pg.locator(".choix-plat b").all_inner_texts()
        plaisirs = await pg.evaluate("recettesListe().filter(r => r.tags.includes('plaisir')).map(r => r.nom)")
        verif(len(noms) >= 20 and all(n in plaisirs for n in noms), f"filtre plaisir : {noms}")
        await pg.fill("#choix-q", "steak"); await pg.dispatch_event("#choix-q", "input")
        verif(await pg.locator(".choix-plat").count() == 1, "recherche « steak » : un seul plat attendu")
        await pg.click("button[data-choix-id='steak-frites-salade']")
        apres = await pg.evaluate("Moteur.grilleDuMois(gen.res.mois)")
        verif(apres["5-dej"] == "steak-frites-salade", "repas non remplacé")
        verif(all(apres[c] == v for c, v in avant.items() if c != "5-dej"), "d'autres repas ont changé")
        verif(await pg.evaluate("gen.res.mois.courses.some(c => c.items.some(i => i.a === 'Bœuf'))"), "courses non recalculées")
        verif(await pg.evaluate("document.getElementById('couche').innerHTML === ''"), "feuille de choix restée ouverte")
        verif("Steak frites + salade" in await pg.inner_text(".gen-liste"), "le planning affiché ne montre pas le nouveau plat")
        # le dessert se change aussi
        await pg.click("button[data-changer='6-des']")
        verif(await pg.locator("button[data-choix-filtre]").count() == 0, "pas de filtres viande/poisson pour un dessert")
        await pg.click("button[data-choix-id='glace']")
        verif(await pg.evaluate("Moteur.grilleDuMois(gen.res.mois)['6-des']") == "glace", "dessert non remplacé")

        # budget plus serré : le chef recompose moins cher (ou le dit)
        await pg.fill("#mois-budget", "420"); await pg.dispatch_event("#mois-budget", "change")
        await pg.click("button[data-generer='calculer']")
        a2 = await pg.evaluate("gen.res.bilan.cout.achats")
        verif(a2 <= g["achats"] + 0.01, f"budget réduit : achats {g['achats']} → {a2}")
        verif(a2 <= 420.5 or "dépasse de" in await pg.inner_text("main"), "dépassement du budget non signalé")
        await pg.fill("#mois-budget", "500"); await pg.dispatch_event("#mois-budget", "change")
        await pg.click("button[data-generer='calculer']")

        # valider (avec confirmation dans la page)
        await pg.click("button[data-generer='valider']")
        verif("Oui, passer à novembre 2026" in await pg.inner_text("main"), "confirmation absente")
        await pg.click("button[data-generer='valider-oui']")
        etat = await pg.evaluate("({ id: MOIS_ID, n: NB_JOURS, budget: budgetFoyer(), courses: COURSES().length, archive: !!E.archives['2026-10'], coches: Object.keys(E.personnes.nicolas.coches).length, achats: Object.keys(E.foyer.achats).length })")
        verif(etat == {"id": "2026-11", "n": 30, "budget": 500, "courses": 4, "archive": True, "coches": 0, "achats": 0}, f"après validation : {etat}")
        verif("Novembre 2026" in await pg.inner_text("main"), "le planning n'affiche pas novembre")
        for v in ("jour", "courses", "budget", "profil", "planning"):
            await pg.click(f"#nav-barre button[data-vue='{v}']")
            t = await pg.inner_text("main")
            verif("octobre" not in t.lower() or v == "planning", f"vue {v} : « octobre » encore affiché")
        await pg.click("#nav-barre button[data-vue='courses']")
        verif(await pg.locator(".courses-puces .puce").count() == 4, "4 puces de courses attendues en novembre")
        await pg.click("button[data-course='stock']")
        verif("Le 30 au soir" in await pg.inner_text("main"), "« Le 30 au soir » attendu dans À la maison")

        # rechargement : novembre reste le mois affiché
        await pg.reload(); await pg.wait_for_timeout(300)
        verif(await pg.evaluate("MOIS_ID") == "2026-11", "novembre perdu au rechargement")

        # rouvrir octobre : coches et achats retrouvés, novembre archivé
        await pg.click("#nav-barre button[data-vue='planning']")
        await pg.click("button[data-rouvrir='2026-10']")
        e2 = await pg.evaluate("({ id: MOIS_ID, n: NB_JOURS, coche: !!E.personnes.nicolas.coches['d2-dej'], achat: !!E.foyer.achats['c1-Poulet'], archiveNov: !!E.archives['2026-11'] })")
        verif(e2 == {"id": "2026-10", "n": 21, "coche": True, "achat": True, "archiveNov": True}, f"réouverture d'octobre : {e2}")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "la page déborde")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
