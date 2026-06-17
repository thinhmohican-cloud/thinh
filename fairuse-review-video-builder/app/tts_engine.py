"""TTS providers with cache and friendly API-key handling."""
from __future__ import annotations
import asyncio, math, wave, struct
from pathlib import Path
from .config import settings
from .utils import hash_text

class TTSError(RuntimeError): pass

def _mock_wav(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(22050)
        for i in range(int(seconds*22050)):
            val = int(9000*math.sin(2*math.pi*440*i/22050)); wav.writeframes(struct.pack('<h', val))

def synthesize_speech(text: str, output_dir: Path | None = None) -> Path:
    """Synthesize Vietnamese narration to cached audio. Demo mode creates a WAV tone."""
    cache = output_dir or settings.cache_dir; cache.mkdir(parents=True, exist_ok=True)
    provider = settings.tts_provider.lower(); ext = "mp3" if provider != "edge_local_demo" else "wav"
    out = cache / f"tts_{provider}_{hash_text(text)}.{ext}"
    if out.exists(): return out
    if provider == "edge_local_demo":
        try:
            import edge_tts
            async def run():
                await edge_tts.Communicate(text, "vi-VN-NamMinhNeural").save(str(out.with_suffix('.mp3')))
            asyncio.run(run()); return out.with_suffix('.mp3')
        except Exception:
            _mock_wav(out, max(3, len(text.split())/2.5)); return out
    if provider == "openai":
        if not settings.openai_api_key: raise TTSError("Thiếu OPENAI_API_KEY cho provider openai")
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        with client.audio.speech.with_streaming_response.create(model="gpt-4o-mini-tts", voice="alloy", input=text) as resp:
            resp.stream_to_file(out)
        return out
    if provider in {"azure","elevenlabs"}:
        key = settings.azure_speech_key if provider=="azure" else settings.elevenlabs_api_key
        if not key: raise TTSError(f"Thiếu API key cho provider {provider}")
        raise TTSError(f"Provider {provider} đã có cấu hình key nhưng adapter demo chưa gọi API; dùng edge_local_demo/openai hoặc mở rộng module.")
    raise TTSError(f"TTS_PROVIDER không hỗ trợ: {provider}")
