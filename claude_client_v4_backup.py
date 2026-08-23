import os
import shutil
import subprocess
from pathlib import Path


class ClaudeResult:

    def __init__(
        self,
        success,
        stdout="",
        stderr="",
        returncode=0,
    ):
        self.success = success
        self.stdout = stdout.strip()
        self.stderr = stderr.strip()
        self.returncode = returncode


class ClaudeClient:

    def __init__(
        self,
        project_root,
        command="claude",
        timeout=600,
    ):
        self.project_root = str(project_root)
        self.timeout = timeout

        # ------------------------------------------------
        # Buscar Claude en Windows
        # ------------------------------------------------

        self.command = self.find_claude(command)

    def find_claude(self, command):

        # 1. Intentar PATH de Python
        found = shutil.which(command)

        if found:
            return found

        # 2. Ubicación conocida de npm en Windows
        candidates = [
            Path(
                os.environ.get("APPDATA", "")
            ) / "npm" / "claude.cmd",

            Path(
                os.environ.get("APPDATA", "")
            ) / "npm" / "claude",

            Path(
                os.environ.get("LOCALAPPDATA", "")
            ) / "npm" / "claude.cmd",

            Path(
                os.environ.get("LOCALAPPDATA", "")
            ) / "npm" / "claude",
        ]

        for candidate in candidates:

            if candidate.exists():
                return str(candidate)

        # 3. Fallback
        return command

    # ====================================================
    # CHECK
    # ====================================================

    def check(self):

        print(
            f"🔎 Claude encontrado en:\n"
            f"   {self.command}"
        )

        try:

            result = subprocess.run(
                [
                    self.command,
                    "--version",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                shell=False,
            )

            output = (
                result.stdout.strip()
                or result.stderr.strip()
            )

            if result.returncode == 0:

                return True, output

            return False, output

        except FileNotFoundError:

            return (
                False,
                "Claude CLI no encontrado."
            )

        except Exception as e:

            return False, str(e)

    # ====================================================
    # ASK
    # ====================================================

    def ask(self, prompt):

        try:

            result = subprocess.run(
                [
                    self.command,
                    "-p",
                    prompt,
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                shell=False,
                env=os.environ.copy(),
            )

            return ClaudeResult(
                success=(
                    result.returncode == 0
                ),
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )

        except FileNotFoundError:

            return ClaudeResult(
                False,
                stderr=(
                    "No encuentro Claude CLI.\n"
                    f"Ruta utilizada: {self.command}"
                ),
                returncode=-1,
            )

        except subprocess.TimeoutExpired:

            return ClaudeResult(
                False,
                stderr=(
                    "Claude tardó demasiado "
                    "en responder."
                ),
                returncode=-2,
            )

        except Exception as e:

            return ClaudeResult(
                False,
                stderr=str(e),
                returncode=-3,
            )

    # ====================================================
    # ASYNC
    # ====================================================

    def ask_async(self, prompt):

        import threading

        result_container = {}

        def worker():

            result_container["result"] = (
                self.ask(prompt)
            )

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        thread.start()

        return thread, result_container