# fairuse-review-video-builder

Ứng dụng Python 3.11+ hỗ trợ dựng video review/reaction tiếng Việt từ các đoạn video ngắn mà người dùng có quyền sử dụng hợp pháp. Tool tự động mute audio gốc, thêm giọng AI, subtitle, overlay nguồn, báo cáo nguồn và risk score bản quyền.

> Lưu ý: đây là tool hỗ trợ dựng video review/reaction có kiểm soát quyền, **không phải tool lách bản quyền**. Ứng dụng không mirror/speed/pitch để né Content ID, không xóa watermark và không che logo nguồn.

## Cài Python

1. Cài Python 3.11+ từ <https://www.python.org/downloads/>.
2. Kiểm tra:

```bash
python --version
```

## Cài FFmpeg

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: tải từ <https://ffmpeg.org/download.html>, thêm `ffmpeg` vào PATH.

Kiểm tra:

```bash
ffmpeg -version
```

## Cài dependencies

```bash
cd fairuse-review-video-builder
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Cấu hình API key

Sao chép file mẫu:

```bash
cp .env.example .env
```

Điền provider cần dùng:

```env
TTS_PROVIDER=openai
OPENAI_API_KEY=...
```

Nếu chưa có API key, dùng:

```env
TTS_PROVIDER=edge_local_demo
```

Không commit `.env` thật. API key chỉ đọc qua biến môi trường và không được lưu vào output project.

## Chạy app

```bash
python run.py
```

Backend FastAPI có thể chạy riêng:

```bash
uvicorn app.main:app --reload
```

## Tạo project

Trong UI:

1. Tab **Project Input**: nhập tên project, video local/đường dẫn có quyền, creator/source URL, rights mode.
2. Tab **Clips & Timecodes**: nhập mỗi dòng theo định dạng:

```text
00:01:05,00:01:10,Bình luận cảnh mở đầu
00:02:00,00:02:08,Phân tích cách dựng cảnh
```

3. Trong tab **Clips & Timecodes**, có thể bấm **Auto Detect Highlights** để tool tự đề xuất các đoạn hook/highlight từ video local.
4. Kiểm tra bảng kết quả gồm `start`, `end`, `score`, `reason`, `purpose`; sửa trực tiếp trong bảng nếu cần.
5. Bấm **Use These Highlights** để lưu danh sách timecode vào project.
6. Tab **Script & Voice**: nhập script review tiếng Việt.
7. Tab **Risk Score**: xem điểm rủi ro và cảnh báo.

## Auto Detect Highlights

Tính năng này phân tích video bằng các tín hiệu biên tập:

- Scene change: điểm chuyển cảnh mạnh.
- Motion: frame difference bằng OpenCV.
- Audio peak: RMS/loudness theo từng window nếu video có audio.
- Hook zone: cộng điểm nhẹ cho đoạn trong 0–30 giây đầu.
- Diversity: tránh chọn các đoạn quá gần hoặc chồng lấn nhau.

Cách dùng:

1. Nhập video path hợp lệ trong tab **Project Input**.
2. Mở tab **Clips & Timecodes**.
3. Chọn số lượng highlight, độ dài clip, scene sensitivity.
4. Bấm **Auto Detect Highlights**.
5. Sửa `purpose` thành lý do bình luận/phân tích cụ thể hơn nếu cần.
6. Bấm **Use These Highlights** trước khi tính risk score hoặc render.

Auto highlight chỉ là gợi ý kỹ thuật. Người dùng vẫn cần đảm bảo quyền sử dụng video, ghi nguồn, mute audio gốc theo mặc định và thêm bình luận/phân tích đủ rõ ràng.

## Render preview/final

- **Render preview 720p**: xuất nhanh `preview_720p.mp4`.
- **Render final 1080p**: xuất `final_video.mp4`.

Output nằm trong `exports/<ten_project>/`:

- `final_video.mp4` hoặc `preview_720p.mp4`
- `subtitles.srt`
- `source_report.json`
- `project_config.json`

## Thiết kế an toàn bản quyền

- Mute 100% audio gốc.
- Thêm voice-over tiếng Việt.
- Thêm subtitle và overlay nguồn.
- Tạo `source_report.json` ghi creator, URL, clip đã dùng, transformation, warnings.
- Risk score chỉ cảnh báo, không thay thế tư vấn pháp lý.
- Không có tính năng lách Content ID, không mirror/speed/pitch để né bản quyền, không xóa watermark/che logo.
