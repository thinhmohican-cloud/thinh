"""Local helper for creating commentary/review videos from short YouTube excerpts.

This tool is designed for legitimate commentary, criticism, education, and other
fair-use-style workflows. It intentionally does not include features whose main
purpose is to hide reuse from copyright-detection systems.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, scrolledtext
import tkinter as tk


DEFAULT_VOICE = "vi-VN-NamMinhNeural"
DEFAULT_OUTPUT = "Video_Review_Hoan_Chinh.mp4"
DEFAULT_CITATION = "Nguồn: video YouTube gốc — dùng trích đoạn ngắn để bình luận/đánh giá."


@dataclass(frozen=True)
class ClipRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def parse_time(value: str) -> float:
    """Parse seconds or HH:MM:SS/MM:SS strings into seconds."""
    value = value.strip()
    if not value:
        raise ValueError("Mốc thời gian không được để trống")
    if ":" not in value:
        seconds = float(value)
        if seconds < 0:
            raise ValueError("Mốc thời gian phải >= 0")
        return seconds

    parts = [float(part) for part in value.split(":")]
    if len(parts) > 3:
        raise ValueError(f"Mốc thời gian không hợp lệ: {value}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    if seconds < 0:
        raise ValueError("Mốc thời gian phải >= 0")
    return seconds


def parse_ranges(raw_ranges: str) -> list[ClipRange]:
    """Parse ranges like '60-65, 01:10-01:18'."""
    ranges: list[ClipRange] = []
    for raw_item in raw_ranges.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if "-" not in item:
            raise ValueError(f"Thiếu dấu '-' trong đoạn: {item}")
        start_raw, end_raw = item.split("-", 1)
        start = parse_time(start_raw)
        end = parse_time(end_raw)
        if end <= start:
            raise ValueError(f"Thời điểm kết thúc phải lớn hơn bắt đầu: {item}")
        if end - start > 15:
            raise ValueError(f"Mỗi trích đoạn nên ngắn gọn (tối đa 15 giây): {item}")
        ranges.append(ClipRange(start, end))

    if not ranges:
        raise ValueError("Vui lòng nhập ít nhất một trích đoạn, ví dụ: 60-65, 120-126")
    return ranges


def download_clips(url: str, ranges: list[ClipRange], temp_folder: Path) -> list[Path]:
    """Download only selected short excerpts instead of the entire source video."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import download_range_func

    downloaded: list[Path] = []
    for index, clip_range in enumerate(ranges, start=1):
        filename = temp_folder / f"clip_{index:02d}.mp4"
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(filename),
            "download_ranges": download_range_func(None, [(clip_range.start, clip_range.end)]),
            "force_keyframes_at_cuts": True,
            "quiet": True,
            "no_warnings": True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        downloaded.append(filename)
    return downloaded


async def generate_ai_voice(text: str, output_audio: Path, voice: str = DEFAULT_VOICE) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_audio))


def prepare_visual_clip(video_file: Path, target_height: int = 1080) -> VideoFileClip:
    """Create a muted, normalized clip for commentary.

    The source audio is removed so the final work is led by the creator's own
    narration. Visual transforms are limited to standard formatting; this avoids
    building an evasion-oriented copyright bypasser.
    """
    from moviepy.editor import VideoFileClip

    clip = VideoFileClip(str(video_file)).without_audio()
    if clip.h > target_height:
        clip = clip.resize(height=target_height)
    return clip


def add_citation_overlay(clip: VideoFileClip, citation: str) -> VideoFileClip:
    """Add a small source/context label for transparency."""
    try:
        from moviepy.editor import CompositeVideoClip, TextClip

        text = (
            TextClip(citation, fontsize=30, color="white", method="caption", size=(clip.w - 80, None))
            .on_color(color=(0, 0, 0), col_opacity=0.55)
            .set_position((40, "bottom"))
            .set_duration(clip.duration)
        )
        return CompositeVideoClip([clip, text], size=clip.size)
    except Exception:
        # TextClip depends on ImageMagick in some MoviePy installations. If the
        # local environment cannot render text, continue without failing export.
        return clip


def render_final_video(video_files: list[Path], audio_file: Path, output_file: Path) -> None:
    from moviepy.editor import AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx

    clips = [add_citation_overlay(prepare_visual_clip(path), DEFAULT_CITATION) for path in video_files]
    final_video = concatenate_videoclips(clips, method="compose")
    ai_audio = AudioFileClip(str(audio_file))

    if final_video.duration > ai_audio.duration:
        final_video = final_video.subclip(0, ai_audio.duration)
    else:
        final_video = final_video.fx(vfx.loop, duration=ai_audio.duration)

    final_video = final_video.set_audio(ai_audio)
    final_video.write_videofile(
        str(output_file),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=max(1, os.cpu_count() or 1),
    )
    final_video.close()
    ai_audio.close()
    for clip in clips:
        clip.close()


def create_review_video(url: str, script: str, ranges_text: str, output_file: Path, keep_temp: bool = False) -> Path:
    if not url.strip():
        raise ValueError("Vui lòng nhập link YouTube")
    if not script.strip():
        raise ValueError("Vui lòng nhập kịch bản bình luận/review")

    ranges = parse_ranges(ranges_text)
    temp_folder = Path(tempfile.mkdtemp(prefix="fair_use_review_"))
    try:
        audio_temp = temp_folder / "voiceover.mp3"
        videos = download_clips(url.strip(), ranges, temp_folder)
        asyncio.run(generate_ai_voice(script.strip(), audio_temp))
        render_final_video(videos, audio_temp, output_file)
        return output_file
    finally:
        if keep_temp:
            print(f"Giữ file tạm tại: {temp_folder}")
        else:
            shutil.rmtree(temp_folder, ignore_errors=True)


def run_gui() -> None:
    root = tk.Tk()
    root.title("Tool tạo video Review/Reaction có bình luận")
    root.geometry("700x650")

    def run_tool() -> None:
        url = url_entry.get()
        script = script_text.get("1.0", tk.END).strip()
        ranges_text = ranges_entry.get()
        output = Path(output_entry.get() or DEFAULT_OUTPUT)

        btn_start.config(state=tk.DISABLED, text="Đang xử lý... Vui lòng đợi!")

        def process() -> None:
            try:
                create_review_video(url, script, ranges_text, output)
                messagebox.showinfo("Thành công", f"Đã xuất video tại:\n{output}")
            except Exception as exc:
                messagebox.showerror("Lỗi", f"Có lỗi xảy ra:\n{exc}")
            finally:
                btn_start.config(state=tk.NORMAL, text="TẠO VIDEO REVIEW")

        threading.Thread(target=process, daemon=True).start()

    btn_start = tk.Button(root, text="TẠO VIDEO REVIEW", font=("Arial", 14, "bold"), bg="green", fg="white", command=run_tool)
    btn_start.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)

    tk.Label(root, text="LINK VIDEO YOUTUBE GỐC:", font=("Arial", 10, "bold")).pack(pady=(20, 5))
    url_entry = tk.Entry(root, width=80, font=("Arial", 10))
    url_entry.pack(pady=5)

    tk.Label(root, text="TRÍCH ĐOẠN NGẮN (ví dụ: 60-65, 02:00-02:08):", font=("Arial", 10, "bold")).pack(pady=5)
    ranges_entry = tk.Entry(root, width=80, font=("Arial", 10))
    ranges_entry.pack(pady=5)
    ranges_entry.insert(0, "60-65, 120-126")

    tk.Label(root, text="FILE XUẤT:", font=("Arial", 10, "bold")).pack(pady=5)
    output_entry = tk.Entry(root, width=80, font=("Arial", 10))
    output_entry.pack(pady=5)
    output_entry.insert(0, DEFAULT_OUTPUT)

    tk.Label(root, text="KỊCH BẢN BÌNH LUẬN/REVIEW CỦA BẠN:", font=("Arial", 10, "bold")).pack(pady=5)
    frame_text = tk.Frame(root)
    frame_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
    script_text = scrolledtext.ScrolledText(frame_text, font=("Arial", 10))
    script_text.pack(fill=tk.BOTH, expand=True)
    script_text.insert(tk.END, "Chào các bạn, đây là phần bình luận và đánh giá của tôi về trích đoạn này...")

    tk.Label(
        root,
        text="Lưu ý: hãy chỉ dùng đoạn cần thiết, thêm bình luận thật sự, và kiểm tra quyền sử dụng trước khi đăng.",
        fg="gray",
        wraplength=640,
    ).pack(pady=5)

    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tạo video review/reaction từ các trích đoạn ngắn và phần đọc kịch bản tiếng Việt.")
    parser.add_argument("--url", help="Link YouTube nguồn")
    parser.add_argument("--script", help="Kịch bản bình luận/review")
    parser.add_argument("--ranges", help="Các trích đoạn, ví dụ: '60-65, 02:00-02:08'")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="File MP4 đầu ra")
    parser.add_argument("--keep-temp", action="store_true", help="Giữ lại file tạm để debug")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.url or args.script or args.ranges:
        if not (args.url and args.script and args.ranges):
            parser.error("CLI cần đủ --url, --script và --ranges")
        create_review_video(args.url, args.script, args.ranges, Path(args.output), args.keep_temp)
    else:
        run_gui()


if __name__ == "__main__":
    main()
