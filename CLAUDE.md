# Marmite — reprise du projet

Document de passation pour reprendre le travail dans Claude Code. Il résume toute la conversation d'origine (claude.ai, du 25 au 30 septembre 2026) et décrit l'état exact du code.

## 1. Contexte

- **Utilisateur** : Nicolas (Nico), vit à La Réunion (secteur Saint-Pierre). Compagne : Aurélie. Le foyer, c'est eux deux.
- **Deux projets alimentaires** sont nés dans cette conversation :
  1. **Marmite**, l'app personnelle du foyer. Elle est en service, et c'est le cœur de ce dossier.
  2. **L'assistant de décision alimentaire**, une app mobile grand public, au stade du prototype bêta sur papier. Voir `docs/prototype-beta-resume.md`.
- **Façon de travailler attendue** :
  - tout en français : interface, libellés, messages système, commentaires de code ;
  - réponses directes et denses, sans emojis ni relances ;
  - adopter un ton proche du sien, mais garder son propre esprit critique : remettre en question ses hypothèses, signaler les angles morts, proposer des alternatives ;
  - Nico se décrit lui-même comme « psycho-rigide » sur le suivi. La précision est un jeu pour lui, pas une contrainte.

## 2. Profils

| | Nicolas | Aurélie |
|---|---|---|
| Âge, taille | 38 ans, 1,80 m | 31 ans, 1,60 m |
| Poids de départ → objectif | 85 → 80 kg | 70 → 60 kg |
| Activité | salle 2 fois par semaine, sinon peu actif | idem |
| Cible par jour | 1 850 à 1 950 kcal, au moins 110 g de protéines | 1 350 à 1 450 kcal, au moins 85 g de protéines |
| Budget du cycle (réglage dans l'app) | 180 € | 170 € |
| Référence « liste initiale » | 208,94 € | 208,94 € (valeur recopiée, **à vérifier avec Nico**) |
| À éviter | fromage (sauf pizza, lasagnes, burger), poisson gras, trop de laitages | rien de déclaré |

Le foyer planifie par **cycles de 21 jours**. Il chiffre une liste complète pour le budget, puis achète en plusieurs courses, avec un objectif d'économies.

## 3. Le cycle d'octobre (données figées)

- **Période** : du jeudi 1er au mercredi 21 octobre 2026.
- **Repas** : 4 par jour et par personne (petit-déjeuner, déjeuner, dîner, dessert).
- **Petits-déjeuners** :
  - Nicolas : lait 250 ml, banane 100 g, flocons d'avoine 65 g, 1 œuf ;
  - Aurélie : 2 œufs, jambon 30 g, tomate 80 g, pain complet 40 g, pomme 150 g.
- **Repères du menu** : 7 repas de poisson (surgelé), 3 repas plaisir les 4, 11 et 18. Les 3 boîtes de lentilles déjà en stock (1 590 g égouttés) sont utilisées.
- **Portions d'Aurélie** : environ 80 % des protéines de Nicolas, environ la moitié des féculents, plus de légumes. Les coefficients fins sont dans `python/adjust.py`.
- **Moyennes par jour** : Nicolas environ 1 880 kcal et 108 g de protéines ; Aurélie environ 1 352 kcal et 91 g.
- **Coûts prévus** :
  - consommation de Nicolas : 176,92 € ; consommation d'Aurélie : 167,84 € ;
  - à l'origine : Course 1 le 01/10 (jours 1 à 5) 129,94 €, Course 2 le 06/10 (jours 6 à 21) 233,17 €, total 363,10 € ;
  - depuis le 30/09/2026, **courses hebdomadaires** recalculées par le moteur (`outils/courses_octobre.js`) : le 1er (jours 1 à 7) 152,53 €, le 8 (8 à 14) 124,25 €, le 15 (15 à 21) 83,81 €. L'ancienne liste reste dans `coursesDeuxFois` du fichier du mois.
- **Choix faits face à la liste d'achats initiale (produite par ChatGPT)** :
  - porc et saucisse retirés ;
  - bœuf réduit à 3 × 900 g, avec 4 repas remplacés par du poisson ;
  - poivrons à 13,98 €/kg en vrac ;
  - jambon : 700 g réellement nécessaires ;
  - avoine : 3 paquets de 500 g.
- **Condiments sans prix** : citrons, sauce soja, concentré de tomate, moutarde et ketchup, ail-gingembre-curcuma, levure. Ils sont en cases jaunes dans l'Excel, prix à saisir.
- **Risques de conservation**, puisque la Course 2 couvre 16 jours :
  - tomates, courgettes, champignons, salade, bananes et avocats s'abîment vite ;
  - les viandes sont à congeler en portions dès l'achat.

### Le classeur Excel `excel/menu_octobre_nicolas_aurelie.xlsx`

Il contient 8 onglets et environ 3 860 formules. Il est généré par `python/build.py`.

- **Menu** : une ligne par aliment. Les quantités en bleu sont modifiables. Chaque repas a sa couleur, et les jours poisson et plaisir sont surlignés.
- **Budget** : totaux, courbe, tableau par course.
- **Courses** : liste unique de 47 produits. Pour chacun : besoins de Nicolas et d'Aurélie, conditionnement, prix, restes reportés d'une course à l'autre, colonne « Conservation ».
- **Liste Nicolas / Liste Aurélie** : consommation individuelle et coût de chacun.
- **Nutrition** : kcal et protéines par jour, calculés avec SUMIFS sur l'onglet Détail.
- **Détail** : 929 lignes, filtrables.
- **Valeurs** : table nutritionnelle.

## 4. L'app Marmite

### Où elle vit

- **Publiée** : https://claude.ai/artifact/8Ez5pJQH4tzZ49GJLgvpB5. C'est une page hébergée par claude.ai, qui appartient au compte de Nico.
- **Capacités d'exécution déclarées** : `db`, pour les données privées synchronisées sur tous ses appareils ; `sample`, pour les appels à Claude de l'assistant ; `user`, pour l'identifiant.
- **Mise à jour** : republier `app/marmite.html` avec l'outil Artifact (action publish, avec l'`url` ci-dessus), sans redéclarer les capacités. Les sessions Claude Code web disposent de cet outil ; lire d'abord la version en ligne (action read) pour vérifier qu'elle n'a pas bougé. Republiée le 30/09/2026 depuis Claude Code (version 7 : cases et prix corrigés, repas remplaçable depuis la bibliothèque ; version 6 : le chef prépare le mois, archives ; version 5 : courses hebdomadaires, budget réel, quantité achetée, stock réel, budget du foyer, planning selon le stock ; version 4 : prix, dépassement, poubelle, jambon au gramme) ; elle correspond à `app/marmite.html`. Titre de la page : « Marmite ». Partage : « toute personne ayant le lien » (réglé dans le menu Partager de la page) ; chaque compte voit ses propres données (`db` par utilisateur).
- **En local** : ouvrir `app/marmite.html` suffit. Les données passent alors en localStorage et l'assistant est indisponible, car `window.claude` est absent. Tout le reste fonctionne.

### Construire

```bash
pip install -r requirements.txt          # une fois ; en session web, ne pas lancer « playwright install » :
                                          # playwright 1.56 correspond au Chromium préinstallé (/opt/pw-browsers)
# Archive d'octobre (ne sert plus qu'à reproduire octobre) :
cd python && python3 build.py            # régénère l'Excel (si menu.py / adjust.py changent)
                                          # ouvrir puis réenregistrer l'Excel dans un tableur pour recalculer les formules
python3 export_appdata.py                 # Excel + menu → donnees/appdata.json (archive, ne plus modifier)
python3 decouper.py                       # migration faite une fois : appdata.json → blocs de donnees/
                                          # (la relancer écrase les blocs : à éviter une fois qu'ils ont été modifiés)
# Chaîne courante :
cd ../app && python3 construire.py        # template + blocs de donnees/ → app/marmite.html
cd .. && for t in tests/*.py; do python3 $t || break; done && node tests/test_moteur.js
node outils/proposer_mois.js 2026-11 [graine] [--jours N] [--invites N] [--budget €] [--debut aaaa-mm-jj]
                                          # proposition du moteur → donnees/propositions/<id>.json + résumé
```

- Le code est un seul fichier HTML, en JavaScript sans framework ni outil de build.
- Les données sont injectées à la place de `__DATA__` dans `app/marmite_template.html`.
- Pour les tests Playwright, `window.claude` est simulé avec une réponse figée. Les polices Google sont bloquées, donc l'erreur console sur les fonts est normale.

### Identité visuelle

L'app reprend exactement la palette du site Fluent & Forward d'Aurélie :

| Rôle | Couleur |
|---|---|
| Vert signature | `#1B6B4A` |
| Fond sombre | `#10382A` |
| Or | `#C9A96E` |
| Crème | `#FAF7F2` |
| Sable | `#E8DDD0` |
| Brun (texte) | `#2C1810` |

- **Polices** : Plus Jakarta Sans pour les titres, DM Sans pour le texte.
- **Icônes** : tracé type Lucide, épaisseur 1,9.
- **Couleurs des repas** : petit-déjeuner or, déjeuner vert, dîner vert clair `#5E9C7F`, dessert bronze `#9C7A45`, avec des variantes éclaircies en sombre. Le brique `#A2412B` est réservé aux alertes.
- **Clin d'œil à Fluent & Forward** : dans le planning, les 4 repas de chaque jour sont des petites barres arrondies vert et or, comme les couvertures de séances.
- **Thème** : clair, sombre ou selon le système. Le bouton force le choix via `data-theme` sur `<html>`, mémorisé dans `localStorage["marmite-theme"]`.
- **Mise en page** : aucune page ne défile en largeur à 360 px (vérifié par les tests) ; en dessous de 400 px l'en-tête se compacte. Barre basse de 5 onglets sur mobile, rail latéral de 232 px à partir de 960 px. Les marges de sécurité iPhone (safe-area) et la réduction des animations sont respectées.

### Écrans

- **En-tête** : sélecteur Nicolas / Aurélie (`localStorage["marmite-actif"]`) et bouton Clair / Sombre. Sur ordinateur, bouton **Plein écran** dans le rail : l'app prend tout l'écran et masque la barre de claude.ai (qui ne peut pas être retirée depuis la page ; les téléphones ne proposent pas le plein écran dans ce cadre, le bouton n'y apparaît pas).
- **Vocabulaire** : l'app ne parle jamais de Claude. Les propositions viennent du **chef** : « J'ai faim, demandez au chef », « Le chef prépare votre menu », « Proposé par le chef ».
- **Aujourd'hui** :
  - navigation entre les 21 jours et bandeaux du jour (courses du jour, jour plaisir, plan pas encore commencé) ;
  - « assiette » en SVG : 4 arcs, un par repas, plus opaques une fois cochés, avec les kcal mangées au centre ;
  - jauges kcal, protéines et coût ;
  - 4 fiches repas avec **Ajuster**, **Changer** et **Je l'ai fait** ;
  - un bouton « J'ai faim, demandez au chef » qui vise le créneau de l'heure actuelle.
- **Ajuster** :
  - chaque quantité s'édite au clavier ou avec − et + (pas de 5 g, 10 ml ou 1 unité) ;
  - un ingrédient se retire, un ingrédient du catalogue s'ajoute ;
  - kcal, protéines, coût et écart au plan se calculent en direct ;
  - à l'enregistrement, le repas passe en `ajuste:true`. Si les quantités redeviennent celles du plan, l'ajustement est supprimé.
- **Planning** : calendrier du lundi au dimanche, qui commence un jeudi. Chaque case affiche les 4 barres de repas, les repères plaisir, poisson et courses, et le coût du jour. Une barre montre le nombre de repas suivis sur 84.
  - Carte **« Le chef prépare votre mois »** (début de mois) : mois (les 3 suivants), nombre de jours, **budget du mois** (par défaut celui du mois en cours, sinon la somme des budgets des profils ramenée à la durée) et invités. Le moteur compose le mois à partir de ce qu'il restera à la maison à la fin du mois en cours (`stockReel(NB_JOURS + 1)`) ; la proposition montre les courses du mois face au budget (et le dépassement si le chef n'y arrive pas), les quotas poisson et plaisir, les kcal et protéines moyennes, **ce qu'il faut acheter chaque semaine** (une ligne par course, aux jours des réglages), ce qu'il faut avant la première course et le planning. **Chaque repas de la proposition se touche pour être remplacé** : une feuille ouvre la bibliothèque filtrée sur ce créneau (plats avec viande ou poisson pour midi et soir, desserts pour le dessert), avec recherche, filtres Viande / Poisson / Plaisir, coût pour deux, et « déjà le … » si la même famille de plat est prévue à moins de 5 jours ; le choix recalcule portions, courses et bilan sans toucher aux autres repas (`Moteur.grilleDuMois` + `composerMois({ grilleImposee })`). **Sur ordinateur** (écran d'au moins 960 px avec souris), une colonne « Bibliothèque » à droite de la proposition (recherche, filtres Viande / Poisson / Plaisir / Desserts) permet de **glisser un plat sur un repas** ; un dessert ne se dépose que sur un dessert, un plat que sur midi ou soir. Même chose dans « Refaire le planning selon le stock ». « Valider ce mois » demande une confirmation dans la page, puis **archive le mois affiché** (`E.archives[id]` : coches, remplacements, achats, prix payés, quantités, décisions, poubelle, planning refait) et active le nouveau (`E.mois`). Un mois archivé se rouvre (« Rouvrir »), le mois affiché étant archivé à son tour.
  - Carte **« Refaire le planning selon le stock »** (en cours de mois, si des aliments ont disparu ou n'ont pas pu être achetés) : bouton « Demander au chef un planning selon le stock ». Le moteur (`app/moteur.js`, injecté dans la page par `construire.py` à la place de `__MOTEUR__`) recompose les jours à partir du premier jour libre (aujourd'hui si aucun repas n'y est coché, sinon demain ; réglable), avec le **stock réel** (`stockReel`), les prix validés (`Moteur.avecPrix`), les objectifs et dernières pesées des profils, l'historique des 5 derniers jours, des invités et un budget facultatifs, et une forte priorité au stock (`poidsStock: 3, penaliteManque: 1`). La proposition affiche les produits du stock utilisés, le coût des courses à venir, les kcal et protéines moyennes, ce qu'il faut acheter avant la prochaine course et le menu jour par jour ; « Une autre idée, chef » change la graine. « Appliquer ce planning » écrit les repas des deux personnes (`remplacements` avec `genere:true`) et remplace les courses non commencées par celles du moteur (`foyer.generation`) ; les courses gardées dont le jour est passé ne gardent que leurs articles cochés (le reste n'a pas été trouvé ou a été laissé). « Revenir au planning d'avant » rétablit tout.
- **Courses** : trois onglets, **Listes**, **À la maison** et **Prix**. Toutes les courses passent par `COURSES()` (celles des données, ou celles d'un menu généré).
  - **Listes** : une puce par course (octobre : 1er, 8 et 15, avec articles cochés / total). Cocher un article (toucher n'importe où sur la ligne, sauf les champs) **valide son prix** : son montant passe dans le réel. Chaque ligne indique le **besoin** de la période et une **quantité achetée** modifiable (conditionnements, ou grammes en vrac ; `foyer.quantites`), qui vaut par défaut la quantité prévue ; le prix payé se tape dans le champ de la ligne (l'estimation sert d'indication ; saisir un prix coche l'article). Totaux : payé (cochés), reste à acheter, part de la personne active. Sous les totaux : la **consommation prévue du foyer** (somme des `totalPrevu`, aux derniers prix validés) face au budget du foyer (somme des budgets des profils), et les achats du cycle (payés + à venir). **Dès que la consommation prévue dépasse le budget**, un panneau propose, sur ce qu'il reste à acheter : **Retirer** une ligne (hors protéines, féculents et hors repas), **Changer des aliments** (échanges `substituts` du catalogue, quantité équivalente en protéines pour une protéine, en kcal pour un féculent, même poids sinon ; seuls les échanges qui font gagner plus de 0,30 € sont proposés), ou **Accepter** le dépassement. Un choix s'applique tout de suite à la liste (`itemsCourse`) et aux repas de la période de la course à partir d'aujourd'hui, pour les deux personnes (remplacements `ajuste:true, modif:id`) ; « Annuler » rétablit l'état d'avant. Un dépassement accepté ne repropose rien tant qu'il ne grandit pas de plus de 1 €. Le même panneau apparaît en haut de l'onglet Budget. Un prix payé devient le prix unitaire du produit dans toute l'app. Magasin, totaux, part de la personne active.
  - **À la maison** : ce qu'il reste réellement (`stockReel(j)` : stock de départ + articles cochés − repas des jours passés − poubelle ; un article non coché n'est pas à la maison). Colonnes : le jour (« Sam. 3 oct. »), puis « Le 21 au soir » prévu avec toutes les courses de la liste. Plus de colonne d'écart. Ruptures en premier, valeur de ce qui est à la maison, repas ajustés. Chaque ligne en stock a une **poubelle** : on saisit la quantité jetée, elle sort du stock à partir de ce jour (jamais d'office), et la carte « À la poubelle » liste les pertes avec leur valeur et un bouton Annuler.
  - **Prix** : le prix de chaque produit, par rayon (au conditionnement, ou au kilo pour le vrac), modifiable. Un prix modifié (`source:"saisi"`) ou déduit d'un prix payé (`source:"paye"`) va dans `foyer.prix` et remplace celui du catalogue partout ; « Rétablir » revient au prix d'origine. Les produits aux prix estimés portent l'étiquette « estimé ».
- **Budget** :
  - **Budget du foyer** en tête (somme des budgets des profils) : barre payé (vert) + reste à acheter (or) face au budget, et pour chacun la part de la personne active ; consommation prévue du foyer ;
  - puis le panneau de dépassement s'il y a lieu, et la **part de la personne active** : prévu face à son budget, déjà consommé, reste à manger, part payée, économie face à la liste initiale ;
  - courbe cumulée sur 21 jours, tableau par course, prix payés face aux prix estimés.
- **Profil** : poids avec courbe et pesées, budget et référence, objectifs kcal et protéines, liste « à éviter », état de la synchronisation, remise à zéro.

### L'assistant « J'ai faim » / « Changer »

- **Formulaire** :
  - envie : Rapide, Réconfortant, Léger, Créole, Plaisir ou Surprends-moi ;
  - nombre de personnes, de 1 à 12, et temps (15 min, 30 min, 45 min, 1 h) ;
  - interrupteur « [l'autre] mange avec nous », qui apparaît à partir de 2 personnes et remplace aussi son repas ;
  - interrupteur « OK pour acheter des produits en plus », désactivé par défaut ;
  - budget maximum par personne, **facultatif**.
- **Principe** : le stock passe en premier. Claude reçoit le stock réel du foyer ce jour-là : achats, moins la consommation planifiée et ajustée, plus les ingrédients libérés par le repas qu'on remplace. Il reçoit aussi les prix au kilo, et les autres produits seulement si les achats sont autorisés.
- **Format de réponse imposé** :

```json
{"plats":[{"nom":"...","pourquoi":"...","temps_min":25,"ingredients":[{"aliment":"Poulet","quantite":300}],"etapes":["..."]}]}
```

  Les quantités sont pour toute la tablée : grammes, ml, ou nombre pour les œufs, wraps et pains burger.
- **Traitement de la réponse** :
  - `trouverAliment()` rapproche les noms du catalogue de façon souple ;
  - l'app recalcule elle-même kcal, protéines et coût, sans faire confiance aux chiffres de Claude ;
  - chaque plat est étiqueté « Tout est à la maison », « À acheter : … » ou « Il manque : … » ;
  - les plats faisables avec le stock seul sont classés en premier.
- **Choix d'un plat** : la tablée est répartie au prorata des kcal prévues pour chacun, les invités comptant pour la moyenne. Le résultat est enregistré dans `remplacements` avec `ia:true` et `convives`.
- **Appel** : `sample.json(consigne, { modelTier: "default", cache: false })`. Les erreurs gérées sont `not_granted`, `rate_limited`, `invalid_json` et les erreurs génériques.

### Données persistées

Schéma version 2. Il est stocké dans `localStorage["marmite-nicolas"]` (le nom date de la version 1) et dans le document `db` `data/users/<id>/marmite`.

```js
{
  version: 2,
  foyer: {
    achats:   { "c1-Poulet": true },                 // articles cochés, par course
    payes:    { "c1-Poulet": 21.5 },                 // prix payés saisis
    prix:     { "Poulet": { prix: 10.75, date, source } },   // prix au paquet (ou €/kg en vrac), source "paye" ou "saisi"
    magasins: { 1: "Leclerc Saint-Pierre" },
    pertes:   [{ j: 3, a: "Jambon", q: 40, date: "2026-10-03" }],  // produits jetés (poubelle), j = jour du plan
    modifs:   [{ id, type: "retrait" | "substitution", cid, a, b, f, gain, date, avant }],  // choix face à un dépassement
    depassementAccepte: 12.5,                                   // dépassement accepté (€)
    quantites: { "c1-Poulet": 3 },                              // quantité achetée modifiée (unité d'achat)
    generation: { depuis, jourRefait, date, graine, invites, gardees, courses, avant, modifsAvant, precedente }   // planning refait par le chef
  },
  mois: { id, titre, debut, jours, invites, plan, courses, share, stockDepart, budget, graine, date },   // mois préparé par le chef (absent : octobre)
  archives: { "2026-10": { titre, date, foyer: { achats, payes, … }, personnes: { nicolas: { coches, remplacements } }, mois } },
  personnes: {
    nicolas: {
      coches: { "d3-dej": true },
      remplacements: { "d3-din": { k, label, plat, items:[[aliment, qté]], convives, ia, ajuste } },
      pesees: [{ date: "2026-10-05", kg: 84.2 }],
      profil: { poids, cible, taille, age, budget, reference, kcalMin, kcalMax, prot, eviter:[] }
    },
    aurelie: { /* même forme */ }
  }
}
```

La fonction `charger()` convertit l'ancien format de la version 1, où tout était à plat et ne concernait que Nicolas. Elle **copie en profondeur** ce qu'elle reçoit : les données du compte en ligne peuvent arriver verrouillées en écriture, et sans copie, cocher une case ou saisir un prix échouait sans bruit (bug corrigé le 30/09/2026, couvert par `tests/test_glisser.py              ordinateur : bibliothèque à glisser sur un repas, dessert sur dessert, bouton Plein écran
tests/test_compte.py`).

### Blocs de données (`donnees/`)

Depuis le 30/09/2026, les données sont découpées en blocs, source de vérité pour l'app :

- `catalogue.json` → `produits[aliment]` : `rayon`, `achat`, `cond`, `vrac`, `rend`, `prix`, `nut` (`[base, unité, kcal, protéines]` ou `null` pour les produits hors repas), `role` (`proteine`, `feculent`, `legume`, `matiere_grasse`, `autre`), `conservation` (`jours` après achat, `lieu`, `frais` si 10 jours ou moins, `estime:true` tant que Nico n'a pas corrigé), `note`. L'ordre suit la table nutritionnelle : l'app s'en sert pour l'affichage et la recherche d'aliments.
- `recettes.json` → `recettes[]` : `id`, `nom`, `repas` (`pdj`, `dej`, `din`, `des`), `tags` (`poisson`, `plaisir`, `restes`), `source`, `portions` de référence par personne, `suit` et `delaiMaxJours` pour les plats de restes. Les 45 plats d'octobre forment la bibliothèque de départ, plus les 6 de Nico du 30/09 ; les petits-déjeuners ont un `nomParPersonne`.

Les blocs sont désormais enrichis à la main : `python/decouper.py` refuse de les écraser sans `--force`.
- `mois/<aaaa-mm>.json` : `id`, `titre`, `debut`, `fin`, `jours`, `note`, `stockDepart`, `share`, `plan` (chaque repas porte l'`id` de sa `recette`), `courses`. Octobre est `2026-10.json`.
- `reglages.json` : cycle mensuel, jours des 4 courses (3, 10, 17, 24, modifiables), quotas (8 poissons, 6 plaisirs), écart minimal de 5 jours entre deux mêmes plats, règles d'inventaire, place de Claude, rappels.

`app/construire.py` prend le mois le plus récent et reconstitue la forme que l'app lit encore (ci-dessous), en ajoutant `mois`, `catalogue`, `recettes` et `reglages` dans `DONNEES`. `tests/test_donnees.py` vérifie que l'app reçoit exactement les données d'octobre d'origine.

### Données du plan telles que l'app les lit (`DONNEES`, reconstituées par `construire.py`)

- `nut[aliment]` : `[base, unité, kcal, protéines]` pour 39 aliments.
- `cat[aliment]` : 47 produits. Pour chacun :
  - `cat` : le rayon ;
  - `achat` : libellé du conditionnement ;
  - `cond` : taille du conditionnement ;
  - `vrac` et `rend` : vente au poids et rendement ;
  - `prix` : par conditionnement, ou au kilo si vrac ;
  - `stock` : stock initial (lentilles 1 590 g, huile 1 000, farine 500) ;
  - `note` : conseil de conservation.
- `share[aliment]` : part de Nicolas dans la consommation. Celle d'Aurélie vaut 1 − share.
- `plan[21]` : `{ d, tag ("plaisir"|""), fish, meals:[{ k, label, plat:{nicolas,aurelie}, items:{nicolas:[[a,q]], aurelie:[[a,q]]} }] }`.
- `courses[2]` : `{ id, date, jourPlan, titre, jour, couvre, items:[{ a, buy, est, needN, needA }] }`.
- Dépenses hors repas, codées en dur dans `HORS_REPAS` : café 1 000 g pour Nicolas, eau 42 L chacun.

### Fonctions clés du template

- **Mois actif** : `activerMois()` règle `DEBUT`, `NB_JOURS`, `PLAN`, `BASE_COURSES`, `SHARE`, `STOCK_DEPART`, `INVITES`, `MOIS_ID`, `MOIS_TITRE` depuis `E.mois` (mois préparé par le chef) ou, à défaut, depuis les données d'octobre. Tous les textes datés en découlent (`dateDuJour`, `libelleJour`, « Le 30 au soir »…). `budgetFoyer()` = budget du mois s'il existe ; `budgetPersonne(p)` = sa part, au prorata des budgets des profils. Les dépenses hors repas viennent de `reglages.horsRepas` (par jour).

- **Écouteurs** posés par affectation (`document.onclick`…) et un même clic traité une seule fois (`e.__marmite`) : si le viewer remettait la page à jour sans la recharger, un toucher ne doit pas cocher puis décocher.
- **Courses** : `COURSES()`, `itemsCourse(c)` (retraits, échanges, quantité achetée), `cleLigne`, `montantLigne`, `bilanCourse` (réel = cochés, à venir = non cochés).
- **Le chef** : `genererMenu`, `appliquerGeneration`, `annulerGeneration`, `carteGeneration`.

- **Plan et repas** : `repasPlan(j,k,p)` renvoie le repas d'origine, `repasDe(j,k,p)` la version ajustée ou remplacée si elle existe.
- **Calculs** :
  - `prixUnitaire(a)` : prix saisi, sinon prix du catalogue divisé par le conditionnement (divisé par 1 000 et par le rendement en vrac) ;
  - `statsRepas`, `statsJour`, `totalPrevu(p)`, `horsRepasJour(p)` ;
  - `bilanCourse(cid,p)` et `part(a,p)`.
- **Stock** :
  - `stockBrut(j, planSeul)` : stock au matin du jour j (j = 22 pour la fin du cycle) = stock initial + courses dont `jourPlan ≤ j` − consommation des jours précédents, pour les deux personnes ;
  - `stockAuDebut(j)` : même calcul en ne gardant que les quantités positives.
- **Assistant** : `consigne()`, `proposer()`, `choisir(i)`, `stockPourIA()`.
- **Ajustement** : `actionEdition()`, `ticketEdition()`, `infosEdition()`.

## 5. Limites connues

- **Plan figé dans les données.** Pour un nouveau cycle, il faut tout régénérer en Python. C'est le sujet en cours, voir la section 6 (passage au mois).
- **Liste de courses fixe.** Ajuster ou remplacer un repas ne la recalcule pas. Seul l'onglet « À la maison » reflète la réalité.
- **Stock estimé.** Un repas non coché compte quand même comme mangé. Les pertes et le grignotage ne sont pas vus. Condiments et épices ne sont pas suivis.
- **Octobre acheté au plus juste.** Beaucoup d'aliments finissent à 0 g le 21 (tomates, pommes de terre, patates douces, riz, lentilles…). Toute portion en plus sur l'un d'eux crée une rupture.
- **Pas de vraie notification.** Une page web fermée ne peut pas sonner sur le téléphone.
- **Référence d'Aurélie.** Les 208,94 € ont été recopiés depuis Nicolas et restent à confirmer.

## 6. Prochaine étape : programmer le mois suivant

Nico veut enchaîner sans tout régénérer en Python, et être prévenu avant la fin du stock. Seul le découpage des données est fait (voir « Avancement »).

### Décisions de Nico (30/09/2026)

- **Cycle = mois calendaire.** Les 21 jours d'octobre étaient une exception : Nico reçoit 3 personnes du 21 au 31 octobre. Le premier mois construit par le moteur sera novembre.
- **4 courses par mois**, à des jours fixés dans `donnees/reglages.json` : la première le 3, puis 10, 17 et 24 par défaut. Chaque course couvre jusqu'à la suivante ; la dernière couvre jusqu'à la première du mois suivant.
- **Quotas mensuels** : 8 repas poisson et 6 repas plaisir.
- **Claude enrichit la bibliothèque de recettes, et n'intervient que le jour où l'on prépare le planning du mois.** Un seul appel par mois, pour économiser l'usage de Claude. Tous les calculs (portions, nutrition, coûts, courses, stock) sont faits par l'app.
- **Inventaire validé avant chaque course.** L'app présente le stock estimé ; l'utilisateur choisit de le vérifier ligne à ligne ou de le valider tel quel. La liste de la course est calculée sur l'inventaire validé. Garde-fou : une vérification des produits frais est imposée une fois par mois, sinon l'erreur du stock estimé s'accumule.
- **« J'ai faim » et « Changer »** proposent deux voies : la bibliothèque, calculée en local sans Claude (par défaut), ou « Nouveauté », qui appelle Claude à la demande.
- **Du 22 au 31 octobre** (3 invités) : en attente, rien n'est planifié pour l'instant.
- **Protéine animale à chaque déjeuner et dîner** (viande, poisson, charcuterie ; les œufs et les lentilles ne comptent pas). Aucun plat végétarien. Les petits-déjeuners ne sont pas concernés. Les 5 plats d'octobre sans viande ni poisson (omelettes, salades lentilles-œufs) sont écartés par le moteur.
- **Aucune perte d'office.** Un produit non consommé reste en stock ; seule la poubelle de l'onglet « À la maison » le classe en perte.
- **Jambon au gramme** (à la coupe), 11,24 €/kg déduits du paquet de 500 g à 5,62 € ; appliqué aussi à octobre (Course 1 : 150 g, Course 2 : 550 g).
- **Préparation du mois suivant le 30** (le dernier jour en février). Les jours avant la première course du mois vivent sur le stock ; la difficulté ne concerne qu'octobre, à cause de la période en attente.
- **Génération paramétrable** : nombre de jours, nombre d'invités et budget, qui peut changer d'un mois à l'autre.
- **Dépassement du budget** : le choix est proposé au moment où il apparaît (retirer, changer des aliments ou accepter), dès octobre.
- **Courses une fois par semaine**, octobre compris (1er, 8 et 15).
- **Budget réel** : cocher un article valide son prix. Quantité achetée modifiable, besoin affiché par défaut.
- **« Le chef »** à la place de Claude dans toute l'app.
- **Déroulé du mois** : en début de mois, le chef propose le planning et ce qu'il faut acheter chaque semaine pour le budget choisi ; on valide, le mois précédent est archivé. En cours de mois, on peut refaire le planning selon le stock si des aliments ont disparu ou n'ont pas pu être achetés (rayon vide, choix de budget).
- **Porc réintégré** (il avait été retiré de la liste d'octobre). Plats ajoutés par Nico : saucisses grillées-frites-haricots verts et steak frites (classés plaisir), hachis parmentier bœuf-porc, cassoulet aux pommes de terre, riz mexicain (poulet ou bœuf, chorizo, haricots rouges, poivrons). Nouveaux produits : saucisses de porc, porc haché, chorizo, haricots rouges et blancs en conserve, avec des prix estimés (`prixEstime:true`) qui se corrigent au premier prix payé.

### Architecture retenue (option hybride)

1. **Trois blocs de données.**
   - **Catalogue produits** : conditionnement, prix réellement payé, rayon, durée de conservation, kcal et protéines.
   - **Recettes** : chaque ingrédient a un rôle (protéine, féculent, légume, matière grasse, autre). Les plats d'octobre forment la bibliothèque de départ.
   - **Mois** : dates, menu, 4 courses, inventaires, suivi. Octobre devient le mois 1, rangé comme les suivants.
2. **Moteur en JavaScript, sans IA.** Il compose le mois à partir de la bibliothèque : quotas de poisson et de repas plaisir, pas le même plat à moins de 5 jours, stock restant utilisé en premier, budget respecté.
3. **Portions calculées.** Par personne : protéine réglée sur l'objectif de protéines, féculent sur la fourchette de kcal, légumes généreux. Objectifs recalculés avec les dernières pesées.
4. **Courses calculées.** Chaque course couvre la période jusqu'à la suivante : besoins de la période − inventaire validé, arrondis aux conditionnements. Les produits qui se gardent (surgelés, secs, conserves) peuvent être avancés sur une course précédente si c'est plus économique ; le frais reste sur la course de sa semaine.
5. **Un appel Claude par mois.** Le jour du planning, un seul `sample.json` envoie : la bibliothèque existante (noms seulement), le catalogue, les envies et les exclusions. Claude répond avec quelques recettes nouvelles au format de la bibliothèque. Nico valide ou écarte chacune, puis le moteur compose le mois sans Claude. Le planning ne rappelle pas Claude dans le mois ; seul le bouton « Nouveauté » de « J'ai faim » peut l'appeler, à la demande.
6. **Écran « Préparer le mois ».**
   1. Inventaire de départ (même logique que l'inventaire avant course).
   2. Réglages : mois, budget, quotas poisson et plaisir, recettes à écarter, dates des 4 courses.
   3. Nouvelles recettes : l'appel Claude du mois, puis validation.
   4. Proposition : le mois s'affiche, avec échange de repas possible.
   5. Validation : 4 listes de courses prévisionnelles, mois précédent archivé avec son bilan.
7. **Rappels.** Le 30 : « Prépare le mois suivant ». J-1 avant chaque course : « Valide l'inventaire, courses demain ». Bandeau et pastille sur l'onglet Courses ; pour une vraie sonnerie, un événement de calendrier (fichier .ics exportable).

### Avancement

1. Fait : découpage des données en blocs (`donnees/catalogue.json`, `recettes.json`, `mois/2026-10.json`, `reglages.json`), l'app inchangée.
2. Fait : moteur `app/moteur.js`, sans écran (voir « Le moteur » ci-dessous), testé par `tests/test_moteur.js`. Propositions générées par `outils/proposer_mois.js` dans `donnees/propositions/`, jamais dans `donnees/mois/` (l'app prendrait le mois le plus récent).
3. Fait : moteur branché dans l'app (injecté par `construire.py`) : « Le chef prépare votre mois » et « Refaire le planning selon le stock » dans Planning, mois actif dans `E.mois`, archives.
4. À faire : inventaire à valider avant chaque course, appel du chef (Claude) au planning du mois pour enrichir la bibliothèque, « J'ai faim » en local, rappels, `reajuster` après chaque course.

### Le moteur (`app/moteur.js`)

`Moteur.composerMois({ catalogue, recettes, reglages, annee + mois ou debut, jours?, invites?, budget?, quotas?, joursCourses?, graine, stockDepart, profils?, poidsActuels?, exclure?, moisReference? })` renvoie `{ mois, bilan }`. `mois` a la forme de `donnees/mois/2026-10.json` (plus `date` par jour, `invites`, `items.invites`, `needI`) ; le même objet sert sous Node (`module.exports`) et dans le navigateur (`Moteur` global).

- **Période** : un mois calendaire par défaut, ou `debut` + `jours` (par exemple du 22 au 31 octobre). Courses aux jours du mois des réglages, ou aux dates `joursCourses`. Quotas des réglages pour un mois entier, au prorata sinon. L'« âge » d'un jour = jours écoulés depuis la dernière course. Avant la première course, le moteur privilégie les plats faisables avec le stock de départ.
- **Invités** : `invites` convives en plus ; la portion d'un invité est la moyenne de Nicolas et d'Aurélie. Ils entrent dans les courses (`needI`) et dans le coût, pas dans `share`.
- **Plats retenus** : déjeuners et dîners avec au moins un produit `animal` du catalogue.
- **Composition** : les plaisirs d'abord (déjeuners du week-end, répartis sur le mois, glace en dessert), puis les poissons (répartis, en alternant déjeuner et dîner), puis le reste jour par jour. Chaque candidat reçoit un score : famille de plat déjà placée à moins de `ecartMinJours` exclue (les variantes d'un même plat, « Bœuf sauté asiatique, … », forment une famille) ; pénalités pour les produits frais au-delà de leur conservation, la même protéine ou le même féculent deux fois dans la journée, les répétitions, le coût ; bonus pour le stock de départ. Un tirage à graine départage : même graine, même mois. Les plats `restes` suivent leur plat d'origine (`suit`, `delaiMaxJours`). Desserts selon la répartition du mois de référence ; petits-déjeuners fixes.
- **Portions** : par personne et par jour, protéines des plats principaux calées sur l'objectif (facteur 0,85 à 1,4), puis féculents calés sur le milieu de la fourchette de kcal (0,5 à 1,6) ; arrondis à 5 g ou à l'unité. `objectifs(profil, poids)` retire environ 14 kcal par kg perdu.
- **Courses** : chaque course achète le besoin de sa période moins le stock, arrondi au conditionnement (vrac : `pasAchat` du produit, 50 g par défaut, 1 g pour le jambon ; rendement compris). Tous les restes passent à la période suivante ; le frais plus vieux que sa conservation estimée est seulement signalé (`fraisAVerifier`), pour l'inventaire.
- **Budget** : celui saisi pour la période, sinon celui des profils (prévu pour `budgetJours` jours) ramené à la durée. Si les achats le dépassent, le moteur recompose en pesant davantage le coût (6 passes au plus) et garde la passe la moins chère.
- **Réajustement en cours de mois** : `Moteur.reajuster({ ...entrées, mois, prix, payes, aPartirDe, budget })`. Dépensé = prix payés des courses faites (sinon estimation aux prix validés) ; les courses restantes sont réestimées aux prix validés (`prix` = `foyer.prix`). Si la projection dépasse le budget, les jours à partir de la prochaine course sont recomposés avec le budget restant (stock réel reporté, quotas restants, écart respecté à la jointure, coût plus pesant : 10 passes) ; la version n'est gardée que si elle coûte vraiment moins, sinon `horsDePortee:true`. Ordre de grandeur mesuré : le menu seul rattrape 3 à 8 % ; au-delà, la variété s'effondre (le même plat plaisir 3 fois).
- **Bilan** : nutrition moyenne, jours hors fourchette, quotas obtenus et visés, coûts (consommation par convive, achats, budget, par course), frais à vérifier, frais consommés au-delà de leur conservation (plats et petits-déjeuners à part), ce qu'il faut avant la première course, stock de fin de période.

### Points ouverts

- **Moteur branché dans l'app** : il devra prendre `foyer.prix` en priorité (`Moteur.avecPrix`) et lancer `reajuster` après chaque course validée, en proposant la nouvelle suite du mois plutôt qu'en l'imposant.

- **Conditionnements à confirmer** : avocat compté à 350 g de chair, salade entière (300 g), champignons en barquette de 250 g : leurs restes s'accumulent d'une semaine à l'autre.
- **Bibliothèque encore dominée par le poulet** : 40 plats principaux avec viande ou poisson (restes compris), 5 plats plaisir (burger, pizza, barbecue, steak frites, saucisses-frites) pour 6 repas plaisir par mois.
- **Prix des nouveaux produits** (saucisses, porc haché, chorizo, haricots) estimés : à corriger au premier achat.
- **Tomates, salade et champignons** dépassent leur conservation estimée en fin de semaine ; le petit-déjeuner d'Aurélie (tomate) et celui de Nicolas (banane) aussi.

- **Du 1er au 2 novembre** : avant la première course du 3, ces deux jours vivent sur le stock restant, qui dépend de la période en attente du 22 au 31 octobre.
- **Conservation** : les durées du catalogue sont des estimations (`estime:true`) à faire corriger par Nico ; elles décident de ce qui est frais et de la course où chaque produit est acheté.
- **Repas plaisir** : 6 par mois, soit le double du rythme d'octobre (3 en 21 jours). La bibliothèque n'en compte que 3 (burger, pizza, barbecue) : il faudra en ajouter, sinon le même plat revient trop souvent.

### Contrainte technique

Les données sont dans un seul document `db`. Avec plusieurs mois et une bibliothèque, prévoir des documents séparés, `…/marmite/mois/<id>` et `…/marmite/recettes/<id>`. Avant de publier une version qui utilise d'autres capacités, vérifier ce que permet l'environnement d'exécution d'Artifact.

## 7. Historique des décisions

1. **Brief UX** de l'assistant de décision alimentaire, puis prototype bêta complet en 12 sections, publié en Claude Doc : https://claude.ai/code/artifact/bc4a564f-9017-41fb-b5bb-487fae08b9c8.
2. **Comparaison avec la version de ChatGPT.** Celle de Claude était plus constructible, celle de ChatGPT meilleure sur le cadrage (hypothèse à tester, 5 critères de réussite). ChatGPT avait introduit 7 erreurs de logique. Les deux versions partagent les mêmes identifiants d'écrans (O1 à H3).
3. **Excel du cycle d'octobre.**
   - Un œuf remplace le jambon au petit-déjeuner de Nicolas.
   - Le poisson remplace 4 repas de bœuf.
   - Prix des poivrons corrigé.
   - Deux courses (du 1er au 5, puis du 6 au 21), listes individuelles, budget fusionné.
4. **Marmite version 1** : Nicolas seul, palette « lagon ».
5. **Marmite version 2** :
   - programme d'Aurélie ;
   - assistant qui part du stock, avec un nombre de personnes réglable, des achats en option et un budget facultatif ;
   - bouton clair / sombre ;
   - palette Fluent & Forward.
6. **Ajustement ingrédient par ingrédient** et onglet de stock « À la maison ».
7. **Réflexion sur le cycle suivant** (section 6).
8. **Décisions du 30/09/2026** : cycle mensuel, 4 courses par mois, Claude limité à un appel par mois pour enrichir la bibliothèque, inventaire validé avant chaque course (vérification facultative). Repo rangé : le contenu des zips est versionné fichier par fichier. Puis : « J'ai faim » en deux voies (bibliothèque locale ou « Nouveauté » via Claude), période du 22 au 31 octobre en attente, quotas de 8 poissons et 6 plaisirs, jours de courses dans les réglages (le premier le 3), vérification mensuelle du frais acceptée. Données découpées en blocs.
9. **Décisions du 30/09/2026, suite** : protéine animale à chaque déjeuner et dîner, aucune perte d'office (poubelle), jambon au gramme, préparation le 30, génération paramétrable (jours, invités, budget). Puis : porc réintégré, 6 plats ajoutés (saucisses-frites, steak frites, hachis parmentier bœuf-porc, cassoulet, riz mexicain poulet ou bœuf), ligne de courses cochable en entier, onglet « Prix » pour modifier les prix, prix modifiable directement sur la ligne de course, projection du cycle, réajustement du budget par le moteur après chaque course. Puis : face à un dépassement, choix proposé sur le moment (retirer, changer des aliments, accepter), appliqué dès octobre ; app republiée. Puis : courses hebdomadaires dès octobre, cocher = prix validé (budget réel), quantité achetée modifiable, « À la maison » en stock réel du jour, budget du foyer avec la part de chacun, « le chef » au lieu de Claude, menu du chef selon le stock dans Planning. Puis : préparation du mois par le chef (planning + courses de chaque semaine pour le budget du mois), validation avec archive du mois précédent ; « refaire selon le stock » réservé au cours de mois. Puis : correction du bug des cases et des prix (données du compte copiées au chargement), repas de la proposition remplaçable depuis la bibliothèque. Puis : glisser-déposer depuis la bibliothèque sur ordinateur, bouton Plein écran pour masquer la barre de claude.ai.

## 8. Arborescence

```
CLAUDE.md                          ce document
requirements.txt                   dépendances Python (openpyxl, playwright)
app/marmite_template.html          source de l'app (modifier ici)
app/marmite.html                   app assemblée (même comportement que la version publiée ; DONNEES contient en plus les blocs)
app/construire.py                  template + données → marmite.html
donnees/catalogue.json             produits : prix, nutrition, rôle, conservation
donnees/recettes.json              bibliothèque de recettes (45 plats d'octobre + 6 de Nico)
donnees/mois/2026-10.json          le mois d'octobre : planning, courses, stock de départ
donnees/reglages.json              jours des courses, quotas, inventaire, place de Claude
donnees/appdata.json               archive d'octobre, source du découpage (ne plus modifier)
python/data.py                     table nutritionnelle NUT
python/menu.py                     menu des 21 jours (abréviations AB, petits-déjeuners, DAYS)
python/adjust.py                   ajustements de portions par personne
python/calc.py                     contrôle nutrition et totaux (python3 calc.py)
python/build.py                    génération de l'Excel
python/export_appdata.py           Excel + menu → donnees/appdata.json
python/decouper.py                 migration appdata.json → blocs de donnees/ (faite une fois)
excel/menu_octobre_nicolas_aurelie.xlsx
app/moteur.js                      moteur de composition d'un mois (planning, portions, courses, bilan)
outils/proposer_mois.js            node outils/proposer_mois.js 2026-11 : proposition + résumé
donnees/propositions/              propositions du moteur, en attente de validation
tests/test_moteur.js               règles du mois (quotas, écart, protéine animale, courses, nutrition, graine, stock, invités, période libre)
tests/test_donnees.py              blocs de données cohérents, app nourrie à l'identique
tests/test_mois.py                 préparation du mois : proposition, repas changé depuis la bibliothèque, budget, courses par semaine, validation, archive, rechargement, réouverture
tests/test_glisser.py              ordinateur : bibliothèque à glisser sur un repas, dessert sur dessert, bouton Plein écran
tests/test_compte.py               données du compte verrouillées en écriture : cases, prix payés, prix modifiés et repas cochés marchent et partent vers le compte
tests/test_generation.py           menu du chef selon le stock : proposition, application, courses recalculées, retour, aucune mention de Claude
outils/courses_octobre.js          octobre repassé en courses hebdomadaires (fait le 30/09/2026)
tests/test_depassement.py          panneau de dépassement : échange, retrait, annulation, acceptation
tests/test_prix.py                 onglet Prix, prix tapé sur la ligne de course, projection du cycle, pas de débordement à 360 px
tests/test_poubelle.py             case cochée en touchant la ligne, poubelle du stock, annulation, jambon au gramme
tests/test_ajustement_stock.py     ajustement d'un repas, retour au plan, stock
tests/test_assistant_personnes_theme.py   Nicolas/Aurélie, thème, assistant simulé, remplacement à 2
docs/prototype-beta-resume.md      résumé du prototype de l'app grand public
```
