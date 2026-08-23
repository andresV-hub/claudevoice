import os


# ============================================================
# VOICE CLAUDE V3 - CONFIGURACION
# ============================================================

# ------------------------------------------------------------
# WHISPER
# ------------------------------------------------------------

MODEL_SIZE = "small"

SAMPLE_RATE = 16000
CHANNELS = 1


# ------------------------------------------------------------
# DETECCION DE VOZ
# ------------------------------------------------------------

# Sensibilidad del microfono.
#
# Si no detecta tu voz:
#     0.015 -> 0.010
#
# Si detecta demasiado ruido:
#     0.015 -> 0.025
#
ENERGY_THRESHOLD = 0.015

# Tiempo de silencio que indica que terminaste de hablar.
SILENCE_DURATION = 1.2

# Audio que conservamos antes de detectar que empezaste.
PRE_ROLL_DURATION = 0.4

# Maximo de segundos que puede durar una intervencion.
MAX_RECORDING_DURATION = 90

# Maximo tiempo esperando a que empieces a hablar.
WAITING_TIMEOUT = 30

# Tamano de cada bloque de audio.
CHUNK_DURATION = 0.1


# ------------------------------------------------------------
# WAKE WORD
# ------------------------------------------------------------

# False = puedes hablar directamente.
#
# True = tienes que empezar diciendo:
#
#     "Claude, analiza este archivo"
#
WAKE_WORD_ENABLED = True

WAKE_WORDS = [
    "claude",
    "claro",
    "claudio",
]


# ------------------------------------------------------------
# CLAUDE CLI
# ------------------------------------------------------------

CLAUDE_CMD = os.path.expandvars(
    r"%APPDATA%\npm\claude.cmd"
)


# ------------------------------------------------------------
# CONVERSACION
# ------------------------------------------------------------

DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "data"
)

CONVERSATION_FILE = os.path.join(
    DATA_DIR,
    "conversation.json"
)

LOG_FILE = os.path.join(
    DATA_DIR,
    "conversation.log"
)


# ------------------------------------------------------------
# SEGURIDAD
# ------------------------------------------------------------

# Si True, ciertas acciones potencialmente peligrosas
# requieren confirmacion.
CONFIRM_DANGEROUS_ACTIONS = True


# ------------------------------------------------------------
# TTS
# ------------------------------------------------------------

TTS_RATE = 0

TTS_VOLUME = 100

# Maximo de caracteres que leeremos.
MAX_TTS_CHARACTERS = 5000


# ------------------------------------------------------------
# COMANDOS LOCALES
# ------------------------------------------------------------

EXIT_COMMANDS = {
    "salir",
    "terminar",
    "adios",
    "adiós",
    "hasta luego",
    "cerrar",
}

CLEAR_COMMANDS = {
    "limpia conversación",
    "limpiar conversación",
    "limpia la conversación",
    "limpiar la conversación",
    "nueva conversación",
}

REPEAT_COMMANDS = {
    "repite",
    "repetir",
    "repítelo",
    "repite eso",
}

PAUSE_COMMANDS = {
    "pausa",
    "espera",
    "para",
    "detente",
}
