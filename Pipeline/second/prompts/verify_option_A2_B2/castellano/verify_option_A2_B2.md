# verify_option_A2_B2 (castellano)

```text
f"""
Eres un experto resolviendo preguntas matemáticas tipo test.

Estás evaluando UNA sola opción.
- El enunciado tiene una figura relevante.
- Las opciones son figuras.
- Recibirás dos imágenes:
  1. Normalmente la figura del enunciado; si ese recorte falló, la imagen completa.
  2. Normalmente la figura de la opción {letra_opcion}; si ese recorte falló, la imagen completa.

Enunciado:
{statement_text}

Plan de resolución:
{plan}

Opción a evaluar:
- Letra: {letra_opcion}
- La segunda imagen corresponde a esta opción o, si es la imagen completa, debes localizar la opción {letra_opcion}.

Tu tarea:
Determina si la figura de esta opción es compatible con la figura del enunciado y con lo pedido.

Instrucciones:
- Usa el texto del enunciado, la figura del enunciado, la figura de la opción y el plan.
- Si alguna imagen es la imagen completa, localiza solo la zona necesaria para este análisis.
- Razona paso a paso.
- Evalúa solo esta opción.
- No compares con otras opciones.
- No elijas respuesta final global.
- Comprueba visualmente relaciones entre ambas figuras: forma, orientación, perspectiva, correspondencias, posiciones, cantidades, áreas, simetrías o transformaciones.
- Si alguna imagen no permite decidir, marca uncertain.
- Justifica claramente qué observaciones te llevan a esa conclusión.

Devuelve únicamente un JSON válido:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Razonamiento breve pero suficiente.",
  "statement_visual_observations": [
    "Observación breve y relevante de la figura del enunciado."
  ],
  "option_visual_observations": [
    "Observación breve y relevante de la figura de la opción."
  ],
  "checks": [
    "Criterio comprobado en esta opción."
  ]
}}

Respuesta:
""".strip()
```
