/* Moteur de composition : règles respectées sur novembre et décembre 2026, et sur une période libre avec invités. */
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
  // chaque déjeuner et dîner contient une protéine animale (les œufs ne comptent pas)
  const animal = a => catalogue[a] && catalogue[a].animal;
  for (const j of m.plan) for (const x of j.meals) if ((x.k === "dej" || x.k === "din") && !x.items.nicolas.some(([a]) => animal(a)))
    verif(false, `${nom} : ${x.plat.nicolas} le ${j.d} sans protéine animale`);
  // aucun produit compté en perte d'office
  verif(!("pertesFrais" in b), `${nom} : pertes automatiques`);
  console.log(`${nom} : ${b.recettesUtilisees} recettes, achats ${b.cout.achats} €, budget ${b.cout.budget} €`);
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

// période libre : du 22 au 31 octobre, 3 invités, budget saisi
{
  const { mois: m, bilan: b } = Moteur.composerMois({ catalogue, recettes, reglages, debut: "2026-10-22", jours: 10, invites: 3, budget: 250, graine: 1, moisReference: reference, stockDepart: {} });
  verif(m.jours === 10 && m.debut === "2026-10-22" && m.fin === "2026-10-31", `période libre : ${m.debut} → ${m.fin}`);
  verif(m.id === "2026-10-22_10j" && m.invites === 3, `période libre : id ${m.id}, invités ${m.invites}`);
  verif(JSON.stringify(m.courses.map(c => c.date)) === JSON.stringify(["2026-10-24"]), `période libre : courses ${m.courses.map(c => c.date)}`);
  verif(b.quotas.objectif.poisson === 3 && b.quotas.objectif.plaisir === 2, `quotas au prorata : ${JSON.stringify(b.quotas.objectif)}`);
  verif(b.cout.budget === 250, "budget saisi ignoré");
  // portion d'un invité = moyenne de Nicolas et d'Aurélie ; la course compte les 3 invités
  const r = m.plan[5].meals.find(x => x.k === "dej");
  const q = (it, a) => (it.find(([x]) => x === a) || [0, 0])[1];
  const a0 = r.items.nicolas.find(([a]) => catalogue[a].animal)[0];
  verif(Math.abs(q(r.items.invites, a0) - (q(r.items.nicolas, a0) + q(r.items.aurelie, a0)) / 2) <= 5, "portion d'invité ≠ moyenne");
  const it = m.courses[0].items.find(i => i.a === a0);
  verif(it && it.needI > 0, "course sans la part des invités");
  const seul = Moteur.composerMois({ catalogue, recettes, reglages, debut: "2026-10-22", jours: 10, invites: 0, graine: 1, moisReference: reference, stockDepart: {} });
  verif(b.cout.achats > seul.bilan.cout.achats * 1.8, `3 invités : achats ${b.cout.achats} € contre ${seul.bilan.cout.achats} € sans`);
}

// objectifs : 3 kg de moins, environ 42 kcal de moins par jour, protéines inchangées
const o = Moteur.objectifs(reglages.personnes.nicolas, 82);
verif(o.kcalMin === 1808 && o.kcalMax === 1908 && o.prot === 110, `objectifs après pesée : ${JSON.stringify(o)}`);

// âge des produits frais : 8 jours au 1er novembre (dernière course le 24 octobre), 0 le jour d'une course
const cal = Moteur.calendrier(new Date(Date.UTC(2026, 10, 1)), 30, reglages);
verif(cal.age(1) === 8 && cal.age(3) === 0 && cal.age(9) === 6, `âge des frais : ${cal.age(1)}, ${cal.age(3)}, ${cal.age(9)}`);

console.log("erreurs", erreurs);
process.exit(erreurs.length ? 1 : 0);
