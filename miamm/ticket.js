// Lecteur de ticket de caisse, sans IA : le texte (PDF du magasin, ou texte copié depuis une photo avec
// Texte en direct / Google Lens) est découpé en lignes d'articles, puis chaque libellé est rapproché d'un produit du
// catalogue : d'abord ce que le foyer a appris (ses corrections), puis un dictionnaire de mots de ticket.
// Même forme de sortie que la lecture par le chef : { magasin, date, total, lignes: [{ libelle, aliment, nombre, poids_g, prix, alimentaire }] }.
(function (racine) {
  const normaliser = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/œ/g, "oe").replace(/æ/g, "ae")
    .replace(/[^a-z0-9]+/g, " ").trim();
  // clé d'apprentissage : le libellé sans chiffres ni unités (« FILET POULET X2 1KG » et « FILET POULET 500G » se rejoignent)
  const cle = libelle => normaliser(libelle).split(" ").filter(m => m && !/\d/.test(m) && !/^(x|kg|g|gr|l|cl|ml|lot|pc|pcs|u)$/.test(m)).join(" ");

  // mots de ticket → produit du catalogue ; la clé la plus longue qui correspond l'emporte (« lait coco » avant « lait »)
  const DICO = [
    ["pomme de terre|pommes de terre|pdt|p de terre|grenaille|frites", "Pommes de terre"], ["patate douce|patates douces", "Patates douces"],
    ["pilon|pilons|manchon", "Pilons de poulet"], ["poulet|filet poulet|cuisse poulet|aiguillette poulet|blanc poulet|volaille", "Poulet"],
    ["steak hache|hache boeuf|haches", "Steak haché"], ["boeuf|bavette|rumsteck|basse cote|pot au feu|bourguignon|entrecote|boulette", "Bœuf"],
    ["lardon|lardons", "Lardons"], ["jambon", "Jambon"], ["bacon", "Bacon"],
    ["colin|cabillaud|merlu|lieu|poisson pane|filet poisson|hoki|tilapia|panga", "Poisson blanc"], ["oeuf|oeufs", "Œufs"],
    ["lait coco|creme coco", "Lait de coco"], ["lait", "Lait"],
    ["mozza rapee|mozzarella rapee|mozzarella rape", "Mozzarella râpée"], ["mozzarella|mozza", "Mozzarella (boule)"],
    ["emmental|gruyere rape|fromage rape", "Emmental râpé"], ["cheddar", "Cheddar"],
    ["riz", "Riz (sec)"], ["lasagne|lasagnes", "Pâtes à lasagnes (sèches)"],
    ["spaghetti|penne|coquillette|fusilli|tagliatelle|macaroni|farfalle|pates|torsade", "Pâtes (sèches)"],
    ["avoine|flocon avoine|flocons avoine", "Flocons d'avoine"], ["wrap|wraps|tortilla", "Wraps"], ["pain burger|buns|pain hamburger", "Pains burger"],
    ["pain de mie", "Pain de mie"], ["pain complet|pain cereale", "Pain complet"],
    ["courgette", "Courgettes"], ["haricot vert|haricots verts", "Haricots verts"],
    ["tomate concassee|tomates concassees|tomate pelee|pulpe tomate|coulis tomate|passata", "Tomates concassées"],
    ["concentre tomate|double concentre", "Concentré de tomate"], ["tomate|tomates", "Tomates"],
    ["poivron", "Poivrons"], ["carotte", "Carottes"], ["aubergine", "Aubergines"], ["champignon|champignons|champ paris", "Champignons"],
    ["salade|laitue|batavia|iceberg|mache|roquette|feuille chene", "Salade"], ["oignon|echalote", "Oignons"], ["mais", "Maïs"],
    ["avocat", "Avocat (chair)"], ["banane", "Bananes"], ["mangue", "Mangue"], ["ananas|victoria", "Ananas"], ["pomme|pommes", "Pommes"],
    ["yaourt|yogourt|yaourts|fromage blanc|skyr", "Yaourt nature"], ["glace|creme glacee|sorbet|cone", "Glace"], ["chocolat", "Chocolat noir"],
    ["lentille verte|lentilles vertes|lentille corail", "Lentilles vertes (sèches)"], ["lentille|lentilles", "Lentilles (égouttées)"],
    ["huile", "Huile"], ["farine", "Farine"],
    ["saucisse fumee|saucisses fumees|morteau|montbeliard|knack|strasbourg", "Saucisses fumées"],
    ["saucisse|saucisses|chipolata|toulouse", "Saucisses (porc)"], ["porc hache|chair saucisse|chair a saucisse", "Porc haché"],
    ["chorizo", "Chorizo"], ["haricot rouge|haricots rouges", "Haricots rouges (égouttés)"],
    ["haricot blanc|haricots blancs|flageolet|lingot", "Haricots blancs (égouttés)"],
    ["cafe|expresso|moulu", "Café"], ["eau minerale|eau source|cristaline|vittel|evian|volvic|eau 5l|bonne eau", "Eau (bouteilles 5 L)"],
    ["citron|citrons|combava", "Citrons"], ["soja|sauce soja", "Sauce soja"], ["moutarde|ketchup|mayonnaise|mayo", "Moutarde / ketchup"],
    ["ail|gingembre|curcuma|massale|epice", "Ail, gingembre, curcuma"], ["levure", "Levure boulangère"],
    ["dinde|escalope", "Dinde (escalope)"], ["echine|cote porc|cotes porc|roti porc|porc", "Porc (échine)"], ["merguez", "Merguez"],
    ["boucane", "Boucané"], ["thon", "Thon (conserve)"], ["crevette|crevettes|gambas", "Crevettes"], ["morue", "Morue salée"],
    ["creme fraiche|creme epaisse|creme liquide|creme legere", "Crème fraîche"],
    ["pois chiche|pois chiches", "Pois chiches (égouttés)"], ["semoule|couscous", "Semoule"], ["boulgour|boulghour", "Boulgour"],
    ["nouille|nouilles|vermicelle|ramen", "Nouilles chinoises"], ["pate pizza", "Pâte à pizza"], ["pate brisee|pate feuilletee", "Pâte brisée"],
    ["brocoli|brocolis", "Brocoli"], ["epinard|epinards", "Épinards"], ["petits pois|petit pois", "Petits pois"],
    ["chouchou|christophine", "Chouchou"], ["chou", "Chou"], ["citrouille|potiron|giraumon|butternut", "Citrouille"],
    ["poireau|poireaux", "Poireaux"], ["concombre", "Concombre"],
  ].flatMap(([cles, a]) => cles.split("|").map(k => [k.split(" "), a]));
  const NON_ALIMENTAIRE = /\b(lessive|adoucissant|javel|eponge|papier|essuie|mouchoir|sopalin|savon|shampo|shampooing|gel douche|dentifrice|brosse|deodorant|rasoir|couche|lingette|sac|sacs|pile|piles|ampoule|coca|cola|soda|limonade|sirop|jus|biere|vin|rhum|whisky|vodka|aperitif|punch|cigarette|tabac|journal|chips|bonbon|biscuit|gateau|croissant|viennoiserie|nettoyant|liquide vaisselle|vaisselle|alu|film|aluminium|litiere|croquette|chat|chien)\b/;
  const IGNORER = /\b(sous total|sous-total|total|a payer|net a payer|montant|tva|cb|carte|especes|rendu|monnaie|ticket|merci|caisse|caissier|siret|tel|www|nb art|nombre d articles|articles|paiement|transaction|fidelite|cagnotte|avantage carte|solde|euros|eur ttc|ht)\b/;
  const MAGASINS = /(e ?leclerc|leclerc|carrefour|super u|hyper u|intermarche|auchan|lidl|leader price|score|jumbo|run market|casino|monoprix|franprix|cora|match|simply|spar|vival|aldi|picard)/;

  // un mot de dictionnaire correspond à un mot du ticket : identique, abrégé (« courg » pour « courgette »), ou au pluriel
  const motOk = (w, t) => t === w || t === w + "s" || t === w + "x" || t === w + "es" || (t.length >= 4 && w.startsWith(t));
  function rapprocher(libelle, noms, appris) {
    const k = cle(libelle);
    if (appris && Object.prototype.hasOwnProperty.call(appris, k)) return { aliment: appris[k], appris: true };
    const mots = normaliser(libelle).split(" ").filter(Boolean);
    let best = null, score = 0;
    for (const [cles, a] of DICO) {
      if (noms && !noms.includes(a)) continue;
      if (!cles.every(w => mots.some(t => motOk(w, t)))) continue;
      const s = cles.join("").length + cles.length * 2;
      if (s > score) { score = s; best = a; }
    }
    return { aliment: best || "", appris: false };
  }

  const prixDe = s => parseFloat(String(s).replace(",", "."));
  // prix en fin de ligne, suivi éventuellement de « € » et d'un code TVA (« 2,99 € 1 », « 2.99 A »)
  const FIN_PRIX = /(-?\d{1,4}[.,]\d{2})\s*(?:€|eur)?\s*(?:[a-z0-9]{1,2})?\s*$/i;
  function lire(texte, noms, appris) {
    const res = { magasin: "", date: "", total: 0, lignes: [] };
    let enAttente = null, fini = false;
    for (const brut of String(texte || "").split(/\r?\n/)) {
      const ligne = brut.replace(/\s+/g, " ").trim(); if (!ligne) continue;
      const n = normaliser(ligne);
      if (!res.magasin) { const m = MAGASINS.exec(n); if (m) res.magasin = m[1].replace(/\b\w/g, c => c.toUpperCase()).replace(/^E ?Leclerc$/, "E.Leclerc"); }
      if (!res.date) { const d = /(\d{2})[\/.-](\d{2})[\/.-](\d{2,4})/.exec(ligne); if (d) res.date = `${d[3].length === 2 ? "20" + d[3] : d[3]}-${d[2]}-${d[1]}`; }
      const fp = FIN_PRIX.exec(ligne);
      if (/\b(total|a payer|net a payer)\b/.test(n) && !/sous/.test(n)) { if (fp && !res.total) res.total = prixDe(fp[1]); fini = true; continue; }
      if (fini) continue;
      if (IGNORER.test(n) && !/\d+[.,]\d+ ?kg/.test(n)) { enAttente = null; continue; }
      // remise : un montant négatif se déduit de l'article précédent
      if (fp && prixDe(fp[1]) < 0) { const der = res.lignes[res.lignes.length - 1]; if (der) der.prix = Math.round((der.prix + prixDe(fp[1])) * 100) / 100; continue; }
      if (/\b(remise|promo|reduction|bon de reduction|coupon)\b/.test(n)) continue;
      const kg = /(\d+[.,]\d{1,3})\s*kg\s*[x*×]/i.exec(ligne), qte = /^(\d{1,2})\s*[x*×]\s*\d+[.,]\d{2}/i.exec(ligne);
      let libelle = fp ? ligne.slice(0, fp.index).trim() : ligne;
      // ligne de détail (poids ou quantité) sous un libellé sans prix
      if (fp && (kg || qte) && (!/[a-z]{3,}/i.test(libelle.replace(/kg|eur/gi, "")) || enAttente)) {
        if (!enAttente) continue;
        libelle = enAttente; enAttente = null;
      } else if (!fp) {
        if (/[a-z]{2,}/i.test(ligne)) enAttente = ligne;
        continue;
      } else enAttente = null;
      if (!/[a-z]{2,}/i.test(libelle)) continue;
      const nn = normaliser(libelle);
      // le nombre d'articles vient d'une ligne « 2 X 1,49 » ; « X12 » dans un libellé décrit le paquet (12 œufs), pas le nombre
      const nombre = qte ? +qte[1] : 1;
      let poids = kg ? Math.round(prixDe(kg[1]) * 1000) : 0;
      if (!poids) { const p = /(\d+(?:[.,]\d+)?)\s*(kg|g|gr)\b/i.exec(libelle); if (p) poids = Math.round(prixDe(p[1]) * (p[2].toLowerCase() === "kg" ? 1000 : 1)) * nombre; }
      const r = rapprocher(libelle, noms, appris);
      const alimentaire = r.appris ? r.aliment !== "" : !NON_ALIMENTAIRE.test(nn);
      res.lignes.push({ libelle: libelle.replace(/\s{2,}/g, " "), aliment: alimentaire ? r.aliment : "", nombre, poids_g: poids, prix: prixDe(fp[1]), alimentaire, appris: r.appris });
    }
    if (!res.total) res.total = Math.round(res.lignes.reduce((s, l) => s + l.prix, 0) * 100) / 100;
    return res;
  }

  const L = { lire, rapprocher, cle, normaliser };
  if (typeof module !== "undefined" && module.exports) module.exports = L; else racine.LecteurTicket = L;
})(typeof window !== "undefined" ? window : globalThis);
