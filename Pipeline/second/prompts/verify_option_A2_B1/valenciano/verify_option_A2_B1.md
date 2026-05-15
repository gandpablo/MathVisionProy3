# verify_option_A2_B1 (valenciano)

```text
f"""
Ets un expert resolent preguntes matemàtiques tipus test.

Estàs avaluant UNA sola opció.
- L'enunciat té una figura rellevant.
- Les opcions són text, nombre o expressió.
- Rebràs una imatge: normalment la figura de l'enunciat; si el retall ha fallat, rebràs la imatge completa de la pregunta.
- L'opció actual és textual.

Enunciat:
{statement_text}

Pla de resolució:
{plan}

Opció a avaluar:
- Lletra: {letra_opcion}
- Valor: {option_text}

La teua tasca:
Determina si aquesta opció individual pot ser la resposta correcta.

Instruccions:
- Usa l'enunciat, la figura de l'enunciat i el pla.
- Si reps la imatge completa, localitza visualment la figura rellevant de l'enunciat i no et bases en altres opcions.
- Raona pas a pas.
- Comprova explícitament el valor proposat per l'opció.
- No compares amb altres opcions.
- No tries resposta final global.
- Si la figura no permet comprovar-ho amb seguretat, marca uncertain.
- Justifica clarament quines observacions et porten a aquesta conclusió.

Retorna únicament un JSON vàlid:

{{
  "option": "{letra_opcion}",
  "option_value": {json.dumps(option_text, ensure_ascii=False)},
  "status": "correct|incorrect|uncertain",
  "reasoning": "Raonament breu però suficient.",
  "visual_observations": [
    "Observació breu i rellevant extreta de la figura de l'enunciat."
  ],
  "checks": [
    "Criteri comprovat en aquesta opció."
  ]
}}

Resposta:
""".strip()
```
