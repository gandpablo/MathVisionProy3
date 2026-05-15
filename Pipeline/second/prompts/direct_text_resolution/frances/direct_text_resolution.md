# direct_text_resolution (frances)

```text
f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.
Résous le problème en utilisant uniquement l'énoncé et les options.

Énoncé:
{statement_text}

Options:
{opciones_json}

Instructions:
- Raisonne étape par étape.
- Utilise des calculs clairs et vérifie les conditions de l'énoncé.
- Évalue toutes les options A-E.
- N'invente pas d'informations qui ne sont pas dans l'énoncé.
- S'il y a une ambiguïté ou des informations manquantes, indique-le.

Renvoie uniquement un objet JSON valide avec cette structure:

{{
  "reasoning": "Raisonnement étape par étape de la résolution.",
  "options_analysis": {{
    "A": "Pourquoi cette option est correcte ou incorrecte.",
    "B": "Pourquoi cette option est correcte ou incorrecte.",
    "C": "Pourquoi cette option est correcte ou incorrecte.",
    "D": "Pourquoi cette option est correcte ou incorrecte.",
    "E": "Pourquoi cette option est correcte ou incorrecte."
  }},
  "final_answer": "A/B/C/D/E"
}}

Réponse:
""".strip()
```
