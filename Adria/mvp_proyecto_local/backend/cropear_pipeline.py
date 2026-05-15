from __future__ import annotations

import base64
import importlib.util
import os
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import requests
from PIL import Image


PIPELINEFIN_DIR = Path(
    os.getenv("CROPEAR_PIPELINE_DIR", "/home/cguiesc/pablo_gandia/CROPEAR/pipelinefin")
).resolve()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
VISION_MODEL = os.getenv("CROPEAR_VISION_MODEL", "qwen2.5vl:7b")
TEXT_MODEL = os.getenv("CROPEAR_TEXT_MODEL", "qwen3:4b")
OPTIONS = ("A", "B", "C", "D", "E")


def _emit_status(status_callback: Callable[[str], None] | None, message: str) -> None:
    if status_callback is None:
        return
    try:
        status_callback(message)
    except Exception as exc:
        print("[backend][cropear] Status callback failed:", exc)


class CropearPipelineError(RuntimeError):
    """Raised when the CROPEAR data pipeline cannot complete."""


@dataclass
class CropearDataPipeline:
    pipeline_dir: Path = PIPELINEFIN_DIR
    ollama_base_url: str = OLLAMA_BASE_URL

    @property
    def pull_command(self) -> str:
        return f"ollama pull {VISION_MODEL} && ollama pull {TEXT_MODEL}"

    def health(self) -> dict[str, Any]:
        dependencies = self._dependency_status()
        ollama = self._ollama_status()
        return {
            "pipeline_dir": str(self.pipeline_dir),
            "pipeline_dir_exists": self.pipeline_dir.exists(),
            "dependencies": dependencies,
            "ollama": ollama,
            "vision_model": VISION_MODEL,
            "text_model": TEXT_MODEL,
        }

    def extract_problem_text(self, *, image_bytes: bytes, language: str = "castellano") -> dict[str, Any]:
        modules = self._load_modules()
        language = modules["normalizar_idioma"](language)
        image_base = modules["imagen_bytes_a_base64"](image_bytes)

        raw_response = modules["llamar_modelo_visual"](
            imagen_base=image_base,
            prompt=modules["crear_prompt_visual"](language),
        )
        classification = modules["limpiar_salida_qwen"](raw_response)
        if not classification:
            raise CropearPipelineError("QwenVL no devolvio una clasificacion OCR valida.")

        return {
            "ok": True,
            "language": language,
            "text": _statement_for_editor(classification),
            "classification": classification,
            "statement_text": classification.get("statement_text") or "",
            "options_text": classification.get("options_text") or {},
            "raw_response": raw_response,
        }

    def solve(
        self,
        *,
        image_bytes: bytes,
        language: str = "castellano",
        status_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        _emit_status(status_callback, "Preparando imagen y modelos...")
        modules = self._load_modules()
        try:
            modules["descargar_modelos_ollama_excepto"](VISION_MODEL)
        except Exception as exc:
            print("[backend][cropear] Could not unload external Ollama models:", exc)
        language = modules["normalizar_idioma"](language)
        image_pil = modules["abrir_imagen_desde_bytes"](image_bytes)
        image_base = modules["imagen_bytes_a_base64"](image_bytes)

        print("[backend][cropear] Phase 1 OCR_PIPE")
        _emit_status(status_callback, "Fase 1/6: extrayendo estructura y recortes con OCR_PIPE...")
        try:
            ocr = modules["PaddleOCR"](
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
            ocr_result = modules["OCR_PIPE"](
                imagen_bytes=image_pil,
                imagen_base=image_base,
                ocr=ocr,
                idioma=language,
            )
        except Exception as exc:
            raise CropearPipelineError(f"No se pudo ejecutar OCR_PIPE: {exc}") from exc

        classification = dict(ocr_result.get("resultado_qwen") or {})
        if not classification:
            raise CropearPipelineError("OCR_PIPE no devolvio resultado_qwen.")

        statement_type = classification.get("statement_type")
        options_type = classification.get("options_type")
        recortes = ocr_result.get("recortes") or {}
        colores_recortes = ocr_result.get("colores_recortes") or {}

        print("[backend][cropear] Phase 2 crop verifier")
        _emit_status(status_callback, "Fase 2/6: verificando calidad de recortes...")
        try:
            bad_crops = modules["verificador_ocr"](
                statement_type=statement_type,
                options_type=options_type,
                colores_bboxes=colores_recortes,
                imagen_bboxes_figuras_enunciado_y_opciones=ocr_result.get(
                    "imagen_bboxes_figuras_enunciado_y_opciones"
                ),
                recortes=recortes,
                idioma=language,
            )
        except Exception as exc:
            raise CropearPipelineError(f"No se pudo ejecutar verificador_ocr: {exc}") from exc
        print("[backend][cropear] bad_crops:", bad_crops)

        print("[backend][cropear] Phase 3 CoT")
        _emit_status(status_callback, "Fase 3/6: generando plan de resolucion...")
        cot_result = modules["ejecutar_cot"](
            resultado_qwen=classification,
            imagen_base=image_base,
            idioma=language,
        )

        crop_images = _serialize_crop_images(recortes, colores_recortes)
        annotated_crops_image = _pil_to_data_url(
            ocr_result.get("imagen_bboxes_figuras_enunciado_y_opciones")
        )
        ocr_sections_image = _pil_to_data_url(ocr_result.get("imagen_bboxes_enunciado_y_opciones"))

        if cot_result.get("resuelto_directo"):
            _emit_status(status_callback, "Caso textual directo: formateando resolucion...")
            return self._format_direct_result(
                language=language,
                classification=classification,
                ocr_result=ocr_result,
                crop_images=crop_images,
                annotated_crops_image=annotated_crops_image,
                ocr_sections_image=ocr_sections_image,
                bad_crops=bad_crops,
                cot_result=cot_result,
            )

        plan_resolucion = cot_result.get("plan_resolucion")
        plan_limpio = cot_result.get("plan_limpio") or {}

        print("[backend][cropear] Phase 4 option-by-option verification")
        _emit_status(status_callback, "Fase 4/6: verificando opciones una a una...")
        razonamientos_opciones = modules["generar_razonamientos_opciones"](
            resultado_qwen=classification,
            recortes=recortes,
            lista_a_probar=bad_crops,
            imagen_base=image_base,
            plan_resolucion=plan_resolucion,
            idioma=language,
        )

        print("[backend][cropear] Phase 5 final decision")
        _emit_status(status_callback, "Fase 5/6: decidiendo respuesta final...")
        decision_result = modules["decidir_respuesta_final"](
            resultado_qwen=classification,
            razonamientos_opciones=razonamientos_opciones,
            idioma=language,
        )

        print("[backend][cropear] Phase 6 visual judge")
        _emit_status(status_callback, "Fase 6/6: revisando con juez visual final...")
        judge_result = modules["juzgar_respuesta_final"](
            resultado_qwen=classification,
            razonamientos_opciones=razonamientos_opciones,
            decision_final=decision_result.get("decision_final"),
            imagen_base=image_base,
            idioma=language,
        )

        decision = decision_result.get("decision_final") or {}
        judge = judge_result.get("respuesta_juez") or {}
        print("[backend][cropear] decision_final:", decision.get("answer") or decision.get("final_answer"))
        print("[backend][cropear] juez_visual:", judge.get("final_answer") or judge.get("answer"))
        option_justifications = _format_option_justifications(
            razonamientos_opciones,
            classification.get("options_text") or {},
            crop_images,
        )
        final_answer = _notebook_pipeline_answer(decision, judge)
        final_reasoning = str(
            judge.get("final_reasoning")
            or judge.get("reasoning")
            or decision.get("reasoning")
            or "No se genero justificacion final."
        ).strip()

        return {
            "ok": True,
            "model": f"{VISION_MODEL} + {TEXT_MODEL}",
            "language": language,
            "statement": classification.get("statement_text") or "",
            "classification": _classification_summary(classification),
            "options_text": classification.get("options_text") or {},
            "visual_grounding": _visual_summary(classification, bad_crops),
            "final_answer": final_answer,
            "summary": final_reasoning,
            "steps": _steps_from_pipeline(plan_limpio, decision, judge),
            "json_valid": bool(decision.get("parse_ok")) and bool(judge.get("parse_ok")),
            "option_justifications": option_justifications,
            "judge_warnings": [],
            "crop_images": crop_images,
            "annotated_crops_image": annotated_crops_image,
            "ocr_sections_image": ocr_sections_image,
            "bad_crops": bad_crops,
            "pipeline_trace": {
                "ocr": _serializable_ocr_trace(ocr_result),
                "cot": {
                    "tipo": cot_result.get("tipo"),
                    "plan_resolucion": plan_resolucion,
                    "plan_limpio": plan_limpio,
                    "error": cot_result.get("error"),
                },
                "decision_final": decision,
                "juez_visual": judge,
            },
        }

    def _format_direct_result(
        self,
        *,
        language: str,
        classification: dict[str, Any],
        ocr_result: dict[str, Any],
        crop_images: dict[str, Any],
        annotated_crops_image: str | None,
        ocr_sections_image: str | None,
        bad_crops: list[str],
        cot_result: dict[str, Any],
    ) -> dict[str, Any]:
        direct = cot_result.get("respuesta_directa") or {}
        final_answer = direct.get("final_answer") or direct.get("answer") or "Respuesta no determinada"
        option_justifications = _format_direct_option_justifications(
            direct.get("options_analysis") or {},
            final_answer,
            classification.get("options_text") or {},
            crop_images,
        )
        reasoning = direct.get("reasoning") or "No se genero razonamiento textual directo."
        return {
            "ok": True,
            "model": TEXT_MODEL,
            "language": language,
            "statement": classification.get("statement_text") or "",
            "classification": _classification_summary(classification),
            "options_text": classification.get("options_text") or {},
            "visual_grounding": _visual_summary(classification, bad_crops),
            "final_answer": final_answer,
            "summary": reasoning,
            "steps": [reasoning],
            "json_valid": bool(direct.get("parse_ok")),
            "option_justifications": option_justifications,
            "crop_images": crop_images,
            "annotated_crops_image": annotated_crops_image,
            "ocr_sections_image": ocr_sections_image,
            "bad_crops": bad_crops,
            "pipeline_trace": {
                "ocr": _serializable_ocr_trace(ocr_result),
                "cot": {
                    "tipo": cot_result.get("tipo"),
                    "resuelto_directo": True,
                    "respuesta_directa": direct,
                    "error": cot_result.get("error"),
                },
            },
        }

    def _load_modules(self) -> dict[str, Any]:
        if not self.pipeline_dir.exists():
            raise CropearPipelineError(f"No existe la carpeta pipelinefin: {self.pipeline_dir}")

        path_text = str(self.pipeline_dir)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)

        try:
            from cot import ejecutar_cot
            from decision_final import decidir_respuesta_final
            from idiomas import normalizar_idioma
            from juez_visual import juzgar_respuesta_final
            from paddleocr import PaddleOCR
            from pipeline_funcion import (
                OCR_PIPE,
                abrir_imagen_desde_bytes,
                crear_prompt_visual,
                descargar_modelos_ollama_excepto,
                imagen_bytes_a_base64,
                liberar_ocr,
                limpiar_salida_qwen,
                llamar_modelo_visual,
                obtener_ocr,
            )
            from verificacion_opciones import generar_razonamientos_opciones
            from verificador_ocr import verificador_ocr
        except Exception as exc:
            raise CropearPipelineError(f"No se pudieron cargar los modulos de pipelinefin: {exc}") from exc

        return {
            "OCR_PIPE": OCR_PIPE,
            "PaddleOCR": PaddleOCR,
            "abrir_imagen_desde_bytes": abrir_imagen_desde_bytes,
            "crear_prompt_visual": crear_prompt_visual,
            "decidir_respuesta_final": decidir_respuesta_final,
            "descargar_modelos_ollama_excepto": descargar_modelos_ollama_excepto,
            "ejecutar_cot": ejecutar_cot,
            "generar_razonamientos_opciones": generar_razonamientos_opciones,
            "imagen_bytes_a_base64": imagen_bytes_a_base64,
            "juzgar_respuesta_final": juzgar_respuesta_final,
            "liberar_ocr": liberar_ocr,
            "limpiar_salida_qwen": limpiar_salida_qwen,
            "llamar_modelo_visual": llamar_modelo_visual,
            "normalizar_idioma": normalizar_idioma,
            "obtener_ocr": obtener_ocr,
            "verificador_ocr": verificador_ocr,
        }

    def _dependency_status(self) -> dict[str, bool]:
        if str(self.pipeline_dir) not in sys.path:
            sys.path.insert(0, str(self.pipeline_dir))
        modules = (
            "ollama",
            "paddleocr",
            "pandas",
            "cv2",
            "numpy",
            "PIL",
            "pipeline_funcion",
            "cot",
            "verificacion_opciones",
            "decision_final",
            "juez_visual",
            "verificador_ocr",
        )
        return {module: importlib.util.find_spec(module) is not None for module in modules}

    def _ollama_status(self) -> dict[str, Any]:
        try:
            response = requests.get(f"{self.ollama_base_url.rstrip('/')}/api/tags", timeout=8)
            response.raise_for_status()
        except requests.RequestException as exc:
            return {
                "running": False,
                "message": f"No se pudo conectar con Ollama: {exc}",
                "required_models": [VISION_MODEL, TEXT_MODEL],
            }

        installed = [
            item.get("name", "")
            for item in response.json().get("models", [])
            if item.get("name")
        ]
        missing = [model for model in (VISION_MODEL, TEXT_MODEL) if model not in installed]
        return {
            "running": True,
            "installed_models": installed,
            "required_models": [VISION_MODEL, TEXT_MODEL],
            "missing_models": missing,
            "message": "Modelos CROPEAR disponibles." if not missing else f"Faltan modelos: {', '.join(missing)}",
        }


def _pil_to_data_url(image: Any) -> str | None:
    if not isinstance(image, Image.Image):
        return None
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{payload}"


def _serialize_crop_images(recortes: dict[str, Any], colores: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for label in ("enunciado", *OPTIONS):
        image = recortes.get(label) if isinstance(recortes, dict) else None
        output[label] = {
            "available": isinstance(image, Image.Image),
            "url": _pil_to_data_url(image),
            "color": colores.get(label) if isinstance(colores, dict) else None,
        }
    return output


def _serializable_ocr_trace(ocr_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "resultado_qwen": ocr_result.get("resultado_qwen"),
        "salida_limpia": ocr_result.get("salida_limpia"),
        "colores_recortes": ocr_result.get("colores_recortes"),
    }


def _statement_for_editor(classification: dict[str, Any]) -> str:
    parts: list[str] = []
    statement = classification.get("statement_text")
    if statement:
        parts.append(str(statement).strip())

    options = classification.get("options_text") or {}
    option_lines = []
    for letter in OPTIONS:
        text = options.get(letter)
        if text:
            option_lines.append(f"{letter}) {text}")
    if option_lines:
        parts.append("\n".join(option_lines))
    return "\n\n".join(parts)


def _classification_summary(classification: dict[str, Any]) -> dict[str, Any]:
    return {
        "statement_type": classification.get("statement_type"),
        "options_type": classification.get("options_type"),
        "statement_text": classification.get("statement_text"),
    }


def _visual_summary(
    classification: dict[str, Any],
    bad_crops: list[str],
) -> str:
    statement_type = classification.get("statement_type") or "?"
    options_type = classification.get("options_type") or "?"
    parts = [f"Clasificacion CROPEAR: enunciado {statement_type}, opciones {options_type}."]
    if bad_crops:
        parts.append("Recortes marcados para usar imagen completa: " + ", ".join(bad_crops) + ".")
    else:
        parts.append("El verificador no marco recortes problematicos.")
    return " ".join(parts)


def _steps_from_pipeline(plan: dict[str, Any], decision: dict[str, Any], judge: dict[str, Any]) -> list[str]:
    steps: list[str] = []
    summary = str(plan.get("problem_summary") or "").strip()
    if summary:
        steps.append(summary)
    for key in ("axioms_or_rules", "statement_analysis_plan", "option_verification_plan"):
        for item in plan.get(key) or []:
            text = str(item).strip()
            if text:
                steps.append(text)
    if decision.get("reasoning"):
        steps.append(str(decision["reasoning"]).strip())
    if judge.get("final_reasoning"):
        steps.append(str(judge["final_reasoning"]).strip())
    return steps or ["El pipeline no devolvio pasos parseables."]


def _format_option_justifications(
    razonamientos_opciones: list[dict[str, Any]],
    options_text: dict[str, Any],
    crop_images: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for item in razonamientos_opciones or []:
        model_response = item.get("respuesta_modelo") or {}
        letter = item.get("opcion") or model_response.get("option")
        if letter not in OPTIONS:
            continue
        crop = crop_images.get(letter) or {}
        output.append(
            {
                "option": letter,
                "status": model_response.get("status") or "uncertain",
                "reasoning": model_response.get("reasoning") or "Sin justificacion parseable.",
                "checks": model_response.get("checks") or [],
                "visual_observations": model_response.get("visual_observations") or [],
                "statement_visual_observations": model_response.get("statement_visual_observations") or [],
                "option_visual_observations": model_response.get("option_visual_observations") or [],
                "option_value": model_response.get("option_value"),
                "option_text": options_text.get(letter),
                "image_source": item.get("imagenes_usadas") or [],
                "crop_url": crop.get("url"),
                "crop_available": bool(crop.get("available")),
                "parse_ok": bool(model_response.get("parse_ok")),
                "error": item.get("error") or model_response.get("error"),
            }
        )
    return output


def _format_direct_option_justifications(
    options_analysis: dict[str, Any],
    final_answer: str,
    options_text: dict[str, Any],
    crop_images: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_final = str(final_answer or "").strip().upper()[:1]
    output = []
    for letter in OPTIONS:
        crop = crop_images.get(letter) or {}
        reasoning = str(options_analysis.get(letter) or "").strip()
        status = "correct" if letter == normalized_final else "incorrect"
        if not reasoning:
            status = "uncertain"
            reasoning = "No se genero analisis especifico para esta opcion."
        output.append(
            {
                "option": letter,
                "status": status,
                "reasoning": reasoning,
                "checks": [],
                "visual_observations": [],
                "option_text": options_text.get(letter),
                "image_source": [],
                "crop_url": crop.get("url"),
                "crop_available": bool(crop.get("available")),
                "parse_ok": bool(reasoning),
            }
        )
    return output


def _notebook_pipeline_answer(decision_final: dict[str, Any], respuesta_juez: dict[str, Any]) -> str:
    respuesta_pipeline = None

    if isinstance(respuesta_juez, dict):
        respuesta_pipeline = respuesta_juez.get("final_answer") or respuesta_juez.get("answer")

    if respuesta_pipeline is None and isinstance(decision_final, dict):
        respuesta_pipeline = decision_final.get("answer") or decision_final.get("final_answer")

    return respuesta_pipeline or "Respuesta no determinada"
