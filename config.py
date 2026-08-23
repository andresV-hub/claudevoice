from pathlib import Path

from console import configure_console


# ============================================================
# VOICE CLAUDE
# ============================================================

VERSION = "5.0"

# La salida lleva emojis y la consola de Windows no siempre
# usa UTF-8. Se prepara aqui porque todos los modulos del
# proyecto importan config.
configure_console()

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
LOG_DIR = DATA_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# WAKE WORDS
# ============================================================

# La palabra de inicio es "Jarvis".
#
# Incluimos variantes porque Whisper transcribe un nombre
# inglés dictado en español de formas distintas segun la
# pronunciacion y el ruido de fondo.
#
# Se comparan siempre normalizadas: en minusculas, sin tildes
# y sin signos de puntuacion.
WAKE_WORDS = (
    "jarvis",
    "yarvis",
    "jarbis",
    "yarbis",
    "harvis",
    "jervis",
    "charvis",
    "yarvi",
    "jarvi",
)


# ============================================================
# WHISPER
# ============================================================

WHISPER_MODEL = "medium"
WHISPER_LANGUAGE = "es"

# "auto" usa GPU si hay CUDA disponible y CPU si no.
# Tambien admite "cuda" o "cpu" de forma explicita.
WHISPER_DEVICE = "auto"

# "auto" elige float16 en GPU e int8 en CPU.
WHISPER_COMPUTE_TYPE = "auto"

# Mayor precisión en la transcripción
WHISPER_BEAM_SIZE = 8
WHISPER_BEST_OF = 5
WHISPER_TEMPERATURE = 0.0

# Evita que Whisper intente continuar o reinterpretar
# frases anteriores.
WHISPER_CONDITION_ON_PREVIOUS_TEXT = False

# Ya usamos Silero VAD para controlar la grabación.
# Desactivamos el VAD interno de Whisper para evitar
# un segundo recorte del audio.
WHISPER_VAD_FILTER = False

# Contexto para mejorar la transcripción de español
# y términos técnicos.
WHISPER_INITIAL_PROMPT = (
    "Transcripción literal en español de España. "
    "Transcribe exactamente lo que dice el usuario. "
    "No corrijas, no resumas y no inventes palabras. "
    "El usuario llama a su asistente Jarvis. "
    "El usuario puede hablar sobre programación, código, "
    "Python, JavaScript, TypeScript, React, APIs, archivos, "
    "proyectos, terminal, comandos y Claude Code."
)


# ============================================================
# AUDIO
# ============================================================

SAMPLE_RATE = 16000
CHANNELS = 1

# Audio guardado antes de detectar oficialmente la voz.
# Evita perder el comienzo de una frase.
AUDIO_PRE_ROLL_MS = 800

# Tiempo máximo esperando a que empieces a hablar.
AUDIO_START_TIMEOUT = 10.0

# Duración máxima de una grabación.
AUDIO_MAX_SECONDS = 45.0


# ============================================================
# VAD - DETECCIÓN DE VOZ
# ============================================================

# Sensibilidad del detector Silero.
# Un valor más bajo detecta voces más suaves.
VAD_THRESHOLD = 0.40

# Tiempo mínimo de voz para considerar que has empezado
# a hablar.
VAD_MIN_SPEECH_MS = 150

# Tiempo de silencio necesario para terminar la grabación.
# Más alto evita cortar frases cuando haces una pausa.
VAD_MIN_SILENCE_MS = 1200


# ============================================================
# CONVERSACIÓN
# ============================================================

CONVERSATION_TIMEOUT = 90

# Número máximo de turnos guardados en el historial local.
#
# Claude mantiene su propio contexto a través de la sesión
# (--resume), asi que este historial solo se usa para los
# logs y para mostrar el estado.
CONVERSATION_MAX_TURNS = 8


# ============================================================
# TTS - VOZ DE CLAUDE
# ============================================================

# Corte duro: nada que se mande a la voz pasa de aqui.
TTS_MAX_CHARS = 1800

# Velocidad de SAPI, entre -10 y 10.
# 0 = velocidad normal.
TTS_RATE = 0

# Volumen de SAPI, entre 0 y 100.
TTS_VOLUME = 100

# Idioma preferido de la voz del sistema.
# Evita que una voz inglesa lea el castellano.
TTS_VOICE_LANGUAGE = "es"

# Fuerza una voz concreta por nombre, por ejemplo "Helena".
# None = elegir automaticamente segun el idioma.
TTS_VOICE_NAME = None


# ============================================================
# TECLADO
# ============================================================

KEY_LISTEN = "f8"
KEY_PAUSE = "f9"
KEY_REPEAT = "f10"
KEY_CANCEL = "esc"


# ============================================================
# CLAUDE
# ============================================================

CLAUDE_COMMAND = "claude"

# Tiempo máximo esperando una respuesta de Claude.
CLAUDE_TIMEOUT = 600

# Politica de permisos de Claude Code en modo no interactivo.
#
# En modo -p nadie puede responder a un aviso de permisos,
# asi que hay que decidirla por adelantado:
#
#   "acceptEdits"       edita archivos sin preguntar
#   "plan"              solo lee y planifica, no modifica nada
#   "default"           deniega lo que requiera confirmacion
#   "bypassPermissions" sin ningun limite (no recomendado)
CLAUDE_PERMISSION_MODE = "acceptEdits"


# ============================================================
# LOGGING
# ============================================================

LOG_ENABLED = True


# ============================================================
# COMPORTAMIENTO DE VOZ
# ============================================================

# False = no leer bloques de código completos.
READ_CODE_ALOUD = False

# A partir de esta longitud, la respuesta no se lee entera:
# se resume en voz alta y el texto completo queda en pantalla.
MAX_VOICE_RESPONSE_CHARS = 900
