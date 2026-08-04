from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.audio_codec import AudioCodec
from src.models.audio_task import AudioTask


AUDIO_FILE_FILTER = "Audio Files (*.mp3 *.wav *.flac *.m4a *.ogg)"


class ConversionWorker(QObject):
    """Run conversion in a worker thread and report status to the UI."""

    log_message = Signal(str)
    progress_changed = Signal(int, int)
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
            total = len(self.tasks)
            for index, task in enumerate(self.tasks, start=1):
                self.log_message.emit(f"[{index}/{total}] \u5f00\u59cb\u8f6c\u6362\uff1a{task.input_file.name}")
                self.converter.convert(task, log_callback=self.log_message.emit)
                outputs.append(str(task.output_file))
                self.progress_changed.emit(index, total)
                self.log_message.emit(f"[{index}/{total}] \u8f6c\u6362\u5b8c\u6210\uff1a{task.output_file}")
            self.completed.emit(outputs)
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self, converter, config, output_dir="output"):
        super().__init__()
        self.converter = converter
        self.config = config
        self.output_dir = Path(output_dir)
        self.input_files = []
        self.thread = None
        self.worker = None

        self.setWindowTitle("Audio Converter")
        self.resize(800, 610)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # Each feature owns a tab. Further functions can be added without changing
        # the conversion page layout.
        self.feature_tabs = QTabWidget()
        root_layout.addWidget(self.feature_tabs)

        converter_page = QWidget()
        self.feature_tabs.addTab(converter_page, "\u683c\u5f0f\u8f6c\u6362")
        layout = QVBoxLayout(converter_page)

        content_layout = QHBoxLayout()
        layout.addLayout(content_layout, stretch=1)

        file_group = QGroupBox("\u5f85\u8f6c\u6362\u6587\u4ef6")
        file_layout = QVBoxLayout(file_group)
        button_layout = QHBoxLayout()
        self.choose_btn = QPushButton("\u9009\u62e9\u6587\u4ef6")
        self.add_btn = QPushButton("\u589e\u52a0\u6587\u4ef6")
        self.remove_btn = QPushButton("\u5220\u9664\u6587\u4ef6")
        self.choose_btn.clicked.connect(self.choose_files)
        self.add_btn.clicked.connect(self.add_files)
        self.remove_btn.clicked.connect(self.remove_selected_file)
        button_layout.addWidget(self.choose_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.remove_btn)
        file_layout.addLayout(button_layout)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.file_list.itemSelectionChanged.connect(self.update_remove_button)
        file_layout.addWidget(self.file_list, stretch=1)
        content_layout.addWidget(file_group, stretch=3)

        operation_group = QGroupBox("\u8f6c\u6362\u8bbe\u7f6e")
        operation_layout = QGridLayout(operation_group)
        operation_layout.addWidget(QLabel("\u8f93\u51fa\u7f16\u7801"), 0, 0)
        self.codec_box = QComboBox()
        for codec in AudioCodec:
            self.codec_box.addItem(codec.display_name, codec)
        operation_layout.addWidget(self.codec_box, 1, 0)

        self.convert_btn = QPushButton("\u5f00\u59cb\u8f6c\u6362")
        self.convert_btn.clicked.connect(self.convert)
        operation_layout.addWidget(self.convert_btn, 2, 0)
        operation_layout.addWidget(QLabel("\u8f6c\u6362\u8fdb\u5ea6"), 3, 0)
        self.progress = QProgressBar()
        self.progress.setFormat("0 / 0")
        operation_layout.addWidget(self.progress, 4, 0)
        operation_layout.setRowStretch(5, 1)
        content_layout.addWidget(operation_group, stretch=2)

        log_group = QGroupBox("\u65e5\u5fd7")
        log_layout = QVBoxLayout(log_group)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(3000)
        log_layout.addWidget(self.log)
        layout.addWidget(log_group, stretch=1)

        self.init_settings_page()
        self.update_remove_button()

    def init_settings_page(self):
        settings_page = QWidget()
        self.feature_tabs.addTab(settings_page, "\u8bbe\u7f6e")
        layout = QVBoxLayout(settings_page)
        settings_group = QGroupBox("\u7a0b\u5e8f\u8bbe\u7f6e")
        settings_layout = QGridLayout(settings_group)

        settings_layout.addWidget(QLabel("\u8f93\u51fa\u76ee\u5f55"), 0, 0)
        self.output_edit = QLineEdit(str(self.output_dir))
        settings_layout.addWidget(self.output_edit, 0, 1)
        self.output_browse_btn = QPushButton("\u6d4f\u89c8")
        self.output_browse_btn.clicked.connect(self.select_output_dir)
        settings_layout.addWidget(self.output_browse_btn, 0, 2)

        settings_layout.addWidget(QLabel("FFmpeg \u8def\u5f84"), 1, 0)
        self.ffmpeg_edit = QLineEdit(self.config.get("ffmpeg_path") or "")
        settings_layout.addWidget(self.ffmpeg_edit, 1, 1)
        self.ffmpeg_browse_btn = QPushButton("\u6d4f\u89c8")
        self.ffmpeg_browse_btn.clicked.connect(self.select_ffmpeg)
        settings_layout.addWidget(self.ffmpeg_browse_btn, 1, 2)

        self.save_settings_btn = QPushButton("\u4fdd\u5b58\u8bbe\u7f6e")
        self.save_settings_btn.clicked.connect(self.save_settings)
        settings_layout.addWidget(self.save_settings_btn, 2, 1)
        settings_layout.setColumnStretch(1, 1)
        layout.addWidget(settings_group)
        layout.addStretch()

    def append_log(self, message):
        self.log.append(message)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def open_audio_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "\u9009\u62e9\u97f3\u9891\u6587\u4ef6", "", AUDIO_FILE_FILTER)
        return files

    def choose_files(self):
        files = self.open_audio_files()
        if files:
            self.set_input_files(files)
            self.append_log(f"\u5df2\u9009\u62e9 {len(files)} \u4e2a\u5f85\u8f6c\u6362\u6587\u4ef6")

    def add_files(self):
        files = self.open_audio_files()
        if not files:
            return
        existing = set(self.input_files)
        added = [file for file in files if file not in existing]
        self.set_input_files([*self.input_files, *added])
        self.append_log(f"\u5df2\u589e\u52a0 {len(added)} \u4e2a\u6587\u4ef6\uff1b\u5f53\u524d\u5171 {len(self.input_files)} \u4e2a")

    def set_input_files(self, files):
        self.input_files = files
        self.file_list.clear()
        for file in self.input_files:
            self.file_list.addItem(Path(file).name)
            self.file_list.item(self.file_list.count() - 1).setToolTip(file)
        self.update_remove_button()

    def update_remove_button(self):
        self.remove_btn.setEnabled(self.file_list.currentRow() >= 0)

    def remove_selected_file(self):
        row = self.file_list.currentRow()
        if row < 0:
            return
        removed_file = self.input_files.pop(row)
        self.file_list.takeItem(row)
        self.append_log(f"\u5df2\u4ece\u5f85\u8f6c\u6362\u5217\u8868\u79fb\u9664\uff1a{Path(removed_file).name}")
        self.update_remove_button()

    def select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "\u9009\u62e9\u8f93\u51fa\u76ee\u5f55", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)

    def select_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "\u9009\u62e9 FFmpeg \u53ef\u6267\u884c\u6587\u4ef6",
            self.ffmpeg_edit.text(),
            "FFmpeg (ffmpeg.exe);;Executable Files (*.exe);;All Files (*)",
        )
        if file_path:
            self.ffmpeg_edit.setText(file_path)

    def save_settings(self):
        output_dir = self.output_edit.text().strip()
        ffmpeg_path = self.ffmpeg_edit.text().strip()
        if not output_dir or not ffmpeg_path:
            self.append_log("\u8bbe\u7f6e\u672a\u4fdd\u5b58\uff1a\u8f93\u51fa\u76ee\u5f55\u548c FFmpeg \u8def\u5f84\u5747\u4e0d\u80fd\u4e3a\u7a7a\u3002")
            return
        self.output_dir = Path(output_dir)
        self.config.config["default_output"] = output_dir
        self.config.config["ffmpeg_path"] = ffmpeg_path
        self.config.save()
        self.converter.ffmpeg.ffmpeg = Path(ffmpeg_path)
        self.append_log(f"\u8bbe\u7f6e\u5df2\u4fdd\u5b58\uff1a\u8f93\u51fa\u76ee\u5f55 {self.output_dir}")

    def convert(self):
        if not self.input_files:
            self.append_log("\u8bf7\u9009\u62e9\u81f3\u5c11\u4e00\u4e2a\u8f93\u5165\u6587\u4ef6")
            return
        codec = self.codec_box.currentData()
        tasks = [
            AudioTask(
                input_file=Path(input_file),
                output_file=self.output_dir / f"{Path(input_file).stem}{codec.extension}",
                codec=codec,
            )
            for input_file in self.input_files
        ]
        self.set_controls_enabled(False)
        self.progress.setRange(0, len(tasks))
        self.progress.setValue(0)
        self.progress.setFormat(f"0 / {len(tasks)}")
        self.append_log("=" * 40)
        self.append_log(f"\u51c6\u5907\u8f6c\u6362 {len(tasks)} \u4e2a\u6587\u4ef6\uff0c\u8f93\u51fa\u76ee\u5f55\uff1a{self.output_dir}")

        self.thread = QThread(self)
        self.worker = ConversionWorker(self.converter, tasks)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log_message.connect(self.append_log)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def update_progress(self, current, total):
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.progress.setFormat(f"{current} / {total}")

    def on_completed(self, outputs):
        self.append_log(f"\u5168\u90e8\u8f6c\u6362\u5b8c\u6210\uff0c\u5171 {len(outputs)} \u4e2a\u6587\u4ef6\u3002")

    def on_failed(self, error):
        self.append_log(f"\u8f6c\u6362\u5931\u8d25\uff1a{error}")

    def on_thread_finished(self):
        self.set_controls_enabled(True)
        self.thread = None
        self.worker = None

    def set_controls_enabled(self, enabled):
        self.output_edit.setEnabled(enabled)
        self.ffmpeg_edit.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.ffmpeg_browse_btn.setEnabled(enabled)
        self.save_settings_btn.setEnabled(enabled)
        self.choose_btn.setEnabled(enabled)
        self.add_btn.setEnabled(enabled)
        self.codec_box.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled and self.file_list.currentRow() >= 0)
