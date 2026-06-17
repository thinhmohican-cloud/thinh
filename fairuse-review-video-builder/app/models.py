"""Pydantic models for fair-use review video projects."""
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class RightsMode(str, Enum):
    own="own"; licensed="licensed"; creative_commons="creative_commons"; fair_use_review="fair_use_review"
class AspectRatio(str, Enum):
    landscape="16:9"; portrait="9:16"; square="1:1"
class RenderQuality(str, Enum):
    preview="preview"; final="final"; two_k="2k"

class ClipTimecode(BaseModel):
    id: str = Field(default="")
    start: str
    end: str
    purpose: str = ""
    @field_validator("start","end")
    @classmethod
    def valid_time(cls, v: str) -> str:
        from .utils import parse_timecode
        parse_timecode(v); return v
    @model_validator(mode="after")
    def end_after_start(self):
        from .utils import parse_timecode
        if parse_timecode(self.end) <= parse_timecode(self.start):
            raise ValueError("Clip end must be after start")
        if not self.id:
            self.id = f"clip_{abs(hash((self.start,self.end,self.purpose))) % 100000}"
        return self

class ProjectConfig(BaseModel):
    project_name: str
    video_path: str
    script: str
    clips: list[ClipTimecode]
    creator_name: str
    source_url: str
    rights_mode: RightsMode
    aspect_ratio: AspectRatio = AspectRatio.landscape
    use_original_audio: bool = False
    burn_subtitles: bool = True
    background_music_path: Optional[str] = None

class ScriptSegment(BaseModel):
    id: str
    text: str
    estimated_duration: float
    matched_clip_id: Optional[str] = None
    overlay_text: str = ""

class HighlightCandidate(BaseModel):
    start: str
    end: str
    score: float = Field(ge=0, le=100)
    reason: str
    purpose: str

    @field_validator("start", "end")
    @classmethod
    def valid_highlight_time(cls, v: str) -> str:
        from .utils import parse_timecode
        parse_timecode(v); return v

    @model_validator(mode="after")
    def valid_highlight_range(self):
        from .utils import parse_timecode
        if parse_timecode(self.end) <= parse_timecode(self.start):
            raise ValueError("Highlight end must be after start")
        return self

class RiskResult(BaseModel):
    risk_score: int
    warnings: list[str]
    total_clip_duration: float
