import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import torch
from faster_whisper import WhisperModel
from silero_vad import load_silero_vad

from config import (
    AUDIO_MAX_SECONDS,
    AUDIO_START_TIMEOUT,
    CHANNELS,
    SAMPLE_RATE,
    TTS_MAX_CHARS,
    TTS_RATE,
    VAD_MIN_SILENCE_MS,
    VAD_MIN_SPEECH_MS,
    VAD_THRESHOLD,
    WHISPER_LANGUAGE,
    WHISPER_MODEL,
)


class SpeechEngine:

    def __init__(self):
        print("\n🧠 Cargando Whisper...")

        self.whisper = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )

        print("🧠 Cargando detector de voz...")

        self.vad = load_silero_vad()

        print("✅ Sistema de voz listo.")

    # ========================================================
    # TTS
    # ========================================================

    def speak(self, text):
        if not text:
            return

        print("\n🔊 Claude hablando...\n")

        clean = self.prepare_for_speech(text)

        if not clean:
            return

        clean = clean[:TTS_MAX_CHARS]

        temp = tempfile.NamedTemporaryFile(
            suffix=".txt",
            delete=False,
            mode="w",
            encoding="utf-8",
        )

        try:
            temp.write(clean)
            temp.close()

            script = f"""
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = {TTS_RATE}
$text = Get-Content -Raw -Encoding UTF8 '{temp.name}'
$speak.Speak($text)
$speak.Dispose()
"""

            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        finally:
            try:
                Path(temp.name).unlink(
                    missing_ok=True
                )
            except Exception:
                pass

    def prepare_for_speech(self, text):

        text = re.sub(
            r"```.*?```",
            " ",
            text,
            flags=re.DOTALL,
        )

        text = re.sub(
            r"`([^`]+)`",
            r"\1",
            text,
        )

        text = re.sub(
            r"https?://\S+",
            " enlace ",
            text,
        )

        text = re.sub(
            r"\[[^\]]+\]\([^)]+\)",
            "",
            text,
        )

        text = re.sub(
            r"[*_#>`]",
            "",
            text,
        )

        text = re.sub(
            r"\n+",
            ". ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ========================================================
    # GRABACIÓN + SILERO VAD
    # ========================================================

    def record_until_silence(self):

        print("\n🎤 Escuchando...")
        print("   Habla cuando quieras.")

        # IMPORTANTE:
        # Silero VAD a 16000 Hz requiere exactamente
        # 512 muestras por llamada.

        chunk_samples = 512
        chunk_ms = 32

        max_chunks = int(
            AUDIO_MAX_SECONDS * 1000 / chunk_ms
        )

        start_timeout_chunks = int(
            AUDIO_START_TIMEOUT * 1000 / chunk_ms
        )

        audio_chunks = []

        speech_started = False
        silence_ms = 0
        speech_ms = 0

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=chunk_samples,
        )

        stream.start()

        try:

            for index in range(max_chunks):

                audio, _ = stream.read(
                    chunk_samples
                )

                mono = audio[:, 0].copy()

                audio_chunks.append(mono)

                tensor = torch.from_numpy(
                    mono
                )

                probability = float(
                    self.vad(
                        tensor,
                        SAMPLE_RATE,
                    ).item()
                )

                speaking = (
                    probability >= VAD_THRESHOLD
                )

                if speaking:

                    speech_ms += chunk_ms
                    silence_ms = 0

                    if (
                        speech_ms
                        >= VAD_MIN_SPEECH_MS
                    ):
                        speech_started = True

                else:

                    if speech_started:
                        silence_ms += chunk_ms

                # Terminamos cuando hay suficiente
                # silencio después de hablar.

                if speech_started:

                    if (
                        silence_ms
                        >= VAD_MIN_SILENCE_MS
                    ):
                        break

                # Si nadie habla durante el timeout,
                # volvemos al modo de escucha.

                else:

                    if (
                        index
                        >= start_timeout_chunks
                    ):
                        break

        finally:

            stream.stop()
            stream.close()

        if not speech_started:
            return None

        audio = np.concatenate(
            audio_chunks
        )

        return self._save_wav(audio)

    # ========================================================
    # GUARDAR WAV
    # ========================================================

    def _save_wav(self, audio):

        audio = np.clip(
            audio,
            -1.0,
            1.0,
        )

        pcm = (
            audio * 32767
        ).astype(np.int16)

        temp = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        )

        temp.close()

        with wave.open(
            temp.name,
            "wb",
        ) as wf:

            wf.setnchannels(
                CHANNELS
            )

            wf.setsampwidth(2)

            wf.setframerate(
                SAMPLE_RATE
            )

            wf.writeframes(
                pcm.tobytes()
            )

        return temp.name

    # ========================================================
    # WHISPER
    # ========================================================

    def transcribe(self, audio_file):

        if not audio_file:
            return ""

        print("🧠 Transcribiendo...")

        try:

            segments, info = (
                self.whisper.transcribe(
                    audio_file,
                    language=WHISPER_LANGUAGE,
                    beam_size=5,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
            )

            text = " ".join(
                segment.text.strip()
                for segment in segments
                if segment.text.strip()
            )

            return text.strip()

        finally:

            try:
                Path(
                    audio_file
                ).unlink(
                    missing_ok=True
                )
            except Exception:
                pass