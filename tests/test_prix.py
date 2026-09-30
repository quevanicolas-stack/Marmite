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
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
