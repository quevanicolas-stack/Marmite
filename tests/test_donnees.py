"""Cohérence des blocs de données : l'app reçoit exactement les données d'octobre d'origine,
et catalogue, recettes, mois et réglages se tiennent entre eux."""
import json, pathlib, sys
RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "app"))
from construire import assembler

d = assembler()
orig = json.loads((RACINE / "donnees" / "appdata.json").read_text(encoding="utf-8"))
erreurs = []
def verif(ok, msg):
    if not ok: erreurs.append(msg)

# 1. l'ancienne forme est reconstituée à l'identique, ordre de la table nutritionnelle compris,
#    à la seule correction près du jambon, acheté au gramme depuis le 30/09/2026
# (les produits ajoutés depuis, porc, chorizo, haricots…, viennent en plus et ne sont pas comparés)
sans_jambon = lambda x: {a: v for a, v in x.items() if a != "Jambon" and a in orig["cat"]}
verif(sans_jambon(d["cat"]) == sans_jambon(orig["cat"]), "cat diffère de l'archive")
j = d["cat"]["Jambon"]
verif(j["vrac"] == 1 and j["cond"] == 1 and j["prix"] == 11.24, f"jambon : {j}")
courses_sans = lambda cs: [dict(c, items=[i for i in c["items"] if i["a"] != "Jambon"]) for c in cs]
verif(courses_sans(d["courses"]) == courses_sans(orig["courses"]), "courses diffèrent de l'archive")
achats_jambon = [(i["buy"], i["est"]) for c in d["courses"] for i in c["items"] if i["a"] == "Jambon"]
verif(achats_jambon == [(150, 1.69), (550, 6.18)], f"jambon acheté : {achats_jambon}")
verif({a: v for a, v in d["nut"].items() if a in orig["nut"]} == orig["nut"], "nut diffère de l'archive")
verif(d["share"] == orig["share"], "share diffère de l'archive")
verif(list(d["nut"])[:len(orig["nut"])] == list(orig["nut"]), "ordre de nut modifié")
plan_sans_id = [dict(j, meals=[{k: v for k, v in m.items() if k != "recette"} for m in j["meals"]]) for j in d["plan"]]
verif(plan_sans_id == orig["plan"], "plan diffère de l'archive")

# 2. chaque repas du planning pointe vers une recette dont les portions sont celles du repas
rec = {r["id"]: r for r in d["recettes"]}
verif(len(rec) == len(d["recettes"]), "identifiants de recettes en double")
for j in d["plan"]:
    for m in j["meals"]:
        r = rec.get(m.get("recette"))
        verif(r is not None, f"jour {j['d']} {m['k']} : recette inconnue")
        if r: verif(r["portions"] == m["items"], f"jour {j['d']} {m['k']} : portions différentes de la recette")

# 3. tous les ingrédients sont au catalogue, avec une nutrition, un rôle et une conservation
cat = d["catalogue"]
for r in d["recettes"]:
    for p, items in r["portions"].items():
        for a, q in items:
            verif(a in cat and cat[a]["nut"], f"{r['id']} : {a} absent du catalogue ou sans nutrition")
verif({a for a, p in cat.items() if p.get("animal")} == {"Poulet", "Bœuf", "Lardons", "Jambon", "Poisson blanc", "Saucisses (porc)", "Porc haché", "Chorizo"}, "protéines animales")
for a, p in cat.items():
    verif(p["role"] in ("proteine", "feculent", "legume", "matiere_grasse", "autre"), f"{a} : rôle inconnu")
    verif(p["conservation"]["jours"] > 0, f"{a} : conservation manquante")

# 4. octobre : 7 poissons, 3 plaisirs, comme prévu
tags = [t for j in d["plan"] for m in j["meals"] for t in rec[m["recette"]]["tags"]]
verif(tags.count("poisson") == 7, f"octobre : {tags.count('poisson')} repas poisson au lieu de 7")
verif(tags.count("plaisir") == 3, f"octobre : {tags.count('plaisir')} repas plaisir au lieu de 3")

# 5. réglages
g = d["reglages"]
verif(g["cycle"] == "mois", "cycle attendu : mois")
verif(len(g["courses"]["jours"]) == 4 and g["courses"]["jours"][0] == 3, "4 courses, la première le 3")
verif(g["courses"]["jours"] == sorted(g["courses"]["jours"]), "jours de courses non triés")
verif(g["quotas"] == {"poisson": 8, "plaisir": 6}, "quotas attendus : 8 poissons, 6 plaisirs")

print(len(cat), "produits,", len(rec), "recettes")
print("erreurs", erreurs)
sys.exit(1 if erreurs else 0)
