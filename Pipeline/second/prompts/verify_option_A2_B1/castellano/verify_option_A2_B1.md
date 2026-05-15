# verify_option_A2_B1 (castellano)

```text
f"""
Eres un experto resolviendo preguntas matemáticas tipo test.

Estás evaluando UNA sola opción.
- El enunciado tiene una figura relevante.
- Las opciones son texto, número o expresión.
- Recibirás una imagen: normalmente la figura del enunciado; si el recorte falló, recibirás la imagen completa de la pregunta.
- La opción actual es textual.

Enunciado:
{statement_text}

Plan de resolución:
{plan}

Opción a evaluar:
- Letra: {letra_opcion}
- Valor: {option_text}

Tu tarea:
Determina si esta opción individual puede ser la respuesta correcta.

Instrucciones:
- Usa el enunciado, la figura del enunciado y el plan.
- Si recibes la imagen completa, localiza visualmente la figura relevante del enunciado y no te apoyes en otras opciones.
- Razona paso a paso.
- Comprueba explícitamente el valor propuesto por la opción.
- No compares con otras opciones.
- No elijas respuesta final global.
- Si la figura no permite comprobarlo con seguridad, marca uncertain.
- Justifica claramente qué observaciones te llevan a esa conclusión.

Devuelve únicamente un JSON válido:

{{
  "option": "{letra_opcion}",
  "option_value": {json.dumps(option_text, ensure_ascii=False)},
  "status": "correct|incorrect|uncertain",
  "reasoning": "Razonamiento breve pero suficiente.",
  "visual_observations": [
    "Observación breve y relevante extraída de la figura del enunciado."
  ],
  "checks": [
    "Criterio comprobado en esta opción."
  ]
}}

Respuesta:
""".strip()
```
