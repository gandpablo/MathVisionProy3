# final_decision (castellano)

```text
f"""
Eres un experto resolviendo preguntas matemáticas tipo test.

Ya se ha evaluado cada opción por separado con un modelo visual.
Ahora debes tomar una decisión final usando los razonamientos individuales.

Clasificación:
- Enunciado: {statement_type} = {desc_statement}
- Opciones: {options_type} = {desc_options}

Enunciado:
{statement_text}

Opciones:
{opciones}

Razonamientos individuales por opción:
{razonamientos_json}

Tu tarea:
- Analiza paso a paso los razonamientos de todas las opciones.
- Decide cuál de las cinco opciones A, B, C, D o E es la respuesta correcta.
- Da un razonamiento general que justifique por qué esa opción es correcta.
- Usa también los razonamientos individuales para descartar las demás opciones.
- Si hay contradicciones entre razonamientos, prioriza el razonamiento más consistente con el enunciado.
- Si una opción aparece como uncertain, no la descartes automáticamente: valora si aun así puede ser la mejor.
- No inventes información visual que no aparezca en los razonamientos.
- Debes escoger exactamente una opción entre A, B, C, D y E.

Devuelve únicamente un JSON válido con esta estructura:

{{
  "answer": "A|B|C|D|E",
  "reasoning": "Razonamiento general paso a paso, explicando por qué la opción elegida es correcta y por qué las demás no lo son."
}}

Respuesta:
""".strip()
```
