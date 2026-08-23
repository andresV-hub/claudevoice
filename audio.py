class AudioController:

    def __init__(self, speech_engine):
        self.speech = speech_engine

    def listen(self):
        audio_file = (
            self.speech.record_until_silence()
        )

        if not audio_file:
            return ""

        return self.speech.transcribe(
            audio_file
        )