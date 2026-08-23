from pathlib import Path

# ============================================================
# VOICE CLAUDE V4 - CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

# ----------------------------
# Whisper
# ----------------------------

WHISPER_MODEL = "small"
WHISPER_LANGUAGE = "es"

SAMPLE_RATE = 16000
CHANNELS = 1

# ----------------------------
# Wake words
# ----------------------------

WAKE_WORDS = (
    "claude",
    "claro",
    "claudio",
    "claud",
)

# ----------------------------
# Audio / VAD
# ----------------------------

VAD_THRESHOLD = 0.55

VAD_MIN_SPEECH_MS = 250
VAD_MIN_SILENCE_MS = 700

AUDIO_START_TIMEOUT = 8.0
AUDIO_MAX_SECONDS = 30.0

PRE_SPEECH_MS = 300

# ----------------------------
# Conversación
# ----------------------------

CONVERSATION_TIMEOUT = 90

# ----------------------------
# TTS
# ----------------------------

TTS_MAX_CHARS = 1800
TTS_RATE = 0

# ----------------------------
# Teclado
# ----------------------------

KEY_LISTEN = "f8"
KEY_PAUSE = "f9"
KEY_REPEAT = "f10"
KEY_CANCEL = "esc"

# ----------------------------
# Claude
# ----------------------------

CLAUDE_COMMAND = "claude"

CLAUDE_TIMEOUT = 600

# ----------------------------
# Debug
# ----------------------------

DEBUG = False
