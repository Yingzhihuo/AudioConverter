from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.audio_codec import AudioCodec
from src.models.audio_task import AudioTask


class ConversionWorker(QObject):
    """在后台执行转换，避免阻塞界面事件循环。"""

    log_message = Signal(str)
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, converter, tasks):
        super().__init__()
        self.converter = converter
        self.tasks = tasks

    @Slot()
    def run(self):
        try:
            outputs = []
            for index, task in enumerate(self.tasks, start=1):
                self.log_message.emit(
                    f"[{index}/{len(self.tasks)}] 开始转换: {task.input_file.name}"
                )
                self.converter.convert(task, log_callback=self.log_message.emit)
                outputs.append(str(task.output_file))
                self.log_message.emit(f"[{index}/{len(self.tasks)}] 转换完成: {task.output_file}")
            self.completed.emit(outputs)
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self, converter):
        super().__init__()
        self.converter = converter
        self.input_files = []
        self.thread = None
        self.worker = None

        self.setWindowTitle("Audio Converter")
        self.resize(720, 500)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        input_btn = QPushButton("浏览")
        input_btn.clicked.connect(self.select_inputs)
        input_layout.addWidget(QLabel("输入文件:"))
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(input_btn)
        layout.addLayout(input_layout)

        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        output_btn = QPushButton("浏览")
        output_btn.clicked.connect(self.select_output)
        output_layout.addWidget(QLabel("输出目录:"))
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        self.codec_box = QComboBox()
        for codec in AudioCodec:
            self.codec_box.addItem(codec.display_name, codec)
        layout.addWidget(QLabel("输出编码:"))
        layout.addWidget(self.codec_box)

        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.clicked.connect(self.convert)
        layout.addWidget(self.convert_btn)

        layout.addWidget(QLabel("转换日志:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(3000)
        layout.addWidget(self.log)

    def append_log(self, message):
        self.log.append(message)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def select_inputs(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音频文件", "", "Audio Files (*.mp3 *.wav *.flac *.m4a *.ogg)"
        )
        if files:
            self.input_files = files
            self.input_edit.setText(f"已选择 {len(files)} 个文件")
            self.append_log(f"已添加 {len(files)} 个待转换文件")

    def select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_edit.setText(folder)

    def convert(self):
        output_dir = self.output_edit.text().strip()
        if not self.input_files:
            self.append_log("请选择输入文件")
            return
        if not output_dir:
            self.append_log("请选择输出目录")
            return

        codec = self.codec_box.currentData()
        tasks = [
            AudioTask(
                input_file=Path(input_file),
                output_file=Path(output_dir) / f"{Path(input_file).stem}{codec.extension}",
                codec=codec,
            )
            for input_file in self.input_files
        ]
        self.convert_btn.setEnabled(False)
        self.append_log("=" * 40)
        self.append_log(f"准备转换 {len(tasks)} 个文件")

        self.thread = QThread(self)
        self.worker = ConversionWorker(self.converter, tasks)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log_message.connect(self.append_log)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def on_completed(self, outputs):
        self.append_log(f"全部转换完成，共 {len(outputs)} 个文件。")

    def on_failed(self, error):
        self.append_log(f"转换失败: {error}")

    def on_thread_finished(self):
        self.convert_btn.setEnabled(True)
        self.thread = None
        self.worker = None
