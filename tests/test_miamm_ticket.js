// Lecteur de ticket sans IA : découpage des lignes (prix, quantités, poids, remises), rapprochement du catalogue, apprentissage du foyer.
const L = require("../miamm/ticket.js");
const noms = Object.keys(require("../donnees/catalogue.json").produits);
const erreurs = [], verif = (ok, m) => { if (!ok) erreurs.push(m); };

const LECLERC = `E.LECLERC SAINT-PIERRE
SAS DISTRISUD  SIRET 123
06/10/2026 18:42  Caisse 12
FILET POULET X2 1KG        11,83 € 1
RIZ LONG GRAIN 1KG
2 X 1,49 €                  2,98 € 1
COURGETTE
0,912 kg x 2,49 €/kg        2,27 € 1
OEUFS PLEIN AIR X12         3,15 € 1
REMISE IMMEDIATE           -0,50 € 1
LESSIVE LIQUIDE 2L          7,90 € 2
COCA COLA 1,5L              1,89 € 3
PDT GRENAILLE 1,5KG         2,49 € 1
LAIT COCO 400ML             1,35 € 1
TOMATES CONCASSEES          0,89 € 1
MOZZA RAPEE 200G            2,10 € 1
CHOCOLAT NOIR 70%           1,80 € 1
ART. INCONNU MAISON         1,00 € 1
SOUS-TOTAL                 40,15
TOTAL A PAYER              40,15 €
CB                         40,15`;
const t = L.lire(LECLERC, noms, {});
const par = Object.fromEntries(t.lignes.map(l => [l.libelle, l]));
verif(t.magasin === "E.Leclerc", "magasin : " + t.magasin);
verif(t.date === "2026-10-06", "date : " + t.date);
verif(t.total === 40.15, "total : " + t.total);
verif(par["FILET POULET X2 1KG"] && par["FILET POULET X2 1KG"].aliment === "Poulet" && par["FILET POULET X2 1KG"].nombre === 1 && par["FILET POULET X2 1KG"].poids_g === 1000 && par["FILET POULET X2 1KG"].prix === 11.83, "poulet : " + JSON.stringify(par["FILET POULET X2 1KG"]));
verif(par["RIZ LONG GRAIN 1KG"] && par["RIZ LONG GRAIN 1KG"].aliment === "Riz (sec)" && par["RIZ LONG GRAIN 1KG"].nombre === 2 && par["RIZ LONG GRAIN 1KG"].prix === 2.98, "riz (quantité sur la ligne suivante) : " + JSON.stringify(par["RIZ LONG GRAIN 1KG"]));
verif(par["COURGETTE"] && par["COURGETTE"].aliment === "Courgettes" && par["COURGETTE"].poids_g === 912, "courgettes au poids : " + JSON.stringify(par["COURGETTE"]));
verif(par["OEUFS PLEIN AIR X12"] && par["OEUFS PLEIN AIR X12"].aliment === "Œufs" && par["OEUFS PLEIN AIR X12"].prix === 2.65, "œufs, remise déduite : " + JSON.stringify(par["OEUFS PLEIN AIR X12"]));
verif(par["LESSIVE LIQUIDE 2L"] && !par["LESSIVE LIQUIDE 2L"].alimentaire, "lessive non alimentaire");
verif(par["COCA COLA 1,5L"] && !par["COCA COLA 1,5L"].alimentaire, "soda non alimentaire");
verif(par["PDT GRENAILLE 1,5KG"] && par["PDT GRENAILLE 1,5KG"].aliment === "Pommes de terre" && par["PDT GRENAILLE 1,5KG"].poids_g === 1500, "pommes de terre : " + JSON.stringify(par["PDT GRENAILLE 1,5KG"]));
verif(par["LAIT COCO 400ML"] && par["LAIT COCO 400ML"].aliment === "Lait de coco", "lait de coco (clé la plus longue)");
verif(par["TOMATES CONCASSEES"] && par["TOMATES CONCASSEES"].aliment === "Tomates concassées", "tomates concassées");
verif(par["MOZZA RAPEE 200G"] && par["MOZZA RAPEE 200G"].aliment === "Mozzarella râpée", "mozzarella râpée");
verif(par["ART. INCONNU MAISON"] && par["ART. INCONNU MAISON"].aliment === "" && par["ART. INCONNU MAISON"].alimentaire, "inconnu : à choisir");
verif(!t.lignes.some(l => /total|cb/i.test(l.libelle)), "lignes de total ou de paiement prises pour des articles");

// apprentissage : la correction du foyer passe avant le dictionnaire, chiffres et unités ignorés
const appris = { [L.cle("ART. INCONNU MAISON 2KG")]: "Citrouille", [L.cle("CHOCOLAT NOIR 70%")]: "" };
const t2 = L.lire(LECLERC, noms, appris), p2 = Object.fromEntries(t2.lignes.map(l => [l.libelle, l]));
verif(p2["ART. INCONNU MAISON"].aliment === "Citrouille" && p2["ART. INCONNU MAISON"].appris, "correction apprise non reprise");
verif(!p2["CHOCOLAT NOIR 70%"].alimentaire, "ligne ignorée par le foyer encore proposée");
// abréviations de caisse
verif(L.rapprocher("COURG BIO", noms).aliment === "Courgettes" && L.rapprocher("CHAMPI PARIS 250G", noms).aliment === "Champignons", "abréviations");
verif(L.rapprocher("MAISON DU CAFE", noms).aliment === "Café", "« maison » pris pour du maïs");

console.log("erreurs", erreurs);
process.exit(erreurs.length ? 1 : 0);
