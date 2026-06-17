"""FFmpeg clip extraction, resizing, muting, and source overlays."""
from __future__ import annotations
from pathlib import Path
from .config import settings
from .models import AspectRatio, ClipTimecode
from .utils import parse_timecode, run_ffmpeg

SIZES = {AspectRatio.landscape:(1920,1080), AspectRatio.portrait:(1080,1920), AspectRatio.square:(1080,1080)}

def process_clip(video_path: str, clip: ClipTimecode, creator_name: str, aspect_ratio: AspectRatio, output_path: Path) -> Path:
    """Cut a clip, mute original audio, resize safely, and add source credit overlay."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w,h = SIZES[aspect_ratio]; start=parse_timecode(clip.start); dur=parse_timecode(clip.end)-start
    label = f"Nguồn: {creator_name}".replace("'", "\\'")
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease," 
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black," 
          f"drawtext=text='{label}':x=24:y=h-th-24:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.45")
    cmd=[settings.ffmpeg_path,"-y","-ss",str(start),"-i",video_path,"-t",str(dur),"-an","-vf",vf,"-r","30","-c:v","libx264","-preset","veryfast","-crf","23",str(output_path)]
    run_ffmpeg(cmd); return output_path
