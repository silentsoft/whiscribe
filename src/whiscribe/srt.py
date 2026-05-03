from whisper_timestamped.make_subtitles import format_timestamp


def convert_segments_to_srt(segments):
    srt_content = ""
    for segment in segments:
        index = segment["id"]
        start = format_timestamp(segment["start"], always_include_hours=True, decimal_marker=',')
        end = format_timestamp(segment["end"], always_include_hours=True, decimal_marker=',')
        text = segment["text"].strip()
        srt_content += f"{index}\n{start} --> {end}\n{text}\n\n"
    return srt_content
