import tempfile
import ffmpeg


def get_audio_tracks(file_path):
    probe = ffmpeg.probe(file_path)
    audio_tracks = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
    return audio_tracks


def extract_audio_track(file_path, track_index, output_format="ogg"):
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}")
    config = {
        "map": f"0:a:{track_index}",
        "ar": "24000",
        "b:a": "32k",
        "c:a": "libopus"
    }
    ffmpeg.input(file_path).output(output_file.name, **config).overwrite_output().run()
    return output_file.name