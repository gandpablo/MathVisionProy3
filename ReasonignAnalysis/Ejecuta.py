#!/usr/bin/env python3
"""Ejecuta la replicacion sobre todo el dataset filtrado con guardado incremental.

El script procesa solo las filas con Imagen == 'SI'. Cada resultado usa el indice
original del CSV y no el indice posicional del dataframe filtrado.
"""

import argparse
import base64
import json
import signal
import sys
import traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path


VISION_MODEL = 'qwen2.5vl:7b'
pd = None
requests = None
Image = None
chat = None


prompt_espanol_desc = """
Eres un experto en clasificación de problemas matemáticos visuales para análisis de modelos multimodales (VLMs).

Tu tarea consiste en analizar la descripción textual, la imagen y la temática de un problema matemático y asignar una o varias etiquetas (multilabel classification) que describan el tipo de razonamiento necesario para resolverlo. La temática se proporciona únicamente como contexto adicional y no debe sustituir el razonamiento real necesario para resolver el problema. Selecciona únicamente las etiquetas indispensables para resolver el problema.

El formato de salida es extremadamente importante:
Devuelve ÚNICAMENTE una lista válida estilo Python con las etiquetas.
No incluyas explicaciones, comentarios, razonamientos, markdown ni texto adicional.
No incluyas etiquetas secundarias, incidentales o meramente contextuales.
Selecciona únicamente las categorías de razonamiento que sean estrictamente necesarias para resolver el problema.
En caso de duda, es preferible devolver menos etiquetas antes que sobreclasificar.

La salida debe seguir estrictamente este formato:
["label1", "label2"]

Si solo hay una etiqueta, igualmente debe devolverse dentro de una lista.

Nunca inventes etiquetas fuera del conjunto predefinido.

Las posibles etiquetas son:

geometry_area: Problemas centrados en calcular, comparar o transformar áreas geométricas. Incluye regiones sombreadas, áreas equivalentes y subdivisión de superficies.

geometry_angle: Problemas donde el objetivo principal es calcular o comparar ángulos. Incluye relaciones angulares en polígonos, circunferencias y triángulos.

geometry_length: Problemas relacionados con distancias, perímetros, lados o proporciones geométricas. Incluye longitudes desconocidas y relaciones métricas.

grid_reasoning: Problemas basados en cuadrículas, tablas o celdas. La disposición espacial discreta es importante.

spatial_rotation: Problemas que requieren rotar mentalmente objetos o piezas. Incluye mosaicos, figuras encajables y rotación de patrones.

spatial_folding: Problemas que requieren imaginar cómo una figura 2D se pliega o transforma en 3D. Incluye cubos, dados y desarrollos planos.

spatial_path: Problemas relacionados con recorridos, caminos o conectividad. Incluye trayectorias válidas y movimientos sobre grafos o rejillas.

pattern_recognition: Problemas donde debe identificarse una regla o patrón visual o numérico. Incluye secuencias y regularidades repetitivas.

constraint_satisfaction: Problemas donde varias restricciones deben cumplirse simultáneamente. Incluye sudokus, restricciones lógicas y condiciones múltiples.

combinatorial_counting: Problemas donde hay que contar configuraciones o posibilidades válidas. Incluye combinaciones, disposiciones y conteo de casos.

Temática:
{PROBLEM_THEME}

Clasifica el siguiente problema:
{PROBLEM_DESCRIPTION}

Ejemplo de salida:
["constraint_satisfaction", "pattern_recognition"]

Un par de ejemplos de la clasificación serían:

Ejemplo 1
Descripción:
"Se ve una rejilla donde están las letras de la palabra BANANA y se quiere encontrar cuántas veces puede leerse BANANA pasando solo entre celdas adyacentes."
Salida:
["grid_reasoning", "spatial_path", "combinatorial_counting"]

Ejemplo 2
Descripción:
"Se muestran varios desarrollos planos de dados y hay que determinar cuáles forman un dado válido."
Salida:
["spatial_folding", "spatial_rotation"]

Ejemplo 3
Descripción:
"Se muestra un cuadrado dividido en regiones y se pide calcular el área sombreada."
Salida:
["geometry_area"]
"""

prompt_ingles_desc = """
You are an expert in classifying visual mathematical problems for multimodal model (VLM) analysis.

Your task is to analyze the textual description, the image, and the thematic context of a mathematical problem and assign one or more labels (multilabel classification) that describe the type of reasoning required to solve it. The thematic context is provided to help interpret the problem setting but should not override the actual reasoning required. Select only the labels indispensable for solving the problem.

The output format is extremely important:
Provide ONLY a valid Python-style list of labels.
Do not include explanations, comments, reasoning, markdown, or additional text.
Do not include secondary, incidental, or merely contextual labels.
Select only the reasoning categories that are strictly necessary to solve the problem.
When in doubt, prefer fewer labels rather than over-labeling.

The output must strictly follow this format:
["label1", "label2"]

If there is only one label, still return a list.

Never invent new labels outside the predefined set.

The possible labels are:

geometry_area: Problems focused on calculating, comparing, or transforming geometric areas. Includes shaded regions, equivalent areas, and surface subdivision.

geometry_angle: Problems where the main objective is to calculate or compare angles. Includes angular relationships in polygons, circles, and triangles.

geometry_length: Problems related to distances, perimeters, sides, or geometric proportions. Includes unknown lengths and metric relationships.

grid_reasoning: Problems based on grids, tables, or cells. Discrete spatial arrangement is important.

spatial_rotation: Problems that require mentally rotating objects or pieces. Includes tilings, interlocking figures, and pattern rotation.

spatial_folding: Problems that require imagining how a 2D figure folds or transforms into 3D. Includes cubes, dice, and flat developments (nets).

spatial_path: Problems related to routes, paths, or connectivity. Includes valid trajectories and movements on graphs or grids.

pattern_recognition: Problems where a visual or numerical rule or pattern must be identified. Includes sequences and repetitive regularities.

constraint_satisfaction: Problems where several constraints must be met simultaneously. Includes sudokus, logical constraints, and multiple conditions.

combinatorial_counting: Problems where one must count valid configurations or possibilities. Includes combinations, arrangements, and case counting.

Theme:
{PROBLEM_THEME}

Classify the following problem:
{PROBLEM_DESCRIPTION}

Output example:
["constraint_satisfaction", "pattern_recognition"]

A couple of examples of the classification would be:

Example 1
Description:
"A grid is shown containing the letters of the word BANANA, and the goal is to find how many times BANANA can be read by moving only between adjacent cells."
Output:
["grid_reasoning", "spatial_path", "combinatorial_counting"]

Example 2
Description:
"Several flat developments of dice are shown, and it must be determined which ones form a valid die."
Output:
["spatial_folding", "spatial_rotation"]

Example 3
Description:
"A square divided into regions is shown, and the task is to calculate the shaded area."
Output:
["geometry_area"]
"""

prompt_frances_desc = """
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
"""

prompt_valenciano_desc = """
Ets un expert en classificació de problemes matemàtics visuals per a l'anàlisi de models multimodals (VLMs).

La teua tasca consisteix a analitzar la descripció textual, la imatge i la temàtica d'un problema matemàtic i assignar una o diverses etiquetes (multilabel classification) que descriguen el tipus de raonament necessari per a resoldre'l. La temàtica es proporciona únicament com a context addicional i no ha de substituir el raonament real necessari per a resoldre el problema. Selecciona únicament les etiquetes indispensables per a resoldre el problema.

El format d'eixida és extremadament important:
Retorna ÚNICAMENT una llista vàlida estil Python amb les etiquetes.
No inclogues explicacions, comentaris, raonaments, markdown ni text addicional.
No inclogues etiquetes secundàries, incidentals o merament contextuals.
Selecciona únicament les categories de raonament que siguen estrictament necessàries per a resoldre el problema.
En cas de dubte, és preferible retornar menys etiquetes abans que sobreclassificar.

L'eixida ha de seguir estrictament aquest format:
["label1", "label2"]

Si només hi ha una etiqueta, igualment ha de retornar-se dins d'una llista.

Mai inventes etiquetes fora del conjunt predefinit.

Les possibles etiquetes són:

geometry_area: Problemes centrats a calcular, comparar o transformar àrees geomètriques. Inclou regions ombrejades, àrees equivalents i subdivisió de superfícies.

geometry_angle: Problemes on l'objectiu principal és calcular o comparar angles. Inclou relacions angulars en polígons, circumferències i triangles.

geometry_length: Problemes relacionats amb distàncies, perímetres, costats o proporcions geomètriques. Inclou longituds desconegudes i relacions mètriques.

grid_reasoning: Problemes basats en quadrícules, taules o cel·les. La disposició espacial discreta és important.

spatial_rotation: Problemes que requereixen rotar mentalment objectes o peces. Inclou mosaics, figures encaixables i rotació de patrons.

spatial_folding: Problemes que requereixen imaginar com una figura 2D es plega o transforma en 3D. Inclou cubs, daus i desplegaments plans.

spatial_path: Problemes relacionats amb recorreguts, camins o connectivitat. Inclou trajectòries vàlides i moviments sobre grafs o reixetes.

pattern_recognition: Problemes on s'ha d'identificar una regla o patró visual o numèric. Inclou seqüències i regularitats repetitives.

constraint_satisfaction: Problemes on s'han de complir diverses restriccions simultàniament. Inclou sudokus, restriccions lògiques i condicions múltiples.

combinatorial_counting: Problemes on cal comptar configuracions o possibilitats vàlides. Inclou combinacions, disposicions i recompte de casos.

Temàtica:
{PROBLEM_THEME}

Classifica el següent problema:
{PROBLEM_DESCRIPTION}

Exemple d'eixida:
["constraint_satisfaction", "pattern_recognition"]

Un parell d'exemples de la classificació serien:

Exemple 1
Descripció:
"Es veu una reixeta on estan les lletres de la paraula BANANA i es vol trobar quantes vegades pot llegir-se BANANA passant només entre cel·les adjacents."
Eixida:
["grid_reasoning", "spatial_path", "combinatorial_counting"]

Exemple 2
Descripció:
"Es mostren diversos desplegaments plans de daus i s'ha de determinar quins formen un dau vàlid."
Eixida:
["spatial_folding", "spatial_rotation"]

Exemple 3
Descripció:
"Es mostra un quadrat dividit en regions i es demana calcular l'àrea ombrejada."
Eixida:
["geometry_area"]
"""

prompts_desc = {
    "ingles": prompt_ingles_desc,
    "castellano": prompt_espanol_desc,
    "frances": prompt_frances_desc,
    "valenciano": prompt_valenciano_desc
}

# Razonamiento

prompt_espanol_razon = """
Eres un auditor experto en IA especializado en analizar errores de razonamiento en modelos multimodales y modelos de lenguaje.

Tu tarea consiste en determinar qué tipo de fallo ha cometido el modelo al resolver un problema matemático o visual.

Para clasificar el error debes tener en cuenta conjuntamente:
- La temática del problema.
- El enunciado del problema.
- La opción seleccionada por el modelo.
- La traza de razonamiento del modelo.

No evalúes solo si la respuesta final es correcta o incorrecta. Analiza si el razonamiento usado por el modelo contiene fallos claros.

Debes clasificar el fallo en una o varias de las siguientes categorías. Usa únicamente las etiquetas que sean realmente necesarias. No incluyas errores secundarios, dudosos o meramente contextuales.

Spatial Folding Deficit: Incapacidad para visualizar objetos 3D a partir de representaciones 2D. Incluye errores al plegar desarrollos planos para formar cubos, dados u otros sólidos.

Rule Hallucination: Invención de reglas, restricciones o condiciones que no aparecen en el problema, o ignorar reglas explícitamente dadas.

Visual Processing Failure (OCR): Error al interpretar información visual de la imagen, como números, letras, colores, posiciones, orientación o localización espacial de elementos.

False Geometric Relationships: Asumir relaciones geométricas no justificadas, como igualdades entre lados, radios, ángulos o longitudes sin evidencia suficiente.

Basic Counting Errors: Error al contar elementos discretos, como segmentos, celdas, figuras, objetos repetidos o casos simples.

Unnecessary Overcomplication: Uso de razonamientos o herramientas matemáticas innecesariamente complejas cuando el problema puede resolverse con una observación o lógica más simple.

Poor Figure Decomposition: Incapacidad para descomponer una figura compleja en partes simples, como regiones, áreas, triángulos, rectángulos u otras formas geométricas básicas.

Positional and Hierarchical Confusion: Confusión sobre la posición relativa, el orden, la orientación, la circularidad o la jerarquía espacial de los elementos. Incluye errores sobre qué objeto está encima, debajo, delante, detrás o conectado con otro.

Coincidental Correctness: El modelo llega a la respuesta correcta, pero mediante una explicación incorrecta, incoherente o basada en premisas falsas.

Process Inconsistency: El modelo cambia valores, premisas, conteos, relaciones o criterios durante la resolución, perdiendo coherencia interna.

INSTRUCCIONES DE CLASIFICACIÓN:
- Analiza cuidadosamente la relación entre el enunciado, la opción seleccionada y la traza de razonamiento.
- Identifica únicamente errores claramente apoyados por la traza.
- No añadas etiquetas por intuición si no hay evidencia suficiente.
- Si el modelo selecciona una opción correcta pero el razonamiento es incorrecto, usa "Coincidental Correctness" si aplica.
- Si el modelo selecciona una opción incorrecta, clasifica el tipo de fallo que explica mejor ese error.
- Si la traza es coherente y no contiene errores claros, devuelve "NO_ERROR".
- Es preferible devolver pocas etiquetas antes que sobreclasificar.

INSTRUCCIONES DE SALIDA:
Devuelve únicamente una lista válida estilo Python con las etiquetas.
No añadas explicación, comentarios, markdown ni texto adicional.

Ejemplo de salida:
["Basic Counting Errors", "Process Inconsistency", "Unnecessary Overcomplication"]

Si no se detecta ningún error de razonamiento, devuelve exactamente:
["NO_ERROR"]

EJEMPLOS

Ejemplo 1
Temática:
Geometría 3D

Enunciado del problema:
¿Qué cubo puede formarse al plegar el desarrollo plano proporcionado?

Opción seleccionada por el modelo:
B

Traza de razonamiento:
El desarrollo consta de 6 caras. La cara 1 está opuesta a la cara 3. Como las caras 2 y 4 son adyacentes, deben repelerse según la regla estándar de bloques de color. Además, al plegar la cara 5 sobre la 6 se crea un vértice esférico en lugar de una esquina. Por tanto, la opción B es correcta.

Salida:
["Spatial Folding Deficit", "Rule Hallucination"]

Ejemplo 2
Temática:
Lógica visual

Enunciado del problema:
Cuenta el número total de triángulos pequeños que se intersecan en la figura.

Opción seleccionada por el modelo:
D

Traza de razonamiento:
Vamos a contar los triángulos pequeños en la mitad superior: 1, 2, 3, 4, 5. Por tanto, hay 4 triángulos pequeños. En la mitad inferior hay 2. Entonces 4 + 2 = 6. Sin embargo, como la figura está delimitada por un círculo, debemos aplicar el teorema de Pitágoras usando el seno para verificar los ángulos, lo que da 14. Por tanto, la respuesta es 14.

Salida:
["Basic Counting Errors", "Process Inconsistency", "Unnecessary Overcomplication"]

Ejemplo 3
Temática:
Cálculo de áreas

Enunciado del problema:
Calcula el área de la región sombreada dentro del cuadrado si el lado mide 4.

Opción seleccionada por el modelo:
C

Traza de razonamiento:
La figura dentro del cuadrado parece un círculo. Como encaja perfectamente dentro del cuadrado, el radio debe ser exactamente igual al lado del cuadrado. Por tanto, radio = 4. El área es pi * 4^2 = 16pi. Como 16pi es aproximadamente 50.24, la respuesta es 50.24.

Salida:
["False Geometric Relationships"]

Ejemplo 4
Temática:
Álgebra básica

Enunciado del problema:
Resuelve x: 3x + 2 = 11.

Opción seleccionada por el modelo:
A

Traza de razonamiento:
Primero, restamos 2 a ambos lados de la ecuación para aislar el término con x. Esto da 3x = 9. Después, dividimos ambos lados entre 3. Esto da x = 3.

Salida:
["NO_ERROR"]

TAREA REAL

Temática:
{PROBLEM_THEME}

Enunciado del problema:
{PROBLEM_DESCRIPTION}

Opción seleccionada por el modelo:
{SELECTED_OPTION}

Traza de razonamiento:
{REASONING_TRACE}
"""

prompt_ingles_razon = """
You are an expert AI auditor specialized in analyzing reasoning errors in multimodal models and large language models.

Your task is to determine what type of failure the model committed when solving a mathematical or visual problem.

To classify the error, you must jointly consider:
- The problem theme.
- The problem statement.
- The option selected by the model.
- The model reasoning trace.

Do not evaluate only whether the final answer is correct or incorrect. Analyze whether the reasoning used by the model contains clear failures.

You must classify the failure into one or more of the following categories. Use only the labels that are truly necessary. Do not include secondary, doubtful, or merely contextual errors.

Spatial Folding Deficit: Inability to visualize 3D objects from 2D representations. Includes errors when folding nets into cubes, dice, or other solids.

Rule Hallucination: Inventing rules, constraints, or conditions that do not appear in the problem, or ignoring explicitly stated rules.

Visual Processing Failure (OCR): Error when interpreting visual information from the image, such as numbers, letters, colors, positions, orientation, or spatial location of elements.

False Geometric Relationships: Assuming unjustified geometric relationships, such as equalities between sides, radii, angles, or lengths without sufficient evidence.

Basic Counting Errors: Error when counting discrete elements, such as segments, cells, figures, repeated objects, or simple cases.

Unnecessary Overcomplication: Use of unnecessarily complex reasoning or mathematical tools when the problem can be solved with simpler observation or logic.

Poor Figure Decomposition: Inability to decompose a complex figure into simple parts, such as regions, areas, triangles, rectangles, or other basic geometric shapes.

Positional and Hierarchical Confusion: Confusion about the relative position, order, orientation, circularity, or spatial hierarchy of elements. Includes errors about which object is above, below, in front of, behind, or connected to another.

Coincidental Correctness: The model reaches the correct answer, but through an incorrect, incoherent, or false-premise-based explanation.

Process Inconsistency: The model changes values, premises, counts, relationships, or criteria during the solution, losing internal coherence.

CLASSIFICATION INSTRUCTIONS:
- Carefully analyze the relationship between the problem statement, the selected option, and the reasoning trace.
- Identify only errors clearly supported by the trace.
- Do not add labels by intuition if there is not enough evidence.
- If the model selects a correct option but the reasoning is incorrect, use "Coincidental Correctness" if applicable.
- If the model selects an incorrect option, classify the type of failure that best explains that error.
- If the trace is coherent and contains no clear errors, return "NO_ERROR".
- Prefer returning fewer labels rather than over-labeling.

OUTPUT INSTRUCTIONS:
Return only a valid Python-style list with the labels.
Do not add explanations, comments, markdown, or additional text.

Example output:
["Basic Counting Errors", "Process Inconsistency", "Unnecessary Overcomplication"]

If no reasoning error is detected, return exactly:
["NO_ERROR"]

REAL TASK

Theme:
{PROBLEM_THEME}

Problem statement:
{PROBLEM_DESCRIPTION}

Option selected by the model:
{SELECTED_OPTION}

Reasoning trace:
{REASONING_TRACE}
"""

prompt_frances_razon = """
Vous êtes un auditeur expert en IA spécialisé dans l’analyse des erreurs de raisonnement des modèles multimodaux et des grands modèles de langage.

Votre tâche consiste à déterminer quel type d’erreur le modèle a commis en résolvant un problème mathématique ou visuel.

Pour classer l’erreur, vous devez tenir compte conjointement :
- De la thématique du problème.
- De l’énoncé du problème.
- De l’option sélectionnée par le modèle.
- De la trace de raisonnement du modèle.

N’évaluez pas seulement si la réponse finale est correcte ou incorrecte. Analysez si le raisonnement utilisé par le modèle contient des erreurs claires.

Vous devez classer l’erreur dans une ou plusieurs des catégories suivantes. Utilisez uniquement les étiquettes réellement nécessaires. N’incluez pas d’erreurs secondaires, douteuses ou simplement contextuelles.

Spatial Folding Deficit: Incapacité à visualiser des objets 3D à partir de représentations 2D. Inclut les erreurs lors du pliage de patrons pour former des cubes, des dés ou d’autres solides.

Rule Hallucination: Invention de règles, contraintes ou conditions qui n’apparaissent pas dans le problème, ou ignorance de règles explicitement données.

Visual Processing Failure (OCR): Erreur d’interprétation des informations visuelles de l’image, comme les nombres, lettres, couleurs, positions, orientation ou localisation spatiale des éléments.

False Geometric Relationships: Supposition de relations géométriques non justifiées, comme des égalités entre côtés, rayons, angles ou longueurs sans preuve suffisante.

Basic Counting Errors: Erreur dans le comptage d’éléments discrets, comme des segments, cellules, figures, objets répétés ou cas simples.

Unnecessary Overcomplication: Utilisation de raisonnements ou d’outils mathématiques inutilement complexes alors que le problème peut être résolu par une observation ou une logique plus simple.

Poor Figure Decomposition: Incapacité à décomposer une figure complexe en parties simples, comme des régions, aires, triangles, rectangles ou autres formes géométriques de base.

Positional and Hierarchical Confusion: Confusion sur la position relative, l’ordre, l’orientation, la circularité ou la hiérarchie spatiale des éléments. Inclut les erreurs sur quel objet est au-dessus, en dessous, devant, derrière ou connecté à un autre.

Coincidental Correctness: Le modèle arrive à la bonne réponse, mais au moyen d’une explication incorrecte, incohérente ou fondée sur de fausses prémisses.

Process Inconsistency: Le modèle modifie des valeurs, prémisses, comptages, relations ou critères pendant la résolution, perdant ainsi sa cohérence interne.

INSTRUCTIONS DE CLASSIFICATION :
- Analysez soigneusement la relation entre l’énoncé, l’option sélectionnée et la trace de raisonnement.
- Identifiez uniquement les erreurs clairement appuyées par la trace.
- N’ajoutez pas d’étiquettes par intuition s’il n’y a pas suffisamment de preuves.
- Si le modèle sélectionne une option correcte mais que le raisonnement est incorrect, utilisez "Coincidental Correctness" si cela s’applique.
- Si le modèle sélectionne une option incorrecte, classez le type d’erreur qui explique le mieux cette erreur.
- Si la trace est cohérente et ne contient pas d’erreurs claires, retournez "NO_ERROR".
- Il est préférable de retourner peu d’étiquettes plutôt que de surclasser.

INSTRUCTIONS DE SORTIE :
Retournez uniquement une liste valide au format Python avec les étiquettes.
N’ajoutez aucune explication, commentaire, markdown ou texte supplémentaire.

Exemple de sortie :
["Basic Counting Errors", "Process Inconsistency", "Unnecessary Overcomplication"]

Si aucune erreur de raisonnement n’est détectée, retournez exactement :
["NO_ERROR"]

TÂCHE RÉELLE

Thématique :
{PROBLEM_THEME}

Énoncé du problème :
{PROBLEM_DESCRIPTION}

Option sélectionnée par le modèle :
{SELECTED_OPTION}

Trace de raisonnement :
{REASONING_TRACE}
"""

prompt_valenciano_razon = """
Ets un auditor expert en IA especialitzat en analitzar errors de raonament en models multimodals i models de llenguatge.

La teua tasca consisteix a determinar quin tipus d’error ha comés el model en resoldre un problema matemàtic o visual.

Per classificar l’error has de tindre en compte conjuntament:
- La temàtica del problema.
- L’enunciat del problema.
- L’opció seleccionada pel model.
- La traça de raonament del model.

No avalues només si la resposta final és correcta o incorrecta. Analitza si el raonament utilitzat pel model conté errors clars.

Has de classificar l’error en una o diverses de les categories següents. Utilitza únicament les etiquetes que siguen realment necessàries. No inclogues errors secundaris, dubtosos o merament contextuals.

Spatial Folding Deficit: Incapacitat per visualitzar objectes 3D a partir de representacions 2D. Inclou errors en plegar desenvolupaments plans per formar cubs, daus o altres sòlids.

Rule Hallucination: Invenció de regles, restriccions o condicions que no apareixen en el problema, o ignorar regles explícitament donades.

Visual Processing Failure (OCR): Error en interpretar informació visual de la imatge, com números, lletres, colors, posicions, orientació o localització espacial d’elements.

False Geometric Relationships: Assumir relacions geomètriques no justificades, com igualtats entre costats, radis, angles o longituds sense evidència suficient.

Basic Counting Errors: Error en comptar elements discrets, com segments, cel·les, figures, objectes repetits o casos simples.

Unnecessary Overcomplication: Ús de raonaments o ferramentes matemàtiques innecessàriament complexes quan el problema pot resoldre’s amb una observació o lògica més simple.

Poor Figure Decomposition: Incapacitat per descompondre una figura complexa en parts simples, com regions, àrees, triangles, rectangles o altres formes geomètriques bàsiques.

Positional and Hierarchical Confusion: Confusió sobre la posició relativa, l’ordre, l’orientació, la circularitat o la jerarquia espacial dels elements. Inclou errors sobre quin objecte està damunt, davall, davant, darrere o connectat amb un altre.

Coincidental Correctness: El model arriba a la resposta correcta, però mitjançant una explicació incorrecta, incoherent o basada en premisses falses.

Process Inconsistency: El model canvia valors, premisses, recomptes, relacions o criteris durant la resolució, perdent coherència interna.

INSTRUCCIONS DE CLASSIFICACIÓ:
- Analitza acuradament la relació entre l’enunciat, l’opció seleccionada i la traça de raonament.
- Identifica únicament errors clarament recolzats per la traça.
- No afegisques etiquetes per intuïció si no hi ha evidència suficient.
- Si el model selecciona una opció correcta però el raonament és incorrecte, usa "Coincidental Correctness" si aplica.
- Si el model selecciona una opció incorrecta, classifica el tipus d’error que millor explica eixe error.
- Si la traça és coherent i no conté errors clars, retorna "NO_ERROR".
- És preferible retornar poques etiquetes abans que sobreclassificar.

INSTRUCCIONS D’EIXIDA:
Retorna únicament una llista vàlida estil Python amb les etiquetes.
No afegisques explicació, comentaris, markdown ni text addicional.

Exemple d’eixida:
["Basic Counting Errors", "Process Inconsistency", "Unnecessary Overcomplication"]

Si no es detecta cap error de raonament, retorna exactament:
["NO_ERROR"]

TASCA REAL

Temàtica:
{PROBLEM_THEME}

Enunciat del problema:
{PROBLEM_DESCRIPTION}

Opció seleccionada pel model:
{SELECTED_OPTION}

Traça de raonament:
{REASONING_TRACE}
"""

prompts_razon = {
    "ingles": prompt_ingles_razon,
    "castellano": prompt_espanol_razon,
    "frances": prompt_frances_razon,
    "valenciano": prompt_valenciano_razon
}

def texto_seguro(valor):
    if pd.isna(valor):
        return ''
    return str(valor)


def normalizar_idioma(idioma):
    idioma = texto_seguro(idioma).strip().lower()
    equivalencias = {
        'espanol': 'castellano',
        'español': 'castellano',
        'spanish': 'castellano',
        'english': 'ingles',
        'inglés': 'ingles',
        'francés': 'frances',
        'french': 'frances',
        'valencia': 'valenciano',
        'valencià': 'valenciano',
        'catalan': 'valenciano',
        'català': 'valenciano',
    }
    return equivalencias.get(idioma, idioma)


def bloque_opciones(opciones, idioma):
    etiquetas = {
        'ingles': 'Options',
        'castellano': 'Opciones',
        'frances': 'Options',
        'valenciano': 'Opcions',
    }
    return f"\n\n{etiquetas.get(idioma, 'Opciones')}:\n{texto_seguro(opciones)}"


def rellenar_plantilla(plantilla, problema, extra=None):
    valores = {
        'PROBLEM_THEME': problema['tematica'],
        'PROBLEM_DESCRIPTION': problema['enunciado'],
        'PROBLEM_OPTIONS': problema['opciones'],
    }
    if extra:
        valores.update(extra)

    prompt = plantilla
    for clave, valor in valores.items():
        prompt = prompt.replace('{' + clave + '}', texto_seguro(valor))
    return prompt


def construir_prompt_desc(problema):
    idioma = problema['idioma']
    prompt = rellenar_plantilla(prompts_desc[idioma], problema)
    return prompt + bloque_opciones(problema['opciones'], idioma)


def construir_prompt_razon(problema, razonamiento, respuesta_modelo):
    idioma = problema['idioma']
    prompt = rellenar_plantilla(
        prompts_razon[idioma],
        problema,
        {
            'SELECTED_OPTION': respuesta_modelo,
            'REASONING_TRACE': razonamiento,
        },
    )
    return prompt + bloque_opciones(problema['opciones'], idioma)

def descargar_bytes_imagen(url):
    respuesta = requests.get(url, timeout=30)
    respuesta.raise_for_status()
    return respuesta.content


def descargar_imagen(url):
    return Image.open(BytesIO(descargar_bytes_imagen(url)))


def imagen_url_a_base64(url):
    return base64.b64encode(descargar_bytes_imagen(url)).decode('utf-8')


def leer_problema(indice_original, dataset):
    fila = dataset.loc[indice_original]
    idioma = normalizar_idioma(fila['idioma'])

    if idioma not in prompts_desc or idioma not in prompts_razon:
        raise ValueError(f'Idioma no soportado: {fila["idioma"]}')

    return {
        'indice_original': int(indice_original),
        'idioma': idioma,
        'referencia': texto_seguro(fila.get('Referencia', '')),
        'enunciado': texto_seguro(fila['Enunciado']),
        'tematica': texto_seguro(fila.get('Tematica', '')),
        'opciones': texto_seguro(fila['Opciones']),
        'imagen_url': texto_seguro(fila['enlace']),
        'respuesta_real': texto_seguro(fila['ground truth']),
        'razon_google': texto_seguro(fila['reasoning Gemini 2.0 Flash']),
        'respuesta_google': texto_seguro(fila['response Gemini 2.0 Flash']),
        'razon_qwen': texto_seguro(fila['reasoning Qwen-VL 7B']),
        'respuesta_qwen': texto_seguro(fila['response Qwen-VL 7B']),
    }


def construir_prompts(problema):
    return {
        'desc': construir_prompt_desc(problema),
        'razon_google': construir_prompt_razon(
            problema,
            razonamiento=problema['razon_google'],
            respuesta_modelo=problema['respuesta_google'],
        ),
        'razon_qwen': construir_prompt_razon(
            problema,
            razonamiento=problema['razon_qwen'],
            respuesta_modelo=problema['respuesta_qwen'],
        ),
    }


def llamar_modelo_visual(imagen_url, prompt, model=VISION_MODEL):
    imagen_b64 = imagen_url_a_base64(imagen_url)
    respuesta = chat(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': prompt,
                'images': [imagen_b64],
            }
        ],
        options={
            'temperature': 0,
            'max_tokens': 512,
        },
    )
    return respuesta['message']['content'].strip()


def ejecutar_llamada(imagen_url, prompt):
    try:
        return {
            'prompt': prompt,
            'respuesta': llamar_modelo_visual(imagen_url, prompt),
            'error': None,
        }
    except Exception as e:
        return {
            'prompt': prompt,
            'respuesta': None,
            'error': repr(e),
        }

def procesar_muestra(indice_original, dataset):
    problema = leer_problema(indice_original, dataset)
    prompts = construir_prompts(problema)
    imagen_url = problema['imagen_url']

    return {
        'indice_original': problema['indice_original'],
        'referencia': problema['referencia'],
        'idioma': problema['idioma'],
        'enunciado': problema['enunciado'],
        'opciones': problema['opciones'],
        'tematica': problema['tematica'],
        'imagen_url': imagen_url,
        'respuesta_real': problema['respuesta_real'],
        'desc': ejecutar_llamada(imagen_url, prompts['desc']),
        'razon_google': {
            'razonamiento_original': problema['razon_google'],
            'respuesta_original': problema['respuesta_google'],
            **ejecutar_llamada(imagen_url, prompts['razon_google']),
        },
        'razon_qwen': {
            'razonamiento_original': problema['razon_qwen'],
            'respuesta_original': problema['respuesta_qwen'],
            **ejecutar_llamada(imagen_url, prompts['razon_qwen']),
        },
        'error_muestra': None,
    }


def resultado_error(indice_original, error):
    return {
        'indice_original': int(indice_original),
        'referencia': None,
        'idioma': None,
        'enunciado': None,
        'opciones': None,
        'tematica': None,
        'imagen_url': None,
        'respuesta_real': None,
        'desc': None,
        'razon_google': None,
        'razon_qwen': None,
        'error_muestra': {
            'tipo': type(error).__name__,
            'mensaje': str(error),
            'traceback': traceback.format_exc(),
        },
    }


def guardar_json(resultados, path):
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    tmp_path.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    tmp_path.replace(path)


def cargar_resultados(path):
    path = Path(path)
    if not path.exists():
        return []

    try:
        datos = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(datos, list):
            raise ValueError('El JSON existente no contiene una lista.')
        return datos
    except Exception as e:
        backup = path.with_name(f'{path.stem}_corrupto_{datetime.now().strftime("%Y%m%d_%H%M%S")}{path.suffix}')
        path.replace(backup)
        print(f'No se pudo leer {path}. Se ha movido a {backup}. Error: {e}')
        return []


def resolver_dataset_path(valor):
    if valor is not None:
        return Path(valor)

    candidatos = [
        Path('../DatasetFull.csv'),
        Path('DatasetFull.csv'),
        Path('/home/cguiesc/pablo_gandia/Replicar/DatasetFull.csv'),
    ]
    return next((path for path in candidatos if path.exists()), candidatos[0])


def cargar_dependencias():
    global pd, requests, Image, chat

    import pandas as pandas_mod
    import requests as requests_mod
    from PIL import Image as image_mod
    from ollama import chat as chat_mod

    pd = pandas_mod
    requests = requests_mod
    Image = image_mod
    chat = chat_mod


def parse_args():
    parser = argparse.ArgumentParser(description='Procesa todo el dataframe filtrado y guarda JSON cada N muestras.')
    parser.add_argument('--dataset', default=None, help='Ruta al DatasetFull.csv. Por defecto prueba rutas conocidas.')
    parser.add_argument('--output', default='replicacion.json', help='Ruta del JSON de salida.')
    parser.add_argument('--model', default='qwen2.5vl:7b', help='Modelo visual de Ollama.')
    parser.add_argument('--save-every', type=int, default=10, help='Guardar cada N muestras procesadas.')
    parser.add_argument('--restart', action='store_true', help='Ignora el JSON existente y empieza desde cero.')
    return parser.parse_args()


def main():
    global VISION_MODEL

    args = parse_args()
    dataset_path = resolver_dataset_path(args.dataset)
    output_path = Path(args.output)
    save_every = max(1, args.save_every)
    VISION_MODEL = args.model

    cargar_dependencias()

    print(f'Dataset: {dataset_path}')
    print(f'Modelo visual: {VISION_MODEL}')
    print(f'JSON de salida: {output_path}')
    print(f'Guardado cada: {save_every} muestras')

    df = pd.read_csv(dataset_path)
    df_filtrado = df[df['Imagen'] == 'SI'].copy()
    indices_originales = [int(i) for i in df_filtrado.index]

    if args.restart:
        resultados = []
    else:
        resultados = cargar_resultados(output_path)

    procesados = {int(item['indice_original']) for item in resultados if 'indice_original' in item}
    pendientes = [indice for indice in indices_originales if indice not in procesados]

    print(f'Total dataset: {len(df)}')
    print(f'Muestras con imagen: {len(df_filtrado)}')
    print(f'Ya procesadas: {len(procesados)}')
    print(f'Pendientes: {len(pendientes)}')

    detener = {'valor': False}

    def pedir_parada(signum, frame):
        detener['valor'] = True
        print('\nParada solicitada. Guardando al terminar la muestra actual...')

    signal.signal(signal.SIGINT, pedir_parada)
    signal.signal(signal.SIGTERM, pedir_parada)

    desde_ultimo_guardado = 0

    for posicion, indice_original in enumerate(pendientes, start=1):
        print(f'Procesando {posicion}/{len(pendientes)} - indice original {indice_original}...')

        try:
            resultado = procesar_muestra(indice_original, df)
        except Exception as e:
            print(f'ERROR en indice original {indice_original}: {type(e).__name__}: {e}')
            resultado = resultado_error(indice_original, e)

        resultados.append(resultado)
        procesados.add(indice_original)
        desde_ultimo_guardado += 1

        if desde_ultimo_guardado >= save_every:
            guardar_json(resultados, output_path)
            print(f'Guardado: {len(resultados)} registros en {output_path}')
            desde_ultimo_guardado = 0

        if detener['valor']:
            break

    guardar_json(resultados, output_path)
    print(f'Procesamiento terminado. Total guardado: {len(resultados)} registros en {output_path}')

    errores_muestra = sum(1 for item in resultados if item.get('error_muestra'))
    errores_llamadas = sum(
        1
        for item in resultados
        for key in ('desc', 'razon_google', 'razon_qwen')
        if isinstance(item.get(key), dict) and item[key].get('error')
    )
    print(f'Errores de muestra: {errores_muestra}')
    print(f'Errores de llamadas al modelo: {errores_llamadas}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'ERROR FATAL antes o despues del bucle principal: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
