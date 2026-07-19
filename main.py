import sys

from PySide6.QtWidgets import QApplication

from src.config.config_manager import ConfigManager
from src.core.ffmpeg_service import FFmpegService
from src.core.converter import AudioConverter

from ui.main_window import MainWindow



def main():

    config = ConfigManager()


    ffmpeg = FFmpegService(
        config.get("ffmpeg_path")
    )


    converter = AudioConverter(
        ffmpeg
    )


    app = QApplication(sys.argv)


    window = MainWindow(
        converter
    )

    window.show()


    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()