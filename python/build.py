import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from data import NUT
from menu import DAYS, BK_N, BK_A, d
from adjust import adj

F = "Arial"
def font(b=False, c="000000", s=10, i=False): return Font(name=F, bold=b, color=c, size=s, italic=i)
HEAD = PatternFill("solid", fgColor="2F4F4F")
DAYFILL = [PatternFill("solid", fgColor="FFFFFF"), PatternFill("solid", fgColor="F2F5F4")]
PLAISIR = PatternFill("solid", fgColor="FCE4D6")
POISSON = PatternFill("solid", fgColor="DDEBF7")
INPUT = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
BLUE = "0000FF"

JOURS = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
def dd(s, p): return {k: adj(p, k, v) for k, v in d(s).items()}
def fmt(q): return str(int(q)) if q == int(q) else str(q).replace('.', ',')
def txt(x):
    out = []
    for ing, q in x.items():
        b, u, _, _ = NUT[ing]
        if ing == 'Œufs': out.append(f"{fmt(q)} œuf" + ("s" if q > 1 else ""))
        elif ing == 'Wraps': out.append(f"{fmt(q)} wrap" + ("s" if q > 1 else ""))
        elif ing == 'Pains burger': out.append(f"{fmt(q)} pain burger")
        else: out.append(f"{ing} {fmt(q)} {u}")
    return " · ".join(out)

wb = Workbook()

# ---------- Valeurs ----------
wv = wb.active; wv.title = "Valeurs"
wv.append(["Aliment", "Base", "Unité", "kcal par base", "Protéines (g) par base"])
for ing, (b, u, k, p) in NUT.items(): wv.append([ing, b, u, k, p])
nv = wv.max_row
wv.cell(row=nv + 2, column=1, value="Valeurs moyennes arrondies (ordre de grandeur des tables de composition type Ciqual/Anses). Viandes, poissons, féculents : poids crus ou secs ; lentilles : égouttées ; œufs, wraps, pains burger : par unité (œuf ≈ 60 g, wrap ≈ 60 g, pain burger ≈ 75 g). Les chiffres en bleu sont modifiables.").font = font(i=True, s=9)
for c in range(1, 6):
    h = wv.cell(row=1, column=c); h.font = font(True, "FFFFFF"); h.fill = HEAD; h.border = BORDER
for r in range(2, nv + 1):
    for c in range(1, 6):
        cell = wv.cell(row=r, column=c); cell.border = BORDER
        cell.font = font(c="000000" if c in (1, 3) else BLUE)
for c, w in zip("ABCDE", (28, 8, 8, 14, 20)): wv.column_dimensions[c].width = w
wv.freeze_panes = "A2"

# ---------- Menu (une ligne par aliment) + Détail (lié au Menu) ----------
from openpyxl.styles import Alignment as AL
wm = wb.create_sheet("Menu", 0)
wd = wb.create_sheet("Détail")
wd.append(["Date", "Repas", "Plat", "Personne", "Aliment", "Quantité", "Unité", "kcal", "Protéines (g)", "Course"])
wm["A1"] = "Menu du 1er au 21 octobre 2026 — Nicolas et Aurélie"; wm["A1"].font = font(True, s=14)
wm["A2"] = ("Une ligne par aliment. Poids crus (viandes, poissons, légumes, pommes de terre) ou secs (riz, pâtes) ; lentilles égouttées ; "
            "huile = cuisson + assaisonnement. Les quantités en bleu se modifient ici : Nutrition, Courses, listes individuelles et Budget se recalculent.")
wm["A2"].font = font(i=True, s=9); wm["A2"].alignment = WRAP; wm.merge_cells("A2:F2"); wm.row_dimensions[2].height = 42
wm["A3"] = "Légende : orange = repas plaisir · bleu = repas poisson · case vide = aliment non prévu pour cette personne"; wm["A3"].font = font(i=True, s=9)
hdr = ["Repas", "Plat", "Aliment", "Nicolas", "Aurélie", "Unité"]
for c, h in enumerate(hdr, 1):
    cell = wm.cell(row=5, column=c, value=h); cell.font = font(True, "FFFFFF"); cell.fill = HEAD; cell.border = BORDER
DAYHEAD = PatternFill("solid", fgColor="5B7F7A")
MEALFILL = {"Petit-déjeuner": PatternFill("solid", fgColor="FFFFFF"), "Déjeuner": PatternFill("solid", fgColor="F7F9F8"),
            "Dîner": PatternFill("solid", fgColor="FFFFFF"), "Dessert": PatternFill("solid", fgColor="F2F2F2")}
r = 6
for i, (day, dej, din, des, tag) in enumerate(DAYS):
    dt = datetime.date(2026, 10, day)
    label = f"{JOURS[dt.weekday()].capitalize()} {day} octobre"
    if tag == "PLAISIR": label += " — repas plaisir"
    if day == 1: label += " — course 1 (du 1er au 5)"
    if day == 6: label += " — grosses courses (du 6 au 21)"
    wm.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    hc = wm.cell(row=r, column=1, value=label); hc.font = font(True, "FFFFFF", s=11); hc.fill = DAYHEAD
    hc.alignment = AL(vertical="center"); wm.row_dimensions[r].height = 20
    r += 1
    meals = [("Petit-déjeuner", ("Smoothie + œuf (Nicolas) / œufs, jambon, pain, pomme (Aurélie)", BK_N, BK_A)),
             ("Déjeuner", dej), ("Dîner", din), ("Dessert", des)]
    for rep, (plat, n, a) in meals:
        xn, xa = dd(n, 'N'), dd(a, 'A')
        ings = list(xn.keys()) + [k for k in xa.keys() if k not in xn]
        fill = MEALFILL[rep]
        if tag == "PLAISIR" and rep == "Déjeuner": fill = PLAISIR
        if plat.startswith("Poisson"): fill = POISSON
        r0 = r
        for ing in ings:
            unit = NUT[ing][1]
            vals = [rep, plat, ing, xn.get(ing), xa.get(ing), "unité(s)" if unit == "unité" else unit]
            for c, v in enumerate(vals, 1):
                cell = wm.cell(row=r, column=c, value=v); cell.fill = fill; cell.border = BORDER
                cell.font = font(b=(c == 1), c=BLUE if c in (4, 5) else "000000")
                cell.alignment = AL(vertical="top", wrap_text=(c == 2))
                if c in (4, 5): cell.number_format = '0;-0;""'
            for pers, col in (("Nicolas", "D"), ("Aurélie", "E")):
                wd.append([dt, rep, plat, pers, ing, f"=Menu!{col}{r}", NUT[ing][1], None, None, 1 if day <= 5 else 2])
                dr = wd.max_row
                wd.cell(row=dr, column=8, value=f"=F{dr}/INDEX(Valeurs!$B$2:$B${nv},MATCH(E{dr},Valeurs!$A$2:$A${nv},0))*INDEX(Valeurs!$D$2:$D${nv},MATCH(E{dr},Valeurs!$A$2:$A${nv},0))")
                wd.cell(row=dr, column=9, value=f"=F{dr}/INDEX(Valeurs!$B$2:$B${nv},MATCH(E{dr},Valeurs!$A$2:$A${nv},0))*INDEX(Valeurs!$E$2:$E${nv},MATCH(E{dr},Valeurs!$A$2:$A${nv},0))")
            r += 1
        if r - 1 > r0:
            wm.merge_cells(start_row=r0, start_column=1, end_row=r - 1, end_column=1)
            wm.merge_cells(start_row=r0, start_column=2, end_row=r - 1, end_column=2)
    r += 1  # ligne vide entre deux jours
for c, w in zip("ABCDEF", (15, 36, 26, 10, 10, 9)): wm.column_dimensions[c].width = w
wm.freeze_panes = "A6"
nd = wd.max_row
for c in range(1, 11):
    h = wd.cell(row=1, column=c); h.font = font(True, "FFFFFF"); h.fill = HEAD
for row in wd.iter_rows(min_row=2, max_row=nd):
    for cell in row:
        cell.font = font(c="008000" if cell.column == 6 else "000000")
    row[0].number_format = "DD/MM/YYYY"; row[7].number_format = "0"; row[8].number_format = "0.0"
for c, w in zip("ABCDEFGHIJ", (12, 14, 40, 10, 26, 10, 7, 8, 13, 9)): wd.column_dimensions[c].width = w
wd.freeze_panes = "A2"; wd.auto_filter.ref = f"A1:J{nd}"
wd["L1"] = "Onglet de calcul : les quantités viennent du Menu (vert = lien). Modifie les quantités dans le Menu, pas ici."
wd["L1"].font = font(i=True, s=9)

# ---------- Nutrition ----------
wn = wb.create_sheet("Nutrition", 1)
wn["A1"] = "Apports estimés par jour"; wn["A1"].font = font(True, s=14)
wn["A2"] = "Repères : Nicolas 1 850-1 950 kcal et 110 g de protéines ou plus ; Aurélie 1 350-1 450 kcal et 85 g ou plus (Mifflin-St Jeor, activité légère, déficit ~500 kcal). Estimations, pas des prescriptions."
wn["A2"].font = font(i=True, s=9); wn["A2"].alignment = WRAP; wn.merge_cells("A2:E2"); wn.row_dimensions[2].height = 30
H = ["Date", "Nicolas kcal", "Nicolas protéines (g)", "Aurélie kcal", "Aurélie protéines (g)"]
for c, h in enumerate(H, 1):
    cell = wn.cell(row=4, column=c, value=h); cell.font = font(True, "FFFFFF"); cell.fill = HEAD; cell.border = BORDER
for i, (day, *_rest) in enumerate(DAYS):
    rr = 5 + i
    wn.cell(row=rr, column=1, value=datetime.date(2026, 10, day)).number_format = "ddd DD/MM"
    for c, (col, pers) in zip((2, 3, 4, 5), (("H", "Nicolas"), ("I", "Nicolas"), ("H", "Aurélie"), ("I", "Aurélie"))):
        wn.cell(row=rr, column=c, value=f'=SUMIFS(Détail!${col}$2:${col}${nd},Détail!$A$2:$A${nd},$A{rr},Détail!$D$2:$D${nd},"{pers}")')
last = 5 + len(DAYS) - 1
rows_avg = [("Moyenne semaine 1 (1-7)", 5, 11), ("Moyenne semaine 2 (8-14)", 12, 18), ("Moyenne semaine 3 (15-21)", 19, 25), ("Moyenne 21 jours", 5, last)]
for j, (lab, a, b) in enumerate(rows_avg):
    rr = last + 2 + j
    wn.cell(row=rr, column=1, value=lab).font = font(True)
    for c in range(2, 6):
        col = get_column_letter(c)
        cell = wn.cell(row=rr, column=c, value=f"=AVERAGE({col}{a}:{col}{b})"); cell.font = font(True)
for row in wn.iter_rows(min_row=5, max_row=last + 5, min_col=1, max_col=5):
    for cell in row:
        if cell.row <= last or cell.value is not None:
            cell.border = BORDER
        if cell.column in (2, 4): cell.number_format = "#,##0"
        if cell.column in (3, 5): cell.number_format = "0"
        if cell.font.name != F or not cell.font.bold: cell.font = font(b=cell.font.bold)
for c, w in zip("ABCDE", (26, 14, 20, 14, 20)): wn.column_dimensions[c].width = w

# ---------- Courses : 2 courses (01/10 et 06/10), Nicolas / Aurélie séparés ----------
from copy import copy
wc = wb.create_sheet("Courses")
wc["A1"] = "Liste de courses — Nicolas et Aurélie (1er au 21 octobre)"; wc["A1"].font = font(True, s=14)
wc["A2"] = ("Course 1 le 01/10 : uniquement ce qu'il faut du 1er au 5 inclus. Course 2 le 06/10 : tout ce qu'il faut du 6 au 21, "
            "restes de la course 1 déduits. Une ligne par produit, besoins de Nicolas et d'Aurélie séparés. "
            "À acheter = nombre de conditionnements, ou grammes si vrac. Jaune = modifiable. Case vide = rien à acheter ou pas de besoin.")
wc["A2"].font = font(i=True, s=9); wc["A2"].alignment = WRAP; wc.merge_cells("A2:X2"); wc.row_dimensions[2].height = 30
# (catégorie, aliment, achat par, cond, vrac, rendement, prix, stock, conservation, besoins manuels [N1, A1, N2, A2])
P = [
 ("Viande", "Poulet", "paquet 1 kg", 1000, 0, 1, 11.27, 0, "Congeler en portions d'un repas le jour de l'achat.", None),
 ("Viande", "Bœuf", "paquet 900 g", 900, 0, 1, 8.40, 0, "Congeler en portions.", None),
 ("Viande", "Lardons", "paquet 200 g", 200, 0, 1, 1.27, 0, "Longue DLC sous vide, se congèle.", None),
 ("Viande", "Jambon", "paquet 500 g (hypothèse)", 500, 0, 1, 5.62, 0, "2 à 3 jours une fois ouvert : préférer plusieurs petits paquets.", None),
 ("Poisson", "Poisson blanc", "sachet 1 kg surgelé", 1000, 0, 1, 7.49, 0, "Surgelé.", None),
 ("Œufs et laitages", "Œufs", "boîte de 12", 12, 0, 1, 3.80, 0, "Vérifier une date au-delà du 21/10.", None),
 ("Œufs et laitages", "Lait", "brique 1 L", 1000, 0, 1, 1.19, 0, "UHT : se garde des mois fermé.", None),
 ("Œufs et laitages", "Yaourt nature", "pot 500 g", 500, 0, 1, 3.25, 0, "Vérifier une date au-delà du 21/10.", None),
 ("Œufs et laitages", "Mozzarella râpée", "sachet 150 g", 150, 0, 1, 3.13, 0, "Se congèle.", None),
 ("Œufs et laitages", "Cheddar", "vrac (g)", 1, 1, 1, 16.50, 0, "", None),
 ("Féculents", "Riz (sec)", "paquet 1 kg", 1000, 0, 1, 2.34, 0, "", None),
 ("Féculents", "Pâtes (sèches)", "paquet 500 g", 500, 0, 1, 1.45, 0, "", None),
 ("Féculents", "Pâtes à lasagnes (sèches)", "paquet 500 g", 500, 0, 1, 2.47, 0, "", None),
 ("Féculents", "Flocons d'avoine", "paquet 500 g", 500, 0, 1, 1.71, 0, "", None),
 ("Féculents", "Pommes de terre", "vrac (g)", 1, 1, 1, 1.45, 0, "Au sec, à l'ombre, loin des oignons : germent vite à la chaleur.", None),
 ("Féculents", "Patates douces", "vrac (g)", 1, 1, 1, 3.29, 0, "Hors frigo, 1 à 2 semaines.", None),
 ("Féculents", "Wraps", "paquet de 8", 8, 0, 1, 2.74, 0, "Longue conservation fermés.", None),
 ("Pain", "Pains burger", "paquet de 2", 2, 0, 1, 3.00, 0, "Pour le 4 octobre.", None),
 ("Pain", "Pain complet", "pièce ~100 g (hypothèse)", 100, 0, 1, 1.20, 0, "Congeler en tranches, sortir la veille.", None),
 ("Légumes", "Haricots verts", "sachet 440 g surgelé", 440, 0, 1, 1.72, 0, "Surgelés.", None),
 ("Légumes", "Carottes", "vrac (g)", 1, 1, 1, 1.99, 0, "2 à 3 semaines au bac à légumes.", None),
 ("Légumes", "Oignons", "vrac (g)", 1, 1, 1, 2.49, 0, "Plusieurs semaines au sec.", None),
 ("Légumes", "Maïs", "boîte (~140 g égouttés)", 140, 0, 1, 0.89, 0, "Conserve.", None),
 ("Légumes", "Tomates", "vrac (g)", 1, 1, 1, 2.79, 0, "Risque sur 16 jours : en prendre une partie peu mûre ; pour les plats cuits de fin de période, la conserve fait l'affaire.", None),
 ("Légumes", "Courgettes", "vrac (g)", 1, 1, 1, 1.49, 0, "Risque sur 16 jours (~1 semaine au frigo) : congeler crues en rondelles celles des plats cuits de la 2e semaine.", None),
 ("Légumes", "Poivrons", "vrac (g)", 1, 1, 1, 13.98, 0, "13,98 €/kg. 1 à 2 semaines au frigo, se congèlent crus en lanières.", None),
 ("Légumes", "Aubergines", "vrac (g)", 1, 1, 1, 2.29, 0, "Celles du barbecue du 18 risquent de ne pas tenir : prendre les plus fermes.", None),
 ("Légumes", "Champignons", "barquette 250 g (hypothèse)", 250, 0, 1, 1.08, 0, "Risque : 3 à 5 jours. Pour les repas après le 11, champignons en conserve ou surgelés.", None),
 ("Légumes", "Salade", "pièce ~300 g utiles", 300, 0, 1, 1.39, 0, "Risque : 4 à 7 jours. En fin de période, remplacer par des carottes râpées.", None),
 ("Fruits", "Pommes", "vrac (g)", 1, 1, 1, 2.99, 0, "3 à 4 semaines au frigo.", None),
 ("Fruits", "Bananes", "vrac (g)", 1, 1, 1, 1.89, 0, "Risque sur 16 jours : acheter vertes, congeler en rondelles les mûres (parfait pour le smoothie).", None),
 ("Fruits", "Avocat (chair)", "avocat ~350 g de chair (hypothèse)", 350, 0, 1, 1.99, 0, "Choisir 3 stades de maturité : un mûr pour le 11-12, deux fermes pour le 17-18.", None),
 ("Fruits", "Mangue", "vrac (g, rendement 70 %)", 1, 1, 0.7, 8.99, 0, "Celle du 14 : la prendre ferme.", None),
 ("Fruits", "Ananas", "pièce ~400 g de chair (hypothèse)", 400, 0, 1, 2.69, 0, "Mangés les 9 et 10 : pas de souci.", None),
 ("Desserts", "Glace", "bac 500 g", 500, 0, 1, 2.49, 0, "Congélateur.", None),
 ("Desserts", "Chocolat noir", "500 g", 500, 0, 1, 5.26, 0, "", None),
 ("Épicerie", "Café", "paquet 1 kg", 1000, 0, 1, 16.00, 0, "Hors menu : 100 % Nicolas (modifiable).", [238, 0, 762, 0]),
 ("Épicerie", "Eau (bouteilles 5 L)", "bouteille 5 L", 5, 0, 1, 1.54, 0, "Hors menu : moitié chacun (modifiable).", [10, 10, 32, 32]),
 ("Épicerie", "Citrons", "pièce", 1, 0, 1, None, 0, "Prix à saisir. Poulet citronné, poisson.", [1, 1, 2, 2]),
 ("Épicerie", "Sauce soja", "flacon", 1, 0, 1, None, 0, "Prix à saisir. Partagé 50/50.", [0.5, 0.5, 0, 0]),
 ("Épicerie", "Concentré de tomate", "tube ou boîte", 1, 0, 1, None, 0, "Prix à saisir. Partagé 50/50.", [0.5, 0.5, 0, 0]),
 ("Épicerie", "Moutarde / ketchup", "flacon", 1, 0, 1, None, 0, "Prix à saisir. Burger du 4.", [0.5, 0.5, 0, 0]),
 ("Épicerie", "Ail, gingembre, curcuma", "si pas en stock", 1, 0, 1, None, 0, "Prix à saisir. Partagé 50/50.", [0.5, 0.5, 0, 0]),
 ("Épicerie", "Levure boulangère", "sachet", 1, 0, 1, None, 0, "Prix à saisir. Pizza du 11.", [0, 0, 0.5, 0.5]),
 ("Déjà en stock", "Lentilles (égouttées)", "3 boîtes de 530 g", 530, 0, 1, 0, 1590, "Ton stock, utilisé en entier.", None),
 ("Déjà en stock", "Huile", "stock", 1000, 0, 1, 0, 1000, "Vérifie qu'il en reste ~700 g.", None),
 ("Déjà en stock", "Farine", "stock", 1000, 0, 1, 0, 500, "Pizza, quiche, béchamel.", None),
]
GROUPS = [("Produit", 1, 9, "2F4F4F"), ("Course 1 — jeudi 01/10 (du 1er au 5)", 10, 13, "4F7A6F"),
          ("Course 2 — mardi 06/10 (du 6 au 21)", 14, 17, "5E7FA6"), ("Total 21 jours", 18, 23, "7F6A3F"),
          ("", 24, 24, "2F4F4F"), ("Calculs", 25, 26, "808080")]
for lab, c1, c2, col in GROUPS:
    if c2 > c1: wc.merge_cells(start_row=4, start_column=c1, end_row=4, end_column=c2)
    cell = wc.cell(row=4, column=c1, value=lab); cell.font = font(True, "FFFFFF")
    cell.alignment = Alignment(horizontal="center")
    for c in range(c1, c2 + 1): wc.cell(row=4, column=c).fill = PatternFill("solid", fgColor=col)
HD = ["Catégorie", "Aliment", "Unité", "Achat par", "Conditionnement", "Vrac (1 = oui)", "Rendement", "Prix (€ par achat, ou €/kg si vrac)", "Stock déjà là",
      "Besoin Nicolas", "Besoin Aurélie", "À acheter", "Dépense (€)",
      "Besoin Nicolas", "Besoin Aurélie", "À acheter", "Dépense (€)",
      "Besoin Nicolas", "Besoin Aurélie", "Coût Nicolas (€)", "Coût Aurélie (€)", "Reste après le 21", "Valeur du reste (€)",
      "Conservation / commentaire", "Prix par g, ml ou unité (€)", "Reste après la course 1"]
for c, h in enumerate(HD, 1):
    cell = wc.cell(row=5, column=c, value=h); cell.font = font(True, "FFFFFF"); cell.fill = copy(wc.cell(row=4, column=c).fill)
    cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center"); cell.border = BORDER
wc.row_dimensions[5].height = 45
DET = f"Détail!$F$2:$F${nd}"; DETE = f"Détail!$E$2:$E${nd}"; DETD = f"Détail!$D$2:$D${nd}"; DETJ = f"Détail!$J$2:$J${nd}"
first = 6
for i, (cat, ing, achat, cond, vrac, rend, prix, stock, cons, man) in enumerate(P):
    r = first + i
    unit = NUT[ing][1] if ing in NUT else ("L" if ing.startswith("Eau") else ("g" if ing == "Café" else "unité"))
    for c, v in {1: cat, 2: ing, 3: unit, 4: achat, 5: cond, 6: vrac, 7: rend, 8: prix, 9: stock, 24: cons}.items():
        wc.cell(row=r, column=c, value=v)
    need_cols = [(10, "Nicolas", 1), (11, "Aurélie", 1), (14, "Nicolas", 2), (15, "Aurélie", 2)]
    for j, (c, pers, k) in enumerate(need_cols):
        if man is None:
            wc.cell(row=r, column=c, value=f'=SUMIFS({DET},{DETE},$B{r},{DETD},"{pers}",{DETJ},{k})')
        else:
            cell = wc.cell(row=r, column=c, value=man[j]); cell.fill = INPUT; cell.font = font(c=BLUE)
    wc.cell(row=r, column=25, value=f'=IF(H{r}="",0,IF(F{r}=1,H{r}/1000/G{r},H{r}/E{r}))')
    def buy(net): return f"=IF({net}<=0,0,IF(F{r}=1,({net})/G{r},ROUNDUP(({net})/E{r},0)))"
    wc.cell(row=r, column=12, value=buy(f"J{r}+K{r}-I{r}"))
    wc.cell(row=r, column=26, value=f"=I{r}+IF(F{r}=1,L{r}*G{r},L{r}*E{r})-(J{r}+K{r})")
    wc.cell(row=r, column=16, value=buy(f"N{r}+O{r}-Z{r}"))
    for bc, dc in ((12, 13), (16, 17)):
        bl = get_column_letter(bc)
        wc.cell(row=r, column=dc, value=f'=IF(H{r}="",0,IF(F{r}=1,{bl}{r}/1000*H{r},{bl}{r}*H{r}))')
    wc.cell(row=r, column=18, value=f"=J{r}+N{r}")
    wc.cell(row=r, column=19, value=f"=K{r}+O{r}")
    wc.cell(row=r, column=20, value=f"=R{r}*Y{r}")
    wc.cell(row=r, column=21, value=f"=S{r}*Y{r}")
    wc.cell(row=r, column=22, value=f"=Z{r}+IF(F{r}=1,P{r}*G{r},P{r}*E{r})-(N{r}+O{r})")
    wc.cell(row=r, column=23, value=f"=V{r}*Y{r}")
last_p = first + len(P) - 1
QTY = '#,##0;-#,##0;""'; EUR = '#,##0.00 €;-#,##0.00 €;""'
PFILL = {10: "EAF1EF", 11: "EAF1EF", 12: "D5E3DF", 13: "D5E3DF", 14: "E8EEF6", 15: "E8EEF6", 16: "D1DDEC", 17: "D1DDEC"}
for row in wc.iter_rows(min_row=first, max_row=last_p, min_col=1, max_col=26):
    for cell in row:
        c = cell.column; cell.border = BORDER
        is_input = cell.fill is not None and cell.fill.fgColor is not None and str(cell.fill.fgColor.rgb).endswith("FFF2CC")
        if not is_input and c in PFILL: cell.fill = PatternFill("solid", fgColor=PFILL[c])
        if c in (8, 9): cell.fill = INPUT
        if c in (5, 6, 7, 8, 9): cell.font = font(c=BLUE)
        elif is_input: pass
        else: cell.font = font(b=(c in (2, 12, 16)))
        if c in (5, 9, 10, 11, 12, 14, 15, 16, 18, 19, 22, 26): cell.number_format = QTY
        if c in (13, 17, 20, 21, 23): cell.number_format = EUR
        if c == 7: cell.number_format = '0%'
        if c == 8: cell.number_format = '#,##0.00 €'
        if c == 25: cell.number_format = '0.0000 €'
        if c in (4, 24): cell.alignment = WRAP
        if c == 1: cell.font = font(i=True, s=9, c="595959")
tr = last_p + 2
wc.cell(row=tr, column=2, value="Dépense en magasin (€)").font = font(True)
for dc in (13, 17, 20, 21, 23):
    col = get_column_letter(dc)
    cell = wc.cell(row=tr, column=dc, value=f"=SUM({col}{first}:{col}{last_p})"); cell.font = font(True); cell.number_format = EUR
wc.cell(row=tr + 1, column=2, value="Consommation — Nicolas (€)").font = font(True)
wc.cell(row=tr + 2, column=2, value="Consommation — Aurélie (€)").font = font(True)
for (nc, ac, dc) in ((10, 11, 13), (14, 15, 17)):
    nl, al = get_column_letter(nc), get_column_letter(ac)
    c1 = wc.cell(row=tr + 1, column=dc, value=f"=SUMPRODUCT({nl}{first}:{nl}{last_p},$Y${first}:$Y${last_p})"); c1.number_format = EUR; c1.font = font(True)
    c2 = wc.cell(row=tr + 2, column=dc, value=f"=SUMPRODUCT({al}{first}:{al}{last_p},$Y${first}:$Y${last_p})"); c2.number_format = EUR; c2.font = font(True)
wc.cell(row=tr + 3, column=2, value="Dépense totale sur 21 jours (€)").font = font(True)
t = wc.cell(row=tr + 3, column=13, value=f"=M{tr}+Q{tr}"); t.font = font(True); t.number_format = EUR
for c, w in zip([get_column_letter(i) for i in range(1, 27)],
                (13, 24, 7, 18, 11, 7, 9, 11, 9, 9, 9, 9, 10, 9, 9, 9, 10, 9, 9, 11, 11, 10, 10, 46, 11, 11)):
    wc.column_dimensions[c].width = w
wc.freeze_panes = "C6"

# ---------- Budget ----------
wbud = wb.create_sheet("Budget")
wbud["A1"] = "Budget individuel du 1er au 21 octobre"; wbud["A1"].font = font(True, s=14)
wbud["A2"] = ("Chacun paie ce qu'il consomme au prix du gramme, du ml ou de l'unité. Les restes (paquets entamés, surgelés) repartent en stock "
              "sur le cycle suivant. Nicolas + Aurélie + reste en stock = dépense totale.")
wbud["A2"].font = font(i=True, s=9); wbud["A2"].alignment = WRAP; wbud.merge_cells("A2:E2"); wbud.row_dimensions[2].height = 30
BH = ["", "Nicolas", "Aurélie", "Reste en stock (reporté)", "Total"]
for c, h in enumerate(BH, 1):
    cell = wbud.cell(row=4, column=c, value=h); cell.font = font(True, "FFFFFF"); cell.fill = HEAD; cell.border = BORDER
    cell.alignment = Alignment(wrap_text=True, vertical="center")
lines = [
 ("Coût sur 21 jours (€)", f"=Courses!T{tr}", f"=Courses!U{tr}", f"=Courses!W{tr}", f"=Courses!M{tr+3}"),
 ("Part du total", "=B5/$E$5", "=C5/$E$5", "=D5/$E$5", "=E5/$E$5"),
 ("Par jour (€)", "=B5/21", "=C5/21", "", "=E5/21"),
 ("Par repas (€, 3 repas/jour)", "=B5/63", "=C5/63", "", "=E5/126"),
 ("Contrôle (doit faire 0)", "", "", "", "=E5-B5-C5-D5"),
]
for i, row in enumerate(lines):
    rr = 5 + i
    for c, v in enumerate(row, 1):
        cell = wbud.cell(row=rr, column=c, value=v if v != "" else None); cell.border = BORDER; cell.font = font(b=(c == 1))
        if i == 1: cell.number_format = '0.0%'
        elif c > 1: cell.number_format = '#,##0.00 €'
wbud.cell(row=11, column=1, value="Par course").font = font(True)
WH = ["", "Consommation Nicolas", "Consommation Aurélie", "Dépense en magasin"]
for c, h in enumerate(WH, 1):
    cell = wbud.cell(row=12, column=c, value=h if h else None); cell.font = font(True, "FFFFFF"); cell.fill = HEAD; cell.border = BORDER
    cell.alignment = Alignment(wrap_text=True, vertical="center")
for k, (lab, dc) in enumerate((("Course 1 — 01/10 (du 1er au 5)", "M"), ("Course 2 — 06/10 (du 6 au 21)", "Q"))):
    rr = 13 + k
    wbud.cell(row=rr, column=1, value=lab).font = font(True); wbud.cell(row=rr, column=1).border = BORDER
    for c, f in ((2, f"=Courses!{dc}{tr+1}"), (3, f"=Courses!{dc}{tr+2}"), (4, f"=Courses!{dc}{tr}")):
        cell = wbud.cell(row=rr, column=c, value=f); cell.number_format = '#,##0.00 €'; cell.border = BORDER; cell.font = font()
wbud.cell(row=16, column=1, value=("Course 1 : au plus juste pour 5 jours. Les conditionnements entamés (paquet de poulet, riz, avoine…) "
    "passent sur la course 2, ce qui explique une dépense de course 1 supérieure à la consommation des 5 jours.")).font = font(i=True, s=9)
wbud.merge_cells("A16:E16"); wbud.cell(row=16, column=1).alignment = WRAP; wbud.row_dimensions[16].height = 30
for c, w in zip("ABCDE", (32, 16, 16, 18, 14)): wbud.column_dimensions[c].width = w

wb._sheets = [wm, wbud, wc, wn, wd, wv]
wb.active = 0
import os; wb.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "excel", "menu_octobre_nicolas_aurelie.xlsx"))
print("saved", nd, "lignes détail")
