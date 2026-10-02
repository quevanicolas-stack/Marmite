"""Dépassement du budget : dès que les prix validés font dépasser le budget du foyer, l'app propose
de retirer, de changer des aliments ou d'accepter. Chaque choix s'applique aux repas et à la liste, et s'annule."""
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
        # 1er octobre, jour de la Course 1
        await pg.add_init_script("{ const V = Date; const t = new V(2026, 9, 1, 10).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        await pg.click("#nav-barre button[data-vue='courses']")

        d0 = await pg.evaluate("depassementFoyer()")
        verif(d0["ecart"] < 0, f"octobre prévu sous le budget attendu : écart {d0['ecart']:.2f}")
        verif(await pg.locator(".depasse").count() == 0, "panneau affiché sans dépassement")

        # le poulet coûte bien plus cher que prévu : 22 € le paquet
        await pg.fill("input[data-paye='c1-Poulet']", "44")
        await pg.dispatch_event("input[data-paye='c1-Poulet']", "change")
        d1 = await pg.evaluate("depassementFoyer()")
        verif(d1["ecart"] > 0, f"dépassement attendu après le poulet à 22 € : écart {d1['ecart']:.2f}")
        verif(await pg.locator(".depasse").count() == 1, "panneau de dépassement absent")
        texte = await pg.inner_text(".depasse")
        verif("Retirer" in texte and "Changer des aliments" in texte and "Accepter" in texte, "les trois choix ne sont pas proposés")
        await pg.screenshot(path="/tmp/marmite_depassement.png", full_page=True)

        # changer des aliments : le premier échange proposé
        bouton = pg.locator("button[data-modif='echange']").first
        a, bb, cid = await bouton.get_attribute("data-a"), await bouton.get_attribute("data-b"), int(await bouton.get_attribute("data-cid"))
        await bouton.click()
        j = await pg.evaluate("jourActuel()")
        verif(await pg.evaluate("E.foyer.modifs.length") == 1, "échange non enregistré")
        items = await pg.evaluate(f"itemsCourse(DONNEES.courses.find(c => c.id === {cid})).map(i => i.a)")
        verif(a not in items and bb in items, f"liste : {a} → {bb} non appliqué ({items})")
        # les repas de la période n'ont plus l'aliment retiré, pour les deux personnes
        reste = await pg.evaluate(f"""(() => {{ const c = DONNEES.courses.find(x => x.id === {cid}); let n = 0;
            for (let d = Math.max(c.jourPlan, jourActuel()); d <= finPeriode(c); d++) for (const k of CLES) for (const p of ['nicolas', 'aurelie'])
              if (repasDe(d, k, p).items.some(([x]) => x === {a!r})) n++; return n; }})()""")
        verif(reste == 0, f"{reste} repas contiennent encore {a}")
        d2 = await pg.evaluate("depassementFoyer()")
        verif(d2["conso"] < d1["conso"], f"l'échange n'a pas réduit la consommation prévue : {d1['conso']:.2f} → {d2['conso']:.2f}")

        # annuler : repas et liste reviennent
        await pg.click("button[data-modif-annuler='0']")
        verif(await pg.evaluate("E.foyer.modifs.length") == 0, "annulation : échange toujours enregistré")
        verif(abs(await pg.evaluate("depassementFoyer().conso") - d1["conso"]) < 0.01, "annulation : consommation non rétablie")
        items = await pg.evaluate(f"itemsCourse(DONNEES.courses.find(c => c.id === {cid})).map(i => i.a)")
        verif(a in items, "annulation : ligne non rétablie")

        # retirer : la ligne disparaît de la liste
        if await pg.locator("button[data-modif='retrait']").count():
            r = pg.locator("button[data-modif='retrait']").first
            ar, cr = await r.get_attribute("data-a"), int(await r.get_attribute("data-cid"))
            await r.click()
            items = await pg.evaluate(f"itemsCourse(DONNEES.courses.find(c => c.id === {cr})).map(i => i.a)")
            verif(ar not in items, f"retrait de {ar} non appliqué")
            await pg.click("button[data-modif-annuler='0']")

        # accepter : le panneau des choix disparaît tant que le dépassement ne grandit pas
        await pg.click("button[data-accepter]")
        verif(await pg.locator("button[data-modif]").count() == 0, "choix toujours proposés après acceptation")
        await pg.fill("input[data-paye='c1-Poulet']", "60")
        await pg.dispatch_event("input[data-paye='c1-Poulet']", "change")
        verif(await pg.locator("button[data-modif]").count() > 0, "nouveau dépassement : choix non reproposés")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "la page déborde")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("écart initial", round(d0["ecart"], 2), "après poulet", round(d1["ecart"], 2), "échange", a, "→", bb)
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
