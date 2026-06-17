"""Application settings loaded from environment."""
from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings
load_dotenv()
class Settings(BaseSettings):
    tts_provider: str = Field("edge_local_demo", alias="TTS_PROVIDER")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    azure_speech_key: str = Field("", alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field("", alias="AZURE_SPEECH_REGION")
    elevenlabs_api_key: str = Field("", alias="ELEVENLABS_API_KEY")
    output_dir: Path = Field(Path("./exports"), alias="OUTPUT_DIR")
    temp_dir: Path = Field(Path("./temp"), alias="TEMP_DIR")
    cache_dir: Path = Field(Path("./cache"), alias="CACHE_DIR")
    ffmpeg_path: str = Field("ffmpeg", alias="FFMPEG_PATH")
    class Config: extra="ignore"
settings = Settings()
