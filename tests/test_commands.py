"""Pruebas del reconocimiento de wake word y comandos.

Se ejecutan con:

    python -m unittest discover tests
    pytest
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commands import detect_command, detect_wake_word, normalize  # noqa: E402


class TestNormalize(unittest.TestCase):

    def test_quita_tildes_y_mayusculas(self):
        self.assertEqual(normalize("¿Cómo Estás?"), "como estas")

    def test_quita_puntuacion(self):
        self.assertEqual(normalize("Para."), "para")
        self.assertEqual(normalize("¡Adiós!"), "adios")

    def test_conserva_la_ene(self):
        self.assertEqual(normalize("Añade una función"), "añade una funcion")

    def test_colapsa_espacios(self):
        self.assertEqual(normalize("  nueva    sesión  "), "nueva sesion")

    def test_texto_vacio(self):
        self.assertEqual(normalize(""), "")
        self.assertEqual(normalize(None), "")


class TestWakeWord(unittest.TestCase):

    def test_wake_word_con_peticion(self):
        wake, rest = detect_wake_word("Jarvis, abre app.py")

        self.assertEqual(wake, "jarvis")
        self.assertEqual(rest, "abre app.py")

    def test_wake_word_sola(self):
        wake, rest = detect_wake_word("Jarvis")

        self.assertEqual(wake, "jarvis")
        self.assertEqual(rest, "")

    def test_acepta_variantes_de_whisper(self):
        for dictado in ("Yarvis abre app.py", "Jarbis abre app.py"):
            wake, rest = detect_wake_word(dictado)

            self.assertIsNotNone(wake, dictado)
            self.assertEqual(rest, "abre app.py")

    def test_conserva_tildes_y_mayusculas_de_la_peticion(self):
        _, rest = detect_wake_word("Jarvis, ¿cómo está la Función Principal?")

        self.assertEqual(rest, "¿cómo está la Función Principal?")

    def test_sin_wake_word(self):
        self.assertEqual(detect_wake_word("abre app.py"), (None, None))

    def test_wake_word_en_medio_no_cuenta(self):
        # Solo dispara al principio de la frase.
        self.assertEqual(detect_wake_word("el nombre es Jarvis"), (None, None))

    def test_texto_vacio(self):
        self.assertEqual(detect_wake_word(""), (None, None))
        self.assertEqual(detect_wake_word("   "), (None, None))


class TestComandos(unittest.TestCase):

    def test_comandos_sueltos(self):
        casos = {
            "para": "stop",
            "Cállate": "stop",
            "cancela": "stop",
            "adiós": "exit",
            "salir": "exit",
            "pausa": "pause",
            "continúa": "resume",
            "repite": "repeat",
            "nueva conversación": "new_session",
            "ayuda": "help",
        }

        for dictado, esperado in casos.items():
            self.assertEqual(detect_command(dictado), esperado, dictado)

    def test_una_peticion_no_es_un_comando(self):
        # Esta es la regresion importante: "para" es una
        # preposicion muy comun y antes cancelaba la peticion.
        peticiones = (
            "escribe un test para el login",
            "cómo salir del bucle",
            "prepara el despliegue",
            "compara estos dos archivos",
            "explica la continuación del método",
            "para qué sirve este archivo",
        )

        for peticion in peticiones:
            self.assertIsNone(detect_command(peticion), peticion)

    def test_texto_vacio(self):
        self.assertIsNone(detect_command(""))
        self.assertIsNone(detect_command(None))


if __name__ == "__main__":
    unittest.main()
