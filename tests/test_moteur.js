/* Moteur de composition : règles respectées sur novembre et décembre 2026, et sur une période libre avec invités. */
const fs = require("fs"), path = require("path");
const Moteur = require("../app/moteur.js");
const DON = path.join(__dirname, "..", "donnees");
const lire = (...c) => JSON.parse(fs.readFileSync(path.join(DON, ...c), "utf8"));
const catalogue = lire("catalogue.json").produits, recettes = lire("recettes.json").recettes, reglages = lire("reglages.json");
const reference = lire("mois", "2026-10.json");
const erreurs = [];
const verif = (ok, msg) => { if (!ok) erreurs.push(msg); };
// plats et variantes dépliées (une variante garde la famille de son plat d'origine)
const toutes = Moteur.deplierVariantes(recettes, catalogue);
const famille = id => Moteur.famille(toutes.find(x => x.id === id));

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

// réajustement en cours de mois : novembre, après la Course 1 (le 3), prochaine course le 10
{
  const base = composer(2026, 11, 1);
  const m = base.mois, budget = 500;
  const c1 = m.courses[0], aPartirDe = m.courses[1].jourPlan;
  const commun = { catalogue, recettes, reglages, graine: 1, moisReference: reference, mois: m, aPartirDe, budget };

  // prix conformes aux estimations : rien ne bouge, projection = achats prévus
  const payesJustes = Object.fromEntries(c1.items.map(it => [`c1-${it.a}`, it.est]));
  const r0 = Moteur.reajuster(Object.assign({}, commun, { payes: payesJustes, budget: 600 }));
  verif(!r0.recompose, "réajustement : recomposé alors que le budget tient");
  verif(Math.abs(r0.budget.projection - base.bilan.cout.achats) < 0.05, `projection ${r0.budget.projection} ≠ achats prévus ${base.bilan.cout.achats}`);

  // poulet validé plus cher : les courses restantes sont réestimées à ce prix
  const r1 = Moteur.reajuster(Object.assign({}, commun, { payes: payesJustes, budget: 600, prix: { Poulet: { prix: 15 } } }));
  const poulet = cs => cs.slice(1).flatMap(c => c.items).filter(i => i.a === "Poulet").reduce((s, i) => s + i.est, 0);
  verif(poulet(r1.mois.courses) > poulet(m.courses) * 1.3, "prix validé du poulet non repris dans les courses restantes");

  // Course 1 payée 80 € de plus que prévu : hors de portée du menu, le planning est gardé et le dépassement signalé
  const payesChers = Object.assign({}, payesJustes); payesChers[`c1-${c1.items[0].a}`] = c1.items[0].est + 80;
  const rx = Moteur.reajuster(Object.assign({}, commun, { payes: payesChers }));
  verif(rx.budget.depense > c1.items.reduce((s, i) => s + i.est, 0) + 79, "dépensé : prix payés non pris en compte");
  verif(rx.budget.horsDePortee && rx.budget.projectionApres > budget, "80 € de trop : dépassement non signalé");
  if (!rx.recompose) verif(JSON.stringify(rx.mois.plan) === JSON.stringify(m.plan), "sans recomposition, le planning doit rester le même");

  // Course 1 payée 25 € de plus : la suite est recomposée, moins chère, avec le budget restant
  const payesPlus = Object.assign({}, payesJustes); payesPlus[`c1-${c1.items[0].a}`] = c1.items[0].est + 25;
  const r2 = Moteur.reajuster(Object.assign({}, commun, { payes: payesPlus }));
  verif(r2.recompose, "25 € de trop : pas de recomposition");
  verif(r2.budget.projectionApres < r2.budget.projection, `projection non réduite : ${r2.budget.projection} → ${r2.budget.projectionApres}`);
  verif(JSON.stringify(r2.mois.plan.slice(0, aPartirDe - 1)) === JSON.stringify(m.plan.slice(0, aPartirDe - 1)), "jours déjà couverts modifiés");
  verif(JSON.stringify(r2.mois.courses[0]) === JSON.stringify(c1), "Course 1 modifiée");
  verif(r2.mois.plan.length === 30 && r2.mois.courses.length === 4, "mois réajusté incomplet");
  verif(JSON.stringify(r2.mois.courses.map(c => c.jourPlan)) === JSON.stringify(m.courses.map(c => c.jourPlan)), "jours de courses déplacés");
  // l'écart entre deux mêmes plats tient aussi à la jointure, et les quotas du mois restent atteints
  const vus = [];
  for (const j of r2.mois.plan) for (const x of j.meals) if (x.k === "dej" || x.k === "din") vus.push([j.d, famille(x.recette)]);
  for (const [d1, f1] of vus) for (const [d2, f2] of vus) if (d2 > d1 && f1 === f2 && d2 - d1 < reglages.ecartMinJours) verif(false, `réajusté : « ${f1} » les ${d1} et ${d2}`);
  const tag = t => r2.mois.plan.reduce((s, j) => s + j.meals.filter(x => (x.k === "dej" || x.k === "din") && toutes.find(r => r.id === x.recette).tags.includes(t)).length, 0);
  verif(tag("poisson") === 8 && tag("plaisir") === 6, `réajusté : ${tag("poisson")} poissons, ${tag("plaisir")} plaisirs`);
  console.log(`réajustement : projection ${r2.budget.projection} € → ${r2.budget.projectionApres} € (budget ${budget} €, dépensé ${r2.budget.depense} €)`);
}

// objectifs : 3 kg de moins, environ 42 kcal de moins par jour, protéines inchangées
const o = Moteur.objectifs(reglages.personnes.nicolas, 82);
verif(o.kcalMin === 1808 && o.kcalMax === 1908 && o.prot === 110, `objectifs après pesée : ${JSON.stringify(o)}`);

// âge des produits frais : 8 jours au 1er novembre (dernière course le 24 octobre), 0 le jour d'une course
const cal = Moteur.calendrier(new Date(Date.UTC(2026, 10, 1)), 30, reglages);
verif(cal.age(1) === 8 && cal.age(3) === 0 && cal.age(9) === 6, `âge des frais : ${cal.age(1)}, ${cal.age(3)}, ${cal.age(9)}`);

// variantes : une viande ou un fromage interchangeable donne un plat de plus, de la même famille
{
  const g = toutes.find(r => r.id === "gratin-de-pommes-de-terre-au-jambon-mozzarella~emmental-rape");
  verif(g && g.portions.nicolas.some(([a]) => a === "Emmental râpé") && !g.portions.nicolas.some(([a]) => a === "Mozzarella râpée"), "variante emmental du gratin");
  verif(g && g.famille === Moteur.famille(recettes.find(r => r.id === "gratin-de-pommes-de-terre-au-jambon-mozzarella")), "la variante ne garde pas la famille du plat");
  const sans = toutes.find(r => r.id === "gratin-de-pommes-de-terre-au-jambon-mozzarella~sans-mozzarella-rapee");
  verif(sans && !sans.portions.nicolas.some(([a]) => a === "Mozzarella râpée"), "variante sans fromage");
  const thon = toutes.find(r => r.id.startsWith("pizza-maison-au-jambon") && r.id.endsWith("~thon-conserve"));
  verif(thon && thon.tags.includes("poisson") && thon.tags.includes("plaisir"), "la pizza au thon n'est pas comptée en poisson");
  const pilons = toutes.find(r => r.id.startsWith("pilons-de-poulet-au-four") && r.id.endsWith("~poulet"));
  verif(pilons && pilons.portions.nicolas.find(([a]) => a === "Poulet")[1] === 170, "facteur pilons → poulet (260 g avec os → 170 g)");
  verif(toutes.length >= recettes.length + 140, `${toutes.length} plats après dépliage`);
}
// produits exclus : plus aucun plat qui en contient (petits-déjeuners exceptés), leurs variantes restent
{
  const exclus = ["Poulet", "Mozzarella râpée"];
  const { mois: m, bilan: b } = composer(2026, 11, 3, { exclureProduits: exclus });
  const trouves = m.plan.flatMap(j => j.meals.filter(x => x.k !== "pdj").flatMap(x => x.items.nicolas.filter(([a]) => exclus.includes(a)).map(([a]) => j.d + x.k + " " + a)));
  verif(!trouves.length, `produits exclus servis : ${trouves.slice(0, 5)}`);
  verif(b.quotas.poisson === reglages.quotas.poisson && b.quotas.plaisir === reglages.quotas.plaisir, `quotas avec exclusions : ${b.quotas.poisson} poissons, ${b.quotas.plaisir} plaisirs`);
  verif(Moteur.deplierVariantes(recettes, catalogue, exclus).some(r => r.id === "gratin-de-pommes-de-terre-au-jambon-mozzarella~emmental-rape"), "la variante sans le produit exclu a disparu");
}

console.log("erreurs", erreurs);
process.exit(erreurs.length ? 1 : 0);
