# global_visual_classification (castellano)

```text
Analiza la imagen de esta pregunta tipo test.

No resuelvas el problema ni indiques la respuesta correcta.

Devuelve únicamente un JSON válido con esta información:

{
  "statement_type": "A.1" or "A.2",
  "options_type": "B.1" or "B.2",
  "statement_text": "...",
  "options_text": {
    "A": "... or null",
    "B": "... or null",
    "C": "... or null",
    "D": "... or null",
    "E": "... or null"
  },
}

Criterios:

statement_text: El texto del enunciado, o null si el enunciado es solo una imagen.
options_text: Un diccionario con el texto de cada opción, o null si las opciones son solo imágenes.

- A.1: el enunciado es solo texto.
- A.2: el enunciado tiene figura relevante.
- B.1: las opciones (A,B,C,D,E) son texto, números o expresiones, no figuras.
- B.2: las opciones posibles (A, B, C, D, E) no son de texto o numericas, sino que son figuras.
- Si las opciones son B.2, pon null en todas las opciones.
- Ignora restos de otras preguntas.
- Si ves que el diccionario options_text tiene contenido, si habias puesto B.2, es B.1.
```
