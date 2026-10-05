// Moteur de Popote : objectifs calculés, foyer de N personnes, enfants, invités, courses hebdomadaires, budget,
// mode Express (priorité au stock), produits exclus, même graine = même menu.
const M = require("../popote/moteur.js");
const cat = require("../donnees/catalogue.json").produits, recettes = require("../donnees/recettes.json").recettes, reglages = require("../donnees/reglages.json");
const erreurs = [], verif = (ok, msg) => { if (!ok) erreurs.push(msg); };
const base = { catalogue: cat, recettes, reglages };
const nico = { id: "n", nom: "Nicolas", sexe: "h", age: 38, taille: 180, poids: 85, cible: 80, activite: "leger", pdj: "sucre" };
const aur = { id: "a", nom: "Aurélie", sexe: "f", age: 31, taille: 160, poids: 70, cible: 60, activite: "leger", pdj: "sale" };

// objectifs : proches de ceux fixés à la main pour le foyer d'origine (1 850-1 950 kcal / 110 g ; 1 350-1 450 / 85 g)
const on = M.objectifs(nico), oa = M.objectifs(aur);
verif(Math.abs((on.kcalMin + on.kcalMax) / 2 - 1900) < 100 && Math.abs(on.prot - 110) <= 5, `objectifs de Nicolas : ${JSON.stringify(on)}`);
verif(Math.abs((oa.kcalMin + oa.kcalMax) / 2 - 1400) < 60 && Math.abs(oa.prot - 85) <= 5, `objectifs d'Aurélie : ${JSON.stringify(oa)}`);
verif(M.objectifs({ sexe: "f", age: 15, taille: 160, poids: 70, cible: 50 }).rythmeKgSemaine === 0, "déficit proposé à une mineure");
verif(M.objectifs({ sexe: "f", age: 30, taille: 150, poids: 50, cible: 40, activite: "sedentaire" }).kcalMin >= 1150, "plancher de 1 200 kcal non respecté");

// un mois sur mesure, courses chaque samedi, budget
const debut = "2026-11-01", jours = 30, jc = [debut].concat(M.joursDeCourses(debut, jours, 6));
const r = M.composer(Object.assign({ personnes: [nico, aur], debut, jours, joursCourses: jc, budget: 500, graine: 3 }, base));
verif(r.periode.plan.length === 30 && r.periode.courses.length === jc.length, "mois ou courses incomplets");
verif(r.bilan.cout.achats <= 520, `achats du mois : ${r.bilan.cout.achats}`);
verif(r.bilan.quotas.poisson === 8 && r.bilan.quotas.plaisir === 6, `quotas : ${JSON.stringify(r.bilan.quotas)}`);
for (const p of ["n", "a"]) { const n = r.bilan.nutrition[p]; verif(n.kcalMoyen >= n.objectifs.kcalMin - 60 && n.kcalMoyen <= n.objectifs.kcalMax + 60 && n.protMoyen >= n.objectifs.prot - 5, `nutrition ${p} : ${JSON.stringify(n)}`); }
verif(r.periode.plan.every(j => j.meals.filter(m => m.k === "dej" || m.k === "din").every(m => m.items.n.some(([a]) => cat[a] && cat[a].animal))), "plat principal sans viande ni poisson");
verif(Object.values(r.periode.parts).every(p => Math.abs(p.n + p.a - 1) < 0.001), "parts de consommation incohérentes");
const r2 = M.composer(Object.assign({ personnes: [nico, aur], debut, jours, joursCourses: jc, budget: 500, graine: 3 }, base));
verif(JSON.stringify(r2.periode.plan) === JSON.stringify(r.periode.plan), "même graine, menu différent");

// quatre personnes dont un enfant, deux invités
const enfant = { id: "e", nom: "Enfant", sexe: "f", age: 8, taille: 128, poids: 26, cible: 26, sansRegime: true, pdj: "sucre" };
const f = M.composer(Object.assign({ personnes: [nico, aur, enfant], invites: 2, debut: "2026-10-06", jours: 7, joursCourses: ["2026-10-06"], graine: 1 }, base));
const kE = f.bilan.nutrition.e.kcalMoyen;
verif(kE < 1300 && kE > 800, `kcal de l'enfant : ${kE}`);
verif(f.periode.courses[0].items.every(i => i.need.invites != null), "invités absents des courses");

// Express : stock du ticket, pas de course prévue → une liste « À compléter », stock utilisé en priorité
const stock = { "Poulet": 2000, "Riz (sec)": 2000, "Courgettes": 1000, "Tomates": 1000, "Œufs": 12, "Pâtes (sèches)": 1000, "Huile": 1000 };
const x = M.composer(Object.assign({ personnes: [nico, aur], debut: "2026-10-06", jours: 5, stockDepart: stock, priorite: "stock", graine: 1 }, base));
verif(x.periode.courses.length <= 1 && (!x.periode.courses[0] || x.periode.courses[0].complement), "Express : courses inattendues");
verif(x.bilan.stockUtilise.length >= 5, `Express : stock peu utilisé (${x.bilan.stockUtilise})`);

// produits exclus
const sansPoulet = M.composer(Object.assign({ personnes: [nico], debut, jours: 14, joursCourses: [debut], exclureProduits: ["Poulet"], graine: 2 }, base));
verif(!sansPoulet.periode.plan.some(j => j.meals.some(m => m.k !== "pdj" && m.items.n.some(([a]) => a === "Poulet"))), "poulet exclu mais présent");

console.log("erreurs", erreurs);
process.exit(erreurs.length ? 1 : 0);
