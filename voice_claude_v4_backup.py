import os
import sys
import time
import threading
from pathlib import Path

import keyboard

from audio import AudioController
from claude_client import ClaudeClient
from commands import (
    detect_wake_word,
    is_exit,
    is_new_session,
    is_pause,
    is_repeat,
    is_resume,
    is_stop,
    print_help,
)
from config import (
    AUDIO_MAX_SECONDS,
    CLAUDE_COMMAND,
    CLAUDE_TIMEOUT,
    CONVERSATION_TIMEOUT,
    KEY_CANCEL,
    KEY_LISTEN,
    KEY_PAUSE,
    KEY_REPEAT,
)
from conversation import Conversation
from project import get_project_info
from speech import SpeechEngine


class VoiceClaude:

    def __init__(self):

        self.running = True
        self.paused = False
        self.cancel_requested = False

        self.last_response = ""

        # ----------------------------------------
        # Proyecto
        # ----------------------------------------

        self.project = get_project_info()

        self.project_root = self.project["root"]

        # ----------------------------------------
        # Speech
        # ----------------------------------------

        self.speech = SpeechEngine()

        # ----------------------------------------
        # Claude
        # ----------------------------------------

        self.claude = ClaudeClient(
            project_root=self.project_root,
            command=CLAUDE_COMMAND,
            timeout=CLAUDE_TIMEOUT,
        )

        # ----------------------------------------
        # Conversación
        # ----------------------------------------

        self.conversation = Conversation(
            timeout=CONVERSATION_TIMEOUT
        )

        # ----------------------------------------
        # Audio
        # ----------------------------------------

        self.audio = AudioController(
            speech_engine=self.speech
        )

    # ========================================================
    # START
    # ========================================================

    def start(self):

        self.print_header()

        if not self.check_claude():
            return

        self.install_hotkeys()

        self.speech.speak(
            "Hola. Estoy listo. Puedes decir Claude, Claro o Claudio."
        )

        print_help()

        self.main_loop()

    # ========================================================
    # HEADER
    # ========================================================

    def print_header(self):

        print(
            "\n"
            + "=" * 60
            + "\n"
            "🎙️  VOICE CLAUDE V4\n"
            + "=" * 60
        )

        print(
            "\nClaude Code controlado por voz."
        )

        print(
            "\nWake words:"
        )

        print(
            "  Claude"
            "\n  Claro"
            "\n  Claudio"
            "\n  Claud"
        )

        print(
            f"\n📁 Proyecto:"
            f"\n   {self.project_root}"
        )

        if self.project["branch"]:
            print(
                f"\n🌿 Git:"
                f"\n   {self.project['branch']}"
            )

        print(
            "\n🧩 Detectado:"
            f"\n   {', '.join(self.project['types'])}"
        )

    # ========================================================
    # CLAUDE CHECK
    # ========================================================

    def check_claude(self):

        print(
            "\n🔎 Comprobando Claude CLI..."
        )

        ok, message = self.claude.check()

        if not ok:
            print(
                "\n❌ Claude CLI no disponible."
            )

            print(message)

            return False

        print(
            "✅ Claude CLI encontrado."
        )

        print(message)

        return True

    # ========================================================
    # HOTKEYS
    # ========================================================

    def install_hotkeys(self):

        keyboard.add_hotkey(
            KEY_LISTEN,
            self.force_listen
        )

        keyboard.add_hotkey(
            KEY_PAUSE,
            self.toggle_pause
        )

        keyboard.add_hotkey(
            KEY_REPEAT,
            self.repeat_last
        )

        keyboard.add_hotkey(
            KEY_CANCEL,
            self.cancel
        )

    def force_listen(self):

        self.paused = False

        print(
            "\n⌨️ F8 → escucha activada."
        )

    def toggle_pause(self):

        self.paused = not self.paused

        if self.paused:
            print(
                "\n⏸️ Voice Claude pausado."
            )
        else:
            print(
                "\n▶️ Voice Claude reanudado."
            )

    def repeat_last(self):

        if self.last_response:
            print(
                "\n🔁 Repitiendo respuesta..."
            )

            self.speech.speak(
                self.last_response
            )

    def cancel(self):

        self.cancel_requested = True

        print(
            "\n⛔ Cancelación solicitada."
        )

    # ========================================================
    # MAIN LOOP
    # ========================================================

    def main_loop(self):

        print(
            "\n🎧 Esperando wake word..."
        )

        while self.running:

            try:

                if self.paused:
                    time.sleep(0.2)
                    continue

                audio_file = (
                    self.speech.record_until_silence()
                )

                if not audio_file:
                    continue

                text = self.speech.transcribe(
                    audio_file
                )

                if not text:
                    continue

                print(
                    "\n👤 Tú:"
                )

                print(text)

                self.process_text(text)

            except KeyboardInterrupt:

                break

            except Exception as e:

                print(
                    "\n❌ Error:"
                )

                print(e)

                time.sleep(1)

        self.shutdown()

    # ========================================================
    # PROCESS TEXT
    # ========================================================

    def process_text(self, text):

        normalized = text.lower().strip()

        # ----------------------------------------
        # EXIT
        # ----------------------------------------

        if is_exit(normalized):

            self.speech.speak(
                "Hasta luego."
            )

            self.running = False
            return

        # ----------------------------------------
        # HELP
        # ----------------------------------------

        if normalized in (
            "ayuda",
            "ayúdame",
        ):

            print_help()
            return

        # ----------------------------------------
        # PAUSE
        # ----------------------------------------

        if is_pause(normalized):

            self.paused = True

            self.speech.speak(
                "Voice Claude pausado."
            )

            return

        # ----------------------------------------
        # RESUME
        # ----------------------------------------

        if is_resume(normalized):

            self.paused = False

            self.speech.speak(
                "Voice Claude reanudado."
            )

            return

        # ----------------------------------------
        # REPEAT
        # ----------------------------------------

        if is_repeat(normalized):

            self.repeat_last()
            return

        # ----------------------------------------
        # NEW SESSION
        # ----------------------------------------

        if is_new_session(normalized):

            self.conversation.reset()

            self.speech.speak(
                "Conversación reiniciada."
            )

            print(
                "\n🧹 Conversación reiniciada."
            )

            return

        # ----------------------------------------
        # STOP
        # ----------------------------------------

        if is_stop(normalized):

            self.cancel()

            self.speech.speak(
                "Detenido."
            )

            return

        # ----------------------------------------
        # WAKE WORD
        # ----------------------------------------

        wake_word, command = detect_wake_word(
            normalized
        )

        if wake_word:

            print(
                f"\n🗣️ Wake word detectada: {wake_word}"
            )

            self.conversation.activate()

            if command:
                self.send_to_claude(command)
            else:
                self.speech.speak(
                    "Sí."
                )

            return

        # ----------------------------------------
        # CONTINUED CONVERSATION
        # ----------------------------------------

        if self.conversation.should_accept_without_wake_word():

            self.send_to_claude(
                normalized
            )

    # ========================================================
    # CLAUDE
    # ========================================================

    def send_to_claude(self, prompt):

        if not prompt:
            return

        print(
            "\n🤖 Enviando a Claude..."
        )

        self.cancel_requested = False

        thread, container = (
            self.claude.ask_async(
                prompt
            )
        )

        spinner = [
            "⠋",
            "⠙",
            "⠹",
            "⠸",
            "⠼",
            "⠴",
            "⠦",
            "⠧",
            "⠇",
            "⠏",
        ]

        index = 0

        while thread.is_alive():

            if self.cancel_requested:

                print(
                    "\n⛔ Operación cancelada localmente."
                )

                return

            print(
                f"\r🤖 Claude trabajando "
                f"{spinner[index % len(spinner)]}",
                end="",
                flush=True,
            )

            index += 1

            time.sleep(0.15)

        print(
            "\r"
            + " " * 50
            + "\r",
            end=""
        )

        result = container.get("result")

        if result is None:

            print(
                "\n❌ No se recibió respuesta de Claude."
            )

            return

        if not result.success:

            self.handle_claude_error(
                result
            )

            return

        response = result.stdout.strip()

        if not response:

            response = (
                "Claude no devolvió texto."
            )

        self.last_response = response

        print(
            "\n🤖 CLAUDE:"
        )

        print(
            "-" * 60
        )

        print(response)

        print(
            "-" * 60
        )

        self.speak_response(
            response
        )

        self.conversation.activate()

    # ========================================================
    # CLAUDE ERROR
    # ========================================================

    def handle_claude_error(self, result):

        error = (
            result.stdout
            or result.stderr
            or "Error desconocido."
        )

        print(
            "\n❌ Claude Code devolvió un error."
        )

        print(
            f"Código: {result.returncode}"
        )

        print(error)

        lower = error.lower()

        if (
            "session limit" in lower
            or "limit" in lower
        ):

            message = (
                "Claude ha alcanzado el límite "
                "de sesión. Voice Claude sigue funcionando."
            )

        elif (
            "not found" in lower
            or "no se encuentra" in lower
        ):

            message = (
                "No encuentro Claude Code."
            )

        else:

            message = (
                "Ha ocurrido un error ejecutando Claude."
            )

        self.speech.speak(
            message
        )

    # ========================================================
    # RESPONSE VOICE
    # ========================================================

    def speak_response(self, response):

        summary = self.make_voice_summary(
            response
        )

        self.speech.speak(
            summary
        )

    def make_voice_summary(self, response):

        if len(response) <= 700:
            return response

        lines = [
            line.strip()
            for line in response.splitlines()
            if line.strip()
        ]

        useful = []

        for line in lines:

            if line.startswith("```"):
                continue

            if len(line) < 180:
                useful.append(line)

            if len(" ".join(useful)) > 650:
                break

        if useful:
            return (
                "He terminado. "
                + " ".join(useful)
            )

        return (
            "He terminado. "
            "La respuesta completa está en pantalla."
        )

    # ========================================================
    # SHUTDOWN
    # ========================================================

    def shutdown(self):

        self.running = False

        try:
            keyboard.unhook_all()
        except Exception:
            pass

        print(
            "\n👋 Voice Claude terminado."
        )


def main():

    app = VoiceClaude()

    app.start()


if __name__ == "__main__":
    main()