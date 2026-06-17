"""SRT generation and subtitle burn filters."""
from __future__ import annotations
from pathlib import Path
from .models import ScriptSegment
from .utils import seconds_to_srt_time

def generate_srt(segments: list[ScriptSegment], output_path: Path) -> Path:
    """Generate an SRT file from script segments."""
    output_path.parent.mkdir(parents=True, exist_ok=True); cursor=0.0; lines=[]
    for idx, seg in enumerate(segments, 1):
        start, end = cursor, cursor + seg.estimated_duration
        lines += [str(idx), f"{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}", seg.text, ""]
        cursor = end
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

def subtitle_filter(srt_path: Path) -> str:
    return f"subtitles='{str(srt_path).replace(':','\\:')}':force_style='FontName=Arial,FontSize=28,BackColour=&H80000000,BorderStyle=4'"
