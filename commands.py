"""Reconocimiento de wake word y de comandos de voz.

Las frases dictadas llegan de Whisper con tildes, mayusculas y
signos de puntuacion variables, asi que todo se compara sobre
una version normalizada del texto.

Regla importante: un comando solo se reconoce cuando la frase
*entera* es ese comando. Buscar los comandos como subcadena
haria que "escribe un test para el login" se interpretase como
la orden "para".
"""

import unicodedata

from config import CONVERSATION_TIMEOUT, VERSION, WAKE_WORDS


# ============================================================
# COMANDOS
# ============================================================

# Cada comando admite varias formas de decirlo.
# Todas deben estar ya normalizadas.
COMMAND_PHRASES = {
    "stop": (
        "para",
        "parate",
        "detente",
        "callate",
        "silencio",
        "cancela",
        "cancelar",
    ),
    "exit": (
        "salir",
        "terminar",
        "adios",
        "hasta luego",
        "cierra el programa",
    ),
    "pause": (
        "pausa",
        "pausar",
        "pausate",
        "deja de escuchar",
    ),
    "resume": (
        "continua",
        "continuar",
        "reanuda",
        "reanudar",
        "sigue escuchando",
    ),
    "repeat": (
        "repite",
        "repetir",
        "repitelo",
        "otra vez",
    ),
    "new_session": (
        "nueva conversacion",
        "nueva sesion",
        "limpia conversacion",
        "limpiar conversacion",
        "empezamos de nuevo",
    ),
    "help": (
        "ayuda",
        "que comandos hay",
    ),
}


# ============================================================
# NORMALIZACION
# ============================================================

# Marcador temporal para proteger la ñ mientras quitamos
# el resto de tildes.
_ENYE = "\u0001"


def normalize(text):
    """Normaliza texto para comparar comandos.

    Pasa a minusculas, elimina tildes y signos de puntuacion y
    colapsa los espacios. Conserva la ñ, que en español si
    distingue palabras.
    """

    if not text:
        return ""

    text = text.lower().strip()
    text = text.replace("ñ", _ENYE)

    decomposed = unicodedata.normalize("NFD", text)

    stripped = "".join(
        char
        for char in decomposed
        if unicodedata.category(char) != "Mn"
    )

    cleaned = "".join(
        char if (char.isalnum() or char.isspace() or char == _ENYE) else " "
        for char in stripped
    )

    return " ".join(cleaned.split()).replace(_ENYE, "ñ")


# ============================================================
# WAKE WORD
# ============================================================

def detect_wake_word(text):
    """Separa la wake word del resto de la frase.

    Devuelve ``(wake_word, resto)``. El resto conserva el texto
    original con sus tildes y mayusculas, porque es lo que se
    envia a Claude; solo la deteccion usa texto normalizado.

    Si la frase no empieza por una wake word devuelve
    ``(None, None)``.

        "Jarvis, abre app.py"  ->  ("jarvis", "abre app.py")
        "Jarvis"               ->  ("jarvis", "")
        "abre app.py"          ->  (None, None)
    """

    if not text:
        return None, None

    words = text.strip().split()

    if not words:
        return None, None

    first = normalize(words[0])

    if first not in WAKE_WORDS:
        return None, None

    rest = " ".join(words[1:]).strip()

    # Whisper suele escribir "Jarvis, ..." o "Jarvis: ...".
    rest = rest.lstrip(",:;.-— ").strip()

    return first, rest


# ============================================================
# COMANDOS
# ============================================================

def detect_command(text):
    """Devuelve el nombre del comando dictado, o None.

    Solo hay coincidencia si la frase completa es el comando.
    """

    normalized = normalize(text)

    if not normalized:
        return None

    for name, phrases in COMMAND_PHRASES.items():
        if normalized in phrases:
            return name

    return None


# ============================================================
# AYUDA
# ============================================================

def help_text():

    wake = "\n".join(
        f"  {word.capitalize()}" for word in WAKE_WORDS[:3]
    )

    commands = "\n".join(
        f"  {name:<12} {', '.join(phrases[:3])}"
        for name, phrases in COMMAND_PHRASES.items()
    )

    return f"""
============================================================
COMANDOS DE VOZ V{VERSION}
============================================================

Wake word (y variantes que Whisper suele oir):

{wake}

Di la wake word y luego la peticion:

  "Jarvis, abre config.py y sube el volumen"

Durante los {CONVERSATION_TIMEOUT} segundos siguientes puedes seguir
hablando sin repetirla.

Comandos (hay que decirlos solos, sin nada mas):

{commands}

Teclado:

  F8   escuchar ahora (sin wake word)
  F9   pausa / reanudar
  F10  repetir ultima respuesta
  ESC  cancelar lo que este haciendo

============================================================
"""


def print_help():
    print(help_text())
