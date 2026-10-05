"""Miamm sur Cloudflare, testé en local avec « wrangler dev » et une clé d'accès simulée (authentificateur virtuel
de Chromium) : invitation, compte, code de secours, menu sur mesure, second membre du foyer invité qui voit le même
menu, déconnexion puis connexion par la clé, ticket lu par le chef (API simulée) en mode Express, ticket ajouté aux
courses, rappels par foyer. Passe sans rien faire si cloudflare/node_modules est absent (npm install)."""
import asyncio, base64, json, os, pathlib, socket, subprocess, sys, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
RACINE = pathlib.Path(__file__).resolve().parent.parent
CF = RACINE / "cloudflare"
if not (CF / "node_modules" / "wrangler").exists():
    print("cloudflare/node_modules absent : test sauté (cd cloudflare && npm install)"); sys.exit(0)
from playwright.async_api import async_playwright

def port_libre():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

RECUS = []
TICKET = {"magasin": "E.Leclerc Saint-Pierre", "date": "2026-10-05", "total": 41.9, "lignes": [
    {"libelle": "FILET POULET X4", "aliment": "Poulet", "nombre": 1, "poids_g": 1200, "prix": 14.2, "alimentaire": True},
    {"libelle": "RIZ LONG 1KG", "aliment": "Riz (sec)", "nombre": 2, "poids_g": 0, "prix": 3.8, "alimentaire": True},
    {"libelle": "COURGETTES VRAC", "aliment": "Courgettes", "nombre": 1, "poids_g": 900, "prix": 3.1, "alimentaire": True},
    {"libelle": "OEUFS PLEIN AIR X12", "aliment": "Œufs", "nombre": 1, "poids_g": 0, "prix": 4.2, "alimentaire": True},
    {"libelle": "COCA 1,5L", "aliment": "", "nombre": 1, "poids_g": 0, "prix": 2.1, "alimentaire": False},
    {"libelle": "PATE FEUILLETEE", "aliment": "", "nombre": 1, "poids_g": 0, "prix": 1.5, "alimentaire": True}]}
class Faux(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0); corps = self.rfile.read(n) if n else b""
        RECUS.append((self.path, dict(self.headers), corps))
        if self.path.startswith("/v1/messages"):
            c2 = corps.replace(b" ", b"")
            image = b'"type":"image"' in c2 or b'"type":"document"' in c2
            texte = json.dumps(TICKET if image else {"plats": []})
            rep = {"id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "stop_reason": "end_turn",
                   "content": [{"type": "text", "text": texte}], "usage": {"input_tokens": 1, "output_tokens": 1}}
            b = json.dumps(rep).encode(); self.send_response(200); self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        self.send_response(410 if "parti" in self.path else 201); self.send_header("content-length", "0"); self.end_headers()

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    faux = ThreadingHTTPServer(("127.0.0.1", port_libre()), Faux); threading.Thread(target=faux.serve_forever, daemon=True).start()
    pf = faux.server_address[1]
    subprocess.run([sys.executable, str(CF / "preparer.py")], check=True, capture_output=True)
    pw = port_libre(); base = f"http://localhost:{pw}"   # une clé d'accès exige un nom de domaine (pas une adresse IP)
    env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
    wr = subprocess.Popen(["npx", "wrangler", "dev", "--ip", "127.0.0.1", "--port", str(pw), "--test-scheduled", "--persist-to", tempfile.mkdtemp(prefix="miamm-"),
                           "--var", "INVITATION_INITIALE:POPO-TE01", "--var", "ANTHROPIC_API_KEY:cle-de-test", "--var", f"ANTHROPIC_BASE_URL:http://127.0.0.1:{pf}",
                           "--show-interactive-dev-session=false"], cwd=CF, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(base + "/api/etat", timeout=2) as x: etat = json.loads(x.read()); break
            except Exception: time.sleep(0.5)
        else:
            wr.kill(); print(wr.stdout.read()[-3000:]); sys.exit("wrangler dev ne répond pas")
        verif(etat.get("miamm") and etat.get("compte") is None, f"/api/etat : {etat}")

        async with async_playwright() as p:
            b = await p.chromium.launch()
            async def telephone():
                ctx = await b.new_context(viewport={"width": 360, "height": 780}, service_workers="block")
                pg = await ctx.new_page(); errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and errs.append(m.text))   # refus attendus (400, polices bloquées)
                await pg.route("**/fonts.g*/**", lambda r: r.abort())
                cdp = await ctx.new_cdp_session(pg)
                await cdp.send("WebAuthn.enable")
                await cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {"protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
                    "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}})
                await pg.goto(base + "/"); await pg.wait_for_selector("text=J'ai une invitation")
                return pg, errs
            async def inscrire(pg, code, nom):
                await pg.click("text=J'ai une invitation")
                await pg.fill("#i-code", code); await pg.fill("#i-nom", nom)
                await pg.click("form[data-form=inscription] button[type=submit]")
                await pg.wait_for_selector("#code-secours", timeout=15000)
                secours = await pg.inner_text("#code-secours")
                await pg.click("button[data-action=secours-ok]")
                return secours

            # 1. Nicolas : invitation initiale, clé d'accès, code de secours
            a, errs_a = await telephone()
            verif(await a.evaluate("document.documentElement.scrollWidth <= innerWidth"), "l'accueil déborde à 360 px")
            await a.click("text=J'ai une invitation"); await a.fill("#i-code", "FAUX-CODE"); await a.fill("#i-nom", "Nico")
            await a.click("form[data-form=inscription] button[type=submit]"); await a.wait_for_selector("text=Invitation inconnue ou déjà utilisée.")
            await a.click("button[data-ecran=accueil]")
            secours = await inscrire(a, "popo-te01", "Nicolas")
            verif(len(secours) == 19 and secours.count("-") == 3, f"code de secours : {secours}")
            await a.wait_for_selector("text=Salut Nicolas !")

            # 2. menu sur mesure pour deux
            await a.click("text=Sur mesure")
            for nom, sexe, age, taille, poids, cible in [("Nicolas", "h", 38, 180, 85, 80), ("Aurélie", "f", 31, 160, 70, 60)]:
                await a.click("button[data-action=personne-ajouter]")
                await a.fill("#p-nom", nom); await a.select_option("#p-sexe", sexe); await a.fill("#p-age", str(age)); await a.fill("#p-taille", str(taille))
                await a.fill("#p-poids", str(poids)); await a.fill("#p-cible", str(cible))
                await a.click("form[data-form=personne] button[type=submit]")
            await a.fill("#g-budget", "500")
            await a.click("button[data-action=composer-mesure]")
            r = await a.evaluate("({ n: S.proposition.periode.jours, achats: S.proposition.bilan.cout.achats, budget: S.proposition.bilan.cout.budget, c1: S.proposition.periode.courses[0].date === S.proposition.periode.debut, kcal: S.proposition.bilan.nutrition[D().personnes[0].id].kcalMoyen })")
            verif(r["n"] == 7 and r["c1"] and 1800 < r["kcal"] < 2100 and r["achats"] <= r["budget"] * 1.15, f"proposition sur mesure : {r}")
            await a.click("button[data-action=valider]")
            await a.wait_for_selector("nav button[data-vue=jour]")
            await a.wait_for_function("S.rev >= 1 && !S.envoi", timeout=10000)
            await a.click("button[data-action=cocher] >> nth=0")
            await a.wait_for_timeout(1200)

            # 3. invitation dans le foyer : Aurélie s'inscrit et voit le même menu
            await a.click("nav button[data-vue=foyer]"); await a.click("button[data-action=inviter][data-type=foyer]")
            code = (await a.inner_text("#invitation .secours")).strip()
            bb, errs_b = await telephone()
            await inscrire(bb, code, "Aurélie")
            await bb.wait_for_selector("nav button[data-vue=jour]", timeout=10000)
            r = await bb.evaluate("({ plats: P().plan[0].meals.map(m => m.plat).join('|'), coche: Object.keys(D().suivi.coches).length, pers: D().personnes.length })")
            ra = await a.evaluate("P().plan[0].meals.map(m => m.plat).join('|')")
            verif(r["plats"] == ra and r["coche"] == 1 and r["pers"] == 2, f"le second membre ne voit pas le même foyer : {r}")
            verif(await bb.evaluate("(async () => (await api('/api/inscription/debut', { invitation: '" + code + "', nom: 'X' })).ok)()") is False, "invitation réutilisable")

            # 4. déconnexion puis connexion par la clé d'accès
            await a.click("button[data-action=deconnexion]"); await a.wait_for_selector("button[data-action=connexion]")
            verif(await a.locator("text=Première fois ? J'ai une invitation").count() == 0, "l'invitation est encore proposée en grand sur un appareil déjà connecté")
            await a.click("button[data-action=connexion]")
            await a.wait_for_selector("nav button[data-vue=jour]", timeout=15000)
            verif(await a.evaluate("S.compte.nom") == "Nicolas", "connexion par la clé ratée")

            # 5. ticket ajouté aux courses : articles prévus cochés, le reste au stock, prix mis à jour
            await a.click("nav button[data-vue=courses]")
            await a.set_input_files("input[data-photo=courses]", str(CF / "statique" / "icone-512.png"))
            await a.wait_for_selector("text=Ticket ajouté", timeout=15000)
            r = await a.evaluate("({ coches: Object.keys(D().suivi.achats).length, prix: D().prix['Poulet'] && D().prix['Poulet'].prix, ajouts: D().ajouts.length })")
            verif(r["coches"] + r["ajouts"] == 4 and abs(r["prix"] - 11.83) < 0.01, f"ticket dans les courses : {r}")
            appel = next((json.loads(c) for chemin, h, c in RECUS if chemin.startswith("/v1/messages")), None)
            verif(appel and appel["model"] == "claude-opus-5-5" and appel["messages"][0]["content"][0]["type"] == "image" and appel["output_config"]["format"]["type"] == "json_schema", "appel de lecture du ticket")

            # 6. Express sur un troisième compte (un proche, son propre foyer)
            await a.click("nav button[data-vue=foyer]"); await a.click("button[data-action=inviter][data-type=proche]")
            code2 = (await a.inner_text("#invitation .secours")).strip()
            c, errs_c = await telephone()
            await inscrire(c, code2, "Léa")
            await c.click("button[data-action=express]")
            # le ticket en PDF (celui qu'envoie le magasin), pas en photo
            pdf = pathlib.Path(tempfile.mkdtemp()) / "ticket.pdf"
            pdf.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 400]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
            avant = len(RECUS)
            await c.set_input_files("input[data-photo=express]", str(pdf))
            await c.wait_for_selector("text=E.Leclerc Saint-Pierre", timeout=15000)
            appel = next((json.loads(c2) for chemin, h, c2 in RECUS[avant:] if chemin.startswith("/v1/messages")), None)
            piece = appel and appel["messages"][0]["content"][0]
            verif(piece and piece["type"] == "document" and piece["source"]["media_type"] == "application/pdf", f"ticket PDF envoyé comme document : {piece and piece['type']}")
            verif(await c.locator("input[data-photo][capture]").count() == 0, "le champ du ticket force encore l'appareil photo (pas de PDF possible)")
            r = await c.evaluate("S.express.lignes.map(l => [l.a, l.q])")
            verif(r == [["Poulet", 1200], ["Riz (sec)", 2000], ["Courgettes", 900], ["Œufs", 12], ["", 0]], f"lignes du ticket : {r}")
            await c.click("button[data-action=plus][data-cle=enfants]")
            await c.click("button[data-action=moins][data-cle=jours]"); await c.click("button[data-action=moins][data-cle=jours]")
            verif(await c.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Express déborde à 360 px")
            await c.click("button[data-action=composer-express]")
            r = await c.evaluate("({ n: S.proposition.periode.jours, pers: S.proposition.periode.personnes.length, utilises: S.proposition.bilan.stockUtilise.length })")
            verif(r["n"] == 5 and r["pers"] == 3 and r["utilises"] >= 3, f"proposition express : {r}")
            await c.click("button[data-action=valider]"); await c.wait_for_selector("nav button[data-vue=jour]")
            await c.wait_for_function("S.rev >= 1 && !S.envoi", timeout=10000)
            verif(await c.evaluate("P().plan[0].meals.length") >= 3, "menu express vide")
            r = await c.evaluate("statsJour(jourDuPlan(), qui())")
            verif(r["kcal"] > 500, f"Aujourd'hui sans calories : {r}")
            # un menu express composé pour d'autres convives que le foyer : les portions restent lisibles
            r = await c.evaluate("(() => { D().personnes = [Object.assign(PERSONNE0(), { id: 'pX', nom: 'Léa', age: 30 })]; delete P().profils; rendre(); return { qui: qui(), kcal: statsJour(jourDuPlan(), qui()).kcal }; })()")
            verif(r["qui"] == "a1" and r["kcal"] > 500, f"portions introuvables quand le foyer diffère du menu : {r}")
            # refaire le menu avec ce qu'il y a à la maison
            await c.click("nav button[data-vue=stock]")
            await c.click("button[data-action=refaire-stock]")
            r = await c.evaluate("({ mode: S.proposition.mode, debut: S.proposition.periode.debut, utilises: S.proposition.bilan.stockUtilise.length })")
            verif(r["mode"] == "stock" and r["utilises"] >= 2, f"menu refait avec le stock : {r}")
            await c.click("button[data-action=valider]"); await c.wait_for_selector("nav button[data-vue=jour]")
            verif(await c.evaluate("P().profils.length === P().personnes.length && statsJour(jourDuPlan(), qui()).kcal > 500"), "menu refait sans profils ou sans calories")
            verif(await a.evaluate("(async () => (await api('/api/foyer')).d.doc.mode)()") == "mesure", "le foyer de Nicolas a été touché par celui de Léa")

            # 7. rappels du foyer de Nicolas envoyés par le cron
            jour = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 4 * 3600))
            await a.evaluate(f"api('/api/rappels', {{ rappels: [{{ date: '{jour}', titre: 'Courses demain', texte: 'Course 2' }}] }}, 'PUT')")
            await a.evaluate(f"api('/api/abonnement', {{ abonnement: {{ endpoint: 'http://127.0.0.1:{pf}/push/nico', keys: {{}} }} }})")
            await c.evaluate(f"api('/api/abonnement', {{ abonnement: {{ endpoint: 'http://127.0.0.1:{pf}/push/lea', keys: {{}} }} }})")
            RECUS.clear()
            urllib.request.urlopen(base + "/__scheduled?cron=0+14+*+*+*", timeout=20).read()
            for _ in range(40):
                if any(x[0] == "/push/nico" for x in RECUS): break
                time.sleep(0.25)
            time.sleep(0.5)
            pushs = [x[0] for x in RECUS if x[0].startswith("/push/")]
            verif(pushs == ["/push/nico"], f"rappels envoyés : {pushs}")
            auth = {k.lower(): v for k, v in dict(next((h for ch, h, _ in RECUS if ch == "/push/nico"), {})).items()}.get("authorization", "")
            verif(auth.startswith("vapid t="), "rappel sans signature VAPID")
            verif(await a.evaluate("(async () => (await (await fetch('/api/rappel')).json()).titre)()") == "Courses demain", "texte du rappel absent")

            for nom, pg in (("Nicolas", a), ("Aurélie", bb), ("Léa", c)):
                for v in ("jour", "menu", "courses", "stock", "foyer"):
                    await pg.click(f"nav button[data-vue={v}]")
                    if not await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"): erreurs.append(f"{nom} : la vue {v} déborde à 360 px")
            texte = await a.inner_text("body") + await c.inner_text("body")
            verif("Claude" not in texte, "l'app parle de Claude")
            verif(not errs_a and not errs_b and not errs_c, f"erreurs de page : {errs_a + errs_b + errs_c}")
            await b.close()
    finally:
        wr.terminate()
        try: wr.wait(10)
        except Exception: wr.kill()
        faux.shutdown()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
