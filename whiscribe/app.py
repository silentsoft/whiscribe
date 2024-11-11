import streamlit as st
import locale
import tempfile
from whisper import tokenizer
from transcriber import Transcriber
from audio import get_audio_tracks, extract_audio_track
from srt import convert_segments_to_srt


st.title("Whiscribe")
st.subheader("Audio to Subtitles")

model_size = st.selectbox("Select Whisper Model", ["tiny", "base", "small", "medium", "large", "turbo"], index=5)

system_language_code, _ = locale.getdefaultlocale()
system_language_code = system_language_code.split('_')[0] if system_language_code else "en"
default_language_index = list(tokenizer.LANGUAGES.keys()).index(system_language_code) if system_language_code in tokenizer.LANGUAGES else 0
language_name = st.selectbox("Select Whisper Language", list(tokenizer.LANGUAGES.values()), index=default_language_index)
language_code = tokenizer.TO_LANGUAGE_CODE[language_name]

audio_file = st.file_uploader("Select an audio file (mp3, wav, mp4)", type=["mp3", "wav", "mp4"])

if audio_file is not None:
    transcriber = Transcriber(model_size)

    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(audio_file.read())
        temp_file_path = temp_file.name

        if audio_file.type == "video/mp4":
            audio_tracks = get_audio_tracks(temp_file_path)

            if audio_tracks:
                track_options = [f"Track {i + 1}: {track['codec_name']} ({track['tags'].get('language', 'unknown')})"
                                 for i, track in enumerate(audio_tracks)]
                selected_track = st.radio("Select an audio track to extract", track_options)
                selected_index = track_options.index(selected_track)

                st.write("Converting selected audio track to MP3...")
                audio_file_path = extract_audio_track(temp_file_path, selected_index, output_format="mp3")
                st.success(f"Audio track {selected_track} converted to MP3.")
            else:
                st.error("No audio tracks found in the uploaded MP4 file.")
                audio_file_path = None
        else:
            audio_file_path = temp_file_path

        if audio_file_path is not None:
            run = st.button("Generate", use_container_width=True)
            if run:
                segments = transcriber.transcribe(audio_file_path, language_code)
                srt_content = convert_segments_to_srt(segments)

                st.success("Subtitles generated successfully!")
                st.download_button(f"Download {audio_file.name}.srt", data=srt_content, file_name=f"{audio_file.name}.srt")
