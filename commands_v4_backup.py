from config import WAKE_WORDS


EXIT_WORDS = (
    "salir",
    "terminar",
    "adios",
    "adiós",
)

PAUSE_WORDS = (
    "pausa",
    "pausar",
)

RESUME_WORDS = (
    "continua",
    "continúa",
    "reanuda",
)

REPEAT_WORDS = (
    "repite",
    "repetir",
)

NEW_SESSION_WORDS = (
    "limpia conversación",
    "limpiar conversación",
    "nueva conversación",
    "nueva sesion",
    "nueva sesión",
)

STOP_WORDS = (
    "para",
    "parar",
    "detente",
    "cállate",
    "callate",
)


def normalize(text):
    return " ".join(
        text.lower()
        .strip()
        .split()
    )


def detect_wake_word(text):
    normalized = normalize(text)

    for word in WAKE_WORDS:
        if normalized == word:
            return word, ""

        prefix = word + " "

        if normalized.startswith(prefix):
            return word, normalized[len(prefix):].strip()

    return None, None


def contains_any(text, words):
    normalized = normalize(text)

    return any(
        word in normalized
        for word in words
    )


def is_exit(text):
    return contains_any(text, EXIT_WORDS)


def is_pause(text):
    return contains_any(text, PAUSE_WORDS)


def is_resume(text):
    return contains_any(text, RESUME_WORDS)


def is_repeat(text):
    return contains_any(text, REPEAT_WORDS)


def is_new_session(text):
    return contains_any(text, NEW_SESSION_WORDS)


def is_stop(text):
    return contains_any(text, STOP_WORDS)


def print_help():
    print(
        """
============================================================
COMANDOS DE VOZ
============================================================

Wake words:
  Claude
  Claro
  Claudio
  Claud

Comandos:
  salir
  terminar
  adios
  pausa
  continúa
  repite
  limpia conversación
  nueva conversación
  para

Teclado:
  F8   activar escucha
  F9   pausa
  F10  repetir
  ESC  cancelar

============================================================
"""
    )