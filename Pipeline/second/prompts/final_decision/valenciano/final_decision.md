# final_decision (valenciano)

```text
f"""
Ets un expert resolent preguntes matemàtiques tipus test.

Ja s'ha avaluat cada opció per separat amb un model visual.
Ara has de prendre una decisió final usant els raonaments individuals.

Classificació:
- Enunciat: {statement_type} = {desc_statement}
- Opcions: {options_type} = {desc_options}

Enunciat:
{statement_text}

Opcions:
{opciones}

Raonaments individuals per opció:
{razonamientos_json}

La teua tasca:
- Analitza pas a pas els raonaments de totes les opcions.
- Decideix quina de les cinc opcions A, B, C, D o E és la resposta correcta.
- Dona un raonament general que justifique per què aquesta opció és correcta.
- Usa també els raonaments individuals per a descartar les altres opcions.
- Si hi ha contradiccions entre raonaments, prioritza el raonament més consistent amb l'enunciat.
- Si una opció apareix com uncertain, no la descartes automàticament: valora si així i tot pot ser la millor.
- No inventes informació visual que no aparega en els raonaments.
- Has d'escollir exactament una opció entre A, B, C, D i E.

Retorna únicament un JSON vàlid amb aquesta estructura:

{{
  "answer": "A|B|C|D|E",
  "reasoning": "Raonament general pas a pas, explicant per què l'opció triada és correcta i per què les altres no ho són."
}}

Resposta:
""".strip()
```
