"""Voice Claude: Claude Code manejado por voz.

Bucle principal: escuchar -> transcribir -> decidir si es un
comando o una peticion -> hablar.
"""

import time

import keyboard

from claude_client import ClaudeClient
from commands import detect_command, detect_wake_word, print_help
from config import (
    CLAUDE_COMMAND,
    CLAUDE_PERMISSION_MODE,
    CLAUDE_TIMEOUT,
    CONVERSATION_TIMEOUT,
    KEY_CANCEL,
    KEY_LISTEN,
    KEY_PAUSE,
    KEY_REPEAT,
    MAX_VOICE_RESPONSE_CHARS,
    VERSION,
    WAKE_WORDS,
)
from conversation import Conversation
from logger import VoiceLogger
from project import get_project_info
from speech import SpeechEngine
from tts import TextToSpeech


SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Espera maxima entre errores seguidos del bucle principal.
MAX_ERROR_BACKOFF = 10.0


class VoiceClaude:

    def __init__(self):

        self.running = True
        self.paused = False
        self.cancel_requested = False

        self.last_response = ""

        self.project = get_project_info()
        self.project_root = self.project["root"]

        self.logger = VoiceLogger()

        self.tts = TextToSpeech()
        self.speech = SpeechEngine()

        self.claude = ClaudeClient(
            project_root=self.project_root,
            command=CLAUDE_COMMAND,
            timeout=CLAUDE_TIMEOUT,
            permission_mode=CLAUDE_PERMISSION_MODE,
        )

        self.conversation = Conversation(timeout=CONVERSATION_TIMEOUT)

        self.commands = {
            "stop": self.command_stop,
            "exit": self.command_exit,
            "pause": self.toggle_pause,
            "resume": self.command_resume,
            "repeat": self.repeat_last,
            "new_session": self.command_new_session,
            "help": print_help,
        }

    # ========================================================
    # ARRANQUE
    # ========================================================

    def start(self):

        self.print_header()

        if not self.check_claude():
            return

        self.install_hotkeys()

        print_help()

        self.tts.speak(
            f"Hola. Soy {WAKE_WORDS[0].capitalize()} y estoy listo."
        )

        self.main_loop()

    def print_header(self):

        print("\n" + "=" * 60)
        print(f"🎙️  VOICE CLAUDE V{VERSION}")
        print("=" * 60)

        print("\nClaude Code controlado por voz.")

        print(f"\n🗣️ Wake word: {WAKE_WORDS[0].capitalize()}")
        print(f"\n📁 Proyecto:\n   {self.project_root}")

        if self.project["branch"]:
            print(f"\n🌿 Git:\n   {self.project['branch']}")

        print(f"\n🧩 Detectado:\n   {', '.join(self.project['types'])}")

        if self.tts.voice_name:
            print(f"\n🔊 Voz:\n   {self.tts.voice_name}")

        print(f"\n🔐 Permisos de Claude:\n   {CLAUDE_PERMISSION_MODE}")

    def check_claude(self):

        print("\n🔎 Comprobando Claude CLI...")
        print(f"   {self.claude.command}")

        ok, message = self.claude.check()

        if not ok:
            print("\n❌ Claude CLI no disponible.")
            print(message)
            return False

        print(f"✅ Claude CLI encontrado. {message}")

        return True

    # ========================================================
    # TECLADO
    # ========================================================

    def install_hotkeys(self):

        hotkeys = (
            (KEY_LISTEN, self.force_listen),
            (KEY_PAUSE, self.toggle_pause),
            (KEY_REPEAT, self.repeat_last),
            (KEY_CANCEL, self.cancel_all),
        )

        try:
            for key, action in hotkeys:
                keyboard.add_hotkey(key, action)

        except Exception as error:
            # keyboard necesita permisos de administrador en
            # algunas configuraciones de Windows.
            print(f"\n⚠️ No pude registrar los atajos de teclado: {error}")

    def force_listen(self):
        """Escucha ahora mismo, sin necesidad de wake word."""

        self.paused = False

        self.tts.stop()
        self.speech.abort()

        self.conversation.activate()

        print("\n⌨️ F8 → te escucho, habla sin wake word.")

    def toggle_pause(self):

        self.paused = not self.paused

        if self.paused:
            self.tts.stop()
            self.speech.abort()
            print("\n⏸️ Voice Claude pausado.")

        else:
            print("\n▶️ Voice Claude reanudado.")

    def repeat_last(self):

        if not self.last_response:
            print("\nℹ️ No hay respuesta para repetir.")
            return

        self.tts.say(self.summarize_for_voice(self.last_response))

    def cancel_all(self):

        print("\n⛔ CANCELAR")

        self.cancel_requested = True

        self.tts.stop()
        self.speech.abort()
        self.claude.cancel()

    # ========================================================
    # BUCLE PRINCIPAL
    # ========================================================

    def main_loop(self):

        print(f"\n🎧 Esperando a que digas {WAKE_WORDS[0].capitalize()}...")

        backoff = 0.0

        while self.running:

            try:

                if self.paused:
                    time.sleep(0.2)
                    continue

                # Nunca grabamos mientras Claude habla: el
                # microfono captaria su propia voz por los
                # altavoces y se la mandaria a Whisper.
                self.tts.wait_until_done(timeout=CLAUDE_TIMEOUT)

                if self.paused or not self.running:
                    continue

                text = self.speech.listen()

                backoff = 0.0

                if not text:
                    continue

                print(f"\n👤 Tú:\n{text}")

                self.logger.write("USER", text)

                self.handle_utterance(text)

            except KeyboardInterrupt:
                break

            except Exception as error:
                print(f"\n❌ Error: {error}")

                # Si el fallo se repite (por ejemplo el micro
                # desconectado) esperamos cada vez mas en lugar
                # de girar en vacio.
                backoff = min(max(backoff * 2, 1.0), MAX_ERROR_BACKOFF)

                time.sleep(backoff)

        self.shutdown()

    # ========================================================
    # INTERPRETAR LO QUE SE HA DICHO
    # ========================================================

    def handle_utterance(self, text):
        """Decide que hacer con una frase transcrita.

        Orden: primero la wake word, y solo despues los comandos.
        Un comando exige que la frase entera sea ese comando, de
        forma que "escribe un test para el login" llegue a Claude
        en lugar de interpretarse como la orden "para".
        """

        wake_word, rest = detect_wake_word(text)

        if wake_word:
            print(f"\n🗣️ Wake word: {wake_word}")

            self.conversation.activate()

            if not rest:
                self.tts.say("Dime.")
                return

            if self.run_command(rest):
                return

            self.send_to_claude(rest)
            return

        if self.run_command(text):
            return

        if self.conversation.should_accept_without_wake_word():
            self.send_to_claude(text)

    def run_command(self, text):
        """Ejecuta el comando dictado. Devuelve si lo habia."""

        name = detect_command(text)

        if not name:
            return False

        print(f"\n🎛️ Comando: {name}")

        self.commands[name]()

        return True

    # ========================================================
    # COMANDOS
    # ========================================================

    def command_stop(self):
        self.cancel_all()
        self.tts.say("Detenido.")

    def command_exit(self):
        self.cancel_all()
        self.tts.speak("Hasta luego.")
        self.running = False

    def command_resume(self):
        self.paused = False
        self.tts.say("Continuamos.")

    def command_new_session(self):
        self.conversation.reset()
        self.claude.reset_session()
        self.last_response = ""
        self.tts.say("Nueva conversación.")

    # ========================================================
    # PETICION A CLAUDE
    # ========================================================

    def send_to_claude(self, prompt):

        prompt = (prompt or "").strip()

        if not prompt:
            return

        self.cancel_requested = False

        final_prompt = self.conversation.build_prompt(prompt, self.project)

        self.conversation.add_user(prompt)
        self.logger.write("CLAUDE_REQUEST", prompt)

        print("\n🤖 Enviando a Claude...")

        thread, container = self.claude.ask_async(final_prompt)

        self.wait_with_spinner(thread)

        result = container.get("result")

        if result is None:
            if self.cancel_requested:
                return

            print("\n❌ No hubo respuesta.")
            return

        if result.cancelled:
            print("\n⛔ Claude cancelado.")
            return

        if not result.success:
            self.handle_error(result)
            return

        self.deliver(result)

    def wait_with_spinner(self, thread):

        index = 0

        while thread.is_alive():

            if self.cancel_requested:
                self.claude.cancel()
                print("\n⛔ Petición cancelada.")
                thread.join(timeout=5)
                return

            print(
                f"\r🤖 Claude {SPINNER[index % len(SPINNER)]}",
                end="",
                flush=True,
            )

            index += 1

            time.sleep(0.15)

        print("\r" + " " * 60 + "\r", end="")

    def deliver(self, result):

        response = result.text or "Claude no devolvió texto."

        self.last_response = response

        self.conversation.add_assistant(response)
        self.logger.write("CLAUDE_RESPONSE", response)

        print("\n🤖 CLAUDE:")
        print("-" * 60)
        print(response)
        print("-" * 60)

        if result.cost_usd:
            print(f"💰 {result.cost_usd:.4f} USD")

        self.tts.say(self.summarize_for_voice(response))

    # ========================================================
    # ERRORES
    # ========================================================

    def handle_error(self, result):

        detail = result.error or result.text or "Error desconocido."

        print("\n❌ Claude Code devolvió un error.")
        print(f"Código: {result.returncode}")
        print(detail)

        self.logger.write("CLAUDE_ERROR", detail)

        lowered = detail.lower()

        if "limit" in lowered and ("session" in lowered or "usage" in lowered):
            message = "Claude ha alcanzado el límite de uso."

        elif "authentication" in lowered or "login" in lowered:
            message = "Claude necesita autenticación."

        elif "permission" in lowered:
            message = "Claude no tiene permisos para hacer eso."

        else:
            message = "Ha ocurrido un error ejecutando Claude."

        self.tts.say(message)

    # ========================================================
    # RESPUESTA HABLADA
    # ========================================================

    @staticmethod
    def summarize_for_voice(response):
        """Recorta una respuesta larga para leerla en voz alta."""

        if len(response) <= MAX_VOICE_RESPONSE_CHARS:
            return response

        lines = []
        total = 0

        for line in response.splitlines():

            line = line.strip()

            if not line or line.startswith("```"):
                continue

            if len(line) >= 180:
                continue

            lines.append(line)
            total += len(line) + 1

            if total >= 700:
                break

        if not lines:
            return "He terminado. La respuesta completa está en pantalla."

        return (
            "He terminado. "
            + " ".join(lines)
            + " La respuesta completa está en pantalla."
        )

    # ========================================================
    # CIERRE
    # ========================================================

    def shutdown(self):

        self.running = False

        self.tts.stop()
        self.claude.cancel()
        self.speech.close()
        self.tts.close()

        try:
            keyboard.unhook_all()
        except Exception:
            pass

        print("\n👋 Voice Claude terminado.")


def main():
    VoiceClaude().start()


if __name__ == "__main__":
    main()
