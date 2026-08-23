import os
import subprocess
import uuid

from config import CLAUDE_CMD


class ClaudeClient:

    def __init__(self, project_dir=None):

        self.session_id = str(uuid.uuid4())

        self.started = False

        if project_dir:
            self.project_dir = os.path.abspath(project_dir)
        else:
            self.project_dir = os.getcwd()

    # ========================================================
    # COMPROBAR CLAUDE
    # ========================================================

    def check(self):

        print()
        print("🔎 Comprobando Claude CLI...")

        if not os.path.exists(CLAUDE_CMD):

            print()
            print("❌ No encuentro Claude CLI:")
            print(CLAUDE_CMD)

            return False

        try:

            resultado = subprocess.run(
                [
                    "cmd.exe",
                    "/c",
                    CLAUDE_CMD,
                    "--version",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_dir,
            )

            if resultado.returncode != 0:

                print()
                print("❌ Claude CLI devolvió un error.")

                if resultado.stderr:
                    print(resultado.stderr)

                return False

            print("✅ Claude CLI encontrado.")
            print(resultado.stdout.strip())

            print()
            print("📁 Proyecto:")
            print(self.project_dir)

            return True

        except Exception as e:

            print()
            print("❌ Error comprobando Claude:")
            print(e)

            return False

    # ========================================================
    # PREGUNTAR A CLAUDE
    # ========================================================

    def ask(self, prompt):

        print()
        print("🤖 Enviando a Claude...")
        print()
        print("📁 Proyecto:")
        print(self.project_dir)
        print()

        if not os.path.exists(CLAUDE_CMD):

            return (
                "No encuentro Claude CLI."
            )

        try:

            if not self.started:

                command = [
                    "cmd.exe",
                    "/c",
                    CLAUDE_CMD,
                    "-p",
                    prompt,
                    "--session-id",
                    self.session_id,
                ]

                self.started = True

            else:

                command = [
                    "cmd.exe",
                    "/c",
                    CLAUDE_CMD,
                    "-p",
                    prompt,
                    "--resume",
                    self.session_id,
                ]

            resultado = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_dir,
            )

            if resultado.returncode != 0:

                print()
                print(
                    "❌ Claude CLI devolvió un error."
                )

                print(
                    "Código:",
                    resultado.returncode
                )

                if resultado.stdout:
                    print()
                    print("STDOUT:")
                    print(resultado.stdout)

                if resultado.stderr:
                    print()
                    print("STDERR:")
                    print(resultado.stderr)

                return self._crear_mensaje_error(
                    resultado
                )

            respuesta = (
                resultado.stdout.strip()
            )

            if not respuesta:

                return (
                    "Claude no ha devuelto "
                    "ninguna respuesta."
                )

            return respuesta

        except Exception as e:

            print()
            print(
                "❌ Error ejecutando Claude:"
            )

            print(repr(e))

            return (
                "Error ejecutando Claude: "
                + str(e)
            )

    # ========================================================
    # ERRORES
    # ========================================================

    def _crear_mensaje_error(
        self,
        resultado
    ):

        salida = (
            resultado.stdout
            or resultado.stderr
            or ""
        ).strip()

        if "session limit" in salida.lower():

            return (
                "Claude ha alcanzado el "
                "límite de sesión. "
                "Espera a que se restablezca "
                "tu límite de uso."
            )

        if salida:

            return (
                "Claude ha devuelto un error: "
                + salida
            )

        return (
            "Claude ha devuelto "
            "un error sin detalles."
        )