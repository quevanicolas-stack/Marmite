# Assistant de décision alimentaire — résumé du prototype bêta

La source de référence est le Claude Doc de Nico, qui fait environ 56 Ko en Markdown :
https://claude.ai/code/artifact/bc4a564f-9017-41fb-b5bb-487fae08b9c8

Pour avoir le texte intégral dans ce dossier, il faut l'exporter en Markdown depuis claude.ai et l'enregistrer ici sous `docs/prototype-beta.md`. Ce résumé ne remplace pas le document.

## Le produit

C'est une app mobile grand public. Elle transforme la question « qu'est-ce que je mange ? » en décision concrète, à partir de cinq éléments : le stock du foyer, les contraintes, les goûts, le temps disponible et le nombre de convives. L'app ne culpabilise jamais le fait de commander.

C'est un produit distinct de Marmite. Marmite est l'app personnelle du foyer ; les deux partagent seulement des idées, comme partir du stock ou gérer un nombre de convives variable.

## Décisions pour la bêta

- **Aucun prix et aucun budget.**
  - Aucun prix n'est affiché, estimé ou utilisé pour classer, faute de source locale fiable. Nico a refusé d'utiliser un catalogue de prix de métropole.
  - Les prix payés sont seulement collectés après un achat réel. Ils serviront plus tard à construire un catalogue local pour La Réunion.
- **Hors périmètre** : comparaison de prix, carte des commerces, commande automatique, budget, scan du frigo, code-barres, communauté et social, créateurs, marketplace, tableau de bord de diététicien, fonctions professionnelles.

## Structure du document de référence

Il compte 12 sections : partis pris, architecture, 34 écrans, 6 parcours, contenu de chaque écran, interactions transverses, moteur de recommandation en 5 étapes, stock, ingrédients manquants, notifications, données stockées, 16 règles impératives, navigation.

- **Identifiants d'écrans** : de O1 à H3.
  - O : onboarding (accueil, taille du foyer, allergies, import de ticket…) ;
  - A1 : accueil ;
  - D : parcours « J'ai faim » et propositions ;
  - R1 : exécution de la recette ;
  - P : planning et « Préparer demain » ;
  - F : après le repas ;
  - S : stock et vérification hebdomadaire ;
  - H : foyer, mes plats, notifications.
- **Temps ajusté** : temps de la recette × facteur de tablée × rythme personnel.
  - Le rythme personnel se nourrit de la réponse « Ça t'a pris… » : moins que prévu = 0,85, comme prévu = 1, plus que prévu = 1,25.
  - Il est borné entre 0,8 et 1,5 et vaut 1 au départ.
- **Moteur de recommandation** : filtres stricts, puis faisabilité, correspondance à l'envie, score sur 100 et diversification sur 3 cartes (« la sûre », « le coup de cœur », « la découverte »).
- **Notifications** : 2 par jour au maximum, toujours liées à un repas, au stock ou à un plat réel.

## Comparaison avec la version de ChatGPT

- **Claude** : version plus constructible (fiches écran par écran, moteur détaillé, règles, modèle de données).
- **ChatGPT** : meilleure sur le cadrage (hypothèse à tester, 5 critères de réussite), mais 7 erreurs de logique.
- Les deux versions consolidées partagent les mêmes identifiants d'écrans et la même formule de temps ajusté.
