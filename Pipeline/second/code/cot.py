import json

from limpieza_modelos import (
    asegurar_lista_texto,
    json_legible,
    normalizar_opcion,
    parsear_json_modelo,
    texto_corto_raw,
)
from idiomas import descripcion_options, descripcion_statement, normalizar_idioma
from pipeline_funcion import llamar_modelo_texto, llamar_modelo_visual


def es_caso_textual_directo(resultado_qwen):
    return (
        isinstance(resultado_qwen, dict)
        and resultado_qwen.get("statement_type") == "A.1"
        and resultado_qwen.get("options_type") == "B.1"
    )


def crear_prompt_plan_resolucion(resultado_qwen, idioma="castellano"):
    idioma = normalizar_idioma(idioma)
    statement_type = resultado_qwen.get("statement_type")
    options_type = resultado_qwen.get("options_type")
    statement_text = resultado_qwen.get("statement_text")
    options_text = resultado_qwen.get("options_text", {})

    desc_statement = descripcion_statement(statement_type, idioma)
    desc_options = descripcion_options(options_type, idioma)
    opciones_json = json.dumps(options_text, ensure_ascii=False, indent=2)

    if idioma == "valenciano":
        return f"""
Ets un planificador expert per a resoldre preguntes matemàtiques tipus test.

Estàs en el pas 3 d'un pipeline. Ja s'ha fet:
1. Classificació global de la pregunta.
2. OCR i retall de figures de l'enunciat i/o de les opcions.

Ara reps de nou la imatge completa, juntament amb aquesta informació:

Classificació:
- Enunciat: {statement_type} = {desc_statement}
- Opcions: {options_type} = {desc_options}

Enunciat:
{statement_text}

Opcions:
{opciones_json}

La teua tasca NO és resoldre el problema ni triar resposta.
La teua tasca és crear un pla de resolució perquè després es puga analitzar cada opció per separat.

El pla ha d'indicar:
- quines regles, propietats, càlculs o criteris cal usar;
- què s'ha d'observar en la figura de l'enunciat, si existeix;
- què s'ha de comprovar en una opció individual;
- com justificar si una opció és correcta, incorrecta o uncertain.

Retorna únicament un JSON vàlid:

{{
  "problem_summary": "Resum breu del problema sense resoldre'l.",
  "axioms_or_rules": [
    "Regla, propietat, càlcul o criteri que cal usar."
  ],
  "statement_analysis_plan": [
    "Quina informació cal extraure de l'enunciat i de la seua figura, si existeix."
  ],
  "option_verification_plan": [
    "Pas 1 per a comprovar una opció individual.",
    "Pas 2 per a verificar si compleix l'enunciat.",
    "Pas 3 per a decidir correct, incorrect o uncertain."
  ],
  "visual_requirements": {{
    "needs_statement_image": true,
    "needs_option_image": true,
    "inspect_in_statement": ["..."],
    "inspect_in_each_option": ["..."]
  }},
  "warnings": [
    "Errors a evitar en avaluar opcions aïllades."
  ]
}}

Restriccions:
- No digues quina és la resposta.
- No compares opcions entre si.
- No resolgues completament l'exercici.
- El pla ha de servir per a avaluar una sola opció cada vegada.
- Si les opcions són figures, explica com verificar visualment cada figura.
- Si les opcions són text o nombres, explica com comprovar el valor proposat.
- Sigues concret i breu.

Resposta:
""".strip()

    if idioma == "ingles":
        return f"""
You are an expert planner for solving multiple-choice math questions.

You are in step 3 of a pipeline. The following has already been done:
1. Global classification of the question.
2. OCR and cropping of figures from the statement and/or the options.

You now receive the full image again, together with this information:

Classification:
- Statement: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Statement:
{statement_text}

Options:
{opciones_json}

Your task is NOT to solve the problem or choose an answer.
Your task is to create a resolution plan so that each option can later be analyzed separately.

The plan must indicate:
- which rules, properties, calculations, or criteria to use;
- what must be observed in the statement figure, if it exists;
- what must be checked in an individual option;
- how to justify whether an option is correct, incorrect, or uncertain.

Return only a valid JSON object:

{{
  "problem_summary": "Brief summary of the problem without solving it.",
  "axioms_or_rules": [
    "Rule, property, calculation, or criterion that must be used."
  ],
  "statement_analysis_plan": [
    "What information must be extracted from the statement and its figure, if it exists."
  ],
  "option_verification_plan": [
    "Step 1 to check an individual option.",
    "Step 2 to verify whether it satisfies the statement.",
    "Step 3 to decide correct, incorrect, or uncertain."
  ],
  "visual_requirements": {{
    "needs_statement_image": true,
    "needs_option_image": true,
    "inspect_in_statement": ["..."],
    "inspect_in_each_option": ["..."]
  }},
  "warnings": [
    "Mistakes to avoid when evaluating isolated options."
  ]
}}

Restrictions:
- Do not say which answer is correct.
- Do not compare options with each other.
- Do not solve the exercise completely.
- The plan must be useful for evaluating one option at a time.
- If the options are figures, explain how to visually verify each figure.
- If the options are text or numbers, explain how to check the proposed value.
- Be concrete and brief.

Answer:
""".strip()

    if idioma == "frances":
        return f"""
Tu es un planificateur expert pour résoudre des questions mathématiques à choix multiple.

Tu es à l'étape 3 d'un pipeline. Les étapes suivantes ont déjà été faites:
1. Classification globale de la question.
2. OCR et recadrage des figures de l'énoncé et/ou des options.

Tu reçois maintenant l'image complète de nouveau, avec ces informations:

Classification:
- Énoncé: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Énoncé:
{statement_text}

Options:
{opciones_json}

Ta tâche N'EST PAS de résoudre le problème ni de choisir une réponse.
Ta tâche est de créer un plan de résolution afin que chaque option puisse ensuite être analysée séparément.

Le plan doit indiquer:
- quelles règles, propriétés, calculs ou critères utiliser;
- ce qu'il faut observer dans la figure de l'énoncé, si elle existe;
- ce qu'il faut vérifier dans une option individuelle;
- comment justifier si une option est correct, incorrect ou uncertain.

Renvoie uniquement un objet JSON valide:

{{
  "problem_summary": "Résumé bref du problème sans le résoudre.",
  "axioms_or_rules": [
    "Règle, propriété, calcul ou critère à utiliser."
  ],
  "statement_analysis_plan": [
    "Quelles informations extraire de l'énoncé et de sa figure, si elle existe."
  ],
  "option_verification_plan": [
    "Étape 1 pour vérifier une option individuelle.",
    "Étape 2 pour vérifier si elle satisfait l'énoncé.",
    "Étape 3 pour décider correct, incorrect ou uncertain."
  ],
  "visual_requirements": {{
    "needs_statement_image": true,
    "needs_option_image": true,
    "inspect_in_statement": ["..."],
    "inspect_in_each_option": ["..."]
  }},
  "warnings": [
    "Erreurs à éviter lors de l'évaluation d'options isolées."
  ]
}}

Restrictions:
- Ne dis pas quelle est la réponse.
- Ne compare pas les options entre elles.
- Ne résous pas complètement l'exercice.
- Le plan doit servir à évaluer une seule option à la fois.
- Si les options sont des figures, explique comment vérifier visuellement chaque figure.
- Si les options sont du texte ou des nombres, explique comment vérifier la valeur proposée.
- Sois concret et bref.

Réponse:
""".strip()

    return f"""
Eres un planificador experto para resolver preguntas matemáticas tipo test.

Estás en el paso 3 de un pipeline. Ya se ha hecho:
1. Clasificación global de la pregunta.
2. OCR y recorte de figuras del enunciado y/o de las opciones.

Ahora recibes la imagen completa de nuevo, junto con esta información:

Clasificación:
- Enunciado: {statement_type} = {desc_statement}
- Opciones: {options_type} = {desc_options}

Enunciado:
{statement_text}

Opciones:
{opciones_json}

Tu tarea NO es resolver el problema ni elegir respuesta.
Tu tarea es crear un plan de resolución para que después se pueda analizar cada opción por separado.

El plan debe indicar:
- qué reglas, propiedades, cálculos o criterios usar;
- qué debe observarse en la figura del enunciado, si existe;
- qué debe comprobarse en una opción individual;
- cómo justificar si una opción es correcta, incorrecta o incierta.

Devuelve únicamente un JSON válido:

{{
  "problem_summary": "Resumen breve del problema sin resolverlo.",
  "axioms_or_rules": [
    "Regla, propiedad, cálculo o criterio que debe usarse."
  ],
  "statement_analysis_plan": [
    "Qué información hay que extraer del enunciado y de su figura, si existe."
  ],
  "option_verification_plan": [
    "Paso 1 para comprobar una opción individual.",
    "Paso 2 para verificar si cumple el enunciado.",
    "Paso 3 para decidir correct, incorrect o uncertain."
  ],
  "visual_requirements": {{
    "needs_statement_image": true,
    "needs_option_image": true,
    "inspect_in_statement": ["..."],
    "inspect_in_each_option": ["..."]
  }},
  "warnings": [
    "Errores a evitar al evaluar opciones aisladas."
  ]
}}

Restricciones:
- No digas cuál es la respuesta.
- No compares opciones entre sí.
- No resuelvas completamente el ejercicio.
- El plan debe servir para evaluar una sola opción cada vez.
- Si las opciones son figuras, explica cómo verificar visualmente cada figura.
- Si las opciones son texto o números, explica cómo comprobar el valor propuesto.
- Sé concreto y breve.

Respuesta:
""".strip()


def crear_prompt_resolucion_textual_directa(resultado_qwen, idioma="castellano"):
    idioma = normalizar_idioma(idioma)
    statement_text = resultado_qwen.get("statement_text")
    options_text = resultado_qwen.get("options_text", {})
    opciones_json = json.dumps(options_text, ensure_ascii=False, indent=2)

    if idioma == "valenciano":
        return f"""
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

    if idioma == "ingles":
        return f"""
You are an expert at solving multiple-choice math questions.
Solve the problem using only the statement and the options.

Statement:
{statement_text}

Options:
{opciones_json}

Instructions:
- Reason step by step.
- Use clear calculations and check the conditions in the statement.
- Evaluate all options A-E.
- Do not invent information that is not in the statement.
- If there is ambiguity or missing information, state it.

Return only a valid JSON object with this structure:

{{
  "reasoning": "Step-by-step reasoning for the solution.",
  "options_analysis": {{
    "A": "Why this option is correct or incorrect.",
    "B": "Why this option is correct or incorrect.",
    "C": "Why this option is correct or incorrect.",
    "D": "Why this option is correct or incorrect.",
    "E": "Why this option is correct or incorrect."
  }},
  "final_answer": "A/B/C/D/E"
}}

Answer:
""".strip()

    if idioma == "frances":
        return f"""
Tu es un expert en résolution de questions mathématiques à choix multiple.
Résous le problème en utilisant uniquement l'énoncé et les options.

Énoncé:
{statement_text}

Options:
{opciones_json}

Instructions:
- Raisonne étape par étape.
- Utilise des calculs clairs et vérifie les conditions de l'énoncé.
- Évalue toutes les options A-E.
- N'invente pas d'informations qui ne sont pas dans l'énoncé.
- S'il y a une ambiguïté ou des informations manquantes, indique-le.

Renvoie uniquement un objet JSON valide avec cette structure:

{{
  "reasoning": "Raisonnement étape par étape de la résolution.",
  "options_analysis": {{
    "A": "Pourquoi cette option est correcte ou incorrecte.",
    "B": "Pourquoi cette option est correcte ou incorrecte.",
    "C": "Pourquoi cette option est correcte ou incorrecte.",
    "D": "Pourquoi cette option est correcte ou incorrecte.",
    "E": "Pourquoi cette option est correcte ou incorrecte."
  }},
  "final_answer": "A/B/C/D/E"
}}

Réponse:
""".strip()

    return f"""
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


def limpiar_plan_resolucion(respuesta_modelo):
    data = parsear_json_modelo(respuesta_modelo)

    if not isinstance(data, dict):
        return {
            "problem_summary": "No se pudo parsear el plan del modelo.",
            "axioms_or_rules": [],
            "statement_analysis_plan": [],
            "option_verification_plan": [
                "Evaluar cada opción con la información disponible.",
                "Marcar la opción como uncertain si la imagen o el texto no permiten decidir.",
            ],
            "visual_requirements": {
                "needs_statement_image": True,
                "needs_option_image": True,
                "inspect_in_statement": [],
                "inspect_in_each_option": [],
            },
            "warnings": [texto_corto_raw(respuesta_modelo)],
            "parse_ok": False,
        }

    visual_requirements = data.get("visual_requirements")
    if not isinstance(visual_requirements, dict):
        visual_requirements = {}

    return {
        "problem_summary": str(data.get("problem_summary") or "").strip(),
        "axioms_or_rules": asegurar_lista_texto(data.get("axioms_or_rules")),
        "statement_analysis_plan": asegurar_lista_texto(data.get("statement_analysis_plan")),
        "option_verification_plan": asegurar_lista_texto(data.get("option_verification_plan")),
        "visual_requirements": {
            "needs_statement_image": bool(visual_requirements.get("needs_statement_image")),
            "needs_option_image": bool(visual_requirements.get("needs_option_image")),
            "inspect_in_statement": asegurar_lista_texto(
                visual_requirements.get("inspect_in_statement")
            ),
            "inspect_in_each_option": asegurar_lista_texto(
                visual_requirements.get("inspect_in_each_option")
            ),
        },
        "warnings": asegurar_lista_texto(data.get("warnings")),
        "parse_ok": True,
    }


def limpiar_resolucion_textual_directa(respuesta_modelo):
    data = parsear_json_modelo(respuesta_modelo)

    if not isinstance(data, dict):
        return {
            "reasoning": "No se pudo parsear la respuesta textual directa.",
            "options_analysis": {letra: "" for letra in ("A", "B", "C", "D", "E")},
            "final_answer": None,
            "parse_ok": False,
            "raw_response": texto_corto_raw(respuesta_modelo),
        }

    options_analysis = data.get("options_analysis")
    if not isinstance(options_analysis, dict):
        options_analysis = {}

    return {
        "reasoning": str(data.get("reasoning") or "").strip(),
        "options_analysis": {
            letra: str(options_analysis.get(letra) or "").strip()
            for letra in ("A", "B", "C", "D", "E")
        },
        "final_answer": normalizar_opcion(data.get("final_answer")),
        "parse_ok": normalizar_opcion(data.get("final_answer")) is not None,
        "raw_response": texto_corto_raw(respuesta_modelo),
    }


def ejecutar_cot(resultado_qwen, imagen_base=None, idioma="castellano"):
    if not isinstance(resultado_qwen, dict):
        return {
            "tipo": "error",
            "resuelto_directo": False,
            "prompt": None,
            "plan_resolucion": json_legible(limpiar_plan_resolucion(None)),
            "plan_limpio": limpiar_plan_resolucion(None),
            "respuesta_directa": None,
            "respuesta_modelo": "",
            "error": "resultado_qwen no es un diccionario válido.",
        }

    if es_caso_textual_directo(resultado_qwen):
        prompt = crear_prompt_resolucion_textual_directa(resultado_qwen, idioma=idioma)

        try:
            respuesta_modelo = llamar_modelo_texto(prompt)
            error = None
        except Exception as exc:
            respuesta_modelo = ""
            error = str(exc)

        respuesta_directa = limpiar_resolucion_textual_directa(respuesta_modelo)

        if error:
            respuesta_directa["reasoning"] = (
                "No se pudo llamar al modelo textual para resolver el caso A.1_B.1."
            )
            respuesta_directa["error"] = error

        return {
            "tipo": "resolucion_directa",
            "resuelto_directo": True,
            "prompt": prompt,
            "plan_resolucion": None,
            "plan_limpio": None,
            "respuesta_directa": respuesta_directa,
            "respuesta_modelo": respuesta_modelo,
            "error": error,
        }

    prompt = crear_prompt_plan_resolucion(resultado_qwen, idioma=idioma)

    if imagen_base is None:
        plan_limpio = limpiar_plan_resolucion(None)
        return {
            "tipo": "plan_resolucion",
            "resuelto_directo": False,
            "prompt": prompt,
            "plan_resolucion": json_legible(plan_limpio),
            "plan_limpio": plan_limpio,
            "respuesta_directa": None,
            "respuesta_modelo": "",
            "error": "No se ha pasado imagen_base; se devuelve solo el prompt.",
        }

    try:
        respuesta_modelo = llamar_modelo_visual(
            imagen_base=imagen_base,
            prompt=prompt,
        )
        error = None
    except Exception as exc:
        respuesta_modelo = ""
        error = str(exc)

    plan_limpio = limpiar_plan_resolucion(respuesta_modelo)

    if error:
        plan_limpio["warnings"].append(
            "No se pudo llamar al modelo visual para generar el plan."
        )
        plan_limpio["error"] = error

    return {
        "tipo": "plan_resolucion",
        "resuelto_directo": False,
        "prompt": prompt,
        "plan_resolucion": json_legible(plan_limpio),
        "plan_limpio": plan_limpio,
        "respuesta_directa": None,
        "respuesta_modelo": respuesta_modelo,
        "error": error,
    }


generar_cot = ejecutar_cot
cot = ejecutar_cot
