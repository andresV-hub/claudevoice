"""Pruebas del estado de la conversacion."""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conversation import Conversation  # noqa: E402


PROYECTO = {
    "name": "voice-claude",
    "root": "C:/proyectos/voice-claude",
    "types": ["Python"],
    "branch": "main",
}


class TestVentanaDeConversacion(unittest.TestCase):

    def test_empieza_inactiva(self):
        conversation = Conversation()

        self.assertTrue(conversation.expired())
        self.assertFalse(conversation.should_accept_without_wake_word())

    def test_acepta_tras_activar(self):
        conversation = Conversation(timeout=60)
        conversation.activate()

        self.assertTrue(conversation.should_accept_without_wake_word())

    def test_caduca_pasado_el_tiempo(self):
        conversation = Conversation(timeout=0.05)
        conversation.activate()

        time.sleep(0.1)

        self.assertFalse(conversation.should_accept_without_wake_word())
        self.assertFalse(conversation.active)


class TestHistorial(unittest.TestCase):

    def test_recorta_al_maximo(self):
        conversation = Conversation(max_turns=4)

        for index in range(10):
            conversation.add_user(f"peticion {index}")

        self.assertEqual(len(conversation.turns), 4)
        self.assertEqual(conversation.turns[-1]["content"], "peticion 9")

    def test_ignora_texto_vacio(self):
        conversation = Conversation()

        conversation.add_user("")
        conversation.add_assistant("   ")

        self.assertEqual(conversation.turns, [])

    def test_guarda_la_ultima_respuesta(self):
        conversation = Conversation()
        conversation.add_assistant("  Listo.  ")

        self.assertEqual(conversation.last_assistant_response, "Listo.")


class TestPrompt(unittest.TestCase):

    def test_presenta_el_proyecto_solo_una_vez(self):
        conversation = Conversation()

        primero = conversation.build_prompt("abre app.py", PROYECTO)

        self.assertIn("voice-claude", primero)
        self.assertIn("Rama Git: main", primero)
        self.assertIn("abre app.py", primero)

        # Claude ya conserva el contexto en su propia sesion.
        segundo = conversation.build_prompt("ahora ejecútalo", PROYECTO)

        self.assertEqual(segundo, "ahora ejecútalo")

    def test_reset_vuelve_a_presentar_el_proyecto(self):
        conversation = Conversation()
        conversation.build_prompt("hola", PROYECTO)
        conversation.reset()

        self.assertIn("Proyecto:", conversation.build_prompt("hola", PROYECTO))

    def test_prompt_vacio(self):
        self.assertEqual(Conversation().build_prompt("   ", PROYECTO), "")


if __name__ == "__main__":
    unittest.main()
