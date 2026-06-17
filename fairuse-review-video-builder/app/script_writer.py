"""Generate Vietnamese review/reaction scripts from selected highlights.

The writer produces original commentary for voice-over. It must not copy source
transcripts, claim facts not visible in the clips, or create copyright-evasion
content.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from .config import settings

logger = logging.getLogger(__name__)

STYLE_GUIDES = {
    "review": "review phân tích, rõ ý, tập trung vào cách cảnh quay tạo cảm xúc",
    "Review phân tích": "review phân tích, rõ ý, tập trung vào cách cảnh quay tạo cảm xúc",
    "Reaction hài hước": "reaction hài hước nhẹ nhàng, duyên dáng, không xúc phạm cá nhân",
    "Tóm tắt nhanh": "tóm tắt nhanh, câu ngắn, dễ đọc cho voice-over",
    "Bình luận chuyên sâu": "bình luận chuyên sâu về nhịp dựng, chuyển cảnh, cảm xúc và ngữ cảnh có thể quan sát",
    "Giọng kể YouTube Shorts": "nhịp nhanh, hook mạnh, câu gọn phù hợp video ngắn",
}

LENGTH_GUIDES = {
    "Ngắn": "Mỗi clip 1 câu bình luận ngắn.",
    "Vừa": "Mỗi clip 2 câu bình luận vừa đủ.",
    "Dài": "Mỗi clip 2-3 câu bình luận chi tiết nhưng không lan man.",
}

@dataclass(frozen=True)
class ScriptClip:
    start: str
    end: str
    reason: str = ""
    purpose: str = ""
    score: float | None = None


def generate_script_from_highlights(
    project_config: Any,
    clips: Iterable[Any],
    style: str = "review",
    tone: str = "natural",
    language: str = "vi",
    length: str = "Vừa",
    provider: str | None = None,
) -> str:
    """Generate a complete Vietnamese commentary script from selected clips.

    Template mode always works without API keys. AI mode is used only when a
    supported provider and API key are configured; otherwise the function falls
    back to template mode to keep the app usable offline.
    """
    normalized = _normalize_clips(clips)
    if not normalized:
        raise ValueError("Bạn cần nhập timecode hoặc chạy Auto Detect Highlights trước.")
    provider_name = (provider or os.environ.get("SCRIPT_PROVIDER") or getattr(settings, "script_provider", "template")).lower()
    if provider_name == "openai" and getattr(settings, "openai_api_key", ""):
        try:
            return _generate_with_openai(project_config, normalized, style, tone, language, length)
        except Exception as exc:
            logger.warning("OpenAI script generation failed; falling back to template: %s", exc)
    if provider_name == "gemini" and getattr(settings, "gemini_api_key", ""):
        try:
            return _generate_with_gemini(project_config, normalized, style, tone, language, length)
        except Exception as exc:
            logger.warning("Gemini script generation failed; falling back to template: %s", exc)
    return _generate_template(project_config, normalized, style, tone, language, length)


def improve_script(script: str, style: str = "review", tone: str = "natural", provider: str | None = None) -> str:
    """Improve wording while preserving the original ideas and approximate length."""
    if not script.strip():
        raise ValueError("Chưa có script để cải thiện.")
    provider_name = (provider or os.environ.get("SCRIPT_PROVIDER") or getattr(settings, "script_provider", "template")).lower()
    if provider_name == "openai" and getattr(settings, "openai_api_key", ""):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": _safety_prompt()}, {"role": "user", "content": f"Hãy làm mượt script sau, giữ nguyên ý chính và không kéo dài quá 15%. Phong cách: {style}, tone: {tone}.\n\n{script}"}],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("OpenAI improve failed; using template improvement: %s", exc)
    return _improve_template(script, style)


def _normalize_clips(clips: Iterable[Any]) -> list[ScriptClip]:
    normalized: list[ScriptClip] = []
    for item in clips:
        if item is None:
            continue
        if isinstance(item, dict):
            getter = item.get
        else:
            getter = lambda key, default=None: getattr(item, key, default)
        start = str(getter("start", "")).strip(); end = str(getter("end", "")).strip()
        if not start or not end:
            continue
        score_raw = getter("score", None)
        try:
            score = float(score_raw) if score_raw not in (None, "") else None
        except (TypeError, ValueError):
            score = None
        normalized.append(ScriptClip(start=start, end=end, reason=str(getter("reason", "")).strip(), purpose=str(getter("purpose", "")).strip(), score=score))
    return normalized


def _generate_template(project_config: Any, clips: list[ScriptClip], style: str, tone: str, language: str, length: str) -> str:
    project_name = getattr(project_config, "project_name", None) or _dict_get(project_config, "project_name", "video này")
    creator = getattr(project_config, "creator_name", None) or _dict_get(project_config, "creator_name", "nguồn gốc")
    style_text = STYLE_GUIDES.get(style, STYLE_GUIDES["review"])
    length_text = LENGTH_GUIDES.get(length, LENGTH_GUIDES["Vừa"])
    paragraphs = [
        f"Mở đầu, mình sẽ nhìn vào các khoảnh khắc nổi bật trong {project_name} từ {creator}. Thay vì phát lại nguyên vẹn, phần này tập trung vào cảm giác, nhịp dựng và lý do vì sao từng đoạn đáng để bình luận.",
    ]
    starters = [
        "Ở đoạn này",
        "Điểm đáng chú ý là",
        "Khoảnh khắc này cho thấy",
        "Đây là phần có thể giữ chân người xem vì",
        "Sang đoạn tiếp theo",
    ]
    for index, clip in enumerate(clips, 1):
        starter = starters[(index - 1) % len(starters)]
        reason = clip.reason or "nhịp hình và chuyển động có điểm nhấn"
        purpose = clip.purpose or "cần thêm bình luận phân tích"
        score_text = f" Điểm gợi ý của đoạn này là {clip.score:.1f}/100," if clip.score is not None else ""
        if length == "Ngắn":
            body = f"{starter}, từ {clip.start} đến {clip.end}, {reason.lower()} nên phù hợp để nêu nhận xét nhanh về {purpose.lower()}."
        elif length == "Dài":
            body = (f"{starter}, từ {clip.start} đến {clip.end}, {reason.lower()} tạo ra một nhịp xem rõ rệt.{score_text} nhưng điều quan trọng hơn là cách đoạn này phục vụ cho phần bình luận: {purpose.lower()}. "
                    f"Với phong cách {style_text}, mình có thể phản ứng vào cảm giác mà cảnh tạo ra, đồng thời chỉ nói những gì quan sát được trong clip.")
        else:
            body = (f"{starter}, từ {clip.start} đến {clip.end}, {reason.lower()} khiến đoạn này trở thành một điểm nhấn đáng xem.{score_text} "
                    f"Mình sẽ dùng nó để {purpose.lower()}, theo hướng {style_text}.")
        paragraphs.append(body)
    paragraphs.append("Kết lại, những đoạn highlight này chỉ là phần trích ngắn để phục vụ nhận xét và phân tích. Phần quan trọng nhất vẫn là góc nhìn bình luận mới, nguồn được ghi rõ và nội dung được biên tập có trách nhiệm.")
    return "\n\n".join(paragraphs)


def _generate_with_openai(project_config: Any, clips: list[ScriptClip], style: str, tone: str, language: str, length: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": _safety_prompt()}, {"role": "user", "content": _prompt(project_config, clips, style, tone, language, length)}],
        temperature=0.75,
    )
    return response.choices[0].message.content.strip()


def _generate_with_gemini(project_config: Any, clips: list[ScriptClip], style: str, tone: str, language: str, length: str) -> str:
    api_key = settings.gemini_api_key
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": _safety_prompt() + "\n\n" + _prompt(project_config, clips, style, tone, language, length)}]}], "generationConfig": {"temperature": 0.75}}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini request failed: {exc}") from exc
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _prompt(project_config: Any, clips: list[ScriptClip], style: str, tone: str, language: str, length: str) -> str:
    source_url = getattr(project_config, "source_url", None) or _dict_get(project_config, "source_url", "")
    creator = getattr(project_config, "creator_name", None) or _dict_get(project_config, "creator_name", "")
    rights = getattr(project_config, "rights_mode", None) or _dict_get(project_config, "rights_mode", "")
    clip_lines = "\n".join(f"- {c.start}–{c.end}: reason={c.reason or 'n/a'}; purpose={c.purpose or 'n/a'}; score={c.score if c.score is not None else 'n/a'}" for c in clips)
    return f"""Viết script voice-over bằng tiếng Việt ({language}) cho video review/reaction.
Phong cách: {style}. Tone: {tone}. Độ dài: {length}.
Creator/source: {creator}. Source URL: {source_url}. Rights mode: {rights}.
Danh sách clip/highlight:
{clip_lines}

Yêu cầu cấu trúc: có mở đầu hook, mỗi clip có một đoạn bình luận tương ứng, và có câu kết. Không copy transcript gốc."""


def _safety_prompt() -> str:
    return (
        "Bạn viết lời bình luận/review tiếng Việt tự nhiên cho voice-over. Không nhận mình là AI. "
        "Không copy lời thoại/transcript gốc nếu không cần. Không khẳng định thông tin không có trong clip. "
        "Tập trung vào bình luận, phân tích, reaction và cảm nhận có căn cứ. "
        "Không tạo nội dung lách bản quyền, né Content ID, hoặc hướng dẫn xóa watermark/che logo. "
        "Không dùng ngôn từ xúc phạm cá nhân."
    )


def _improve_template(script: str, style: str) -> str:
    replacements = {
        "Mình sẽ": "Mình có thể",
        "đáng xem": "đáng chú ý",
        "phù hợp để": "rất hợp để",
    }
    improved = script.strip()
    for src, dst in replacements.items():
        improved = improved.replace(src, dst)
    prefix = "Bản chỉnh mượt:\n\n" if not improved.lower().startswith("bản chỉnh") else ""
    return prefix + improved


def _dict_get(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, dict) else default
