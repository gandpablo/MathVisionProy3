import json

from decision_final import compactar_razonamientos
from idiomas import descripcion_options, descripcion_statement, normalizar_idioma
from limpieza_modelos import (
    normalizar_opcion,
    parsear_json_modelo,
    texto_corto_raw,
)
from pipeline_funcion import llamar_modelo_visual


def respuesta_previa_a_opcion(decision_final):
    if isinstance(decision_final, dict):
        return normalizar_opcion(
            decision_final.get("final_answer")
            or decision_final.get("answer")
        )

    return normalizar_opcion(decision_final)


def crear_prompt_juez_visual(
    resultado_qwen,
    razonamientos_opciones,
    decision_final,
    idioma="castellano",
):
    idioma = normalizar_idioma(idioma)
    statement_type = resultado_qwen.get("statement_type")
    options_type = resultado_qwen.get("options_type")
    statement_text = resultado_qwen.get("statement_text")
    options_text = resultado_qwen.get("options_text", {})

    desc_statement = descripcion_statement(statement_type, idioma)
    desc_options = descripcion_options(options_type, idioma)

    if options_type == "B.1":
        opciones = json.dumps(options_text, ensure_ascii=False, indent=2)
    elif idioma == "valenciano":
        opciones = "Les opcions A, B, C, D i E són figures."
    elif idioma == "ingles":
        opciones = "Options A, B, C, D, and E are figures."
    elif idioma == "frances":
        opciones = "Les options A, B, C, D et E sont des figures."
    else:
        opciones = "Las opciones A, B, C, D y E son figuras."

    razonamientos_compactos = compactar_razonamientos(razonamientos_opciones)
    razonamientos_json = json.dumps(razonamientos_compactos, ensure_ascii=False, indent=2)
    decision_json = json.dumps(decision_final, ensure_ascii=False, indent=2)

    if idioma == "valenciano":
        return f"""
Ets un model jutge expert en raonament matemàtic visual.

La teua tasca és revisar críticament una solució proposada per a una pregunta matemàtica tipus test.

Rebràs:
- La imatge ORIGINAL COMPLETA de la pregunta.
- L'enunciat extret.
- Les opcions.
- Els raonaments individuals per opció.
- La decisió final generada prèviament.

Has d'actuar com a verificador final visual i lògic.

Classificació:
- Enunciat: {statement_type} = {desc_statement}
- Opcions: {options_type} = {desc_options}

Enunciat:
{statement_text}

Opcions:
{opciones}

Raonaments individuals:
{razonamientos_json}

Decisió final prèvia:
{decision_json}

La teua tasca:
- Revisa directament la imatge completa.
- Comprova si la resposta final proposada és consistent amb la imatge i l'enunciat.
- Detecta possibles errors d'interpretació visual.
- Detecta possibles errors geomètrics, numèrics o lògics.
- Detecta possibles errors causats per retalls incorrectes o raonaments febles.
- Raona pas a pas.
- Si la resposta prèvia és incorrecta, corregeix-la.
- Has d'escollir exactament una opció entre A, B, C, D i E.
- No inventes informació que no estiga present en la imatge o en l'enunciat.

Presta especial atenció a:
- orientació espacial,
- recomptes,
- proporcions,
- àrees,
- perspectiva,
- figures semblants,
- simetries,
- nombres menuts en figures,
- detalls visuals fàcils de confondre.

Retorna únicament un JSON vàlid:

{{
  "final_answer": "A|B|C|D|E",
  "final_reasoning": "Raonament final complet i corregit."
}}

Resposta:
""".strip()

    if idioma == "ingles":
        return f"""
You are an expert judge model for visual mathematical reasoning.

Your task is to critically review a proposed solution for a multiple-choice math question.

You will receive:
- The COMPLETE ORIGINAL image of the question.
- The extracted statement.
- The options.
- The individual reasonings by option.
- The previously generated final decision.

You must act as the final visual and logical verifier.

Classification:
- Statement: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Statement:
{statement_text}

Options:
{opciones}

Individual reasonings:
{razonamientos_json}

Previous final decision:
{decision_json}

Your task:
- Review the full image directly.
- Check whether the proposed final answer is consistent with the image and the statement.
- Detect possible visual interpretation errors.
- Detect possible geometric, numeric, or logical errors.
- Detect possible errors caused by incorrect crops or weak reasoning.
- Reason step by step.
- If the previous answer is incorrect, correct it.
- You must choose exactly one option among A, B, C, D, and E.
- Do not invent information that is not present in the image or in the statement.

Pay special attention to:
- spatial orientation,
- counts,
- proportions,
- areas,
- perspective,
- similar figures,
- symmetries,
- small numbers in figures,
- visual details that are easy to confuse.

Return only a valid JSON object:

{{
  "final_answer": "A|B|C|D|E",
  "final_reasoning": "Complete and corrected final reasoning."
}}

Answer:
""".strip()

    if idioma == "frances":
        return f"""
Tu es un modèle juge expert en raisonnement mathématique visuel.

Ta tâche est d'examiner de manière critique une solution proposée pour une question mathématique à choix multiple.

Tu recevras:
- L'image ORIGINALE COMPLÈTE de la question.
- L'énoncé extrait.
- Les options.
- Les raisonnements individuels par option.
- La décision finale générée précédemment.

Tu dois agir comme vérificateur final visuel et logique.

Classification:
- Énoncé: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Énoncé:
{statement_text}

Options:
{opciones}

Raisonnements individuels:
{razonamientos_json}

Décision finale précédente:
{decision_json}

Ta tâche:
- Examine directement l'image complète.
- Vérifie si la réponse finale proposée est cohérente avec l'image et l'énoncé.
- Détecte les erreurs possibles d'interprétation visuelle.
- Détecte les erreurs géométriques, numériques ou logiques possibles.
- Détecte les erreurs possibles causées par des recadrages incorrects ou des raisonnements faibles.
- Raisonne étape par étape.
- Si la réponse précédente est incorrecte, corrige-la.
- Tu dois choisir exactement une option parmi A, B, C, D et E.
- N'invente pas d'informations qui ne sont pas présentes dans l'image ou dans l'énoncé.

Fais particulièrement attention à:
- l'orientation spatiale,
- les comptages,
- les proportions,
- les aires,
- la perspective,
- les figures similaires,
- les symétries,
- les petits nombres dans les figures,
- les détails visuels faciles à confondre.

Renvoie uniquement un objet JSON valide:

{{
  "final_answer": "A|B|C|D|E",
  "final_reasoning": "Raisonnement final complet et corrigé."
}}

Réponse:
""".strip()

    return f"""
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


def limpiar_respuesta_juez(respuesta_modelo, decision_final=None, error=None):
    data = parsear_json_modelo(respuesta_modelo)
    fallback = respuesta_previa_a_opcion(decision_final) or "A"

    if not isinstance(data, dict):
        razonamiento = "No se pudo parsear la respuesta del juez visual."
        if error:
            razonamiento = "No se pudo llamar al modelo visual juez."

        return {
            "final_answer": fallback,
            "final_reasoning": razonamiento,
            "parse_ok": False,
            "raw_response": texto_corto_raw(respuesta_modelo),
            "error": error,
        }

    final_answer = normalizar_opcion(
        data.get("final_answer")
        or data.get("answer")
    )
    final_reasoning = str(
        data.get("final_reasoning")
        or data.get("reasoning")
        or ""
    ).strip()

    return {
        "final_answer": final_answer or fallback,
        "final_reasoning": final_reasoning
        or "El juez no devolvió razonamiento parseable.",
        "parse_ok": final_answer is not None and bool(final_reasoning),
        "raw_response": texto_corto_raw(respuesta_modelo),
        "error": error,
    }


def juzgar_respuesta_final(
    resultado_qwen,
    razonamientos_opciones,
    decision_final,
    imagen_base,
    idioma="castellano",
):
    prompt = crear_prompt_juez_visual(
        resultado_qwen=resultado_qwen,
        razonamientos_opciones=razonamientos_opciones,
        decision_final=decision_final,
        idioma=idioma,
    )

    try:
        respuesta_texto = llamar_modelo_visual(
            imagen_base=imagen_base,
            prompt=prompt,
        )
        error = None
    except Exception as exc:
        respuesta_texto = ""
        error = str(exc)

    respuesta_juez = limpiar_respuesta_juez(
        respuesta_modelo=respuesta_texto,
        decision_final=decision_final,
        error=error,
    )

    return {
        "prompt": prompt,
        "respuesta_juez": respuesta_juez,
        "respuesta_texto": respuesta_texto,
        "error": error,
    }


generar_respuesta_juez = juzgar_respuesta_final
