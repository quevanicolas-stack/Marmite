"""Assemble app/marmite.html = marmite_template.html + données (remplace __DATA__).

Les données viennent des blocs de donnees/ (catalogue, recettes, mois, réglages).
Le mois affiché est le plus récent de donnees/mois/. L'app lit encore l'ancienne forme
(nut, cat, share, plan, courses) : elle est reconstituée ici, et les blocs nouveaux
(recettes, reglages, mois) sont ajoutés à côté pour le moteur à venir.
"""
import json, os
ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(ICI, "..", "donnees")


def lire(*chemin):
    return json.load(open(os.path.join(DON, *chemin), encoding="utf-8"))


def assembler():
    catalogue = lire("catalogue.json")["produits"]
    mois = lire("mois", sorted(os.listdir(os.path.join(DON, "mois")))[-1])
    stock = mois["stockDepart"]
    return {
        "nut": {a: p["nut"] for a, p in catalogue.items() if p["nut"]},
        "cat": {a: {"cat": p["rayon"], "achat": p["achat"], "cond": p["cond"], "vrac": p["vrac"], "rend": p["rend"],
                    "prix": p["prix"], "stock": stock.get(a, 0), "note": p["note"]} for a, p in catalogue.items()},
        "share": mois["share"],
        "plan": mois["plan"],
        "courses": mois["courses"],
        "mois": {k: mois[k] for k in ("id", "titre", "debut", "fin", "jours")},
        "catalogue": catalogue,
        "recettes": lire("recettes.json")["recettes"],
        "reglages": lire("reglages.json"),
    }


if __name__ == "__main__":
    t = open(os.path.join(ICI, "marmite_template.html"), encoding="utf-8").read()
    assert "__DATA__" in t
    d = json.dumps(assembler(), ensure_ascii=False, separators=(",", ":"))
    open(os.path.join(ICI, "marmite.html"), "w", encoding="utf-8").write(t.replace("__DATA__", d))
    print("app/marmite.html construit")
