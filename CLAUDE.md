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
  - Course 1, le 01/10, pour les jours 1 à 5 au plus juste : 129,94 € (35 articles) ;
  - Course 2, le 06/10, pour les jours 6 à 21 en une fois : 233,17 € (34 articles) ;
  - total foyer : 363,10 €.
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
- **Mise à jour** : republier `app/marmite.html` avec l'outil Artifact (action publish, avec l'`url` ci-dessus), sans redéclarer les capacités. Les sessions Claude Code web disposent de cet outil ; lire d'abord la version en ligne (action read) pour vérifier qu'elle n'a pas bougé. Au 30/09/2026, la version publiée a les mêmes données que `app/marmite.html` (seul l'ordre des clés JSON des courses diffère).
- **En local** : ouvrir `app/marmite.html` suffit. Les données passent alors en localStorage et l'assistant est indisponible, car `window.claude` est absent. Tout le reste fonctionne.

### Construire

```bash
pip install -r requirements.txt          # une fois ; en session web, ne pas lancer « playwright install » :
                                          # playwright 1.56 correspond au Chromium préinstallé (/opt/pw-browsers)
cd python && python3 build.py            # régénère l'Excel (si menu.py / adjust.py changent)
                                          # ouvrir puis réenregistrer l'Excel dans un tableur pour recalculer les formules
python3 export_appdata.py                 # Excel + menu → donnees/appdata.json
cd ../app && python3 construire.py        # template + données → app/marmite.html
cd .. && python3 tests/test_ajustement_stock.py && python3 tests/test_assistant_personnes_theme.py
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
- **Mise en page** : barre basse de 5 onglets sur mobile, rail latéral de 232 px à partir de 960 px. Les marges de sécurité iPhone (safe-area) et la réduction des animations sont respectées.

### Écrans

- **En-tête** : sélecteur Nicolas / Aurélie (`localStorage["marmite-actif"]`) et bouton Clair / Sombre.
- **Aujourd'hui** :
  - navigation entre les 21 jours et bandeaux du jour (courses, jour plaisir, plan pas encore commencé) ;
  - « assiette » en SVG : 4 arcs, un par repas, plus opaques une fois cochés, avec les kcal mangées au centre ;
  - jauges kcal, protéines et coût ;
  - 4 fiches repas avec **Ajuster**, **Changer** et **Je l'ai fait** ;
  - un bouton « J'ai faim, autre chose ? » qui vise le créneau de l'heure actuelle.
- **Ajuster** :
  - chaque quantité s'édite au clavier ou avec − et + (pas de 5 g, 10 ml ou 1 unité) ;
  - un ingrédient se retire, un ingrédient du catalogue s'ajoute ;
  - kcal, protéines, coût et écart au plan se calculent en direct ;
  - à l'enregistrement, le repas passe en `ajuste:true`. Si les quantités redeviennent celles du plan, l'ajustement est supprimé.
- **Planning** : calendrier du lundi au dimanche, qui commence un jeudi. Chaque case affiche les 4 barres de repas, les repères plaisir, poisson et courses, et le coût du jour. Une barre montre le nombre de repas suivis sur 84.
- **Courses** : trois onglets.
  - **Course 1 / Course 2** : cases à cocher et prix payé. Un prix payé devient le prix unitaire du produit dans toute l'app. Magasin, totaux, part de la personne active.
  - **À la maison** : stock estimé du foyer, trois colonnes (ce matin, le 21 au soir, écart avec le plan d'origine), ruptures en premier, bilan des ajustements.
- **Budget** : pour la personne active.
  - prévu face au budget, déjà consommé, reste à manger, part payée, économie face à la liste initiale ;
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
    prix:     { "Poulet": { prix: 10.75, date } },   // prix unitaire déduit (€/paquet, ou €/kg si vrac)
    magasins: { 1: "Leclerc Saint-Pierre" }
  },
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

La fonction `charger()` convertit l'ancien format de la version 1, où tout était à plat et ne concernait que Nicolas.

### Données du plan (`donnees/appdata.json`, injectées dans `DONNEES`)

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

Nico veut enchaîner sans tout régénérer en Python, et être prévenu avant la fin du stock. Rien n'est construit.

### Décisions de Nico (30/09/2026)

- **Cycle = mois calendaire.** Les 21 jours d'octobre étaient une exception : Nico reçoit 3 personnes du 21 au 31 octobre. Le premier mois construit par le moteur sera novembre.
- **4 courses par mois.**
- **Claude enrichit la bibliothèque de recettes, et n'intervient que le jour où l'on prépare le planning du mois.** Un seul appel par mois, pour économiser l'usage de Claude. Tous les calculs (portions, nutrition, coûts, courses, stock) sont faits par l'app.
- **Inventaire validé avant chaque course.** L'app présente le stock estimé ; l'utilisateur choisit de le vérifier ligne à ligne ou de le valider tel quel. La liste de la course est calculée sur l'inventaire validé.

### Architecture retenue (option hybride)

1. **Trois blocs de données.**
   - **Catalogue produits** : conditionnement, prix réellement payé, rayon, durée de conservation, kcal et protéines.
   - **Recettes** : chaque ingrédient a un rôle (protéine, féculent, légume, matière grasse, autre). Les plats d'octobre forment la bibliothèque de départ.
   - **Mois** : dates, menu, 4 courses, inventaires, suivi. Octobre devient le mois 1, rangé comme les suivants.
2. **Moteur en JavaScript, sans IA.** Il compose le mois à partir de la bibliothèque : quotas de poisson et de repas plaisir, pas le même plat à moins de 5 jours, stock restant utilisé en premier, budget respecté.
3. **Portions calculées.** Par personne : protéine réglée sur l'objectif de protéines, féculent sur la fourchette de kcal, légumes généreux. Objectifs recalculés avec les dernières pesées.
4. **Courses calculées.** Chaque course couvre la période jusqu'à la suivante : besoins de la période − inventaire validé, arrondis aux conditionnements. Les produits qui se gardent (surgelés, secs, conserves) peuvent être avancés sur une course précédente si c'est plus économique ; le frais reste sur la course de sa semaine.
5. **Un appel Claude par mois.** Le jour du planning, un seul `sample.json` envoie : la bibliothèque existante (noms seulement), le catalogue, les envies et les exclusions. Claude répond avec quelques recettes nouvelles au format de la bibliothèque. Nico valide ou écarte chacune, puis le moteur compose le mois sans Claude. Les appels suivants du mois sont bloqués.
6. **Écran « Préparer le mois ».**
   1. Inventaire de départ (même logique que l'inventaire avant course).
   2. Réglages : mois, budget, quotas poisson et plaisir, recettes à écarter, dates des 4 courses.
   3. Nouvelles recettes : l'appel Claude du mois, puis validation.
   4. Proposition : le mois s'affiche, avec échange de repas possible.
   5. Validation : 4 listes de courses prévisionnelles, mois précédent archivé avec son bilan.
7. **Rappels.** J-3 avant la fin du mois : « Prépare le mois suivant ». J-1 avant chaque course : « Valide l'inventaire, courses demain ». Bandeau et pastille sur l'onglet Courses ; pour une vraie sonnerie, un événement de calendrier (fichier .ics exportable).

### Points ouverts

- **« J'ai faim » et « Changer »** appellent Claude à chaque demande, ce qui contredit la règle d'un seul appel par mois. Proposition : les faire passer sur un moteur local qui pioche dans la bibliothèque selon le stock réel. À confirmer avec Nico.
- **Du 22 au 31 octobre** (3 invités), rien n'est planifié ni chiffré. À traiter hors moteur ou comme un mois partiel.
- **Quotas mensuels** : 7 poissons et 3 plaisirs valaient pour 21 jours. Pour un mois, environ 10 poissons et 4 plaisirs (un par semaine) ; à confirmer.
- **Dates des courses** : fixes (par exemple le 1er, le 8, le 15 et le 22) ou un jour de la semaine (le samedi).

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
8. **Décisions du 30/09/2026** : cycle mensuel, 4 courses par mois, Claude limité à un appel par mois pour enrichir la bibliothèque, inventaire validé avant chaque course (vérification facultative). Repo rangé : le contenu des zips est versionné fichier par fichier.

## 8. Arborescence

```
CLAUDE.md                          ce document
requirements.txt                   dépendances Python (openpyxl, playwright)
app/marmite_template.html          source de l'app (modifier ici)
app/marmite.html                   app assemblée, identique à la version publiée
app/construire.py                  template + données → marmite.html
donnees/appdata.json               données du cycle d'octobre (plan, catalogue, courses)
python/data.py                     table nutritionnelle NUT
python/menu.py                     menu des 21 jours (abréviations AB, petits-déjeuners, DAYS)
python/adjust.py                   ajustements de portions par personne
python/calc.py                     contrôle nutrition et totaux (python3 calc.py)
python/build.py                    génération de l'Excel
python/export_appdata.py           Excel + menu → donnees/appdata.json
excel/menu_octobre_nicolas_aurelie.xlsx
tests/test_ajustement_stock.py     ajustement d'un repas, retour au plan, stock
tests/test_assistant_personnes_theme.py   Nicolas/Aurélie, thème, assistant simulé, remplacement à 2
docs/prototype-beta-resume.md      résumé du prototype de l'app grand public
```
