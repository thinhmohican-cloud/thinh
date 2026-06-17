"""Rights and fair-use-style risk scoring helpers."""
from __future__ import annotations
from .models import ProjectConfig, RiskResult
from .utils import parse_timecode

AUTO_PURPOSE = "Đoạn được chọn vì có chuyển động/cao trào, cần thêm bình luận phân tích."

def evaluate_project(config: ProjectConfig) -> RiskResult:
    """Return a non-blocking 0-100 copyright risk score with warnings."""
    warnings: list[str] = []; score = 0
    durations = [parse_timecode(c.end)-parse_timecode(c.start) for c in config.clips]
    total = sum(durations)
    if len(config.clips) > 8:
        score += 8; warnings.append("Có nhiều highlight từ cùng một video; hãy chọn lọc đoạn thật sự cần bình luận.")
    if total > 120: score += 25; warnings.append("Tổng thời lượng trích đoạn vượt 120 giây từ cùng nguồn.")
    elif total > 60: score += 15; warnings.append("Tổng thời lượng trích đoạn khá dài; cân nhắc rút ngắn.")
    for clip, dur in zip(config.clips, durations):
        if not clip.purpose.strip():
            clip.purpose = AUTO_PURPOSE
        if dur > 30: score += 10; warnings.append(f"Clip {clip.id} dài hơn 30 giây.")
        if clip.purpose.strip() == AUTO_PURPOSE:
            score += 5; warnings.append(f"Clip {clip.id} là gợi ý auto; nên bổ sung purpose/bình luận phân tích cụ thể hơn.")
        elif len(clip.purpose.strip()) < 8:
            score += 12; warnings.append(f"Clip {clip.id} thiếu lý do bình luận rõ ràng.")
    if not config.creator_name.strip() or not config.source_url.strip():
        score += 20; warnings.append("Thiếu source credit (creator/source URL).")
    if len(config.script.strip()) < 80:
        score += 18; warnings.append("Script/voice-over quá ngắn; nên thêm bình luận/phân tích rõ hơn.")
    if config.use_original_audio:
        score += 25; warnings.append("Cố dùng audio gốc làm tăng rủi ro; tool mặc định mute audio gốc.")
    if config.rights_mode == "fair_use_review": score += 5
    elif config.rights_mode in {"own", "licensed"}: score = max(0, score-15)
    return RiskResult(risk_score=min(100, score), warnings=warnings, total_clip_duration=total)
