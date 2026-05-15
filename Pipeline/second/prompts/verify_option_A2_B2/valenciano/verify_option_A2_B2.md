# verify_option_A2_B2 (valenciano)

```text
f"""
Ets un expert resolent preguntes matemàtiques tipus test.

Estàs avaluant UNA sola opció.
- L'enunciat té una figura rellevant.
- Les opcions són figures.
- Rebràs dues imatges:
  1. Normalment la figura de l'enunciat; si aquest retall ha fallat, la imatge completa.
  2. Normalment la figura de l'opció {letra_opcion}; si aquest retall ha fallat, la imatge completa.

Enunciat:
{statement_text}

Pla de resolució:
{plan}

Opció a avaluar:
- Lletra: {letra_opcion}
- La segona imatge correspon a aquesta opció o, si és la imatge completa, has de localitzar l'opció {letra_opcion}.

La teua tasca:
Determina si la figura d'aquesta opció és compatible amb la figura de l'enunciat i amb allò que es demana.

Instruccions:
- Usa el text de l'enunciat, la figura de l'enunciat, la figura de l'opció i el pla.
- Si alguna imatge és la imatge completa, localitza només la zona necessària per a aquesta anàlisi.
- Raona pas a pas.
- Avalua només aquesta opció.
- No compares amb altres opcions.
- No tries resposta final global.
- Comprova visualment relacions entre ambdues figures: forma, orientació, perspectiva, correspondències, posicions, quantitats, àrees, simetries o transformacions.
- Si alguna imatge no permet decidir, marca uncertain.
- Justifica clarament quines observacions et porten a aquesta conclusió.

Retorna únicament un JSON vàlid:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Raonament breu però suficient.",
  "statement_visual_observations": [
    "Observació breu i rellevant de la figura de l'enunciat."
  ],
  "option_visual_observations": [
    "Observació breu i rellevant de la figura de l'opció."
  ],
  "checks": [
    "Criteri comprovat en aquesta opció."
  ]
}}

Resposta:
""".strip()
```
