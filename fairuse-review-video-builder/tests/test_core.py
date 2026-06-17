from pathlib import Path
from app.models import ProjectConfig, ClipTimecode
from app.utils import parse_timecode
from app.rights_checker import evaluate_project
from app.script_segmenter import split_script
from app.report_generator import build_report


def sample_project(**kwargs):
    data = dict(project_name="Demo", video_path="input.mp4", script="Đây là bình luận phân tích rất rõ ràng về cảnh phim. Tôi giải thích bối cảnh và quan điểm riêng.", clips=[ClipTimecode(id="c1", start="00:00:01", end="00:00:05", purpose="Bình luận cảnh mở đầu")], creator_name="Creator", source_url="https://example.com", rights_mode="fair_use_review")
    data.update(kwargs)
    return ProjectConfig(**data)

def test_parse_timecode():
    assert parse_timecode("01:02:03") == 3723
    assert parse_timecode("02:03") == 123
    assert parse_timecode("5.5") == 5.5

def test_risk_score():
    result = evaluate_project(sample_project())
    assert 0 <= result.risk_score <= 100
    assert result.total_clip_duration == 4

def test_split_script():
    segments = split_script("Câu một. Câu hai?", sample_project().clips)
    assert len(segments) == 2
    assert segments[0].matched_clip_id == "c1"

def test_generate_source_report():
    project = sample_project()
    report = build_report(project, evaluate_project(project))
    assert report["sources"][0]["creator"] == "Creator"
    assert report["transformations"][0] == "Muted original audio"
