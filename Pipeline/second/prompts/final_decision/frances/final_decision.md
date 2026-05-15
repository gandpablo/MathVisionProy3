# final_decision (frances)

```text
f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.

Chaque option a déjà été évaluée séparément avec un modèle visuel.
Tu dois maintenant prendre une décision finale en utilisant les raisonnements individuels.

Classification:
- Énoncé: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Énoncé:
{statement_text}

Options:
{opciones}

Raisonnements individuels par option:
{razonamientos_json}

Ta tâche:
- Analyse étape par étape les raisonnements de toutes les options.
- Décide laquelle des cinq options A, B, C, D ou E est la bonne réponse.
- Donne un raisonnement général qui justifie pourquoi cette option est correcte.
- Utilise aussi les raisonnements individuels pour écarter les autres options.
- S'il y a des contradictions entre les raisonnements, privilégie le raisonnement le plus cohérent avec l'énoncé.
- Si une option apparaît comme uncertain, ne l'écarte pas automatiquement: évalue si elle peut tout de même être la meilleure.
- N'invente pas d'informations visuelles qui n'apparaissent pas dans les raisonnements.
- Tu dois choisir exactement une option parmi A, B, C, D et E.

Renvoie uniquement un objet JSON valide avec cette structure:

{{
  "answer": "A|B|C|D|E",
  "reasoning": "Raisonnement général étape par étape, expliquant pourquoi l'option choisie est correcte et pourquoi les autres ne le sont pas."
}}

Réponse:
""".strip()
```
