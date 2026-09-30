/* ============================================================
   Marmite — moteur de composition d'un mois (sans IA)
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

  /* ---------- Outils ---------- */
  // Générateur pseudo-aléatoire à graine : même graine, même mois.
  function hasard(graine) {
    let a = graine >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const arrondi = (x, pas) => Math.round(x / pas) * pas;
  const r2 = x => Math.round(x * 100) / 100;
  const dateUTC = (a, m, j) => new Date(Date.UTC(a, m - 1, j));
  const iso = d => d.toISOString().slice(0, 10);
  const nomJour = (a, m, j) => { const d = dateUTC(a, m, j); return `${JOURS_SEM[d.getUTCDay()]} ${j === 1 ? "1er" : j} ${MOIS[m - 1]}`; };
  const joursDansMois = (a, m) => dateUTC(a, m + 1, 0).getUTCDate();

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

  /* ---------- Objectifs ---------- */
  // Les besoins baissent avec le poids : environ 14 kcal par kg (métabolisme de base × activité légère).
  // Les protéines restent calées sur le profil, qui vise le poids objectif.
  function objectifs(profil, poidsActuel) {
    const delta = poidsActuel != null && profil.poids ? poidsActuel - profil.poids : 0;
    const k = Math.round(delta * 14);
    return { kcalMin: profil.kcalMin + k, kcalMax: profil.kcalMax + k, prot: profil.prot };
  }

  /* ---------- Calendrier et courses ---------- */
  function calendrier(annee, mois, reglages) {
    const n = joursDansMois(annee, mois);
    const jc = reglages.courses.jours.filter(j => j >= 1 && j <= n).sort((x, y) => x - y);
    // âge des produits frais au jour j : jours écoulés depuis la dernière course
    // (avant la première course du mois : depuis la dernière du mois précédent)
    const prec = mois === 1 ? [annee - 1, 12] : [annee, mois - 1];
    const derniereAvant = reglages.courses.jours.filter(j => j <= joursDansMois(...prec)).slice(-1)[0];
    const age = j => {
      const c = jc.filter(x => x <= j).slice(-1)[0];
      return c != null ? j - c : j + joursDansMois(...prec) - derniereAvant;
    };
    const periodes = jc.map((c, i) => ({ id: i + 1, debut: c, fin: (jc[i + 1] || n + 1) - 1 }));
    return { n, jc, age, periodes };
  }

  /* ---------- Composition du planning ---------- */
  function composer(ctx) {
    const { cat, recettes, reglages, annee, mois, cal, alea, poidsCout, exclure } = ctx;
    const actives = recettes.filter(r => !exclure.has(r.id));
    const plats = actives.filter(r => (r.repas.includes("dej") || r.repas.includes("din")) && !r.tags.includes("restes"));
    const restes = actives.filter(r => r.tags.includes("restes") && r.suit);
    const desserts = actives.filter(r => r.repas.includes("des"));
    const pdj = actives.find(r => r.repas.includes("pdj"));
    const ecart = reglages.ecartMinJours || 5;
    const N = cal.n;
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
    // stock de départ encore disponible pour les plats (lentilles, farine…) : on le consomme en priorité
    const stockDispo = Object.assign({}, ctx.stockDepart);
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

    // 1. repas plaisir : déjeuners du week-end, répartis sur le mois
    const nbPlaisir = reglages.quotas.plaisir, nbPoisson = reglages.quotas.poisson;
    const weekends = [];
    for (let j = 1; j <= N; j++) { const w = dateUTC(annee, mois, j).getUTCDay(); if (w === 0 || w === 6) weekends.push(j); }
    const joursPlaisir = repartir(weekends, nbPlaisir, N);
    const plaisirs = plats.filter(r => r.tags.includes("plaisir"));
    for (const j of joursPlaisir) { const r = meilleur(plaisirs, j, "dej") || meilleur(plaisirs.concat(plats), j, "dej"); if (r) placerAvecRestes(j, "dej", r); }

    // 2. poisson : réparti régulièrement, en alternant déjeuner et dîner
    const poissons = plats.filter(r => r.tags.includes("poisson"));
    for (let i = 0; i < nbPoisson; i++) {
      let j = Math.min(N, Math.max(1, Math.round((i + 0.5) * N / nbPoisson)));
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

    // 4. desserts : glace les jours plaisir, sinon la répartition d'octobre, fruits frais près des courses
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
    // arrondis : unités entières, 5 g ou 5 ml sinon
    for (const k of Object.keys(items)) items[k] = items[k].map(([a, q]) => [a, UNITES_ENTIERES.has(a) ? Math.max(1, Math.round(q)) : Math.max(5, arrondi(q, 5))]);
    return items;
  }

  /* ---------- Courses ---------- */
  function listeCourses(ctx, plan) {
    const { cat, reglages, annee, mois, cal } = ctx;
    const N = cal.n;
    // consommation par jour, par personne et par produit (repas + hors repas)
    const conso = [];
    for (let j = 1; j <= N; j++) {
      const c = { nicolas: {}, aurelie: {} };
      for (const m of plan[j - 1].meals) for (const p of PERSONNES) for (const [a, q] of m.items[p]) c[p][a] = (c[p][a] || 0) + q;
      for (const h of reglages.horsRepas || []) for (const p of PERSONNES) if (h.parJour[p]) c[p][h.a] = (c[p][h.a] || 0) + h.parJour[p];
      conso.push(c);
    }
    const besoin = (a, d1, d2, p) => { let s = 0; for (let j = d1; j <= d2; j++) { const c = conso[j - 1]; for (const pp of p ? [p] : PERSONNES) s += c[pp][a] || 0; } return s; };
    const produits = [...new Set(conso.flatMap(c => PERSONNES.flatMap(p => Object.keys(c[p]))))];
    const stock = {};
    for (const a of produits) stock[a] = ctx.stockDepart[a] || 0;
    const manquesAvant = [];
    const alertesRupture = [];

    // avant la première course : on vit sur le stock
    const avant = cal.jc.length ? cal.jc[0] - 1 : N;
    for (const a of produits) {
      const b = besoin(a, 1, avant);
      if (b > stock[a] + 1e-6) manquesAvant.push({ a, q: r2(b - stock[a]) });
      stock[a] = Math.max(0, stock[a] - b);
    }

    const courses = [];
    const pertes = [];
    for (const per of cal.periodes) {
      const items = [];
      // frais restant de la période précédente : perdu s'il a dépassé sa conservation au jour de la course
      if (per.id > 1) {
        const ecoule = per.debut - cal.periodes[per.id - 2].debut;
        for (const a of produits) {
          const c = cat[a];
          if (c && c.conservation && c.conservation.frais && stock[a] > 0.5 && ecoule >= c.conservation.jours) {
            pertes.push({ a, course: per.id, q: r2(stock[a]), cout: r2(stock[a] * prixUnitaire(cat, a)) });
            stock[a] = 0;
          }
        }
      }
      for (const a of produits) {
        const c = cat[a]; if (!c) continue;
        // chaque course couvre sa période ; les restes de conditionnement passent à la suivante,
        // ce qui étale la dépense sans rien acheter de plus sur le mois
        const b = besoin(a, per.debut, per.fin);
        let manque = b - stock[a];
        let buy = 0, est = 0;
        if (manque > 1e-6) {
          if (c.vrac) { buy = Math.ceil(manque / (c.rend || 1) / 50) * 50; est = buy / 1000 * (c.prix || 0); stock[a] += buy * (c.rend || 1); }
          else { buy = Math.ceil(manque / c.cond - 1e-9); est = buy * (c.prix || 0); stock[a] += buy * c.cond; }
        }
        const needN = besoin(a, per.debut, per.fin, "nicolas"), needA = besoin(a, per.debut, per.fin, "aurelie");
        stock[a] -= needN + needA;
        if (stock[a] < -1e-6) { alertesRupture.push({ a, course: per.id, q: r2(-stock[a]) }); stock[a] = 0; }
        if (buy > 0) items.push({ a, buy, est: r2(est), needN: r2(needN), needA: r2(needA) });
      }
      const d1 = per.debut, d2 = per.fin;
      courses.push({
        id: per.id, date: iso(dateUTC(annee, mois, d1)), jourPlan: d1, titre: `Course ${per.id}`,
        jour: nomJour(annee, mois, d1), couvre: `du ${d1 === 1 ? "1er" : d1} au ${d2} ${MOIS[mois - 1]}`,
        items: items.sort((x, y) => produits.indexOf(x.a) - produits.indexOf(y.a)),
      });
    }
    const stockFin = {};
    for (const a of produits) if (stock[a] > 0.5) stockFin[a] = r2(stock[a]);
    return { courses, conso, manquesAvant, alertesRupture, stockFin, pertes };
  }

  /* ---------- Point d'entrée ---------- */
  function composerMois(entrees) {
    const { catalogue, recettes, reglages, annee, mois } = entrees;
    const cat = catalogue;
    const profils = {};
    for (const p of PERSONNES) {
      const base = Object.assign({}, reglages.personnes[p], (entrees.profils || {})[p] || {});
      profils[p] = Object.assign(base, objectifs(base, (entrees.poidsActuels || {})[p]));
    }
    const cal = calendrier(annee, mois, reglages);
    const exclure = new Set(entrees.exclure || []);
    const budgetMois = PERSONNES.reduce((s, p) => s + profils[p].budget * cal.n / (profils[p].budgetJours || cal.n), 0);

    // fréquence des desserts dans le mois de référence (octobre) : sert de répartition cible
    const freq = {};
    for (const j of entrees.moisReference ? entrees.moisReference.plan : []) for (const m of j.meals) if (m.k === "des") freq[m.recette] = (freq[m.recette] || 0) + 1;
    const recs = recettes.map(r => Object.assign({}, r, { frequenceReference: freq[r.id] || 1 }));

    // on recompose en donnant plus de poids au coût tant que le budget est dépassé
    let res = null;
    for (let passe = 0; passe < 6; passe++) {
      const ctx = { cat, recettes: recs, reglages, annee, mois, cal, exclure, stockDepart: entrees.stockDepart || {},
        alea: hasard((entrees.graine || 1) + passe * 7919), poidsCout: 0.5 + passe * 0.8 };
      const { grille, joursPlaisir } = composer(ctx);
      const plan = [];
      for (let j = 1; j <= cal.n; j++) {
        const parPersonne = {};
        for (const p of PERSONNES) {
          const repas = {};
          for (const k of ["pdj", "dej", "din", "des"]) { const r = grille[`${j}-${k}`]; if (r) repas[k] = r.portions[p]; }
          parPersonne[p] = portionsDuJour(cat, repas, profils[p]);
        }
        const meals = ["pdj", "dej", "din", "des"].filter(k => grille[`${j}-${k}`]).map(k => {
          const r = grille[`${j}-${k}`];
          return { k, label: LABELS[k], plat: r.nomParPersonne || { nicolas: r.nom, aurelie: r.nom },
            items: { nicolas: parPersonne.nicolas[k], aurelie: parPersonne.aurelie[k] }, recette: r.id };
        });
        const fish = meals.some(m => (grille[`${j}-${m.k}`].tags || []).includes("poisson"));
        plan.push({ d: j, tag: joursPlaisir.includes(j) ? "plaisir" : (fish ? "poisson" : ""), fish, meals });
      }
      const cr = listeCourses(ctx, plan);
      const cout = { nicolas: 0, aurelie: 0 };
      for (const c of cr.conso) for (const p of PERSONNES) for (const [a, q] of Object.entries(c[p])) cout[p] += prixUnitaire(cat, a) * q;
      res = { ctx, plan, cr, cout, joursPlaisir };
      if (cout.nicolas + cout.aurelie <= budgetMois) break;
    }

    const { plan, cr, cout, joursPlaisir } = res;
    // part de Nicolas dans la consommation de chaque produit
    const share = {};
    const tot = {};
    for (const c of cr.conso) for (const p of PERSONNES) for (const [a, q] of Object.entries(c[p])) { tot[a] = tot[a] || { nicolas: 0, aurelie: 0 }; tot[a][p] += q; }
    for (const [a, t] of Object.entries(tot)) share[a] = t.nicolas + t.aurelie ? Math.round(t.nicolas / (t.nicolas + t.aurelie) * 10000) / 10000 : 0.5;

    // bilan nutritionnel et alertes
    const nut = {};
    const horsFourchette = [];
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
    const compte = tag => plan.reduce((s, j) => s + j.meals.filter(m => (m.k === "dej" || m.k === "din") && (recettes.find(r => r.id === m.recette).tags || []).includes(tag)).length, 0);
    const [a0, m0] = [annee, mois];
    const moisObj = {
      version: 1, id: `${a0}-${String(m0).padStart(2, "0")}`, titre: `${MOIS[m0 - 1][0].toUpperCase()}${MOIS[m0 - 1].slice(1)} ${a0}`,
      debut: iso(dateUTC(a0, m0, 1)), fin: iso(dateUTC(a0, m0, res.ctx.cal.n)), jours: res.ctx.cal.n,
      note: "Proposition du moteur.", stockDepart: entrees.stockDepart || {}, share, plan, courses: cr.courses,
    };
    const achats = cr.courses.reduce((s, c) => s + c.items.reduce((t, i) => t + i.est, 0), 0);
    const bilan = {
      nutrition: nut,
      quotas: { poisson: compte("poisson"), plaisir: compte("plaisir"), joursPlaisir },
      cout: { consommation: { nicolas: r2(cout.nicolas), aurelie: r2(cout.aurelie) }, achats: r2(achats), budgetMois: r2(budgetMois),
              parCourse: cr.courses.map(c => ({ id: c.id, date: c.date, total: r2(c.items.reduce((t, i) => t + i.est, 0)), articles: c.items.length })) },
      manquesAvantPremiereCourse: cr.manquesAvant,
      ruptures: cr.alertesRupture,
      // les petits-déjeuners sont fixes : leurs dépassements sont signalés à part
      fraisAuDelaConservation: fraisTard.filter(x => x.k !== "pdj"),
      fraisAuDelaPetitDejeuner: fraisTard.filter(x => x.k === "pdj"),
      pertesFrais: cr.pertes,
      horsFourchette,
      stockFin: cr.stockFin,
      recettesUtilisees: [...new Set(plan.flatMap(j => j.meals.map(m => m.recette)))].length,
    };
    return { mois: moisObj, bilan };
  }

  return { composerMois, objectifs, prixUnitaire, totaux, calendrier, portionsDuJour };
})();
if (typeof module !== "undefined") module.exports = Moteur;
