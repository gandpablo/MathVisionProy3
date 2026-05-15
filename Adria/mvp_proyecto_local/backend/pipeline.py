from __future__ import annotations

import json
from typing import Any, Callable

from .cropear_pipeline import CropearDataPipeline
from .llm import OllamaClient, OllamaError


CHAT_PROMPT_TEMPLATE = """
/no_think
Eres el chat de MathVision AI.
Responde preguntas sobre una resolucion generada por el pipeline CROPEAR.
Se breve, educativo y claro.
Usa el contexto del problema, la clasificacion, los recortes y la justificacion por opcion.
No cambies la respuesta final salvo que el usuario detecte un error.
Si falta informacion visual, dilo.
Responde directamente; no muestres razonamiento interno.

Contexto:
{solution_context}

Pregunta:
{user_question}
""".strip()


class MathVisionPipeline:
    def __init__(self, llm: OllamaClient):
        self.llm = llm
        self.cropear = CropearDataPipeline()

    def health(self) -> dict[str, Any]:
        return self.cropear.health()

    def extract_problem_text(self, *, image_bytes: bytes, language: str = "castellano") -> dict[str, Any]:
        return self.cropear.extract_problem_text(image_bytes=image_bytes, language=language)

    def solve(
        self,
        *,
        image_bytes: bytes,
        language: str = "castellano",
        status_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        return self.cropear.solve(
            image_bytes=image_bytes,
            language=language,
            status_callback=status_callback,
        )

    def chat(
        self,
        *,
        user_question: str,
        solution_context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
        image_bytes: bytes | None = None,
    ) -> str:
        del image_bytes
        context_text = _format_solution_context(solution_context, history or [])
        prompt = CHAT_PROMPT_TEMPLATE.format(
            solution_context=context_text,
            user_question=user_question.strip(),
        )
        print("[backend][pipeline] CROPEAR chat with existing solution context")
        answer = self.llm.chat_text(prompt, temperature=0.1, num_predict=2400)
        if not answer.strip():
            print("[backend][pipeline] Empty chat response, retrying with shorter prompt")
            answer = self.llm.chat_text(
                _short_chat_prompt(solution_context, user_question),
                temperature=0.1,
                num_predict=1600,
            )
        if not answer.strip():
            print("[backend][pipeline] Empty chat response, using CROPEAR context answer")
            return _answer_from_context(user_question, solution_context)
        return answer


def _format_solution_context(solution: dict[str, Any], history: list[dict[str, str]]) -> str:
    options = []
    for item in solution.get("option_justifications", [])[:5]:
        option = item.get("option", "?")
        status = item.get("status", "uncertain")
        reason = _clip(item.get("reasoning", ""), 450)
        checks = "; ".join(_clip(check, 160) for check in item.get("checks", [])[:3])
        text = f"{option}: {status}. {reason}"
        if checks:
            text += f" Comprobaciones: {checks}"
        options.append(text)

    lines = [
        f"Enunciado: {_clip(solution.get('statement', ''), 1200)}",
        f"Clasificacion: {json.dumps(solution.get('classification', {}), ensure_ascii=False)}",
        f"Respuesta final: {_clip(solution.get('final_answer', ''), 80)}",
        f"Resumen final: {_clip(solution.get('summary', ''), 1200)}",
        f"Recortes revisados con imagen completa: {', '.join(solution.get('bad_crops', []) or []) or 'ninguno'}",
    ]

    steps = [_clip(step, 320) for step in solution.get("steps", [])[:6] if str(step).strip()]
    if steps:
        lines.append("Pasos principales:\n" + "\n".join(f"- {step}" for step in steps))
    if options:
        lines.append("Justificacion por opcion:\n" + "\n".join(f"- {item}" for item in options))

    if history:
        recent = []
        for item in history[-4:]:
            role = item.get("role", "usuario")
            content = _clip(item.get("content", ""), 260)
            recent.append(f"{role}: {content}")
        lines.append("Chat reciente:\n" + "\n".join(recent))
    return "\n\n".join(lines)


def _short_chat_prompt(solution: dict[str, Any], user_question: str) -> str:
    return f"""
/no_think
Responde en español, en 2-5 frases, usando solo este resultado CROPEAR.

Respuesta final: {_clip(solution.get('final_answer', ''), 80)}
Resumen: {_clip(solution.get('summary', ''), 900)}
Opciones: {_clip(_options_one_line(solution.get('option_justifications', [])), 900)}

Pregunta: {user_question.strip()}
""".strip()


def _answer_from_context(user_question: str, solution: dict[str, Any]) -> str:
    question = user_question.lower()
    final_answer = str(solution.get("final_answer") or "no determinada").strip()
    summary = _clip(solution.get("summary", ""), 900)
    options = solution.get("option_justifications", [])

    if "opcion" in question or "opción" in question or any(letter in question.split() for letter in ("a", "b", "c", "d", "e")):
        option_lines = []
        for item in options[:5]:
            option = item.get("option", "?")
            status = item.get("status", "uncertain")
            reason = _clip(item.get("reasoning", ""), 260)
            option_lines.append(f"{option}: {status}. {reason}")
        if option_lines:
            return "Según el análisis CROPEAR por opción:\n" + "\n".join(option_lines)

    if summary:
        return f"La respuesta final del pipeline es {final_answer}. {summary}"
    return f"La respuesta final del pipeline es {final_answer}. No hay más detalle textual disponible en el contexto guardado."


def _options_one_line(options: list[dict[str, Any]]) -> str:
    parts = []
    for item in options[:5]:
        parts.append(
            f"{item.get('option', '?')}={item.get('status', 'uncertain')}: "
            f"{_clip(item.get('reasoning', ''), 180)}"
        )
    return " | ".join(parts)


def _clip(value: Any, limit: int) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
