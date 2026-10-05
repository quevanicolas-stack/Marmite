"""Version Cloudflare, testée en local avec « wrangler dev » : code du foyer, un seul document pour deux téléphones
(révision et fusion quand les deux enregistrent), le chef (API simulée), les rappels (Web Push simulé, cron),
copier / importer les données. Passe sans rien faire si cloudflare/node_modules est absent (npm install)."""
import asyncio, base64, json, os, pathlib, socket, subprocess, sys, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
RACINE = pathlib.Path(__file__).resolve().parent.parent
CF = RACINE / "cloudflare"
if not (CF / "node_modules" / "wrangler").exists():
    print("cloudflare/node_modules absent : test sauté (cd cloudflare && npm install)"); sys.exit(0)
from playwright.async_api import async_playwright

def port_libre():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

# ---- faux serveurs : API Messages et service de notifications ----
RECUS = []
PLATS = {"plats": [{"nom": "Poulet coco express", "pourquoi": "Tout est à la maison", "temps_min": 20,
                    "ingredients": [{"aliment": "Poulet", "quantite": 300}, {"aliment": "Riz", "quantite": 150}], "etapes": ["Saisir", "Mijoter"]}]}
class Faux(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0); corps = self.rfile.read(n) if n else b""
        RECUS.append((self.path, dict(self.headers), corps))
        if self.path.startswith("/v1/messages"):
            rep = {"id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "stop_reason": "end_turn",
                   "content": [{"type": "text", "text": json.dumps(PLATS)}], "usage": {"input_tokens": 1, "output_tokens": 1}}
            b = json.dumps(rep).encode(); self.send_response(200); self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        self.send_response(410 if "parti" in self.path else 201); self.send_header("content-length", "0"); self.end_headers()

def requete(base, chemin, methode="GET", corps=None, code="code-du-test"):
    r = urllib.request.Request(base + chemin, method=methode, data=json.dumps(corps).encode() if corps is not None else None,
                               headers={"content-type": "application/json", "authorization": "Bearer " + code})
    try:
        with urllib.request.urlopen(r, timeout=20) as x: return x.status, json.loads(x.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")

async def main():
    erreurs = []
    def verif(ok, msg):
        if not ok: erreurs.append(msg)
    faux = ThreadingHTTPServer(("127.0.0.1", port_libre()), Faux); threading.Thread(target=faux.serve_forever, daemon=True).start()
    pf = faux.server_address[1]
    subprocess.run([sys.executable, str(CF / "preparer.py")], check=True, capture_output=True)
    pw = port_libre(); base = f"http://127.0.0.1:{pw}"
    env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
    persist = tempfile.mkdtemp(prefix="marmite-wrangler-")
    wr = subprocess.Popen(["npx", "wrangler", "dev", "--ip", "127.0.0.1", "--port", str(pw), "--test-scheduled", "--persist-to", persist,
                           "--var", "CODE_FOYER:code-du-test", "--var", "ANTHROPIC_API_KEY:cle-de-test", "--var", f"ANTHROPIC_BASE_URL:http://127.0.0.1:{pf}",
                           "--show-interactive-dev-session=false"], cwd=CF, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(base + "/api/etat", timeout=2) as x: etat = json.loads(x.read()); break
            except Exception: time.sleep(0.5)
        else:
            wr.kill(); print(wr.stdout.read()[-3000:]); sys.exit("wrangler dev ne répond pas")
        verif(etat.get("marmite") and etat.get("chef") and len(base64.urlsafe_b64decode(etat["vapid"] + "==")) == 65, f"/api/etat : {etat}")
        verif(requete(base, "/api/foyer", code="mauvais")[0] == 401, "mauvais code accepté")

        async with async_playwright() as p:
            b = await p.chromium.launch()
            async def appareil():
                ctx = await b.new_context(viewport={"width": 360, "height": 780}, service_workers="block")
                await ctx.add_init_script("try { localStorage.setItem('marmite-tickets', 'manuel'); } catch (e) {}")
                pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
                await pg.route("**/fonts.g*/**", lambda r: r.abort())
                await pg.goto(base + "/"); await pg.wait_for_selector("#code-foyer")
                return pg, errs
            # 1. premier téléphone : la porte, un mauvais code puis le bon
            a, errs_a = await appareil()
            verif(await a.evaluate("document.documentElement.scrollWidth <= innerWidth"), "la porte déborde à 360 px")
            await a.fill("#code-foyer", "faux"); await a.click("#porte button[type=submit]")
            await a.wait_for_selector("text=Code incorrect.")
            await a.fill("#code-foyer", "code-du-test"); await a.click("#porte button[type=submit]")
            await a.wait_for_function("!document.getElementById('porte') && sync === 'serveur'")
            st, d = requete(base, "/api/foyer")
            verif(st == 200 and d["rev"] == 1 and d["doc"]["version"] == 2, f"le premier appareil n'a pas créé le foyer : {st} {d.get('rev')}")
            # cocher un repas : il part au serveur
            await a.evaluate("E.personnes.nicolas.coches['d2-dej'] = true; sauver();")
            await a.wait_for_function("SERVEUR.rev === 2", timeout=10000)
            verif(requete(base, "/api/foyer")[1]["doc"]["personnes"]["nicolas"]["coches"].get("d2-dej"), "la coche n'est pas sur le serveur")

            # 2. second téléphone : il reçoit le foyer
            bb, errs_b = await appareil()
            await bb.fill("#code-foyer", "code-du-test"); await bb.click("#porte button[type=submit]")
            await bb.wait_for_function("!document.getElementById('porte') && sync === 'serveur'")
            verif(await bb.evaluate("!!E.personnes.nicolas.coches['d2-dej'] && SERVEUR.rev === 2"), "le second téléphone n'a pas reçu le foyer")

            # 3. les deux enregistrent sans s'être vus : fusion
            await a.evaluate("E.foyer.achats['c1-Poulet'] = true; sauver();")
            await a.wait_for_function("SERVEUR.rev === 3", timeout=10000)
            await bb.evaluate("E.foyer.payes['c1-Lait'] = 1.15; E.personnes.aurelie.coches['d2-din'] = true; sauver();")
            await bb.wait_for_function("SERVEUR.rev === 4", timeout=10000)
            r = await bb.evaluate("({ poulet: !!E.foyer.achats['c1-Poulet'], lait: E.foyer.payes['c1-Lait'], din: !!E.personnes.aurelie.coches['d2-din'] })")
            verif(r == {"poulet": True, "lait": 1.15, "din": True}, f"fusion sur le second téléphone : {r}")
            await a.evaluate("tirerServeur()"); await a.wait_for_function("SERVEUR.rev === 4")
            verif(await a.evaluate("E.foyer.payes['c1-Lait'] === 1.15 && !!E.personnes.aurelie.coches['d2-din'] && !!E.foyer.achats['c1-Poulet']"), "le premier téléphone n'a pas récupéré les changements")
            # une case décochée d'un côté reste décochée après fusion
            await a.evaluate("delete E.foyer.achats['c1-Poulet']; sauver();"); await a.wait_for_function("SERVEUR.rev === 5", timeout=10000)
            await bb.evaluate("tirerServeur()"); await bb.wait_for_function("SERVEUR.rev === 5")
            verif(await bb.evaluate("!E.foyer.achats['c1-Poulet']"), "la case décochée revient après fusion")

            # 4. le chef passe par le serveur
            await a.evaluate("ouvrirIA('faim')"); await a.click("button[data-action='proposer']")
            await a.wait_for_function("ia && ia.etat === 'resultats'", timeout=15000)
            verif(await a.evaluate("ia.propositions[0].nom") == "Poulet coco express", "proposition du chef absente")
            appel = next((json.loads(c) for chemin, h, c in RECUS if chemin.startswith("/v1/messages")), None)
            verif(appel and appel["model"] == "claude-opus-5-5" and appel["output_config"]["format"]["type"] == "json_schema", f"appel du chef : {appel and {k: appel[k] for k in ('model', 'output_config')}}")
            await a.evaluate("fermerIA()")
            texte = await a.inner_text("body")
            verif("Claude" not in texte, "l'app parle de Claude")

            # 5. rappels : liste envoyée par l'app, cron, notification sans contenu signée VAPID, abonnement périmé retiré
            st, rp = requete(base, "/api/rappel")
            jour = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 4 * 3600))
            requete(base, "/api/rappels", "PUT", {"rappels": [{"date": jour, "titre": "Courses demain", "texte": "Course 2 : vérifie le stock."}]})
            requete(base, "/api/abonnement", "POST", {"abonnement": {"endpoint": f"http://127.0.0.1:{pf}/push/tel-1", "keys": {}}})
            requete(base, "/api/abonnement", "POST", {"abonnement": {"endpoint": f"http://127.0.0.1:{pf}/push/parti", "keys": {}}})
            RECUS.clear()
            urllib.request.urlopen(base + "/__scheduled?cron=0+14+*+*+*", timeout=20).read()
            for _ in range(40):
                if len([x for x in RECUS if x[0].startswith("/push/")]) >= 2: break
                time.sleep(0.25)
            pushs = {chemin: h for chemin, h, c in RECUS if chemin.startswith("/push/")}
            h = pushs.get("/push/tel-1", {})
            auth = {k.lower(): v for k, v in h.items()}.get("authorization", "")
            verif(auth.startswith("vapid t=") and ", k=" in auth, f"notification sans signature VAPID : {auth[:40]}")
            if auth.startswith("vapid t="):
                jwt = auth[len("vapid t="):].split(",")[0]; charge = json.loads(base64.urlsafe_b64decode(jwt.split(".")[1] + "=="))
                verif(charge["aud"] == f"http://127.0.0.1:{pf}" and charge["sub"].startswith("https://"), f"jeton VAPID : {charge}")
                try:
                    from cryptography.hazmat.primitives.asymmetric import ec, utils
                    from cryptography.hazmat.primitives import hashes
                    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), base64.urlsafe_b64decode(etat["vapid"] + "=="))
                    sig = base64.urlsafe_b64decode(jwt.split(".")[2] + "==")
                    pub.verify(utils.encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")),
                               ".".join(jwt.split(".")[:2]).encode(), ec.ECDSA(hashes.SHA256()))
                except ImportError: pass
                except Exception as e: verif(False, f"signature VAPID invalide : {e}")
            verif(requete(base, "/api/rappel")[1]["titre"] == "Courses demain", "texte du rappel du jour absent")
            st, d = requete(base, "/api/rappels/essai", "POST")
            verif(d.get("envoyes") == 1, f"l'abonnement périmé n'a pas été retiré : {d}")
            # l'app envoie ses rappels : la veille des courses et la préparation du mois
            await a.evaluate("SERVEUR.rappels = ''; envoyerRappels()"); await a.wait_for_timeout(500)
            await a.click("#nav-barre button[data-vue='profil']")
            profil = await a.inner_text("main")
            verif("Rappels sur ce téléphone" in profil and "Enregistrées pour le foyer" in profil, "cartes Données / Rappels absentes")
            verif(await a.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Profil déborde à 360 px")

            # 6. copier les données puis les importer dans la version de fichier (hors serveur)
            await a.click("button[data-action='exporter']")
            exporte = await a.input_value("#donnees-texte")
            verif(json.loads(exporte)["foyer"]["payes"].get("c1-Lait") == 1.15, "export incomplet")
            loc = await b.new_page(viewport={"width": 360, "height": 780}); errs_l = []; loc.on("pageerror", lambda e: errs_l.append(str(e)))
            await loc.route("**/fonts.g*/**", lambda r: r.abort())
            await loc.add_init_script("try { localStorage.setItem('marmite-tickets', 'manuel'); } catch (e) {}")
            await loc.goto((RACINE / "app" / "marmite.html").as_uri()); await loc.wait_for_timeout(300)
            verif(await loc.evaluate("!SERVEUR.actif && !document.getElementById('porte')"), "la version de fichier se croit sur le serveur")
            await loc.click("#nav-barre button[data-vue='profil']"); await loc.click("button[data-action='importer']")
            await loc.fill("#donnees-texte", exporte)
            loc.once("dialog", lambda dlg: asyncio.ensure_future(dlg.accept()))
            await loc.click("button[data-action='importer-ok']")
            verif(await loc.evaluate("E.foyer.payes['c1-Lait'] === 1.15 && !!E.personnes.aurelie.coches['d2-din']"), "import des données raté")
            verif(not errs_a and not errs_b and not errs_l, f"erreurs de page : {errs_a + errs_b + errs_l}")
            await b.close()
    finally:
        wr.terminate()
        try: wr.wait(10)
        except Exception: wr.kill()
        faux.shutdown()
    print("erreurs", erreurs)
    sys.exit(1 if erreurs else 0)

asyncio.run(main())
