/* Octobre 2026 repassé en courses hebdomadaires (décision du 30/09/2026) : le 1er, le 8 et le 15.
   Recalcule donnees/mois/2026-10.json → courses à partir du planning d'octobre (inchangé).
   Les condiments sans prix de l'ancienne liste sont gardés en rappel dans la course correspondante.
   Usage : node outils/courses_octobre.js */
const fs = require("fs"), path = require("path");
const Moteur = require("../app/moteur.js");
const DON = path.join(__dirname, "..", "donnees");
const fichier = path.join(DON, "mois", "2026-10.json");
const lire = f => JSON.parse(fs.readFileSync(path.join(DON, f), "utf8"));
const m = JSON.parse(fs.readFileSync(fichier, "utf8"));
const catalogue = lire("catalogue.json").produits, reglages = lire("reglages.json");
const dates = ["2026-10-01", "2026-10-08", "2026-10-15"];

const anciennes = m.coursesDeuxFois || m.courses;
const r = Moteur.coursesPour({ catalogue, reglages, plan: m.plan, debut: m.debut, joursCourses: dates, stockDepart: m.stockDepart });
if (r.ruptures.length) throw new Error("ruptures : " + JSON.stringify(r.ruptures));
// rappels sans prix (citrons, sauce soja…) : Course 1 s'ils y étaient, sinon Course 2
for (const [i, c] of anciennes.entries())
  for (const it of c.items) if (catalogue[it.a] && catalogue[it.a].prix == null && !r.courses.some(x => x.items.some(y => y.a === it.a)))
    r.courses[Math.min(i, 1)].items.push(Object.assign({}, it));

m.coursesDeuxFois = anciennes;
m.courses = r.courses;
m.corrections = (m.corrections || []).filter(x => !x.includes("hebdomadaires")).concat(
  "30/09/2026 : courses hebdomadaires le 1er, le 8 et le 15 octobre (au lieu du 1er et du 6), recalculées par le moteur ; l'ancienne liste est gardée dans coursesDeuxFois.");
fs.writeFileSync(fichier, JSON.stringify(m, null, 1) + "\n");
for (const c of m.courses) console.log(`${c.titre} (${c.jour}, ${c.couvre}) : ${c.items.length} articles, ${c.items.reduce((s, i) => s + (i.est || 0), 0).toFixed(2)} €`);
console.log("Avant :", anciennes.map(c => `${c.titre} ${c.items.reduce((s, i) => s + (i.est || 0), 0).toFixed(2)} €`).join(", "));
