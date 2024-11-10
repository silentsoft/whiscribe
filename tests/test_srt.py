import pytest
from whiscribe.srt import convert_segments_to_srt


def test_convert_segments_to_srt():
    segments = [
        {"id": 1, "start": 0.0, "end": 5.0, "text": "Hello world"},
        {"id": 2, "start": 5.0, "end": 10.0, "text": "This is a test"}
    ]
    srt_content = convert_segments_to_srt(segments)
    assert "1\n00:00:00,000 --> 00:00:05,000\nHello world\n" in srt_content
    assert "2\n00:00:05,000 --> 00:00:10,000\nThis is a test\n" in srt_content
