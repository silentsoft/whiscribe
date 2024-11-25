import ssl
import whisper_timestamped


ssl._create_default_https_context = ssl._create_unverified_context


class Transcriber:
    def __init__(self, model_size="base"):
        self.model = whisper_timestamped.load_model(model_size)

    def transcribe(self, audio_file, language="en"):
        result = whisper_timestamped.transcribe(self.model,
                                                audio_file,
                                                language=language,
                                                condition_on_previous_text=False)
        return result["segments"]
