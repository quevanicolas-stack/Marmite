"""Courses : toucher la ligne d'un article le coche (le champ « Prix payé » ne décoche pas).
Poubelle de l'onglet « À la maison » : un produit jeté sort du stock, jamais d'office ; on peut annuler.
Jambon acheté au gramme : 150 g à la Course 1."""
import asyncio, pathlib, sys
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
from playwright.async_api import async_playwright

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 390, "height": 844})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        # le plan commence le 1er octobre : on se place au 3 pour avoir du stock « ce matin »
        await pg.add_init_script("{ const V = Date; const t = new V(2026, 9, 3, 12).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)

        await pg.click("#nav-barre button[data-vue='courses']")
        texte = await pg.inner_text("main")
        verif("150 g en vrac" in texte, "Course 1 : jambon attendu à 150 g en vrac")

        # toucher le nom de l'article coche la case ; toucher le champ « Prix payé » ne la décoche pas
        await pg.locator(".article .nom").nth(3).click()
        verif(await pg.locator(".article button.check").nth(3).get_attribute("aria-pressed") == "true", "clic sur le nom : case non cochée")
        await pg.locator(".article input[data-paye]").first.click()
        verif(await pg.locator(".article button.check").nth(3).get_attribute("aria-pressed") == "true", "clic sur « Prix payé » : case décochée")
        await pg.locator(".article .detail").nth(3).click()
        verif(await pg.locator(".article button.check").nth(3).get_attribute("aria-pressed") == "false", "second clic sur la ligne : case toujours cochée")

        j = await pg.evaluate("jourDuPlan()")
        avant = await pg.evaluate(f"stockBrut({j})['Jambon']")
        verif(await pg.evaluate("E.foyer.pertes.length") == 0, "aucune perte au départ")
        await pg.click("button[data-course='stock']")
        await pg.click("button[data-jeter='Jambon']")
        await pg.fill("#jeter-q", "40")
        await pg.click("button[data-jeter-ok='Jambon']")
        apres = await pg.evaluate(f"stockBrut({j})['Jambon']")
        verif(abs(avant - 40 - apres) < 0.01, f"jambon : {avant} → {apres}, 40 g jetés attendus")
        verif(await pg.evaluate(f"stockBrut({j}, true)['Jambon']") == avant, "le plan d'origine ne voit pas la poubelle")
        verif("À la poubelle" in await pg.inner_text("main"), "carte « À la poubelle » absente")
        await pg.screenshot(path="/tmp/marmite_poubelle.png", full_page=True)

        await pg.click("button[data-perte-suppr='0']")
        verif(await pg.evaluate(f"stockBrut({j})['Jambon']") == avant, "annulation : stock non rétabli")
        verif(await pg.evaluate("E.foyer.pertes.length") == 0, "annulation : perte toujours enregistrée")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("jour", j, "jambon", avant)
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
