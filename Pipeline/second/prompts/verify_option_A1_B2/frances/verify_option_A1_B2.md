# verify_option_A1_B2 (frances)

```text
f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.

Tu évalues UNE seule option.
- L'énoncé est uniquement textuel.
- Les options sont des figures.
- Tu recevras une image: normalement la figure de l'option {letra_opcion}; si le recadrage a échoué, tu recevras l'image complète de la question.

Énoncé:
{statement_text}

Plan de résolution:
{plan}

Option à évaluer:
- Lettre: {letra_opcion}
- L'image reçue correspond à cette option ou, si c'est l'image complète, tu dois localiser l'option {letra_opcion}.

Ta tâche:
Détermine si la figure de cette option satisfait l'énoncé.

Instructions:
- Utilise l'énoncé, l'image de l'option et le plan.
- Si tu reçois l'image complète, analyse uniquement l'option {letra_opcion}.
- Raisonne étape par étape.
- Évalue uniquement cette option.
- Ne compare pas avec les autres options.
- Ne choisis pas de réponse finale globale.
- Vérifie visuellement la forme, les quantités, l'orientation, les positions, les symétries, les mesures ou les relations nécessaires.
- Si le recadrage ou l'image complète ne permet pas de décider, marque uncertain.
- Justifie clairement quelles observations te conduisent à cette conclusion.

Renvoie uniquement un objet JSON valide:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Raisonnement bref mais suffisant.",
  "visual_observations": [
    "Observation brève et pertinente extraite de la figure de l'option."
  ],
  "checks": [
    "Critère vérifié pour cette option."
  ]
}}

Réponse:
""".strip()
```
