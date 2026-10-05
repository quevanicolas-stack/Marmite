"""Bibliothèque de 100 plats (déjeuners et dîners) écrits pour Marmite, avec leurs variantes.

    python3 outils/bibliotheque.py        # ajoute ou remplace ces plats dans donnees/recettes.json
                                          # et les produits nouveaux dans donnees/catalogue.json

Chaque plat porte une protéine animale (viande, poisson, charcuterie). Les quantités sont celles de Nicolas ;
celles d'Aurélie s'en déduisent par rôle (protéine 80 %, féculent 50 %, légumes 120 %, matière grasse et
fromage 75 %). Le moteur recale de toute façon les portions de chacun sur ses objectifs du jour.

Variantes : un ingrédient interchangeable (une viande pour une autre, un fromage pour un autre, ou pas de
fromage) donne un plat de plus, de la même famille (le moteur ne le remet pas à moins de 5 jours de l'original).
Le moteur déplie les variantes (Moteur.deplierVariantes) ; un produit exclu retire les variantes qui le
contiennent et garde celles qui le remplacent.

Les produits nouveaux ont des prix estimés (prixEstime) qui se corrigent au premier prix payé.
"""
import json, os, re, unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(ICI, "..", "donnees")
SOURCE = "claude-2026-10-05"

# ---------- Produits nouveaux ----------
def P(rayon, achat, cond, prix, nut, role, jours, lieu, vrac=0, animal=False, substituts=None, note=""):
    d = {"rayon": rayon, "achat": achat, "cond": cond, "vrac": vrac, "rend": 1, "prix": prix,
         "nut": [100, nut[2] if len(nut) > 2 else "g", nut[0], nut[1]], "role": role,
         "conservation": {"jours": jours, "lieu": lieu, "frais": jours <= 10, "estime": True},
         "note": (note + " " if note else "") + "Prix estimé le 05/10/2026 : se corrige au premier prix payé.", "prixEstime": True}
    if vrac: d["pasAchat"] = 50
    if animal: d["animal"] = True
    if substituts: d["substituts"] = substituts
    return d

PRODUITS = {
    # viandes et charcuteries
    "Dinde (escalope)": P("Viande", "barquette 500 g", 500, 6.50, (110, 24), "proteine", 3, "frigo", animal=True, substituts=["Poulet"], note="Se congèle le jour de l'achat."),
    "Porc (échine)": P("Viande", "barquette 600 g", 600, 6.90, (200, 19), "proteine", 3, "frigo", animal=True, substituts=["Poulet", "Dinde (escalope)"], note="Échine ou côtes, se congèle."),
    "Steak haché": P("Viande", "4 × 100 g surgelés", 400, 4.90, (215, 18), "proteine", 120, "congélateur", animal=True, substituts=["Porc haché"]),
    "Merguez": P("Viande", "paquet de 6 (330 g)", 330, 4.20, (300, 15), "proteine", 90, "congélateur", animal=True, substituts=["Saucisses (porc)"]),
    "Saucisses fumées": P("Viande", "paquet de 4 (280 g)", 280, 4.50, (290, 14), "proteine", 21, "frigo", animal=True, substituts=["Saucisses (porc)"]),
    "Boucané": P("Viande", "barquette 400 g", 400, 7.90, (310, 16), "proteine", 21, "frigo", animal=True, substituts=["Lardons"], note="Poitrine fumée créole."),
    "Pilons de poulet": P("Viande", "sachet 1 kg surgelé", 1000, 3.79, (120, 12.5), "proteine", 120, "congélateur", animal=True, substituts=["Poulet"],
                         note="Poids avec les os (65 % de viande). Prix du ticket du 01/10/2026."),
    # poissons
    "Thon (conserve)": P("Poisson", "boîte 140 g égouttés", 140, 2.20, (115, 26), "proteine", 730, "placard", animal=True, substituts=["Poisson blanc"], note="Au naturel."),
    "Crevettes": P("Poisson", "sachet 400 g surgelé", 400, 6.90, (90, 20), "proteine", 120, "congélateur", animal=True, substituts=["Poisson blanc"]),
    "Morue salée": P("Poisson", "barquette 400 g", 400, 9.50, (110, 25), "proteine", 60, "frigo", animal=True, substituts=["Poisson blanc"], note="Poids dessalé ; dessaler 12 h."),
    # crèmerie
    "Emmental râpé": P("Œufs et laitages", "sachet 200 g", 200, 2.60, (380, 28), "autre", 30, "frigo", substituts=["Mozzarella râpée", "Cheddar"]),
    "Mozzarella (boule)": P("Œufs et laitages", "boule 125 g", 125, 1.10, (250, 18), "autre", 15, "frigo", substituts=["Mozzarella râpée"]),
    "Crème fraîche": P("Œufs et laitages", "pot 200 g", 200, 1.65, (290, 2.4), "matiere_grasse", 21, "frigo"),
    # épicerie, féculents
    "Lait de coco": P("Épicerie", "boîte 400 ml", 400, 1.90, (190, 1.9, "ml"), "matiere_grasse", 730, "placard"),
    "Tomates concassées": P("Épicerie", "boîte 400 g", 400, 1.10, (25, 1.2), "legume", 730, "placard", substituts=["Tomates"]),
    "Pois chiches (égouttés)": P("Féculents", "boîte 400 g (265 g égouttés)", 265, 1.20, (140, 7.5), "feculent", 730, "placard", substituts=["Haricots blancs (égouttés)"]),
    "Lentilles vertes (sèches)": P("Féculents", "paquet 500 g", 500, 2.10, (330, 24), "feculent", 365, "placard"),
    "Semoule": P("Féculents", "paquet 1 kg", 1000, 1.90, (360, 12), "feculent", 365, "placard", substituts=["Riz (sec)"]),
    "Boulgour": P("Féculents", "paquet 500 g", 500, 2.30, (350, 12), "feculent", 365, "placard", substituts=["Semoule"]),
    "Nouilles chinoises": P("Féculents", "paquet 250 g", 250, 1.60, (360, 11), "feculent", 365, "placard", substituts=["Pâtes (sèches)"]),
    "Pâte à pizza": P("Féculents", "pâte 260 g", 260, 1.90, (280, 8), "feculent", 21, "frigo"),
    "Pâte brisée": P("Féculents", "pâte 230 g", 230, 1.30, (400, 6), "feculent", 21, "frigo"),
    "Pain de mie": P("Pain", "paquet 500 g", 500, 1.90, (260, 8.5), "feculent", 10, "placard", substituts=["Pain complet"]),
    # légumes
    "Brocoli": P("Légumes", "sachet 1 kg surgelé", 1000, 2.60, (34, 2.8), "legume", 180, "congélateur", substituts=["Haricots verts"]),
    "Épinards": P("Légumes", "sachet 1 kg surgelé", 1000, 2.40, (25, 3), "legume", 180, "congélateur"),
    "Petits pois": P("Légumes", "sachet 1 kg surgelé", 1000, 2.50, (80, 5.4), "legume", 180, "congélateur", substituts=["Haricots verts"]),
    "Chou": P("Légumes", "vrac (g)", 1, 1.99, (25, 1.3), "legume", 14, "frigo", vrac=1),
    "Chouchou": P("Légumes", "vrac (g)", 1, 2.49, (20, 0.8), "legume", 10, "frigo", vrac=1, substituts=["Courgettes"]),
    "Citrouille": P("Légumes", "vrac (g)", 1, 1.99, (26, 1), "legume", 14, "placard", vrac=1, note="Giraumon."),
    "Poireaux": P("Légumes", "vrac (g)", 1, 3.49, (30, 1.5), "legume", 10, "frigo", vrac=1),
    "Concombre": P("Légumes", "pièce ~300 g", 300, 1.20, (13, 0.6), "legume", 7, "frigo"),
}

# ---------- Ingrédients interchangeables ----------
VIANDE_BLANCHE = ["Poulet", "Dinde (escalope)", "Porc (échine)"]
VOLAILLE = ["Poulet", "Dinde (escalope)"]
MIJOTE = ["Bœuf", "Porc (échine)", "Poulet"]
HACHE = ["Steak haché", "Porc haché"]
SAUCISSE = ["Saucisses fumées", "Saucisses (porc)", "Merguez"]
CHARCUT = ["Lardons", "Bacon", "Jambon"]
POISSON = ["Poisson blanc", "Crevettes"]
POISSON_PLUS = ["Poisson blanc", "Crevettes", "Thon (conserve)"]
FROMAGE = ["Mozzarella râpée", "Emmental râpé", "Cheddar", None]      # None : sans fromage
FROMAGE_PIZZA = ["Mozzarella (boule)", "Mozzarella râpée", "Emmental râpé"]
PIZZA_GARNI = ["Jambon", "Chorizo", "Thon (conserve)"]
# quantité de remplacement quand le poids utile change (pilons avec os)
FACTEUR = {("Pilons de poulet", "Poulet"): 0.65, ("Poulet", "Pilons de poulet"): 1.55}

LAB = {"Poulet": "poulet", "Dinde (escalope)": "dinde", "Porc (échine)": "porc", "Bœuf": "bœuf", "Steak haché": "bœuf haché",
       "Porc haché": "porc haché", "Saucisses fumées": "saucisses fumées", "Saucisses (porc)": "saucisses", "Merguez": "merguez",
       "Lardons": "lardons", "Bacon": "bacon", "Jambon": "jambon", "Poisson blanc": "poisson blanc", "Crevettes": "crevettes",
       "Thon (conserve)": "thon", "Mozzarella râpée": "mozzarella", "Emmental râpé": "emmental", "Cheddar": "cheddar",
       "Mozzarella (boule)": "mozzarella fraîche", "Pilons de poulet": "pilons de poulet", "Chorizo": "chorizo", "Boucané": "boucané", "Morue salée": "morue", None: "sans fromage"}

R = []
SECTION = [""]
def section(titre): SECTION[0] = titre
def plat(nom, items, tags=(), p=None, f=None, repas=("dej", "din")):
    """nom : modèle avec {p} (ingrédient principal interchangeable) et {f} (fromage) ;
       items : [(produit, quantité pour Nicolas)] ; p, f : (produit par défaut, liste des produits possibles)."""
    R.append({"nom": nom, "items": items, "tags": list(tags), "p": p, "f": f, "repas": list(repas), "section": SECTION[0]})

section("Cuisine créole")
plat("Cari de {p}, riz, lentilles", [("Poulet", 160), ("Tomates", 100), ("Oignons", 40), ("Riz (sec)", 80), ("Lentilles vertes (sèches)", 30), ("Huile", 8)], p=("Poulet", MIJOTE))
plat("Rougail {p}, riz, haricots rouges", [("Saucisses fumées", 140), ("Tomates", 120), ("Oignons", 40), ("Riz (sec)", 75), ("Haricots rouges (égouttés)", 80), ("Huile", 5)], p=("Saucisses fumées", SAUCISSE))
plat("Civet de {p}, riz, haricots blancs", [("Porc (échine)", 160), ("Oignons", 50), ("Tomates", 80), ("Riz (sec)", 75), ("Haricots blancs (égouttés)", 80), ("Huile", 8)], p=("Porc (échine)", MIJOTE))
plat("Rougail boucané, riz, lentilles", [("Boucané", 130), ("Tomates", 120), ("Oignons", 40), ("Riz (sec)", 75), ("Lentilles vertes (sèches)", 35)])
plat("Rougail morue, riz, haricots verts", [("Morue salée", 150), ("Tomates", 120), ("Oignons", 40), ("Riz (sec)", 85), ("Haricots verts", 150), ("Huile", 8)], tags=["poisson"])
plat("Cari de {p}, riz, chouchou", [("Poisson blanc", 180), ("Tomates", 100), ("Oignons", 30), ("Chouchou", 150), ("Riz (sec)", 85), ("Huile", 8)], tags=["poisson"], p=("Poisson blanc", POISSON))
plat("Gratin de chouchou au jambon ({f})", [("Jambon", 100), ("Chouchou", 350), ("Lait", 80), ("Farine", 10), ("Mozzarella râpée", 25), ("Riz (sec)", 60)], f=("Mozzarella râpée", FROMAGE))
plat("Massalé de {p}, riz, citrouille", [("Porc (échine)", 160), ("Citrouille", 150), ("Oignons", 40), ("Tomates", 60), ("Riz (sec)", 80), ("Huile", 8)], p=("Porc (échine)", MIJOTE))
plat("Brochettes de {p}, rougail tomate, riz", [("Poulet", 160), ("Tomates", 150), ("Oignons", 30), ("Riz (sec)", 85), ("Huile", 8)], p=("Poulet", VIANDE_BLANCHE))
plat("Sauté de {p} au chouchou, riz", [("Porc (échine)", 160), ("Chouchou", 200), ("Oignons", 30), ("Riz (sec)", 85), ("Huile", 8)], p=("Porc (échine)", VIANDE_BLANCHE))
plat("Cari de {p} aux haricots blancs, riz", [("Poulet", 150), ("Haricots blancs (égouttés)", 100), ("Tomates", 100), ("Oignons", 40), ("Riz (sec)", 70), ("Huile", 8)], p=("Poulet", MIJOTE))
plat("Grillade de {p}, achards de légumes, riz", [("Poulet", 160), ("Chou", 80), ("Carottes", 80), ("Haricots verts", 60), ("Riz (sec)", 85), ("Huile", 10)], p=("Poulet", VIANDE_BLANCHE))
plat("Cari de {p} au lait de coco, citrouille, riz", [("Crevettes", 170), ("Lait de coco", 60), ("Citrouille", 150), ("Oignons", 30), ("Riz (sec)", 85)], tags=["poisson"], p=("Crevettes", POISSON))
plat("Rougail {p} aux pommes de terre, salade", [("Saucisses (porc)", 140), ("Pommes de terre", 300), ("Tomates", 100), ("Oignons", 40), ("Salade", 50)], p=("Saucisses (porc)", SAUCISSE))

section("Cuisine française")
plat("Gratin de pommes de terre au jambon ({f})", [("Jambon", 100), ("Pommes de terre", 330), ("Crème fraîche", 30), ("Lait", 60), ("Mozzarella râpée", 25), ("Salade", 50)], f=("Mozzarella râpée", FROMAGE))
plat("Hachis parmentier de patate douce au {p}, salade", [("Steak haché", 150), ("Patates douces", 330), ("Lait", 50), ("Oignons", 40), ("Salade", 50)], p=("Steak haché", HACHE))
plat("Blanquette de {p}, riz, carottes", [("Dinde (escalope)", 160), ("Crème fraîche", 30), ("Champignons", 80), ("Carottes", 100), ("Riz (sec)", 85)], p=("Dinde (escalope)", VIANDE_BLANCHE))
plat("{p} à la crème et à la moutarde, pâtes, haricots verts", [("Poulet", 160), ("Crème fraîche", 30), ("Pâtes (sèches)", 85), ("Haricots verts", 150)], p=("Poulet", VIANDE_BLANCHE))
plat("Escalope de {p} aux champignons, pâtes", [("Dinde (escalope)", 160), ("Champignons", 120), ("Crème fraîche", 25), ("Pâtes (sèches)", 85)], p=("Dinde (escalope)", VIANDE_BLANCHE))
plat("Quiche lorraine ({p}), salade", [("Lardons", 70), ("Pâte brisée", 70), ("Œufs", 2), ("Crème fraîche", 30), ("Lait", 60), ("Salade", 70)], p=("Lardons", CHARCUT))
plat("Croque-monsieur ({f}), salade", [("Jambon", 70), ("Pain de mie", 120), ("Emmental râpé", 30), ("Salade", 70)], tags=["plaisir"], f=("Emmental râpé", ["Emmental râpé", "Mozzarella râpée", "Cheddar"]))
plat("Bœuf bourguignon, pommes de terre vapeur", [("Bœuf", 170), ("Carottes", 100), ("Champignons", 60), ("Oignons", 40), ("Pommes de terre", 300), ("Huile", 8)])
plat("Mijoté de {p} aux carottes, purée", [("Bœuf", 170), ("Carottes", 150), ("Oignons", 40), ("Pommes de terre", 300), ("Lait", 50)], p=("Bœuf", MIJOTE))
plat("Sauté de {p} aux pommes, riz", [("Porc (échine)", 160), ("Pommes", 100), ("Oignons", 40), ("Riz (sec)", 80), ("Huile", 8)], p=("Porc (échine)", VIANDE_BLANCHE))
plat("{p} aux lentilles et carottes", [("Saucisses (porc)", 140), ("Lentilles vertes (sèches)", 70), ("Carottes", 120), ("Oignons", 40)], p=("Saucisses (porc)", SAUCISSE))
plat("Petit salé aux lentilles ({p})", [("Lardons", 110), ("Lentilles vertes (sèches)", 75), ("Carottes", 100), ("Oignons", 40)], p=("Lardons", ["Lardons", "Boucané"]))
plat("Poisson blanc à la provençale, riz", [("Poisson blanc", 180), ("Tomates", 150), ("Courgettes", 100), ("Oignons", 30), ("Riz (sec)", 85), ("Huile", 8)], tags=["poisson"])
plat("Brandade de {p}, salade", [("Poisson blanc", 170), ("Pommes de terre", 320), ("Lait", 60), ("Huile", 10), ("Salade", 60)], tags=["poisson"], p=("Poisson blanc", ["Poisson blanc", "Morue salée"]))
plat("Poisson pané maison, purée, petits pois", [("Poisson blanc", 180), ("Farine", 15), ("Œufs", 1), ("Pommes de terre", 300), ("Lait", 50), ("Petits pois", 120), ("Huile", 10)], tags=["poisson"])
plat("Gratin de courgettes au {p} ({f})", [("Porc haché", 140), ("Courgettes", 300), ("Tomates concassées", 80), ("Mozzarella râpée", 25), ("Riz (sec)", 70)], p=("Porc haché", HACHE), f=("Mozzarella râpée", FROMAGE))
plat("Tomates farcies au {p}, riz", [("Porc haché", 140), ("Tomates", 280), ("Oignons", 30), ("Riz (sec)", 80)], p=("Porc haché", HACHE))
plat("Courgettes farcies au {p}, semoule", [("Steak haché", 140), ("Courgettes", 300), ("Oignons", 30), ("Semoule", 75)], p=("Steak haché", HACHE))
plat("Omelette {p}-champignons, pommes de terre sautées", [("Jambon", 60), ("Œufs", 3), ("Champignons", 100), ("Pommes de terre", 280), ("Huile", 10)], p=("Jambon", CHARCUT))
plat("Poêlée de pommes de terre, {p}, haricots verts", [("Lardons", 90), ("Pommes de terre", 320), ("Haricots verts", 150), ("Oignons", 30), ("Huile", 5)], p=("Lardons", CHARCUT))
plat("Gratin de poireaux au jambon ({f}), riz", [("Jambon", 100), ("Poireaux", 250), ("Crème fraîche", 30), ("Mozzarella râpée", 25), ("Riz (sec)", 70)], f=("Mozzarella râpée", FROMAGE))
plat("{p} sauce citron, purée de patate douce, brocoli", [("Poisson blanc", 180), ("Patates douces", 300), ("Brocoli", 150), ("Crème fraîche", 15)], tags=["poisson"], p=("Poisson blanc", POISSON))
plat("{p} au four, patates douces, brocoli", [("Pilons de poulet", 260), ("Patates douces", 320), ("Brocoli", 150), ("Huile", 8)], p=("Pilons de poulet", ["Pilons de poulet", "Poulet"]))
plat("Échine de porc grillée, pommes de terre sautées, haricots verts", [("Porc (échine)", 170), ("Pommes de terre", 300), ("Haricots verts", 150), ("Huile", 10)])
plat("Steak haché, purée maison, carottes", [("Steak haché", 150), ("Pommes de terre", 320), ("Lait", 60), ("Carottes", 150)])

section("Cuisine italienne")
plat("Spaghetti bolognaise au {p}", [("Steak haché", 140), ("Tomates concassées", 120), ("Oignons", 30), ("Carottes", 50), ("Pâtes (sèches)", 90), ("Huile", 5)], p=("Steak haché", HACHE))
plat("Pâtes à l'arrabbiata au chorizo", [("Chorizo", 60), ("Jambon", 50), ("Tomates concassées", 120), ("Pâtes (sèches)", 90), ("Huile", 5)])
plat("Pâtes au thon, tomates et poivrons", [("Thon (conserve)", 120), ("Tomates concassées", 100), ("Poivrons", 80), ("Pâtes (sèches)", 90), ("Huile", 5)], tags=["poisson"])
plat("Risotto {p}-champignons", [("Poulet", 150), ("Riz (sec)", 85), ("Champignons", 100), ("Oignons", 30), ("Crème fraîche", 20)], p=("Poulet", VIANDE_BLANCHE))
plat("Pizza maison au {p} ({f}), salade", [("Jambon", 70), ("Pâte à pizza", 130), ("Tomates concassées", 60), ("Champignons", 50), ("Mozzarella (boule)", 60), ("Salade", 60)],
     tags=["plaisir"], p=("Jambon", PIZZA_GARNI), f=("Mozzarella (boule)", FROMAGE_PIZZA))
plat("Pizza chorizo-poivrons ({f}), salade", [("Chorizo", 60), ("Pâte à pizza", 130), ("Tomates concassées", 60), ("Poivrons", 70), ("Mozzarella râpée", 50), ("Salade", 60)],
     tags=["plaisir"], f=("Mozzarella râpée", FROMAGE_PIZZA))
plat("Gratin de pâtes au jambon ({f})", [("Jambon", 100), ("Pâtes (sèches)", 85), ("Lait", 80), ("Farine", 10), ("Mozzarella râpée", 25), ("Brocoli", 120)], f=("Mozzarella râpée", FROMAGE))
plat("Escalope milanaise de {p}, spaghetti à la tomate", [("Dinde (escalope)", 160), ("Farine", 15), ("Œufs", 1), ("Pâtes (sèches)", 85), ("Tomates concassées", 100), ("Huile", 10)], p=("Dinde (escalope)", VOLAILLE))
plat("Minestrone au jambon et aux pâtes", [("Jambon", 90), ("Courgettes", 100), ("Carottes", 80), ("Haricots blancs (égouttés)", 70), ("Tomates concassées", 100), ("Pâtes (sèches)", 50)])
plat("Boulettes de bœuf à la tomate, pâtes", [("Bœuf", 160), ("Tomates concassées", 130), ("Oignons", 30), ("Pâtes (sèches)", 85)])
plat("Lasagnes au {p} et aux épinards ({f})", [("Steak haché", 130), ("Pâtes à lasagnes (sèches)", 80), ("Épinards", 150), ("Tomates concassées", 100), ("Lait", 80), ("Mozzarella râpée", 30)],
     tags=["plaisir"], p=("Steak haché", HACHE), f=("Mozzarella râpée", FROMAGE_PIZZA))

section("Cuisine asiatique")
plat("Sauté de {p} au brocoli, riz", [("Poulet", 160), ("Brocoli", 180), ("Oignons", 30), ("Riz (sec)", 85), ("Huile", 8)], p=("Poulet", MIJOTE))
plat("Nouilles sautées, {p} et légumes", [("Poulet", 150), ("Nouilles chinoises", 85), ("Carottes", 80), ("Chou", 100), ("Huile", 10)], p=("Poulet", VIANDE_BLANCHE + ["Crevettes"]))
plat("Riz cantonais au jambon", [("Jambon", 80), ("Œufs", 1), ("Riz (sec)", 85), ("Petits pois", 80), ("Oignons", 20), ("Huile", 10)])
plat("Porc au caramel, riz, haricots verts", [("Porc (échine)", 160), ("Oignons", 40), ("Riz (sec)", 85), ("Haricots verts", 150)])
plat("Bœuf aux oignons, riz", [("Bœuf", 160), ("Oignons", 100), ("Poivrons", 60), ("Riz (sec)", 85), ("Huile", 8)])
plat("Curry de {p} au lait de coco, riz", [("Poulet", 160), ("Lait de coco", 60), ("Carottes", 80), ("Oignons", 30), ("Riz (sec)", 85)], p=("Poulet", VIANDE_BLANCHE + ["Crevettes"]))
plat("Crevettes sautées à l'ail, nouilles, poivrons", [("Crevettes", 170), ("Nouilles chinoises", 85), ("Poivrons", 100), ("Huile", 10)], tags=["poisson"])
plat("Poisson vapeur au gingembre, riz, chou sauté", [("Poisson blanc", 180), ("Riz (sec)", 85), ("Chou", 150), ("Huile", 8)], tags=["poisson"])
plat("Bò bún au bœuf", [("Bœuf", 150), ("Nouilles chinoises", 70), ("Salade", 60), ("Carottes", 80), ("Concombre", 80), ("Huile", 5)])
plat("Pad thaï, {p}", [("Poulet", 140), ("Nouilles chinoises", 85), ("Œufs", 1), ("Carottes", 60), ("Chou", 60), ("Huile", 10)], p=("Poulet", ["Poulet", "Crevettes"]))
plat("Curry de bœuf aux patates douces", [("Bœuf", 160), ("Patates douces", 280), ("Lait de coco", 50), ("Oignons", 30)])
plat("Bibimbap au {p}, œuf, épinards", [("Steak haché", 130), ("Œufs", 1), ("Riz (sec)", 85), ("Épinards", 120), ("Carottes", 60), ("Huile", 5)], p=("Steak haché", HACHE))

section("Tex-Mex")
plat("Chili con carne au {p}, riz", [("Steak haché", 140), ("Haricots rouges (égouttés)", 100), ("Tomates concassées", 120), ("Poivrons", 60), ("Riz (sec)", 70)], p=("Steak haché", HACHE))
plat("Poulet tikka au yaourt, riz, concombre", [("Poulet", 160), ("Yaourt nature", 60), ("Riz (sec)", 85), ("Concombre", 100)])
plat("Enchiladas de {p} ({f})", [("Poulet", 140), ("Wraps", 2), ("Tomates concassées", 100), ("Poivrons", 60), ("Cheddar", 30)], tags=["plaisir"], p=("Poulet", ["Poulet", "Steak haché"]), f=("Cheddar", FROMAGE))
plat("Quesadillas au {p} ({f}), salade", [("Poulet", 130), ("Wraps", 2), ("Poivrons", 60), ("Maïs", 50), ("Cheddar", 35), ("Salade", 50)], tags=["plaisir"], p=("Poulet", ["Poulet", "Jambon"]), f=("Cheddar", ["Cheddar", "Emmental râpé", "Mozzarella râpée"]))
plat("Burritos au {p}, riz, haricots rouges", [("Poulet", 140), ("Wraps", 2), ("Riz (sec)", 50), ("Haricots rouges (égouttés)", 70), ("Tomates", 80), ("Salade", 40)], p=("Poulet", ["Poulet", "Steak haché", "Porc haché"]))
plat("Bowl mexicain, {p}, riz, maïs, avocat", [("Poulet", 150), ("Riz (sec)", 75), ("Maïs", 60), ("Haricots rouges (égouttés)", 60), ("Avocat (chair)", 50), ("Tomates", 80)], p=("Poulet", ["Poulet", "Steak haché", "Crevettes"]))
plat("Patates douces farcies au chili ({p})", [("Steak haché", 130), ("Patates douces", 320), ("Haricots rouges (égouttés)", 60), ("Tomates concassées", 80)], p=("Steak haché", HACHE))
plat("Wrap de {p} croustillant, crudités", [("Poulet", 140), ("Farine", 15), ("Wraps", 2), ("Salade", 50), ("Tomates", 80), ("Huile", 10)], tags=["plaisir"], p=("Poulet", VOLAILLE))

section("Méditerranée et Orient")
plat("Couscous {p}-merguez", [("Poulet", 100), ("Merguez", 60), ("Semoule", 80), ("Carottes", 80), ("Courgettes", 100), ("Pois chiches (égouttés)", 60)], p=("Poulet", VOLAILLE))
plat("Tajine de {p} aux légumes, semoule", [("Poulet", 160), ("Carottes", 100), ("Courgettes", 100), ("Oignons", 40), ("Semoule", 75), ("Huile", 8)], p=("Poulet", MIJOTE))
plat("Kefta de bœuf, semoule, salade tomate-concombre", [("Steak haché", 150), ("Oignons", 20), ("Semoule", 75), ("Tomates", 100), ("Concombre", 100), ("Huile", 5)])
plat("Brochettes de {p} marinées, boulgour, salade", [("Dinde (escalope)", 160), ("Yaourt nature", 30), ("Boulgour", 80), ("Salade", 60), ("Tomates", 80), ("Huile", 5)], p=("Dinde (escalope)", VIANDE_BLANCHE))
plat("Moussaka au {p} ({f})", [("Steak haché", 140), ("Aubergines", 250), ("Tomates concassées", 80), ("Lait", 80), ("Farine", 10), ("Mozzarella râpée", 25), ("Pommes de terre", 150)], p=("Steak haché", HACHE), f=("Mozzarella râpée", FROMAGE))
plat("{p} au citron, pommes de terre, courgettes", [("Poulet", 160), ("Pommes de terre", 300), ("Courgettes", 150), ("Huile", 10)], p=("Poulet", VIANDE_BLANCHE))
plat("Merguez grillées, semoule, légumes", [("Merguez", 150), ("Semoule", 80), ("Courgettes", 100), ("Carottes", 80), ("Pois chiches (égouttés)", 50)], tags=["plaisir"])
plat("Chakchouka, {p}, pain complet", [("Merguez", 80), ("Œufs", 2), ("Poivrons", 120), ("Tomates concassées", 120), ("Pain complet", 80)], p=("Merguez", ["Merguez", "Chorizo"]))
plat("Taboulé, {p}", [("Poulet", 150), ("Semoule", 75), ("Tomates", 100), ("Concombre", 100), ("Huile", 10)], p=("Poulet", ["Poulet", "Thon (conserve)", "Crevettes"]))
plat("Kebab maison de {p}, crudités, frites au four", [("Dinde (escalope)", 140), ("Wraps", 2), ("Salade", 50), ("Tomates", 60), ("Oignons", 20), ("Yaourt nature", 30), ("Pommes de terre", 150)],
     tags=["plaisir"], p=("Dinde (escalope)", VIANDE_BLANCHE))

section("Plaisirs et grillades")
plat("Burger bacon-oignons ({f}), frites au four", [("Steak haché", 120), ("Bacon", 30), ("Pains burger", 1), ("Cheddar", 20), ("Oignons", 30), ("Salade", 30), ("Pommes de terre", 220)],
     tags=["plaisir"], f=("Cheddar", ["Cheddar", "Emmental râpé", None]))
plat("Fish and chips, coleslaw", [("Poisson blanc", 180), ("Farine", 20), ("Pommes de terre", 300), ("Chou", 80), ("Carottes", 50), ("Huile", 15)], tags=["plaisir", "poisson"])
plat("Poulet frit, frites au four, coleslaw", [("Pilons de poulet", 260), ("Farine", 20), ("Œufs", 1), ("Pommes de terre", 280), ("Chou", 80), ("Carottes", 50), ("Huile", 15)], tags=["plaisir"])
plat("Nuggets de {p} maison, frites au four, crudités", [("Poulet", 150), ("Farine", 20), ("Œufs", 1), ("Pommes de terre", 280), ("Carottes", 80), ("Huile", 12)], tags=["plaisir"], p=("Poulet", VOLAILLE))
plat("Tartiflette, {p} ({f}), salade", [("Lardons", 80), ("Pommes de terre", 320), ("Oignons", 40), ("Crème fraîche", 30), ("Emmental râpé", 30), ("Salade", 60)],
     tags=["plaisir"], p=("Lardons", ["Lardons", "Bacon"]), f=("Emmental râpé", ["Emmental râpé", "Mozzarella râpée", "Cheddar"]))
plat("Côtes de porc grillées, patates douces, salade", [("Porc (échine)", 170), ("Patates douces", 300), ("Salade", 60), ("Huile", 8)])
plat("Brochettes de {p} et légumes grillés, pommes de terre", [("Poulet", 150), ("Poivrons", 80), ("Courgettes", 80), ("Oignons", 30), ("Pommes de terre", 300), ("Huile", 8)], p=("Poulet", VIANDE_BLANCHE + ["Merguez"]))
plat("Croque-madame ({f}), frites au four", [("Jambon", 60), ("Pain de mie", 100), ("Œufs", 1), ("Emmental râpé", 25), ("Pommes de terre", 150)], tags=["plaisir"], f=("Emmental râpé", ["Emmental râpé", "Mozzarella râpée", "Cheddar"]))

section("Salades et bols")
plat("Salade César, {p} ({f})", [("Poulet", 150), ("Salade", 100), ("Pain complet", 50), ("Emmental râpé", 15), ("Tomates", 80), ("Huile", 10)], p=("Poulet", VOLAILLE + ["Crevettes"]), f=("Emmental râpé", FROMAGE))
plat("Salade niçoise au thon", [("Thon (conserve)", 120), ("Œufs", 1), ("Tomates", 120), ("Haricots verts", 100), ("Pommes de terre", 220), ("Salade", 50), ("Huile", 10)], tags=["poisson"])
plat("Poke bowl, {p}, riz, avocat, concombre", [("Thon (conserve)", 120), ("Riz (sec)", 80), ("Avocat (chair)", 60), ("Concombre", 80), ("Carottes", 60), ("Maïs", 40)], tags=["poisson"], p=("Thon (conserve)", POISSON_PLUS))
plat("Salade de riz au thon, maïs, tomates", [("Thon (conserve)", 120), ("Riz (sec)", 80), ("Maïs", 60), ("Tomates", 100), ("Œufs", 1), ("Huile", 10)], tags=["poisson"])
plat("Salade de pâtes, {p}, tomates, maïs", [("Poulet", 140), ("Pâtes (sèches)", 80), ("Tomates", 100), ("Maïs", 50), ("Concombre", 80), ("Huile", 10)], p=("Poulet", ["Poulet", "Jambon", "Thon (conserve)"]))
plat("Salade de lentilles, {p}, carottes", [("Lardons", 80), ("Lentilles vertes (sèches)", 70), ("Carottes", 100), ("Oignons", 20), ("Huile", 10)], p=("Lardons", ["Lardons", "Boucané", "Jambon"]))
plat("Buddha bowl, {p}, patate douce, brocoli", [("Dinde (escalope)", 150), ("Patates douces", 280), ("Brocoli", 150), ("Pois chiches (égouttés)", 50), ("Huile", 8)], p=("Dinde (escalope)", VOLAILLE))
plat("Salade de pommes de terre, {p}, haricots verts", [("Jambon", 100), ("Pommes de terre", 300), ("Haricots verts", 120), ("Oignons", 20), ("Huile", 10)], p=("Jambon", ["Jambon", "Saucisses fumées", "Thon (conserve)"]))
plat("Salade de boulgour, {p}, concombre, tomates", [("Poulet", 140), ("Boulgour", 80), ("Concombre", 100), ("Tomates", 100), ("Huile", 10)], p=("Poulet", ["Poulet", "Crevettes"]))
plat("Wrap froid, {p}, avocat, crudités", [("Poulet", 130), ("Wraps", 2), ("Avocat (chair)", 50), ("Salade", 40), ("Carottes", 60)], p=("Poulet", ["Poulet", "Jambon", "Thon (conserve)"]))
plat("Salade de semoule, pois chiches, {p}", [("Poulet", 130), ("Semoule", 70), ("Pois chiches (égouttés)", 60), ("Tomates", 100), ("Concombre", 80), ("Huile", 10)], p=("Poulet", ["Poulet", "Merguez"]))
plat("Salade tiède de patates douces, {p}, épinards", [("Bacon", 70), ("Patates douces", 300), ("Épinards", 120), ("Oignons", 20), ("Huile", 8)], p=("Bacon", CHARCUT))


# ---------- Assemblage ----------
def slug(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80]

COEF = {"proteine": 0.8, "feculent": 0.5, "legume": 1.2, "matiere_grasse": 0.75, "autre": 0.75}
ENTIERS = {"Œufs", "Wraps", "Pains burger"}

def arrondi(a, q):
    return max(1, round(q)) if a in ENTIERS else max(5, int(round(q / 5.0) * 5))

def nom_de(modele, p, f):
    n = modele.replace("{p}", LAB[p] if p else "").replace("{f}", LAB[f])
    return n[0].upper() + n[1:]

def assembler(catalogue):
    out = []
    for r in R:
        p0 = r["p"][0] if r["p"] else None
        f0 = r["f"][0] if r["f"] else None
        nom = nom_de(r["nom"], p0, f0)
        for a, _ in r["items"]:
            assert a in catalogue, f"{nom} : {a} absent du catalogue"
        nic = [[a, q] for a, q in r["items"]]
        aur = [[a, arrondi(a, q * COEF[catalogue[a]["role"]])] for a, q in r["items"]]
        poisson = any(catalogue[a]["rayon"] == "Poisson" for a, _ in r["items"])
        tags = sorted(set(r["tags"]) | ({"poisson"} if poisson else set()))
        rec = {"id": slug(nom), "nom": nom, "repas": r["repas"], "tags": tags, "source": SOURCE,
               "portions": {"nicolas": nic, "aurelie": aur}}
        var = []
        for cle, choix in (("p", r["p"]), ("f", r["f"])):
            if not choix: continue
            de, liste = choix
            assert de in [a for a, _ in r["items"]], f"{nom} : {de} n'est pas un ingrédient"
            vers = []
            for b in liste:
                if b == de: continue
                assert b is None or b in catalogue, f"{nom} : {b} absent du catalogue"
                n = nom_de(r["nom"], b if cle == "p" else p0, b if cle == "f" else f0)
                v = {"a": b, "nom": n}
                if (de, b) in FACTEUR: v["f"] = FACTEUR[(de, b)]
                vers.append(v)
            if vers: var.append({"de": de, "vers": vers})
        if var: rec["variantes"] = var
        rec["_section"] = r["section"]
        out.append(rec)
    ids = [x["id"] for x in out]
    assert len(ids) == len(set(ids)), "identifiants en double"
    return out

def carte(nouvelles, catalogue):
    """docs/bibliotheque.md : les plats par cuisine, avec leurs variantes, pour piocher des idées."""
    nouveaux = [a for a in PRODUITS]
    l = ["# Bibliothèque de plats", "",
         f"{len(nouvelles)} plats écrits pour Marmite le 05/10/2026, chacun avec une viande, un poisson ou une charcuterie. "
         f"Entre crochets, les variantes : un ingrédient remplacé par un autre donne un plat de plus "
         f"({sum(len(v['vers']) for x in nouvelles for v in x.get('variantes', []))} variantes). "
         "Le chef les propose comme les autres plats ; un produit exclu dans Profil retire les variantes qui le contiennent.", "",
         "Repères : ★ plaisir, ≈ poisson. Quantités par personne dans l'app (calées chaque jour sur les objectifs de chacun).", ""]
    for sec in dict.fromkeys(x["_section"] for x in nouvelles):
        lot = [x for x in nouvelles if x["_section"] == sec]
        l += [f"## {sec} ({len(lot)})", ""]
        for x in lot:
            marque = ("★ " if "plaisir" in x["tags"] else "") + ("≈ " if "poisson" in x["tags"] else "")
            var = [w["nom"] for v in x.get("variantes", []) for w in v["vers"]]
            ingr = ", ".join(a.lower() if a not in ("Œufs",) else "œufs" for a, _ in x["portions"]["nicolas"])
            l.append(f"- {marque}**{x['nom']}** : {ingr}." + (f" [{' · '.join(var)}]" if var else ""))
        l.append("")
    l += ["## Produits ajoutés au catalogue", "",
          "Prix estimés, corrigés au premier prix payé (ticket ou case cochée).", ""]
    for a in nouveaux:
        c = catalogue[a]
        l.append(f"- {a} : {c['achat']}, {str(c['prix']).replace('.', ',')} {'€/kg' if c['vrac'] else '€'}")
    os.makedirs(os.path.join(ICI, "..", "docs"), exist_ok=True)
    open(os.path.join(ICI, "..", "docs", "bibliotheque.md"), "w", encoding="utf-8").write("\n".join(l) + "\n")


if __name__ == "__main__":
    pc = os.path.join(DON, "catalogue.json"); cat = json.load(open(pc, encoding="utf-8"))
    for a, p in PRODUITS.items():
        if a not in cat["produits"]: cat["produits"][a] = p
    json.dump(cat, open(pc, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pr = os.path.join(DON, "recettes.json"); rec = json.load(open(pr, encoding="utf-8"))
    nouvelles = assembler(cat["produits"])
    anciens = {x["id"] for x in rec["recettes"] if x.get("source") != SOURCE}
    double = [x["id"] for x in nouvelles if x["id"] in anciens]
    assert not double, f"déjà dans la bibliothèque : {double}"
    carte(nouvelles, cat["produits"])
    for x in nouvelles: x.pop("_section", None)
    rec["recettes"] = [x for x in rec["recettes"] if x.get("source") != SOURCE] + nouvelles
    json.dump(rec, open(pr, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    nv = sum(len(v["vers"]) for x in nouvelles for v in x.get("variantes", []))
    print(f"{len(nouvelles)} plats, {nv} variantes, {sum('plaisir' in x['tags'] for x in nouvelles)} plaisir, "
          f"{sum('poisson' in x['tags'] for x in nouvelles)} poisson ; catalogue : {len(cat['produits'])} produits")
