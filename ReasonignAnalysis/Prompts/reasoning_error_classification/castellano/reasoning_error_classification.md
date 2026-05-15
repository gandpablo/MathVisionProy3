# reasoning_error_classification (castellano)

```text
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
```
