from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
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
    """在后台转换文件，并把日志和整体进度发送给界面线程。"""

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
                self.log_message.emit(f"[{index}/{total}] 开始转换：{task.input_file.name}")
                self.converter.convert(task, log_callback=self.log_message.emit)
                outputs.append(str(task.output_file))
                self.progress_changed.emit(index, total)
                self.log_message.emit(f"[{index}/{total}] 转换完成：{task.output_file}")
            self.completed.emit(outputs)
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self, converter, output_dir="output"):
        super().__init__()
        self.converter = converter
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

        # 每个页签代表一项可选功能
        self.feature_tabs = QTabWidget()
        root_layout.addWidget(self.feature_tabs)

        converter_page = QWidget()
        self.feature_tabs.addTab(converter_page, "格式转换")
        layout = QVBoxLayout(converter_page)

        content_layout = QHBoxLayout()
        layout.addLayout(content_layout, stretch=1)

        file_group = QGroupBox("待转换文件")
        file_layout = QVBoxLayout(file_group)
        button_layout = QHBoxLayout()
        self.choose_btn = QPushButton("选择文件")
        self.add_btn = QPushButton("增加文件")
        self.remove_btn = QPushButton("删除文件")
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

        operation_group = QGroupBox("转换设置")
        operation_layout = QGridLayout(operation_group)
        operation_layout.addWidget(QLabel("输出编码"), 0, 0)
        self.codec_box = QComboBox()
        for codec in AudioCodec:
            self.codec_box.addItem(codec.display_name, codec)
        operation_layout.addWidget(self.codec_box, 1, 0)

        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.clicked.connect(self.convert)
        operation_layout.addWidget(self.convert_btn, 2, 0)

        operation_layout.addWidget(QLabel("转换进度"), 3, 0)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setValue(0)
        self.progress.setFormat("0 / 0")
        operation_layout.addWidget(self.progress, 4, 0)
        operation_layout.setRowStretch(5, 1)
        content_layout.addWidget(operation_group, stretch=2)

        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(3000)
        log_layout.addWidget(self.log)
        layout.addWidget(log_group, stretch=1)
        self.update_remove_button()

    def append_log(self, message):
        self.log.append(message)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def choose_files(self):
        """重新选择文件，并替换当前待处理列表。"""
        files = self.open_audio_files()
        if files:
            self.set_input_files(files)
            self.append_log(f"已选择 {len(files)} 个待转换文件")

    def add_files(self):
        """将新选择的文件追加至列表，重复路径会自动忽略。"""
        files = self.open_audio_files()
        if not files:
            return

        existing = set(self.input_files)
        added = [file for file in files if file not in existing]
        self.set_input_files([*self.input_files, *added])
        self.append_log(f"已增加 {len(added)} 个文件；当前共 {len(self.input_files)} 个")

    def open_audio_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择音频文件", "", AUDIO_FILE_FILTER)
        return files

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
        self.append_log(f"已从待转换列表移除：{Path(removed_file).name}")
        self.update_remove_button()

    def convert(self):
        if not self.input_files:
            self.append_log("请选择至少一个输入文件")
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
        self.append_log(f"准备转换 {len(tasks)} 个文件，输出目录：{self.output_dir}")

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
        self.append_log(f"全部转换完成，共 {len(outputs)} 个文件。")

    def on_failed(self, error):
        self.append_log(f"转换失败：{error}")

    def on_thread_finished(self):
        self.set_controls_enabled(True)
        self.thread = None
        self.worker = None

    def set_controls_enabled(self, enabled):
        self.choose_btn.setEnabled(enabled)
        self.add_btn.setEnabled(enabled)
        self.codec_box.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled and self.file_list.currentRow() >= 0)
