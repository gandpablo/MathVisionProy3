import ast
import json
import re


OPCIONES_VALIDAS = ("A", "B", "C", "D", "E")


def limpiar_texto_modelo(respuesta):
    texto = "" if respuesta is None else str(respuesta).strip()
    texto = re.sub(
        r"<think>.*?</think>",
        "",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    texto = re.sub(r"^```(?:json)?", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"```$", "", texto).strip()
    return texto.replace("```json", "").replace("```", "").strip()


def normalizar_json_like(texto):
    texto = str(texto).strip()
    texto = re.sub(r"\bNone\b", "null", texto)
    texto = re.sub(r"\bTrue\b", "true", texto)
    texto = re.sub(r"\bFalse\b", "false", texto)
    texto = re.sub(r",\s*([}\]])", r"\1", texto)
    return texto


def extraer_segmento_balanceado(texto, apertura="{", cierre="}"):
    inicio = texto.find(apertura)

    if inicio == -1:
        return None

    profundidad = 0
    en_string = False
    escape = False
    comilla = None

    for i, caracter in enumerate(texto[inicio:], start=inicio):
        if en_string:
            if escape:
                escape = False
            elif caracter == "\\":
                escape = True
            elif caracter == comilla:
                en_string = False
            continue

        if caracter in {'"', "'"}:
            en_string = True
            comilla = caracter
            continue

        if caracter == apertura:
            profundidad += 1
        elif caracter == cierre:
            profundidad -= 1

            if profundidad == 0:
                return texto[inicio:i + 1]

    return None


def candidatos_json(texto):
    texto = limpiar_texto_modelo(texto)
    candidatos = [texto]

    for apertura, cierre in (("{", "}"), ("[", "]")):
        segmento = extraer_segmento_balanceado(texto, apertura, cierre)
        if segmento and segmento not in candidatos:
            candidatos.append(segmento)

        inicio = texto.find(apertura)
        fin = texto.rfind(cierre)
        if inicio != -1 and fin != -1 and fin > inicio:
            segmento_amplio = texto[inicio:fin + 1]
            if segmento_amplio not in candidatos:
                candidatos.append(segmento_amplio)

    return candidatos


def parsear_json_modelo(respuesta, default=None):
    for candidato in candidatos_json(respuesta):
        normalizado = normalizar_json_like(candidato)

        for texto in (normalizado, candidato):
            try:
                return json.loads(texto)
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                return ast.literal_eval(texto)
            except (ValueError, SyntaxError, TypeError):
                pass

    return default


def asegurar_lista_texto(valor):
    if valor is None:
        return []

    if isinstance(valor, str):
        texto = valor.strip()
        return [texto] if texto else []

    if isinstance(valor, (list, tuple, set)):
        salida = []
        for item in valor:
            if item is None:
                continue
            texto = str(item).strip()
            if texto:
                salida.append(texto)
        return salida

    texto = str(valor).strip()
    return [texto] if texto else []


def normalizar_opcion(valor):
    if valor is None:
        return None

    texto = str(valor).strip().upper()

    if texto in {"A/B/C/D/E", "A|B|C|D|E"}:
        return None

    if re.fullmatch(r"[A-E](?:\s*[/|]\s*[A-E])+", texto):
        return None

    if texto in OPCIONES_VALIDAS:
        return texto

    match = re.search(r"\b([A-E])\b", texto)
    if match:
        return match.group(1)

    return None


def normalizar_status(valor):
    texto = "" if valor is None else str(valor).strip().lower()

    if texto in {"correct", "correcta", "correcto", "correcte", "true", "vrai"}:
        return "correct"

    if texto in {
        "incorrect",
        "incorrecta",
        "incorrecto",
        "incorrecte",
        "false",
        "faux",
        "fausse",
    }:
        return "incorrect"

    if texto in {
        "uncertain",
        "dudosa",
        "dudoso",
        "incierta",
        "incierto",
        "incerta",
        "incert",
        "incertaine",
        "incertain",
        "doubtful",
    }:
        return "uncertain"

    return "uncertain"


def json_legible(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def texto_corto_raw(respuesta, limite=500):
    texto = limpiar_texto_modelo(respuesta)

    if len(texto) <= limite:
        return texto

    return texto[:limite].rstrip() + "..."
