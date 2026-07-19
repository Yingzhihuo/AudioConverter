from dataclasses import dataclass
from pathlib import Path

from src.core.audio_codec import AudioCodec


@dataclass
class AudioTask:
    input_file: Path
    output_file: Path
    codec: AudioCodec

    bitrate: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    overwrite: bool = True