"""Miamm, mode d'essai (fichier ouvert sans serveur) : bouton « + » d'Aujourd'hui, grignotage pris dans le stock
(kcal et coût calculés, sorti du stock le lendemain) ou saisi à la main, compté dans le bilan du jour ; journal du Foyer
(repas cochés et grignotages, kcal et coût, filtre par personne, retrait) ; repas mangés gardés au changement de menu."""
import asyncio, pathlib, subprocess, sys
from playwright.async_api import async_playwright
RACINE = pathlib.Path(__file__).resolve().parent.parent

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    subprocess.run([sys.executable, str(RACINE / "miamm" / "construire.py")], check=True, capture_output=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 360, "height": 740})
        js = []; pg.on("pageerror", lambda e: js.append(str(e)))
        await pg.goto((RACINE / "miamm" / "miamm.html").as_uri())
        await pg.wait_for_function("typeof S !== 'undefined' && S.ecran !== 'chargement'")
        await pg.evaluate("""() => {
          S.doc.personnes = [Object.assign(PERSONNE0(), { id: 'p1', nom: 'Nico', sexe: 'h', age: 38, taille: 180, poids: 85, cible: 80 }),
                             Object.assign(PERSONNE0(), { id: 'p2', nom: 'Aurélie', age: 31, taille: 160, poids: 70, cible: 60 })];
          S.doc.reglages.debut = aujourdhui();
          S.proposition = Object.assign(composerSurMesure(1), { mode: 'mesure', graine: 1 }); validerProposition();
        }""")
        await pg.click("button[data-action=cocher][data-k=pdj]")

        # bouton « + » en haut à droite, sans recouvrir le bouton du thème
        fab, theme = await pg.locator(".fab").bounding_box(), await pg.locator(".entete [data-action=theme]").bounding_box()
        verif(fab["y"] < 40 and fab["x"] + fab["width"] <= 360 - 12, f"bouton + mal placé : {fab}")
        verif(theme["x"] + theme["width"] <= fab["x"], f"le + recouvre le thème : {fab} {theme}")
        await pg.mouse.wheel(0, 600); await pg.wait_for_timeout(100)
        verif((await pg.locator(".fab").bounding_box())["y"] < 40, "le + ne reste pas en haut au défilement")

        avant = await pg.evaluate("statsJour(jourDuPlan(), 'p1')")
        stock0 = await pg.evaluate("stockReel(jourDuPlan() + 1)['Bananes'] || 0")
        # grignotage pris dans le stock : calculé tout seul
        await pg.click(".fab")
        await pg.select_option("#g-a", "Bananes")
        await pg.fill("#g-q", "120"); await pg.locator("#g-q").dispatch_event("change")
        verif(await pg.input_value("#g-nom") == "Bananes", "nom non rempli par le produit")
        kcal = int(await pg.input_value("#g-kcal")); verif(100 <= kcal <= 120, f"kcal de 120 g de banane : {kcal}")
        verif(float(await pg.input_value("#g-prix")) > 0, "coût non calculé")
        await pg.click("form[data-form=grignotage] button[type=submit]")
        apres = await pg.evaluate("statsJour(jourDuPlan(), 'p1')")
        verif(abs(apres["fkcal"] - avant["fkcal"] - kcal) < 1 and apres["kcal"] == avant["kcal"], f"bilan du jour : {avant} → {apres}")
        verif(abs(await pg.evaluate("stockReel(jourDuPlan() + 1)['Bananes'] || 0") - (stock0 - 120)) < 0.01, "banane non sortie du stock")
        verif("Dont" in await pg.locator(".carte").first.inner_text(), "grignotage absent du bilan affiché")

        # grignotage saisi à la main, pour Aurélie
        await pg.click(".fab")
        await pg.click("button[data-action=gri-qui][data-id=p2]")
        await pg.fill("#g-nom", "Chips"); await pg.fill("#g-kcal", "270"); await pg.fill("#g-prix", "1.5")
        await pg.click("form[data-form=grignotage] button[type=submit]")
        g = await pg.evaluate("Object.values(D().grignotages).find(x => x.nom === 'Chips')")
        verif(g and g["pid"] == "p2" and g["kcal"] == 270 and g["prix"] == 1.5 and not g.get("a"), f"grignotage manuel : {g}")

        # journal du foyer
        await pg.click("[data-vue=foyer]")
        texte = await pg.locator(".journal-jour").first.inner_text()
        for mot in ("Petit-déjeuner", "Grignotage", "Chips", "Bananes", "kcal", "€"):
            verif(mot.lower() in texte.lower(), f"journal sans « {mot} » : {texte}")
        verif(await pg.locator(".ligne-j").count() == 4, "journal : 2 petits-déjeuners et 2 grignotages attendus")
        verif(await pg.evaluate("document.documentElement.scrollWidth") <= 360, "le journal déborde à 360 px")
        await pg.click("button[data-action=journal-qui][data-id=p2]")
        verif(await pg.locator(".ligne-j").count() == 2, "filtre Aurélie")
        await pg.click("button[data-action=gri-retirer]")
        verif(await pg.evaluate("Object.values(D().grignotages).length") == 1, "grignotage non retiré")

        # nouveau menu : les repas mangés restent dans le journal
        await pg.evaluate("() => { S.proposition = Object.assign(composerSurMesure(2), { mode: 'mesure', graine: 2 }); validerProposition(); }")
        verif(len(await pg.evaluate("Object.values(D().journal).flat()")) == 2, "repas mangés perdus au changement de menu")
        verif(len(await pg.evaluate("entreesJournal()")) == 3, "journal après changement de menu")
        verif(not js, f"erreurs JS : {js}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
