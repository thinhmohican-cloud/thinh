"""Streamlit UI with project, risk, preview, export, and settings tabs."""
from __future__ import annotations
import streamlit as st
from .models import ProjectConfig, ClipTimecode, RightsMode, AspectRatio, RenderQuality
from .rights_checker import evaluate_project
from .renderer import render_project
from .config import settings

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
        raw = st.text_area("Timecodes: start,end,purpose mỗi dòng", ss.get("raw_clips","00:00:01,00:00:05,Bình luận cảnh mở đầu")); ss.raw_clips=raw
    with tabs[2]:
        ss.script = st.text_area("Script review tiếng Việt", ss.get("script","Đây là phần bình luận phân tích của tôi."), height=220)
    def build_config():
        clips=[]
        for i,line in enumerate(ss.get("raw_clips","").splitlines(),1):
            if not line.strip(): continue
            start,end,purpose=(line.split(",",2)+[""])[:3]
            clips.append(ClipTimecode(id=f"clip_{i:03d}", start=start.strip(), end=end.strip(), purpose=purpose.strip()))
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
