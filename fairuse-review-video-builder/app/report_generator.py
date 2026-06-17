"""Source report JSON generation."""
from __future__ import annotations
from pathlib import Path
from .models import ProjectConfig, RiskResult
from .utils import write_json

def build_report(config: ProjectConfig, risk: RiskResult) -> dict:
    """Build the source and transformation report dictionary."""
    return {"project_name": config.project_name, "rights_mode": config.rights_mode.value,
        "sources": [{"creator": config.creator_name, "source_url": config.source_url,
            "clips_used": [{"start": c.start, "end": c.end, "purpose": c.purpose} for c in config.clips]}],
        "transformations": ["Muted original audio", "Added Vietnamese voice-over", "Added subtitles", "Added source credit overlay", "Added analytical commentary overlays"],
        "risk_score": risk.risk_score, "warnings": risk.warnings}

def write_report(config: ProjectConfig, risk: RiskResult, output_path: Path) -> Path:
    write_json(output_path, build_report(config, risk)); return output_path
