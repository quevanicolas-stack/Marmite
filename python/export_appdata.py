"""Exporte les données de l'app (donnees/appdata.json) à partir du classeur Excel et du menu.

nut     : valeurs nutritionnelles [base, unité, kcal, protéines] (data.py)
cat     : catalogue produits lu dans l'onglet Courses (rayon, conditionnement, vrac, rendement, prix, stock initial, conseil)
share   : part de Nicolas dans la consommation de chaque produit (Aurélie = 1 - share)
plan    : 21 jours × 4 repas, plat et ingrédients pour chaque personne (portions ajustées par adjust.py)
courses : 2 courses (jourPlan = jour du cycle où elle a lieu), quantités achetées et estimations
"""
import json, os
from openpyxl import load_workbook
from data import NUT
from menu import DAYS, BK_N, BK_A, d
from adjust import adj

ICI = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(ICI, "..", "excel", "menu_octobre_nicolas_aurelie.xlsx")
SORTIE = os.path.join(ICI, "..", "donnees", "appdata.json")

def dd(s, p): return [[k, v] for k, v in {k: adj(p, k, v) for k, v in d(s).items()}.items()]

wb = load_workbook(XLSX, data_only=True)  # le classeur doit avoir été recalculé (valeurs en cache)
wc = wb["Courses"]
cat, share, courses = {}, {}, {1: [], 2: []}
for r in range(6, 60):
    a = wc.cell(row=r, column=2).value
    if not a or wc.cell(row=r, column=1).value is None: continue
    g = lambda c: wc.cell(row=r, column=c).value
    nN, nA = (g(18) or 0), (g(19) or 0)
    share[a] = round(nN / (nN + nA), 4) if (nN + nA) else 0.5
    cat[a] = {"cat": g(1), "achat": g(4), "cond": g(5), "vrac": g(6), "rend": g(7), "prix": g(8), "stock": g(9), "note": g(24) or ""}
    for k, (bc, dc, ncN, ncA) in {1: (12, 13, 10, 11), 2: (16, 17, 14, 15)}.items():
        buy = g(bc) or 0
        if buy > 0:
            courses[k].append({"a": a, "buy": round(buy, 1), "est": round(g(dc) or 0, 2), "needN": round(g(ncN) or 0, 1), "needA": round(g(ncA) or 0, 1)})

plan = []
for day, dej, din, des, tag in DAYS:
    meals = []
    for key, lab, platN, platA, n, a in (
        ("pdj", "Petit-déjeuner", "Smoothie banane-avoine et œuf", "Œufs, jambon, tomate, pain complet et pomme", BK_N, BK_A),
        ("dej", "Déjeuner", dej[0], dej[0], dej[1], dej[2]),
        ("din", "Dîner", din[0], din[0], din[1], din[2]),
        ("des", "Dessert", des[0], des[0], des[1], des[2])):
        meals.append({"k": key, "label": lab, "plat": {"nicolas": platN, "aurelie": platA}, "items": {"nicolas": dd(n, "N"), "aurelie": dd(a, "A")}})
    plan.append({"d": day, "tag": tag.lower() if tag else "", "fish": any(m["plat"]["nicolas"].startswith("Poisson") for m in meals), "meals": meals})

out = {"nut": {k: list(v) for k, v in NUT.items()}, "cat": cat, "share": share, "plan": plan, "courses": [
    {"id": 1, "date": "2026-10-01", "jourPlan": 1, "titre": "Course 1", "jour": "jeudi 1er octobre", "couvre": "du 1er au 5 octobre", "items": courses[1]},
    {"id": 2, "date": "2026-10-06", "jourPlan": 6, "titre": "Course 2", "jour": "mardi 6 octobre", "couvre": "du 6 au 21 octobre", "items": courses[2]}]}
json.dump(out, open(SORTIE, "w"), ensure_ascii=False, separators=(",", ":"))
print("appdata.json :", len(json.dumps(out, ensure_ascii=False)), "octets")
