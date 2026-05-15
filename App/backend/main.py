from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .cropear_pipeline import CropearPipelineError
from .llm import OllamaClient, OllamaConnectionError, OllamaError, OllamaModelMissingError
from .pipeline import MathVisionPipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="MathVision AI", version="0.1.0")
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="assets")

llm_client = OllamaClient()
pipeline = MathVisionPipeline(llm_client)
LAST_CONTEXT: dict[str, Any] = {}
PIPELINE_STATUS_LOCK = Lock()
PIPELINE_STATUS: dict[str, Any] = {
    "running": False,
    "phase": "idle",
    "message": "Esperando problema.",
    "updated_at": datetime.now(timezone.utc).isoformat(),
}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    statement: str | None = None
    visual_grounding: str | None = None
    final_answer: str | None = None
    summary: str | None = None
    steps: list[str] | None = None
    classification: dict[str, Any] | None = None
    option_justifications: list[dict[str, Any]] | None = None
    history: list[ChatMessage] = Field(default_factory=list)


@app.get("/api/health")
def health() -> dict[str, Any]:
    print("[backend][api] GET /api/health")
    ollama = llm_client.health()
    data_pipeline = pipeline.health()
    dependencies_ok = all(data_pipeline.get("dependencies", {}).values())
    missing_models = data_pipeline.get("ollama", {}).get("missing_models", [])
    ocr = {
        "available": bool(data_pipeline.get("pipeline_dir_exists") and dependencies_ok and not missing_models),
        "message": data_pipeline.get("ollama", {}).get("message", "Estado CROPEAR no disponible."),
    }
    return {
        "ok": True,
        "ocr": ocr,
        "data_pipeline": data_pipeline,
        "ollama": ollama,
        "model": llm_client.model,
    }


def _set_pipeline_status(message: str, *, phase: str = "running", running: bool = True) -> None:
    with PIPELINE_STATUS_LOCK:
        PIPELINE_STATUS.update(
            {
                "running": running,
                "phase": phase,
                "message": message,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )


def _get_pipeline_status() -> dict[str, Any]:
    with PIPELINE_STATUS_LOCK:
        return dict(PIPELINE_STATUS)


@app.get("/api/solve/status")
def solve_status() -> dict[str, Any]:
    return _get_pipeline_status()


@app.post("/api/ocr")
async def ocr_endpoint(
    file: UploadFile = File(...),
    language: str = Form("castellano"),
) -> JSONResponse:
    print(
        "[backend][api] POST /api/ocr",
        {"filename": file.filename, "content_type": file.content_type, "language": language},
    )
    image_bytes = await file.read()
    try:
        result = pipeline.extract_problem_text(image_bytes=image_bytes, language=language)
        return JSONResponse(result)
    except CropearPipelineError as exc:
        print("[backend][api] CROPEAR OCR unavailable:", exc)
        return JSONResponse(
            {
                "ok": False,
                "text": "",
                "error": str(exc),
                "install_command": pipeline.cropear.pull_command,
            },
            status_code=200,
        )
    except Exception as exc:
        print("[backend][api] OCR failed:", exc)
        return JSONResponse(
            {
                "ok": False,
                "text": "",
                "error": "No se pudo extraer el enunciado con el pipeline CROPEAR. Revisa Ollama, los modelos y la imagen.",
            },
            status_code=200,
        )


@app.post("/api/solve")
async def solve_endpoint(
    file: UploadFile = File(...),
    language: str = Form("castellano"),
) -> JSONResponse:
    global LAST_CONTEXT

    print(
        "[backend][api] POST /api/solve",
        {"filename": file.filename, "language": language},
    )
    image_bytes = await file.read()

    def report_status(message: str) -> None:
        _set_pipeline_status(message, phase="solve", running=True)

    _set_pipeline_status("Preparando pipeline CROPEAR...", phase="starting", running=True)
    try:
        result = await run_in_threadpool(
            pipeline.solve,
            image_bytes=image_bytes,
            language=language,
            status_callback=report_status,
        )
    except (OllamaConnectionError, OllamaModelMissingError) as exc:
        print("[backend][api] Solve Ollama error:", exc)
        _set_pipeline_status("Error de Ollama durante la resolucion.", phase="error", running=False)
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc),
                "model": llm_client.model,
                "install_command": llm_client.pull_command,
            },
            status_code=503,
        )
    except CropearPipelineError as exc:
        print("[backend][api] Solve CROPEAR error:", exc)
        _set_pipeline_status("Error del pipeline CROPEAR durante la resolucion.", phase="error", running=False)
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc),
                "install_command": pipeline.cropear.pull_command,
            },
            status_code=503,
        )
    except OllamaError as exc:
        print("[backend][api] Solve model error:", exc)
        _set_pipeline_status("Error del modelo durante la resolucion.", phase="error", running=False)
        return JSONResponse({"ok": False, "error": str(exc), "model": llm_client.model}, status_code=502)
    except Exception as exc:
        print("[backend][api] Solve unexpected error:", exc)
        _set_pipeline_status("Error inesperado durante la resolucion.", phase="error", running=False)
        return JSONResponse(
            {
                "ok": False,
                "error": "No se pudo resolver el problema. Revisa el OCR y que Ollama este activo.",
            },
            status_code=500,
        )

    LAST_CONTEXT = {
        **result,
        "image_bytes": image_bytes,
    }
    _set_pipeline_status("Resolucion completada.", phase="done", running=False)
    public_result = {key: value for key, value in result.items() if key != "image_bytes"}
    return JSONResponse(public_result)


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> JSONResponse:
    print("[backend][api] POST /api/chat", {"question_chars": len(request.question)})
    solution_context = _context_from_request(request)
    if not solution_context:
        return JSONResponse(
            {
                "ok": False,
                "error": "Primero resuelve un problema para que el chat tenga contexto.",
            },
            status_code=400,
        )

    image_bytes = LAST_CONTEXT.get("image_bytes")
    history = [item.dict() for item in request.history]
    try:
        answer = pipeline.chat(
            user_question=request.question,
            solution_context=solution_context,
            history=history,
            image_bytes=image_bytes,
        )
    except (OllamaConnectionError, OllamaModelMissingError) as exc:
        print("[backend][api] Chat Ollama error:", exc)
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc),
                "model": llm_client.model,
                "install_command": llm_client.pull_command,
            },
            status_code=503,
        )
    except OllamaError as exc:
        print("[backend][api] Chat model error:", exc)
        return JSONResponse({"ok": False, "error": str(exc), "model": llm_client.model}, status_code=502)

    return JSONResponse({"ok": True, "answer": answer, "model": llm_client.model})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/{path:path}")
def static_files(path: str) -> FileResponse:
    requested = (PROJECT_ROOT / path).resolve()
    allowed_suffixes = {".html", ".css", ".js", ".jpg", ".jpeg", ".png", ".webp", ".svg", ".ico"}
    if not str(requested).startswith(str(PROJECT_ROOT)) or requested.suffix.lower() not in allowed_suffixes:
        raise HTTPException(status_code=404, detail="Not found")
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(requested)


def _context_from_request(request: ChatRequest) -> dict[str, Any]:
    if request.final_answer or request.summary or request.visual_grounding or request.statement:
        return {
            "statement": request.statement or LAST_CONTEXT.get("statement", ""),
            "visual_grounding": request.visual_grounding or LAST_CONTEXT.get("visual_grounding", ""),
            "final_answer": request.final_answer or LAST_CONTEXT.get("final_answer", ""),
            "summary": request.summary or LAST_CONTEXT.get("summary", ""),
            "steps": request.steps or LAST_CONTEXT.get("steps", []),
            "classification": request.classification or LAST_CONTEXT.get("classification", {}),
            "option_justifications": request.option_justifications or LAST_CONTEXT.get("option_justifications", []),
        }

    if LAST_CONTEXT:
        return {key: value for key, value in LAST_CONTEXT.items() if key != "image_bytes"}

    return {}
