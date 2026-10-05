// Marmite sur Cloudflare : sert la page (public/) et l'API du foyer.
//  /api/etat         public : le serveur répond, le chef est-il disponible, clé publique des rappels
//  /api/foyer        GET / PUT (code du foyer) : le document du foyer, avec un numéro de révision
//  /api/chef         POST (code) : « J'ai faim » et « Changer », réponse JSON imposée
//  /api/abonnement   POST / DELETE (code) : rappels sur un téléphone (Web Push)
//  /api/rappels      PUT (code) : dates des rappels calculées par l'app ; POST /api/rappels/essai : rappel d'essai
//  /api/rappel       public : texte du rappel du jour, lu par le service worker à la réception
// Le cron (wrangler.toml) envoie chaque jour les rappels dont la date est aujourd'hui.
import Anthropic from "@anthropic-ai/sdk";

const json = (d, status = 200) => new Response(JSON.stringify(d), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const erreur = (code, message, status) => json({ code, message }, status);

/* ---------- Base D1 : une table clé → valeur avec révision, une table d'abonnements ---------- */
let tablesPretes = false;
async function tables(env) {
  if (tablesPretes) return;
  await env.BASE.batch([
    env.BASE.prepare("CREATE TABLE IF NOT EXISTS docs (cle TEXT PRIMARY KEY, rev INTEGER NOT NULL, valeur TEXT NOT NULL, date TEXT NOT NULL)"),
    env.BASE.prepare("CREATE TABLE IF NOT EXISTS abonnements (endpoint TEXT PRIMARY KEY, valeur TEXT NOT NULL, date TEXT NOT NULL)"),
  ]);
  tablesPretes = true;
}
async function lire(env, cle) {
  const l = await env.BASE.prepare("SELECT rev, valeur FROM docs WHERE cle = ?").bind(cle).first();
  return l ? { rev: l.rev, valeur: JSON.parse(l.valeur) } : null;
}
async function ecrire(env, cle, valeur) {
  await env.BASE.prepare("INSERT INTO docs (cle, rev, valeur, date) VALUES (?, 1, ?, ?) ON CONFLICT(cle) DO UPDATE SET rev = rev + 1, valeur = excluded.valeur, date = excluded.date")
    .bind(cle, JSON.stringify(valeur), new Date().toISOString()).run();
}

/* ---------- Code du foyer ---------- */
async function codeValide(req, env) {
  const recu = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (!recu || !env.CODE_FOYER) return false;
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([crypto.subtle.digest("SHA-256", enc.encode(recu)), crypto.subtle.digest("SHA-256", enc.encode(env.CODE_FOYER))]);
  return crypto.subtle.timingSafeEqual(a, b);
}

/* ---------- Date du jour à La Réunion ---------- */
const jourLocal = (env, d = new Date()) => new Intl.DateTimeFormat("en-CA", { timeZone: env.FUSEAU || "Indian/Reunion", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);

/* ---------- Web Push sans contenu (le service worker lit /api/rappel) ---------- */
const b64url = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
async function clesVapid(env) {
  const l = await lire(env, "vapid");
  if (l) return l.valeur;
  const paire = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const cles = { publique: b64url(await crypto.subtle.exportKey("raw", paire.publicKey)), privee: await crypto.subtle.exportKey("jwk", paire.privateKey) };
  // première écriture seulement : si deux requêtes génèrent en même temps, la première gagne
  await env.BASE.prepare("INSERT OR IGNORE INTO docs (cle, rev, valeur, date) VALUES ('vapid', 1, ?, ?)").bind(JSON.stringify(cles), new Date().toISOString()).run();
  return (await lire(env, "vapid")).valeur;
}
async function jetonVapid(env, cles, endpoint) {
  const enc = s => b64url(new TextEncoder().encode(JSON.stringify(s)));
  const corps = enc({ typ: "JWT", alg: "ES256" }) + "." + enc({ aud: new URL(endpoint).origin, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: env.CONTACT });
  const cle = await crypto.subtle.importKey("jwk", cles.privee, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, cle, new TextEncoder().encode(corps));
  return corps + "." + b64url(sig);
}
async function pousser(env) {
  const cles = await clesVapid(env);
  const { results } = await env.BASE.prepare("SELECT endpoint FROM abonnements").all();
  let envoyes = 0;
  for (const { endpoint } of results) {
    const r = await fetch(endpoint, { method: "POST", headers: {
      authorization: `vapid t=${await jetonVapid(env, cles, endpoint)}, k=${cles.publique}`, ttl: "43200", urgency: "normal", "content-length": "0",
    } });
    if (r.status === 404 || r.status === 410) await env.BASE.prepare("DELETE FROM abonnements WHERE endpoint = ?").bind(endpoint).run();
    else if (r.ok) envoyes++;
  }
  return envoyes;
}
async function rappelsDuJour(env) {
  const l = await lire(env, "rappels"), auj = jourLocal(env);
  return ((l && l.valeur) || []).filter(r => r.date === auj);
}

/* ---------- Le chef ---------- */
const SCHEMA_PLATS = {
  type: "object", additionalProperties: false, required: ["plats"],
  properties: { plats: { type: "array", items: {
    type: "object", additionalProperties: false, required: ["nom", "pourquoi", "temps_min", "ingredients", "etapes"],
    properties: {
      nom: { type: "string" }, pourquoi: { type: "string" }, temps_min: { type: "integer" },
      ingredients: { type: "array", items: { type: "object", additionalProperties: false, required: ["aliment", "quantite"],
        properties: { aliment: { type: "string" }, quantite: { type: "number" } } } },
      etapes: { type: "array", items: { type: "string" } },
    } } } },
};
async function chef(req, env) {
  if (!env.ANTHROPIC_API_KEY) return erreur("indisponible", "Le chef n'est pas branché sur ce serveur.", 503);
  const { consigne } = await req.json().catch(() => ({}));
  if (typeof consigne !== "string" || !consigne.trim() || consigne.length > 60000) return erreur("requete", "Consigne manquante ou trop longue.", 400);
  // garde-fou de dépense : un nombre d'appels par jour
  const cle = "chef-" + jourLocal(env), compte = await lire(env, cle);
  if (compte && compte.valeur >= +(env.CHEF_PAR_JOUR || 30)) return erreur("rate_limited", "Le chef a assez travaillé pour aujourd'hui.", 429);
  await ecrire(env, cle, (compte ? compte.valeur : 0) + 1);
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY, ...(env.ANTHROPIC_BASE_URL ? { baseURL: env.ANTHROPIC_BASE_URL } : {}) });
  try {
    const rep = await client.beta.messages.create({
      model: "claude-opus-5-5",
      max_tokens: 16000,
      betas: ["server-side-fallback-2026-07-01"],
      fallbacks: "default",
      output_config: { effort: "low", format: { type: "json_schema", schema: SCHEMA_PLATS } },
      messages: [{ role: "user", content: consigne }],
    });
    if (rep.stop_reason === "refusal") return erreur("refus", "Le chef n'a pas voulu répondre à cette demande.", 422);
    const texte = rep.content.filter(b => b.type === "text").map(b => b.text).join("");
    try { return json(JSON.parse(texte)); } catch (e) { return erreur("invalid_json", "Réponse illisible.", 502); }
  } catch (e) {
    if (e instanceof Anthropic.RateLimitError) return erreur("rate_limited", "Trop de demandes.", 429);
    if (e instanceof Anthropic.AuthenticationError) return erreur("indisponible", "Clé du chef refusée.", 503);
    if (e instanceof Anthropic.APIError) return erreur("chef", "Le chef n'a pas pu répondre.", 502);
    throw e;
  }
}

/* ---------- Routeur ---------- */
async function api(req, env) {
  const url = new URL(req.url), chemin = url.pathname, m = req.method;
  await tables(env);
  if (chemin === "/api/etat") {
    return json({ marmite: true, code: !!env.CODE_FOYER, chef: !!env.ANTHROPIC_API_KEY, vapid: (await clesVapid(env)).publique });
  }
  if (chemin === "/api/rappel") {
    const l = await rappelsDuJour(env);
    return json(l.length ? { titre: l.map(r => r.titre).join(" · "), texte: l.map(r => r.texte).join("\n"), date: l[0].date }
      : { titre: "Marmite", texte: "Un rappel t'attend dans l'app.", date: jourLocal(env) });
  }
  if (!env.CODE_FOYER) return erreur("code", "Le code du foyer n'est pas réglé sur le serveur.", 503);
  if (!(await codeValide(req, env))) {
    await new Promise(r => setTimeout(r, 400)); // freine les essais au hasard
    return erreur("code", "Code du foyer incorrect.", 401);
  }

  if (chemin === "/api/foyer" && m === "GET") {
    const l = await lire(env, "foyer");
    return json({ doc: l ? l.valeur : null, rev: l ? l.rev : 0 });
  }
  if (chemin === "/api/foyer" && m === "PUT") {
    const { doc, rev } = await req.json().catch(() => ({}));
    if (!doc || typeof doc !== "object") return erreur("requete", "Document manquant.", 400);
    const valeur = JSON.stringify(doc), date = new Date().toISOString();
    // écriture seulement si personne n'a enregistré entre-temps (révision attendue)
    const r = (rev || 0) === 0
      ? await env.BASE.prepare("INSERT OR IGNORE INTO docs (cle, rev, valeur, date) VALUES ('foyer', 1, ?, ?)").bind(valeur, date).run()
      : await env.BASE.prepare("UPDATE docs SET rev = rev + 1, valeur = ?, date = ? WHERE cle = 'foyer' AND rev = ?").bind(valeur, date, rev).run();
    if (!r.meta.changes) {
      const l = await lire(env, "foyer");
      return json({ code: "conflit", doc: l ? l.valeur : null, rev: l ? l.rev : 0 }, 409);
    }
    return json({ rev: (rev || 0) + 1 });
  }
  if (chemin === "/api/chef" && m === "POST") return chef(req, env);
  if (chemin === "/api/abonnement" && m === "POST") {
    const { abonnement } = await req.json().catch(() => ({}));
    // les navigateurs donnent toujours une adresse https ; http n'est admis que vers la machine locale (tests)
    if (!abonnement || !/^(https:\/\/|http:\/\/(127\.0\.0\.1|localhost)[:/])/.test(abonnement.endpoint || "")) return erreur("requete", "Abonnement invalide.", 400);
    await env.BASE.prepare("INSERT INTO abonnements (endpoint, valeur, date) VALUES (?, ?, ?) ON CONFLICT(endpoint) DO UPDATE SET valeur = excluded.valeur, date = excluded.date")
      .bind(abonnement.endpoint, JSON.stringify(abonnement), new Date().toISOString()).run();
    return json({ ok: true });
  }
  if (chemin === "/api/abonnement" && m === "DELETE") {
    const { endpoint } = await req.json().catch(() => ({}));
    await env.BASE.prepare("DELETE FROM abonnements WHERE endpoint = ?").bind(endpoint || "").run();
    return json({ ok: true });
  }
  if (chemin === "/api/rappels" && m === "PUT") {
    const { rappels } = await req.json().catch(() => ({}));
    if (!Array.isArray(rappels)) return erreur("requete", "Liste de rappels attendue.", 400);
    const propres = rappels.filter(r => r && /^\d{4}-\d{2}-\d{2}$/.test(r.date)).slice(0, 60)
      .map(r => ({ date: r.date, titre: String(r.titre || "Marmite").slice(0, 80), texte: String(r.texte || "").slice(0, 300) }));
    const avant = await lire(env, "rappels");
    if (!avant || JSON.stringify(avant.valeur) !== JSON.stringify(propres)) await ecrire(env, "rappels", propres);
    return json({ ok: true, n: propres.length });
  }
  if (chemin === "/api/rappels/essai" && m === "POST") return json({ envoyes: await pousser(env) });
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
    if ((await rappelsDuJour(env)).length) ctx.waitUntil(pousser(env));
  },
};
