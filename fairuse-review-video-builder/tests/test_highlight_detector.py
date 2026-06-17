import shutil
import subprocess
from pathlib import Path

import pytest

from app.highlight_detector import _select_diverse, detect_highlights
from app.models import HighlightCandidate
from app.utils import seconds_to_timecode, timecode_to_seconds


def test_seconds_to_timecode():
    assert seconds_to_timecode(5) == "00:00:05"
    assert seconds_to_timecode(65) == "00:01:05"
    assert seconds_to_timecode(3661) == "01:01:01"


def test_timecode_to_seconds():
    assert timecode_to_seconds("00:01:05") == 65
    assert timecode_to_seconds("01:01:01") == 3661


def test_select_diverse_avoids_overlapping_highlights():
    candidates = [
        HighlightCandidate(start="00:00:05", end="00:00:10", score=90, reason="High motion", purpose="Bình luận"),
        HighlightCandidate(start="00:00:07", end="00:00:12", score=70, reason="Audio peak", purpose="Bình luận"),
        HighlightCandidate(start="00:00:25", end="00:00:30", score=60, reason="Scene change", purpose="Bình luận"),
    ]
    selected = _select_diverse(candidates, max_clips=8, min_gap=10)
    assert [c.start for c in selected] == ["00:00:05", "00:00:25"]


def _make_test_video(path: Path) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
        "-shortest", "-c:v", "libx264", "-c:a", "aac", str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg/ffprobe not installed")
def test_detect_highlights_returns_valid_list_when_video_exists(tmp_path):
    video = tmp_path / "sample video.mp4"
    _make_test_video(video)
    highlights = detect_highlights(str(video), max_clips=3, clip_duration=4)
    assert isinstance(highlights, list)
    assert highlights
    assert all(h.start and h.end and 0 <= h.score <= 100 and h.purpose for h in highlights)


def test_detect_highlights_graceful_error_when_video_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        detect_highlights(str(tmp_path / "missing.mp4"))
