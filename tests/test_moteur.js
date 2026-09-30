/* Moteur de composition : règles du mois respectées sur novembre 2026 et décembre 2026. */
const fs = require("fs"), path = require("path");
const Moteur = require("../app/moteur.js");
const DON = path.join(__dirname, "..", "donnees");
const lire = (...c) => JSON.parse(fs.readFileSync(path.join(DON, ...c), "utf8"));
const catalogue = lire("catalogue.json").produits, recettes = lire("recettes.json").recettes, reglages = lire("reglages.json");
const reference = lire("mois", "2026-10.json");
const erreurs = [];
const verif = (ok, msg) => { if (!ok) erreurs.push(msg); };
const famille = id => { const r = recettes.find(x => x.id === id); return (r.nom || r.id).split(/[,(+]/)[0].trim().toLowerCase(); };

function composer(annee, mois, graine, extra) {
  return Moteur.composerMois(Object.assign({ catalogue, recettes, reglages, annee, mois, graine, moisReference: reference, stockDepart: {} }, extra || {}));
}

for (const [annee, mois, n] of [[2026, 11, 30], [2026, 12, 31]]) {
  const { mois: m, bilan: b } = composer(annee, mois, 1);
  const nom = m.id;
  verif(m.plan.length === n, `${nom} : ${m.plan.length} jours au lieu de ${n}`);
  verif(m.plan.every(j => ["pdj", "dej", "din", "des"].every(k => j.meals.some(x => x.k === k))), `${nom} : repas manquant`);
  verif(b.quotas.poisson === reglages.quotas.poisson, `${nom} : ${b.quotas.poisson} poissons`);
  verif(b.quotas.plaisir === reglages.quotas.plaisir, `${nom} : ${b.quotas.plaisir} plaisirs`);
  // pas deux fois la même famille de plat à moins de l'écart minimal (desserts et petits-déjeuners exceptés)
  const vus = [];
  for (const j of m.plan) for (const x of j.meals) if (x.k === "dej" || x.k === "din") vus.push([j.d, famille(x.recette)]);
  for (const [d1, f1] of vus) for (const [d2, f2] of vus)
    if (d2 > d1 && f1 === f2 && d2 - d1 < reglages.ecartMinJours) verif(false, `${nom} : « ${f1} » les ${d1} et ${d2}`);
  // courses aux jours des réglages, sans rupture
  verif(JSON.stringify(m.courses.map(c => c.jourPlan)) === JSON.stringify(reglages.courses.jours), `${nom} : jours de courses`);
  verif(b.ruptures.length === 0, `${nom} : ruptures ${JSON.stringify(b.ruptures)}`);
  // nutrition moyenne dans la fourchette, protéines atteintes
  for (const [p, x] of Object.entries(b.nutrition)) {
    verif(x.kcalMoyen >= x.objectifs.kcalMin && x.kcalMoyen <= x.objectifs.kcalMax, `${nom} : ${p} ${x.kcalMoyen} kcal en moyenne`);
    verif(x.protMoyen >= x.objectifs.prot, `${nom} : ${p} ${x.protMoyen} g de protéines en moyenne`);
  }
  verif(b.horsFourchette.length <= 8, `${nom} : ${b.horsFourchette.length} jours hors fourchette`);
  for (const c of m.courses) verif(c.items.every(i => i.buy > 0 && i.est >= 0), `${nom} : article vide dans la course ${c.id}`);
  console.log(`${nom} : ${b.recettesUtilisees} recettes, achats ${b.cout.achats} €, pertes ${b.pertesFrais.reduce((s, x) => s + x.cout, 0).toFixed(2)} €`);
}

// même graine, même mois ; graine différente, planning différent
const a = JSON.stringify(composer(2026, 11, 1).mois.plan), b2 = JSON.stringify(composer(2026, 11, 1).mois.plan);
verif(a === b2, "même graine : résultats différents");
verif(a !== JSON.stringify(composer(2026, 11, 2).mois.plan), "graines 1 et 2 : même planning");

// recette écartée : jamais proposée
const sansPizza = composer(2026, 11, 1, { exclure: ["pizza-maison-boeuf-poivrons-champignons-salade"] }).mois;
verif(!sansPizza.plan.some(j => j.meals.some(x => x.recette === "pizza-maison-boeuf-poivrons-champignons-salade")), "recette écartée proposée");

// stock de départ : utilisé avant d'acheter
const avecLentilles = composer(2026, 11, 1, { stockDepart: { "Lentilles (égouttées)": 5000 } });
const achatLentilles = avecLentilles.mois.courses.flatMap(c => c.items).filter(i => i.a === "Lentilles (égouttées)");
verif(achatLentilles.length === 0, "lentilles achetées alors qu'il y en a 5 kg en stock");

// objectifs : 3 kg de moins, environ 42 kcal de moins par jour, protéines inchangées
const o = Moteur.objectifs(reglages.personnes.nicolas, 82);
verif(o.kcalMin === 1808 && o.kcalMax === 1908 && o.prot === 110, `objectifs après pesée : ${JSON.stringify(o)}`);

// âge des produits frais : 8 jours au 1er novembre (dernière course le 24 octobre), 0 le jour d'une course
const cal = Moteur.calendrier(2026, 11, reglages);
verif(cal.age(1) === 8 && cal.age(3) === 0 && cal.age(9) === 6, `âge des frais : ${cal.age(1)}, ${cal.age(3)}, ${cal.age(9)}`);

console.log("erreurs", erreurs);
process.exit(erreurs.length ? 1 : 0);
