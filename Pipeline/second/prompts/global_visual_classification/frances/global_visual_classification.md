# global_visual_classification (frances)

```text
Analyse l'image de cette question à choix multiple.

Ne résous pas le problème et n'indique pas la bonne réponse.

Renvoie uniquement un objet JSON valide avec ces informations:

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

Critères:

statement_text: Le texte de l'énoncé, ou null si l'énoncé est seulement une image.
options_text: Un dictionnaire avec le texte de chaque option, ou null si les options sont seulement des images.

- A.1: l'énoncé est uniquement textuel.
- A.2: l'énoncé contient une figure pertinente.
- B.1: les options (A,B,C,D,E) sont du texte, des nombres ou des expressions, pas des figures.
- B.2: les options possibles (A, B, C, D, E) ne sont pas textuelles ni numériques, mais des figures.
- Si les options sont B.2, mets null dans toutes les options.
- Ignore les restes d'autres questions.
- Si tu vois que le dictionnaire options_text contient du contenu alors que tu avais mis B.2, c'est B.1.
```
