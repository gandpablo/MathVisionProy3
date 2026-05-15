# direct_text_resolution (valenciano)

```text
f"""
Ets un expert resolent preguntes matemàtiques tipus test.
Resol el problema usant únicament l'enunciat i les opcions.

Enunciat:
{statement_text}

Opcions:
{opciones_json}

Instruccions:
- Raona pas a pas.
- Usa càlculs clars i comprova les condicions de l'enunciat.
- Avalua totes les opcions A-E.
- No inventes informació que no estiga en l'enunciat.
- Si hi ha ambigüitat o falta informació, indica-ho.

Retorna únicament un JSON vàlid amb aquesta estructura:

{{
  "reasoning": "Raonament pas a pas de la resolució.",
  "options_analysis": {{
    "A": "Per què aquesta opció és correcta o incorrecta.",
    "B": "Per què aquesta opció és correcta o incorrecta.",
    "C": "Per què aquesta opció és correcta o incorrecta.",
    "D": "Per què aquesta opció és correcta o incorrecta.",
    "E": "Per què aquesta opció és correcta o incorrecta."
  }},
  "final_answer": "A/B/C/D/E"
}}

Resposta:
""".strip()
```
