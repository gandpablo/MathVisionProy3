import base64
import json
from io import BytesIO

from ollama import chat

from limpieza_modelos import (
    asegurar_lista_texto,
    json_legible,
    normalizar_opcion,
    normalizar_status,
    parsear_json_modelo,
    texto_corto_raw,
)
from idiomas import normalizar_idioma
from pipeline_funcion import OPCIONES, VISION_MODEL, descargar_modelos_ollama_excepto


def pil_a_base64(img_pil):
    if img_pil is None:
        return None

    buffer = BytesIO()
    img_pil.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def llamar_modelo_visual_multi(imagenes_base64, prompt, model=VISION_MODEL):
    imagenes = [imagen for imagen in imagenes_base64 if imagen]

    if not imagenes:
        raise ValueError("No hay imágenes válidas para llamar al modelo visual.")

    descargar_modelos_ollama_excepto(model)
    respuesta = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": imagenes,
            }
        ],
        options={"temperature": 0, "seed": 0},
    )

    return respuesta["message"]["content"].strip()


def formatear_plan(plan_resolucion):
    if isinstance(plan_resolucion, (dict, list)):
        return json_legible(plan_resolucion)

    return "" if plan_resolucion is None else str(plan_resolucion)


def normalizar_lista_a_probar(lista_a_probar):
    if not lista_a_probar:
        return []

    salida = []

    for item in lista_a_probar:
        texto = str(item).strip()

        if texto.lower() == "enunciado" and "enunciado" not in salida:
            salida.append("enunciado")
            continue

        letra = normalizar_opcion(texto)
        if letra and letra not in salida:
            salida.append(letra)

    return salida


def seleccionar_imagen_base64(etiqueta, recortes, lista_a_probar, imagen_base):
    lista = normalizar_lista_a_probar(lista_a_probar)
    recortes = recortes if isinstance(recortes, dict) else {}
    usar_completa = etiqueta in lista or recortes.get(etiqueta) is None

    if usar_completa:
        return imagen_base, "imagen_completa"

    imagen_recorte = pil_a_base64(recortes.get(etiqueta))

    if imagen_recorte is None:
        return imagen_base, "imagen_completa"

    if etiqueta == "enunciado":
        return imagen_recorte, "recorte_enunciado"

    return imagen_recorte, f"recorte_{etiqueta}"


def crear_prompt_verificar_opcion_A2_B1(
    resultado_qwen,
    plan_resolucion,
    letra_opcion,
    idioma="castellano",
):
    idioma = normalizar_idioma(idioma)
    statement_text = resultado_qwen.get("statement_text")
    options_text = resultado_qwen.get("options_text", {})
    option_text = options_text.get(letra_opcion)
    plan = formatear_plan(plan_resolucion)

    if idioma == "valenciano":
        return f"""
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

    if idioma == "ingles":
        return f"""
You are an expert at solving multiple-choice math questions.

You are evaluating ONE option only.
- The statement has a relevant figure.
- The options are text, a number, or an expression.
- You will receive one image: normally the statement figure; if the crop failed, you will receive the full question image.
- The current option is textual.

Statement:
{statement_text}

Resolution plan:
{plan}

Option to evaluate:
- Letter: {letra_opcion}
- Value: {option_text}

Your task:
Determine whether this individual option can be the correct answer.

Instructions:
- Use the statement, the statement figure, and the plan.
- If you receive the full image, visually locate the relevant statement figure and do not rely on other options.
- Reason step by step.
- Explicitly check the value proposed by the option.
- Do not compare with other options.
- Do not choose a global final answer.
- If the figure does not allow a safe check, mark uncertain.
- Clearly justify which observations lead you to that conclusion.

Return only a valid JSON object:

{{
  "option": "{letra_opcion}",
  "option_value": {json.dumps(option_text, ensure_ascii=False)},
  "status": "correct|incorrect|uncertain",
  "reasoning": "Brief but sufficient reasoning.",
  "visual_observations": [
    "Brief and relevant observation extracted from the statement figure."
  ],
  "checks": [
    "Criterion checked for this option."
  ]
}}

Answer:
""".strip()

    if idioma == "frances":
        return f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.

Tu évalues UNE seule option.
- L'énoncé contient une figure pertinente.
- Les options sont du texte, un nombre ou une expression.
- Tu recevras une image: normalement la figure de l'énoncé; si le recadrage a échoué, tu recevras l'image complète de la question.
- L'option actuelle est textuelle.

Énoncé:
{statement_text}

Plan de résolution:
{plan}

Option à évaluer:
- Lettre: {letra_opcion}
- Valeur: {option_text}

Ta tâche:
Détermine si cette option individuelle peut être la bonne réponse.

Instructions:
- Utilise l'énoncé, la figure de l'énoncé et le plan.
- Si tu reçois l'image complète, localise visuellement la figure pertinente de l'énoncé et ne t'appuie pas sur les autres options.
- Raisonne étape par étape.
- Vérifie explicitement la valeur proposée par l'option.
- Ne compare pas avec les autres options.
- Ne choisis pas de réponse finale globale.
- Si la figure ne permet pas de vérifier avec certitude, marque uncertain.
- Justifie clairement quelles observations te conduisent à cette conclusion.

Renvoie uniquement un objet JSON valide:

{{
  "option": "{letra_opcion}",
  "option_value": {json.dumps(option_text, ensure_ascii=False)},
  "status": "correct|incorrect|uncertain",
  "reasoning": "Raisonnement bref mais suffisant.",
  "visual_observations": [
    "Observation brève et pertinente extraite de la figure de l'énoncé."
  ],
  "checks": [
    "Critère vérifié pour cette option."
  ]
}}

Réponse:
""".strip()

    return f"""
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


def crear_prompt_verificar_opcion_A1_B2(
    resultado_qwen,
    plan_resolucion,
    letra_opcion,
    idioma="castellano",
):
    idioma = normalizar_idioma(idioma)
    statement_text = resultado_qwen.get("statement_text")
    plan = formatear_plan(plan_resolucion)

    if idioma == "valenciano":
        return f"""
Ets un expert resolent preguntes matemàtiques tipus test.

Estàs avaluant UNA sola opció.
- L'enunciat és només text.
- Les opcions són figures.
- Rebràs una imatge: normalment la figura de l'opció {letra_opcion}; si el retall ha fallat, rebràs la imatge completa de la pregunta.

Enunciat:
{statement_text}

Pla de resolució:
{plan}

Opció a avaluar:
- Lletra: {letra_opcion}
- La imatge rebuda correspon a aquesta opció o, si és la imatge completa, has de localitzar l'opció {letra_opcion}.

La teua tasca:
Determina si la figura d'aquesta opció compleix l'enunciat.

Instruccions:
- Usa l'enunciat, la imatge de l'opció i el pla.
- Si reps la imatge completa, analitza només l'opció {letra_opcion}.
- Raona pas a pas.
- Avalua només aquesta opció.
- No compares amb altres opcions.
- No tries resposta final global.
- Comprova visualment forma, quantitats, orientació, posicions, simetries, mesures o relacions necessàries.
- Si el retall o la imatge completa no permeten decidir, marca uncertain.
- Justifica clarament quines observacions et porten a aquesta conclusió.

Retorna únicament un JSON vàlid:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Raonament breu però suficient.",
  "visual_observations": [
    "Observació breu i rellevant extreta de la figura de l'opció."
  ],
  "checks": [
    "Criteri comprovat en aquesta opció."
  ]
}}

Resposta:
""".strip()

    if idioma == "ingles":
        return f"""
You are an expert at solving multiple-choice math questions.

You are evaluating ONE option only.
- The statement is text only.
- The options are figures.
- You will receive one image: normally the figure of option {letra_opcion}; if the crop failed, you will receive the full question image.

Statement:
{statement_text}

Resolution plan:
{plan}

Option to evaluate:
- Letter: {letra_opcion}
- The received image corresponds to this option, or if it is the full image, you must locate option {letra_opcion}.

Your task:
Determine whether the figure in this option satisfies the statement.

Instructions:
- Use the statement, the option image, and the plan.
- If you receive the full image, analyze only option {letra_opcion}.
- Reason step by step.
- Evaluate only this option.
- Do not compare with other options.
- Do not choose a global final answer.
- Visually check the necessary shape, quantities, orientation, positions, symmetries, measurements, or relationships.
- If the crop or full image does not allow a decision, mark uncertain.
- Clearly justify which observations lead you to that conclusion.

Return only a valid JSON object:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Brief but sufficient reasoning.",
  "visual_observations": [
    "Brief and relevant observation extracted from the option figure."
  ],
  "checks": [
    "Criterion checked for this option."
  ]
}}

Answer:
""".strip()

    if idioma == "frances":
        return f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.

Tu évalues UNE seule option.
- L'énoncé est uniquement textuel.
- Les options sont des figures.
- Tu recevras une image: normalement la figure de l'option {letra_opcion}; si le recadrage a échoué, tu recevras l'image complète de la question.

Énoncé:
{statement_text}

Plan de résolution:
{plan}

Option à évaluer:
- Lettre: {letra_opcion}
- L'image reçue correspond à cette option ou, si c'est l'image complète, tu dois localiser l'option {letra_opcion}.

Ta tâche:
Détermine si la figure de cette option satisfait l'énoncé.

Instructions:
- Utilise l'énoncé, l'image de l'option et le plan.
- Si tu reçois l'image complète, analyse uniquement l'option {letra_opcion}.
- Raisonne étape par étape.
- Évalue uniquement cette option.
- Ne compare pas avec les autres options.
- Ne choisis pas de réponse finale globale.
- Vérifie visuellement la forme, les quantités, l'orientation, les positions, les symétries, les mesures ou les relations nécessaires.
- Si le recadrage ou l'image complète ne permet pas de décider, marque uncertain.
- Justifie clairement quelles observations te conduisent à cette conclusion.

Renvoie uniquement un objet JSON valide:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Raisonnement bref mais suffisant.",
  "visual_observations": [
    "Observation brève et pertinente extraite de la figure de l'option."
  ],
  "checks": [
    "Critère vérifié pour cette option."
  ]
}}

Réponse:
""".strip()

    return f"""
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


def crear_prompt_verificar_opcion_A2_B2(
    resultado_qwen,
    plan_resolucion,
    letra_opcion,
    idioma="castellano",
):
    idioma = normalizar_idioma(idioma)
    statement_text = resultado_qwen.get("statement_text")
    plan = formatear_plan(plan_resolucion)

    if idioma == "valenciano":
        return f"""
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

    if idioma == "ingles":
        return f"""
You are an expert at solving multiple-choice math questions.

You are evaluating ONE option only.
- The statement has a relevant figure.
- The options are figures.
- You will receive two images:
  1. Normally the statement figure; if that crop failed, the full image.
  2. Normally the figure of option {letra_opcion}; if that crop failed, the full image.

Statement:
{statement_text}

Resolution plan:
{plan}

Option to evaluate:
- Letter: {letra_opcion}
- The second image corresponds to this option, or if it is the full image, you must locate option {letra_opcion}.

Your task:
Determine whether the figure in this option is compatible with the statement figure and with what is being asked.

Instructions:
- Use the statement text, the statement figure, the option figure, and the plan.
- If any image is the full image, locate only the area needed for this analysis.
- Reason step by step.
- Evaluate only this option.
- Do not compare with other options.
- Do not choose a global final answer.
- Visually check relationships between both figures: shape, orientation, perspective, correspondences, positions, quantities, areas, symmetries, or transformations.
- If any image does not allow a decision, mark uncertain.
- Clearly justify which observations lead you to that conclusion.

Return only a valid JSON object:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Brief but sufficient reasoning.",
  "statement_visual_observations": [
    "Brief and relevant observation from the statement figure."
  ],
  "option_visual_observations": [
    "Brief and relevant observation from the option figure."
  ],
  "checks": [
    "Criterion checked for this option."
  ]
}}

Answer:
""".strip()

    if idioma == "frances":
        return f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.

Tu évalues UNE seule option.
- L'énoncé contient une figure pertinente.
- Les options sont des figures.
- Tu recevras deux images:
  1. Normalement la figure de l'énoncé; si ce recadrage a échoué, l'image complète.
  2. Normalement la figure de l'option {letra_opcion}; si ce recadrage a échoué, l'image complète.

Énoncé:
{statement_text}

Plan de résolution:
{plan}

Option à évaluer:
- Lettre: {letra_opcion}
- La seconde image correspond à cette option ou, si c'est l'image complète, tu dois localiser l'option {letra_opcion}.

Ta tâche:
Détermine si la figure de cette option est compatible avec la figure de l'énoncé et avec ce qui est demandé.

Instructions:
- Utilise le texte de l'énoncé, la figure de l'énoncé, la figure de l'option et le plan.
- Si une image est l'image complète, localise seulement la zone nécessaire pour cette analyse.
- Raisonne étape par étape.
- Évalue uniquement cette option.
- Ne compare pas avec les autres options.
- Ne choisis pas de réponse finale globale.
- Vérifie visuellement les relations entre les deux figures: forme, orientation, perspective, correspondances, positions, quantités, aires, symétries ou transformations.
- Si une image ne permet pas de décider, marque uncertain.
- Justifie clairement quelles observations te conduisent à cette conclusion.

Renvoie uniquement un objet JSON valide:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Raisonnement bref mais suffisant.",
  "statement_visual_observations": [
    "Observation brève et pertinente de la figure de l'énoncé."
  ],
  "option_visual_observations": [
    "Observation brève et pertinente de la figure de l'option."
  ],
  "checks": [
    "Critère vérifié pour cette option."
  ]
}}

Réponse:
""".strip()

    return f"""
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


def limpiar_razonamiento_opcion(respuesta_modelo, letra_opcion, caso, error=None):
    data = parsear_json_modelo(respuesta_modelo)

    if not isinstance(data, dict):
        razonamiento = "No se pudo parsear la respuesta del modelo para esta opción."
        if error:
            razonamiento = "No se pudo llamar al modelo visual para esta opción."

        return {
            "option": letra_opcion,
            "status": "uncertain",
            "reasoning": razonamiento,
            "visual_observations": [],
            "statement_visual_observations": [],
            "option_visual_observations": [],
            "checks": [],
            "parse_ok": False,
            "raw_response": texto_corto_raw(respuesta_modelo),
            "error": error,
        }

    option = normalizar_opcion(data.get("option")) or letra_opcion
    salida = {
        "option": option,
        "status": normalizar_status(data.get("status")),
        "reasoning": str(data.get("reasoning") or "").strip(),
        "checks": asegurar_lista_texto(data.get("checks")),
        "parse_ok": True,
        "raw_response": texto_corto_raw(respuesta_modelo),
    }

    if "option_value" in data:
        salida["option_value"] = data.get("option_value")

    if caso == "A2_B2":
        salida["statement_visual_observations"] = asegurar_lista_texto(
            data.get("statement_visual_observations")
        )
        salida["option_visual_observations"] = asegurar_lista_texto(
            data.get("option_visual_observations")
        )
        salida["visual_observations"] = (
            salida["statement_visual_observations"]
            + salida["option_visual_observations"]
        )
    else:
        salida["visual_observations"] = asegurar_lista_texto(
            data.get("visual_observations")
        )
        salida["statement_visual_observations"] = asegurar_lista_texto(
            data.get("statement_visual_observations")
        )
        salida["option_visual_observations"] = asegurar_lista_texto(
            data.get("option_visual_observations")
        )

    if not salida["reasoning"]:
        salida["reasoning"] = "El modelo no devolvió razonamiento parseable."
        salida["parse_ok"] = False

    if error:
        salida["error"] = error
        salida["parse_ok"] = False

    return salida


def construir_resultado_opcion(
    letra_opcion,
    caso,
    prompt,
    imagenes_base64,
    imagenes_usadas,
    model=VISION_MODEL,
):
    try:
        respuesta_texto = llamar_modelo_visual_multi(
            imagenes_base64=imagenes_base64,
            prompt=prompt,
            model=model,
        )
        error = None
    except Exception as exc:
        respuesta_texto = ""
        error = str(exc)

    respuesta_modelo = limpiar_razonamiento_opcion(
        respuesta_modelo=respuesta_texto,
        letra_opcion=letra_opcion,
        caso=caso,
        error=error,
    )

    return {
        "opcion": letra_opcion,
        "respuesta_modelo": respuesta_modelo,
        "respuesta_texto": respuesta_texto,
        "imagenes_usadas": imagenes_usadas,
        "prompt": prompt,
        "error": error,
    }


def probar_opcion_A2_B1(
    resultado_qwen,
    recortes,
    lista_a_probar,
    imagen_base,
    plan_resolucion,
    letra_opcion,
    model=VISION_MODEL,
    idioma="castellano",
):
    prompt = crear_prompt_verificar_opcion_A2_B1(
        resultado_qwen=resultado_qwen,
        plan_resolucion=plan_resolucion,
        letra_opcion=letra_opcion,
        idioma=idioma,
    )
    img_enunciado_base, origen_enunciado = seleccionar_imagen_base64(
        "enunciado",
        recortes,
        lista_a_probar,
        imagen_base,
    )

    return construir_resultado_opcion(
        letra_opcion=letra_opcion,
        caso="A2_B1",
        prompt=prompt,
        imagenes_base64=[img_enunciado_base],
        imagenes_usadas={"enunciado": origen_enunciado},
        model=model,
    )


def probar_opcion_A1_B2(
    resultado_qwen,
    recortes,
    lista_a_probar,
    imagen_base,
    plan_resolucion,
    letra_opcion,
    model=VISION_MODEL,
    idioma="castellano",
):
    prompt = crear_prompt_verificar_opcion_A1_B2(
        resultado_qwen=resultado_qwen,
        plan_resolucion=plan_resolucion,
        letra_opcion=letra_opcion,
        idioma=idioma,
    )
    img_opcion_base, origen_opcion = seleccionar_imagen_base64(
        letra_opcion,
        recortes,
        lista_a_probar,
        imagen_base,
    )

    return construir_resultado_opcion(
        letra_opcion=letra_opcion,
        caso="A1_B2",
        prompt=prompt,
        imagenes_base64=[img_opcion_base],
        imagenes_usadas={letra_opcion: origen_opcion},
        model=model,
    )


def probar_opcion_A2_B2(
    resultado_qwen,
    recortes,
    lista_a_probar,
    imagen_base,
    plan_resolucion,
    letra_opcion,
    model=VISION_MODEL,
    idioma="castellano",
):
    prompt = crear_prompt_verificar_opcion_A2_B2(
        resultado_qwen=resultado_qwen,
        plan_resolucion=plan_resolucion,
        letra_opcion=letra_opcion,
        idioma=idioma,
    )
    img_enunciado_base, origen_enunciado = seleccionar_imagen_base64(
        "enunciado",
        recortes,
        lista_a_probar,
        imagen_base,
    )
    img_opcion_base, origen_opcion = seleccionar_imagen_base64(
        letra_opcion,
        recortes,
        lista_a_probar,
        imagen_base,
    )

    return construir_resultado_opcion(
        letra_opcion=letra_opcion,
        caso="A2_B2",
        prompt=prompt,
        imagenes_base64=[img_enunciado_base, img_opcion_base],
        imagenes_usadas={
            "enunciado": origen_enunciado,
            letra_opcion: origen_opcion,
        },
        model=model,
    )


def probar_opcion_visual(
    resultado_qwen,
    recortes,
    lista_a_probar,
    imagen_base,
    plan_resolucion,
    letra_opcion,
    model=VISION_MODEL,
    idioma="castellano",
):
    st = resultado_qwen.get("statement_type")
    ot = resultado_qwen.get("options_type")

    if st == "A.2" and ot == "B.1":
        return probar_opcion_A2_B1(
            resultado_qwen,
            recortes,
            lista_a_probar,
            imagen_base,
            plan_resolucion,
            letra_opcion,
            model=model,
            idioma=idioma,
        )

    if st == "A.1" and ot == "B.2":
        return probar_opcion_A1_B2(
            resultado_qwen,
            recortes,
            lista_a_probar,
            imagen_base,
            plan_resolucion,
            letra_opcion,
            model=model,
            idioma=idioma,
        )

    if st == "A.2" and ot == "B.2":
        return probar_opcion_A2_B2(
            resultado_qwen,
            recortes,
            lista_a_probar,
            imagen_base,
            plan_resolucion,
            letra_opcion,
            model=model,
            idioma=idioma,
        )

    return {
        "opcion": letra_opcion,
        "respuesta_modelo": limpiar_razonamiento_opcion(
            respuesta_modelo=None,
            letra_opcion=letra_opcion,
            caso=f"{st}_{ot}",
            error=f"Caso no soportado en paso visual: {st}_{ot}",
        ),
        "respuesta_texto": "",
        "imagenes_usadas": {},
        "prompt": "",
        "error": f"Caso no soportado en paso visual: {st}_{ot}",
    }


def generar_razonamientos_opciones(
    resultado_qwen,
    recortes,
    lista_a_probar,
    imagen_base,
    plan_resolucion,
    model=VISION_MODEL,
    verbose=True,
    incluir_prompts=False,
    idioma="castellano",
):
    razonamientos = []

    for letra in OPCIONES:
        if verbose:
            print(f"\nEvaluando opción {letra}...")

        resultado = probar_opcion_visual(
            resultado_qwen=resultado_qwen,
            recortes=recortes,
            lista_a_probar=lista_a_probar,
            imagen_base=imagen_base,
            plan_resolucion=plan_resolucion,
            letra_opcion=letra,
            model=model,
            idioma=idioma,
        )

        if not incluir_prompts:
            resultado = dict(resultado)
            resultado.pop("prompt", None)

        razonamientos.append(resultado)

    return razonamientos
