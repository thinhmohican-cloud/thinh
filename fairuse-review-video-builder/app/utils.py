"""Shared utility helpers."""
from __future__ import annotations
import hashlib, json, logging, subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

def parse_timecode(value: str) -> float:
    """Parse SS, MM:SS, or HH:MM:SS(.ms) into seconds."""
    value = str(value).strip()
    if not value: raise ValueError("Timecode is empty")
    if ":" not in value:
        sec = float(value)
    else:
        parts = value.split(":")
        if len(parts) > 3: raise ValueError(f"Invalid timecode: {value}")
        sec = 0.0
        for part in parts: sec = sec * 60 + float(part)
    if sec < 0: raise ValueError("Timecode must be non-negative")
    return sec

def seconds_to_srt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000)); total = int(seconds)
    h, rem = divmod(total, 3600); m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())[:80] or "project"

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def run_ffmpeg(cmd: list[str]) -> None:
    logging.getLogger(__name__).info("Running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"FFmpeg failed: {proc.stderr[-2000:]}")
