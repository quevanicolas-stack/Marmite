"""Assemble app/marmite.html = marmite_template.html + donnees/appdata.json (remplace __DATA__)."""
import os
ICI = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(ICI, "marmite_template.html"), encoding="utf-8").read()
d = open(os.path.join(ICI, "..", "donnees", "appdata.json"), encoding="utf-8").read()
assert "__DATA__" in t
open(os.path.join(ICI, "marmite.html"), "w", encoding="utf-8").write(t.replace("__DATA__", d))
print("app/marmite.html construit")
