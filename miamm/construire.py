"""Assemble Miamm : app.html + moteur.js + badge de la mascotte + blocs de donnees/ (catalogue, recettes, réglages) → miamm.html."""
import json, pathlib
ICI = pathlib.Path(__file__).resolve().parent
DONNEES = ICI.parent / "donnees"

def construire():
    lire = lambda f: json.loads((DONNEES / f).read_text(encoding="utf-8"))
    donnees = {"catalogue": lire("catalogue.json")["produits"], "recettes": lire("recettes.json")["recettes"], "reglages": lire("reglages.json")}
    page = (ICI / "app.html").read_text(encoding="utf-8")
    moteur = (ICI / "moteur.js").read_text(encoding="utf-8")
    images = {cle: (ICI / "logo" / f"{nom}.txt").read_text().strip() for cle, nom in (("__BADGE__", "badge-192"), ("__CHEF_COURSES__", "chef-courses"), ("__CHEF_STOCK__", "chef-stock"))}
    assert page.count("__DATA__") == 1 and page.count("__MOTEUR__") == 1 and all(page.count(cle) == 1 for cle in images)
    # « </ » échappé pour que rien dans les données ne ferme la balise script
    data = json.dumps(donnees, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for cle, url in images.items(): page = page.replace(cle, url)
    page = page.replace("__DATA__", data).replace("__MOTEUR__", moteur)
    (ICI / "miamm.html").write_text(page, encoding="utf-8")
    print("miamm/miamm.html construit")

if __name__ == "__main__":
    construire()
