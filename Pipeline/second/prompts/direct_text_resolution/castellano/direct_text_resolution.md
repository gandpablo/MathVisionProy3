# direct_text_resolution (castellano)

```text
f"""
Eres un experto resolviendo preguntas matemáticas tipo test.
Resuelve el problema usando únicamente el enunciado y las opciones.

Enunciado:
{statement_text}

Opciones:
{opciones_json}

Instrucciones:
- Razona paso a paso.
- Usa cálculos claros y comprueba las condiciones del enunciado.
- Evalúa todas las opciones A-E.
- No inventes información que no esté en el enunciado.
- Si hay ambigüedad o falta información, indícalo.

Devuelve únicamente un JSON válido con esta estructura:

{{
  "reasoning": "Razonamiento paso a paso de la resolución.",
  "options_analysis": {{
    "A": "Por qué esta opción es correcta o incorrecta.",
    "B": "Por qué esta opción es correcta o incorrecta.",
    "C": "Por qué esta opción es correcta o incorrecta.",
    "D": "Por qué esta opción es correcta o incorrecta.",
    "E": "Por qué esta opción es correcta o incorrecta."
  }},
  "final_answer": "A/B/C/D/E"
}}

Respuesta:
""".strip()
```
