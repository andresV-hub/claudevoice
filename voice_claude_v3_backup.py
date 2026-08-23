import re
import os

from audio import (
    grabar_audio,
    eliminar_audio,
)

from speech import (
    transcribir,
    hablar,
)

from claude_client import (
    ClaudeClient,
)

from conversation import (
    Conversation,
)

from config import (
    WAKE_WORD_ENABLED,
    WAKE_WORDS,
    EXIT_COMMANDS,
    CLEAR_COMMANDS,
    REPEAT_COMMANDS,
    PAUSE_COMMANDS,
)


# ============================================================
# UTILIDADES
# ============================================================

def limpiar_texto(texto):
    return texto.lower().strip().strip(
        " .,!?¿¡;:\"'()[]{}"
    )


def comprobar_wake_word(texto):
    """
    Comprueba si la frase empieza por una de las wake words.

    Ejemplos:
        Claude, analiza este archivo
        Claro, analiza este archivo
        Claudio, analiza este archivo
    """

    if not WAKE_WORD_ENABLED:
        return True, texto

    limpio = texto.strip()

    for wake_word in WAKE_WORDS:

        patron = (
            r"^"
            + re.escape(wake_word)
            + r"\b"
            + r"\s*[:,.-]?\s*"
        )

        match = re.match(
            patron,
            limpio,
            flags=re.IGNORECASE,
        )

        if match:

            restante = limpio[
                match.end():
            ].strip()

            return True, restante

    return False, ""


# ============================================================
# COMANDOS
# ============================================================

def mostrar_ayuda():

    print()
    print("=" * 60)
    print("COMANDOS DE VOZ")
    print("=" * 60)
    print()

    print("Wake words:")
    print("  Claude")
    print("  Claro")
    print("  Claudio")
    print()

    print("Comandos:")
    print("  salir")
    print("  terminar")
    print("  adios")
    print("  repite")
    print("  pausa")
    print("  limpia conversación")
    print("  nueva conversación")
    print()

    print("=" * 60)
    print()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("🎙️  VOICE CLAUDE V3")
    print("=" * 60)
    print()

    print(
        "Claude Code controlado por voz."
    )

    print()

    if WAKE_WORD_ENABLED:

        print(
            "Wake words activadas:"
        )

        print(
            "  " + ", ".join(WAKE_WORDS)
        )

    else:

        print(
            "Wake words desactivadas."
        )

    print()

    # ========================================================
    # COMPONENTES
    # ========================================================


    claude = ClaudeClient(
        project_dir=os.environ.get(
            "VOICE_CLAUDE_PROJECT",
            os.getcwd()
        )
    )

    conversation = Conversation()

    # ========================================================
    # COMPROBAR CLAUDE
    # ========================================================

    if not claude.check():

        print()
        print(
            "No puedo iniciar Claude."
        )

        return

    # ========================================================
    # SALUDO
    # ========================================================

    hablar(
        "Hola. Estoy listo. "
        "Puedes hablar conmigo."
    )

    print()

    mostrar_ayuda()

    # ========================================================
    # BUCLE PRINCIPAL
    # ========================================================

    while True:

        audio_file = None

        try:

            # ------------------------------------------------
            # GRABAR
            # ------------------------------------------------

            audio_file = grabar_audio()

            if not audio_file:
                continue

            # ------------------------------------------------
            # TRANSCRIBIR
            # ------------------------------------------------

            texto = transcribir(
                audio_file
            )

            eliminar_audio(
                audio_file
            )

            audio_file = None

            if not texto:

                print(
                    "❌ No he entendido nada."
                )

                continue

            # ------------------------------------------------
            # WAKE WORD
            # ------------------------------------------------

            activado, texto = (
                comprobar_wake_word(
                    texto
                )
            )

            if not activado:

                print(
                    "💤 Wake word no detectada."
                )

                continue

            # ------------------------------------------------
            # SOLO WAKE WORD
            # ------------------------------------------------

            if not texto:

                hablar(
                    "Sí, dime."
                )

                continue

            # ------------------------------------------------
            # COMANDO
            # ------------------------------------------------

            comando = limpiar_texto(
                texto
            )

            # =================================================
            # SALIR
            # =================================================

            if comando in EXIT_COMMANDS:

                hablar(
                    "Hasta luego."
                )

                break

            # =================================================
            # AYUDA
            # =================================================

            if comando in {
                "ayuda",
                "comandos",
                "qué puedo decir",
                "que puedo decir",
            }:

                mostrar_ayuda()

                hablar(
                    "Te he mostrado los comandos "
                    "disponibles en pantalla."
                )

                continue

            # =================================================
            # LIMPIAR CONVERSACIÓN
            # =================================================

            if comando in CLEAR_COMMANDS:

                conversation.clear()

                claude = ClaudeClient(
                    project_dir=os.environ.get(
                        "VOICE_CLAUDE_PROJECT",
                        os.getcwd()
                    )
                )

                hablar(
                    "Conversación limpiada. "
                    "Empezamos de nuevo."
                )

                continue

            # =================================================
            # REPETIR
            # =================================================

            if comando in REPEAT_COMMANDS:

                ultima = conversation.last()

                if ultima:

                    hablar(
                        ultima
                    )

                else:

                    hablar(
                        "Todavía no tengo "
                        "ninguna respuesta."
                    )

                continue

            # =================================================
            # PAUSA
            # =================================================

            if comando in PAUSE_COMMANDS:

                hablar(
                    "De acuerdo."
                )

                continue

            # =================================================
            # MOSTRAR PETICIÓN
            # =================================================

            print()
            print(
                "📨 Petición:"
            )

            print(
                texto
            )

            # =================================================
            # GUARDAR PREGUNTA
            # =================================================

            conversation.add_user(
                texto
            )

            # =================================================
            # CLAUDE
            # =================================================

            respuesta = claude.ask(
                texto
            )

            # =================================================
            # GUARDAR RESPUESTA
            # =================================================

            conversation.add_assistant(
                respuesta
            )

            # =================================================
            # MOSTRAR RESPUESTA
            # =================================================

            print()
            print(
                "🤖 Claude:"
            )
            print()

            print(
                respuesta
            )

            print()

            # =================================================
            # VOZ
            # =================================================

            hablar(
                respuesta
            )

            print()
            print(
                "-" * 60
            )
            print()

        except KeyboardInterrupt:

            print()
            print()
            print(
                "👋 Voice Claude terminado."
            )

            break

        except Exception as e:

            print()
            print(
                "❌ Error inesperado:"
            )

            print(
                repr(e)
            )

            try:

                hablar(
                    "Ha ocurrido un error."
                )

            except Exception:

                pass

        finally:

            if audio_file:

                eliminar_audio(
                    audio_file
                )


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    main()