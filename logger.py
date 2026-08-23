"""Registro de la conversacion en disco.

El nombre del fichero se calcula en cada escritura: una sesion
que cruce la medianoche pasa sola al log del dia siguiente en
lugar de seguir escribiendo en el del dia anterior.
"""

from datetime import datetime

from config import LOG_DIR, LOG_ENABLED


class VoiceLogger:

    def __init__(self, enabled=LOG_ENABLED, directory=LOG_DIR):
        self.enabled = enabled
        self.directory = directory

    @property
    def file(self):
        return self.directory / f"{datetime.now():%Y-%m-%d}.log"

    def write(self, role, text):

        if not self.enabled or not text:
            return

        line = f"[{datetime.now():%H:%M:%S}] {role}: {text}\n"

        try:
            self.directory.mkdir(parents=True, exist_ok=True)

            with open(self.file, "a", encoding="utf-8") as handle:
                handle.write(line)

        except Exception:
            # El log nunca debe tumbar la aplicacion.
            pass
