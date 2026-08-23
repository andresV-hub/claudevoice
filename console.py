"""Preparacion de la salida por consola.

La consola de Windows y, sobre todo, la salida redirigida a un
fichero usan cp1252, que no sabe escribir los emojis de la
interfaz: cualquier print con un emoji aborta el programa con
UnicodeEncodeError.

Este modulo no depende de nada mas para que cualquier otro pueda
importarlo sin arrastrar configuracion.
"""

import sys


def configure_console():
    """Fuerza UTF-8 en stdout y stderr. Es idempotente."""

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
