import streamlit as st
import locale
import tempfile
from whisper import tokenizer
from transcriber import Transcriber
from audio import get_audio_tracks, extract_audio_track
from srt import convert_segments_to_srt


@st.cache_data
def copy_file_to_temp_dir(file):
    _copied_file = None
    if file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file.read())
            _copied_file = temp_file.name
    return _copied_file


@st.cache_data
def extract_audio_tracks(file, _tracks):
    _extracted_tracks = []
    for i, track in enumerate(_tracks):
        _extracted_tracks.append((track, extract_audio_track(file, i)))
    return _extracted_tracks


@st.cache_resource
def load_transcriber(_model_size):
    return Transcriber(_model_size)


st.set_page_config(
    page_title="Whiscribe",
    menu_items={
        "Report a bug": "https://github.com/silentsoft/whiscribe/issues",
        "About": "- Author: [silentsoft](https://github.com/silentsoft)\n"
                 "- Source Code: [GitHub](https://github.com/silentsoft/whiscribe)"
    }
)

st.title("Whiscribe")
st.subheader("Audio to Subtitles")

model_size = st.selectbox("Select Whisper Model", ["tiny", "base", "small", "medium", "large", "turbo"], index=5)

system_language_code, _ = locale.getdefaultlocale()
system_language_code = system_language_code.split('_')[0] if system_language_code else "en"
default_language_index = list(tokenizer.LANGUAGES.keys()).index(system_language_code) if system_language_code in tokenizer.LANGUAGES else 0
language_name = st.selectbox("Select Whisper Language", list(tokenizer.LANGUAGES.values()), index=default_language_index)
language_code = tokenizer.TO_LANGUAGE_CODE[language_name]

selected_audio_file = st.file_uploader("Select an audio file")
if selected_audio_file is not None:
    temp_file_path = copy_file_to_temp_dir(selected_audio_file)
    audio_tracks = get_audio_tracks(temp_file_path)
    if audio_tracks:
        extracted_tracks = extract_audio_tracks(temp_file_path, audio_tracks)

        tracks = [f"Track {i + 1}: {track['codec_name']}" for i, (track, _) in enumerate(extracted_tracks)]
        selected_track = st.selectbox("Select an audio track to extract", tracks, index=0)
        selected_index = tracks.index(selected_track)
        st.audio(extracted_tracks[selected_index][1])

        run = st.button("Generate", use_container_width=True)
        if run:
            transcriber = load_transcriber(model_size)
            with st.spinner("Generating subtitles..."):
                audio_file_path = extracted_tracks[selected_index][1]
                segments = transcriber.transcribe(audio_file_path, language_code)
                st.session_state["srt_content"] = convert_segments_to_srt(segments)
                st.toast("Subtitles generated successfully!")

        if "srt_content" in st.session_state:
            edited_srt_content = st.text_area("Generated Subtitles", value=st.session_state["srt_content"], height=280)
            st.session_state["srt_content"] = edited_srt_content
            st.download_button(f"Download {selected_audio_file.name}.srt",
                               data=edited_srt_content,
                               file_name=f"{selected_audio_file.name}.srt",
                               type="primary",
                               use_container_width=True)
    else:
        st.error("No audio tracks found in the file.")
