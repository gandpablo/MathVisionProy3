# verify_option_A1_B2 (castellano)

```text
f"""
Eres un experto resolviendo preguntas matemáticas tipo test.

Estás evaluando UNA sola opción.
- El enunciado es solo texto.
- Las opciones son figuras.
- Recibirás una imagen: normalmente la figura de la opción {letra_opcion}; si el recorte falló, recibirás la imagen completa de la pregunta.

Enunciado:
{statement_text}

Plan de resolución:
{plan}

Opción a evaluar:
- Letra: {letra_opcion}
- La imagen recibida corresponde a esta opción o, si es la imagen completa, debes localizar la opción {letra_opcion}.

Tu tarea:
Determina si la figura de esta opción cumple el enunciado.

Instrucciones:
- Usa el enunciado, la imagen de la opción y el plan.
- Si recibes la imagen completa, analiza solo la opción {letra_opcion}.
- Razona paso a paso.
- Evalúa solo esta opción.
- No compares con otras opciones.
- No elijas respuesta final global.
- Comprueba visualmente forma, cantidades, orientación, posiciones, simetrías, medidas o relaciones necesarias.
- Si el recorte o la imagen completa no permiten decidir, marca uncertain.
- Justifica claramente qué observaciones te llevan a esa conclusión.

Devuelve únicamente un JSON válido:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Razonamiento breve pero suficiente.",
  "visual_observations": [
    "Observación breve y relevante extraída de la figura de la opción."
  ],
  "checks": [
    "Criterio comprobado en esta opción."
  ]
}}

Respuesta:
""".strip()
```
