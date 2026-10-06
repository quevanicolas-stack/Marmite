// Miamm sur Cloudflare : sert la page (public/) et l'API.
//  Comptes : clés d'accès (WebAuthn), sur invitation ; un code de secours par compte ; session en cookie HttpOnly.
//  Foyers : un document par foyer, avec révision (deux téléphones peuvent enregistrer, l'app fusionne).
//  Le chef : « J'ai faim » (/api/chef) et la lecture des tickets de caisse en photo ou en PDF (/api/ticket), via l'API Anthropic.
//  Rappels : Web Push signé VAPID, par foyer, envoyés par le cron (wrangler.toml).
import Anthropic from "@anthropic-ai/sdk";
import { b64url, verifierInscription, verifierConnexion } from "./cles.js";

const json = (d, status = 200, entetes = {}) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...entetes },
});
const erreur = (code, message, status) => json({ code, message }, status);
const maintenant = () => new Date().toISOString();
const aleatoire = n => b64url(crypto.getRandomValues(new Uint8Array(n)));
const hacher = async s => b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)));
const jourLocal = (env, d = new Date()) => new Intl.DateTimeFormat("en-CA", { timeZone: env.FUSEAU || "Indian/Reunion", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);

/* ---------- Base D1 ---------- */
let tablesPretes = false;
async function tables(env) {
  if (tablesPretes) return;
  await env.BASE.batch([
    "CREATE TABLE IF NOT EXISTS docs (cle TEXT PRIMARY KEY, rev INTEGER NOT NULL, valeur TEXT NOT NULL, date TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS comptes (id TEXT PRIMARY KEY, nom TEXT NOT NULL, foyer TEXT NOT NULL, secours TEXT, cree TEXT NOT NULL)",
    "CREATE UNIQUE INDEX IF NOT EXISTS comptes_secours ON comptes(secours)",
    "CREATE TABLE IF NOT EXISTS cles (id TEXT PRIMARY KEY, compte TEXT NOT NULL, cle TEXT NOT NULL, alg INTEGER NOT NULL, compteur INTEGER NOT NULL, cree TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, compte TEXT NOT NULL, expire TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS defis (id TEXT PRIMARY KEY, valeur TEXT NOT NULL, expire TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS invitations (code TEXT PRIMARY KEY, foyer TEXT, par TEXT, cree TEXT NOT NULL, utilisee TEXT)",
    "CREATE TABLE IF NOT EXISTS abonnements (endpoint TEXT PRIMARY KEY, foyer TEXT NOT NULL, valeur TEXT NOT NULL, date TEXT NOT NULL)",
  ].map(q => env.BASE.prepare(q)));
  tablesPretes = true;
}
async function lire(env, cle) {
  const l = await env.BASE.prepare("SELECT rev, valeur FROM docs WHERE cle = ?").bind(cle).first();
  return l ? { rev: l.rev, valeur: JSON.parse(l.valeur) } : null;
}
async function ecrire(env, cle, valeur) {
  await env.BASE.prepare("INSERT INTO docs (cle, rev, valeur, date) VALUES (?, 1, ?, ?) ON CONFLICT(cle) DO UPDATE SET rev = rev + 1, valeur = excluded.valeur, date = excluded.date")
    .bind(cle, JSON.stringify(valeur), maintenant()).run();
}
// compteur quotidien (garde-fou de dépense) : vrai si la limite est atteinte
async function limite(env, nom, max) {
  const cle = `${nom}-${jourLocal(env)}`, l = await lire(env, cle);
  if (l && l.valeur >= max) return true;
  await ecrire(env, cle, (l ? l.valeur : 0) + 1);
  return false;
}

/* ---------- Sessions ---------- */
const NOM_COOKIE = "miamm_session";
function cookieSession(req, valeur, maxAge) {
  const local = /^http:\/\/(localhost|127\.0\.0\.1)[:/]/.test(req.url);
  return `${NOM_COOKIE}=${valeur}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${maxAge}${local ? "" : "; Secure"}`;
}
async function ouvrirSession(env, req, compte) {
  const jeton = aleatoire(32);
  await env.BASE.prepare("INSERT INTO sessions (id, compte, expire) VALUES (?, ?, ?)").bind(await hacher(jeton), compte, new Date(Date.now() + 180 * 86400000).toISOString()).run();
  return cookieSession(req, jeton, 180 * 86400);
}
async function compteDe(env, req) {
  const m = (req.headers.get("cookie") || "").match(new RegExp(`(?:^|; )${NOM_COOKIE}=([^;]+)`));
  if (!m) return null;
  const s = await env.BASE.prepare("SELECT c.id, c.nom, c.foyer, s.expire FROM sessions s JOIN comptes c ON c.id = s.compte WHERE s.id = ?").bind(await hacher(m[1])).first();
  if (!s || s.expire < maintenant()) return null;
  return { id: s.id, nom: s.nom, foyer: s.foyer, jeton: m[1] };
}

/* ---------- Clés d'accès ---------- */
const rp = req => { const u = new URL(req.url); return { origine: u.origin, rpId: u.hostname }; };
async function nouveauDefi(env, valeur) {
  const id = aleatoire(32);
  await env.BASE.prepare("DELETE FROM defis WHERE expire < ?").bind(maintenant()).run();
  await env.BASE.prepare("INSERT INTO defis (id, valeur, expire) VALUES (?, ?, ?)").bind(id, JSON.stringify(valeur), new Date(Date.now() + 5 * 60000).toISOString()).run();
  return id;
}
async function prendreDefi(env, id) {
  const d = await env.BASE.prepare("DELETE FROM defis WHERE id = ? RETURNING valeur, expire").bind(id || "").first();
  return d && d.expire >= maintenant() ? JSON.parse(d.valeur) : null;
}
const optionsCreation = (req, defi, idUtilisateur, nom) => ({
  challenge: defi, rp: { name: "Miamm", id: rp(req).rpId },
  user: { id: idUtilisateur, name: nom, displayName: nom },
  pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
  authenticatorSelection: { residentKey: "required", requireResidentKey: true, userVerification: "preferred" },
  attestation: "none", timeout: 120000,
});
// code de secours : 4 groupes de 4 caractères sans ambiguïté (pas de 0/O, 1/I)
function codeSecours() {
  const alpha = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789", o = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(o, x => alpha[x % alpha.length]).join("").match(/.{4}/g).join("-");
}
const normaliserCode = c => String(c || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
async function invitationValide(env, code) {
  const c = normaliserCode(code);
  if (!c) return null;
  if (env.INVITATION_INITIALE && c === normaliserCode(env.INVITATION_INITIALE)) return { code: c, foyer: null, initiale: true };
  const l = await env.BASE.prepare("SELECT code, foyer FROM invitations WHERE code = ? AND utilisee IS NULL").bind(c).first();
  return l ? { code: l.code, foyer: l.foyer } : null;
}

/* ---------- Web Push sans contenu ---------- */
async function clesVapid(env) {
  const l = await lire(env, "vapid");
  if (l) return l.valeur;
  const paire = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const cles = { publique: b64url(await crypto.subtle.exportKey("raw", paire.publicKey)), privee: await crypto.subtle.exportKey("jwk", paire.privateKey) };
  await env.BASE.prepare("INSERT OR IGNORE INTO docs (cle, rev, valeur, date) VALUES ('vapid', 1, ?, ?)").bind(JSON.stringify(cles), maintenant()).run();
  return (await lire(env, "vapid")).valeur;
}
async function jetonVapid(env, cles, endpoint) {
  const enc = s => b64url(new TextEncoder().encode(JSON.stringify(s)));
  const corps = enc({ typ: "JWT", alg: "ES256" }) + "." + enc({ aud: new URL(endpoint).origin, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: env.CONTACT });
  const cle = await crypto.subtle.importKey("jwk", cles.privee, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  return corps + "." + b64url(await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, cle, new TextEncoder().encode(corps)));
}
async function pousser(env, foyer) {
  const cles = await clesVapid(env);
  const { results } = foyer ? await env.BASE.prepare("SELECT endpoint FROM abonnements WHERE foyer = ?").bind(foyer).all() : await env.BASE.prepare("SELECT endpoint FROM abonnements").all();
  let envoyes = 0;
  for (const { endpoint } of results) {
    const r = await fetch(endpoint, { method: "POST", headers: { authorization: `vapid t=${await jetonVapid(env, cles, endpoint)}, k=${cles.publique}`, ttl: "43200", urgency: "normal", "content-length": "0" } });
    if (r.status === 404 || r.status === 410) await env.BASE.prepare("DELETE FROM abonnements WHERE endpoint = ?").bind(endpoint).run();
    else if (r.ok) envoyes++;
  }
  return envoyes;
}
async function rappelsDuJour(env, foyer) {
  const l = await lire(env, "rappels:" + foyer), auj = jourLocal(env);
  return ((l && l.valeur) || []).filter(r => r.date === auj);
}

/* ---------- Le chef (API Anthropic) ---------- */
const client = env => new Anthropic({ apiKey: env.ANTHROPIC_API_KEY, ...(env.ANTHROPIC_BASE_URL ? { baseURL: env.ANTHROPIC_BASE_URL } : {}) });
async function appelJson(env, contenu, schema, effort) {
  try {
    const rep = await client(env).beta.messages.create({
      model: "claude-opus-5-5", max_tokens: 16000,
      betas: ["server-side-fallback-2026-07-01"], fallbacks: "default",
      output_config: { effort, format: { type: "json_schema", schema } },
      messages: [{ role: "user", content: contenu }],
    });
    if (rep.stop_reason === "refusal") return erreur("refus", "Le chef n'a pas voulu répondre à cette demande.", 422);
    if (rep.stop_reason === "max_tokens") { console.error("chef : réponse coupée", rep.usage); return erreur("invalid_json", "Réponse trop longue, réessaie.", 502); }
    const texte = rep.content.filter(b => b.type === "text").map(b => b.text).join("");
    try { return json(JSON.parse(texte)); } catch (e) { console.error("chef : JSON illisible", texte.slice(0, 300)); return erreur("invalid_json", "Réponse illisible.", 502); }
  } catch (e) {
    console.error("chef :", e && e.status, e && e.message);
    if (e instanceof Anthropic.RateLimitError) return erreur("rate_limited", "Trop de demandes, réessaie dans une minute.", 429);
    if (e instanceof Anthropic.AuthenticationError) return erreur("indisponible", "Clé du chef refusée.", 503);
    if (e instanceof Anthropic.PermissionDeniedError) return erreur("indisponible", "Clé du chef sans accès à ce modèle.", 503);
    // le détail brut (qui nomme le fournisseur) reste dans les journaux ; l'app ne montre qu'un motif en français
    if (e instanceof Anthropic.BadRequestError && /credit balance/i.test(e.message || "")) return erreur("credit", "Le chef est en pause : le crédit du service est épuisé (à recharger par l'administrateur).", 503);
    if (e instanceof Anthropic.APIError) return erreur("chef", `Le chef n'a pas pu répondre (erreur ${e.status || "réseau"}), réessaie plus tard.`, 502);
    return erreur("chef", "Le chef n'a pas pu répondre, réessaie plus tard.", 502);
  }
}
const SCHEMA_PLATS = {
  type: "object", additionalProperties: false, required: ["plats"],
  properties: { plats: { type: "array", items: {
    type: "object", additionalProperties: false, required: ["nom", "pourquoi", "temps_min", "ingredients", "etapes"],
    properties: { nom: { type: "string" }, pourquoi: { type: "string" }, temps_min: { type: "integer" },
      ingredients: { type: "array", items: { type: "object", additionalProperties: false, required: ["aliment", "quantite"], properties: { aliment: { type: "string" }, quantite: { type: "number" } } } },
      etapes: { type: "array", items: { type: "string" } } } } } },
};
const SCHEMA_TICKET = {
  type: "object", additionalProperties: false, required: ["magasin", "date", "total", "lignes"],
  properties: {
    magasin: { type: "string" }, date: { type: "string", description: "aaaa-mm-jj, vide si illisible" }, total: { type: "number" },
    lignes: { type: "array", items: { type: "object", additionalProperties: false, required: ["libelle", "aliment", "nombre", "poids_g", "prix", "alimentaire"],
      properties: {
        libelle: { type: "string", description: "le texte de la ligne, tel qu'imprimé" },
        aliment: { type: "string", description: "le nom exact du catalogue qui correspond, ou une chaîne vide si aucun ne correspond" },
        nombre: { type: "number", description: "nombre d'articles (paquets, pièces, barquettes)" },
        poids_g: { type: "number", description: "poids en grammes si la ligne est vendue au poids ou si le poids est imprimé, sinon 0" },
        prix: { type: "number", description: "montant payé pour la ligne, en euros, remises déduites" },
        alimentaire: { type: "boolean" },
      } } },
  },
};
async function chef(corps, env, compte) {
  if (!env.ANTHROPIC_API_KEY) return erreur("indisponible", "Le chef n'est pas branché sur ce serveur.", 503);
  const { consigne } = corps;
  if (typeof consigne !== "string" || !consigne.trim() || consigne.length > 60000) return erreur("requete", "Consigne manquante ou trop longue.", 400);
  if (await limite(env, "chef-" + compte.foyer, +(env.CHEF_PAR_JOUR || 30))) return erreur("rate_limited", "Le chef a assez travaillé pour aujourd'hui.", 429);
  return appelJson(env, consigne, SCHEMA_PLATS, "low");
}
// photo (JPEG, PNG, WebP) ou PDF du ticket, en data URI ; pas d'expression régulière sur le contenu (plusieurs centaines
// de Ko) : le temps de calcul d'un Worker est compté
const TYPES_TICKET = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
// lecture des photos par le chef : payante, coupée tant que LECTURE_CHEF ne vaut pas « oui » (l'app lit les PDF et le texte collé sans elle)
const lectureChef = env => !!env.ANTHROPIC_API_KEY && env.LECTURE_CHEF === "oui";
async function ticket(corps, env, compte) {
  if (!lectureChef(env)) return erreur("indisponible", "La lecture des photos par le chef est coupée : envoie le PDF du ticket ou colle son texte.", 503);
  const { image, catalogue } = corps;
  const v = typeof image === "string" ? image.indexOf(";base64,") : -1, type = v > 5 ? image.slice(5, v) : "";
  if (!TYPES_TICKET.includes(type) || !image.startsWith("data:")) return erreur("requete", "Envoie une photo ou un PDF du ticket.", 400);
  const data = image.slice(v + 8);
  if (!data || data.length > 9_000_000) return erreur("requete", "Fichier absent ou trop lourd (6 Mo au plus).", 400);
  if (await limite(env, "ticket-" + compte.foyer, +(env.TICKETS_PAR_JOUR || 15))) return erreur("rate_limited", "Assez de tickets pour aujourd'hui.", 429);
  const noms = (Array.isArray(catalogue) ? catalogue : []).filter(x => typeof x === "string").slice(0, 400);
  const consigne = `Voici un ticket de caisse de supermarché (photo ou PDF). Relève chaque ligne d'article.
Pour chaque ligne : le libellé imprimé, le nombre d'articles, le poids en grammes s'il est imprimé (produits à la coupe, au poids, ou poids écrit dans le libellé), le montant payé remises déduites, et si c'est de l'alimentaire (boissons sucrées, alcool, hygiène, entretien = non alimentaire).
Rapproche chaque ligne alimentaire d'un nom de ce catalogue quand c'est clairement le même produit (une marque ou une variante du même produit compte ; « filet de poulet » → « Poulet ») ; sinon laisse aliment vide.
Catalogue : ${noms.join(" ; ")}
Donne aussi le magasin, la date (aaaa-mm-jj) et le total payé.`;
  const piece = type === "application/pdf"
    ? { type: "document", source: { type: "base64", media_type: type, data } }
    : { type: "image", source: { type: "base64", media_type: type, data } };
  return appelJson(env, [piece, { type: "text", text: consigne }], SCHEMA_TICKET, "low");
}

/* ---------- Routeur ---------- */
async function api(req, env) {
  const url = new URL(req.url), chemin = url.pathname, m = req.method;
  await tables(env);
  // requêtes qui modifient : même origine et JSON (protection contre les requêtes d'un autre site)
  if (m !== "GET") {
    const o = req.headers.get("origin");
    if (o && o !== url.origin) return erreur("origine", "Origine refusée.", 403);
    if (!/^application\/json/.test(req.headers.get("content-type") || "")) return erreur("requete", "JSON attendu.", 415);
  }
  const corps = m !== "GET" ? await req.json().catch(() => ({})) : {};
  const compte = await compteDe(env, req);

  if (chemin === "/api/etat") return json({ miamm: true, chef: !!env.ANTHROPIC_API_KEY, lectureChef: lectureChef(env), vapid: (await clesVapid(env)).publique,
    compte: compte ? { id: compte.id, nom: compte.nom, foyer: compte.foyer } : null });
  if (chemin === "/api/rappel") {
    // lu par le service worker à la réception d'un rappel : le texte du jour pour le foyer de la session, sinon générique
    const l = compte ? await rappelsDuJour(env, compte.foyer) : [];
    return json(l.length ? { titre: l.map(r => r.titre).join(" · "), texte: l.map(r => r.texte).join("\n"), date: l[0].date }
      : { titre: "Miamm", texte: "Un rappel t'attend dans l'app.", date: jourLocal(env) });
  }

  // inscription : invitation + prénom → options de création de la clé → vérification → compte, foyer, session, code de secours
  if (chemin === "/api/inscription/debut" && m === "POST") {
    const inv = await invitationValide(env, corps.invitation);
    const nom = String(corps.nom || "").trim().slice(0, 40);
    if (!inv) return erreur("invitation", "Invitation inconnue ou déjà utilisée.", 400);
    if (!nom) return erreur("requete", "Prénom manquant.", 400);
    const idUtilisateur = aleatoire(16), defi = aleatoire(32);
    const id = await nouveauDefi(env, { type: "inscription", defi, invitation: inv, nom, idUtilisateur });
    return json({ id, options: optionsCreation(req, defi, idUtilisateur, nom) });
  }
  if (chemin === "/api/inscription/fin" && m === "POST") {
    const d = await prendreDefi(env, corps.id);
    if (!d || d.type !== "inscription") return erreur("defi", "Demande expirée, recommence.", 400);
    const inv = await invitationValide(env, d.invitation.code);
    if (!inv) return erreur("invitation", "Invitation déjà utilisée.", 400);
    let cle;
    try { cle = await verifierInscription(corps.reponse, { defi: d.defi, ...rp(req) }); } catch (e) { return erreur("cle", "Clé d'accès refusée : " + e.message, 400); }
    const foyer = inv.foyer || aleatoire(12), secours = codeSecours();
    const stmts = [
      env.BASE.prepare("INSERT INTO comptes (id, nom, foyer, secours, cree) VALUES (?, ?, ?, ?, ?)").bind(d.idUtilisateur, d.nom, foyer, await hacher(normaliserCode(secours)), maintenant()),
      env.BASE.prepare("INSERT INTO cles (id, compte, cle, alg, compteur, cree) VALUES (?, ?, ?, ?, ?, ?)").bind(cle.idCle, d.idUtilisateur, JSON.stringify(cle.cle), cle.alg, cle.compteur, maintenant()),
    ];
    if (!inv.initiale) stmts.push(env.BASE.prepare("UPDATE invitations SET utilisee = ? WHERE code = ?").bind(maintenant(), inv.code));
    await env.BASE.batch(stmts);
    return json({ compte: { id: d.idUtilisateur, nom: d.nom, foyer }, secours, nouveauFoyer: !inv.foyer }, 200, { "set-cookie": await ouvrirSession(env, req, d.idUtilisateur) });
  }
  // connexion : clé d'accès découvrable (le téléphone propose le compte)
  if (chemin === "/api/connexion/debut" && m === "POST") {
    const defi = aleatoire(32), id = await nouveauDefi(env, { type: "connexion", defi });
    return json({ id, options: { challenge: defi, rpId: rp(req).rpId, userVerification: "preferred", timeout: 120000 } });
  }
  if (chemin === "/api/connexion/fin" && m === "POST") {
    const d = await prendreDefi(env, corps.id);
    if (!d || d.type !== "connexion") return erreur("defi", "Demande expirée, recommence.", 400);
    const rep = corps.reponse || {};
    const k = await env.BASE.prepare("SELECT k.compte, k.cle, k.alg, k.compteur, c.nom, c.foyer FROM cles k JOIN comptes c ON c.id = k.compte WHERE k.id = ?").bind(rep.id || "").first();
    if (!k) return erreur("cle", "Cette clé d'accès n'est liée à aucun compte.", 400);
    let n;
    try { n = await verifierConnexion(rep, { defi: d.defi, ...rp(req), cle: JSON.parse(k.cle), alg: k.alg, compteur: k.compteur }); } catch (e) { return erreur("cle", "Clé d'accès refusée : " + e.message, 400); }
    await env.BASE.prepare("UPDATE cles SET compteur = ? WHERE id = ?").bind(n, rep.id).run();
    return json({ compte: { id: k.compte, nom: k.nom, foyer: k.foyer } }, 200, { "set-cookie": await ouvrirSession(env, req, k.compte) });
  }
  // code de secours (téléphone perdu) : ouvre une session ; l'app propose ensuite de créer une nouvelle clé
  if (chemin === "/api/secours" && m === "POST") {
    await new Promise(r => setTimeout(r, 400));
    const c = await env.BASE.prepare("SELECT id, nom, foyer FROM comptes WHERE secours = ?").bind(await hacher(normaliserCode(corps.code))).first();
    if (!c) return erreur("secours", "Code de secours inconnu.", 400);
    const secours = codeSecours();   // un code ne sert qu'une fois
    await env.BASE.prepare("UPDATE comptes SET secours = ? WHERE id = ?").bind(await hacher(normaliserCode(secours)), c.id).run();
    return json({ compte: c, secours }, 200, { "set-cookie": await ouvrirSession(env, req, c.id) });
  }

  if (!compte) return erreur("session", "Connecte-toi d'abord.", 401);

  if (chemin === "/api/deconnexion" && m === "POST") {
    await env.BASE.prepare("DELETE FROM sessions WHERE id = ?").bind(await hacher(compte.jeton)).run();
    return json({ ok: true }, 200, { "set-cookie": cookieSession(req, "", 0) });
  }
  // nouvelle clé pour ce compte (nouvel appareil, ou après le code de secours)
  if (chemin === "/api/cle/debut" && m === "POST") {
    const defi = aleatoire(32), id = await nouveauDefi(env, { type: "cle", defi, compte: compte.id });
    return json({ id, options: optionsCreation(req, defi, compte.id, compte.nom) });
  }
  if (chemin === "/api/cle/fin" && m === "POST") {
    const d = await prendreDefi(env, corps.id);
    if (!d || d.type !== "cle" || d.compte !== compte.id) return erreur("defi", "Demande expirée, recommence.", 400);
    let cle;
    try { cle = await verifierInscription(corps.reponse, { defi: d.defi, ...rp(req) }); } catch (e) { return erreur("cle", "Clé d'accès refusée : " + e.message, 400); }
    await env.BASE.prepare("INSERT INTO cles (id, compte, cle, alg, compteur, cree) VALUES (?, ?, ?, ?, ?, ?)").bind(cle.idCle, compte.id, JSON.stringify(cle.cle), cle.alg, cle.compteur, maintenant()).run();
    return json({ ok: true });
  }
  if (chemin === "/api/invitations" && m === "POST") {
    // « foyer » : la personne rejoint ce foyer ; « proche » : elle crée le sien
    const code = codeSecours().slice(0, 9);
    await env.BASE.prepare("INSERT INTO invitations (code, foyer, par, cree) VALUES (?, ?, ?, ?)").bind(normaliserCode(code), corps.type === "foyer" ? compte.foyer : null, compte.id, maintenant()).run();
    return json({ code, type: corps.type === "foyer" ? "foyer" : "proche" });
  }
  if (chemin === "/api/membres" && m === "GET") {
    const { results } = await env.BASE.prepare("SELECT nom FROM comptes WHERE foyer = ? ORDER BY cree").bind(compte.foyer).all();
    return json({ membres: results.map(r => r.nom) });
  }

  const cleFoyer = "foyer:" + compte.foyer;
  if (chemin === "/api/foyer" && m === "GET") {
    const l = await lire(env, cleFoyer);
    return json({ doc: l ? l.valeur : null, rev: l ? l.rev : 0 });
  }
  if (chemin === "/api/foyer" && m === "PUT") {
    const { doc, rev } = corps;
    if (!doc || typeof doc !== "object") return erreur("requete", "Document manquant.", 400);
    const valeur = JSON.stringify(doc), date = maintenant();
    if (valeur.length > 2_000_000) return erreur("requete", "Document trop lourd.", 413);
    const r = (rev || 0) === 0
      ? await env.BASE.prepare("INSERT OR IGNORE INTO docs (cle, rev, valeur, date) VALUES (?, 1, ?, ?)").bind(cleFoyer, valeur, date).run()
      : await env.BASE.prepare("UPDATE docs SET rev = rev + 1, valeur = ?, date = ? WHERE cle = ? AND rev = ?").bind(valeur, date, cleFoyer, rev).run();
    if (!r.meta.changes) { const l = await lire(env, cleFoyer); return json({ code: "conflit", doc: l ? l.valeur : null, rev: l ? l.rev : 0 }, 409); }
    return json({ rev: (rev || 0) + 1 });
  }
  if (chemin === "/api/chef" && m === "POST") return chef(corps, env, compte);
  if (chemin === "/api/ticket" && m === "POST") return ticket(corps, env, compte);
  if (chemin === "/api/abonnement" && m === "POST") {
    const ab = corps.abonnement;
    // les navigateurs donnent toujours une adresse https ; http n'est admis que vers la machine locale (tests)
    if (!ab || !/^(https:\/\/|http:\/\/(127\.0\.0\.1|localhost)[:/])/.test(ab.endpoint || "")) return erreur("requete", "Abonnement invalide.", 400);
    await env.BASE.prepare("INSERT INTO abonnements (endpoint, foyer, valeur, date) VALUES (?, ?, ?, ?) ON CONFLICT(endpoint) DO UPDATE SET foyer = excluded.foyer, valeur = excluded.valeur, date = excluded.date")
      .bind(ab.endpoint, compte.foyer, JSON.stringify(ab), maintenant()).run();
    return json({ ok: true });
  }
  if (chemin === "/api/abonnement" && m === "DELETE") {
    await env.BASE.prepare("DELETE FROM abonnements WHERE endpoint = ? AND foyer = ?").bind(corps.endpoint || "", compte.foyer).run();
    return json({ ok: true });
  }
  if (chemin === "/api/rappels" && m === "PUT") {
    if (!Array.isArray(corps.rappels)) return erreur("requete", "Liste de rappels attendue.", 400);
    const propres = corps.rappels.filter(r => r && /^\d{4}-\d{2}-\d{2}$/.test(r.date)).slice(0, 60)
      .map(r => ({ date: r.date, titre: String(r.titre || "Miamm").slice(0, 80), texte: String(r.texte || "").slice(0, 300) }));
    const avant = await lire(env, "rappels:" + compte.foyer);
    if (!avant || JSON.stringify(avant.valeur) !== JSON.stringify(propres)) await ecrire(env, "rappels:" + compte.foyer, propres);
    return json({ ok: true, n: propres.length });
  }
  if (chemin === "/api/rappels/essai" && m === "POST") return json({ envoyes: await pousser(env, compte.foyer) });
  return erreur("introuvable", "Route inconnue.", 404);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname.startsWith("/api/")) {
      try { return await api(req, env); } catch (e) { return erreur("serveur", "Erreur du serveur.", 500); }
    }
    return env.ASSETS.fetch(req);
  },
  async scheduled(evt, env, ctx) {
    await tables(env);
    const { results } = await env.BASE.prepare("SELECT DISTINCT foyer FROM abonnements").all();
    for (const { foyer } of results) if ((await rappelsDuJour(env, foyer)).length) ctx.waitUntil(pousser(env, foyer));
  },
};
