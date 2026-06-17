"""Vietnamese script segmentation and clip matching."""
from __future__ import annotations
import re
from .models import ClipTimecode, ScriptSegment

def split_script(script: str, clips: list[ClipTimecode] | None = None) -> list[ScriptSegment]:
    """Split script into readable segments and estimate narration duration."""
    chunks = [c.strip() for c in re.split(r"(?<=[.!?。！？])\s+|\n{2,}", script.strip()) if c.strip()]
    if not chunks and script.strip(): chunks = [script.strip()]
    segments=[]; clips = clips or []
    for i, text in enumerate(chunks, 1):
        words = len(re.findall(r"\w+", text, flags=re.UNICODE))
        duration = max(2.0, words / 2.6)
        clip_id = clips[(i-1) % len(clips)].id if clips else None
        overlay = text[:80] + ("…" if len(text) > 80 else "")
        segments.append(ScriptSegment(id=f"seg_{i:03d}", text=text, estimated_duration=duration, matched_clip_id=clip_id, overlay_text=overlay))
    return segments
