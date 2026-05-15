# global_visual_classification (valenciano)

```text
Analitza la imatge d'aquesta pregunta tipus test.

No resolgues el problema ni indiques la resposta correcta.

Retorna únicament un JSON vàlid amb aquesta informació:

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

Criteris:

statement_text: El text de l'enunciat, o null si l'enunciat és només una imatge.
options_text: Un diccionari amb el text de cada opció, o null si les opcions són només imatges.

- A.1: l'enunciat és només text.
- A.2: l'enunciat té una figura rellevant.
- B.1: les opcions (A,B,C,D,E) són text, nombres o expressions, no figures.
- B.2: les opcions possibles (A, B, C, D, E) no són de text ni numèriques, sinó figures.
- Si les opcions són B.2, posa null en totes les opcions.
- Ignora restes d'altres preguntes.
- Si veus que el diccionari options_text té contingut i havies posat B.2, aleshores és B.1.
```
