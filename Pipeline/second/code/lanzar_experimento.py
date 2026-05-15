import argparse
import json
import os
import re
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd
from paddleocr import PaddleOCR

from cot import ejecutar_cot
from decision_final import decidir_respuesta_final
from idiomas import normalizar_idioma
from juez_visual import juzgar_respuesta_final
from limpieza_modelos import normalizar_opcion, normalizar_status, parsear_json_modelo
from pipeline_funcion import (
    OCR_PIPE,
    abrir_imagen_desde_bytes,
    imagen_bytes_a_base64,
    obtener_bytes_imagen,
)
from verificacion_opciones import generar_razonamientos_opciones
from verificador_ocr import verificador_ocr
import os
import sys

print("=== OLLAMA ===")
print("OLLAMA_HOST:", os.environ.get("OLLAMA_HOST", "No definido -> usa 127.0.0.1:11434 por defecto"))

print("\n=== PYTHON ===")
print("Python executable:", sys.executable)


BASE_DIR = Path(__file__).resolve().parent
DATASET_DEFAULT = "/home/cguiesc/pablo_gandia/CROPEAR/pipelinefin/filtrado_pipeline822.csv"
OUTPUT_DEFAULT = BASE_DIR / "resultados_experimentos_822a.json"
AUTOSAVE_CADA = 3
OPCIONES = ("A", "B", "C", "D", "E")
PATRON_STATUS = re.compile(
    r"\bstatus\b\s*[:=]\s*[\"']?([A-Za-zÀ-ÿ]+)",
    flags=re.IGNORECASE,
)


@contextmanager
def silenciar_salidas():
    with open(os.devnull, "w") as devnull:
        with redirect_stdout(devnull), redirect_stderr(devnull):
            yield


def guardar_json_atomico(resultados, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    os.replace(tmp_path, output_path)


def es_url(valor):
    texto = str(valor).strip().lower()
    return texto.startswith("http://") or texto.startswith("https://")


def indice_json(indice):
    try:
        return int(indice)
    except (TypeError, ValueError):
        return str(indice)


def respuesta_bool_desde_status(valor):
    if isinstance(valor, bool):
        return valor

    status = normalizar_status(valor)

    if status == "correct":
        return True
    if status == "incorrect":
        return False

    return None


def status_desde_texto(texto):
    texto = "" if texto is None else str(texto).strip()

    respuesta = respuesta_bool_desde_status(texto)
    if respuesta is not None:
        return respuesta

    match = PATRON_STATUS.search(texto)
    if match:
        return respuesta_bool_desde_status(match.group(1))

    texto_lower = texto.lower()

    if re.search(r"\b(incorrect|incorrecta|incorrecto|incorrecte|false|faux|fausse)\b", texto_lower):
        return False

    if re.search(r"\b(correct|correcta|correcto|correcte|true|vrai)\b", texto_lower):
        return True

    if re.search(r"\b(uncertain|incierta|incierto|incerta|incert|incertain|incertaine)\b", texto_lower):
        return None

    return None


def extraer_dict_razonamiento(item):
    candidatos = []

    if isinstance(item, dict):
        candidatos.extend([
            item.get("respuesta_modelo"),
            item.get("respuesta_texto"),
            item,
        ])
    else:
        candidatos.append(item)

    for candidato in candidatos:
        if isinstance(candidato, dict):
            return candidato

        parsed = parsear_json_modelo(candidato)
        if isinstance(parsed, dict):
            return parsed

    return {}


def extraer_respuesta_opcion(item):
    data = extraer_dict_razonamiento(item)

    for clave in ("status", "estado", "is_correct", "correct"):
        if clave in data:
            valor = data.get(clave)
            respuesta = respuesta_bool_desde_status(valor)
            if respuesta is not None or str(valor or "").strip():
                return respuesta

    for candidato in (
        data.get("raw_response"),
        data.get("reasoning"),
        item.get("respuesta_texto") if isinstance(item, dict) else None,
        item,
    ):
        respuesta = status_desde_texto(candidato)
        if respuesta is not None:
            return respuesta

    return None


def respuestas_desde_razonamientos(razonamientos_opciones):
    respuestas = {f"respuesta_{letra}": None for letra in OPCIONES}

    if not isinstance(razonamientos_opciones, list):
        return respuestas

    for posicion, item in enumerate(razonamientos_opciones):
        data = extraer_dict_razonamiento(item)

        opcion = normalizar_opcion(data.get("option"))
        if opcion is None and isinstance(item, dict):
            opcion = normalizar_opcion(item.get("opcion") or item.get("option"))
        if opcion is None and posicion < len(OPCIONES):
            opcion = OPCIONES[posicion]

        if opcion not in OPCIONES:
            continue

        respuestas[f"respuesta_{opcion}"] = extraer_respuesta_opcion(item)

    return respuestas


def primer_valor_no_vacio(data, claves):
    if not isinstance(data, dict):
        return None

    for clave in claves:
        valor = data.get(clave)
        if valor is None:
            continue

        if isinstance(valor, str):
            valor = valor.strip()
            if not valor:
                continue

        return valor

    return None


def extraer_respuesta_razonamiento(
    data,
    claves_respuesta=("answer", "final_answer"),
    claves_razonamiento=("reasoning", "final_reasoning"),
):
    respuesta = normalizar_opcion(primer_valor_no_vacio(data, claves_respuesta))
    razonamiento = primer_valor_no_vacio(data, claves_razonamiento)

    if razonamiento is not None:
        razonamiento = str(razonamiento).strip() or None

    return respuesta, razonamiento


def resultado_base(indice):
    return {
        "indice": indice_json(indice),
        "idioma": None,
        "razonamiento_general": None,
        "respuesta_general": None,
        "razonamiento_antes_juez": None,
        "respuesta_antes_juez": None,
        "decision_antes_juez": None,
        "razonamiento_juzgado": None,
        "respuesta_final": None,
        "respuesta_A": None,
        "respuesta_B": None,
        "respuesta_C": None,
        "respuesta_D": None,
        "respuesta_E": None,
        "error": None,
    }


def procesar_fila(indice, fila, ocr):
    resultado = resultado_base(indice)

    try:
        idioma = normalizar_idioma(fila.get("idioma", "castellano"))
        resultado["idioma"] = idioma

        img_url = fila["enlace"]
        local = not es_url(img_url)

        imagen_raw = obtener_bytes_imagen(img_url, local=local)
        imagen_bytes = abrir_imagen_desde_bytes(imagen_raw)
        imagen_base = imagen_bytes_a_base64(imagen_raw)

        print('Haciendo OCR...', flush=True)
        salidas = OCR_PIPE(imagen_bytes, imagen_base, ocr, idioma=idioma)
        resultado_qwen = salidas.get("resultado_qwen")

        if not isinstance(resultado_qwen, dict):
            raise ValueError("OCR_PIPE no devolvió resultado_qwen válido.")

        recortes = salidas.get("recortes", {})
        colores_recortes = salidas.get("colores_recortes", {})
        imagen_bboxes = salidas.get("imagen_bboxes_figuras_enunciado_y_opciones")

        print('Verificando opciones con OCR...', flush=True)
        lista_a_probar = verificador_ocr(
            statement_type=resultado_qwen.get("statement_type"),
            options_type=resultado_qwen.get("options_type"),
            colores_bboxes=colores_recortes,
            imagen_bboxes_figuras_enunciado_y_opciones=imagen_bboxes,
            recortes=recortes,
            idioma=idioma,
        )

        print('Ejecutando CoT...', flush=True)
        salida_cot = ejecutar_cot(
            resultado_qwen=resultado_qwen,
            imagen_base=imagen_base,
            idioma=idioma,
        )

        if salida_cot.get("resuelto_directo"):
            respuesta_directa = salida_cot.get("respuesta_directa") or {}
            respuesta_previa, razonamiento_previo = extraer_respuesta_razonamiento(
                respuesta_directa,
                claves_respuesta=("final_answer", "answer"),
                claves_razonamiento=("reasoning", "final_reasoning"),
            )
            resultado["razonamiento_general"] = razonamiento_previo
            resultado["respuesta_general"] = respuesta_previa
            resultado["razonamiento_antes_juez"] = razonamiento_previo
            resultado["respuesta_antes_juez"] = respuesta_previa
            resultado["decision_antes_juez"] = respuesta_directa
            resultado["razonamiento_juzgado"] = razonamiento_previo
            resultado["respuesta_final"] = respuesta_previa
            resultado["error"] = respuesta_directa.get("error")
            return resultado

        print('Generando razonamientos para cada opción...', flush=True)
        plan_resolucion = salida_cot.get("plan_resolucion")
        razonamientos_opciones = generar_razonamientos_opciones(
            resultado_qwen=resultado_qwen,
            recortes=recortes,
            lista_a_probar=lista_a_probar,
            imagen_base=imagen_base,
            plan_resolucion=plan_resolucion,
            verbose=False,
            idioma=idioma,
        )
        resultado.update(respuestas_desde_razonamientos(razonamientos_opciones))

        print('Decidiendo respuesta final...', flush=True)
        salida_decision = decidir_respuesta_final(
            resultado_qwen=resultado_qwen,
            razonamientos_opciones=razonamientos_opciones,
            idioma=idioma,
        )
        decision_final = salida_decision.get("decision_final") or {}

        print('Juzgando respuesta final...', flush=True)
        salida_juez = juzgar_respuesta_final(
            resultado_qwen=resultado_qwen,
            razonamientos_opciones=razonamientos_opciones,
            decision_final=decision_final,
            imagen_base=imagen_base,
            idioma=idioma,
        )
        respuesta_juez = salida_juez.get("respuesta_juez") or {}

        respuesta_previa, razonamiento_previo = extraer_respuesta_razonamiento(
            decision_final,
            claves_respuesta=("answer", "final_answer"),
            claves_razonamiento=("reasoning", "final_reasoning"),
        )
        respuesta_final, razonamiento_juzgado = extraer_respuesta_razonamiento(
            respuesta_juez,
            claves_respuesta=("final_answer", "answer"),
            claves_razonamiento=("final_reasoning", "reasoning"),
        )

        resultado["razonamiento_general"] = razonamiento_previo
        resultado["respuesta_general"] = respuesta_previa
        resultado["razonamiento_antes_juez"] = razonamiento_previo
        resultado["respuesta_antes_juez"] = respuesta_previa
        resultado["decision_antes_juez"] = decision_final
        resultado["razonamiento_juzgado"] = razonamiento_juzgado
        resultado["respuesta_final"] = respuesta_final
        resultado["error"] = (
            salida_cot.get("error")
            or salida_decision.get("error")
            or salida_juez.get("error")
        )

    except Exception as exc:
        resultado["error"] = {
            "tipo": exc.__class__.__name__,
            "mensaje": str(exc),
            "traceback": traceback.format_exc(),
        }

    return resultado


def crear_ocr():
    return PaddleOCR(
        device="cpu",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def lanzar_experimento(dataset_path, output_path, autosave_cada=AUTOSAVE_CADA):
    df = pd.read_csv(dataset_path)
    total = len(df)
    resultados = []

    try:
        with silenciar_salidas():
            ocr = crear_ocr()

        for posicion, (indice, fila) in enumerate(df.iterrows(), start=1):
            faltan = total - posicion
            print(
                f"\nMuestra {posicion}/{total} | indice {indice_json(indice)} | faltan {faltan}",
                flush=True,
            )

            with silenciar_salidas():
                resultado = procesar_fila(indice, fila, ocr)

            resultados.append(resultado)

            if autosave_cada > 0 and posicion % autosave_cada == 0:
                guardar_json_atomico(resultados, output_path)

    finally:
        if resultados:
            guardar_json_atomico(resultados, output_path)

    return resultados


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--output", default=str(OUTPUT_DEFAULT))
    parser.add_argument("--autosave-cada", type=int, default=AUTOSAVE_CADA)
    return parser.parse_args()


def main():
    args = parse_args()
    resultados = []

    try:
        resultados = lanzar_experimento(
            dataset_path=args.dataset,
            output_path=args.output,
            autosave_cada=args.autosave_cada,
        )
    finally:
        if resultados:
            guardar_json_atomico(resultados, args.output)


if __name__ == "__main__":
    main()
