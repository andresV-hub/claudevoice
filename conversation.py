"""Estado de la conversacion de voz.

Claude mantiene su propio contexto a traves de la sesion que
reanudamos con ``--resume``, asi que aqui ya no se reenvia el
historial en cada prompt. Esta clase se ocupa de dos cosas:

* la ventana de tiempo durante la cual puedes seguir hablando
  sin repetir la wake word,
* un historial corto para los logs y para "repite".
"""

import time

from config import CONVERSATION_MAX_TURNS, CONVERSATION_TIMEOUT


class Conversation:

    def __init__(
        self,
        timeout=CONVERSATION_TIMEOUT,
        max_turns=CONVERSATION_MAX_TURNS,
    ):

        self.timeout = timeout
        self.max_turns = max_turns

        self.active = False
        self.last_activity = 0.0

        self.turns = []
        self.last_assistant_response = ""

        # La primera peticion de cada sesion lleva la ficha del
        # proyecto; las siguientes ya no hacen falta.
        self.introduced = False

    # ========================================================
    # VENTANA DE CONVERSACION
    # ========================================================

    def activate(self):
        self.active = True
        self.touch()

    def deactivate(self):
        self.active = False

    def touch(self):
        self.last_activity = time.time()

    def expired(self):

        if not self.active:
            return True

        return (time.time() - self.last_activity) > self.timeout

    def should_accept_without_wake_word(self):
        """Indica si una frase suelta cuenta como peticion."""

        if self.expired():
            self.deactivate()
            return False

        self.touch()

        return True

    # ========================================================
    # HISTORIAL
    # ========================================================

    def add_user(self, text):
        self._add("user", text)

    def add_assistant(self, text):

        if text and text.strip():
            self.last_assistant_response = text.strip()

        self._add("assistant", text)

    def _add(self, role, text):

        if not text or not text.strip():
            return

        self.turns.append(
            {
                "role": role,
                "content": text.strip(),
                "time": time.time(),
            }
        )

        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

        self.touch()

    # ========================================================
    # PROMPT
    # ========================================================

    def build_prompt(self, user_text, project=None):
        """Construye el prompt que se manda a la CLI.

        La ficha del proyecto solo viaja en la primera peticion
        de la sesion. Repetirla en cada turno gastaba tokens sin
        aportar nada, porque Claude ya la tiene en su contexto.
        """

        user_text = (user_text or "").strip()

        if not user_text:
            return ""

        if self.introduced or not project:
            return user_text

        self.introduced = True

        lines = [
            "Estás siendo controlado por voz desde Voice Claude.",
            "Responde en español, de forma breve y directa: tus",
            "respuestas se leen en voz alta.",
            "",
            f"Proyecto: {project.get('name', '')}",
            f"Directorio: {project.get('root', '')}",
        ]

        types = project.get("types") or []

        if types:
            lines.append(f"Tipo: {', '.join(types)}")

        if project.get("branch"):
            lines.append(f"Rama Git: {project['branch']}")

        lines += ["", "PETICIÓN DEL USUARIO:", user_text]

        return "\n".join(lines)

    # ========================================================
    # ESTADO
    # ========================================================

    def reset(self):

        self.active = False
        self.last_activity = 0.0
        self.introduced = False

        self.turns.clear()
        self.last_assistant_response = ""

    def status(self):

        return {
            "active": self.active,
            "turns": len(self.turns),
            "expired": self.expired(),
            "seconds_since_activity": (
                time.time() - self.last_activity if self.last_activity else None
            ),
        }
