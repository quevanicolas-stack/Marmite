/* ============================================================
   Marmite — moteur de composition d'une période (sans IA)
   Par défaut un mois calendaire ; on peut choisir la date de début, le nombre de jours,
   le nombre d'invités et le budget.
   Entrées : catalogue, recettes, réglages, profils, stock de départ.
   Sortie : un mois au format de donnees/mois/<aaaa-mm>.json (plan, courses, share)
            + un bilan (nutrition, coûts, quotas, alertes).
   Fonctionne dans le navigateur (objet global Moteur) et sous Node (module.exports).
   ============================================================ */
const Moteur = (() => {
  const PERSONNES = ["nicolas", "aurelie"];
  const LABELS = { pdj: "Petit-déjeuner", dej: "Déjeuner", din: "Dîner", des: "Dessert" };
  const JOURS_SEM = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  const MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  const UNITES_ENTIERES = new Set(["Œufs", "Wraps", "Pains burger"]);
  const JOUR_MS = 86400000;

  /* ---------- Outils ---------- */
  // Générateur pseudo-aléatoire à graine : même graine, même planning.
  function hasard(graine) {
    let a = graine >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const arrondi = (x, pas) => Math.round(x / pas) * pas;
  const r2 = x => Math.round(x * 100) / 100;
  const dateISO = s => { const [a, m, j] = s.split("-").map(Number); return new Date(Date.UTC(a, m - 1, j)); };
  const iso = d => d.toISOString().slice(0, 10);
  const plus = (d, n) => new Date(d.getTime() + n * JOUR_MS);
  const joursDansMois = d => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
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
  // Prix d'une unité consommée (g, ml, unité) : conditionnement, ou kilo brut en vrac corrigé du rendement.
  function prixUnitaire(cat, a) {
    const c = cat[a]; if (!c || c.prix == null) return 0;
    return c.vrac ? c.prix / 1000 / (c.rend || 1) : c.prix / c.cond;
  }
  const coutItems = (cat, items) => items.reduce((s, [a, q]) => s + prixUnitaire(cat, a) * q, 0);
  // Un plat principal doit contenir une protéine animale (viande, poisson, charcuterie ; les œufs ne comptent pas).
  const aProteineAnimale = (cat, r) => r.portions.nicolas.some(([a]) => cat[a] && cat[a].animal);

  /* ---------- Objectifs ---------- */
  // Les besoins baissent avec le poids : environ 14 kcal par kg (métabolisme de base × activité légère).
  // Les protéines restent calées sur le profil, qui vise le poids objectif.
  function objectifs(profil, poidsActuel) {
    const delta = poidsActuel != null && profil.poids ? poidsActuel - profil.poids : 0;
    const k = Math.round(delta * 14);
    return { kcalMin: profil.kcalMin + k, kcalMax: profil.kcalMax + k, prot: profil.prot };
  }

  /* ---------- Calendrier et courses ---------- */
  // debut : Date (UTC) ; n : nombre de jours ; joursCourses : dates ISO imposées, sinon les jours du mois des réglages.
  function calendrier(debut, n, reglages, joursCourses) {
    const dates = []; for (let j = 1; j <= n; j++) dates.push(plus(debut, j - 1));
    const estCourse = d => joursCourses ? joursCourses.includes(iso(d)) : reglages.courses.jours.includes(d.getUTCDate());
    const jc = []; for (let j = 1; j <= n; j++) if (estCourse(dates[j - 1])) jc.push(j);
    // âge des produits frais au jour j : jours écoulés depuis la dernière course
    // (avant la première course de la période : on remonte le calendrier des réglages)
    const age = j => {
      const c = jc.filter(x => x <= j).slice(-1)[0];
      if (c != null) return j - c;
      for (let k = 1; k <= 62; k++) if (reglages.courses.jours.includes(plus(dates[j - 1], -k).getUTCDate())) return k;
      return 7;
    };
    const periodes = jc.map((c, i) => ({ id: i + 1, debut: c, fin: (jc[i + 1] || n + 1) - 1 }));
    return { n, dates, jc, age, periodes };
  }

  /* ---------- Composition du planning ---------- */
  function composer(ctx) {
    const { cat, recettes, reglages, cal, alea, poidsCout, exclure, quotas } = ctx;
    const actives = recettes.filter(r => !exclure.has(r.id));
    const principaux = actives.filter(r => (r.repas.includes("dej") || r.repas.includes("din")) && aProteineAnimale(cat, r));
    const plats = principaux.filter(r => !r.tags.includes("restes"));
    const restes = principaux.filter(r => r.tags.includes("restes") && r.suit);
    const desserts = actives.filter(r => r.repas.includes("des"));
    const pdj = actives.find(r => r.repas.includes("pdj"));
    const ecart = reglages.ecartMinJours || 5;
    const N = cal.n;
    const avantCourse = cal.jc.length ? cal.jc[0] - 1 : 0;
    const grille = {}; // "j-k" -> recette
    const place = (j, k, r) => { grille[`${j}-${k}`] = r; };
    const libre = (j, k) => j >= 1 && j <= N && !grille[`${j}-${k}`];
    // les variantes d'un même plat (« Bœuf sauté asiatique, riz, légumes » / « …, poivrons-carottes ») comptent ensemble
    const usages = r => Object.values(grille).filter(x => famille(x) === famille(r)).length;
    const tropProche = (r, j) => Object.entries(grille).some(([cle, x]) => famille(x) === famille(r) && Math.abs(+cle.split("-")[0] - j) < ecart);
    const coutRef = r => PERSONNES.reduce((s, p) => s + coutItems(cat, r.portions[p]), 0);
    const coutMoyen = plats.reduce((s, r) => s + coutRef(r), 0) / Math.max(1, plats.length);
    const principal = (r, role) => {
      const it = r.portions.nicolas.filter(([a]) => cat[a] && cat[a].role === role).sort((x, y) => y[1] - x[1]);
      return it.length ? it[0][0] : null;
    };
    // stock de départ encore disponible : utilisé en priorité, et seul disponible avant la première course
    const stockConnu = Object.keys(ctx.stockDepart).length > 0;
    const stockDispo = Object.assign({}, ctx.stockDepart);
    const besoinRef = (r, a) => PERSONNES.reduce((s, p) => s + r.portions[p].filter(([x]) => x === a).reduce((t, [, q]) => t + q, 0), 0);
    const consommer = r => { for (const p of PERSONNES) for (const [a, q] of r.portions[p]) if (stockDispo[a] != null) stockDispo[a] -= q; };

    function score(r, j, k) {
      if (tropProche(r, j)) return -Infinity;
      let s = alea() * 1.2;
      // produits frais : pénalité si le plat tombe au-delà de leur conservation depuis la dernière course
      s -= penaliteFrais(cat, r, cal.age(j));
      // même protéine ou même féculent deux fois dans la journée
      const autre = grille[`${j}-${k === "dej" ? "din" : "dej"}`];
      if (autre) {
        if (principal(autre, "proteine") === principal(r, "proteine")) s -= 1.5;
        if (principal(autre, "feculent") === principal(r, "feculent")) s -= 0.5;
      }
      s -= 1.5 * usages(r);
      s -= poidsCout * (coutRef(r) / coutMoyen - 1);
      // stock de départ : bonus si le plat l'utilise et qu'il en reste assez
      for (const [a, q] of r.portions.nicolas) if (stockDispo[a] != null && stockDispo[a] >= q * 2) s += 1.5;
      // avant la première course, on vit sur le stock : chaque ingrédient manquant coûte cher
      if (j <= avantCourse && stockConnu)
        for (const [a] of r.portions.nicolas) if (!(stockDispo[a] >= besoinRef(r, a))) s -= 2;
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
      // au dîner qui suit : le jour même si le plat est un déjeuner, sinon dans le délai permis
      for (let d = k === "dej" ? 0 : 1; d <= Math.max(1, suite.delaiMaxJours || 0); d++) {
        if (libre(j + d, "din") && !tropProche(suite, j + d)) { place(j + d, "din", suite); consommer(suite); return; }
      }
    }

    // 1. repas plaisir : déjeuners du week-end, répartis sur la période (hors jours avant la première course si possible)
    const weekends = [];
    for (let j = 1; j <= N; j++) { const w = cal.dates[j - 1].getUTCDay(); if (w === 0 || w === 6) weekends.push(j); }
    const apres = weekends.filter(j => j > avantCourse);
    const joursPlaisir = repartir(apres.length >= quotas.plaisir ? apres : weekends, quotas.plaisir, N);
    const plaisirs = plats.filter(r => r.tags.includes("plaisir"));
    for (const j of joursPlaisir) { const r = meilleur(plaisirs, j, "dej") || meilleur(plats, j, "dej"); if (r) placerAvecRestes(j, "dej", r); }

    // 2. poisson : réparti régulièrement, en alternant déjeuner et dîner
    const poissons = plats.filter(r => r.tags.includes("poisson"));
    for (let i = 0; i < quotas.poisson; i++) {
      let j = Math.min(N, Math.max(1, Math.round((i + 0.5) * N / quotas.poisson)));
      let k = i % 2 ? "dej" : "din";
      for (let d = 0; d < N && !libre(j, k); d++) { const alt = k === "dej" ? "din" : "dej"; if (libre(j, alt)) { k = alt; break; } j = j % N + 1; }
      const r = meilleur(poissons, j, k); if (r) placerAvecRestes(j, k, r);
    }

    // 3. le reste, jour par jour
    const courants = plats.filter(r => !r.tags.includes("poisson") && !r.tags.includes("plaisir"));
    for (let j = 1; j <= N; j++) for (const k of ["dej", "din"]) {
      if (!libre(j, k)) continue;
      const r = meilleur(courants, j, k) || meilleur(plats, j, k);
      if (r) placerAvecRestes(j, k, r);
    }

    // 4. desserts : glace les jours plaisir, sinon la répartition du mois de référence, fruits frais près des courses
    const poidsDes = {};
    for (const r of desserts) poidsDes[r.id] = r.frequenceReference || 1;
    const hors = desserts.filter(r => !/glace/i.test(r.nom || ""));
    const glace = desserts.find(r => /glace/i.test(r.nom || ""));
    const totalPoids = hors.reduce((s, r) => s + poidsDes[r.id], 0);
    const faits = {};
    for (let j = 1; j <= N; j++) {
      if (glace && joursPlaisir.includes(j)) { place(j, "des", glace); continue; }
      let top = null, best = -Infinity;
      const places = Object.values(faits).reduce((s, v) => s + v, 0) + 1;
      for (const r of hors) {
        let s = poidsDes[r.id] / totalPoids * places - (faits[r.id] || 0);
        s -= penaliteFrais(cat, r, cal.age(j));
        const hier = grille[`${j - 1}-des`]; if (hier && hier.id === r.id) s -= 0.7;
        s += alea() * 0.3;
        if (s > best) { best = s; top = r; }
      }
      if (top) { place(j, "des", top); faits[top.id] = (faits[top.id] || 0) + 1; }
    }
    if (pdj) for (let j = 1; j <= N; j++) place(j, "pdj", pdj);
    return { grille, joursPlaisir };
  }

  // Choisit n jours dans la liste en maximisant l'écart entre eux.
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

  // Famille d'un plat : son nom avant la première virgule ou parenthèse.
  const famille = r => (r.nom || r.id).split(/[,(+]/)[0].trim().toLowerCase();

  // Produits frais utilisés au-delà de leur conservation depuis la dernière course :
  // pénalité qui grandit avec le dépassement, plafonnée par produit.
  function penaliteFrais(cat, r, age) {
    let s = 0;
    for (const [a] of r.portions.nicolas) {
      const c = cat[a]; if (!c || !c.conservation) continue;
      const depasse = age - c.conservation.jours + 1;
      if (depasse > 0) s += Math.min(1.5, 0.5 * depasse);
    }
    return s;
  }

  /* ---------- Portions ---------- */
  // Par personne et par jour : protéines des plats principaux calées sur l'objectif de protéines,
  // puis féculents calés sur le milieu de la fourchette de kcal. Légumes et desserts inchangés.
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
      const cible = obj.prot * 1.02;
      const f = Math.min(1.4, Math.max(0.85, 1 + (cible - t.prot) / protRole));
      if (t.prot < obj.prot || t.prot > obj.prot * 1.15) echelle("proteine", f);
    }
    t = jour();
    const kFec = totaux(cat, deRole("feculent")).kcal;
    if (kFec > 0) {
      const cible = (obj.kcalMin + obj.kcalMax) / 2;
      echelle("feculent", Math.min(1.6, Math.max(0.5, 1 + (cible - t.kcal) / kFec)));
    }
    return arrondir(items);
  }
  // arrondis : unités entières, 5 g ou 5 ml sinon
  function arrondir(items) {
    const out = {};
    for (const k of Object.keys(items)) out[k] = items[k].map(([a, q]) => [a, UNITES_ENTIERES.has(a) ? Math.max(1, Math.round(q)) : Math.max(5, arrondi(q, 5))]);
    return out;
  }
  // Portion d'un invité : la moyenne de Nicolas et d'Aurélie, ingrédient par ingrédient.
  function portionInvite(itN, itA) {
    const q = {};
    for (const [a, x] of itN) q[a] = (q[a] || 0) + x / 2;
    for (const [a, x] of itA) q[a] = (q[a] || 0) + x / 2;
    return Object.entries(q);
  }

  /* ---------- Courses ---------- */
  function listeCourses(ctx, plan) {
    const { cat, reglages, cal, invites } = ctx;
    const N = cal.n;
    const QUI = invites > 0 ? PERSONNES.concat("invites") : PERSONNES;
    // consommation par jour, par convive et par produit (repas + hors repas)
    const conso = [];
    for (let j = 1; j <= N; j++) {
      const c = { nicolas: {}, aurelie: {}, invites: {} };
      for (const m of plan[j - 1].meals) for (const p of QUI) for (const [a, q] of m.items[p] || []) c[p][a] = (c[p][a] || 0) + q * (p === "invites" ? invites : 1);
      for (const h of reglages.horsRepas || []) for (const p of PERSONNES) if (h.parJour[p]) c[p][h.a] = (c[p][h.a] || 0) + h.parJour[p];
      conso.push(c);
    }
    const besoin = (a, d1, d2, p) => { let s = 0; for (let j = d1; j <= d2; j++) { const c = conso[j - 1]; for (const pp of p ? [p] : QUI) s += c[pp][a] || 0; } return s; };
    const produits = [...new Set(conso.flatMap(c => QUI.flatMap(p => Object.keys(c[p]))))];
    const stock = {};
    for (const a of produits) stock[a] = ctx.stockDepart[a] || 0;
    const manquesAvant = [], ruptures = [], fraisAVerifier = [];

    // avant la première course : on vit sur le stock
    const avant = cal.jc.length ? cal.jc[0] - 1 : N;
    for (const a of produits) {
      const b = besoin(a, 1, avant);
      if (b > stock[a] + 1e-6) manquesAvant.push({ a, q: r2(b - stock[a]) });
      stock[a] = Math.max(0, stock[a] - b);
    }

    const courses = [];
    for (const per of cal.periodes) {
      const items = [];
      // frais restant de la période précédente et plus vieux que sa conservation estimée :
      // signalé pour l'inventaire, jamais compté en perte d'office (c'est l'utilisateur qui le jette ou non)
      if (per.id > 1) {
        const ecoule = per.debut - cal.periodes[per.id - 2].debut;
        for (const a of produits) {
          const c = cat[a];
          if (c && c.conservation && c.conservation.frais && stock[a] > 0.5 && ecoule >= c.conservation.jours)
            fraisAVerifier.push({ a, course: per.id, q: r2(stock[a]) });
        }
      }
      for (const a of produits) {
        const c = cat[a]; if (!c) continue;
        // chaque course couvre sa période ; les restes passent à la suivante
        const b = besoin(a, per.debut, per.fin);
        const manque = b - stock[a];
        let buy = 0, est = 0;
        if (manque > 1e-6) {
          if (c.vrac) { const pas = c.pasAchat || 50; buy = Math.ceil(manque / (c.rend || 1) / pas - 1e-9) * pas; est = buy / 1000 * (c.prix || 0); stock[a] += buy * (c.rend || 1); }
          else { buy = Math.ceil(manque / c.cond - 1e-9); est = buy * (c.prix || 0); stock[a] += buy * c.cond; }
        }
        const nd = {}; for (const p of QUI) nd[p] = besoin(a, per.debut, per.fin, p);
        stock[a] -= b;
        if (stock[a] < -1e-6) { ruptures.push({ a, course: per.id, q: r2(-stock[a]) }); stock[a] = 0; }
        if (buy > 0) {
          const it = { a, buy, est: r2(est), needN: r2(nd.nicolas), needA: r2(nd.aurelie) };
          if (invites > 0) it.needI = r2(nd.invites);
          items.push(it);
        }
      }
      const d1 = cal.dates[per.debut - 1], d2 = cal.dates[per.fin - 1];
      courses.push({
        id: per.id, date: iso(d1), jourPlan: per.debut, titre: `Course ${per.id}`,
        jour: nomJour(d1), couvre: `du ${court(d1)} au ${court(d2)}`,
        items: items.sort((x, y) => produits.indexOf(x.a) - produits.indexOf(y.a)),
      });
    }
    const stockFin = {};
    for (const a of produits) if (stock[a] > 0.5) stockFin[a] = r2(stock[a]);
    return { courses, conso, manquesAvant, ruptures, stockFin, fraisAVerifier, QUI };
  }

  /* ---------- Point d'entrée ---------- */
  // entrees : { catalogue, recettes, reglages, debut ("aaaa-mm-jj") ou annee + mois, jours?, invites?, budget?,
  //             quotas?, joursCourses?, graine?, stockDepart?, profils?, poidsActuels?, exclure?, moisReference? }
  function composerMois(entrees) {
    const { catalogue, recettes, reglages } = entrees;
    const cat = catalogue;
    const debut = entrees.debut ? dateISO(entrees.debut) : new Date(Date.UTC(entrees.annee, entrees.mois - 1, 1));
    const moisEntier = debut.getUTCDate() === 1 && (entrees.jours == null || entrees.jours === joursDansMois(debut));
    const n = entrees.jours || joursDansMois(debut);
    const invites = Math.max(0, Math.round(entrees.invites || 0));
    const profils = {};
    for (const p of PERSONNES) {
      const base = Object.assign({}, reglages.personnes[p], (entrees.profils || {})[p] || {});
      profils[p] = Object.assign(base, objectifs(base, (entrees.poidsActuels || {})[p]));
    }
    const cal = calendrier(debut, n, reglages, entrees.joursCourses);
    const exclure = new Set(entrees.exclure || []);
    // quotas : ceux des réglages pour un mois entier, au prorata sinon
    const quotas = entrees.quotas || (moisEntier ? reglages.quotas
      : { poisson: Math.round(reglages.quotas.poisson * n / joursDansMois(debut)), plaisir: Math.round(reglages.quotas.plaisir * n / joursDansMois(debut)) });
    // budget des achats de la période : saisi, sinon celui des profils ramené à la durée (invités non compris)
    const budget = entrees.budget != null ? entrees.budget
      : PERSONNES.reduce((s, p) => s + profils[p].budget * n / (profils[p].budgetJours || n), 0);

    // fréquence des desserts dans le mois de référence : sert de répartition cible
    const freq = {};
    for (const j of entrees.moisReference ? entrees.moisReference.plan : []) for (const m of j.meals) if (m.k === "des") freq[m.recette] = (freq[m.recette] || 0) + 1;
    const recs = recettes.map(r => Object.assign({}, r, { frequenceReference: freq[r.id] || 1 }));

    // on recompose en donnant plus de poids au coût tant que les achats dépassent le budget
    let res = null;
    for (let passe = 0; passe < 6; passe++) {
      const ctx = { cat, recettes: recs, reglages, cal, exclure, quotas, invites, stockDepart: entrees.stockDepart || {},
        alea: hasard((entrees.graine || 1) + passe * 7919), poidsCout: 0.5 + passe * 0.8 };
      const { grille, joursPlaisir } = composer(ctx);
      const plan = [];
      for (let j = 1; j <= n; j++) {
        const parPersonne = {};
        for (const p of PERSONNES) {
          const repas = {};
          for (const k of ["pdj", "dej", "din", "des"]) { const r = grille[`${j}-${k}`]; if (r) repas[k] = r.portions[p]; }
          parPersonne[p] = portionsDuJour(cat, repas, profils[p]);
        }
        const meals = ["pdj", "dej", "din", "des"].filter(k => grille[`${j}-${k}`]).map(k => {
          const r = grille[`${j}-${k}`];
          const items = { nicolas: parPersonne.nicolas[k], aurelie: parPersonne.aurelie[k] };
          if (invites > 0) items.invites = arrondir({ x: portionInvite(items.nicolas, items.aurelie) }).x;
          return { k, label: LABELS[k], plat: r.nomParPersonne || { nicolas: r.nom, aurelie: r.nom }, items, recette: r.id };
        });
        const fish = meals.some(m => (grille[`${j}-${m.k}`].tags || []).includes("poisson"));
        plan.push({ d: j, date: iso(cal.dates[j - 1]), tag: joursPlaisir.includes(j) ? "plaisir" : (fish ? "poisson" : ""), fish, meals });
      }
      const cr = listeCourses(ctx, plan);
      const achats = cr.courses.reduce((s, c) => s + c.items.reduce((t, i) => t + i.est, 0), 0);
      res = { ctx, plan, cr, joursPlaisir, achats };
      if (achats <= budget) break;
    }

    const { plan, cr, joursPlaisir, achats } = res;
    const cout = {};
    for (const p of cr.QUI) cout[p] = 0;
    for (const c of cr.conso) for (const p of cr.QUI) for (const [a, q] of Object.entries(c[p])) cout[p] += prixUnitaire(cat, a) * q;
    // part de Nicolas dans la consommation du foyer (invités exclus) de chaque produit
    const share = {}, tot = {};
    for (const c of cr.conso) for (const p of PERSONNES) for (const [a, q] of Object.entries(c[p])) { tot[a] = tot[a] || { nicolas: 0, aurelie: 0 }; tot[a][p] += q; }
    for (const [a, t] of Object.entries(tot)) share[a] = t.nicolas + t.aurelie ? Math.round(t.nicolas / (t.nicolas + t.aurelie) * 10000) / 10000 : 0.5;

    // bilan nutritionnel et alertes
    const nut = {}, horsFourchette = [];
    for (const p of PERSONNES) {
      let k = 0, pr = 0;
      for (const j of plan) {
        const t = totaux(cat, j.meals.flatMap(m => m.items[p])); k += t.kcal; pr += t.prot;
        if (t.kcal < profils[p].kcalMin - 50 || t.kcal > profils[p].kcalMax + 50 || t.prot < profils[p].prot - 5)
          horsFourchette.push({ p, d: j.d, kcal: Math.round(t.kcal), prot: Math.round(t.prot) });
      }
      nut[p] = { kcalMoyen: Math.round(k / plan.length), protMoyen: Math.round(pr / plan.length), objectifs: { kcalMin: profils[p].kcalMin, kcalMax: profils[p].kcalMax, prot: profils[p].prot } };
    }
    const fraisTard = [];
    for (const j of plan) for (const m of j.meals) for (const a of new Set(m.items.nicolas.concat(m.items.aurelie).map(([x]) => x))) {
      const c = cat[a]; if (c && c.conservation && res.ctx.cal.age(j.d) >= c.conservation.jours) fraisTard.push({ d: j.d, k: m.k, a });
    }
    const tagsDe = id => (recettes.find(r => r.id === id).tags || []);
    const compte = tag => plan.reduce((s, j) => s + j.meals.filter(m => (m.k === "dej" || m.k === "din") && tagsDe(m.recette).includes(tag)).length, 0);
    const fin = cal.dates[n - 1];
    const moisObj = {
      version: 1,
      id: moisEntier ? iso(debut).slice(0, 7) : `${iso(debut)}_${n}j`,
      titre: moisEntier ? `${MOIS[debut.getUTCMonth()][0].toUpperCase()}${MOIS[debut.getUTCMonth()].slice(1)} ${debut.getUTCFullYear()}` : `Du ${court(debut)} au ${court(fin)} ${fin.getUTCFullYear()}`,
      debut: iso(debut), fin: iso(fin), jours: n, invites,
      note: "Proposition du moteur.", stockDepart: entrees.stockDepart || {}, share, plan, courses: cr.courses,
    };
    const bilan = {
      nutrition: nut,
      quotas: { poisson: compte("poisson"), plaisir: compte("plaisir"), objectif: quotas, joursPlaisir },
      cout: { consommation: Object.fromEntries(Object.entries(cout).map(([p, v]) => [p, r2(v)])), achats: r2(achats), budget: r2(budget),
              parCourse: cr.courses.map(c => ({ id: c.id, date: c.date, total: r2(c.items.reduce((t, i) => t + i.est, 0)), articles: c.items.length })) },
      manquesAvantPremiereCourse: cr.manquesAvant,
      ruptures: cr.ruptures,
      // les petits-déjeuners sont fixes : leurs dépassements sont signalés à part
      fraisAuDelaConservation: fraisTard.filter(x => x.k !== "pdj"),
      fraisAuDelaPetitDejeuner: fraisTard.filter(x => x.k === "pdj"),
      fraisAVerifier: cr.fraisAVerifier,
      horsFourchette,
      stockFin: cr.stockFin,
      recettesUtilisees: [...new Set(plan.flatMap(j => j.meals.map(m => m.recette)))].length,
    };
    return { mois: moisObj, bilan };
  }

  return { composerMois, objectifs, prixUnitaire, totaux, calendrier, portionsDuJour, aProteineAnimale };
})();
if (typeof module !== "undefined") module.exports = Moteur;
