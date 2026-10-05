"""Prépare public/ pour Cloudflare : app/marmite.html devient index.html (avec manifeste, icônes et service
worker), plus les fichiers de statique/. La page reste la même que la version claude.ai : elle détecte seule
qu'elle tourne sur le serveur du foyer (/api/etat)."""
import pathlib, shutil
ICI = pathlib.Path(__file__).resolve().parent
PUBLIC = ICI / "public"
TETE = """<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" type="image/png" href="/icone-192.png">
<meta name="theme-color" content="#1B6B4A">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Marmite">
<script>if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));</script>
"""

def preparer():
    page = (ICI.parent / "app" / "marmite.html").read_text(encoding="utf-8")
    assert page.count("</head>") == 1, "en-tête de page introuvable"
    if PUBLIC.exists(): shutil.rmtree(PUBLIC)
    PUBLIC.mkdir()
    (PUBLIC / "index.html").write_text(page.replace("</head>", TETE + "</head>"), encoding="utf-8")
    for f in (ICI / "statique").iterdir(): shutil.copy(f, PUBLIC / f.name)
    print("public/ prêt :", ", ".join(sorted(p.name for p in PUBLIC.iterdir())))

if __name__ == "__main__":
    preparer()
