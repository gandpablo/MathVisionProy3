from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_MODEL = "qwen3:4b"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_VISION_MODEL = "qwen2.5vl:7b"


class OllamaError(RuntimeError):
    """Generic local Ollama client error."""


class OllamaConnectionError(OllamaError):
    """Raised when Ollama is not reachable."""


class OllamaModelMissingError(OllamaError):
    """Raised when the requested local model is not installed."""


@dataclass
class OllamaClient:
    model: str = DEFAULT_MODEL
    base_url: str = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

    @property
    def pull_command(self) -> str:
        return f"ollama pull {self.model}"

    def health(self) -> dict[str, Any]:
        try:
            models = self.list_models()
            running_models = self.running_models()
        except OllamaConnectionError as exc:
            return {
                "running": False,
                "model": self.model,
                "model_installed": False,
                "message": str(exc),
            }

        installed = self.model in models
        return {
            "running": True,
            "model": self.model,
            "model_installed": installed,
            "installed_models": models,
            "running_models": running_models,
            "message": "Ollama disponible." if installed else self._missing_model_message(),
        }

    def list_models(self) -> list[str]:
        url = f"{self.base_url.rstrip('/')}/api/tags"
        print("[backend][ollama] Listing models:", url)
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
        except requests.RequestException as exc:
            print("[backend][ollama] Ollama connection failed:", exc)
            raise OllamaConnectionError(
                "No se pudo conectar con Ollama en http://localhost:11434. "
                "Inicia Ollama y ejecuta: "
                f"{self.pull_command}"
            ) from exc

        payload = response.json()
        return [item.get("name", "") for item in payload.get("models", []) if item.get("name")]

    def running_models(self) -> list[str]:
        url = f"{self.base_url.rstrip('/')}/api/ps"
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
        except requests.RequestException as exc:
            print("[backend][ollama] Could not list running models:", exc)
            raise OllamaConnectionError("No se pudo consultar los modelos cargados en Ollama.") from exc

        payload = response.json()
        return [item.get("name", "") for item in payload.get("models", []) if item.get("name")]

    def unload_other_running_models(self) -> None:
        preserved_models = _preserved_ollama_models(self.model)
        for model_name in self.running_models():
            if model_name in preserved_models:
                continue
            print("[backend][ollama] Unloading non-target model:", model_name)
            url = f"{self.base_url.rstrip('/')}/api/generate"
            payload = {
                "model": model_name,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            }
            try:
                response = requests.post(url, json=payload, timeout=20)
                response.raise_for_status()
            except requests.RequestException as exc:
                print("[backend][ollama] Could not unload model:", model_name, exc)

    def ensure_model_available(self) -> None:
        models = self.list_models()
        if self.model not in models:
            print("[backend][ollama] Missing model:", self.model, "installed:", models)
            raise OllamaModelMissingError(self._missing_model_message())

    def chat_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
        num_predict: int = 260,
    ) -> str:
        message: dict[str, Any] = {"role": "user", "content": prompt}
        return self._chat(
            messages=[message],
            temperature=temperature,
            num_predict=num_predict,
        )

    def _chat(self, messages: list[dict[str, Any]], *, temperature: float, num_predict: int) -> str:
        self.unload_other_running_models()
        self.ensure_model_available()
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        print(
            "[backend][ollama] Chat request:",
            {"model": self.model, "temperature": temperature, "num_predict": num_predict, "has_image": "images" in messages[0]},
        )
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            print("[backend][ollama] Chat request failed:", exc)
            raise OllamaConnectionError(
                "Ollama no respondio correctamente. Comprueba que esta iniciado y que el modelo esta descargado: "
                f"{self.pull_command}"
            ) from exc

        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not content:
            print(
                "[backend][ollama] Empty response:",
                {
                    "done": data.get("done"),
                    "done_reason": data.get("done_reason"),
                    "eval_count": data.get("eval_count"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                },
            )
            return ""
        print("[backend][ollama] Chat response chars:", len(content))
        return content.strip()

    def _missing_model_message(self) -> str:
        return f"El modelo '{self.model}' no esta instalado. Ejecuta: {self.pull_command}"


def _preserved_ollama_models(current_model: str) -> set[str]:
    raw = os.getenv("OLLAMA_KEEP_LOADED_MODELS", "")
    preserved = {item.strip() for item in raw.split(",") if item.strip()}
    preserved.add(current_model)
    return preserved
