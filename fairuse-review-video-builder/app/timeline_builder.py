"""Timeline assembly around narration audio."""
from __future__ import annotations
from pathlib import Path
from .config import settings
from .utils import run_ffmpeg

def concat_clips(processed_clips: list[Path], output_path: Path) -> Path:
    """Concatenate processed clips in order using FFmpeg concat demuxer."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = output_path.with_suffix('.txt')
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in processed_clips), encoding="utf-8")
    run_ffmpeg([settings.ffmpeg_path,"-y","-f","concat","-safe","0","-i",str(list_file),"-c","copy",str(output_path)])
    return output_path

def mux_with_audio(video_path: Path, audio_path: Path, output_path: Path, background_music: Path | None = None) -> Path:
    """Use narration as the main timeline and trim/extend video to match audio."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if background_music:
        cmd=[settings.ffmpeg_path,"-y","-stream_loop","-1","-i",str(video_path),"-i",str(audio_path),"-i",str(background_music),"-filter_complex","[2:a]volume=0.12[a2];[1:a][a2]amix=inputs=2:duration=first, loudnorm[a]","-map","0:v","-map","[a]","-shortest","-c:v","libx264","-c:a","aac","-r","30",str(output_path)]
    else:
        cmd=[settings.ffmpeg_path,"-y","-stream_loop","-1","-i",str(video_path),"-i",str(audio_path),"-map","0:v","-map","1:a","-shortest","-c:v","libx264","-c:a","aac","-af","loudnorm","-r","30",str(output_path)]
    run_ffmpeg(cmd); return output_path
