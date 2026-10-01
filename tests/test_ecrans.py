"""Aujourd'hui : bilan en bande collante, repas du moment en haut puis « J'ai faim », repas faits repliés, aucun prix.
Courses : mode magasin (par défaut) épuré, la case coche, le reste de la ligne ouvre le détail.
Ajuster : rien ne déborde à 360 px."""
import asyncio, pathlib, sys
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
from playwright.async_api import async_playwright

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 360, "height": 780}, device_scale_factor=2)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        # samedi 3 octobre, 12 h 30 : le déjeuner est le repas du moment
        await pg.add_init_script("{ const V = Date; const t = new V(2026, 9, 3, 12, 30).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)

        # ordre : déjeuner (maintenant), « J'ai faim », puis les autres repas
        ordre = await pg.evaluate("[...document.querySelectorAll('.repas-jour > *')].map(e => e.id || e.dataset.ia)")
        verif(ordre[:2] == ["t-dej", "faim"], f"ordre des fiches : {ordre}")
        verif("maintenant" in (await pg.inner_text("#t-dej")).lower(), "pastille « Maintenant » absente")
        # aucun prix sur l'écran du jour
        verif("€" not in await pg.inner_text("main"), "un prix est encore affiché sur Aujourd'hui")
        # bilan : bande collante, toujours visible après défilement
        await pg.evaluate("window.scrollTo(0, 900)"); await pg.wait_for_timeout(100)
        haut = await pg.evaluate("document.querySelector('.bilan-mini').getBoundingClientRect().top")
        verif(0 <= haut < 5, f"le bilan ne reste pas en haut au défilement ({haut})")
        await pg.evaluate("window.scrollTo(0, 0)")
        await pg.click(".bilan-tete")
        verif("Objectif" in await pg.inner_text(".bilan-mini"), "le bilan ne s'ouvre pas au toucher")

        # un repas fait se replie et passe en bas ; le dîner devient le repas du moment
        await pg.click("#t-dej button[data-coche]")
        verif(await pg.locator("#t-dej.replie").count() == 1, "le déjeuner fait n'est pas replié")
        ordre = await pg.evaluate("[...document.querySelectorAll('.repas-jour > *')].map(e => e.id || e.dataset.ia)")
        verif(ordre[0] == "t-din" and ordre[-1] == "t-dej", f"ordre après le déjeuner : {ordre}")
        verif(await pg.evaluate("statsJour(3).kcalFait > 0 && document.querySelector('.bilan-val b').textContent !== '0'"), "le bilan ne compte pas le repas fait")
        await pg.click("#t-dej .replie-tete")
        verif(await pg.locator("#t-dej button[data-coche][aria-pressed='true']").count() == 1, "le repas fait ne se déplie pas")

        # Ajuster : pas de débordement à 360 px
        await pg.click("#t-din button[data-ed='ouvrir']")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Ajuster déborde à 360 px")
        verif(await pg.evaluate("document.querySelector('#t-din').getBoundingClientRect().right <= innerWidth"), "la fiche Ajuster sort de l'écran")
        verif("€" not in await pg.inner_text("#ed-infos"), "prix affiché dans Ajuster")
        await pg.click("button[data-ed='annuler']")

        # Courses : mode magasin par défaut
        await pg.click("#nav-barre button[data-vue='courses']")
        verif(await pg.locator(".article.mag").count() > 0, "le mode magasin n'est pas actif par défaut")
        verif(await pg.locator(".article input").count() == 0, "des champs sont visibles en mode magasin")
        # toucher le nom ouvre le détail sans cocher
        await pg.locator(".article.mag .nom").nth(1).click()
        verif(await pg.locator(".article.mag.ouvert input[data-paye]").count() == 1, "le détail ne s'ouvre pas au toucher")
        verif(await pg.locator(".article.mag button.check").nth(1).get_attribute("aria-pressed") == "false", "toucher le nom a coché l'article")
        # taper dans le champ de prix ne referme pas le détail ; le prix coche l'article
        cle = await pg.locator(".article.mag.ouvert input[data-paye]").get_attribute("data-paye")
        await pg.locator(".article.mag.ouvert input[data-paye]").click()
        verif(await pg.locator(".article.mag.ouvert").count() == 1, "toucher le champ referme le détail")
        await pg.fill(f"input[data-paye='{cle}']", "4.2"); await pg.dispatch_event(f"input[data-paye='{cle}']", "change")
        verif(await pg.evaluate(f"!!E.foyer.achats['{cle}'] && E.foyer.payes['{cle}'] === 4.2"), "le prix payé n'est pas enregistré")
        # la case coche
        await pg.locator(".article.mag button.check").nth(0).click()
        verif(await pg.locator(".article.mag button.check").nth(0).get_attribute("aria-pressed") == "true", "la case ne coche pas")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Courses déborde à 360 px")
        # retour au mode détaillé, mémorisé
        await pg.click("button[data-mode-courses]")
        verif(await pg.locator(".article input[data-paye]").count() > 3, "le mode détaillé ne revient pas")
        verif(await pg.evaluate("localStorage.getItem('marmite-courses')") == "detail", "le mode n'est pas mémorisé")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
