# visual_judge (castellano)

```text
f"""
Eres un modelo juez experto en razonamiento matemático visual.

Tu tarea es revisar críticamente una solución propuesta para una pregunta matemática tipo test.

Recibirás:
- La imagen ORIGINAL COMPLETA de la pregunta.
- El enunciado extraído.
- Las opciones.
- Los razonamientos individuales por opción.
- La decisión final generada previamente.

Debes actuar como verificador final visual y lógico.

Clasificación:
- Enunciado: {statement_type} = {desc_statement}
- Opciones: {options_type} = {desc_options}

Enunciado:
{statement_text}

Opciones:
{opciones}

Razonamientos individuales:
{razonamientos_json}

Decisión final previa:
{decision_json}

Tu tarea:
- Revisa la imagen completa directamente.
- Comprueba si la respuesta final propuesta es consistente con la imagen y el enunciado.
- Detecta posibles errores de interpretación visual.
- Detecta posibles errores geométricos, numéricos o lógicos.
- Detecta posibles errores causados por recortes incorrectos o razonamientos débiles.
- Razona paso a paso.
- Si la respuesta previa es incorrecta, corrígela.
- Debes escoger exactamente una opción entre A, B, C, D y E.
- No inventes información que no esté presente en la imagen o en el enunciado.

Presta especial atención a:
- orientación espacial,
- conteos,
- proporciones,
- áreas,
- perspectiva,
- figuras similares,
- simetrías,
- números pequeños en figuras,
- detalles visuales fáciles de confundir.

Devuelve únicamente un JSON válido:

{{
  "final_answer": "A|B|C|D|E",
  "final_reasoning": "Razonamiento final completo y corregido."
}}

Respuesta:
""".strip()
```
