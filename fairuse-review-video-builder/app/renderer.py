"""High-level render pipeline."""
from __future__ import annotations
from pathlib import Path
from .models import ProjectConfig, RenderQuality
from .clip_processor import process_clip
from .rights_checker import evaluate_project
from .script_segmenter import split_script
from .subtitle_generator import generate_srt, subtitle_filter
from .tts_engine import synthesize_speech
from .timeline_builder import concat_clips, mux_with_audio
from .report_generator import write_report
from .utils import safe_name, write_json, run_ffmpeg
from .config import settings

def render_project(config: ProjectConfig, quality: RenderQuality = RenderQuality.preview) -> dict[str, Path]:
    """Render project outputs: MP4, SRT, source report, and sanitized config."""
    base = settings.output_dir / safe_name(config.project_name); temp = settings.temp_dir / safe_name(config.project_name)
    base.mkdir(parents=True, exist_ok=True); temp.mkdir(parents=True, exist_ok=True)
    risk=evaluate_project(config); segments=split_script(config.script, config.clips)
    srt=generate_srt(segments, base/"subtitles.srt"); audio=synthesize_speech(config.script)
    clips=[process_clip(config.video_path,c,config.creator_name,config.aspect_ratio,temp/f"{i:03d}_{c.id}.mp4") for i,c in enumerate(config.clips,1)]
    concat=concat_clips(clips, temp/"visuals.mp4")
    muxed=mux_with_audio(concat,audio,temp/"muxed.mp4", Path(config.background_music_path) if config.background_music_path else None)
    final=base/("preview_720p.mp4" if quality==RenderQuality.preview else "final_video.mp4")
    vf=[]
    if quality==RenderQuality.preview: vf.append("scale=-2:720")
    if config.burn_subtitles: vf.append(subtitle_filter(srt))
    cmd=[settings.ffmpeg_path,"-y","-i",str(muxed)]
    if vf: cmd += ["-vf", ",".join(vf)]
    cmd += ["-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-r","30",str(final)]
    run_ffmpeg(cmd)
    report=write_report(config,risk,base/"source_report.json")
    safe_config=config.model_dump(); safe_config.pop("background_music_path", None)
    write_json(base/"project_config.json", safe_config)
    return {"video":final,"subtitles":srt,"source_report":report,"project_config":base/"project_config.json"}
