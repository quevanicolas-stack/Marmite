"""Découpe donnees/appdata.json (archive d'octobre) en trois blocs + les réglages.

donnees/catalogue.json    produits : rayon, conditionnement, prix, nutrition, rôle, conservation
donnees/recettes.json     bibliothèque : plats d'octobre avec leurs portions de référence par personne
donnees/mois/2026-10.json le mois d'octobre : dates, stock de départ, parts, planning, courses
donnees/reglages.json     règles des mois suivants (dates des courses, quotas, inventaire, Claude)

Migration à lancer une fois. Ensuite, ces fichiers sont la source : app/construire.py les assemble.
"""
import json, os, re, unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(ICI, "..", "donnees")
SRC = json.load(open(os.path.join(DON, "appdata.json"), encoding="utf-8"))

# Rôle de chaque produit dans une recette : sert au moteur pour régler les portions
# (protéine → objectif de protéines, féculent → fourchette de kcal, légumes généreux).
ROLES = {
    "proteine": ["Poulet", "Bœuf", "Lardons", "Jambon", "Poisson blanc", "Œufs", "Lentilles (égouttées)"],
    "feculent": ["Riz (sec)", "Pâtes (sèches)", "Pâtes à lasagnes (sèches)", "Flocons d'avoine", "Pommes de terre",
                 "Patates douces", "Wraps", "Pains burger", "Pain complet", "Farine"],
    "legume": ["Courgettes", "Haricots verts", "Tomates", "Poivrons", "Carottes", "Aubergines", "Champignons",
               "Salade", "Oignons", "Maïs", "Avocat (chair)"],
    "matiere_grasse": ["Huile"],
}
ROLE = {a: r for r, l in ROLES.items() for a in l}

# Conservation après achat, en suivant le conseil de la note (viandes congelées, pain congelé…).
# Estimations à corriger par Nico. « frais » = 10 jours ou moins : vérifié à l'inventaire.
GARDE = {
    "Poulet": (90, "congélateur"), "Bœuf": (90, "congélateur"), "Lardons": (21, "frigo"), "Jambon": (7, "frigo"),
    "Poisson blanc": (180, "congélateur"), "Œufs": (28, "frigo"), "Lait": (90, "placard"),
    "Yaourt nature": (21, "frigo"), "Mozzarella râpée": (60, "congélateur"), "Cheddar": (21, "frigo"),
    "Riz (sec)": (365, "placard"), "Pâtes (sèches)": (365, "placard"), "Pâtes à lasagnes (sèches)": (365, "placard"),
    "Flocons d'avoine": (180, "placard"), "Pommes de terre": (21, "placard"), "Patates douces": (10, "placard"),
    "Wraps": (60, "placard"), "Pains burger": (60, "congélateur"), "Pain complet": (60, "congélateur"),
    "Haricots verts": (180, "congélateur"), "Carottes": (18, "frigo"), "Oignons": (30, "placard"),
    "Maïs": (365, "placard"), "Tomates": (6, "ambiant"), "Courgettes": (7, "frigo"), "Poivrons": (10, "frigo"),
    "Aubergines": (6, "frigo"), "Champignons": (4, "frigo"), "Salade": (5, "frigo"), "Pommes": (25, "frigo"),
    "Bananes": (6, "ambiant"), "Avocat (chair)": (5, "ambiant"), "Mangue": (6, "ambiant"), "Ananas": (6, "ambiant"),
    "Glace": (180, "congélateur"), "Chocolat noir": (365, "placard"), "Café": (180, "placard"),
    "Eau (bouteilles 5 L)": (365, "placard"), "Citrons": (14, "frigo"), "Sauce soja": (365, "placard"),
    "Concentré de tomate": (180, "placard"), "Moutarde / ketchup": (180, "frigo"),
    "Ail, gingembre, curcuma": (180, "placard"), "Levure boulangère": (180, "placard"),
    "Lentilles (égouttées)": (365, "placard"), "Huile": (365, "placard"), "Farine": (180, "placard"),
}
FRAIS_MAX_JOURS = 10

def slug(s):
    s = s.replace("œ", "oe").replace("Œ", "Oe")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# Protéines animales : un plat principal doit en contenir une (les œufs ne comptent pas).
ANIMAL = {"Poulet", "Bœuf", "Lardons", "Jambon", "Poisson blanc"}

# Corrections de Nico (30/09/2026) appliquées au catalogue et au mois d'octobre.
# Jambon acheté à la coupe, au gramme près : prix au kilo déduit du paquet de 500 g à 5,62 €.
JAMBON = {"achat": "à la coupe, au gramme", "cond": 1, "vrac": 1, "rend": 1, "pasAchat": 1,
          "prix": round(5.62 / 0.5, 2), "note": "Au gramme près, à la coupe. 2 à 3 jours une fois ouvert."}


def catalogue():
    produits = {}
    # ordre de la table nutritionnelle d'abord : l'app s'en sert pour l'affichage et la recherche d'aliments
    ordre = list(SRC["nut"]) + [a for a in SRC["cat"] if a not in SRC["nut"]]
    for a in ordre:
        c = SRC["cat"][a]
        jours, lieu = GARDE[a]
        produits[a] = {
            "rayon": c["cat"], "achat": c["achat"], "cond": c["cond"], "vrac": c["vrac"], "rend": c["rend"],
            "prix": c["prix"], "nut": SRC["nut"].get(a), "role": ROLE.get(a, "autre"),
            "conservation": {"jours": jours, "lieu": lieu, "frais": jours <= FRAIS_MAX_JOURS, "estime": True},
            "note": c["note"],
        }
        if a in ANIMAL:
            produits[a]["animal"] = True
    produits["Jambon"].update(JAMBON)
    return {"version": 1, "produits": produits}


def recettes_et_plan():
    recettes, index, plan = [], {}, []
    for j in SRC["plan"]:
        jour = dict(j, meals=[])
        for m in j["meals"]:
            cle = json.dumps([m["k"], m["plat"], m["items"]], ensure_ascii=False, sort_keys=True)
            if cle not in index:
                noms = set(m["plat"].values())
                nom = m["plat"]["nicolas"] if len(noms) == 1 else None
                base = slug(nom) if nom else "pdj-" + slug(m["plat"]["nicolas"])
                rid, n = base, 2
                while any(r["id"] == rid for r in recettes):
                    rid, n = f"{base}-{n}", n + 1
                tags = []
                if any(a == "Poisson blanc" for a, _ in m["items"]["nicolas"]): tags.append("poisson")
                if j["tag"] == "plaisir" and m["k"] == "dej": tags.append("plaisir")
                if "restes" in (nom or "").lower(): tags.append("restes")
                r = {"id": rid, "nom": nom, "repas": [m["k"]], "tags": tags, "source": "octobre-2026",
                     "portions": {p: [[a, q] for a, q in m["items"][p]] for p in ("nicolas", "aurelie")}}
                if nom is None:  # petits-déjeuners : un plat différent par personne
                    r["nomParPersonne"] = m["plat"]
                recettes.append(r)
                index[cle] = rid
            jour["meals"].append(dict(m, recette=index[cle]))
        plan.append(jour)
    # plats de restes : cuisinés avec le surplus d'un autre plat, placés juste après lui
    suites = {"lasagnes-restes-du-samedi-salade": ("lasagnes-boeuf-courgettes-salade", 2),
              "salade-des-restes-du-barbecue-poulet-avocat-pommes-de-terre": ("barbecue-boeuf-poulet-pommes-de-terre-legumes-grilles", 0)}
    for r in recettes:
        if r["id"] in suites:
            r["suit"], r["delaiMaxJours"] = suites[r["id"]]
    return {"version": 1, "recettes": recettes}, plan


def mois(plan):
    stock = {a: c["stock"] for a, c in SRC["cat"].items() if c["stock"]}
    courses = json.loads(json.dumps(SRC["courses"]))
    for c in courses:  # jambon au gramme : on achète exactement le besoin de chaque course
        for it in c["items"]:
            if it["a"] == "Jambon":
                it["buy"] = int(it["needN"] + it["needA"])
                it["est"] = round(it["buy"] / 1000 * JAMBON["prix"], 2)
    return {
        "version": 1, "id": "2026-10", "titre": "Octobre 2026",
        "debut": "2026-10-01", "fin": "2026-10-21", "jours": len(plan),
        "note": "Cycle exceptionnel de 21 jours : 3 invités du 21 au 31 octobre (période en attente).",
        "stockDepart": stock, "share": SRC["share"], "plan": plan, "courses": courses,
        "corrections": ["30/09/2026 : jambon acheté au gramme (11,24 €/kg) au lieu du paquet de 500 g."],
    }


REGLAGES = {
    "version": 1,
    "cycle": "mois",
    "courses": {
        "jours": [3, 10, 17, 24],
        "note": "Jours du mois, modifiables. Chaque course couvre jusqu'à la suivante ; "
                "la dernière couvre jusqu'à la première du mois suivant.",
    },
    "quotas": {"poisson": 8, "plaisir": 6},
    "ecartMinJours": 5,
    "inventaire": {
        "avantChaqueCourse": True,
        "verificationFacultative": True,
        "verificationFraisParMois": 1,
        "fraisMaxJours": FRAIS_MAX_JOURS,
    },
    "claude": {
        "planning": "un appel le jour du planning du mois, pour proposer des recettes nouvelles",
        "jaiFaim": "bibliothèque locale par défaut ; « Nouveauté » appelle Claude à la demande",
    },
    # préparation du mois suivant le 30 (le dernier jour en février) ; rappel la veille de chaque course
    "rappels": {"preparerMoisJour": 30, "coursesJ": -1},
    # Valeurs par défaut des profils (l'app garde les siennes dans le profil de chacun).
    # Le budget est celui d'un cycle de budgetJours jours : le moteur le ramène à la durée du mois.
    "personnes": {
        "nicolas": {"poids": 85, "kcalMin": 1850, "kcalMax": 1950, "prot": 110, "budget": 180, "budgetJours": 21},
        "aurelie": {"poids": 70, "kcalMin": 1350, "kcalMax": 1450, "prot": 85, "budget": 170, "budgetJours": 21},
    },
    # Dépenses hors repas (quantité par jour, dans l'unité du catalogue : g pour le café, litres pour l'eau)
    "horsRepas": [
        {"a": "Café", "parJour": {"nicolas": round(1000 / 21, 1)}},
        {"a": "Eau (bouteilles 5 L)", "parJour": {"nicolas": 2, "aurelie": 2}},
    ],
}


def ecrire(chemin, obj):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    rec, plan = recettes_et_plan()
    ecrire(os.path.join(DON, "catalogue.json"), catalogue())
    ecrire(os.path.join(DON, "recettes.json"), rec)
    ecrire(os.path.join(DON, "mois", "2026-10.json"), mois(plan))
    ecrire(os.path.join(DON, "reglages.json"), REGLAGES)
    print(len(SRC["cat"]), "produits,", len(rec["recettes"]), "recettes, octobre", len(plan), "jours")
