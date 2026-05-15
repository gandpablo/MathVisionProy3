import base64
import gc
import json
import os
import re
import tempfile
import textwrap
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import requests
from ollama import chat
from paddleocr import PaddleOCR
from PIL import Image, ImageDraw

from idiomas import texto_por_idioma


VISION_MODEL = "qwen2.5vl:7b"
TEXT_MODEL = "qwen2.5vl:7b"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_HOST", "http://localhost:11434"))
PADDLE_DEVICE = os.getenv("CROPEAR_PADDLE_DEVICE", "auto")
OLLAMA_KEEP_LOADED_MODELS = os.getenv("CROPEAR_KEEP_LOADED_MODELS", "")

OPCIONES = ["A", "B", "C", "D", "E"]
COLORES_RECORTES = {
    "enunciado": "blue",
    "A": "red",
    "B": "green",
    "C": "purple",
    "D": "orange",
    "E": "brown",
}
PATRON_OPCION = re.compile(
    r"(?:^|\s)([A-E])\s*[\)\.\:\-]?\s*(?=$|\s|[0-9¿A-Z])"
)

_OCR = None


def descargar_bytes_imagen_url(url):
    respuesta = requests.get(url, timeout=30)
    respuesta.raise_for_status()

    return respuesta.content


def leer_bytes_imagen_local(ruta):
    with open(ruta, "rb") as f:
        return f.read()


def obtener_bytes_imagen(ruta, local):
    if not local:
        return descargar_bytes_imagen_url(ruta)
    else:
        return leer_bytes_imagen_local(ruta)


def abrir_imagen_desde_bytes(imagen_bytes):
    return Image.open(BytesIO(imagen_bytes)).convert("RGB")


def imagen_bytes_a_base64(imagen_bytes):
    return base64.b64encode(imagen_bytes).decode("utf-8")


def mostrar_imagen_bytes(imagen_bytes, figsize=(8, 6)):
    import matplotlib.pyplot as plt

    plt.figure(figsize=figsize)
    plt.imshow(imagen_bytes)
    plt.axis("off")
    plt.show()


def leer_problema(indice, dataset_path):
    df = pd.read_csv(dataset_path)
    fila = df.iloc[indice]
    return fila


def print_margin(texto, width=80):
    print(textwrap.fill(texto, width=width))


def llamar_modelo_visual(imagen_base, prompt, model=VISION_MODEL):
    descargar_modelos_ollama_excepto(model)
    respuesta = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [imagen_base],
            }
        ],
        options={"temperature": 0, "seed": 0},
    )

    return respuesta["message"]["content"].strip()


def llamar_modelo_texto(prompt, model=TEXT_MODEL):
    descargar_modelos_ollama_excepto(model)
    respuesta = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={"temperature": 0, "seed": 0},
    )

    texto = respuesta["message"]["content"]

    return texto.strip()


def descargar_modelos_ollama_excepto(model):
    base_url = OLLAMA_BASE_URL.rstrip("/")
    modelos_a_conservar = {
        nombre.strip()
        for nombre in OLLAMA_KEEP_LOADED_MODELS.split(",")
        if nombre.strip()
    }
    modelos_a_conservar.add(model)

    try:
        response = requests.get(f"{base_url}/api/ps", timeout=8)
        response.raise_for_status()
        modelos = response.json().get("models", [])
    except Exception:
        return

    for item in modelos:
        nombre = item.get("name")
        if not nombre or nombre in modelos_a_conservar:
            continue

        try:
            requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": nombre,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": 0,
                },
                timeout=20,
            )
        except Exception:
            pass


def obtener_ocr():
    global _OCR

    if _OCR is None:
        _OCR = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device=resolver_dispositivo_paddle(),
        )

    return _OCR


def liberar_ocr():
    global _OCR

    _OCR = None
    gc.collect()
    try:
        import paddle

        if paddle.device.is_compiled_with_cuda():
            paddle.device.cuda.empty_cache()
    except Exception:
        pass


def resolver_dispositivo_paddle():
    if PADDLE_DEVICE != "auto":
        return PADDLE_DEVICE

    try:
        import paddle

        if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
            return "gpu:0"
    except Exception:
        pass

    return "cpu"


PROMPTS_VISUAL = {
    "castellano": """
Analiza la imagen de esta pregunta tipo test.

No resuelvas el problema ni indiques la respuesta correcta.

Devuelve únicamente un JSON válido con esta información:

{
  "statement_type": "A.1" or "A.2",
  "options_type": "B.1" or "B.2",
  "statement_text": "...",
  "options_text": {
    "A": "... or null",
    "B": "... or null",
    "C": "... or null",
    "D": "... or null",
    "E": "... or null"
  },
}

Criterios:

statement_text: El texto del enunciado, o null si el enunciado es solo una imagen.
options_text: Un diccionario con el texto de cada opción, o null si las opciones son solo imágenes.

- A.1: el enunciado es solo texto.
- A.2: el enunciado tiene figura relevante.
- B.1: las opciones (A,B,C,D,E) son texto, números o expresiones, no figuras.
- B.2: las opciones posibles (A, B, C, D, E) no son de texto o numericas, sino que son figuras.
- Si las opciones son B.2, pon null en todas las opciones.
- Ignora restos de otras preguntas.
- Si ves que el diccionario options_text tiene contenido, si habias puesto B.2, es B.1.
""",
    "valenciano": """
Analitza la imatge d'aquesta pregunta tipus test.

No resolgues el problema ni indiques la resposta correcta.

Retorna únicament un JSON vàlid amb aquesta informació:

{
  "statement_type": "A.1" or "A.2",
  "options_type": "B.1" or "B.2",
  "statement_text": "...",
  "options_text": {
    "A": "... or null",
    "B": "... or null",
    "C": "... or null",
    "D": "... or null",
    "E": "... or null"
  },
}

Criteris:

statement_text: El text de l'enunciat, o null si l'enunciat és només una imatge.
options_text: Un diccionari amb el text de cada opció, o null si les opcions són només imatges.

- A.1: l'enunciat és només text.
- A.2: l'enunciat té una figura rellevant.
- B.1: les opcions (A,B,C,D,E) són text, nombres o expressions, no figures.
- B.2: les opcions possibles (A, B, C, D, E) no són de text ni numèriques, sinó figures.
- Si les opcions són B.2, posa null en totes les opcions.
- Ignora restes d'altres preguntes.
- Si veus que el diccionari options_text té contingut i havies posat B.2, aleshores és B.1.
""",
    "ingles": """
Analyze the image of this multiple-choice question.

Do not solve the problem or state the correct answer.

Return only a valid JSON object with this information:

{
  "statement_type": "A.1" or "A.2",
  "options_type": "B.1" or "B.2",
  "statement_text": "...",
  "options_text": {
    "A": "... or null",
    "B": "... or null",
    "C": "... or null",
    "D": "... or null",
    "E": "... or null"
  },
}

Criteria:

statement_text: The text of the statement, or null if the statement is only an image.
options_text: A dictionary with the text of each option, or null if the options are only images.

- A.1: the statement is text only.
- A.2: the statement has a relevant figure.
- B.1: the options (A,B,C,D,E) are text, numbers, or expressions, not figures.
- B.2: the possible options (A, B, C, D, E) are not text or numeric; they are figures.
- If the options are B.2, set every option to null.
- Ignore remains of other questions.
- If you see content in the options_text dictionary and you had selected B.2, then it is B.1.
""",
    "frances": """
Analyse l'image de cette question à choix multiple.

Ne résous pas le problème et n'indique pas la bonne réponse.

Renvoie uniquement un objet JSON valide avec ces informations:

{
  "statement_type": "A.1" or "A.2",
  "options_type": "B.1" or "B.2",
  "statement_text": "...",
  "options_text": {
    "A": "... or null",
    "B": "... or null",
    "C": "... or null",
    "D": "... or null",
    "E": "... or null"
  },
}

Critères:

statement_text: Le texte de l'énoncé, ou null si l'énoncé est seulement une image.
options_text: Un dictionnaire avec le texte de chaque option, ou null si les options sont seulement des images.

- A.1: l'énoncé est uniquement textuel.
- A.2: l'énoncé contient une figure pertinente.
- B.1: les options (A,B,C,D,E) sont du texte, des nombres ou des expressions, pas des figures.
- B.2: les options possibles (A, B, C, D, E) ne sont pas textuelles ni numériques, mais des figures.
- Si les options sont B.2, mets null dans toutes les options.
- Ignore les restes d'autres questions.
- Si tu vois que le dictionnaire options_text contient du contenu alors que tu avais mis B.2, c'est B.1.
""",
}

PROMPT_VISUAL = PROMPTS_VISUAL["castellano"]


def crear_prompt_visual(idioma="castellano"):
    return texto_por_idioma(PROMPTS_VISUAL, idioma).strip()


def limpiar_salida_qwen(respuesta):
    """
    Limpia la salida de Qwen y devuelve siempre un diccionario Python válido.

    Espera algo parecido a:
    {
      "statement_type": "A.1" / "A.2",
      "options_type": "B.1" / "B.2",
      "statement_text": "...",
      "options_text": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "...",
        "E": "..."
      }
    }
    """

    if respuesta is None:
        return None

    texto = str(respuesta).strip()

    # Quitar bloques markdown tipo ```json ... ```
    texto = re.sub(r"^```(?:json)?", "", texto.strip(), flags=re.IGNORECASE).strip()
    texto = re.sub(r"```$", "", texto.strip()).strip()

    # Extraer solo el primer JSON si hay texto antes/después
    inicio = texto.find("{")
    fin = texto.rfind("}")

    if inicio == -1 or fin == -1:
        return None

    texto_json = texto[inicio:fin + 1]

    # Normalizaciones típicas
    texto_json = texto_json.replace("None", "null")
    texto_json = texto_json.replace("True", "true")
    texto_json = texto_json.replace("False", "false")

    try:
        data = json.loads(texto_json)
    except json.JSONDecodeError:
        return None

    # Estructura base segura
    salida = {
        "statement_type": data.get("statement_type"),
        "options_type": data.get("options_type"),
        "statement_text": data.get("statement_text"),
        "options_text": {
            "A": None,
            "B": None,
            "C": None,
            "D": None,
            "E": None,
        }
    }

    # Normalizar tipos
    if salida["statement_type"] not in {"A.1", "A.2"}:
        salida["statement_type"] = None

    if salida["options_type"] not in {"B.1", "B.2"}:
        salida["options_type"] = None

    # Normalizar texto del enunciado
    if isinstance(salida["statement_text"], str):
        salida["statement_text"] = salida["statement_text"].strip()
        if salida["statement_text"].lower() in {"", "null", "none"}:
            salida["statement_text"] = None

    # Normalizar opciones
    opciones = data.get("options_text", {})

    if isinstance(opciones, dict):
        for letra in ["A", "B", "C", "D", "E"]:
            valor = opciones.get(letra)

            if isinstance(valor, str):
                valor = valor.strip()
                if valor.lower() in {"", "null", "none", "... or null"}:
                    valor = None

            salida["options_text"][letra] = valor

    # Regla: si options_type es B.2, las opciones deben ser null
    if salida["options_type"] == "B.2":
        salida["options_text"] = {
            "A": None,
            "B": None,
            "C": None,
            "D": None,
            "E": None,
        }

    # Regla extra: si hay texto real en opciones, debe ser B.1
    hay_texto_opciones = any(
        salida["options_text"][letra] is not None
        for letra in ["A", "B", "C", "D", "E"]
    )

    if hay_texto_opciones:
        salida["options_type"] = "B.1"

    return salida


def convertir_box(box):
    box = np.array(box)

    if box.ndim == 1 and len(box) == 4:
        x1, y1, x2, y2 = box
        return int(x1), int(y1), int(x2), int(y2)

    xs = box[:, 0]
    ys = box[:, 1]

    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def extraer_cuadros_texto(resultado_ocr):
    cuadros = []

    for r in resultado_ocr:
        try:
            res = r["res"]
        except KeyError:
            res = r

        textos = res["rec_texts"]
        scores = res["rec_scores"]
        boxes = res["rec_boxes"]

        for texto, score, box in zip(textos, scores, boxes):
            texto = texto.strip()

            if texto == "":
                continue

            x1, y1, x2, y2 = convertir_box(box)

            cuadros.append({
                "texto": texto,
                "score": float(score),
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            })

    return cuadros


def ejecutar_ocr_imagen_pil(ocr, imagen_pil):
    imagen_np = np.array(imagen_pil)

    try:
        return ocr.predict(imagen_np)
    except Exception:
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            imagen_pil.save(f.name)
            return ocr.predict(f.name)


def unir_bloques(bloques):
    if not bloques:
        return None

    bloques = sorted(bloques, key=lambda b: (b["y1"], b["x1"]))
    return {
        "texto": " ".join(b["texto"].strip() for b in bloques),
        "score": sum(b.get("score", 1) for b in bloques) / len(bloques),
        "x1": min(b["x1"] for b in bloques),
        "y1": min(b["y1"] for b in bloques),
        "x2": max(b["x2"] for b in bloques),
        "y2": max(b["y2"] for b in bloques),
    }


def normalizar_texto_opcion(txt):
    txt = str(txt).strip().upper()
    txt = txt.replace("Α", "A").replace("Β", "B")
    return txt


def letras_opcion_en_bloque(b):
    txt = normalizar_texto_opcion(b["texto"])

    letras = []

    # Caso claro: A), B., C:
    letras += re.findall(r"\b([A-E])\s*[\)\.\:\-]", txt)

    # Caso OCR detecta solo "A"
    if txt in OPCIONES:
        letras.append(txt)

    # Caso varios tokens: "A B C D E"
    tokens = re.findall(r"\b[A-E]\b", txt)
    if len(tokens) >= 1:
        letras += tokens

    # Quitar duplicados manteniendo orden
    res = []
    for l in letras:
        if l not in res:
            res.append(l)

    return res


def es_bloque_opcion(b):
    return len(letras_opcion_en_bloque(b)) > 0


def limpiar_ocr_por_tipo(qwen_json, cuadros_texto, margen_y=80):
    st = qwen_json.get("statement_type")
    ot = qwen_json.get("options_type")

    cuadros = sorted(cuadros_texto, key=lambda b: (b["y1"], b["x1"]))

    bloques_opciones = [b for b in cuadros if es_bloque_opcion(b)]
    y_opciones = min([b["y1"] for b in bloques_opciones], default=None)

    candidatos_enunciado = []

    for b in cuadros:
        txt = str(b["texto"]).strip()

        if es_bloque_opcion(b):
            continue

        if y_opciones is not None and b["y1"] >= y_opciones - margen_y:
            continue

        if len(txt) < 8 and not re.search(r"[¿?.,]", txt):
            continue

        candidatos_enunciado.append(b)

    bloque_enunciado = unir_bloques(candidatos_enunciado)

    if st == "A.1":
        secciones_enunciado = "no apply"
    else:
        secciones_enunciado = [bloque_enunciado] if bloque_enunciado else []

    if ot == "B.1":
        secciones_opciones = "no apply"
    else:
        opciones_detectadas = []

        for b in bloques_opciones:
            letras = letras_opcion_en_bloque(b)

            for letra in letras:
                opciones_detectadas.append({
                    "opcion": letra,
                    "score": float(b.get("score", 1)),
                    "x1": int(b["x1"]),
                    "y1": int(b["y1"]),
                    "x2": int(b["x2"]),
                    "y2": int(b["y2"]),
                })

        # Si hay duplicados, quedarse con la caja más fiable
        mejor_por_opcion = {}

        for op in opciones_detectadas:
            letra = op["opcion"]

            if letra not in mejor_por_opcion:
                mejor_por_opcion[letra] = op
                continue

            actual = mejor_por_opcion[letra]

            mejor_score = op["score"] > actual["score"]
            caja_mas_pequena = (
                (op["x2"] - op["x1"]) * (op["y2"] - op["y1"])
                <
                (actual["x2"] - actual["x1"]) * (actual["y2"] - actual["y1"])
            )

            if mejor_score or caja_mas_pequena:
                mejor_por_opcion[letra] = op

        secciones_opciones = [
            mejor_por_opcion[l]
            for l in OPCIONES
            if l in mejor_por_opcion
        ]

    return {
        "secciones_enunciado": secciones_enunciado,
        "secciones_opciones": secciones_opciones
    }


def preparar_bboxes_colores(json_ocr, colores=None):
    """
    Recibe un JSON OCR dividido por secciones y devuelve:
    {
        (x1, y1, x2, y2): color,
        ...
    }

    Ignora secciones con valor "no apply", None o listas vacías.
    """

    if colores is None:
        colores = {
            "secciones_enunciado": "red",
            "secciones_opciones": "blue",
        }

    bboxes = {}

    for seccion, elementos in json_ocr.items():

        if elementos is None:
            continue

        if isinstance(elementos, str) and elementos.lower().strip() == "no apply":
            continue

        if not isinstance(elementos, list):
            continue

        color = colores.get(seccion, "yellow")

        for elem in elementos:
            try:
                box = (
                    int(elem["x1"]),
                    int(elem["y1"]),
                    int(elem["x2"]),
                    int(elem["y2"]),
                )
                bboxes[box] = color
            except KeyError:
                continue

    return bboxes


def dibujar_bboxes_en_imagen(imagen, bboxes_colores, colores=None, grosor=4):
    """
    Recibe imagen en bytes y JSON OCR.
    Devuelve una PIL.Image con los rectángulos dibujados encima.
    """
    draw = ImageDraw.Draw(imagen)

    for (x1, y1, x2, y2), color in bboxes_colores.items():
        for i in range(grosor):
            draw.rectangle(
                [x1 - i, y1 - i, x2 + i, y2 + i],
                outline=color
            )

    return imagen


def es_no_apply(valor):
    return isinstance(valor, str) and valor.lower().strip() == "no apply"


def copiar_box(c):
    return {
        "x1": int(c["x1"]),
        "y1": int(c["y1"]),
        "x2": int(c["x2"]),
        "y2": int(c["y2"]),
    }


def box_a_tuple(b):
    return int(b["x1"]), int(b["y1"]), int(b["x2"]), int(b["y2"])


def tuple_a_box(t):
    x1, y1, x2, y2 = t
    return {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}


def clip_box(b, w, h):
    return {
        "x1": max(0, min(int(b["x1"]), w - 1)),
        "y1": max(0, min(int(b["y1"]), h - 1)),
        "x2": max(0, min(int(b["x2"]), w)),
        "y2": max(0, min(int(b["y2"]), h)),
    }


def escala_recorte(imagen_pil):
    w, h = imagen_pil.size
    escala = min(w / 1446, h / 580)
    return max(0.35, min(1.5, escala))


def escalar_recorte(valor, escala, minimo=1):
    return max(minimo, int(round(valor * escala)))


def expandir_box(b, margen, w, h):
    return clip_box({
        "x1": b["x1"] - margen,
        "y1": b["y1"] - margen,
        "x2": b["x2"] + margen,
        "y2": b["y2"] + margen,
    }, w, h)


def area_box(b):
    return max(0, b["x2"] - b["x1"]) * max(0, b["y2"] - b["y1"])


def centro_box(b):
    return (b["x1"] + b["x2"]) / 2, (b["y1"] + b["y2"]) / 2


def interseccion_area(a, b):
    x1 = max(a["x1"], b["x1"])
    y1 = max(a["y1"], b["y1"])
    x2 = min(a["x2"], b["x2"])
    y2 = min(a["y2"], b["y2"])

    if x2 <= x1 or y2 <= y1:
        return 0

    return (x2 - x1) * (y2 - y1)


def ratio_solape(a, b):
    inter = interseccion_area(a, b)
    menor = min(area_box(a), area_box(b))

    if menor == 0:
        return 0

    return inter / menor


def unir_boxes(boxes):
    boxes = [b for b in boxes if b is not None]

    if not boxes:
        return None

    return {
        "x1": min(b["x1"] for b in boxes),
        "y1": min(b["y1"] for b in boxes),
        "x2": max(b["x2"] for b in boxes),
        "y2": max(b["y2"] for b in boxes),
    }


def distancia_manhattan(a, b):
    ax, ay = centro_box(a)
    bx, by = centro_box(b)
    return abs(ax - bx) + abs(ay - by)


def extraer_anchors_desde_cuadros(cuadros_texto):
    anchors = []

    for c in cuadros_texto:
        letras = letras_opcion_en_bloque(c)

        for letra in letras:
            box = copiar_box(c)
            box.update({
                "opcion": letra,
                "texto": c.get("texto", ""),
                "score": float(c.get("score", 1)),
            })
            anchors.append(box)

    mejor_por_opcion = {}

    for a in anchors:
        letra = a["opcion"]

        if letra not in mejor_por_opcion:
            mejor_por_opcion[letra] = a
            continue

        actual = mejor_por_opcion[letra]
        mejor_score = a["score"] > actual["score"]
        caja_mas_pequena = area_box(a) < area_box(actual)

        if mejor_score or caja_mas_pequena:
            mejor_por_opcion[letra] = a

    return [mejor_por_opcion[l] for l in OPCIONES if l in mejor_por_opcion]


def extraer_anchors_desde_salida_limpia(salida_limpia):
    elementos = salida_limpia.get("secciones_opciones")

    if elementos is None or es_no_apply(elementos) or not isinstance(elementos, list):
        return []

    anchors = []

    for elem in elementos:
        if "opcion" not in elem:
            continue

        box = copiar_box(elem)
        box.update({
            "opcion": elem["opcion"],
            "texto": elem.get("texto", f"{elem['opcion']})"),
            "score": float(elem.get("score", 1)),
        })
        anchors.append(box)

    return sorted(anchors, key=lambda a: (a["y1"], a["x1"]))


def borrar_box_en_mask(mask, box, origen_x, origen_y, pad=10):
    x1 = max(0, box["x1"] - origen_x - pad)
    y1 = max(0, box["y1"] - origen_y - pad)
    x2 = min(mask.shape[1], box["x2"] - origen_x + pad)
    y2 = min(mask.shape[0], box["y2"] - origen_y + pad)

    if x2 > x1 and y2 > y1:
        mask[y1:y2, x1:x2] = False


def componentes_en_region(imagen_pil, region, boxes_borrar=None, threshold=245, kernel_size=5, iterations=2, min_area=200):
    img = np.array(imagen_pil)
    h, w = img.shape[:2]
    region = clip_box(region, w, h)

    x1, y1, x2, y2 = region["x1"], region["y1"], region["x2"], region["y2"]

    if x2 <= x1 or y2 <= y1:
        return [], region, None

    crop = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)

    # Pixeles no blancos. Es simple y funciona bien para lineas negras/grises.
    mask = gray < threshold

    for b in boxes_borrar or []:
        borrar_box_en_mask(mask, b, x1, y1, pad=10)

    mask_uint8 = mask.astype(np.uint8) * 255
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    mask_uint8 = cv2.dilate(mask_uint8, kernel, iterations=iterations)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_uint8, 8)
    componentes = []

    for i in range(1, num_labels):
        cx, cy, cw, ch, area = stats[i]

        if area < min_area:
            continue

        comp = {
            "x1": int(x1 + cx),
            "y1": int(y1 + cy),
            "x2": int(x1 + cx + cw),
            "y2": int(y1 + cy + ch),
            "area": int(area),
        }
        componentes.append(comp)

    componentes = sorted(componentes, key=lambda c: c["area"], reverse=True)
    return componentes, region, mask_uint8


def filtrar_componentes_por_bloqueos(componentes, boxes_bloqueadas, max_solape=0.35):
    filtrados = []

    for comp in componentes:
        toca_bloqueo = any(ratio_solape(comp, b) > max_solape for b in boxes_bloqueadas or [])

        if not toca_bloqueo:
            filtrados.append(comp)

    return filtrados


def cajas_texto_enunciado_para_borrar(cuadros_texto, anchors_opciones_todos):
    y_opciones_min = min([a["y1"] for a in anchors_opciones_todos], default=None)
    cajas = []

    for c in cuadros_texto:
        if es_bloque_opcion(c):
            continue

        texto = str(c.get("texto", "")).strip()

        # Evita borrar letras/numeros internos pequeños de una figura.
        if len(texto) <= 3 and not re.search(r"[¿?.,;:]", texto):
            continue

        if y_opciones_min is not None and c["y1"] >= y_opciones_min - 20:
            continue

        cajas.append(copiar_box(c))

    return cajas


def calcular_region_enunciado(imagen_pil, cuadros_texto, anchors_opciones_todos, cajas_texto_enunciado):
    w, h = imagen_pil.size
    y_opciones_min = min([a["y1"] for a in anchors_opciones_todos], default=None)
    base = unir_boxes(cajas_texto_enunciado)

    if base is None:
        y1 = 0
        y2 = y_opciones_min - 20 if y_opciones_min is not None else int(h * 0.65)
    else:
        y1 = max(0, base["y1"] - 45)
        y2 = y_opciones_min - 20 if y_opciones_min is not None else min(h, base["y2"] + 320)

    if y2 <= y1 + 20:
        y2 = min(h, y1 + 280)

    return clip_box({"x1": 0, "y1": y1, "x2": w, "y2": y2}, w, h)


def detectar_bbox_figura_enunciado(
    imagen_pil,
    cuadros_texto,
    anchors_opciones_todos,
    necesita_figura_enunciado,
    margen=25,
):
    if not necesita_figura_enunciado:
        return None

    w, h = imagen_pil.size
    cajas_borrar = cajas_texto_enunciado_para_borrar(cuadros_texto, anchors_opciones_todos)
    region = calcular_region_enunciado(imagen_pil, cuadros_texto, anchors_opciones_todos, cajas_borrar)

    boxes_borrar = cajas_borrar + anchors_opciones_todos
    componentes, _, _ = componentes_en_region(
        imagen_pil,
        region,
        boxes_borrar=boxes_borrar,
        threshold=245,
        kernel_size=5,
        iterations=2,
        min_area=300,
    )
    componentes = filtrar_componentes_por_bloqueos(componentes, boxes_borrar, max_solape=0.25)

    if not componentes:
        return None

    # La figura del enunciado suele ser el componente grande que queda cerca del bloque de enunciado.
    componentes = sorted(componentes, key=lambda c: c["area"], reverse=True)
    principal = componentes[0]

    # Si la figura queda partida en piezas cercanas, se unen para no recortar a medias.
    seleccionados = [principal]

    for c in componentes[1:]:
        cerca = distancia_manhattan(c, principal) < 180
        suficientemente_grande = c["area"] >= principal["area"] * 0.08

        if cerca and suficientemente_grande:
            seleccionados.append(c)

    bbox = unir_boxes(seleccionados)
    return expandir_box(bbox, margen, w, h)


def calcular_region_opcion(
    imagen_pil,
    anchor,
    anchors_opciones,
    margen_izq=None,
    arriba=None,
    ancho_max=None,
    abajo=None,
):
    w, h = imagen_pil.size
    acx, acy = centro_box(anchor)
    escala = escala_recorte(imagen_pil)
    margen_izq = escalar_recorte(40, escala, minimo=12) if margen_izq is None else margen_izq
    arriba = escalar_recorte(260, escala, minimo=85) if arriba is None else arriba
    ancho_max = escalar_recorte(330, escala, minimo=130) if ancho_max is None else ancho_max
    abajo = escalar_recorte(50, escala, minimo=14) if abajo is None else abajo

    region = {
        "x1": anchor["x1"] - margen_izq,
        "y1": anchor["y1"] - arriba,
        "x2": anchor["x1"] + ancho_max,
        "y2": anchor["y2"] + abajo,
    }

    # Si hay una opción a la derecha en la misma fila, no dejamos que el crop se meta en ella.
    mismas_fila_derecha = []

    for otro in anchors_opciones:
        if otro["opcion"] == anchor["opcion"]:
            continue

        ocx, ocy = centro_box(otro)
        misma_fila = abs(ocy - acy) < 90

        if misma_fila and ocx > acx:
            mismas_fila_derecha.append(otro)

    if mismas_fila_derecha:
        siguiente = sorted(mismas_fila_derecha, key=lambda a: a["x1"])[0]
        region["x2"] = min(region["x2"], siguiente["x1"] - 20)

    # Si hay filas arriba/abajo, cortamos por la mitad entre filas para no coger otra opción.
    filas_arriba = []
    filas_abajo = []

    for otro in anchors_opciones:
        if otro["opcion"] == anchor["opcion"]:
            continue

        _, ocy = centro_box(otro)

        if ocy < acy - 90:
            filas_arriba.append(otro)
        elif ocy > acy + 90:
            filas_abajo.append(otro)

    if filas_arriba:
        anterior = sorted(filas_arriba, key=lambda a: centro_box(a)[1], reverse=True)[0]
        _, prev_y = centro_box(anterior)
        region["y1"] = max(region["y1"], int((prev_y + acy) / 2))

    if filas_abajo:
        siguiente = sorted(filas_abajo, key=lambda a: centro_box(a)[1])[0]
        _, next_y = centro_box(siguiente)
        region["y2"] = min(region["y2"], int((acy + next_y) / 2))

    return clip_box(region, w, h)


def ajustar_region_opcion_por_texto_inferior(region, anchor, cuadros_texto, imagen_pil):
    if not cuadros_texto:
        return region

    w, h = imagen_pil.size
    escala = escala_recorte(imagen_pil)
    margen_y = escalar_recorte(10, escala, minimo=4)
    candidatos = []

    for cuadro in cuadros_texto:
        if es_bloque_opcion(cuadro):
            continue

        if cuadro["y1"] <= anchor["y2"] + margen_y:
            continue

        solape_x = min(cuadro["x2"], region["x2"]) - max(cuadro["x1"], region["x1"])
        if solape_x > 0:
            candidatos.append(cuadro)

    if candidatos:
        siguiente = sorted(candidatos, key=lambda c: c["y1"])[0]
        limite = max(anchor["y2"] + margen_y, siguiente["y1"] - margen_y)
        region = dict(region)
        region["y2"] = min(region["y2"], limite)

    return clip_box(region, w, h)


def detectar_bbox_figura_opcion(
    imagen_pil,
    anchor,
    anchors_opciones,
    cajas_texto_enunciado,
    bbox_enunciado=None,
    margen=None,
    cuadros_texto=None,
):
    w, h = imagen_pil.size
    escala = escala_recorte(imagen_pil)
    margen = escalar_recorte(25, escala, minimo=8) if margen is None else margen
    region = calcular_region_opcion(imagen_pil, anchor, anchors_opciones)
    region = ajustar_region_opcion_por_texto_inferior(region, anchor, cuadros_texto, imagen_pil)

    boxes_borrar = anchors_opciones.copy()
    boxes_bloqueadas = anchors_opciones.copy()

    # El texto del enunciado y la figura del enunciado no deben contaminar las opciones.
    boxes_borrar += cajas_texto_enunciado
    boxes_bloqueadas += cajas_texto_enunciado

    if bbox_enunciado is not None:
        boxes_borrar.append(bbox_enunciado)
        boxes_bloqueadas.append(bbox_enunciado)

    componentes, _, _ = componentes_en_region(
        imagen_pil,
        region,
        boxes_borrar=boxes_borrar,
        threshold=245,
        kernel_size=5,
        iterations=2,
        min_area=200,
    )
    componentes = filtrar_componentes_por_bloqueos(componentes, boxes_bloqueadas, max_solape=0.35)

    if not componentes:
        return None

    # Elegimos el componente grande más cercano a la letra de opción.
    componentes = sorted(componentes, key=lambda c: (-c["area"], distancia_manhattan(c, anchor)))
    principal = componentes[0]

    # Si la figura esta en varias piezas cercanas, se unen para no dejarla a medias.
    seleccionados = [principal]

    for c in componentes[1:]:
        cerca_de_principal = distancia_manhattan(c, principal) < 130
        cerca_de_anchor = distancia_manhattan(c, anchor) < 280
        suficientemente_grande = c["area"] >= principal["area"] * 0.07

        if suficientemente_grande and (cerca_de_principal or cerca_de_anchor):
            seleccionados.append(c)

    bbox = unir_boxes(seleccionados)
    return expandir_box(bbox, margen, w, h)


def construir_salida_figuras(
    bbox_enunciado,
    resultados_bbox_opciones,
    necesita_figura_enunciado,
    necesita_figuras_opciones,
):
    if necesita_figura_enunciado:
        figuras_enunciado = [bbox_enunciado] if bbox_enunciado is not None else []
    else:
        figuras_enunciado = "no apply"

    if necesita_figuras_opciones:
        figuras_opciones = []

        for letra in OPCIONES:
            bbox = resultados_bbox_opciones.get(letra)

            if bbox is None:
                continue

            item = {"opcion": letra}
            item.update(bbox)
            figuras_opciones.append(item)
    else:
        figuras_opciones = "no apply"

    return {
        "figuras_enunciado": figuras_enunciado,
        "figuras_opciones": figuras_opciones,
    }


def dibujar_etiqueta(draw, x, y, texto, color, margen=3):
    bbox_texto = draw.textbbox((0, 0), texto)
    ancho = bbox_texto[2] - bbox_texto[0]
    alto = bbox_texto[3] - bbox_texto[1]
    y_texto = max(0, y - alto - 2 * margen - 4)

    draw.rectangle(
        [x, y_texto, x + ancho + 2 * margen, y_texto + alto + 2 * margen],
        fill=color,
    )
    draw.text((x + margen, y_texto + margen), texto, fill="white")


def dibujar_box_con_etiqueta(draw, bbox, texto, color, grosor=5):
    x1, y1, x2, y2 = box_a_tuple(bbox)
    draw.rectangle([x1, y1, x2, y2], outline=color, width=grosor)


def dibujar_secciones_ocr(imagen_pil, salida_limpia):
    imagen = imagen_pil.copy()
    colores = {
        "secciones_enunciado": "red",
        "secciones_opciones": "blue",
    }
    bboxes_colores = preparar_bboxes_colores(salida_limpia, colores=colores)
    imagen = dibujar_bboxes_en_imagen(imagen, bboxes_colores)

    return imagen


def dibujar_figura_enunciado(imagen_pil, bbox_enunciado):
    if bbox_enunciado is None:
        return None

    imagen = imagen_pil.copy()
    draw = ImageDraw.Draw(imagen)
    dibujar_box_con_etiqueta(draw, bbox_enunciado, "Figura enunciado", COLORES_RECORTES["enunciado"])
    return imagen


def dibujar_figuras_opciones(imagen_pil, resultados_bbox_opciones):
    boxes = {
        letra: bbox
        for letra, bbox in resultados_bbox_opciones.items()
        if bbox is not None
    }

    if not boxes:
        return None

    imagen = imagen_pil.copy()
    draw = ImageDraw.Draw(imagen)

    for letra, bbox in boxes.items():
        color = COLORES_RECORTES.get(letra, "red")
        dibujar_box_con_etiqueta(draw, bbox, f"Figura {letra}", color)

    return imagen


def dibujar_figuras_final(imagen_pil, bbox_enunciado, resultados_bbox_opciones):
    hay_enunciado = bbox_enunciado is not None
    hay_opciones = any(bbox is not None for bbox in resultados_bbox_opciones.values())

    if not hay_enunciado and not hay_opciones:
        return None

    imagen = imagen_pil.copy()
    draw = ImageDraw.Draw(imagen)

    if bbox_enunciado is not None:
        dibujar_box_con_etiqueta(draw, bbox_enunciado, "Figura enunciado", COLORES_RECORTES["enunciado"])

    for letra, bbox in resultados_bbox_opciones.items():
        if bbox is None:
            continue

        color = COLORES_RECORTES.get(letra, "red")
        dibujar_box_con_etiqueta(draw, bbox, f"Figura {letra}", color)

    return imagen


def recortar_box(imagen_pil, bbox):
    if bbox is None:
        return None

    w, h = imagen_pil.size
    bbox = clip_box(bbox, w, h)

    if bbox["x2"] <= bbox["x1"] or bbox["y2"] <= bbox["y1"]:
        return None

    return imagen_pil.crop((bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]))


def construir_recortes(
    imagen_pil,
    bbox_enunciado,
    resultados_bbox_opciones,
    necesita_figura_enunciado,
    necesita_figuras_opciones,
):
    recortes = {
        "enunciado": None,
        "A": None,
        "B": None,
        "C": None,
        "D": None,
        "E": None,
    }

    if necesita_figura_enunciado:
        recortes["enunciado"] = recortar_box(imagen_pil, bbox_enunciado)

    if necesita_figuras_opciones:
        for letra in OPCIONES:
            recortes[letra] = recortar_box(imagen_pil, resultados_bbox_opciones.get(letra))

    return recortes


def construir_colores_recortes(recortes):
    return {
        nombre: COLORES_RECORTES.get(nombre) if recorte is not None else None
        for nombre, recorte in recortes.items()
    }


def salida_vacia(resultado_qwen=None, salida_limpia=None):
    return {
        "resultado_qwen": resultado_qwen,
        "salida_limpia": salida_limpia,
        "imagen_bboxes_enunciado_y_opciones": None,
        "imagen_bbox_figura_enunciado": None,
        "imagen_bboxes_figuras_opciones": None,
        "imagen_bboxes_figuras_enunciado_y_opciones": None,
        "recortes": {
            "enunciado": None,
            "A": None,
            "B": None,
            "C": None,
            "D": None,
            "E": None,
        },
        "colores_recortes": {
            "enunciado": None,
            "A": None,
            "B": None,
            "C": None,
            "D": None,
            "E": None,
        },
    }


def OCR_PIPE(imagen_bytes, imagen_base, ocr, idioma="castellano"):
    """
    Ejecuta el mismo pipeline del notebook sobre una imagen ya abierta y su base64.

    Parámetros esperados:
        imagen_bytes: PIL.Image, como devuelve abrir_imagen_desde_bytes(imagen_raw)
        imagen_base: str, como devuelve imagen_bytes_a_base64(imagen_raw)
        ocr: PaddleOCR ya inicializado
        idioma: "castellano", "valenciano", "ingles" o "frances"

    Devuelve un diccionario con resultado_qwen, salida_limpia, las imágenes con
    boxes, los recortes de enunciado/opciones y sus colores.
    """

    if not isinstance(imagen_bytes, Image.Image):
        imagen_bytes = abrir_imagen_desde_bytes(imagen_bytes)
    else:
        imagen_bytes = imagen_bytes.convert("RGB")

    respuesta_vl = llamar_modelo_visual(
        imagen_base=imagen_base,
        prompt=crear_prompt_visual(idioma),
    )
    resultado_qwen = limpiar_salida_qwen(respuesta_vl)

    if resultado_qwen is None:
        return salida_vacia(resultado_qwen=None, salida_limpia=None)

    statement_type = resultado_qwen["statement_type"]
    options_type = resultado_qwen["options_type"]

    necesita_figura_enunciado = statement_type == "A.2"
    necesita_figuras_opciones = options_type == "B.2"

    if ocr is None:
        ocr = obtener_ocr()

    resultado_ocr = ejecutar_ocr_imagen_pil(ocr, imagen_bytes)
    cuadros_texto = extraer_cuadros_texto(resultado_ocr)

    salida_limpia = limpiar_ocr_por_tipo(resultado_qwen, cuadros_texto)
    imagen_bboxes_enunciado_y_opciones = dibujar_secciones_ocr(imagen_bytes, salida_limpia)

    anchors_opciones_todos = extraer_anchors_desde_cuadros(cuadros_texto)
    anchors_opciones = extraer_anchors_desde_salida_limpia(salida_limpia)

    if necesita_figuras_opciones and not anchors_opciones:
        anchors_opciones = anchors_opciones_todos

    if not necesita_figuras_opciones:
        anchors_opciones = []

    cajas_texto_enunciado = cajas_texto_enunciado_para_borrar(cuadros_texto, anchors_opciones_todos)

    bbox_enunciado = detectar_bbox_figura_enunciado(
        imagen_pil=imagen_bytes,
        cuadros_texto=cuadros_texto,
        anchors_opciones_todos=anchors_opciones_todos,
        necesita_figura_enunciado=necesita_figura_enunciado,
    )

    resultados_bbox_opciones = {letra: None for letra in OPCIONES}

    if necesita_figuras_opciones:
        for letra in OPCIONES:
            anchor = next((a for a in anchors_opciones if a["opcion"] == letra), None)

            if anchor is None:
                resultados_bbox_opciones[letra] = None
                continue

            bbox = detectar_bbox_figura_opcion(
                imagen_pil=imagen_bytes,
                anchor=anchor,
                anchors_opciones=anchors_opciones,
                cajas_texto_enunciado=cajas_texto_enunciado,
                bbox_enunciado=bbox_enunciado,
                cuadros_texto=cuadros_texto,
            )
            resultados_bbox_opciones[letra] = bbox

    construir_salida_figuras(
        bbox_enunciado,
        resultados_bbox_opciones,
        necesita_figura_enunciado,
        necesita_figuras_opciones,
    )

    imagen_bbox_figura_enunciado = dibujar_figura_enunciado(imagen_bytes, bbox_enunciado)
    imagen_bboxes_figuras_opciones = dibujar_figuras_opciones(imagen_bytes, resultados_bbox_opciones)
    imagen_bboxes_figuras_enunciado_y_opciones = dibujar_figuras_final(
        imagen_bytes,
        bbox_enunciado,
        resultados_bbox_opciones,
    )

    recortes = construir_recortes(
        imagen_bytes,
        bbox_enunciado,
        resultados_bbox_opciones,
        necesita_figura_enunciado,
        necesita_figuras_opciones,
    )
    colores_recortes = construir_colores_recortes(recortes)

    return {
        "resultado_qwen": resultado_qwen,
        "salida_limpia": salida_limpia,
        "imagen_bboxes_enunciado_y_opciones": imagen_bboxes_enunciado_y_opciones,
        "imagen_bbox_figura_enunciado": imagen_bbox_figura_enunciado,
        "imagen_bboxes_figuras_opciones": imagen_bboxes_figuras_opciones,
        "imagen_bboxes_figuras_enunciado_y_opciones": imagen_bboxes_figuras_enunciado_y_opciones,
        "recortes": recortes,
        "colores_recortes": colores_recortes,
    }
