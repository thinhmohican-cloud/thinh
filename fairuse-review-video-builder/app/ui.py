"""Streamlit UI with project, auto highlights, risk, preview, export, and settings tabs."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from .highlight_detector import detect_highlights
from .models import ProjectConfig, ClipTimecode, RightsMode, AspectRatio, RenderQuality
from .rights_checker import evaluate_project
from .renderer import render_project
from .config import settings


def _clips_to_rows(clips: list[ClipTimecode]) -> list[dict[str, object]]:
    return [{"start": c.start, "end": c.end, "score": "", "reason": "Manual", "purpose": c.purpose} for c in clips]


def _rows_to_clips(rows: list[dict[str, object]]) -> list[ClipTimecode]:
    clips: list[ClipTimecode] = []
    for i, row in enumerate(rows, 1):
        start = str(row.get("start", "")).strip(); end = str(row.get("end", "")).strip()
        if not start or not end:
            continue
        purpose = str(row.get("purpose", "")).strip()
        if not purpose:
            purpose = "Đoạn được chọn vì có chuyển động/cao trào, cần thêm bình luận phân tích."
        clips.append(ClipTimecode(id=f"clip_{i:03d}", start=start, end=end, purpose=purpose))
    return clips


def run_ui() -> None:
    """Run the Streamlit interface."""
    st.set_page_config(page_title="Fairuse Review Video Builder", layout="wide")
    st.title("fairuse-review-video-builder")
    tabs = st.tabs(["Project Input","Clips & Timecodes","Script & Voice","Risk Score","Preview","Export","API Keys / Settings"])
    ss = st.session_state
    with tabs[0]:
        ss.project_name = st.text_input("Tên project", ss.get("project_name","demo_review"))
        ss.video_path = st.text_input("File video local / đường dẫn có quyền", ss.get("video_path",""))
        ss.creator_name = st.text_input("Creator/source name", ss.get("creator_name",""))
        ss.source_url = st.text_input("Source URL", ss.get("source_url",""))
        ss.rights_mode = st.selectbox("Chế độ quyền", [m.value for m in RightsMode], index=3)
        ss.aspect_ratio = st.selectbox("Format", [a.value for a in AspectRatio])
    with tabs[1]:
        st.subheader("Auto Highlight Detector")
        col1, col2, col3 = st.columns(3)
        max_clips = col1.number_input("Số lượng highlight muốn lấy", min_value=1, max_value=20, value=int(ss.get("max_clips", 8)))
        clip_duration = col2.number_input("Độ dài mỗi clip (giây)", min_value=4.0, max_value=7.0, value=float(ss.get("clip_duration", 5.0)), step=0.5)
        scene_sensitivity = col3.selectbox("Scene sensitivity", ["low", "medium", "high"], index=1)
        if st.button("Auto Detect Highlights"):
            try:
                highlights = detect_highlights(ss.get("video_path", ""), int(max_clips), float(clip_duration), scene_sensitivity)
                ss.highlight_rows = [h.model_dump() for h in highlights]
                st.success(f"Đã phát hiện {len(highlights)} highlight đề xuất.")
            except Exception as exc:
                st.error(f"Không thể auto detect highlights: {exc}")
                st.info("Bạn vẫn có thể nhập/sửa timecode thủ công bên dưới.")
        rows = ss.get("highlight_rows") or []
        st.caption("Bạn có thể sửa trực tiếp start/end/purpose trước khi dùng để render.")
        edited = st.data_editor(pd.DataFrame(rows, columns=["start", "end", "score", "reason", "purpose"]), num_rows="dynamic", use_container_width=True, key="highlight_editor")
        if st.button("Use These Highlights"):
            ss.highlight_rows = edited.to_dict("records")
            ss.clips = _rows_to_clips(ss.highlight_rows)
            st.success("Đã lưu danh sách highlights vào project hiện tại.")
        with st.expander("Fallback nhập thủ công"):
            raw = st.text_area("Timecodes: start,end,purpose mỗi dòng", ss.get("raw_clips","00:00:01,00:00:05,Bình luận cảnh mở đầu")); ss.raw_clips=raw
            if st.button("Use Manual Timecodes"):
                manual_rows=[]
                for line in raw.splitlines():
                    if not line.strip(): continue
                    start,end,purpose=(line.split(",",2)+[""])[:3]
                    manual_rows.append({"start": start.strip(), "end": end.strip(), "score": "", "reason": "Manual", "purpose": purpose.strip()})
                ss.highlight_rows = manual_rows; ss.clips = _rows_to_clips(manual_rows)
                st.success("Đã lưu timecode thủ công.")
    with tabs[2]:
        ss.script = st.text_area("Script review tiếng Việt", ss.get("script","Đây là phần bình luận phân tích của tôi."), height=220)
    def build_config():
        clips = ss.get("clips")
        if not clips:
            rows = ss.get("highlight_rows") or []
            clips = _rows_to_clips(rows)
        if not clips:
            clips = _rows_to_clips(_clips_to_rows([]))
        return ProjectConfig(project_name=ss.project_name, video_path=ss.video_path, script=ss.script, clips=clips, creator_name=ss.creator_name, source_url=ss.source_url, rights_mode=ss.rights_mode, aspect_ratio=ss.aspect_ratio)
    with tabs[3]:
        if st.button("Tính risk score"):
            try:
                r=evaluate_project(build_config()); st.metric("Risk score", r.risk_score); st.warning("\n".join(r.warnings) or "Không có cảnh báo lớn.")
            except Exception as e: st.error(str(e))
    with tabs[4]: st.info("Dùng tab Export để render preview 720p rồi mở file trong thư mục exports.")
    with tabs[5]:
        col1,col2=st.columns(2)
        if col1.button("Render preview 720p"):
            try: st.json({k:str(v) for k,v in render_project(build_config(), RenderQuality.preview).items()})
            except Exception as e: st.error(str(e))
        if col2.button("Render final 1080p"):
            try: st.json({k:str(v) for k,v in render_project(build_config(), RenderQuality.final).items()})
            except Exception as e: st.error(str(e))
    with tabs[6]:
        st.code(f"TTS_PROVIDER={settings.tts_provider}\nOUTPUT_DIR={settings.output_dir}\nTEMP_DIR={settings.temp_dir}\nCACHE_DIR={settings.cache_dir}\nFFMPEG_PATH={settings.ffmpeg_path}")
        st.caption("API key được đọc từ .env, không lưu vào project output.")
