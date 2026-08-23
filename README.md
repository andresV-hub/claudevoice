# Voice Claude

Claude Code manejado por voz, en español y sobre Windows.

Dices **Jarvis** seguido de lo que quieras, Whisper transcribe, la
petición va a la CLI de Claude Code dentro del proyecto en el que
estés, y la respuesta se lee en voz alta.

```
Tú:      "Jarvis, añade un test para el login"
Claude:  edita los archivos y te resume lo que ha hecho
```

## Requisitos

- Windows 10 u 11 (la síntesis de voz usa SAPI).
- Python 3.11 o superior.
- [Claude Code](https://claude.com/claude-code) instalado y autenticado:
  `npm install -g @anthropic-ai/claude-code`
- Una voz española instalada en Windows (Configuración → Hora e idioma
  → Voz). Sin ella, el sistema lee el castellano con acento inglés.

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

La primera ejecución descarga el modelo de Whisper (`medium`, ~1,5 GB).

## Uso

Ejecútalo **desde la carpeta del proyecto sobre el que quieras
trabajar**: Voice Claude detecta la raíz del proyecto y lanza a Claude
allí.

```powershell
cd C:\ruta\a\mi\proyecto
C:\ruta\a\voice-claude\.venv\Scripts\python C:\ruta\a\voice-claude\voice_claude.py
```

### Wake word

La palabra de inicio es **Jarvis**. También se aceptan las variantes que
Whisper suele oír al dictarla en español (*Yarvis*, *Jarbis*, *Harvis*…).

Después de una petición tienes 90 segundos para seguir hablando sin
repetir la wake word. El contador se reinicia con cada frase.

### Comandos de voz

Hay que decirlos **solos**, sin nada más en la frase. Así, "escribe un
test **para** el login" es una petición normal y no la orden de parar.

| Comando | Se dice |
| --- | --- |
| Parar / callar | para, cállate, cancela, silencio |
| Salir | salir, adiós, terminar |
| Pausar | pausa, deja de escuchar |
| Reanudar | continúa, reanuda |
| Repetir | repite, otra vez |
| Nueva conversación | nueva conversación, nueva sesión |
| Ayuda | ayuda |

### Teclado

| Tecla | Acción |
| --- | --- |
| F8 | Escuchar ahora, sin wake word |
| F9 | Pausar / reanudar |
| F10 | Repetir la última respuesta |
| ESC | Cancelar lo que esté haciendo |

Los atajos son globales, así que funcionan aunque la ventana no tenga el
foco. En algunas configuraciones de Windows, `keyboard` necesita permisos
de administrador; si no se registran, verás un aviso al arrancar.

## Configuración

Todo se ajusta en `config.py`:

- **Wake word** — `WAKE_WORDS`.
- **Whisper** — `WHISPER_MODEL` (`small` va notablemente más rápido en
  CPU), `WHISPER_DEVICE` (`auto` usa la GPU si hay CUDA).
- **Micrófono / VAD** — `VAD_THRESHOLD` si no te detecta la voz,
  `VAD_MIN_SILENCE_MS` si te corta cuando haces pausas.
- **Voz** — `TTS_VOICE_NAME`, `TTS_RATE`, `TTS_VOLUME`.
- **Permisos de Claude** — `CLAUDE_PERMISSION_MODE`.

### Permisos de Claude

En modo no interactivo nadie puede responder a un aviso de permisos, así
que la política se decide por adelantado. El valor por defecto es
`acceptEdits`: **Claude edita archivos de tu proyecto sin preguntar**. Si
prefieres que solo lea y proponga, cámbialo a `plan`.

## Estructura

| Archivo | Responsabilidad |
| --- | --- |
| `voice_claude.py` | Bucle principal y orquestación |
| `speech.py` | Micrófono, VAD y transcripción |
| `tts.py` | Síntesis de voz por SAPI |
| `claude_client.py` | Puente con la CLI de Claude Code |
| `commands.py` | Wake word y comandos de voz |
| `conversation.py` | Ventana de conversación e historial |
| `project.py` | Detección del proyecto y de la rama Git |
| `logger.py` | Registro diario en `data/logs/` |
| `config.py` | Toda la configuración |

## Pruebas

```powershell
.venv\Scripts\python -m unittest discover -s tests
```

o, si instalas `requirements-dev.txt`:

```powershell
.venv\Scripts\pytest
```

## Privacidad

El audio se transcribe **en local** con Whisper; no sale de tu máquina.
Lo que sí sale es el texto de tus peticiones y las respuestas, que van a
la API de Anthropic a través de la CLI de Claude Code. Las conversaciones
se guardan en claro en `data/logs/`; ponlo a `False` en `LOG_ENABLED` si
no lo quieres.
