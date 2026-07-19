from src.config.config_manager import ConfigManager


def main():
    config = ConfigManager()

    print("FFmpeg:")
    print(config.get("ffmpeg_path"))

    print("FFprobe:")
    print(config.get("ffprobe_path"))


if __name__ == "__main__":
    main()