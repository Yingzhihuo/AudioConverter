from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QTextEdit,
)

from src.core.audio_codec import AudioCodec
from src.models.audio_task import AudioTask


class MainWindow(QMainWindow):

    def __init__(self, converter):
        super().__init__()

        self.converter = converter

        self.setWindowTitle(
            "Audio Converter"
        )

        self.resize(
            600,
            400
        )

        self.init_ui()


    def init_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        layout = QVBoxLayout()

        central.setLayout(
            layout
        )


        # 输入文件

        input_layout = QHBoxLayout()

        self.input_edit = QLineEdit()

        input_btn = QPushButton(
            "浏览"
        )

        input_btn.clicked.connect(
            self.select_input
        )


        input_layout.addWidget(
            QLabel("输入文件:")
        )

        input_layout.addWidget(
            self.input_edit
        )

        input_layout.addWidget(
            input_btn
        )


        layout.addLayout(
            input_layout
        )


        # 输出目录

        output_layout = QHBoxLayout()

        self.output_edit = QLineEdit()

        output_btn = QPushButton(
            "浏览"
        )

        output_btn.clicked.connect(
            self.select_output
        )


        output_layout.addWidget(
            QLabel("输出目录:")
        )

        output_layout.addWidget(
            self.output_edit
        )

        output_layout.addWidget(
            output_btn
        )


        layout.addLayout(
            output_layout
        )


        # 编码选择

        self.codec_box = QComboBox()

        for codec in AudioCodec:
            self.codec_box.addItem(
                codec.display_name,
                codec
            )


        layout.addWidget(
            QLabel("输出编码:")
        )

        layout.addWidget(
            self.codec_box
        )


        # 转换按钮

        self.convert_btn = QPushButton(
            "开始转换"
        )

        self.convert_btn.clicked.connect(
            self.convert
        )

        layout.addWidget(
            self.convert_btn
        )


        # 日志

        self.log = QTextEdit()

        self.log.setReadOnly(
            True
        )

        layout.addWidget(
            self.log
        )


    def select_input(self):

        file, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.m4a)"
        )

        if file:
            self.input_edit.setText(
                file
            )


    def select_output(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录"
        )

        if folder:
            self.output_edit.setText(
                folder
            )

    def convert(self):

        try:

            input_file = self.input_edit.text()

            output_dir = self.output_edit.text()

            if not input_file:
                self.log.append(
                    "请选择输入文件"
                )
                return

            if not output_dir:
                self.log.append(
                    "请选择输出目录"
                )
                return

            codec = self.codec_box.currentData()

            input_path = Path(
                input_file
            )

            output_path = (
                    Path(output_dir)
                    /
                    f"{input_path.stem}{codec.extension}"
            )

            task = AudioTask(

                input_file=input_path,

                output_file=output_path,

                codec=codec
            )

            self.log.append(
                "开始转换..."
            )

            self.converter.convert(
                task
            )

            self.log.append(
                f"转换完成:\n{output_path}"
            )


        except Exception as e:

            self.log.append(
                f"转换失败:\n{e}"
            )