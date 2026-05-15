import pandas as pd
import base64
import json
import re
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import requests
from PIL import Image
from ollama import chat

DATASET_PATH = 'pablo_gandia/Replicar/DatasetFull.csv'
VISION_MODEL = 'qwen2.5vl:7b'
MODEL_LABEL = 'Qwen2.5VL 7B'
TEXT_MODEL = 'qwen3:4b'
AUTOSAVE_EVERY = 30
OUTPUT_PATH = 'pablo_gandia/Replicar/DatasetFull_Pipeline.csv'

print(f'Dataset: {DATASET_PATH}')
print(f'Modelo visual: {VISION_MODEL}')
print(f'CSV de salida: {OUTPUT_PATH}')
print()

df = pd.read_csv(DATASET_PATH)

def get_prompts(extracted_int, language):

    prompts = {
        'ingles': f"""Analyze question {extracted_int} shown in the image and choose the correct answer from the given options.
        **Instructions**:
        Explain your reasoning and provide your final answer in this specific format, without any changes:
            Reasoning: Describe the thought process that led to your answer.
            Answer: A), B), C), D), or E).
        """,
        
        'castellano': f"""Analiza la pregunta {extracted_int} mostrada en la imagen y elige la respuesta correcta entre las opciones dadas.
        **Instrucciones**:
        Explica tu razonamiento y proporciona tu respuesta final en este formato específico, sin cambios:
            Razonamiento: Describe el proceso de pensamiento que te llevó a la respuesta.
            Respuesta: A), B), C), D) o E).
        """,

        'frances':f"""Analyse la question {extracted_int} montrée dans l'image et choisis la bonne réponse parmi les options proposées.
        **Instructions** :
        Explique ton raisonnement et fournis ta réponse finale dans ce format, sans aucune modification:
            Raisonnement : Décris le processus de réflexion qui t'a conduit à ta réponse.
            Réponse : A), B), C), D) ou E).
        """,

        'valenciano':f"""Analitza la pregunta {extracted_int} mostrada en la imatge i tria la resposta correcta entre les opcions donades.
        **Instruccions**:
        Explica el teu raonament i proporciona la teua resposta final en aquest format específic, sense canvis:
            Raonament: Descriu el procés de pensament que t'ha portat a la resposta.
            Resposta: A), B), C), D) o E).
        """
    }

    return prompts[language]


def anadir_formato_json(prompt, idioma):
    formatos = {
        'ingles': "\n\nReturn only valid JSON with exactly this format: {\"reasoning\": \"...\", \"answer\": \"A\"}. Do not add markdown or extra text.",
        'castellano': "\n\nDevuelve solo JSON valido con exactamente este formato: {\"reasoning\": \"...\", \"answer\": \"A\"}. No anadas markdown ni texto extra.",
        'frances': "\n\nRetourne seulement un JSON valide avec exactement ce format : {\"reasoning\": \"...\", \"answer\": \"A\"}. N'ajoute ni markdown ni texte extra.",
        'valenciano': "\n\nTorna nomes JSON valid amb exactament este format: {\"reasoning\": \"...\", \"answer\": \"A\"}. No afegisques markdown ni text extra.",
    }
    return prompt + formatos[idioma]

def descargar_bytes_imagen(url):
    respuesta = requests.get(url, timeout=30)
    respuesta.raise_for_status()
    return respuesta.content


def descargar_imagen(url):
    return Image.open(BytesIO(descargar_bytes_imagen(url)))


def imagen_url_a_base64(url):
    return base64.b64encode(descargar_bytes_imagen(url)).decode('utf-8')


def leer_problema(indice, dataset=df):
    fila = dataset.iloc[indice]

    return {
        'idioma': fila['idioma'],
        'enunciado': fila['Enunciado'],
        'opciones': fila['Opciones'],
        'imagen_url': fila['enlace'],
        'respuesta': fila['ground truth'],
        "tematica":    fila["Tematica"],
        "tiene_imagen": fila["existe"].strip().upper() == "SI"
    }


def llamar_modelo_visual(imagen_url, prompt, model=VISION_MODEL):
    imagen_b64 = imagen_url_a_base64(imagen_url)
    respuesta = chat(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': prompt,
                'images': [imagen_b64],
            }
        ],
        options={
            'temperature': 0,
            'max_tokens': 512,
        },
    )
    return respuesta['message']['content'].strip()

def llamar_modelo_texto(prompt, model=TEXT_MODEL):
    respuesta = chat(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': prompt,
            }
        ],
        options={'temperature': 0},
    )

    texto = respuesta['message']['content']

    if '</think>' in texto:
        texto = texto.split('</think>', 1)[1]

    return texto.strip()

####VER
def obtener_prompt(enunciado, idioma):
    extracted_int = enunciado.split()[1]
    return get_prompts(extracted_int, idioma)


def extraer_json(texto):
    """
    Intenta extraer el primer objeto JSON válido del texto.
    Si falla, devuelve un diccionario vacío.
    """
    # Buscar un bloque ```json ... ``` si existe
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if match:
        texto = match.group(1)

    # Intentar parsear directamente
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # Buscar el primer { ... } en el texto
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    print("  [AVISO] No se pudo parsear el JSON del modelo. Texto recibido:")
    print(texto[:300])
    return {}



def extraer_json_respuesta(texto):
    inicio = texto.find('{')

    if inicio == -1:
        raise ValueError('No se ha encontrado el inicio de un JSON en la respuesta del modelo.')

    variantes = []
    fin_llave = texto.rfind('}')
    if fin_llave != -1 and fin_llave >= inicio:
        variantes.append(texto[inicio:fin_llave + 1])

    candidato = texto[inicio:].strip()
    variantes.append(candidato)

    if candidato.endswith(')'):
        variantes.append(candidato[:-1] + '}')

    diferencia_llaves = candidato.count('{') - candidato.count('}')
    if diferencia_llaves > 0:
        variantes.append(candidato + ('}' * diferencia_llaves))

    ultimo_error = None
    for variante in variantes:
        try:
            return json.loads(variante)
        except json.JSONDecodeError as e:
            ultimo_error = e

    raise ValueError(f'No se ha podido parsear el JSON devuelto por el modelo: {ultimo_error}')


def sacar_razonamiento_y_respuesta(texto):
    try:
        datos = extraer_json_respuesta(texto)
        razonamiento = str(datos.get('reasoning', '')).strip()
        respuesta = str(datos.get('answer', '')).strip().upper()
    except Exception:
        razonamiento_match = re.search(r'\"reasoning\"\s*:\s*\"((?:\\\\.|[^\"\\\\])*)\"', texto, re.S)
        respuesta_match = re.search(r'\"answer\"\s*:\s*\"([A-E])', texto, re.I)

        if razonamiento_match is None or respuesta_match is None:
            raise

        razonamiento = json.loads('"' + razonamiento_match.group(1) + '"').strip()
        respuesta = respuesta_match.group(1).upper()

    match = re.search(r'[A-E]', respuesta)
    if match is None:
        raise ValueError('No se ha podido extraer una respuesta entre A y E.')

    return razonamiento, match.group(0)

###Geometría
def resolver_geometria(problema):
        ### FASE 1
    def fase1_segmentacion_semantica(problema):
        """
        FASE 1 - Segmentación Semántica (Visual Grounding)
    
        Pide al modelo visual que identifique las entidades geométricas presentes
        en la imagen: vértices, segmentos, ángulos, figuras y medidas conocidas.
        """
        prompt = f"""Analyze the image of the following mathematical geometry problem.
    
    Statement: {problema['enunciado']}
    
    Your task (DO NOT answer the question):
    Identify and list in a structured way ALL visible geometric elements:
    - Vertices (A, B, C...) and their relative positions.
    - Segments and their lengths (if indicated).
    - Angles and whether they are marked as right, equal, etc.
    - Geometric figures (triangle, square, circle, polygon, etc.).
    - Known values: numerical measurements written on the image.
    
    Be precise and concise. Do not solve the problem."""
    
        print("  [Fase 1] Extrayendo entidades geométricas...")
        return llamar_modelo_visual(problema["imagen_url"], prompt)

    
    ### FASE 2
    def fase2_inyeccion_axiomas(problem, entidades):
        """
        FASE 2 - Inyección de Axiomas (Axiom Prompting)
    
        A partir del inventario de entidades del Paso 1, el modelo escribe
        los teoremas y propiedades matemáticas que va a usar, SIN resolver.
        """
        prompt = f"""You are an expert in mathematical geometry.
    
    Problem:
    {problema['enunciado']}
    
    Geometric entities identified in the image:
    {entidades}
    
    Your task (DO NOT solve the problem yet):
    Write down the mathematical theorems, properties, and formulas that are applicable
    to the detected figures. For example:
    - "The sum of the internal angles of a triangle is 180°."
    - "The area of a circle is π·r²."
    - "The Pythagorean theorem: a² + b² = c²."
    
    List only those that are relevant to this specific problem."""
    
        print("  [Fase 2] Identificando axiomas y teoremas relevantes...")
        return llamar_modelo_texto(prompt)


    def fase3_cot_estructural(problema, entidades, axiomas):
        """
        FASE 3 - CoT Estructural (Razonamiento por Capas)
    
        El modelo razona paso a paso, dividiendo el problema en sub-problemas:
        cálculos intermedios → relación parte/todo → solución final.
        """
        prompt = f"""You are an expert in solving geometry problems.
    
    ### Problem
    {problema['enunciado']}
    
    ### Options
    {problema['opciones']}
    
    ### Identified geometric entities
    {entidades}
    
    ### Applicable properties and theorems
    {axiomas}
    
    ### Instructions
    Solve the problem step by step following THIS order:
    1. Intermediate calculations (e.g., finding lengths, partial areas, auxiliary angles).
    2. Part-to-whole relationship (e.g., how the calculated parts combine to reach the result).
    3. Calculation of the final unknown.
    Show each arithmetic operation clearly.
    
    ### Output format (MANDATORY)
    Return ONLY valid JSON, with no additional text:
    
    {{
        "calculos_intermedios": "<step-by-step>",
        "relacion_parte_todo": "<reasoning>",
        "solucion_previa": "<candidate answer from options>",
        "justificacion": "<brief explanation>"
    }}
    
    DO NOT include text outside the JSON. DO NOT include markdown. DO NOT include comments."""
    
        print("  [Fase 3] Resolviendo con cadena de razonamiento estructurada...")
        return llamar_modelo_texto(prompt)


    def fase4_self_refinement(problema, solucion_fase3):
        """
        FASE 4 - Auto-Consistencia Lingüística (Self-Refinement)
    
        El modelo revisa si la respuesta es coherente con las dimensiones visuales
        del enunciado y corrige errores si los detecta.
        """
        prompt = f"""You are an expert geometry reviewer.
    
    ### Original problem
    {problema['enunciado']}
    
    ### Available options
    {problema['opciones']}
    
    ### Proposed solution (in JSON)
    {solucion_fase3}
    
    ### Your task
    1. Verify that the calculations are arithmetically correct.
    2. Check that the answer is consistent with the magnitudes in the statement
       (e.g., if the side is 6 cm, an area of 1000 cm² does not make sense).
    3. If you detect an error, correct it.
    4. Confirm or correct the final answer.
    
    ### Output format (MANDATORY)
    Return ONLY valid JSON:
    
    {{
        "respuesta": "<letter of the correct option, e.g. C>",
        "justificacion": "<brief and clear explanation of why it is correct>",
        "correccion_aplicada": <true or false>
    }}
    
    DO NOT include text outside the JSON. DO NOT include markdown. DO NOT include comments."""
    
        print("  [Fase 4] Verificando coherencia y auto-corrigiendo...")
        return llamar_modelo_texto(prompt)

     
        
        
    """
    Ejecuta las 4 fases del pipeline de Geometría y Figuras.

    Devuelve un diccionario con:
        - referencia, enunciado, opciones, respuesta_correcta
        - fase1_entidades, fase2_axiomas, fase3_cot (string JSON)
        - respuesta_final (letra), justificacion, correccion_aplicada
    """
 
    # Si el problema no tiene imagen, usamos un placeholder para las fases visuales
    if not problema["tiene_imagen"]:
        print("  [AVISO] El problema no tiene imagen asociada. Se omite la fase visual.")
        entidades = "No hay imagen disponible para este problema."
    else:
        # FASE 1 – Segmentación Semántica
        entidades = fase1_segmentacion_semantica(problema)
        print(f"  → Entidades: {entidades[:120]}...")

    # FASE 2 – Inyección de Axiomas
    axiomas = fase2_inyeccion_axiomas(problema, entidades)
    print(f"  → Axiomas: {axiomas[:120]}...")

    # FASE 3 – CoT Estructural
    cot_raw = fase3_cot_estructural(problema, entidades, axiomas)
    print(f"  → CoT: {cot_raw[:120]}...")

    # FASE 4 – Self-Refinement
    resultado_raw = fase4_self_refinement(problema, cot_raw)
    print(f"  → Resultado: {resultado_raw[:120]}...")

    # Parsear resultado de la Fase 4
    resultado_json = extraer_json(resultado_raw)

    respuesta_final   = resultado_json.get("respuesta", "ERROR")
    justificacion     = resultado_json.get("justificacion", "")
    correccion        = resultado_json.get("correccion_aplicada", False)

    es_correcta = (
        respuesta_final.strip().upper() == problema["respuesta"].strip().upper()
    )

    print(f"\n  RESPUESTA FINAL  : {respuesta_final}")
    print(f"  RESPUESTA CORRECTA: {problema['respuesta']}")
    print(f"  ¿ACERTADO?        : {'✓ SÍ' if es_correcta else '✗ NO'}")

    return {
        "enunciado":           problema["enunciado"],
        "opciones":            problema["opciones"],
        "respuesta_correcta":  problema["respuesta"],
        "tematica":            problema["tematica"],
        # Datos intermedios
        "fase1":     entidades,
        "fase2":       axiomas,
        "fase3":           cot_raw,
        # Resultado
        "respuesta_modelo":    respuesta_final,
        "justificacion":       justificacion,
        "correccion_aplicada": correccion,
        "es_correcta":         es_correcta,
    }

###Algebra

def resolver_algebra(problema):
    ### FASE 1: Data Extraction
    def fase1_data_extraction(problema):
        """
        FASE 1 - Data Extraction
        Genera un inventario de datos crudos sin resolver.
        """
        prompt = f"""Analyze the image and extract all mathematical information. 
        
        Statement: {problema['enunciado']}
        
        Your task:
        List objects and their differences, transcribe text or numbers exactly, 
        and describe the structure (table, scale, grid). 
        Do not solve; generate a raw data inventory."""
    
        print("  [Fase 1] Extrayendo datos visuales...")
        return llamar_modelo_visual(problema["imagen_url"], prompt)

    ### FASE 2: Formalization
    def fase2_formalization(problema, datos_crudos):
        """
        FASE 2 - Formalization
        Traduce la información visual a lenguaje algebraico formal.
        """
        prompt = f"""Based on the inventory, translate the information into formal equations. 
        
        Inventory of data:
        {datos_crudos}
        
        Instructions:
        - Use '=' for scales or balances. 
        - Define sequences as $a_1, a_2, a_3...$. 
        - Ensure every visual relationship has a mathematical representation."""
    
        print("  [Fase 2] Formalizando ecuaciones...")
        return llamar_modelo_texto(prompt)

    ### FASE 3: Substitution & Reduction
    def fase3_substitution_reduction(problema, ecuaciones):
        """
        FASE 3 - Substitution & Reduction
        Resolución paso a paso del sistema de ecuaciones o secuencia.
        """
        prompt = f"""Solve the equations one by one based on these options: {problema['opciones']}
        
        Equations:
        {ecuaciones}
        
        Instructions:
        1. Identify the easiest variable to isolate.
        2. Substitute its value into other expressions.
        3. Show the full development of each operation (+, -, multiplication, division).
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "desarrollo_paso_a_paso": "<arithmetic operations>",
            "variables_aisladas": "<values found per variable>",
            "solucion_previa": "<candidate answer from options>",
            "justificacion_matematica": "<explanation of the reduction>"
        }}"""
    
        print("  [Fase 3] Resolviendo por sustitución y reducción...")
        return llamar_modelo_texto(prompt)

    ### FASE 4: Mathematical Constraints
    def fase4_mathematical_constraints(problema, solucion_fase3):
        """
        FASE 4 - Mathematical Constraints
        Auditoría de signos, orden de operaciones y consistencia final.
        """
        prompt = f"""Audit the process: 
        1. Did you follow the order of operations (PEMDAS/BODMAS)? 
        2. Are the sign rules correct? 
        3. Does the final value satisfy all initial visual expressions?
        
        Proposed Solution:
        {solucion_fase3}
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "respuesta": "<letter of the correct option>",
            "justificacion": "<final audit summary>",
            "correccion_aplicada": <true or false>
        }}"""
    
        print("  [Fase 4] Auditando restricciones matemáticas...")
        return llamar_modelo_texto(prompt)

    # --- EJECUCIÓN DEL PIPELINE ---
    
    if not problema["tiene_imagen"]:
        print("  [AVISO] El problema no tiene imagen asociada.")
        datos_crudos = f"No image. Text-only data: {problema['enunciado']}"
    else:
        datos_crudos = fase1_data_extraction(problema)

    ecuaciones = fase2_formalization(problema, datos_crudos)
    cot_raw = fase3_substitution_reduction(problema, ecuaciones)
    resultado_raw = fase4_mathematical_constraints(problema, cot_raw)

    # Parsear resultado final
    resultado_json = extraer_json(resultado_raw)
    respuesta_final = resultado_json.get("respuesta", "ERROR")
    es_correcta = (respuesta_final.strip().upper() == problema["respuesta"].strip().upper())

    print(f"\n  RESPUESTA FINAL  : {respuesta_final}")
    print(f"  ¿ACERTADO?        : {'✓ SÍ' if es_correcta else '✗ NO'}")

    return {
  
        "respuesta_modelo": respuesta_final,
        "es_correcta": es_correcta,
        "fase1": datos_crudos,
        "fase2": ecuaciones,
        "fase3": cot_raw,
        "justificacion": resultado_json.get("justificacion", ""),
        "correccion_aplicada": resultado_json.get("correccion_aplicada", False)
    }

###Lógica
def resolver_logica(problema):
    ### FASE 1: Feature Mapping
    def fase1_feature_mapping(problema):
        """
        FASE 1 - Feature Mapping
        Catalogación de variables lógicas sin deducir reglas.
        """
        prompt = f"""Analyze the image as a system of logical variables. 
        
        Statement: {problema['enunciado']}
        
        Your task:
        Catalog each element by: 
        1. Physical properties (shape, color, size, orientation). 
        2. Spatial distribution (relative position). 
        3. Changes (differences between element A and B). 
        
        Do not deduce the rule yet."""
    
        print("  [Fase 1] Mapeando variables visuales...")
        return llamar_modelo_visual(problema["imagen_url"], prompt)

    ### FASE 2: Pattern Induction
    def fase2_pattern_induction(problema, entidades):
        """
        FASE 2 - Pattern Induction
        Identificación explícita de la regla lógica.
        """
        prompt = f"""Identify the underlying logic: Progression (rotation/increment), 
        Visual Operation (addition/superposition of shapes), or Classification (odd one out). 
        
        Entities and variables mapped:
        {entidades}
        
        State the rule explicitly: 'The rule is...'"""
    
        print("  [Fase 2] Induciendo el patrón lógico...")
        return llamar_modelo_texto(prompt)

    ### FASE 3: Reasoning Chain
    def fase3_reasoning_chain(problema, entidades, regla):
        """
        FASE 3 - Reasoning Chain
        Aplicación paso a paso y descarte de opciones.
        """
        prompt = f"""Apply the rule step-by-step: 
        1. Predict the next state.
        2. Compare with these options: {problema['opciones']}
        3. Discard choices that violate any attribute mapped in Phase 1 (e.g., 'Option C is incorrect because the color is red, but the rule requires blue').
        
        Context:
        - Mapped Attributes: {entidades}
        - Established Rule: {regla}
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "prediccion_estado": "<next state description>",
            "descarte_opciones": "<step-by-step elimination>",
            "solucion_previa": "<candidate answer from options>",
            "justificacion_logica": "<logic breakdown>"
        }}"""
    
        print("  [Fase 3] Aplicando cadena de razonamiento...")
        return llamar_modelo_texto(prompt)

    ### FASE 4: Logic Audit
    def fase4_logic_audit(problema, razonamiento):
        """
        FASE 4 - Logic Audit
        Auditoría inversa y verificación de simplicidad/consistencia.
        """
        prompt = f"""Perform a reverse audit: 
        1. Does the rule hold from the beginning of the series? 
        2. Is there a simpler rule? 
        3. Did you ignore any small visual detail? 
        4. Confirm the solution is the only one fulfilling 100% of the conditions.
        
        Proposed Reasoning:
        {razonamiento}
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "respuesta": "<letter of the correct option>",
            "justificacion": "<final audit summary>",
            "correccion_aplicada": <true or false>
        }}"""
    
        print("  [Fase 4] Ejecutando auditoría de lógica...")
        return llamar_modelo_texto(prompt)

    # --- EJECUCIÓN DEL PIPELINE ---
    
    if not problema["tiene_imagen"]:
        print("  [AVISO] No hay imagen. Se requiere input visual para Lógica Visual.")
        entidades = "No image available."
    else:
        entidades = fase1_feature_mapping(problema)

    regla = fase2_pattern_induction(problema, entidades)
    cot_raw = fase3_reasoning_chain(problema, entidades, regla)
    resultado_raw = fase4_logic_audit(problema, cot_raw)

    # Parsear y retornar (mismo esquema que el original)
    resultado_json = extraer_json(resultado_raw)
    respuesta_final = resultado_json.get("respuesta", "ERROR")
    es_correcta = (respuesta_final.strip().upper() == problema["respuesta"].strip().upper())

    return {
        "respuesta_modelo": respuesta_final,
        "es_correcta": es_correcta,
        "fase1": entidades,
        "fase2": regla,
        "fase3": cot_raw,
        "justificacion": resultado_json.get("justificacion", "")
    }


###Patrones
def resolver_patrones(problema):
    ### FASE 1: State Decomposition
    def fase1_state_decomposition(problema):
        """
        FASE 1 - State Decomposition
        Descompone la secuencia en estados y describe sus componentes.
        """
        prompt = f"""Break the sequence into individual states (State 1, State 2...). 
        
        Statement: {problema['enunciado']}
        
        Your task:
        Describe: 
        1. Constant elements. 
        2. Variable elements (moving or changing). 
        3. Quantitative values (counting sides/pieces). 
        4. Orientation (rotation in degrees or clock positions)."""
    
        print("  [Fase 1] Descomponiendo estados de la secuencia...")
        return llamar_modelo_visual(problema["imagen_url"], prompt)

    ### FASE 2: Delta Identification
    def fase2_delta_identification(problema, estados):
        """
        FASE 2 - Delta Identification
        Identifica la diferencia exacta entre estados consecutivos.
        """
        prompt = f"""Compare State 1 with State 2, and State 2 with State 3. 
        
        Decomposed States:
        {estados}
        
        Your task:
        - What is the exact difference (delta)? 
        - Is the difference constant? 
        - If the delta changes, is there a pattern in that change (e.g., $+1, +2, +3$)?."""
    
        print("  [Fase 2] Identificando deltas de cambio...")
        return llamar_modelo_texto(prompt)

    ### FASE 3: Sequence Modeling
    def fase3_sequence_modeling(problema, estados, deltas):
        """
        FASE 3 - Sequence Modeling
        Genera la regla general y predice el siguiente estado.
        """
        prompt = f"""Generate the general rule for this sequence based on these options: {problema['opciones']}
        
        Context:
        - States: {estados}
        - Deltas: {deltas}
        
        Instructions:
        - If numeric: 'State $n$ is $f(n) = \dots$'. 
        - If visual: 'Element [X] performs action [Y] while [Z] remains fixed'. 
        - Use this to predict the missing state.
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "regla_general": "<mathematical or visual rule>",
            "prediccion_estado_n": "<detailed description of the target state>",
            "solucion_previa": "<candidate answer from options>",
            "justificacion": "<logic connecting rule to prediction>"
        }}"""
    
        print("  [Fase 3] Modelando la regla de la secuencia...")
        return llamar_modelo_texto(prompt)

    ### FASE 4: Forward-Backward Check
    def fase4_forward_backward_check(problema, solucion_fase3):
        """
        FASE 4 - Forward-Backward Check
        Verificación en ambos sentidos para asegurar consistencia total.
        """
        prompt = f"""Perform a Forward-Backward check: 
        1. Projection: Does the predicted next element match the visual rules for every detail?
        2. Retro-verification: If you apply the rule backward from State 2, do you reach State 1? 
        3. Ensure the rule explains every single detail (color, count, position).
        
        Proposed Solution:
        {solucion_fase3}
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "respuesta": "<letter of the correct option>",
            "justificacion": "<final summary of the forward/backward check>",
            "correccion_aplicada": <true or false>
        }}"""
    
        print("  [Fase 4] Ejecutando verificación Forward-Backward...")
        return llamar_modelo_texto(prompt)

    # --- EJECUCIÓN DEL PIPELINE ---
    
    if not problema["tiene_imagen"]:
        print("  [AVISO] Se requiere una secuencia visual para este pipeline.")
        estados = "No image available."
    else:
        estados = fase1_state_decomposition(problema)

    deltas = fase2_delta_identification(problema, estados)
    cot_raw = fase3_sequence_modeling(problema, estados, deltas)
    resultado_raw = fase4_forward_backward_check(problema, cot_raw)

    # Parsear y retornar
    resultado_json = extraer_json(resultado_raw)
    respuesta_final = resultado_json.get("respuesta", "ERROR")
    es_correcta = (respuesta_final.strip().upper() == problema["respuesta"].strip().upper())

    print(f"\n  RESPUESTA FINAL  : {respuesta_final}")
    print(f"  ¿ACERTADO?        : {'✓ SÍ' if es_correcta else '✗ NO'}")

    return {
  
        "respuesta_modelo": respuesta_final,
        "es_correcta": es_correcta,
        "fase1": estados,
        "fase2": deltas,
        "fase3": cot_raw,
        "justificacion": resultado_json.get("justificacion", "")
    }


###Combinatoria
def resolver_combinatoria(problema):
    ### FASE 1: Sample Space Definition
    def fase1_sample_space(problema):
        """
        FASE 1 - Sample Space Definition
        Define el inventario de elementos y el conjunto S sin operar.
        """
        prompt = f"""Analyze the image to define the sample space.
        
        Statement: {problema['enunciado']}
        
        Your task:
        1. Inventory of elements: List every unique object (e.g., '3 red balls, 2 blue balls'). 
        2. Categorization: Are the objects distinguishable or identical within their group? 
        3. Container/Structure: Describe the environment (urn, deck, grid, or path). 
        
        Do not perform operations; simply define the set $S$."""
    
        print("  [Fase 1] Definiendo el espacio muestral...")
        return llamar_modelo_visual(problema["imagen_url"], prompt)

    ### FASE 2: Selection Rules
    def fase2_selection_rules(problema, inventario):
        """
        FASE 2 - Selection Rules
        Identifica restricciones visuales y selecciona la técnica (Combinatoria/Permutación).
        """
        prompt = f"""Analyze the constraints of the visual problem.
        
        Inventory of elements:
        {inventario}
        
        Your task:
        1. Does order matter? (e.g., codes vs. groups). 
        2. Is there replacement or repetition? 
        3. Additional visual constraints: Are there elements that must stay together or positions that are blocked? 
        
        Define the technique: 'We will use [Combinations/Permutations] because...'"""
    
        print("  [Fase 2] Identificando reglas de selección y técnica...")
        return llamar_modelo_texto(prompt)

    ### FASE 3: Formula Mapping
    def fase3_formula_mapping(problema, inventario, reglas):
        """
        FASE 3 - Formula Mapping
        Traduce la lógica visual a fórmulas matemáticas y realiza la sustitución.
        """
        prompt = f"""Translate the visual logic into a formula.
        
        ### Context
        - Elements: {inventario}
        - Selection logic: {reglas}
        - Options: {problema['opciones']}
        
        ### Instructions
        1. If it's probability, define $P(A) = \\frac{{\\text{{Favorable Cases}}}}{{\\text{{Total Cases}}}}$. 
        2. If it's combinatorics, use the appropriate notation (e.g., $\\binom{{n}}{{k}}$ or $P_n$). 
        3. Substitute the values from Phase 1 into your formula.
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "formula_seleccionada": "<formula with notation>",
            "sustitucion_valores": "<calculation with values>",
            "solucion_previa": "<candidate answer from options>",
            "justificacion": "<logic connecting visual rules to formula>"
        }}"""
    
        print("  [Fase 3] Mapeando fórmulas y calculando...")
        return llamar_modelo_texto(prompt)

    ### FASE 4: Logic Convergence
    def fase4_logic_convergence(problema, solucion_fase3):
        """
        FASE 4 - Logic Convergence
        Auditoría de consistencia matemática y coherencia visual.
        """
        prompt = f"""Audit the result for consistency:
        1. Probability Bound: Is the result between 0 and 1? 
        2. Symmetry: Does 'choosing k' match 'leaving n-k'? 
        3. Extreme Cases: If you manually list the first 3 possible cases, do they match your formula's logic? 
        4. Confirm the answer is mathematically and visually coherent.
        
        Proposed Solution:
        {solucion_fase3}
        
        ### Output format (MANDATORY)
        Return ONLY valid JSON:
        {{
            "respuesta": "<letter of the correct option>",
            "justificacion": "<final audit summary>",
            "correccion_aplicada": <true or false>
        }}"""
    
        print("  [Fase 4] Auditando convergencia lógica...")
        return llamar_modelo_texto(prompt)

    # --- EJECUCIÓN DEL PIPELINE ---
    
    if not problema["tiene_imagen"]:
        print("  [AVISO] Sin imagen. Se define el espacio basándose en el texto.")
        inventario = f"Inventory based on text: {problema['enunciado']}"
    else:
        inventario = fase1_sample_space(problema)

    reglas = fase2_selection_rules(problema, inventario)
    cot_raw = fase3_formula_mapping(problema, inventario, reglas)
    resultado_raw = fase4_logic_convergence(problema, cot_raw)

    # Parsear y retornar
    resultado_json = extraer_json(resultado_raw)
    respuesta_final = resultado_json.get("respuesta", "ERROR")
    es_correcta = (respuesta_final.strip().upper() == problema["respuesta"].strip().upper())

    print(f"\n  RESPUESTA FINAL  : {respuesta_final}")
    print(f"  ¿ACERTADO?        : {'✓ SÍ' if es_correcta else '✗ NO'}")

    return {
        "enunciado": problema["enunciado"],
        "respuesta_correcta": problema["respuesta"],
        "fase1": inventario,
        "fase2": reglas,
        "fase3": cot_raw,
        "respuesta_modelo": respuesta_final,
        "justificacion": resultado_json.get("justificacion", ""),
        "es_correcta": es_correcta
    }





def resolver (problema):

    tematica = problema['tematica']

    if tematica == 'Geometría y Figuras':
        respuesta = resolver_geometria(problema)

    elif tematica == 'Álgebra y Aritmética Visual':
        respuesta = resolver_algebra(problema)

    elif tematica == 'Lógica y Razonamiento Visual':
        respuesta = resolver_logica(problema)
  
    elif tematica == 'Patrones y Secuencias':
        respuesta = resolver_patrones(problema)
 
    elif tematica == 'Combinatoria y Probabilidad':
        respuesta = resolver_combinatoria(problema)
       
    else:
        print ('No categoría.')
        respuesta = None

    return respuesta



def action(INDICE_PRUEBA, df):

    problema = leer_problema(INDICE_PRUEBA, df)

    respuesta = resolver(problema)
    return respuesta




filas = []

for indice in range(len(df)):
    print(f"Procesando índice {indice}...")
    
    try:
        respuesta = action(indice, df)
        fase1 = respuesta["fase1"],
        fase2 =  respuesta["fase2"],
        fase3 =  respuesta["fase3"],
        respuesta1 = respuesta["respuesta_modelo"],
        razonamiento = respuesta["justificacion"],
        es_correcta =  respuesta["es_correcta"]
        if razonamiento is None or respuesta is None:
            error = 1
        else:
            error = 0

    except Exception as e:
        print(f"Error en índice {indice}: {e}")

        razonamiento = None
        respuesta1 = None
        error = 1
        fase1 = None
        fase2 =  None
        fase3 = None
    filas.append({
        'indice_original': indice,
        'razonamiento': razonamiento,
        'respuesta': respuesta1,
        "fase1" : fase1,
        "fase2" :  fase2,
        "fase2" :  fase3,
        'error': error
    })

    if len(filas) % AUTOSAVE_EVERY == 0:
        pd.DataFrame(filas).to_csv(OUTPUT_PATH, index=False)
        print(f"Guardado intermedio después de procesar {len(filas)} índices.")

df_new = pd.DataFrame(filas)
df_new.to_csv(OUTPUT_PATH, index=False)

print("Procesamiento terminado.")
