/* Propose un mois avec le moteur et affiche un résumé lisible.
   Usage : node outils/proposer_mois.js 2026-11 [graine]
   Écrit donnees/propositions/<aaaa-mm>.json (mois + bilan). Ne touche pas à donnees/mois/ :
   app/construire.py prend le mois le plus récent de ce dossier, une proposition n'y va qu'une fois validée. */
const fs = require("fs"), path = require("path");
const Moteur = require("../app/moteur.js");
const DON = path.join(__dirname, "..", "donnees");
const lire = (...c) => JSON.parse(fs.readFileSync(path.join(DON, ...c), "utf8"));

const [annee, mois] = (process.argv[2] || "2026-11").split("-").map(Number);
const graine = Number(process.argv[3] || 1);
const moisDispo = fs.readdirSync(path.join(DON, "mois")).sort();
const reference = lire("mois", moisDispo[moisDispo.length - 1]);

const { mois: m, bilan: b } = Moteur.composerMois({
  catalogue: lire("catalogue.json").produits,
  recettes: lire("recettes.json").recettes,
  reglages: lire("reglages.json"),
  annee, mois, graine,
  moisReference: reference,
  stockDepart: {},   // inventaire inconnu tant que la période du 22 au 31 octobre est en attente
});

fs.mkdirSync(path.join(DON, "propositions"), { recursive: true });
const sortie = path.join(DON, "propositions", `${m.id}.json`);
fs.writeFileSync(sortie, JSON.stringify({ mois: m, bilan: b }, null, 1) + "\n");

const eur = x => x.toFixed(2).replace(".", ",") + " €";
const court = s => s.length > 58 ? s.slice(0, 57) + "…" : s;
console.log(`${m.titre} — graine ${graine}\n`);
for (const j of m.plan) {
  const r = k => { const x = j.meals.find(y => y.k === k); return x ? court(x.plat.nicolas) : "—"; };
  const mark = (j.tag === "plaisir" ? "P" : " ") + (j.fish ? "F" : " ") + (m.courses.some(c => c.jourPlan === j.d) ? "C" : " ");
  console.log(`${String(j.d).padStart(2)} ${mark} | ${r("dej").padEnd(58)} | ${r("din").padEnd(58)} | ${r("des")}`);
}
console.log("\n(P plaisir, F poisson, C jour de courses)");
console.log(`\nQuotas : ${b.quotas.poisson} poissons, ${b.quotas.plaisir} plaisirs ; ${b.recettesUtilisees} recettes utilisées`);
for (const [p, n] of Object.entries(b.nutrition))
  console.log(`${p} : ${n.kcalMoyen} kcal et ${n.protMoyen} g de protéines par jour (objectif ${n.objectifs.kcalMin}-${n.objectifs.kcalMax} kcal, ${n.objectifs.prot} g)`);
console.log(`\nCoût consommé : Nicolas ${eur(b.cout.consommation.nicolas)}, Aurélie ${eur(b.cout.consommation.aurelie)} ; budget du mois ${eur(b.cout.budgetMois)}`);
console.log(`Achats : ${eur(b.cout.achats)} — ` + b.cout.parCourse.map(c => `course ${c.id} (${c.date}) ${eur(c.total)}, ${c.articles} articles`).join(" ; "));
console.log(`Stock restant en fin de mois : ${Object.keys(b.stockFin).length} produits`);
const parProduit = l => Object.entries(l.reduce((o, x) => (o[x.a] = (o[x.a] || 0) + 1, o), {})).map(([a, n]) => `${a} ${n}`).join(", ");
console.log(`Plats avec un frais au-delà de sa conservation estimée : ${b.fraisAuDelaConservation.length} (${parProduit(b.fraisAuDelaConservation)})`);
console.log(`Petits-déjeuners concernés : ${b.fraisAuDelaPetitDejeuner.length} (${parProduit(b.fraisAuDelaPetitDejeuner)})`);
console.log(`Pertes de frais estimées : ${eur(b.pertesFrais.reduce((s, x) => s + x.cout, 0))} (${b.pertesFrais.map(x => `${x.a} ${x.q}`).join(", ")})`);
console.log(`Jours hors fourchette : ${b.horsFourchette.map(x => `${x.p} le ${x.d} (${x.kcal} kcal, ${x.prot} g)`).join(" ; ") || "aucun"}`);
console.log(`À avoir avant la première course : ${b.manquesAvantPremiereCourse.map(x => `${x.a} ${x.q}`).join(", ")}`);
if (b.ruptures.length) console.log(`Ruptures : ${JSON.stringify(b.ruptures)}`);
console.log(`\nÉcrit : ${path.relative(process.cwd(), sortie)}`);
