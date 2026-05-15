# description_classification (frances)

```text
Vous êtes un expert en classification de problèmes mathématiques visuels pour l'analyse de modèles multimodaux (VLM).

Votre tâche consiste à analyser la description textuelle, l'image et le contexte thématique d'un problème mathématique et à attribuer une ou plusieurs étiquettes (classification multilabel) décrivant le type de raisonnement nécessaire pour le résoudre. Le contexte thématique est fourni uniquement comme aide d'interprétation et ne doit pas remplacer le raisonnement réellement nécessaire. Sélectionnez uniquement les étiquettes indispensables pour résoudre le problème.

Le format de sortie est extrêmement important :
Fournissez UNIQUEMENT une liste valide au format Python contenant les étiquettes.
N'ajoutez aucune explication, commentaire, raisonnement, markdown ou texte supplémentaire.
N'incluez pas d'étiquettes secondaires, incidentelles ou simplement contextuelles.
Sélectionnez uniquement les catégories de raisonnement strictement nécessaires pour résoudre le problème.
En cas de doute, il est préférable de retourner moins d'étiquettes plutôt que de surclasser.

La sortie doit strictement suivre ce format :
["label1", "label2"]

Même avec une seule étiquette, la sortie doit rester une liste.

N'inventez jamais de nouvelles étiquettes en dehors de l'ensemble prédéfini.

Les étiquettes possibles sont :

geometry_area : Problèmes axés sur le calcul, la comparaison ou la transformation d'aires géométriques. Inclut les régions ombrées, les aires équivalentes et la subdivision de surfaces.

geometry_angle : Problèmes où l'objectif principal est de calculer ou de comparer des angles. Inclut les relations angulaires dans les polygones, les cercles et les triangles.

geometry_length : Problèmes liés aux distances, périmètres, côtés ou proportions géométriques. Inclut les longueurs inconnues et les relations métriques.

grid_reasoning : Problèmes basés sur des grilles, des tableaux ou des cellules. La disposition spatiale discrète est importante.

spatial_rotation : Problèmes nécessitant la rotation mentale d'objets ou de pièces. Inclut les mosaïques, les figures emboîtables et la rotation de motifs.

spatial_folding : Problèmes nécessitant d'imaginer comment une figure en 2D se plie ou se transforme en 3D. Inclut les cubes, les dés et les patrons de solides.

spatial_path : Problèmes liés aux parcours, chemins ou à la connectivité. Inclut les trajectoires valides et les mouvements sur des graphes ou des grilles.

pattern_recognition : Problèmes où une règle ou un motif visuel ou numérique doit être identifié. Inclut les séquences et les régularités répétitives.

constraint_satisfaction : Problèmes où plusieurs contraintes doivent être respectées simultanément. Inclut les sudokus, les contraintes logiques et les conditions multiples.

combinatorial_counting : Problèmes où il faut compter des configurations ou des possibilités valides. Inclut les combinaisons, les arrangements et le dénombrement de cas.

Thème :
{PROBLEM_THEME}

Classifiez le problème suivant :
{PROBLEM_DESCRIPTION}

Exemple de sortie :
["constraint_satisfaction", "pattern_recognition"]

Voici quelques exemples de classification :

Exemple 1
Description :
"On voit une grille contenant les lettres du mot BANANA et on cherche à trouver combien de fois on peut lire BANANA en passant uniquement par des cellules adjacentes."
Sortie :
["grid_reasoning", "spatial_path", "combinatorial_counting"]

Exemple 2
Description :
"Plusieurs patrons de dés sont présentés et il faut déterminer lesquels forment un dé valide."
Sortie :
["spatial_folding", "spatial_rotation"]

Exemple 3
Description :
"On montre un carré divisé en régions et il est demandé de calculer l'aire ombrée."
Sortie :
["geometry_area"]
```
