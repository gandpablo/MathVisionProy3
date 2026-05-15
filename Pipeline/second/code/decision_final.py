import json

from idiomas import descripcion_options, descripcion_statement, normalizar_idioma
from limpieza_modelos import normalizar_opcion, parsear_json_modelo, texto_corto_raw
from pipeline_funcion import llamar_modelo_texto
from ollama import generate

def inferir_respuesta_desde_razonamientos(razonamientos_opciones):
    if not isinstance(razonamientos_opciones, list):
        return "A"

    for item in razonamientos_opciones:
        if not isinstance(item, dict):
            continue

        respuesta = item.get("respuesta_modelo", item)
        if not isinstance(respuesta, dict):
            continue

        status = str(respuesta.get("status") or "").strip().lower()
        opcion = normalizar_opcion(
            respuesta.get("option")
            or item.get("opcion")
            or item.get("option")
        )

        if status == "correct" and opcion:
            return opcion

    for item in razonamientos_opciones:
        if isinstance(item, dict):
            opcion = normalizar_opcion(item.get("opcion") or item.get("option"))
            if opcion:
                return opcion

    return "A"


def compactar_razonamientos(razonamientos_opciones):
    if not isinstance(razonamientos_opciones, list):
        return []

    compactos = []

    for item in razonamientos_opciones:
        if not isinstance(item, dict):
            continue

        respuesta = item.get("respuesta_modelo", item)
        if isinstance(respuesta, dict):
            respuesta = dict(respuesta)
            respuesta.pop("raw_response", None)

        compactos.append({
            "opcion": item.get("opcion") or item.get("option"),
            "respuesta_modelo": respuesta,
            "imagenes_usadas": item.get("imagenes_usadas", {}),
            "error": item.get("error"),
        })

    return compactos


def crear_prompt_decision_final(resultado_qwen, razonamientos_opciones, idioma="castellano"):
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
        opciones = "Les opcions A, B, C, D i E són figures. No hi ha text d'opcions."
    elif idioma == "ingles":
        opciones = "Options A, B, C, D, and E are figures. There is no option text."
    elif idioma == "frances":
        opciones = "Les options A, B, C, D et E sont des figures. Il n'y a pas de texte d'options."
    else:
        opciones = "Las opciones A, B, C, D y E son figuras. No hay texto de opciones."

    razonamientos_compactos = compactar_razonamientos(razonamientos_opciones)
    razonamientos_json = json.dumps(razonamientos_compactos, ensure_ascii=False, indent=2)

    if idioma == "valenciano":
        return f"""
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

    if idioma == "ingles":
        return f"""
You are an expert at solving multiple-choice math questions.

Each option has already been evaluated separately with a visual model.
Now you must make a final decision using the individual reasonings.

Classification:
- Statement: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Statement:
{statement_text}

Options:
{opciones}

Individual reasoning by option:
{razonamientos_json}

Your task:
- Analyze the reasoning for all options step by step.
- Decide which of the five options A, B, C, D, or E is the correct answer.
- Give a general reasoning that justifies why that option is correct.
- Also use the individual reasonings to rule out the other options.
- If there are contradictions between reasonings, prioritize the reasoning most consistent with the statement.
- If an option appears as uncertain, do not discard it automatically: assess whether it may still be the best choice.
- Do not invent visual information that does not appear in the reasonings.
- You must choose exactly one option among A, B, C, D, and E.

Return only a valid JSON object with this structure:

{{
  "answer": "A|B|C|D|E",
  "reasoning": "General step-by-step reasoning, explaining why the chosen option is correct and why the others are not."
}}

Answer:
""".strip()

    if idioma == "frances":
        return f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.

Chaque option a déjà été évaluée séparément avec un modèle visuel.
Tu dois maintenant prendre une décision finale en utilisant les raisonnements individuels.

Classification:
- Énoncé: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Énoncé:
{statement_text}

Options:
{opciones}

Raisonnements individuels par option:
{razonamientos_json}

Ta tâche:
- Analyse étape par étape les raisonnements de toutes les options.
- Décide laquelle des cinq options A, B, C, D ou E est la bonne réponse.
- Donne un raisonnement général qui justifie pourquoi cette option est correcte.
- Utilise aussi les raisonnements individuels pour écarter les autres options.
- S'il y a des contradictions entre les raisonnements, privilégie le raisonnement le plus cohérent avec l'énoncé.
- Si une option apparaît comme uncertain, ne l'écarte pas automatiquement: évalue si elle peut tout de même être la meilleure.
- N'invente pas d'informations visuelles qui n'apparaissent pas dans les raisonnements.
- Tu dois choisir exactement une option parmi A, B, C, D et E.

Renvoie uniquement un objet JSON valide avec cette structure:

{{
  "answer": "A|B|C|D|E",
  "reasoning": "Raisonnement général étape par étape, expliquant pourquoi l'option choisie est correcte et pourquoi les autres ne le sont pas."
}}

Réponse:
""".strip()

    return f"""
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


def limpiar_decision_final(respuesta_modelo, razonamientos_opciones=None, error=None):
    data = parsear_json_modelo(respuesta_modelo)
    inferida = inferir_respuesta_desde_razonamientos(razonamientos_opciones)

    if not isinstance(data, dict):
        razonamiento = "No se pudo parsear la decisión final del modelo."
        if error:
            razonamiento = "No se pudo llamar al modelo textual para la decisión final."

        return {
            "answer": inferida,
            "reasoning": razonamiento,
            "parse_ok": False,
            "raw_response": texto_corto_raw(respuesta_modelo),
            "error": error,
        }

    answer = normalizar_opcion(data.get("answer") or data.get("final_answer"))
    reasoning = str(data.get("reasoning") or data.get("final_reasoning") or "").strip()

    return {
        "answer": answer or inferida,
        "reasoning": reasoning or "El modelo no devolvió razonamiento parseable.",
        "parse_ok": answer is not None and bool(reasoning),
        "raw_response": texto_corto_raw(respuesta_modelo),
        "error": error,
    }


def decidir_respuesta_final(resultado_qwen, razonamientos_opciones, idioma="castellano"):
    prompt = crear_prompt_decision_final(
        resultado_qwen,
        razonamientos_opciones,
        idioma=idioma,
    )

    try:
        respuesta_texto = llamar_modelo_texto(prompt)
        error = None
    except Exception as exc:
        respuesta_texto = ""
        error = str(exc)

    decision_final = limpiar_decision_final(
        respuesta_modelo=respuesta_texto,
        razonamientos_opciones=razonamientos_opciones,
        error=error,
    )

    return {
        "prompt": prompt,
        "decision_final": decision_final,
        "respuesta_texto": respuesta_texto,
        "error": error,
    }


generar_decision_final = decidir_respuesta_final
