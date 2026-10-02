"""Onglet « Prix » des courses : un prix modifié remplace celui du catalogue partout (courses, coût des repas),
se rétablit en un clic, et un prix payé y apparaît comme tel."""
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
        # lignes détaillées (prix et quantité visibles) : le mode magasin est testé dans test_ecrans.py
        await pg.add_init_script("try { localStorage.setItem('marmite-courses', 'detail'); } catch (e) {}")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        await pg.click("#nav-barre button[data-vue='courses']")

        # Course 1 : estimation du poulet (2 paquets à 11,27 €)
        avant = await pg.evaluate("bilanCourse(1).est")
        await pg.click("button[data-course='prix']")
        verif(await pg.locator("input[data-prix-a='Poulet']").input_value() == "11.27", "prix du poulet d'origine attendu : 11,27")
        # produits ajoutés depuis octobre : présents, marqués « estimé » tant que personne n'a corrigé leur prix
        verif("estimé" in await pg.inner_text(".prix-ligne:has(input[data-prix-a='Saucisses (porc)'])"), "saucisses : étiquette « estimé » absente")

        # le poulet passe à 12,50 € le paquet : +2 × 1,23 € sur la Course 1
        await pg.fill("input[data-prix-a='Poulet']", "12.5")
        await pg.dispatch_event("input[data-prix-a='Poulet']", "change")
        apres = await pg.evaluate("bilanCourse(1).est")
        verif(abs(apres - avant - 2 * 1.23) < 0.01, f"Course 1 : {avant:.2f} → {apres:.2f}, +2,46 € attendus")
        verif(await pg.evaluate("prixUnitaire('Poulet')") == 0.0125, "prix unitaire du poulet non mis à jour")
        verif(await pg.evaluate("E.foyer.prix['Poulet'].source") == "saisi", "source du prix : saisi attendu")
        verif("modifié le" in await pg.inner_text(".prix-ligne:has(input[data-prix-a='Poulet'])"), "mention « modifié le » absente")
        await pg.screenshot(path="/tmp/marmite_prix.png")

        # vrac : le prix est au kilo
        verif("€/kg" in await pg.inner_text(".prix-ligne:has(input[data-prix-a='Tomates'])"), "tomates : prix au kilo attendu")

        # rétablir
        await pg.click("button[data-prix-reset='Poulet']")
        verif(abs(await pg.evaluate("bilanCourse(1).est") - avant) < 0.01, "rétablir : estimation d'origine non retrouvée")
        verif(await pg.evaluate("!E.foyer.prix['Poulet']"), "rétablir : prix saisi toujours enregistré")

        # un prix payé à la course apparaît dans l'onglet Prix
        await pg.click("button[data-course='1']")
        await pg.locator(".article", has_text="Poulet").locator("button.check").click()
        await pg.fill("input[data-paye='c1-Poulet']", "21")
        await pg.dispatch_event("input[data-paye='c1-Poulet']", "change")
        await pg.click("button[data-course='prix']")
        verif(await pg.locator("input[data-prix-a='Poulet']").input_value() == "10.5", "prix payé : 21 € pour 2 paquets → 10,50 € attendus")
        verif("d'après le prix payé" in await pg.inner_text(".prix-ligne:has(input[data-prix-a='Poulet'])"), "mention « d'après le prix payé » absente")
        # prix tapé directement sur la ligne, sans cocher : l'article se coche, la projection du cycle suit
        await pg.click("button[data-course='1']")   # retour aux listes, puis la Course 2
        await pg.click("button[data-course='2']")
        proj0 = await pg.evaluate("projectionFoyer().total")
        it = await pg.evaluate("DONNEES.courses[1].items.find(i => i.a === 'Bœuf')")
        est = await pg.evaluate("estimationLigne(DONNEES.courses[1].items.find(i => i.a === 'Bœuf'))")
        await pg.fill("input[data-paye='c2-Bœuf']", str(round(est + 5, 2)))
        await pg.dispatch_event("input[data-paye='c2-Bœuf']", "change")
        verif(await pg.evaluate("!!E.foyer.achats['c2-Bœuf']"), "prix tapé sans cocher : article non coché")
        proj1 = await pg.evaluate("projectionFoyer().total")
        # +5 € sur la ligne payée, et le nouveau prix du bœuf réestime aussi les lignes de bœuf pas encore payées
        autres = await pg.evaluate("DONNEES.courses.filter(c => c.id !== 2).flatMap(c => c.items).filter(i => i.a === 'Bœuf').reduce((s, i) => s + i.buy, 0)")
        attendu = 5 + autres * 5 / it["buy"]
        verif(abs(proj1 - proj0 - attendu) < 0.02, f"projection : {proj0:.2f} → {proj1:.2f}, +{attendu:.2f} € attendus")
        verif("Consommation prévue du foyer" in await pg.inner_text("main"), "ligne de projection absente")
        await pg.screenshot(path="/tmp/marmite_course_prix.png")
        # pas de défilement horizontal sur téléphone, dans aucun onglet des courses
        await pg.set_viewport_size({"width": 360, "height": 800})
        for c in ("1", "2", "stock", "prix"):
            await pg.click(f"button[data-course='{c}']")
            verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"onglet {c} : la page déborde à 360 px")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
