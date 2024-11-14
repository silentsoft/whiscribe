import tempfile
import ffmpeg


def get_audio_tracks(file_path):
    probe = ffmpeg.probe(file_path)
    audio_tracks = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
    return audio_tracks


def extract_audio_track(file_path, track_index, output_format="mp3"):
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}")
    ffmpeg.input(file_path).output(output_file.name, map=f"0:a:{track_index}").overwrite_output().run()
    return output_file.name