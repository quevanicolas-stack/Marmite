"""Ticket du 1er octobre reporté une fois dans la Course 1 (quantités, prix payés, produits hors liste), annulable.
Valider le panier : pas coché = pas acheté (budget, stock prévu), puis refaire le planning selon les achats.
Ajouter un produit à une course (catalogue ou nouveau produit) et un achat spontané au stock."""
import asyncio, json, pathlib, sys
RACINE = pathlib.Path(__file__).resolve().parent.parent
PAGE = (RACINE / "app" / "marmite.html").as_uri()
TICKET = json.load(open(RACINE / "donnees" / "tickets" / "2026-10-01-leclerc.json", encoding="utf-8"))
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
        # vendredi 2 octobre au matin, lendemain des courses
        await pg.add_init_script("{ const V = Date; const t = new V(2026, 9, 2, 9).getTime(); Date = class extends V { constructor(...a) { super(...(a.length ? a : [t])); } static now() { return t; } }; }")
        await pg.goto(PAGE); await pg.wait_for_timeout(300)

        # 1. le ticket est reporté tout seul dans la Course 1
        r = await pg.evaluate("""(() => { const c = COURSES()[0], it = itemsCourse(c), b = bilanCourse(1);
          return { imp: !!E.foyer.imports['leclerc-2026-10-01'], faits: b.faits, total: b.total, paye: Math.round(b.paye * 100) / 100,
                   non: it.filter(x => !E.foyer.achats[cleLigne(1, x)]).map(x => x.a).sort(),
                   ajouts: it.filter(x => x.ajout).map(x => x.a).sort(),
                   jambon: it.find(x => x.a === 'Jambon').buy, poulet: E.foyer.prix['Poulet'].prix, prixJambon: E.foyer.prix['Jambon'].prix,
                   bacon: !!DONNEES.cat['Bacon'] }; })()""")
        verif(r["imp"], "ticket non reporté")
        verif(r["faits"] == len(TICKET["lignes"]), f"{r['faits']} lignes cochées, {len(TICKET['lignes'])} attendues")
        verif(abs(r["paye"] - TICKET["totalImporte"]) < 0.01, f"payé {r['paye']} au lieu de {TICKET['totalImporte']}")
        verif(r["non"] == sorted(["Flocons d'avoine", "Pain complet", "Salade", "Sauce soja", "Concentré de tomate", "Ail, gingembre, curcuma"]), f"non achetés : {r['non']}")
        verif(r["ajouts"] == ["Bacon", "Farine", "Huile"], f"produits hors liste : {r['ajouts']}")
        verif(r["jambon"] == 246 and r["prixJambon"] == 17.44, f"jambon : {r['jambon']} g à {r['prixJambon']} €/kg")
        verif(r["poulet"] == 11.83, f"prix du poulet {r['poulet']} (le filet, pas la moyenne avec les pilons)")
        await pg.click("#nav-barre button[data-vue='courses']")
        verif("Ticket E.Leclerc" in await pg.inner_text("main"), "bandeau du ticket absent")
        # reporté une seule fois : décocher puis recharger ne le réapplique pas
        await pg.reload(); await pg.wait_for_timeout(300)
        verif(await pg.evaluate("bilanCourse(1).faits") == len(TICKET["lignes"]), "le ticket a été reporté deux fois ou perdu au rechargement")

        # 2. valider le panier
        await pg.click("#nav-barre button[data-vue='courses']")
        avant = await pg.evaluate("bilanCourse(1).avenir")
        verif(avant > 0, "rien à acheter avant validation")
        await pg.click("button[data-panier-valider='1']")
        verif("Flocons d'avoine" in await pg.inner_text(".valider-panier"), "la confirmation ne liste pas les non-achetés")
        await pg.click("button[data-panier-ok='1']")
        r = await pg.evaluate("({ val: valide(1), avenir: bilanCourse(1).avenir, est: Math.round(bilanCourse(1).est * 100) / 100, pain: stockBrut(3)['Pain complet'] || 0 })")
        verif(r["val"] and r["avenir"] == 0, f"panier validé : reste à acheter {r['avenir']}")
        verif(abs(r["est"] - TICKET["totalImporte"]) < 0.01, f"coût de la course {r['est']} après validation")
        verif(r["pain"] <= 0, "le pain complet non acheté compte encore dans le stock prévu")
        texte = await pg.inner_text("main")
        verif("Panier validé" in texte and "pas acheté" in texte, "panier validé : bandeau ou étiquettes absents")
        # puis refaire le planning selon les achats
        await pg.click("button[data-replanifier]")
        r = await pg.evaluate("({ vue, mode: gen && gen.mode, j0: gen && gen.j0, gardees: gen && gen.res && gen.res.gardees })")
        verif(r["vue"] == "planning" and r["mode"] == "stock" and r["j0"] == 2 and 1 in (r["gardees"] or []), f"planning selon les achats : {r}")

        # 3. ajouter un produit du catalogue à la Course 2, puis un nouveau produit
        await pg.click("#nav-barre button[data-vue='courses']")
        await pg.click("button.puce[data-course='2']")
        await pg.click("button[data-ajout-ouvrir='liste']")
        await pg.fill("#ajout-q", "chori"); await pg.dispatch_event("#ajout-q", "input")
        await pg.click("button[data-ajout-choisir='Chorizo']")
        await pg.fill("#ajout-qte", "2")
        await pg.click("button[data-ajout-ok]")
        verif(await pg.evaluate("itemsCourse(COURSES()[1]).some(x => x.a === 'Chorizo' && x.ajout && x.buy === 2)"), "Chorizo non ajouté à la Course 2")
        await pg.click("button[data-ajout-ouvrir='liste']")
        await pg.fill("#ajout-q", "Fromage blanc"); await pg.dispatch_event("#ajout-q", "input")
        await pg.click("button[data-ajout-nouveau]")
        verif(await pg.locator("#np-nom").input_value() == "Fromage blanc", "le nom cherché n'est pas repris")
        verif(await pg.evaluate("[...document.querySelectorAll('.feuille-ia input, .feuille-ia select')].every(e => e.getBoundingClientRect().right <= innerWidth)"), "le formulaire du nouveau produit sort de l'écran")
        await pg.select_option("#np-rayon", "Œufs et laitages")
        await pg.fill("#np-cond", "200"); await pg.fill("#np-prix", "1.65"); await pg.fill("#np-kcal", "290"); await pg.fill("#np-prot", "2.4")
        await pg.click("button[data-ajout-creer]")
        await pg.click("button[data-ajout-ok]")
        r = await pg.evaluate("({ cat: DONNEES.cat['Fromage blanc'], nut: DONNEES.nut['Fromage blanc'], ligne: itemsCourse(COURSES()[1]).some(x => x.a === 'Fromage blanc'), garde: !!E.foyer.produits['Fromage blanc'] })")
        verif(r["cat"] and r["cat"]["cond"] == 200 and r["cat"]["prix"] == 1.65 and r["nut"] == [100, "g", 290, 2.4], f"nouveau produit mal créé : {r}")
        verif(r["ligne"] and r["garde"], "nouveau produit absent de la liste ou non enregistré")
        # un produit déjà prévu n'est pas doublé
        prevus = await pg.evaluate("itemsCourse(COURSES()[1]).filter(x => x.a === 'Poulet').length")
        await pg.click("button[data-ajout-ouvrir='liste']")
        await pg.fill("#ajout-q", "poulet"); await pg.dispatch_event("#ajout-q", "input")
        await pg.click("button[data-ajout-choisir='Poulet']"); await pg.click("button[data-ajout-ok]")
        verif(await pg.evaluate("itemsCourse(COURSES()[1]).filter(x => x.a === 'Poulet').length") == prevus, "produit déjà prévu ajouté en double")
        # retirer un produit ajouté
        n = await pg.evaluate("itemsCourse(COURSES()[1]).length")
        await pg.locator(".article.mag", has_text="Chorizo").locator(".nom").click()
        await pg.click(".article.mag.ouvert button[data-ajout-suppr]")
        verif(await pg.evaluate("itemsCourse(COURSES()[1]).length") == n - 1, "le produit ajouté ne se retire pas")

        # 4. achat spontané au stock (À la maison)
        await pg.click("button[data-course='stock']")
        oeufs = await pg.evaluate("stockReel(2)['Œufs'] || 0")
        paye = await pg.evaluate("bilanCourse(1).paye")
        await pg.click("button[data-ajout-ouvrir='achat']")
        await pg.fill("#ajout-q", "œufs"); await pg.dispatch_event("#ajout-q", "input")
        await pg.click("button[data-ajout-choisir='Œufs']")
        await pg.fill("#ajout-qte", "1"); await pg.fill("#ajout-prix", "3.9")
        await pg.click("button[data-ajout-ok]")
        r = await pg.evaluate(f"({{ oeufs: stockReel(2)['Œufs'], paye: bilanCourse(1).paye }})")
        verif(abs(r["oeufs"] - oeufs - 12) < 0.01, f"achat spontané : œufs {oeufs} → {r['oeufs']}")
        verif(abs(r["paye"] - paye - 3.9) < 0.01, "achat spontané absent du budget")
        verif("Achats hors liste" in await pg.inner_text("main"), "carte des achats hors liste absente")
        verif(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "la page déborde")

        # 5. annuler le report du ticket rétablit la liste d'avant
        await pg.evaluate("delete E.foyer.validees[1]; rendre();")
        await pg.evaluate("courseSel = 1; rendre();")
        await pg.click("button[data-ticket-annuler]")
        r = await pg.evaluate("""({ faits: itemsCourse(COURSES()[0]).filter(x => !x.spontane && E.foyer.achats[cleLigne(1, x)]).length,
          ajouts: itemsCourse(COURSES()[0]).filter(x => x.ajout && !x.spontane).length, imp: E.foyer.imports['leclerc-2026-10-01'],
          oeufs: itemsCourse(COURSES()[0]).some(x => x.spontane && x.a === 'Œufs'), creme: itemsCourse(COURSES()[1]).some(x => x.a === 'Fromage blanc'),
          prix: E.foyer.prix['Jambon'] || null })""")
        verif(r["faits"] == 0 and r["ajouts"] == 0 and r["imp"].get("annule"), f"annulation du ticket incomplète : {r}")
        verif(r["oeufs"] and r["creme"], "annuler le ticket a effacé les achats faits depuis")
        verif(r["prix"] is None, "le prix du jambon venu du ticket n'est pas rétabli")
        verif(not errs, f"erreurs de page : {errs}")
        await b.close()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
