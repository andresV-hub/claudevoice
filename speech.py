"""Captura de microfono y transcripcion.

El flujo es siempre el mismo: Silero VAD decide cuando empiezas
y cuando terminas de hablar, y Whisper transcribe el recorte.

El stream de entrada se abre una sola vez y se reutiliza. Antes
se abria y se cerraba en cada iteracion del bucle principal, lo
que costaba tiempo en cada vuelta y se comia el principio de la
primera palabra.
"""

import collections
import tempfile
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import torch

from faster_whisper import WhisperModel
from silero_vad import load_silero_vad

from config import (
    AUDIO_MAX_SECONDS,
    AUDIO_PRE_ROLL_MS,
    AUDIO_START_TIMEOUT,
    CHANNELS,
    SAMPLE_RATE,
    VAD_MIN_SILENCE_MS,
    VAD_MIN_SPEECH_MS,
    VAD_THRESHOLD,
    WHISPER_BEAM_SIZE,
    WHISPER_BEST_OF,
    WHISPER_COMPUTE_TYPE,
    WHISPER_CONDITION_ON_PREVIOUS_TEXT,
    WHISPER_DEVICE,
    WHISPER_INITIAL_PROMPT,
    WHISPER_LANGUAGE,
    WHISPER_MODEL,
    WHISPER_TEMPERATURE,
    WHISPER_VAD_FILTER,
)


# Silero VAD exige bloques de exactamente 512 muestras
# cuando se trabaja a 16 kHz.
CHUNK_SAMPLES = 512


def resolve_device():
    """Decide en que dispositivo corre Whisper.

    faster-whisper es varias veces mas rapido en GPU, pero el
    tipo de calculo tiene que acompañar: float16 en CUDA e int8
    en CPU.
    """

    device = WHISPER_DEVICE
    compute_type = WHISPER_COMPUTE_TYPE

    if device == "auto":
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    return device, compute_type


class SpeechEngine:

    def __init__(self):

        device, compute_type = resolve_device()

        print("\n🧠 Cargando Whisper...")
        print(f"   Modelo: {WHISPER_MODEL}")
        print(f"   Dispositivo: {device} ({compute_type})")

        try:
            self.whisper = WhisperModel(
                WHISPER_MODEL,
                device=device,
                compute_type=compute_type,
            )

        except Exception as error:
            if device == "cpu":
                raise

            print(f"⚠️ No pude usar la GPU ({error}). Vuelvo a CPU.")

            self.whisper = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )

        print("🧠 Cargando detector de voz...")

        self.vad = load_silero_vad()

        self._stream = None
        self._stream_lock = threading.Lock()
        self._abort = threading.Event()

        print("✅ Sistema de voz listo.")

    # ========================================================
    # STREAM DE ENTRADA
    # ========================================================

    def _ensure_stream(self):

        with self._stream_lock:

            if self._stream is None:
                stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="float32",
                    blocksize=CHUNK_SAMPLES,
                )

                stream.start()

                self._stream = stream

            return self._stream

    def _drop_stream(self):
        """Cierra el stream para que la siguiente llamada lo reabra."""

        with self._stream_lock:

            stream = self._stream
            self._stream = None

        if stream is None:
            return

        for action in (stream.stop, stream.close):
            try:
                action()
            except Exception:
                pass

    def flush(self):
        """Descarta el audio acumulado desde la ultima grabacion.

        Es lo que evita que el microfono se coma la voz de Claude
        saliendo por los altavoces y se la mande a Whisper.
        """

        try:
            stream = self._ensure_stream()

            while True:
                pending = stream.read_available

                if pending <= 0:
                    break

                stream.read(pending)

        except Exception:
            self._drop_stream()

    def close(self):
        self._drop_stream()

    # ========================================================
    # ABORTAR
    # ========================================================

    def abort(self):
        """Interrumpe la grabacion en curso."""

        self._abort.set()

    # ========================================================
    # GRABAR HASTA DETECTAR SILENCIO
    # ========================================================

    def record_until_silence(self):

        self._abort.clear()

        try:
            stream = self._ensure_stream()

        except Exception as error:
            print(f"\n⚠️ No pude abrir el microfono: {error}")
            self._drop_stream()
            return None

        # El audio que se haya acumulado mientras Claude hablaba
        # o pensaba ya no interesa.
        self.flush()

        print("\n🎤 Escuchando...")

        chunk_ms = int(CHUNK_SAMPLES / SAMPLE_RATE * 1000)

        max_chunks = int(AUDIO_MAX_SECONDS * 1000 / chunk_ms)
        start_timeout_chunks = int(AUDIO_START_TIMEOUT * 1000 / chunk_ms)
        pre_roll_chunks = max(1, int(AUDIO_PRE_ROLL_MS / chunk_ms))

        # Guarda los ultimos fragmentos de audio antes de detectar
        # oficialmente la voz, para no perder el inicio de la frase.
        pre_roll = collections.deque(maxlen=pre_roll_chunks)

        audio_chunks = []

        speech_started = False

        silence_ms = 0
        speech_ms = 0

        try:

            for index in range(max_chunks):

                if self._abort.is_set():
                    return None

                audio, _ = stream.read(CHUNK_SAMPLES)

                mono = audio[:, 0].copy()

                probability = float(
                    self.vad(torch.from_numpy(mono), SAMPLE_RATE).item()
                )

                speaking = probability >= VAD_THRESHOLD

                # ----------------------------------------------
                # TODAVIA NO HEMOS EMPEZADO A GRABAR
                # ----------------------------------------------

                if not speech_started:

                    pre_roll.append(mono)

                    if speaking:
                        speech_ms += chunk_ms

                        if speech_ms >= VAD_MIN_SPEECH_MS:
                            speech_started = True

                            print("🟢 Voz detectada...")

                            # Añadimos el audio anterior para no
                            # perder el inicio.
                            audio_chunks.extend(pre_roll)

                            silence_ms = 0

                    else:
                        speech_ms = 0

                    # No se detecto voz durante el tiempo maximo
                    # de espera.
                    if index >= start_timeout_chunks and not speech_started:
                        return None

                # ----------------------------------------------
                # YA ESTAMOS GRABANDO
                # ----------------------------------------------

                else:

                    audio_chunks.append(mono)

                    if speaking:
                        silence_ms = 0
                    else:
                        silence_ms += chunk_ms

                    # Terminamos despues de un silencio
                    # suficientemente largo.
                    if silence_ms >= VAD_MIN_SILENCE_MS:
                        break

        except Exception as error:
            print(f"\n⚠️ Error grabando: {error}")
            self._drop_stream()
            return None

        if not speech_started or not audio_chunks:
            return None

        return self._save_wav(np.concatenate(audio_chunks))

    # ========================================================
    # GUARDAR WAV
    # ========================================================

    @staticmethod
    def _save_wav(audio):

        audio = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)

        pcm = (audio * 32767).astype(np.int16)

        temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp.close()

        with wave.open(temp.name, "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm.tobytes())

        return temp.name

    # ========================================================
    # TRANSCRIBIR
    # ========================================================

    def transcribe(self, audio_file):

        if not audio_file:
            return ""

        print("🧠 Transcribiendo...")

        try:
            segments, _ = self.whisper.transcribe(
                audio_file,
                language=WHISPER_LANGUAGE,
                beam_size=WHISPER_BEAM_SIZE,
                best_of=WHISPER_BEST_OF,
                temperature=WHISPER_TEMPERATURE,
                vad_filter=WHISPER_VAD_FILTER,
                condition_on_previous_text=WHISPER_CONDITION_ON_PREVIOUS_TEXT,
                initial_prompt=WHISPER_INITIAL_PROMPT,
            )

            parts = [
                segment.text.strip()
                for segment in segments
                if segment.text.strip()
            ]

            return " ".join(parts).strip()

        except Exception as error:
            print(f"\n⚠️ Error transcribiendo: {error}")
            return ""

        finally:
            try:
                Path(audio_file).unlink(missing_ok=True)
            except Exception:
                pass

    # ========================================================
    # ESCUCHAR Y TRANSCRIBIR
    # ========================================================

    def listen(self):
        """Graba una frase y devuelve su transcripcion."""

        audio_file = self.record_until_silence()

        if not audio_file:
            return ""

        return self.transcribe(audio_file)
