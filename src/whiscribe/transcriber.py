import os
import sys
import ssl
import whisper_timestamped


ssl._create_default_https_context = ssl._create_unverified_context


def _get_models_dir():
    platform_name = sys.platform
    if platform_name.startswith("darwin"):
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    elif platform_name.startswith("win"):
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "Whiscribe", "models")


class Transcriber:
    def __init__(self, model_size="base"):
        self.model = whisper_timestamped.load_model(model_size, download_root=_get_models_dir())

    def transcribe(self, audio_file, language="en", initial_prompt=None):
        result = whisper_timestamped.transcribe(self.model,
                                                audio_file,
                                                language=language,
                                                initial_prompt=initial_prompt,
                                                condition_on_previous_text=False)
        return result["segments"]
