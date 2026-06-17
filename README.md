# Fair-use Review Video Tool

Local Python tool for making Vietnamese review/reaction videos from short YouTube excerpts plus your own commentary narration.

## What it does

- Accepts a YouTube URL, a Vietnamese review script, and explicit short clip ranges.
- Downloads only the requested excerpts instead of the full source video.
- Generates Vietnamese text-to-speech narration with Microsoft Edge TTS.
- Removes source audio so the final video is driven by your own commentary.
- Loops or trims visuals to match the narration length.
- Adds a small source/context label when the local MoviePy text backend supports it.

## Important usage note

This project is for commentary, criticism, review, education, and similar legitimate uses. It does not implement copyright-detection evasion features. You are responsible for checking licenses, platform rules, and whether your final edit is sufficiently transformative before publishing.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You also need `ffmpeg` available on your PATH.

## GUI usage

```bash
python fair_use_review_tool.py
```

Fill in:

1. YouTube URL.
2. Clip ranges, for example `60-65, 02:00-02:08`.
3. Output file name.
4. Your commentary/review script.

## CLI usage

```bash
python fair_use_review_tool.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --ranges "60-65, 02:00-02:08" \
  --script "Đây là phần bình luận của tôi..." \
  --output review.mp4
```

Each selected excerpt is limited to 15 seconds to encourage concise quotation instead of wholesale reuse.
