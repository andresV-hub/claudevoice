"""Sintesis de voz sobre SAPI (Windows).

Antes se lanzaba un proceso de PowerShell por cada frase, lo
que añadia entre medio segundo y segundo y medio de espera
antes de oir nada. Aqui hablamos con SAPI directamente por COM
desde un hilo dedicado: arranca al instante y se puede cortar
al instante.

El objeto COM vive entero dentro de ese hilo. Los objetos SAPI
tienen afinidad de hilo, asi que el resto del programa se
comunica con el mediante una cola.
"""

import queue
import re
import threading

from config import (
    READ_CODE_ALOUD,
    TTS_MAX_CHARS,
    TTS_RATE,
    TTS_VOICE_LANGUAGE,
    TTS_VOICE_NAME,
    TTS_VOLUME,
)


# Banderas de SAPI ISpVoice::Speak.
SVSF_ASYNC = 1
SVSF_PURGE_BEFORE_SPEAK = 2


# Codigos de idioma de Windows, en hexadecimal, tal y como
# aparecen en el atributo "Language" de cada voz.
_LANGUAGE_IDS = {
    "es": ("0c0a", "040a", "080a", "200a", "2c0a", "0a"),
    "en": ("0409", "0809", "09"),
}


class TextToSpeech:

    def __init__(self):

        self._queue = queue.Queue()
        self._stop_current = threading.Event()
        self._idle = threading.Event()
        self._idle.set()

        self.voice_name = None
        self.available = False

        self._ready = threading.Event()

        self._thread = threading.Thread(
            target=self._run,
            name="tts",
            daemon=True,
        )

        self._thread.start()

        # Esperamos a saber si SAPI ha arrancado para poder
        # avisar al usuario durante el arranque.
        self._ready.wait(timeout=10)

    # ========================================================
    # API PUBLICA
    # ========================================================

    def speak(self, text):
        """Encola una frase y espera a que termine de decirse."""

        if not self.say(text):
            return

        self.wait_until_done()

    def say(self, text):
        """Encola una frase y vuelve inmediatamente."""

        clean = self.prepare_for_speech(text)

        if not clean or not self.available:
            return False

        self._idle.clear()
        self._queue.put(clean[:TTS_MAX_CHARS])

        return True

    # Nombre historico, se mantiene por comodidad.
    speak_async = say

    def stop(self):
        """Corta la frase actual y vacia la cola."""

        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        self._stop_current.set()

    def is_speaking(self):
        return not self._idle.is_set()

    def wait_until_done(self, timeout=None):
        """Bloquea hasta que no quede nada por decir."""

        return self._idle.wait(timeout=timeout)

    def close(self):
        self.stop()
        self._queue.put(None)

    # ========================================================
    # HILO DE VOZ
    # ========================================================

    def _run(self):

        voice = None

        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()

            voice = win32com.client.Dispatch("SAPI.SpVoice")

            self._select_voice(voice)

            voice.Rate = TTS_RATE
            voice.Volume = TTS_VOLUME

            self.available = True

        except Exception as error:
            print(f"\n⚠️ No hay sintesis de voz disponible: {error}")
            self.available = False

        finally:
            self._ready.set()

        if not self.available:
            # Vaciamos la cola para que nadie se quede esperando.
            while True:
                item = self._queue.get()
                self._idle.set()
                if item is None:
                    return

        while True:

            text = self._queue.get()

            if text is None:
                break

            self._stop_current.clear()

            try:
                self._speak_one(voice, text)

            except Exception as error:
                print(f"\n⚠️ Error de voz: {error}")

            finally:
                if self._queue.empty():
                    self._idle.set()

    def _speak_one(self, voice, text):

        voice.Speak(text, SVSF_ASYNC)

        # WaitUntilDone devuelve False mientras siga hablando,
        # asi que podemos vigilar la peticion de parada.
        while not voice.WaitUntilDone(100):

            if self._stop_current.is_set():
                voice.Speak("", SVSF_ASYNC | SVSF_PURGE_BEFORE_SPEAK)
                break

    # ========================================================
    # SELECCION DE VOZ
    # ========================================================

    def _select_voice(self, voice):
        """Elige una voz del idioma configurado.

        Sin esto, Windows usa la voz por defecto del sistema,
        que muchas veces es inglesa y lee el castellano con
        acento ingles.
        """

        try:
            voices = list(voice.GetVoices())
        except Exception:
            return

        if not voices:
            return

        chosen = None

        if TTS_VOICE_NAME:
            wanted = TTS_VOICE_NAME.lower()

            for candidate in voices:
                if wanted in self._describe(candidate).lower():
                    chosen = candidate
                    break

        if chosen is None:
            chosen = self._first_voice_for_language(
                voices,
                TTS_VOICE_LANGUAGE,
            )

        if chosen is None:
            self.voice_name = self._describe(voices[0])
            return

        try:
            voice.Voice = chosen
            self.voice_name = self._describe(chosen)
        except Exception:
            pass

    def _first_voice_for_language(self, voices, language):

        if not language:
            return None

        language_ids = _LANGUAGE_IDS.get(language.lower(), ())

        for candidate in voices:

            try:
                attribute = candidate.GetAttribute("Language").lower()
            except Exception:
                attribute = ""

            if any(attribute.endswith(code) for code in language_ids):
                return candidate

        # Segundo intento, por el nombre de la voz.
        for candidate in voices:
            description = self._describe(candidate).lower()

            if "spanish" in description or "español" in description:
                return candidate

        return None

    @staticmethod
    def _describe(candidate):

        try:
            return candidate.GetDescription()
        except Exception:
            return ""

    # ========================================================
    # LIMPIEZA DEL TEXTO
    # ========================================================

    @staticmethod
    def prepare_for_speech(text):
        """Quita el markdown que no tiene sentido leer en voz alta."""

        if not text:
            return ""

        if READ_CODE_ALOUD:
            text = text.replace("```", " ")
        else:
            text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"https?://\S+", " enlace ", text)
        text = re.sub(r"[*_#>`|]", "", text)
        text = re.sub(r"\n+", ". ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()
