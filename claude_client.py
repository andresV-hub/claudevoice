"""Puente con la CLI de Claude Code.

Tres decisiones importantes:

* El prompt viaja por stdin, no como argumento. La linea de
  comandos de Windows tiene un limite de unos 32 KB y un prompt
  con contexto lo alcanza antes de lo que parece.

* Se usa ``--output-format json``, que devuelve el texto de la
  respuesta ya separado de los metadatos e indica si hubo error.

* Se guarda el ``session_id`` y se reanuda con ``--resume``, asi
  que Claude conserva su propio contexto entre peticiones y no
  hay que reenviarle el historial en cada prompt.
"""

import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

from console import configure_console

configure_console()


class ClaudeResult:

    def __init__(
        self,
        success,
        text="",
        error="",
        returncode=0,
        cancelled=False,
        session_id=None,
        cost_usd=None,
    ):
        self.success = success
        self.text = (text or "").strip()
        self.error = (error or "").strip()
        self.returncode = returncode
        self.cancelled = cancelled
        self.session_id = session_id
        self.cost_usd = cost_usd


class ClaudeClient:

    def __init__(
        self,
        project_root,
        command="claude",
        timeout=600,
        permission_mode="acceptEdits",
    ):

        self.project_root = str(project_root)
        self.timeout = timeout
        self.permission_mode = permission_mode

        self.command = self.find_claude(command)

        self.session_id = None

        self.process = None
        self.lock = threading.Lock()
        self.cancelled = False

    # ========================================================
    # LOCALIZAR LA CLI
    # ========================================================

    @staticmethod
    def find_claude(command):

        found = shutil.which(command)

        if found:
            return found

        names = ("claude.cmd", "claude.exe", "claude")

        roots = (
            Path(os.environ.get("APPDATA", "")) / "npm",
            Path(os.environ.get("LOCALAPPDATA", "")) / "npm",
            Path.home() / ".local" / "bin",
            Path.home() / ".claude" / "local",
        )

        for root in roots:
            for name in names:
                candidate = root / name

                try:
                    if candidate.exists():
                        return str(candidate)
                except OSError:
                    continue

        return command

    # ========================================================
    # COMPROBACION
    # ========================================================

    def check(self):

        try:
            result = subprocess.run(
                [self.command, "--version"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )

            output = result.stdout.strip() or result.stderr.strip()

            return result.returncode == 0, output

        except Exception as error:
            return False, str(error)

    # ========================================================
    # SESION
    # ========================================================

    def reset_session(self):
        """Olvida la sesion actual: la siguiente peticion empieza de cero."""

        self.session_id = None

    def _build_args(self, resume):

        args = [
            self.command,
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            self.permission_mode,
        ]

        if resume and self.session_id:
            args += ["--resume", self.session_id]

        return args

    # ========================================================
    # PETICION
    # ========================================================

    def ask(self, prompt):
        """Envia un prompt y espera la respuesta.

        Si reanudar la sesion falla (por ejemplo porque se borro
        el historial) se reintenta una vez empezando de cero.
        """

        result = self._run(prompt, resume=True)

        session_lost = (
            not result.success
            and not result.cancelled
            and self.session_id
            and self._looks_like_lost_session(result)
        )

        if session_lost:
            print("\n⚠️ La sesion anterior ya no existe. Empiezo una nueva.")

            self.reset_session()

            result = self._run(prompt, resume=False)

        return result

    @staticmethod
    def _looks_like_lost_session(result):

        haystack = f"{result.error} {result.text}".lower()

        return any(
            hint in haystack
            for hint in ("session", "resume", "not found", "no conversation")
        )

    def _run(self, prompt, resume):

        with self.lock:

            if self.process is not None:
                return ClaudeResult(
                    False,
                    error="Claude ya está ejecutando otra petición.",
                    returncode=-10,
                )

            self.cancelled = False

            try:
                self.process = subprocess.Popen(
                    self._build_args(resume),
                    cwd=self.project_root,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=os.environ.copy(),
                    creationflags=(
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        if os.name == "nt"
                        else 0
                    ),
                )

            except FileNotFoundError:
                self.process = None

                return ClaudeResult(
                    False,
                    error=(
                        "No encuentro la CLI de Claude. "
                        "Instalala con: npm install -g @anthropic-ai/claude-code"
                    ),
                    returncode=-1,
                )

            except Exception as error:
                self.process = None

                return ClaudeResult(False, error=str(error), returncode=-3)

            process = self.process

        try:
            stdout, stderr = process.communicate(
                input=prompt,
                timeout=self.timeout,
            )

        except subprocess.TimeoutExpired:
            self.cancel()

            return ClaudeResult(
                False,
                error="Claude superó el tiempo máximo.",
                returncode=-2,
                cancelled=True,
            )

        except Exception as error:
            return ClaudeResult(False, error=str(error), returncode=-3)

        finally:
            with self.lock:
                self.process = None

        if self.cancelled:
            return ClaudeResult(False, cancelled=True, returncode=-4)

        return self._parse(stdout, stderr, process.returncode)

    # ========================================================
    # RESPUESTA
    # ========================================================

    def _parse(self, stdout, stderr, returncode):

        stdout = (stdout or "").strip()
        stderr = (stderr or "").strip()

        try:
            payload = json.loads(stdout)

        except (ValueError, TypeError):
            # Sin JSON valido nos quedamos con el texto tal cual.
            return ClaudeResult(
                success=(returncode == 0 and bool(stdout)),
                text=stdout,
                error=stderr or ("Respuesta ilegible de Claude." if stdout else ""),
                returncode=returncode,
            )

        if isinstance(payload, list):
            payload = payload[-1] if payload else {}

        if not isinstance(payload, dict):
            payload = {}

        session_id = payload.get("session_id")

        if session_id:
            self.session_id = session_id

        text = payload.get("result") or ""
        is_error = bool(payload.get("is_error")) or returncode != 0

        return ClaudeResult(
            success=not is_error,
            text=text,
            error=(text if is_error else "") or stderr,
            returncode=returncode,
            session_id=session_id,
            cost_usd=payload.get("total_cost_usd"),
        )

    # ========================================================
    # CANCELAR
    # ========================================================

    def cancel(self):

        with self.lock:

            process = self.process

            if process is None:
                return False

            self.cancelled = True
            self.process = None

        # Matar va antes que escribir: si la consola falla al
        # imprimir, Claude tiene que morir igualmente.
        try:
            if process.poll() is None:
                self._kill_tree(process)

            print("\n⛔ Claude detenido.")

            return True

        except Exception as error:
            print(f"\n⚠️ No pude terminar Claude: {error}")
            return False

    @staticmethod
    def _kill_tree(process):
        """Mata el proceso y sus hijos.

        En Windows la CLI es un .cmd que lanza node: matar solo el
        .cmd deja a node trabajando en el proyecto por su cuenta.
        """

        if os.name == "nt":
            try:
                subprocess.run(
                    [
                        "taskkill",
                        "/F",
                        "/T",
                        "/PID",
                        str(process.pid),
                    ],
                    capture_output=True,
                    timeout=10,
                )

                return

            except Exception:
                pass

        process.kill()

        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass

    # ========================================================
    # ASINCRONO
    # ========================================================

    def ask_async(self, prompt):
        """Lanza la peticion en segundo plano.

        Devuelve el hilo y un contenedor donde aparecera el
        ``ClaudeResult`` cuando termine.
        """

        container = {}

        def worker():
            try:
                container["result"] = self.ask(prompt)

            except Exception as error:
                container["result"] = ClaudeResult(
                    False,
                    error=str(error),
                    returncode=-3,
                )

        thread = threading.Thread(target=worker, name="claude", daemon=True)
        thread.start()

        return thread, container
