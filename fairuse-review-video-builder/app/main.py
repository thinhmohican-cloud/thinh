"""FastAPI backend for the fair-use review video builder."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException
from .models import ProjectConfig, RenderQuality
from .rights_checker import evaluate_project
from .renderer import render_project
from .utils import write_json

app = FastAPI(title="fairuse-review-video-builder")
DB = Path("projects.sqlite3")

def init_db() -> None:
    """Create the project metadata table if needed."""
    with sqlite3.connect(DB) as con:
        con.execute("CREATE TABLE IF NOT EXISTS projects (name TEXT PRIMARY KEY, config_json TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
init_db()

@app.get("/health")
def health() -> dict[str, str]: return {"status":"ok"}

@app.post("/projects")
def create_project(config: ProjectConfig) -> dict[str, object]:
    """Validate and store a project metadata record."""
    with sqlite3.connect(DB) as con:
        con.execute("INSERT OR REPLACE INTO projects(name, config_json) VALUES (?, ?)", (config.project_name, config.model_dump_json()))
    return {"project_name": config.project_name, "risk": evaluate_project(config).model_dump()}

@app.post("/risk")
def risk(config: ProjectConfig) -> dict: return evaluate_project(config).model_dump()

@app.post("/render/{quality}")
def render(quality: RenderQuality, config: ProjectConfig) -> dict[str, str]:
    """Render preview/final outputs."""
    try: return {k: str(v) for k,v in render_project(config, quality).items()}
    except Exception as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
