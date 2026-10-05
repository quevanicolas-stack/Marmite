/* ============================================================
   Miamm — moteur de composition d'une période (sans IA)
   Dérivé du moteur de Marmite, pour un foyer de N personnes.
   Entrées : catalogue, recettes, réglages, personnes du foyer, période (début + jours), jours de courses,
             stock de départ, budget facultatif, invités.
   Sortie : { periode, bilan }. periode.plan[j].meals[k].items = { <id personne>: [[aliment, qté]], invites? } ;
            periode.courses[c].items[i].need = { <id>: qté, invites? } ; periode.parts[aliment] = { <id>: fraction }.
   Fonctionne dans le navigateur (objet global Moteur) et sous Node (module.exports).
   ============================================================ */
const Moteur = (() => {
  const LABELS = { pdj: "Petit-déjeuner", dej: "Déjeuner", din: "Dîner", des: "Dessert" };
  const CLES = ["pdj", "dej", "din", "des"];
  const JOURS_SEM = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  const MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  const UNITES_ENTIERES = new Set(["Œufs", "Wraps", "Pains burger"]);
  const JOUR_MS = 86400000;
  // Les recettes portent deux portions de référence, issues du foyer d'origine : une « grande » (environ 1 900 kcal par
  // jour) et une « petite » (environ 1 400 kcal, plus de légumes). Chaque personne part de la plus proche de son objectif.
  const REF_GRANDE = "nicolas", REF_PETITE = "aurelie", SEUIL_REF = 1650;

  /* ---------- Outils ---------- */
  function hasard(graine) {
    let a = graine >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const arrondi = (x, pas) => Math.round(x / pas) * pas;
  const r2 = x => Math.round(x * 100) / 100;
  const dateISO = s => { const [a, m, j] = s.split("-").map(Number); return new Date(Date.UTC(a, m - 1, j)); };
  const iso = d => d.toISOString().slice(0, 10);
  const plus = (d, n) => new Date(d.getTime() + n * JOUR_MS);
  const jourMois = d => { const j = d.getUTCDate(); return j === 1 ? "1er" : String(j); };
  const nomJour = d => `${JOURS_SEM[d.getUTCDay()]} ${jourMois(d)} ${MOIS[d.getUTCMonth()]}`;
  const court = d => `${jourMois(d)} ${MOIS[d.getUTCMonth()]}`;

  /* ---------- Nutrition et prix ---------- */
  function nutrition(cat, a, q) {
    const n = cat[a] && cat[a].nut; if (!n) return { kcal: 0, prot: 0 };
    return { kcal: n[2] * q / n[0], prot: n[3] * q / n[0] };
  }
  function totaux(cat, items) {
    let kcal = 0, prot = 0;
    for (const [a, q] of items) { const n = nutrition(cat, a, q); kcal += n.kcal; prot += n.prot; }
    return { kcal, prot };
  }
  function prixUnitaire(cat, a) {
    const c = cat[a]; if (!c || c.prix == null) return 0;
    return c.vrac ? c.prix / 1000 / (c.rend || 1) : c.prix / c.cond;
  }
  const coutItems = (cat, items) => items.reduce((s, [a, q]) => s + prixUnitaire(cat, a) * q, 0);
  const portionsRef = r => r.portions[REF_GRANDE] || Object.values(r.portions)[0] || [];
  const aProteineAnimale = (cat, r) => portionsRef(r).some(([a]) => cat[a] && cat[a].animal);

  /* ---------- Objectifs d'une personne ---------- */
  // Mifflin-St Jeor × activité ; perte de poids : 500 kcal de moins par jour (environ 0,45 kg par semaine), jamais plus
  // de 25 % du maintien ni sous un plancher (1 200 kcal pour une femme, 1 500 pour un homme). Pas de déficit avant
  // 18 ans ni quand la personne l'a demandé (grossesse, raison médicale). Protéines : 1,4 g par kg de poids visé.
  const ACTIVITE = { sedentaire: 1.2, leger: 1.375, modere: 1.55, actif: 1.725 };
  function objectifs(p) {
    if (p.kcalMin && p.kcalMax && p.prot) return { kcalMin: p.kcalMin, kcalMax: p.kcalMax, prot: p.prot, manuel: true };
    const poids = +p.poids || 70, taille = +p.taille || 170, age = +p.age || 35, homme = p.sexe === "h";
    const maintien = (10 * poids + 6.25 * taille - 5 * age + (homme ? 5 : -161)) * (ACTIVITE[p.activite] || ACTIVITE.leger);
    const cible = +p.cible || poids, plancher = homme ? 1500 : 1200;
    let centre = maintien, rythme = 0;
    if (!p.sansRegime && age >= 18 && cible < poids - 0.5) { const d = Math.min(500, maintien * 0.25); centre = Math.max(plancher, maintien - d); rythme = -(maintien - centre) * 7 / 7700; }
    else if (cible > poids + 0.5) { centre = maintien + 250; rythme = 250 * 7 / 7700; }
    const prot = Math.round(1.4 * (cible > poids ? cible : Math.min(poids, Math.max(cible, poids * 0.85))));
    return { kcalMin: Math.round(centre - 50), kcalMax: Math.round(centre + 50), prot, maintien: Math.round(maintien), rythmeKgSemaine: r2(rythme) };
  }
  const refDe = obj => (obj.kcalMin + obj.kcalMax) / 2 >= SEUIL_REF ? REF_GRANDE : REF_PETITE;

  /* ---------- Calendrier et courses ---------- */
  // debut : Date (UTC) ; n jours ; joursCourses : dates ISO des courses dans la période (peut être vide).
  function calendrier(debut, n, joursCourses) {
    const dates = []; for (let j = 1; j <= n; j++) dates.push(plus(debut, j - 1));
    const jc = []; for (let j = 1; j <= n; j++) if ((joursCourses || []).includes(iso(dates[j - 1]))) jc.push(j);
    const age = j => { const c = jc.filter(x => x <= j).slice(-1)[0]; return c != null ? j - c : j - 1; };
    const periodes = jc.map((c, i) => ({ id: i + 1, debut: c, fin: (jc[i + 1] || n + 1) - 1 }));
    return { n, dates, jc, age, periodes };
  }
  // Jours de courses : chaque semaine, le jour choisi (0 = dimanche … 6 = samedi), dans la période.
  function joursDeCourses(debutISO, n, jourSemaine) {
    const d0 = dateISO(debutISO), l = [];
    for (let j = 0; j < n; j++) { const d = plus(d0, j); if (d.getUTCDay() === jourSemaine) l.push(iso(d)); }
    return l;
  }

  /* ---------- Bibliothèque ---------- */
  const famille = r => r.famille || (r.nom || r.id).split(/[,(+]/)[0].trim().toLowerCase();
  const slug = s => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  // Le petit-déjeuner d'origine a deux versions (une par personne du foyer d'origine) : ce sont ici deux formules,
  // « sucré » et « salé », que chaque personne choisit.
  function formulesPetitDej(recettes) {
    const r = recettes.find(x => x.repas.includes("pdj"));
    if (!r) return {};
    const nom = r.nomParPersonne || {};
    return {
      sucre: { id: "pdj-sucre", nom: nom[REF_GRANDE] || r.nom, repas: ["pdj"], tags: [], portions: { [REF_GRANDE]: r.portions[REF_GRANDE], [REF_PETITE]: r.portions[REF_GRANDE] } },
      sale: { id: "pdj-sale", nom: nom[REF_PETITE] || r.nom, repas: ["pdj"], tags: [], portions: { [REF_GRANDE]: r.portions[REF_PETITE], [REF_PETITE]: r.portions[REF_PETITE] } },
    };
  }
  function deplierVariantes(recettes, cat, exclus) {
    const ex = new Set(exclus || []), out = [];
    const refs = [REF_GRANDE, REF_PETITE];
    const permis = r => !refs.some(p => (r.portions[p] || []).some(([a]) => ex.has(a)));
    for (const r of recettes) {
      if (r.repas.includes("pdj")) continue;
      const fam = famille(r), base = Object.assign({}, r, { famille: fam });
      if (permis(base)) out.push(base);
      for (const v of r.variantes || []) for (const w of v.vers || []) {
        const portions = {};
        for (const p of refs) portions[p] = (r.portions[p] || []).flatMap(([a, q]) => {
          if (a !== v.de) return [[a, q]];
          if (!w.a) return [];
          const x = q * (w.f || 1);
          return [[w.a, UNITES_ENTIERES.has(w.a) ? Math.max(1, Math.round(x)) : Math.max(5, arrondi(x, 5))]];
        });
        let tags = (r.tags || []).slice();
        if (cat) { const poisson = portions[REF_GRANDE].some(([a]) => cat[a] && cat[a].rayon === "Poisson"); tags = tags.filter(t => t !== "poisson").concat(poisson ? ["poisson"] : []); }
        const x = Object.assign({}, r, { id: r.id + "~" + slug(w.a || "sans " + v.de), nom: w.nom || r.nom, famille: fam, portions, tags, base: r.id, variante: { de: v.de, vers: w.a || null } });
        delete x.variantes;
        if (permis(x)) out.push(x);
      }
    }
    return out;
  }

  function penaliteFrais(cat, r, age) {
    let s = 0;
    for (const [a] of portionsRef(r)) {
      const c = cat[a]; if (!c || !c.conservation) continue;
      const depasse = age - c.conservation.jours + 1;
      if (depasse > 0) s += Math.min(1.5, 0.5 * depasse);
    }
    return s;
  }
  function repartir(candidats, n, N) {
    if (candidats.length <= n) return candidats.slice();
    const ecartMin = Math.max(2, Math.floor(N / n) - 2);
    const choix = [];
    for (let i = 0; i < n; i++) {
      const cible = (i + 0.5) * N / n;
      const libres = candidats.filter(c => !choix.includes(c));
      const loin = libres.filter(c => choix.every(x => Math.abs(x - c) >= ecartMin));
      const pool = loin.length ? loin : libres;
      choix.push(pool.reduce((b, c) => Math.abs(c - cible) < Math.abs(b - cible) ? c : b));
    }
    return choix.sort((x, y) => x - y);
  }

  /* ---------- Composition du planning ---------- */
  function composer(ctx) {
    const { cat, recettes, reglages, cal, alea, poidsCout, quotas, convives } = ctx;
    const principaux = recettes.filter(r => (r.repas.includes("dej") || r.repas.includes("din")) && aProteineAnimale(cat, r));
    const plats = principaux.filter(r => !r.tags.includes("restes"));
    const restes = principaux.filter(r => r.tags.includes("restes") && r.suit);
    const desserts = recettes.filter(r => r.repas.includes("des"));
    const ecart = reglages.ecartMinJours || 5;
    const N = cal.n;
    const avantCourse = cal.jc.length ? cal.jc[0] - 1 : (ctx.toutSurStock ? N : 0);
    const grille = {};
    const place = (j, k, r) => { grille[`${j}-${k}`] = r; };
    const libre = (j, k) => j >= 1 && j <= N && !grille[`${j}-${k}`];
    const usages = r => Object.values(grille).filter(x => famille(x) === famille(r)).length;
    const historique = (ctx.historique || []).map(h => ({ j: h.j, r: recettes.find(x => x.id === h.recette) })).filter(h => h.r);
    const tropProche = (r, j) => Object.entries(grille).some(([cle, x]) => famille(x) === famille(r) && Math.abs(+cle.split("-")[0] - j) < ecart)
      || historique.some(h => famille(h.r) === famille(r) && j - h.j < ecart);
    // quantités pour toute la tablée : une portion de référence par convive (grande ou petite selon la personne)
    const besoinTablee = (r, a) => convives.reduce((s, ref) => s + (r.portions[ref] || []).filter(([x]) => x === a).reduce((t, [, q]) => t + q, 0), 0);
    const coutRef = r => convives.reduce((s, ref) => s + coutItems(cat, r.portions[ref] || []), 0);
    const coutMoyen = plats.reduce((s, r) => s + coutRef(r), 0) / Math.max(1, plats.length);
    const principal = (r, role) => {
      const it = portionsRef(r).filter(([a]) => cat[a] && cat[a].role === role).sort((x, y) => y[1] - x[1]);
      return it.length ? it[0][0] : null;
    };
    const stockConnu = Object.keys(ctx.stockDepart).length > 0;
    const stockDispo = Object.assign({}, ctx.stockDepart);
    const consommer = r => { for (const [a] of portionsRef(r)) if (stockDispo[a] != null) stockDispo[a] -= besoinTablee(r, a); };

    function score(r, j, k) {
      if (tropProche(r, j)) return -Infinity;
      let s = alea() * 1.2;
      s -= penaliteFrais(cat, r, cal.age(j));
      const autre = grille[`${j}-${k === "dej" ? "din" : "dej"}`];
      if (autre) {
        if (principal(autre, "proteine") === principal(r, "proteine")) s -= 1.5;
        if (principal(autre, "feculent") === principal(r, "feculent")) s -= 0.5;
      }
      s -= 1.5 * usages(r);
      s -= poidsCout * (coutRef(r) / coutMoyen - 1);
      for (const [a] of portionsRef(r)) if (stockDispo[a] != null && stockDispo[a] >= besoinTablee(r, a) * 1.5) s += ctx.poidsStock != null ? ctx.poidsStock : 1.5;
      if (ctx.penaliteManque && stockConnu)
        for (const [a] of portionsRef(r)) if (!(stockDispo[a] >= besoinTablee(r, a))) s -= ctx.penaliteManque;
      if (j <= avantCourse && stockConnu)
        for (const [a] of portionsRef(r)) if (!(stockDispo[a] >= besoinTablee(r, a))) s -= 2;
      return s;
    }
    function meilleur(liste, j, k) {
      let top = null, best = -Infinity;
      for (const r of liste) { const v = score(r, j, k); if (v > best) { best = v; top = r; } }
      return top;
    }
    function placerAvecRestes(j, k, r) {
      place(j, k, r); consommer(r);
      const suite = restes.find(x => x.suit === r.id);
      if (!suite) return;
      for (let d = k === "dej" ? 0 : 1; d <= Math.max(1, suite.delaiMaxJours || 0); d++) {
        if (libre(j + d, "din") && !tropProche(suite, j + d)) { place(j + d, "din", suite); consommer(suite); return; }
      }
    }
    // jours où le foyer ne mange pas à la maison à midi (cantine, travail) : pas de déjeuner prévu
    const sansDej = new Set(ctx.joursSansDejeuner || []);
    const weekends = [];
    for (let j = 1; j <= N; j++) { const w = cal.dates[j - 1].getUTCDay(); if (w === 0 || w === 6) weekends.push(j); }
    const apres = weekends.filter(j => j > avantCourse);
    const joursPlaisir = repartir(apres.length >= quotas.plaisir ? apres : weekends, quotas.plaisir, N);
    const plaisirs = plats.filter(r => r.tags.includes("plaisir"));
    for (const j of joursPlaisir) { const k = sansDej.has(j) ? "din" : "dej"; const r = meilleur(plaisirs, j, k) || meilleur(plats, j, k); if (r) placerAvecRestes(j, k, r); }
    const poissons = plats.filter(r => r.tags.includes("poisson") && !r.tags.includes("plaisir"));
    const dejaPoisson = Object.values(grille).filter(r => (r.tags || []).includes("poisson")).length;
    const nPoisson = Math.max(0, quotas.poisson - dejaPoisson);
    for (let i = 0; i < nPoisson; i++) {
      let j = Math.min(N, Math.max(1, Math.round((i + 0.5) * N / nPoisson)));
      let k = i % 2 ? "dej" : "din";
      if (sansDej.has(j)) k = "din";
      for (let d = 0; d < N && !libre(j, k); d++) { const alt = k === "dej" ? "din" : "dej"; if (libre(j, alt) && !(alt === "dej" && sansDej.has(j))) { k = alt; break; } j = j % N + 1; }
      const r = meilleur(poissons, j, k); if (r) placerAvecRestes(j, k, r);
    }
    const courants = plats.filter(r => !r.tags.includes("poisson") && !r.tags.includes("plaisir"));
    for (let j = 1; j <= N; j++) for (const k of ["dej", "din"]) {
      if (!libre(j, k) || (k === "dej" && sansDej.has(j))) continue;
      const r = meilleur(courants, j, k) || meilleur(plats, j, k);
      if (r) placerAvecRestes(j, k, r);
    }
    if (ctx.avecDessert !== false) {
      const hors = desserts.filter(r => !/glace/i.test(r.nom || ""));
      const glace = desserts.find(r => /glace/i.test(r.nom || ""));
      const faits = {};
      for (let j = 1; j <= N; j++) {
        if (glace && joursPlaisir.includes(j)) { place(j, "des", glace); continue; }
        let top = null, best = -Infinity;
        for (const r of hors) {
          let s = -(faits[r.id] || 0) - penaliteFrais(cat, r, cal.age(j));
          const hier = grille[`${j - 1}-des`]; if (hier && hier.id === r.id) s -= 0.7;
          s += alea() * 0.6;
          if (s > best) { best = s; top = r; }
        }
        if (top) { place(j, "des", top); faits[top.id] = (faits[top.id] || 0) + 1; }
      }
    }
    return { grille, joursPlaisir };
  }

  function grilleDepuis(ids, recettes) {
    const grille = {}, joursPlaisir = [];
    for (const [cle, id] of Object.entries(ids)) {
      const r = recettes.find(x => x.id === id); if (!r) continue;
      grille[cle] = r;
      const [j, k] = cle.split("-");
      if ((k === "dej" || k === "din") && (r.tags || []).includes("plaisir") && !joursPlaisir.includes(+j)) joursPlaisir.push(+j);
    }
    return { grille, joursPlaisir: joursPlaisir.sort((a, b) => a - b) };
  }
  const grilleDuPlan = periode => Object.fromEntries(periode.plan.flatMap(j => j.meals.filter(m => m.k !== "pdj").map(m => [`${j.d}-${m.k}`, m.recette])));

  /* ---------- Portions ---------- */
  function portionsDuJour(cat, repas, obj) {
    const items = {};
    for (const k of Object.keys(repas)) items[k] = repas[k].map(([a, q]) => [a, q]);
    const principaux = ["dej", "din"].filter(k => items[k]);
    const jour = () => totaux(cat, Object.values(items).flat());
    const deRole = role => principaux.flatMap(k => items[k].filter(([a]) => cat[a] && cat[a].role === role));
    const echelle = (role, f) => { for (const k of principaux) items[k] = items[k].map(([a, q]) => [a, cat[a] && cat[a].role === role ? q * f : q]); };
    const protRole = totaux(cat, deRole("proteine")).prot;
    let t = jour();
    if (protRole > 0) {
      const f = Math.min(1.4, Math.max(0.6, 1 + (obj.prot * 1.02 - t.prot) / protRole));
      if (t.prot < obj.prot || t.prot > obj.prot * 1.15) echelle("proteine", f);
    }
    t = jour();
    const kFec = totaux(cat, deRole("feculent")).kcal;
    if (kFec > 0) echelle("feculent", Math.min(1.6, Math.max(0.5, 1 + ((obj.kcalMin + obj.kcalMax) / 2 - t.kcal) / kFec)));
    return arrondir(items);
  }
  function arrondir(items) {
    const out = {};
    for (const k of Object.keys(items)) out[k] = items[k].map(([a, q]) => [a, UNITES_ENTIERES.has(a) ? Math.max(1, Math.round(q)) : Math.max(5, arrondi(q, 5))]);
    return out;
  }
  // Portion d'un invité : la moyenne des personnes du foyer, ingrédient par ingrédient.
  function portionInvite(listes) {
    const q = {};
    for (const l of listes) for (const [a, x] of l) q[a] = (q[a] || 0) + x / listes.length;
    return Object.entries(q);
  }

  /* ---------- Courses ---------- */
  function listeCourses(ctx, plan) {
    const { cat, cal, invites, ids } = ctx;
    const N = cal.n;
    const QUI = invites > 0 ? ids.concat("invites") : ids;
    const conso = [];
    for (let j = 1; j <= N; j++) {
      const c = {}; for (const p of QUI) c[p] = {};
      for (const m of plan[j - 1].meals) for (const p of QUI) for (const [a, q] of m.items[p] || []) c[p][a] = (c[p][a] || 0) + q * (p === "invites" ? invites : 1);
      conso.push(c);
    }
    const besoin = (a, d1, d2, p) => { let s = 0; for (let j = d1; j <= d2; j++) { const c = conso[j - 1]; for (const pp of p ? [p] : QUI) s += c[pp][a] || 0; } return s; };
    const produits = [...new Set(conso.flatMap(c => QUI.flatMap(p => Object.keys(c[p]))))];
    const stock = {};
    for (const a of produits) stock[a] = ctx.stockDepart[a] || 0;
    const ruptures = [], fraisAVerifier = [];
    // avant la première course (ou toute la période s'il n'y en a pas) : ce qui manque au stock est à acheter tout de suite
    const avant = cal.jc.length ? cal.jc[0] - 1 : N;
    const aCompleter = [];
    for (const a of produits) {
      const b = besoin(a, 1, avant), c = cat[a];
      if (b > stock[a] + 1e-6 && c) {
        const manque = b - stock[a];
        let buy, est;
        if (c.vrac) { const pas = c.pasAchat || 50; buy = Math.ceil(manque / (c.rend || 1) / pas - 1e-9) * pas; est = buy / 1000 * (c.prix || 0); stock[a] += buy * (c.rend || 1); }
        else { buy = Math.ceil(manque / c.cond - 1e-9); est = buy * (c.prix || 0); stock[a] += buy * c.cond; }
        const need = {}; for (const p of QUI) need[p] = r2(besoin(a, 1, avant, p));
        aCompleter.push({ a, buy, est: r2(est), manque: r2(manque), need });
      }
      stock[a] = Math.max(0, stock[a] - b);
    }
    const courses = [];
    if (aCompleter.length) {
      const d1 = cal.dates[0], d2 = cal.dates[avant - 1] || cal.dates[0];
      courses.push({ id: 0, date: iso(d1), jourPlan: 1, titre: cal.jc.length ? "Avant la première course" : "À compléter", jour: nomJour(d1),
        couvre: `du ${court(d1)} au ${court(d2)}`, complement: true, items: aCompleter.sort((x, y) => produits.indexOf(x.a) - produits.indexOf(y.a)) });
    }
    for (const per of cal.periodes) {
      const items = [];
      if (per.id > 1) {
        const ecoule = per.debut - cal.periodes[per.id - 2].debut;
        for (const a of produits) {
          const c = cat[a];
          if (c && c.conservation && c.conservation.frais && stock[a] > 0.5 && ecoule >= c.conservation.jours) fraisAVerifier.push({ a, course: per.id, q: r2(stock[a]) });
        }
      }
      for (const a of produits) {
        const c = cat[a]; if (!c) continue;
        const b = besoin(a, per.debut, per.fin);
        const manque = b - stock[a];
        let buy = 0, est = 0;
        if (manque > 1e-6) {
          if (c.vrac) { const pas = c.pasAchat || 50; buy = Math.ceil(manque / (c.rend || 1) / pas - 1e-9) * pas; est = buy / 1000 * (c.prix || 0); stock[a] += buy * (c.rend || 1); }
          else { buy = Math.ceil(manque / c.cond - 1e-9); est = buy * (c.prix || 0); stock[a] += buy * c.cond; }
        }
        const need = {}; for (const p of QUI) need[p] = r2(besoin(a, per.debut, per.fin, p));
        stock[a] -= b;
        if (stock[a] < -1e-6) { ruptures.push({ a, course: per.id, q: r2(-stock[a]) }); stock[a] = 0; }
        if (buy > 0) items.push({ a, buy, est: r2(est), need });
      }
      const d1 = cal.dates[per.debut - 1], d2 = cal.dates[per.fin - 1];
      courses.push({ id: per.id, date: iso(d1), jourPlan: per.debut, titre: `Course ${per.id}`, jour: nomJour(d1), couvre: `du ${court(d1)} au ${court(d2)}`,
        items: items.sort((x, y) => produits.indexOf(x.a) - produits.indexOf(y.a)) });
    }
    const stockFin = {};
    for (const a of produits) if (stock[a] > 0.5) stockFin[a] = r2(stock[a]);
    return { courses, conso, ruptures, stockFin, fraisAVerifier, QUI };
  }

  /* ---------- Point d'entrée ---------- */
  // entrees : { catalogue, recettes, reglages, personnes: [{ id, nom, sexe, age, taille, poids, cible, activite, pdj, sansRegime,
  //             kcalMin?, kcalMax?, prot? }], debut ("aaaa-mm-jj"), jours, joursCourses? (dates ISO), invites?, budget?,
  //             graine?, stockDepart?, exclureProduits?, quotas?, historique?, grilleImposee?, priorite? ("stock"), avecDessert?,
  //             joursSansDejeuner? }
  function composer_periode(entrees) {
    const { catalogue: cat, recettes, reglages } = entrees;
    const debut = dateISO(entrees.debut);
    const n = Math.max(1, Math.min(62, Math.round(entrees.jours || 7)));
    const invites = Math.max(0, Math.round(entrees.invites || 0));
    const personnes = (entrees.personnes || []).length ? entrees.personnes : [{ id: "p1", nom: "Moi" }];
    const ids = personnes.map(p => p.id);
    const obj = {}, ref = {};
    for (const p of personnes) { obj[p.id] = objectifs(p); ref[p.id] = refDe(obj[p.id]); }
    const convives = personnes.map(p => ref[p.id]).concat(Array(invites).fill(personnes.length > 1 ? REF_GRANDE : ref[ids[0]]));
    const cal = calendrier(debut, n, entrees.joursCourses || []);
    const base = reglages.quotas || { poisson: 8, plaisir: 6 };
    const quotas = entrees.quotas || { poisson: Math.round(base.poisson * n / 30), plaisir: Math.round(base.plaisir * n / 30) };
    const budget = entrees.budget != null && entrees.budget !== "" ? +entrees.budget : null;
    const recs = deplierVariantes(recettes, cat, entrees.exclureProduits);
    const pdj = formulesPetitDej(recettes);
    const surStock = entrees.priorite === "stock";
    let res = null;
    const passes = entrees.grilleImposee ? 1 : (budget != null ? (entrees.passes || 6) : 1), pasCout = entrees.pasCout || 0.8;
    for (let passe = 0; passe < passes; passe++) {
      const historique = (entrees.historique || []).map(h => ({ j: Math.round((dateISO(h.date) - debut) / JOUR_MS) + 1, recette: h.recette }));
      const ctx = { cat, recettes: recs, reglages, cal, quotas, invites, ids, convives, historique, stockDepart: entrees.stockDepart || {},
        poidsStock: surStock ? 3 : entrees.poidsStock, penaliteManque: surStock ? 2.5 : (entrees.penaliteManque || 0), toutSurStock: surStock,
        avecDessert: entrees.avecDessert, joursSansDejeuner: entrees.joursSansDejeuner,
        alea: hasard((entrees.graine || 1) + passe * 7919), poidsCout: 0.5 + passe * pasCout };
      const { grille, joursPlaisir } = entrees.grilleImposee ? grilleDepuis(entrees.grilleImposee, recs) : composer(ctx);
      const plan = [];
      for (let j = 1; j <= n; j++) {
        const parPersonne = {};
        for (const p of personnes) {
          const repas = {};
          const f = pdj[p.pdj || (ref[p.id] === REF_GRANDE ? "sucre" : "sale")];
          if (f && p.pdj !== "aucun") repas.pdj = f.portions[ref[p.id]];
          // petits appétits (enfants, petits gabarits) : toute la portion de référence est réduite d'abord
          const centre = (obj[p.id].kcalMin + obj[p.id].kcalMax) / 2, reduc = ref[p.id] === REF_PETITE && centre < 1350 ? Math.max(0.45, centre / 1400) : 1;
          for (const k of ["dej", "din", "des"]) { const r = grille[`${j}-${k}`]; if (r) repas[k] = r.portions[ref[p.id]].map(([a, q]) => [a, q * reduc]); }
          parPersonne[p.id] = portionsDuJour(cat, repas, obj[p.id]);
        }
        const meals = [];
        if (personnes.some(p => parPersonne[p.id].pdj)) {
          const items = {}, noms = {};
          for (const p of personnes) if (parPersonne[p.id].pdj) { items[p.id] = parPersonne[p.id].pdj; noms[p.id] = pdj[p.pdj || (ref[p.id] === REF_GRANDE ? "sucre" : "sale")].nom; }
          meals.push({ k: "pdj", label: LABELS.pdj, plat: "Petit-déjeuner", noms, items, recette: null });
        }
        for (const k of ["dej", "din", "des"]) {
          const r = grille[`${j}-${k}`]; if (!r) continue;
          const items = {};
          for (const p of personnes) items[p.id] = parPersonne[p.id][k];
          if (invites > 0) items.invites = arrondir({ x: portionInvite(personnes.map(p => items[p.id])) }).x;
          meals.push({ k, label: LABELS[k], plat: r.nom, items, recette: r.id });
        }
        const fish = meals.some(m => m.recette && (grille[`${j}-${m.k}`].tags || []).includes("poisson"));
        plan.push({ d: j, date: iso(cal.dates[j - 1]), tag: joursPlaisir.includes(j) ? "plaisir" : (fish ? "poisson" : ""), fish, meals });
      }
      const cr = listeCourses(ctx, plan);
      const achats = cr.courses.reduce((s, c) => s + c.items.reduce((t, i) => t + i.est, 0), 0);
      if (!res || achats < res.achats) res = { ctx, plan, cr, joursPlaisir, achats };
      if (budget == null || achats <= budget) break;
    }
    const { plan, cr, joursPlaisir, achats } = res;
    const cout = {};
    for (const p of cr.QUI) cout[p] = 0;
    for (const c of cr.conso) for (const p of cr.QUI) for (const [a, q] of Object.entries(c[p])) cout[p] += prixUnitaire(cat, a) * q;
    // part de chaque personne dans la consommation de chaque produit (invités exclus)
    const parts = {}, tot = {};
    for (const c of cr.conso) for (const p of ids) for (const [a, q] of Object.entries(c[p])) { tot[a] = tot[a] || {}; tot[a][p] = (tot[a][p] || 0) + q; }
    for (const [a, t] of Object.entries(tot)) { const s = Object.values(t).reduce((x, y) => x + y, 0); parts[a] = {}; for (const p of ids) parts[a][p] = s ? Math.round((t[p] || 0) / s * 10000) / 10000 : 1 / ids.length; }
    const nut = {}, horsFourchette = [];
    for (const p of ids) {
      let k = 0, pr = 0;
      for (const j of plan) {
        const t = totaux(cat, j.meals.flatMap(m => m.items[p] || [])); k += t.kcal; pr += t.prot;
        if (t.kcal < obj[p].kcalMin - 80 || t.kcal > obj[p].kcalMax + 80 || t.prot < obj[p].prot - 8) horsFourchette.push({ p, d: j.d, kcal: Math.round(t.kcal), prot: Math.round(t.prot) });
      }
      nut[p] = { kcalMoyen: Math.round(k / plan.length), protMoyen: Math.round(pr / plan.length), objectifs: obj[p] };
    }
    const tagsDe = id => ((recs.find(r => r.id === id) || {}).tags || []);
    const compte = tag => plan.reduce((s, j) => s + j.meals.filter(m => (m.k === "dej" || m.k === "din") && tagsDe(m.recette).includes(tag)).length, 0);
    const fin = cal.dates[n - 1];
    const stockUtilise = Object.keys(entrees.stockDepart || {}).filter(a => cr.conso.some(c => cr.QUI.some(p => c[p][a])));
    const periode = {
      version: 1, debut: iso(debut), fin: iso(fin), jours: n, invites,
      titre: `Du ${court(debut)} au ${court(fin)}`,
      personnes: personnes.map(p => ({ id: p.id, nom: p.nom })),
      stockDepart: entrees.stockDepart || {}, parts, plan, courses: cr.courses, graine: entrees.graine || 1,
    };
    const bilan = {
      nutrition: nut,
      quotas: { poisson: compte("poisson"), plaisir: compte("plaisir"), objectif: quotas, joursPlaisir },
      cout: { consommation: Object.fromEntries(Object.entries(cout).map(([p, v]) => [p, r2(v)])), achats: r2(achats), budget,
              parCourse: cr.courses.map(c => ({ id: c.id, titre: c.titre, date: c.date, total: r2(c.items.reduce((t, i) => t + i.est, 0)), articles: c.items.length })) },
      stockUtilise, ruptures: cr.ruptures, fraisAVerifier: cr.fraisAVerifier, horsFourchette, stockFin: cr.stockFin,
      recettesUtilisees: [...new Set(plan.flatMap(j => j.meals.map(m => m.recette).filter(Boolean)))].length,
    };
    return { periode, bilan };
  }

  function avecPrix(catalogue, prix) {
    const cat = {};
    for (const [a, c] of Object.entries(catalogue)) {
      const p = prix && prix[a] != null ? (typeof prix[a] === "object" ? prix[a].prix : prix[a]) : null;
      cat[a] = p != null ? Object.assign({}, c, { prix: p }) : c;
    }
    return cat;
  }

  return { composer: composer_periode, objectifs, joursDeCourses, deplierVariantes, famille, grilleDuPlan, avecPrix, prixUnitaire, totaux, formulesPetitDej, LABELS, CLES };
})();
if (typeof module !== "undefined") module.exports = Moteur;
