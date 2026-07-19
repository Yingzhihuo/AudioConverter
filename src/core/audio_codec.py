from enum import Enum


class AudioCodec(Enum):
    MP3 = ("MP3", "libmp3lame", ".mp3")
    AAC = ("AAC", "aac", ".m4a")
    FLAC = ("FLAC", "flac", ".flac")
    WAV = ("WAV", "pcm_s16le", ".wav")
    OPUS = ("Opus", "libopus", ".opus")
    OGG = ("OGG Vorbis", "libvorbis", ".ogg")

    def __init__(self, display_name, ffmpeg_codec, extension):
        self.display_name = display_name
        self.ffmpeg_codec = ffmpeg_codec
        self.extension = extension