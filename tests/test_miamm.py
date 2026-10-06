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
def pdf_texte(lignes):
    """PDF minimal avec du vrai texte (comme le e-ticket d'un magasin), une ligne par entrée."""
    flux = "BT /F1 9 Tf 12 TL 20 560 Td " + " ".join("(%s) '" % l.replace("\\", "").replace("(", "").replace(")", "") for l in lignes) + " ET"
    objets = ["<</Type/Catalog/Pages 2 0 R>>", "<</Type/Pages/Kids[3 0 R]/Count 1>>",
              "<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 600]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>",
              "<</Type/Font/Subtype/Type1/BaseFont/Helvetica/Encoding/WinAnsiEncoding>>",
              "<</Length %d>>stream\n%s\nendstream" % (len(flux.encode("latin-1")), flux)]
    sortie, pos = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objets, 1): pos.append(len(sortie)); sortie += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode("latin-1")
    xref = len(sortie)
    sortie += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1) + "".join("%010d 00000 n \n" % p for p in pos)
               + "trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, xref)).encode("latin-1")
    return bytes(sortie)
TICKET_PDF = ["E.LECLERC SAINT-PIERRE", "06/10/2026 18:42", "FILET POULET 1,2KG 11,83", "RIZ LONG GRAIN 1KG", "2 X 1,49 2,98",
              "COURGETTE", "0,900 kg x 2,49 2,24", "OEUFS PLEIN AIR X12 3,15", "COCA COLA 1,5L 1,89", "ART MYSTERE MAISON 1,00", "TOTAL A PAYER 23,09"]
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
                           "--var", "INVITATION_INITIALE:POPO-TE01", "--var", "ANTHROPIC_API_KEY:cle-de-test", "--var", "LECTURE_CHEF:oui", "--var", f"ANTHROPIC_BASE_URL:http://127.0.0.1:{pf}",
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
            await bb.wait_for_selector("button[data-action=foyer]", timeout=10000)
            await bb.click("button[data-action=foyer]"); await bb.wait_for_selector("nav button[data-vue=jour]")
            r = await bb.evaluate("({ plats: P().plan[0].meals.map(m => m.plat).join('|'), coche: Object.keys(D().suivi.coches).length, pers: D().personnes.length })")
            ra = await a.evaluate("P().plan[0].meals.map(m => m.plat).join('|')")
            verif(r["plats"] == ra and r["coche"] == 1 and r["pers"] == 2, f"le second membre ne voit pas le même foyer : {r}")
            verif(await bb.evaluate("(async () => (await api('/api/inscription/debut', { invitation: '" + code + "', nom: 'X' })).ok)()") is False, "invitation réutilisable")

            # 4. déconnexion puis connexion par la clé d'accès
            await a.click("button[data-action=deconnexion]"); await a.wait_for_selector("button[data-action=connexion]")
            verif(await a.locator("text=Première fois ? J'ai une invitation").count() == 0, "l'invitation est encore proposée en grand sur un appareil déjà connecté")
            await a.click("button[data-action=connexion]")
            # la page principale s'ouvre ; le bouton maison mène au foyer, le logo ramène à la page principale
            await a.wait_for_selector("button[data-action=foyer]", timeout=15000)
            await a.click("button[data-action=foyer]"); await a.wait_for_selector("nav button[data-vue=jour]")
            await a.click("nav button[data-vue=courses]"); await a.click("button[data-action=principale]")
            await a.wait_for_selector("button.hero"); await a.click("button[data-action=foyer]")
            verif(await a.evaluate("S.vue") == "courses", "retour au foyer sans revenir sur l'onglet quitté")
            verif(await a.evaluate("S.compte.nom") == "Nicolas", "connexion par la clé ratée")

            # 5. ticket ajouté aux courses : articles prévus cochés, le reste au stock, prix mis à jour
            await a.click("nav button[data-vue=courses]")
            await a.click("button[data-action=ticket][data-ou=courses]")
            verif(await a.locator("input[data-photo=courses]").count() == 1, "photo par le chef absente alors que le serveur l'autorise")
            await a.set_input_files("input[data-photo=courses]", str(CF / "statique" / "icone-512.png"))
            await a.wait_for_selector("button[data-action=revue-ok]", timeout=15000)
            await a.click("button[data-action=revue-ok]")
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
            # le ticket en PDF (celui qu'envoie le magasin) : lu sur l'appareil, sans appel au chef
            pdf = pathlib.Path(tempfile.mkdtemp()) / "ticket.pdf"
            pdf.write_bytes(pdf_texte(TICKET_PDF))
            avant = len(RECUS)
            verif(await c.locator("input[data-photo][capture]").count() == 0, "le champ du ticket force encore l'appareil photo")
            await c.set_input_files("input[data-pdf=express]", str(pdf))
            await c.wait_for_selector("text=E.Leclerc", timeout=15000)
            verif(not any(ch.startswith("/v1/messages") for ch, h, c2 in RECUS[avant:]), "le PDF a été envoyé au chef (payant)")
            r = await c.evaluate("S.express.lignes.map(l => [l.a, l.q])")
            verif(r[:4] == [["Poulet", 1200], ["Riz (sec)", 2000], ["Courgettes", 900], ["Œufs", 12]] and r[4] == ["", 0] and len(r) == 5, f"lignes du PDF : {r}")
            # correction : la ligne inconnue devient de la citrouille, et c'est retenu pour le foyer
            await c.select_option("select[data-ligne='4']", "Citrouille")
            r = await c.evaluate("({ appris: D().appris[LecteurTicket.cle('ART MYSTERE MAISON')], q: S.express.lignes[4].q })")
            verif(r["appris"] == "Citrouille" and r["q"] > 0, f"correction non retenue : {r}")
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
            await c.click("nav button[data-vue=courses]")
            await c.click("button[data-action=ticket][data-ou=courses]")
            await c.click("button[data-action=coller]")
            await c.fill("#t-texte", "LECLERC\nART MYSTERE MAISON 2KG   1,20\nCHAMPI PARIS 250G   1,59\nLESSIVE 2L   6,90\nTOTAL 9,69")
            avant = len(RECUS)
            await c.click("button[data-action=lire-texte]")
            await c.wait_for_selector("button[data-action=revue-ok]")
            r = await c.evaluate("revue.lignes.map(l => l.a)")
            verif(r == ["Citrouille", "Champignons"], f"texte collé, habitude du foyer : {r}")
            verif(await c.evaluate("document.documentElement.scrollWidth <= innerWidth"), "vérification du ticket déborde à 360 px")
            await c.click("button[data-action=revue-ok]")
            await c.wait_for_selector("text=Ticket ajouté")
            verif(await c.evaluate("stockReel(jourDuPlan())['Citrouille'] > 0"), "ticket collé absent du stock")
            verif(not any(ch.startswith("/v1/messages") for ch, h, c2 in RECUS[avant:]), "le texte collé a été envoyé au chef")
            # photo d'un ticket papier lue sur l'appareil (Tesseract servi par le Worker), sans appel au chef
            pp = await c.context.new_page()
            await pp.set_viewport_size({"width": 480, "height": 440})
            await pp.set_content("<body style='margin:0;padding:24px;background:linear-gradient(120deg,#8a8a8a,#d8d8d8)'><div style='transform:rotate(-2deg);filter:blur(.5px);width:380px;padding:20px;background:#f6f5f0;font:17px monospace;line-height:1.5;white-space:pre'>LECLERC\nSTEAK HACHE 5%% X4      6,49\nOIGNONS JAUNES 1KG      1,79\nLESSIVE 2L              6,90\nPAPAYE                  2,10\nTOTAL A PAYER          17,28</div></body>")
            image = pathlib.Path(tempfile.mkdtemp()) / "ticket.png"
            image.write_bytes(await pp.screenshot()); await pp.close()
            await c.click("nav button[data-vue=courses]")
            await c.click("button[data-action=ticket][data-ou=courses]")
            avant = len(RECUS)
            await c.set_input_files("input[data-ocr=courses]", str(image))
            await c.wait_for_selector("button[data-action=revue-ok]", timeout=60000)
            r = await c.evaluate("revue.lignes.map(l => [l.a, l.prix])")
            verif(["Steak haché", 6.49] in r and ["Oignons", 1.79] in r and not any(a == "" and p == 6.9 for a, p in r), f"photo du ticket lue : {r}")
            verif(not any(ch.startswith("/v1/messages") for ch, h, c2 in RECUS[avant:]), "la photo a été envoyée au chef (payant)")
            await c.click("button[data-action=revue-ok]"); await c.wait_for_selector("text=Ticket ajouté")
            # ajuster un repas dans Aujourd'hui, puis revenir au menu prévu
            await c.click("nav button[data-vue=jour]")
            await c.click("article#r-dej button[data-action=ajuster]")
            await c.click("button[data-action=aj-pas][data-i='0'][data-s='1']")
            await c.click("button[data-action=aj-ok]")
            r = await c.evaluate("({ aj: !!(D().suivi.remplacements[jourDuPlan() + '-dej'] || {}).ajuste, q: repas(jourDuPlan(), 'dej').items[qui()][0][1] - P().plan[jourDuPlan() - 1].meals.find(m => m.k === 'dej').items[qui()][0][1] })")
            verif(r["aj"] and r["q"] > 0, f"repas ajusté : {r}")
            await c.click("article#r-dej button[data-action=ajuster]"); await c.click("button[data-action=aj-plan]")
            verif(await c.evaluate("!D().suivi.remplacements[jourDuPlan() + '-dej']"), "retour au menu prévu raté")
            # stock remis à zéro, puis refait à la main et par un ticket
            await c.click("nav button[data-vue=stock]")
            c.once("dialog", lambda dl: asyncio.ensure_future(dl.accept()))
            await c.click("button[data-action=stock-zero]")
            verif(await c.evaluate("Object.keys(stockMaintenant()).length") == 0, "stock pas remis à zéro")
            await c.select_option("#st-a", "Poulet"); await c.fill("#st-q", "800"); await c.click("button[data-action=stock-ajouter]")
            await c.fill("input[data-stock='Poulet']", "500"); await c.dispatch_event("input[data-stock='Poulet']", "change")
            verif(await c.evaluate("JSON.stringify(stockMaintenant())") == '{"Poulet":500}', "stock refait à la main")
            await c.click("button[data-action=ticket][data-ou=courses]"); await c.click("button[data-action=coller]")
            await c.fill("#t-texte", "RIZ LONG GRAIN 1KG  1,49\nTOTAL 1,49")
            await c.click("button[data-action=lire-texte]"); await c.click("button[data-action=revue-ok]")
            verif(await c.evaluate("stockMaintenant()['Riz (sec)']") == 1000, "ticket après la remise à zéro absent du stock")
            # chrono et pas pendant les courses
            await c.click("nav button[data-vue=courses]")
            await c.click("button[data-action=chrono-go]")
            await c.evaluate("""(async () => { const ev = z => { const e = new Event('devicemotion'); e.accelerationIncludingGravity = { x: 0, y: 0, z }; dispatchEvent(e); };
              for (let i = 0; i < 4; i++) { ev(9.8); ev(13); await new Promise(r => setTimeout(r, 320)); ev(9); } chrono.debut -= 65000; })()""")
            await c.click("button[data-action=chrono-stop]")
            r = await c.evaluate("Object.values(D().suivi.chronos)[0]")
            verif(r and r["pas"] == 4 and r["duree"] >= 65000, f"chrono des courses : {r}")
            verif(await c.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Courses déborde à 360 px avec le chrono")
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
