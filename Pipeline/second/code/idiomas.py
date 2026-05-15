import unicodedata


IDIOMA_PREDETERMINADO = "castellano"
IDIOMAS_SOPORTADOS = ("castellano", "valenciano", "ingles", "frances")


def _normalizar_clave(texto):
    texto = "" if texto is None else str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.replace("-", "_").replace(" ", "_")


_ALIAS_IDIOMAS = {
    "castellano": "castellano",
    "espanol": "castellano",
    "es": "castellano",
    "spanish": "castellano",
    "valenciano": "valenciano",
    "valencia": "valenciano",
    "valencian": "valenciano",
    "ca": "valenciano",
    "catala": "valenciano",
    "ingles": "ingles",
    "english": "ingles",
    "en": "ingles",
    "frances": "frances",
    "french": "frances",
    "fr": "frances",
}


def normalizar_idioma(idioma):
    return _ALIAS_IDIOMAS.get(_normalizar_clave(idioma), IDIOMA_PREDETERMINADO)


def texto_por_idioma(textos, idioma):
    idioma = normalizar_idioma(idioma)
    return textos.get(idioma, textos[IDIOMA_PREDETERMINADO])


DESCRIPCIONES_STATEMENT = {
    "castellano": {
        "A.1": "enunciado solo texto",
        "A.2": "enunciado con figura relevante",
    },
    "valenciano": {
        "A.1": "enunciat només de text",
        "A.2": "enunciat amb figura rellevant",
    },
    "ingles": {
        "A.1": "text-only statement",
        "A.2": "statement with a relevant figure",
    },
    "frances": {
        "A.1": "énoncé uniquement textuel",
        "A.2": "énoncé avec une figure pertinente",
    },
}


DESCRIPCIONES_OPTIONS = {
    "castellano": {
        "B.1": "opciones textuales/numéricas",
        "B.2": "opciones con figuras",
    },
    "valenciano": {
        "B.1": "opcions textuals/numèriques",
        "B.2": "opcions amb figures",
    },
    "ingles": {
        "B.1": "textual/numeric options",
        "B.2": "options with figures",
    },
    "frances": {
        "B.1": "options textuelles/numériques",
        "B.2": "options avec des figures",
    },
}


def descripcion_statement(statement_type, idioma):
    descripciones = texto_por_idioma(DESCRIPCIONES_STATEMENT, idioma)
    return descripciones.get(statement_type, descripciones["A.2"])


def descripcion_options(options_type, idioma):
    descripciones = texto_por_idioma(DESCRIPCIONES_OPTIONS, idioma)
    return descripciones.get(options_type, descripciones["B.2"])
