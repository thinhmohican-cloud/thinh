"""Shared utility helpers."""
from __future__ import annotations
import hashlib, json, logging, os, subprocess, shutil
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


def seconds_to_timecode(seconds: float) -> str:
    """Format seconds as HH:MM:SS, rounded to the nearest whole second."""
    seconds = max(0.0, float(seconds))
    total = int(round(seconds))
    h, rem = divmod(total, 3600); m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def timecode_to_seconds(timecode: str) -> float:
    """Alias for parse_timecode using the naming requested by the UI/detector."""
    return parse_timecode(timecode)

def clamp_time_range(start: float, end: float, duration: float) -> tuple[float, float]:
    """Clamp a start/end pair into a media duration while preserving length where possible."""
    duration = max(0.0, float(duration))
    start = max(0.0, float(start)); end = max(start, float(end))
    length = max(0.1, end - start)
    if length >= duration:
        return 0.0, duration
    if end > duration:
        end = duration; start = max(0.0, end - length)
    return start, min(duration, end)

def get_video_duration(video_path: str) -> float:
    """Return video duration in seconds using ffprobe/FFmpeg tooling."""
    path = Path(video_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy video: {video_path}")
    ffmpeg_name = os.environ.get('FFMPEG_PATH', 'ffmpeg')
    ffmpeg_candidate = shutil.which(ffmpeg_name) or ffmpeg_name
    ffprobe = str(Path(ffmpeg_candidate).with_name('ffprobe')) if Path(ffmpeg_candidate).parent != Path('.') else 'ffprobe'
    cmd = [ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError('FFprobe/FFmpeg chưa được cài hoặc chưa có trong PATH.') from exc
    if proc.returncode != 0:
        raise RuntimeError(f'Không đọc được duration video: {proc.stderr[-500:]}')
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise RuntimeError('Duration video không hợp lệ.') from exc
