"""Assemble Popote : app.html + moteur.js + blocs de donnees/ (catalogue, recettes, réglages) → popote.html."""
import json, pathlib
ICI = pathlib.Path(__file__).resolve().parent
DONNEES = ICI.parent / "donnees"

def construire():
    lire = lambda f: json.loads((DONNEES / f).read_text(encoding="utf-8"))
    donnees = {"catalogue": lire("catalogue.json")["produits"], "recettes": lire("recettes.json")["recettes"], "reglages": lire("reglages.json")}
    page = (ICI / "app.html").read_text(encoding="utf-8")
    moteur = (ICI / "moteur.js").read_text(encoding="utf-8")
    assert page.count("__DATA__") == 1 and page.count("__MOTEUR__") == 1
    # « </ » échappé pour que rien dans les données ne ferme la balise script
    data = json.dumps(donnees, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = page.replace("__DATA__", data).replace("__MOTEUR__", moteur)
    (ICI / "popote.html").write_text(page, encoding="utf-8")
    print("popote/popote.html construit")

if __name__ == "__main__":
    construire()
