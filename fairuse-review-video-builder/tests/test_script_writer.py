import os

import pytest

from app.script_writer import generate_script_from_highlights, improve_script


def sample_project():
    return {
        "project_name": "Demo Review",
        "creator_name": "Creator A",
        "source_url": "https://example.com/video",
        "rights_mode": "fair_use_review",
    }


def sample_clips():
    return [
        {"start": "00:00:05", "end": "00:00:10", "score": 87.5, "reason": "High motion + Hook zone", "purpose": "Bình luận đoạn mở đầu"},
        {"start": "00:00:20", "end": "00:00:25", "score": 75.0, "reason": "Scene change", "purpose": "Phân tích nhịp dựng"},
    ]


def test_generate_script_template_not_empty_with_clips(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SCRIPT_PROVIDER", "template")
    script = generate_script_from_highlights(sample_project(), sample_clips(), style="Review phân tích", provider="template")
    assert script.strip()
    assert "00:00:05" in script
    assert "00:00:20" in script


def test_generate_script_warns_when_no_clips():
    with pytest.raises(ValueError, match="Bạn cần nhập timecode"):
        generate_script_from_highlights(sample_project(), [], provider="template")


def test_style_and_tone_affect_template_output():
    script = generate_script_from_highlights(sample_project(), sample_clips(), style="Reaction hài hước", tone="natural", length="Dài", provider="template")
    assert "reaction hài hước" in script.lower()
    assert "không xúc phạm" in script.lower()


def test_no_api_required_for_template(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    script = generate_script_from_highlights(sample_project(), sample_clips(), provider="template")
    assert "Mở đầu" in script


def test_improve_script_template_no_api():
    improved = improve_script("Mình sẽ nói về đoạn này vì nó đáng xem.", provider="template")
    assert improved.startswith("Bản chỉnh mượt")
    assert "Mình có thể" in improved
