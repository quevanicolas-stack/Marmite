"""Ordinateur : bibliothèque à droite de la proposition du mois ; glisser un plat sur un repas le remplace
(un dessert seulement sur un dessert). Bouton « Plein écran » dans le rail pour masquer la barre de claude.ai."""
import asyncio, pathlib, sys
PAGE = (pathlib.Path(__file__).resolve().parent.parent / "app" / "marmite.html").as_uri()
from playwright.async_api import async_playwright

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1280, "height": 900})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/fonts.g*/**", lambda r: r.abort())
        await pg.add_init_script("try { localStorage.setItem('marmite-tickets', 'manuel'); } catch (e) {}")   # ticket non reporté (testé dans test_achats.py)
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        verif(await pg.locator("#theme-rail button[data-action='plein-ecran']").count() == 1, "bouton Plein écran absent du rail")
        await pg.click("#nav-rail button[data-vue='planning']")
        await pg.click("button[data-generer='mois']")
        verif(await pg.locator(".biblio").is_visible(), "bibliothèque non affichée sur ordinateur")
        await pg.fill("#biblio-q", "cassoulet"); await pg.dispatch_event("#biblio-q", "input")
        verif(await pg.locator(".biblio-plat").count() == 1, "recherche dans la bibliothèque")
        avant = await pg.evaluate("Moteur.grilleDuMois(gen.res.mois)")
        await pg.drag_and_drop(".biblio-plat[data-drag-id='cassoulet-pommes-de-terre']", "button[data-changer='7-din']")
        apres = await pg.evaluate("Moteur.grilleDuMois(gen.res.mois)")
        verif(apres["7-din"] == "cassoulet-pommes-de-terre", f"glisser : dîner du 7 = {apres['7-din']}")
        verif(all(apres[c] == v for c, v in avant.items() if c != "7-din"), "d'autres repas ont changé")
        # un plat sur un dessert : refusé
        await pg.drag_and_drop(".biblio-plat[data-drag-id='cassoulet-pommes-de-terre']", "button[data-changer='8-des']")
        verif(await pg.evaluate("Moteur.grilleDuMois(gen.res.mois)['8-des']") == apres["8-des"], "un plat a remplacé un dessert")
        await pg.click("button[data-biblio-filtre='dessert']")
        await pg.fill("#biblio-q", ""); await pg.dispatch_event("#biblio-q", "input")
        await pg.drag_and_drop(".biblio-plat[data-drag-id='mangue']", "button[data-changer='8-des']")
        verif(await pg.evaluate("Moteur.grilleDuMois(gen.res.mois)['8-des']") == "mangue", "dessert non remplacé par glisser")
        await pg.screenshot(path="/tmp/marmite_glisser.png")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "la page déborde")
        # sur téléphone, pas de bibliothèque latérale ni de bouton plein écran dans la barre du haut
        await pg.set_viewport_size({"width": 390, "height": 844})
        verif(not await pg.locator(".biblio").is_visible(), "bibliothèque affichée sur téléphone")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)
asyncio.run(main())
