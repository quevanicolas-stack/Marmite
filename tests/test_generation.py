"""Planning : « Demander au chef un planning selon le stock » (en cours de mois). La proposition part du stock réel, s'applique aux repas
à venir des deux personnes et recalcule les courses suivantes ; on peut revenir au menu d'avant.
Aucune mention de Claude à l'écran : on parle du chef."""
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
        await pg.add_init_script("try { localStorage.setItem('marmite-tickets', 'manuel'); } catch (e) {}")   # ticket non reporté (testé dans test_achats.py)
        # 3 octobre : la Course 1 est faite (tout coché), le petit-déjeuner du jour est coché
        await pg.add_init_script("{ const V = Date; const t = new V(2026, 9, 3, 12).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        verif("demandez au chef" in (await pg.inner_text("main")).lower(), "bouton « J'ai faim, demandez au chef » absent")
        await pg.evaluate("""for (const it of itemsCourse(COURSES()[0])) E.foyer.achats[cleLigne(1, it)] = true;
                             E.personnes.nicolas.coches['d3-pdj'] = true; rendre();""")
        await pg.click("#nav-barre button[data-vue='planning']")
        await pg.click("button[data-generer='ouvrir']")
        texte = await pg.inner_text("main")
        verif("Refaire le planning selon le stock" in texte and "Le chef prépare votre mois" in texte, "cartes du chef absentes")
        res = await pg.evaluate("gen && gen.res && { j0: gen.j0, jours: gen.res.mois.plan.length, courses: gen.res.mois.courses.map(c => c.date), gardees: gen.res.gardees, stock: gen.res.stockUtilise.length }")
        verif(res and res["j0"] == 4, f"premier jour modifiable : {res and res['j0']}, 4 attendu (repas du 3 déjà coché)")
        verif(res and res["jours"] == 18, "18 jours à composer du 4 au 21")
        verif(res and res["courses"] == ["2026-10-08", "2026-10-15"] and res["gardees"] == [1], f"courses : {res}")
        verif(res and res["stock"] > 5, "le menu n'utilise presque rien du stock")
        await pg.screenshot(path="/tmp/marmite_generation.png", full_page=True)

        # une autre proposition change le menu
        avant = await pg.evaluate("JSON.stringify(gen.res.mois.plan.map(j => j.meals.map(m => m.recette)))")
        await pg.click("button[data-generer='autre']")
        verif(await pg.evaluate("JSON.stringify(gen.res.mois.plan.map(j => j.meals.map(m => m.recette)))") != avant, "« Une autre idée » donne le même menu")

        # appliquer
        await pg.click("button[data-generer='appliquer']")
        etat = await pg.evaluate("""(() => { const out = { genere: 0, sansViande: [], avant: 0 };
            for (let d = 1; d <= NB_JOURS; d++) for (const k of CLES) for (const p of ['nicolas', 'aurelie']) {
              const r = E.personnes[p].remplacements['d' + d + '-' + k];
              if (r && r.genere) { out.genere++; if (d < 4) out.avant++;
                if ((k === 'dej' || k === 'din') && !r.items.some(([a]) => DONNEES.catalogue[a] && DONNEES.catalogue[a].animal)) out.sansViande.push(d + k); } }
            out.courses = COURSES().map(c => [c.id, c.jourPlan]); return out; })()""")
        verif(etat["genere"] == 18 * 4 * 2, f"{etat['genere']} repas générés, 144 attendus")
        verif(etat["avant"] == 0, "des jours déjà passés ont été modifiés")
        verif(not etat["sansViande"], f"repas sans viande ni poisson : {etat['sansViande']}")
        verif(etat["courses"] == [[1, 1], [2, 8], [3, 15]], f"courses après génération : {etat['courses']}")
        verif("Revenir au planning d'avant" in await pg.inner_text("main"), "lien pour revenir au planning d'avant absent")

        # revenir au menu d'avant
        await pg.click("button[data-generer='annuler']")
        verif(await pg.evaluate("!E.foyer.generation && !Object.values(E.personnes.nicolas.remplacements).some(r => r.genere)"), "retour au menu d'avant incomplet")
        verif(await pg.evaluate("COURSES() === DONNEES.courses"), "courses d'origine non rétablies")

        # aucune mention de Claude, dans aucune vue
        for v in ("jour", "planning", "courses", "budget", "profil"):
            await pg.click(f"#nav-barre button[data-vue='{v}']")
            verif("Claude" not in await pg.inner_text("body"), f"« Claude » affiché dans la vue {v}")
        await pg.click("#nav-barre button[data-vue='jour']")
        await pg.click("button[data-ia='faim']")
        verif("Demandez au chef" in await pg.inner_text("body"), "feuille « Demandez au chef » absente")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "la page déborde")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
