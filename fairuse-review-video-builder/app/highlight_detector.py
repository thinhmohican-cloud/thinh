"""Automatic highlight detection for review/reaction clip suggestions.

The detector ranks short segments using editorial signals only: scene changes,
motion, audio peaks, and an early-video hook bonus. It does not transform video
for copyright-detection evasion and never mirrors, speeds, pitches, or hides
source marks.
"""
from __future__ import annotations

import logging
import math
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from .config import settings
from .models import HighlightCandidate
from .utils import clamp_time_range, get_video_duration, seconds_to_timecode

logger = logging.getLogger(__name__)

SCENE_THRESHOLDS = {"low": 0.45, "medium": 0.35, "high": 0.25}

@dataclass(frozen=True)
class _SignalPoint:
    time: float
    score: float
    reason: str


def detect_highlights(
    video_path: str,
    max_clips: int = 8,
    clip_duration: float = 5.0,
    scene_sensitivity: str = "medium",
) -> list[HighlightCandidate]:
    """Detect highlight candidates from a local video path.

    Args:
        video_path: Local video file path.
        max_clips: Maximum number of clips to suggest.
        clip_duration: Desired clip length in seconds, clamped to 4-7 seconds.
        scene_sensitivity: One of ``low``, ``medium``, or ``high``.

    Returns:
        Ranked, non-overlapping highlight candidates with timecodes and reasons.

    Raises:
        FileNotFoundError: If ``video_path`` does not exist.
        RuntimeError: If FFmpeg/video probing fails.
    """
    path = Path(video_path).expanduser()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy video: {video_path}")
    if max_clips < 1:
        return []
    clip_duration = max(4.0, min(7.0, float(clip_duration)))
    duration = get_video_duration(str(path))
    if duration <= 0:
        raise RuntimeError("Không đọc được duration của video.")

    scene_points = _detect_scene_changes(path, scene_sensitivity)
    motion_points = _detect_motion(path, duration)
    audio_points = _detect_audio_peaks(path, duration)
    candidates = _build_candidates(scene_points, motion_points, audio_points, duration, clip_duration)
    selected = _select_diverse(candidates, max_clips=max_clips, min_gap=max(8.0, clip_duration * 1.8))
    logger.info("Detected %d highlight candidates for %s", len(selected), path)
    return selected


def _detect_scene_changes(path: Path, sensitivity: str) -> list[_SignalPoint]:
    threshold = SCENE_THRESHOLDS.get(sensitivity, SCENE_THRESHOLDS["medium"])
    cmd = [
        settings.ffmpeg_path, "-hide_banner", "-i", str(path), "-vf",
        f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg chưa được cài hoặc FFMPEG_PATH không đúng.") from exc
    if proc.returncode not in (0, 1):
        logger.warning("Scene detection returned %s: %s", proc.returncode, proc.stderr[-500:])
    points: list[_SignalPoint] = []
    for line in proc.stderr.splitlines():
        marker = "pts_time:"
        if marker in line:
            try:
                value = line.split(marker, 1)[1].split()[0]
                points.append(_SignalPoint(float(value), 35.0, "scene change"))
            except (ValueError, IndexError):
                continue
    return points


def _detect_motion(path: Path, duration: float, sample_every: float = 0.75) -> list[_SignalPoint]:
    try:
        import cv2  # type: ignore
    except Exception:
        logger.warning("OpenCV không khả dụng; bỏ qua motion detection.")
        return []
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        logger.warning("OpenCV không mở được video; bỏ qua motion detection.")
        return []
    points: list[tuple[float, float]] = []
    previous = None
    t = 0.0
    while t <= duration:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            t += sample_every; continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 90))
        if previous is not None:
            diff = cv2.absdiff(gray, previous).mean()
            points.append((t, float(diff)))
        previous = gray
        t += sample_every
    cap.release()
    if not points:
        return []
    values = [p[1] for p in points]
    mean = sum(values) / len(values)
    stdev = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)) or 1.0
    return [_SignalPoint(t, min(30.0, max(0.0, (v - mean) / stdev * 10 + 12)), "high motion") for t, v in points if v > mean + stdev * 0.6]


def _detect_audio_peaks(path: Path, duration: float, window: float = 0.75) -> list[_SignalPoint]:
    if not shutil.which(settings.ffmpeg_path) and Path(settings.ffmpeg_path).name == settings.ffmpeg_path:
        logger.warning("FFmpeg không khả dụng; bỏ qua audio peak detection.")
        return []
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "audio.wav"
        cmd = [settings.ffmpeg_path, "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(wav_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not wav_path.exists():
            logger.info("Video không có audio hoặc không trích xuất được audio; bỏ qua audio peaks.")
            return []
        with wave.open(str(wav_path), "rb") as wav_file:
            rate = wav_file.getframerate(); frames_per = max(1, int(rate * window)); idx = 0; rms_points=[]
            while True:
                frames = wav_file.readframes(frames_per)
                if not frames: break
                samples = [int.from_bytes(frames[i:i+2], "little", signed=True) for i in range(0, len(frames), 2)]
                if samples:
                    rms = math.sqrt(sum(s*s for s in samples) / len(samples))
                    rms_points.append((idx * window, rms))
                idx += 1
    if not rms_points:
        return []
    values = [p[1] for p in rms_points]
    mean = sum(values) / len(values); stdev = math.sqrt(sum((v-mean)**2 for v in values) / len(values)) or 1.0
    return [_SignalPoint(t, min(25.0, max(0.0, (v - mean) / stdev * 8 + 10)), "audio peak") for t, v in rms_points if v > mean + stdev * 0.8]


def _build_candidates(
    scene_points: list[_SignalPoint],
    motion_points: list[_SignalPoint],
    audio_points: list[_SignalPoint],
    duration: float,
    clip_duration: float,
) -> list[HighlightCandidate]:
    bucket: dict[int, dict[str, object]] = {}
    for point in [*scene_points, *motion_points, *audio_points]:
        start, end = clamp_time_range(point.time - clip_duration * 0.35, point.time + clip_duration * 0.65, duration)
        key = int(start // 2)
        current = bucket.setdefault(key, {"start": start, "end": end, "score": 0.0, "reasons": set()})
        current["score"] = float(current["score"]) + point.score
        current["reasons"].add(point.reason)  # type: ignore[union-attr]
    if not bucket:
        # Fallback: evenly spaced editorial suggestions rather than failing on low-motion videos.
        step = max(clip_duration + 8.0, duration / 6.0)
        t = 0.0
        while t < duration:
            start, end = clamp_time_range(t, t + clip_duration, duration)
            bucket[int(start // 2)] = {"start": start, "end": end, "score": 20.0, "reasons": {"evenly sampled fallback"}}
            t += step
    candidates: list[HighlightCandidate] = []
    for data in bucket.values():
        start = float(data["start"]); end = float(data["end"]); reasons = sorted(data["reasons"])  # type: ignore[arg-type]
        score = min(100.0, float(data["score"]) + (12.0 if start < 30 else 0.0))
        reason = " + ".join(r.replace("scene change", "Scene change").replace("high motion", "High motion").replace("audio peak", "Audio peak") for r in reasons)
        if start < 30 and "Hook zone" not in reason:
            reason = f"{reason} + Hook zone" if reason else "Hook zone"
        purpose = "Đoạn hook/cao trào phù hợp để bình luận" if score >= 45 else "Đoạn được chọn vì có chuyển động/cao trào, cần thêm bình luận phân tích."
        candidates.append(HighlightCandidate(start=seconds_to_timecode(start), end=seconds_to_timecode(end), score=round(score, 1), reason=reason, purpose=purpose))
    return sorted(candidates, key=lambda c: c.score, reverse=True)


def _select_diverse(candidates: list[HighlightCandidate], max_clips: int = 8, min_gap: float = 10.0) -> list[HighlightCandidate]:
    """Select non-overlapping highlights and keep the highest score in nearby regions."""
    from .utils import timecode_to_seconds
    selected: list[HighlightCandidate] = []
    for cand in sorted(candidates, key=lambda c: c.score, reverse=True):
        start = timecode_to_seconds(cand.start); end = timecode_to_seconds(cand.end)
        too_close = False
        for chosen in selected:
            cs = timecode_to_seconds(chosen.start); ce = timecode_to_seconds(chosen.end)
            overlaps = start < ce and end > cs
            near = abs(start - cs) < min_gap
            if overlaps or near:
                too_close = True; break
        if not too_close:
            selected.append(cand)
        if len(selected) >= max_clips:
            break
    return sorted(selected, key=lambda c: timecode_to_seconds(c.start))
