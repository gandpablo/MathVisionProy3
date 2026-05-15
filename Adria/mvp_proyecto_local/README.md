# MathVision AI

MVP local para resolver problemas matemáticos visuales tipo Kangaroo con el pipeline CROPEAR:
clasificación/OCR visual, recortes, verificación de recortes, CoT, verificación opción por opción,
decisión final y juez visual.

Los modelos usados por el pipeline son `qwen2.5vl:7b` para visión y `qwen3:4b` para texto.
No se entrenan modelos y no se usan APIs externas.

## Requisitos locales

Instala Ollama:

```bash
brew install ollama
```

Descarga los modelos:

```bash
ollama pull qwen2.5vl:7b
ollama pull qwen3:4b
```

Si usas la app desde terminal y Ollama no está ya corriendo, inicia Ollama en otra terminal o desde la app de Ollama.

## Entorno

```bash
/home/cguiesc/venvs/app/bin/python -m pip install -r requirements.txt
```

## Ejecutar

```bash
/home/cguiesc/venvs/app/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

También puedes usar:

```bash
./run.sh
```

`run.sh` usa el entorno `/home/cguiesc/venvs/app` por defecto y busca un puerto libre a partir de `8000`.

Abre:

```text
la URL que muestre run.sh, por ejemplo http://127.0.0.1:8001 si 8000 esta ocupado
```

## Configuración

La app usa el pipeline de `/home/cguiesc/pablo_gandia/CROPEAR/pipelinefin`.
Puedes cambiar esa ruta con:

```bash
CROPEAR_PIPELINE_DIR=/ruta/a/pipelinefin
```

URL de Ollama si no usas la predeterminada:

```bash
OLLAMA_BASE_URL=http://localhost:11434
```

## Uso

1. Elige el idioma del problema: castellano, valenciano, inglés o francés.
2. Sube `2014_Nivel1_01.jpg` o cualquier imagen del problema.
3. La app llama a `/api/ocr` para extraer enunciado/opciones con QwenVL y mostrar el texto detectado.
4. Pulsa **Resolver problema**.
5. La app llama a `/api/solve`, que ejecuta:
   - `OCR_PIPE`: clasificación A.1/A.2 y B.1/B.2, PaddleOCR, OpenCV y recortes;
   - `verificador_ocr`: marca recortes problemáticos para usar imagen completa;
   - `ejecutar_cot`: plan o resolución textual directa para A.1/B.1;
   - `generar_razonamientos_opciones`: justifica A, B, C, D y E por separado;
   - `decidir_respuesta_final`: elige respuesta con `qwen3:4b`;
   - `juzgar_respuesta_final`: revisa la respuesta con `qwen2.5vl:7b`.
6. Revisa la justificación por opción y los recortes generados.
7. Usa el chat para preguntar sobre la resolución actual.

## Endpoints

- `GET /api/health`
- `POST /api/ocr`
- `POST /api/solve`
- `POST /api/chat`

FastAPI sirve también `index.html`, `styles.css`, `app.js` y `assets/` desde la misma URL.

## Errores esperados

Si alguno de los modelos no está instalado, verás una instrucción clara:

```bash
ollama pull qwen2.5vl:7b
ollama pull qwen3:4b
```

Aunque el pipeline verifica las opciones por separado, los modelos pueden fallar en razonamiento
matemático complejo. Revisa siempre el OCR, los recortes, la respuesta y los pasos.
