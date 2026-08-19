from pathlib import Path
import threading

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from src.core.ffmpeg_service import ConversionCancelled
from src.models.audio_task import AudioTask


AUDIO_FILE_FILTER = "Audio Files (*.mp3 *.wav *.flac *.m4a *.ogg)"
AUDIO_FILE_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}

CODEC_PREVIEW_DETAILS = {
    AudioCodec.MP3: ("有损压缩", "编码器默认"),
    AudioCodec.AAC: ("有损压缩", "编码器默认"),
    AudioCodec.FLAC: ("无损压缩", "无损，由音频内容决定"),
    AudioCodec.WAV: ("无压缩 PCM", "随采样率和声道数变化"),
    AudioCodec.OPUS: ("有损压缩", "编码器默认"),
    AudioCodec.OGG: ("有损压缩", "编码器默认"),
}


class AudioFileListWidget(QListWidget):
    """A file list that accepts supported local audio files by drag and drop."""

    files_dropped = Signal(list, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    @staticmethod
    def audio_files_from_mime_data(mime_data):
        files = []
        rejected = 0
        if not mime_data.hasUrls():
            return files, rejected

        for url in mime_data.urls():
            if not url.isLocalFile():
                rejected += 1
                continue
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
                files.append(str(path))
            else:
                rejected += 1
        return files, rejected

    def dragEnterEvent(self, event):
        files, _ = self.audio_files_from_mime_data(event.mimeData())
        if files:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        files, _ = self.audio_files_from_mime_data(event.mimeData())
        if files:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files, rejected = self.audio_files_from_mime_data(event.mimeData())
        if not files:
            event.ignore()
            return
        self.files_dropped.emit(files, rejected)
        event.acceptProposedAction()


class ConversionWorker(QObject):
    """Run conversion in a worker thread and report status to the UI."""

    log_message = Signal(str)
    progress_changed = Signal(int, int)
    completed = Signal(list)
    cancelled = Signal(list, int)
    failed = Signal(str)

    def __init__(self, converter, tasks):
        super().__init__()
        self.converter = converter
        self.tasks = tasks
        self.cancellation_event = threading.Event()

    def request_cancel(self):
        self.cancellation_event.set()
        self.converter.cancel_current_conversion()

    @Slot()
    def run(self):
        try:
            outputs = []
            total = len(self.tasks)
            for index, task in enumerate(self.tasks, start=1):
                if self.cancellation_event.is_set():
                    self.cancelled.emit(outputs, total)
                    return
                self.log_message.emit(f"[{index}/{total}] \u5f00\u59cb\u8f6c\u6362\uff1a{task.input_file.name}")
                self.converter.convert(
                    task,
                    log_callback=self.log_message.emit,
                    cancellation_event=self.cancellation_event,
                )
                outputs.append(str(task.output_file))
                self.progress_changed.emit(index, total)
                self.log_message.emit(f"[{index}/{total}] \u8f6c\u6362\u5b8c\u6210\uff1a{task.output_file}")
            if self.cancellation_event.is_set():
                self.cancelled.emit(outputs, total)
            else:
                self.completed.emit(outputs)
        except ConversionCancelled:
            self.cancelled.emit(outputs, total)
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self, converter, config, output_dir="output"):
        super().__init__()
        self.converter = converter
        self.config = config
        self.output_dir = Path(output_dir)
        self.input_files = []
        self.metadata_files = []
        self.metadata_loaded = False
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

        self.file_list = AudioFileListWidget()
        self.file_list.setToolTip("\u53ef\u5c06\u97f3\u9891\u6587\u4ef6\u62d6\u62fd\u5230\u6b64\u5904\u5bfc\u5165")
        self.file_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.file_list.itemSelectionChanged.connect(self.update_remove_button)
        self.file_list.files_dropped.connect(self.import_dropped_conversion_files)
        file_layout.addWidget(self.file_list, stretch=1)
        content_layout.addWidget(file_group, stretch=3)

        operation_group = QGroupBox("\u8f6c\u6362\u8bbe\u7f6e")
        operation_layout = QGridLayout(operation_group)
        operation_layout.addWidget(QLabel("\u8f93\u51fa\u7f16\u7801"), 0, 0)
        self.codec_box = QComboBox()
        for codec in AudioCodec:
            self.codec_box.addItem(codec.display_name, codec)
        self.codec_box.currentIndexChanged.connect(self.update_codec_preview)
        operation_layout.addWidget(self.codec_box, 1, 0)

        self.convert_btn = QPushButton("\u5f00\u59cb\u8f6c\u6362")
        self.convert_btn.clicked.connect(self.convert)
        operation_layout.addWidget(self.convert_btn, 2, 0)
        operation_layout.addWidget(QLabel("\u8f6c\u6362\u8fdb\u5ea6"), 3, 0)
        self.progress = QProgressBar()
        self.progress.setFormat("0 / 0")
        operation_layout.addWidget(self.progress, 4, 0)
        self.cancel_btn = QPushButton("\u53d6\u6d88")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet(
            "QPushButton { color: #c62828; font-weight: bold; }"
            "QPushButton:disabled { color: #c98b8b; }"
        )
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        operation_layout.addWidget(self.cancel_btn, 4, 1)
        operation_layout.setColumnStretch(0, 1)

        operation_layout.addWidget(QLabel("\u8f93\u51fa\u9884\u89c8"), 5, 0, 1, 2)
        self.codec_preview = QLabel()
        self.codec_preview.setWordWrap(True)
        self.codec_preview.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.codec_preview.setStyleSheet(
            "QLabel { background-color: #f7f7f7; border: 1px solid #c7c7c7; "
            "padding: 7px; color: #333333; }"
        )
        operation_layout.addWidget(self.codec_preview, 6, 0, 1, 2)
        operation_layout.setRowStretch(6, 1)
        self.update_codec_preview()
        content_layout.addWidget(operation_group, stretch=2)

        log_group = QGroupBox("\u65e5\u5fd7")
        log_layout = QVBoxLayout(log_group)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(3000)
        log_layout.addWidget(self.log)
        layout.addWidget(log_group, stretch=1)

        self.init_metadata_page()
        self.init_settings_page()

        # Settings remains a page, but its entry lives at the far right of the tab bar.
        self.feature_tabs.tabBar().setTabVisible(self.settings_page_index, False)
        self.settings_btn = QPushButton("\u8bbe\u7f6e")
        self.settings_btn.clicked.connect(
            lambda: self.feature_tabs.setCurrentIndex(self.settings_page_index)
        )
        self.feature_tabs.setCornerWidget(self.settings_btn, Qt.Corner.TopRightCorner)
        self.update_remove_button()

    def init_metadata_page(self):
        metadata_page = QWidget()
        self.feature_tabs.addTab(metadata_page, "\u4fee\u6539\u4fe1\u606f")
        layout = QVBoxLayout(metadata_page)

        content_layout = QHBoxLayout()
        layout.addLayout(content_layout, stretch=1)

        file_group = QGroupBox("\u6d4f\u89c8\u6587\u4ef6")
        file_layout = QVBoxLayout(file_group)
        button_layout = QHBoxLayout()
        self.metadata_choose_btn = QPushButton("\u9009\u62e9\u6587\u4ef6")
        self.metadata_add_btn = QPushButton("\u589e\u52a0\u6587\u4ef6")
        self.metadata_remove_btn = QPushButton("\u5220\u9664\u6587\u4ef6")
        self.metadata_choose_btn.clicked.connect(self.choose_metadata_files)
        self.metadata_add_btn.clicked.connect(self.add_metadata_files)
        self.metadata_remove_btn.clicked.connect(self.remove_selected_metadata_file)
        button_layout.addWidget(self.metadata_choose_btn)
        button_layout.addWidget(self.metadata_add_btn)
        button_layout.addWidget(self.metadata_remove_btn)
        file_layout.addLayout(button_layout)

        self.metadata_file_list = AudioFileListWidget()
        self.metadata_file_list.setToolTip("\u53ef\u5c06\u97f3\u9891\u6587\u4ef6\u62d6\u62fd\u5230\u6b64\u5904\u5bfc\u5165")
        self.metadata_file_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.metadata_file_list.currentRowChanged.connect(self.load_selected_metadata)
        self.metadata_file_list.files_dropped.connect(self.import_dropped_metadata_files)
        file_layout.addWidget(self.metadata_file_list, stretch=1)
        content_layout.addWidget(file_group, stretch=2)

        information_group = QGroupBox("\u4fee\u6539\u97f3\u9891\u4fe1\u606f")
        information_layout = QGridLayout(information_group)
        self.metadata_name_label = QLabel("\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u97f3\u9891\u6587\u4ef6")
        self.metadata_name_label.setWordWrap(True)
        information_layout.addWidget(self.metadata_name_label, 0, 0, 1, 2)

        field_labels = [
            ("title", "\u6807\u9898"),
            ("artist", "\u53c2\u4e0e\u521b\u4f5c\u7684\u827a\u672f\u5bb6"),
            ("album", "\u4e13\u8f91"),
            ("album_artist", "\u4e13\u8f91\u827a\u672f\u5bb6"),
            ("genre", "\u6d41\u6d3e"),
            ("date", "\u5e74\u4efd"),
            ("track", "\u97f3\u8f68\u53f7"),
        ]
        self.metadata_edits = {}
        for row, (key, label) in enumerate(field_labels, start=1):
            information_layout.addWidget(QLabel(label), row, 0)
            edit = QLineEdit()
            edit.setEnabled(False)
            information_layout.addWidget(edit, row, 1)
            self.metadata_edits[key] = edit

        self.metadata_status = QLabel("")
        self.metadata_status.setWordWrap(True)
        information_layout.addWidget(self.metadata_status, len(field_labels) + 1, 0, 1, 2)
        information_layout.setRowStretch(len(field_labels) + 2, 1)

        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_metadata_btn = QPushButton("\u4fdd\u5b58")
        self.save_metadata_btn.setEnabled(False)
        self.save_metadata_btn.clicked.connect(self.save_metadata)
        save_layout.addWidget(self.save_metadata_btn)
        information_layout.addLayout(save_layout, len(field_labels) + 3, 0, 1, 2)
        information_layout.setColumnStretch(1, 1)
        content_layout.addWidget(information_group, stretch=3)

        self.update_metadata_controls()

    def init_settings_page(self):
        settings_page = QWidget()
        self.settings_page_index = self.feature_tabs.addTab(settings_page, "\u8bbe\u7f6e")
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

    def update_codec_preview(self):
        codec = self.codec_box.currentData()
        if codec is None:
            self.codec_preview.clear()
            return

        compression_type, bitrate = CODEC_PREVIEW_DETAILS[codec]
        self.codec_preview.setText(
            f"\u683c\u5f0f\uff1a{codec.display_name} ({codec.extension})\n"
            f"\u7f16\u7801\u5668\uff1a{codec.ffmpeg_codec}\n"
            f"\u7c7b\u578b\uff1a{compression_type}\n"
            f"\u7801\u7387\uff1a{bitrate}\n"
            "\u91c7\u6837\u7387\uff1a\u4fdd\u6301\u6e90\u6587\u4ef6\n"
            "\u58f0\u9053\uff1a\u4fdd\u6301\u6e90\u6587\u4ef6"
        )

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

    @staticmethod
    def normalized_path_key(file):
        return str(Path(file).resolve()).casefold()

    def import_dropped_conversion_files(self, files, rejected):
        existing = {self.normalized_path_key(file) for file in self.input_files}
        added = []
        for file in files:
            key = self.normalized_path_key(file)
            if key not in existing:
                existing.add(key)
                added.append(file)

        if added:
            self.set_input_files([*self.input_files, *added])
        skipped = rejected + len(files) - len(added)
        message = f"\u5df2\u901a\u8fc7\u62d6\u62fd\u5bfc\u5165 {len(added)} \u4e2a\u5f85\u8f6c\u6362\u6587\u4ef6"
        if skipped:
            message += f"\uff0c\u8df3\u8fc7 {skipped} \u4e2a\u4e0d\u652f\u6301\u6216\u91cd\u590d\u7684\u6587\u4ef6"
        self.append_log(message)

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

    def choose_metadata_files(self):
        files = self.open_audio_files()
        if files:
            self.set_metadata_files(files)

    def add_metadata_files(self):
        files = self.open_audio_files()
        if not files:
            return
        existing = set(self.metadata_files)
        added = [file for file in files if file not in existing]
        current_row = self.metadata_file_list.currentRow()
        self.set_metadata_files([*self.metadata_files, *added], current_row)

    def set_metadata_files(self, files, selected_row=0):
        self.metadata_files = files
        self.metadata_file_list.blockSignals(True)
        self.metadata_file_list.clear()
        for file in files:
            self.metadata_file_list.addItem(Path(file).name)
            self.metadata_file_list.item(self.metadata_file_list.count() - 1).setToolTip(file)
        self.metadata_file_list.blockSignals(False)
        if files:
            self.metadata_file_list.setCurrentRow(max(0, min(selected_row, len(files) - 1)))
        else:
            self.load_selected_metadata(-1)
        self.update_metadata_controls()

    def import_dropped_metadata_files(self, files, rejected):
        existing = {self.normalized_path_key(file) for file in self.metadata_files}
        added = []
        for file in files:
            key = self.normalized_path_key(file)
            if key not in existing:
                existing.add(key)
                added.append(file)

        current_row = self.metadata_file_list.currentRow()
        if added:
            self.set_metadata_files([*self.metadata_files, *added], current_row)
        skipped = rejected + len(files) - len(added)
        message = f"\u5df2\u901a\u8fc7\u62d6\u62fd\u5bfc\u5165 {len(added)} \u4e2a\u5f85\u4fee\u6539\u6587\u4ef6"
        if skipped:
            message += f"\uff0c\u8df3\u8fc7 {skipped} \u4e2a\u4e0d\u652f\u6301\u6216\u91cd\u590d\u7684\u6587\u4ef6"
        self.append_log(message)

    def remove_selected_metadata_file(self):
        row = self.metadata_file_list.currentRow()
        if row < 0:
            return
        files = [*self.metadata_files]
        files.pop(row)
        self.set_metadata_files(files, min(row, len(files) - 1))

    def update_metadata_controls(self):
        has_selection = 0 <= self.metadata_file_list.currentRow() < len(self.metadata_files)
        self.metadata_remove_btn.setEnabled(has_selection)
        self.save_metadata_btn.setEnabled(has_selection and self.metadata_loaded)
        for edit in self.metadata_edits.values():
            edit.setEnabled(has_selection and self.metadata_loaded)

    def clear_metadata_fields(self):
        for edit in self.metadata_edits.values():
            edit.clear()

    def load_selected_metadata(self, row):
        self.metadata_loaded = False
        self.clear_metadata_fields()
        self.metadata_status.clear()
        if row < 0 or row >= len(self.metadata_files):
            self.metadata_name_label.setText("\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u97f3\u9891\u6587\u4ef6")
            self.update_metadata_controls()
            return

        audio_file = Path(self.metadata_files[row])
        self.metadata_name_label.setText(f"\u5f53\u524d\u6587\u4ef6：{audio_file.name}")
        try:
            metadata = self.converter.ffmpeg.read_metadata(audio_file)
        except Exception as error:
            self.metadata_status.setText(f"\u8bfb\u53d6\u5931\u8d25：{error}")
            self.update_metadata_controls()
            return

        for key, edit in self.metadata_edits.items():
            edit.setText(metadata.get(key, ""))
        self.metadata_loaded = True
        self.metadata_status.setText("\u5df2\u8bfb\u53d6\u97f3\u9891\u4fe1\u606f")
        self.update_metadata_controls()

    def save_metadata(self):
        row = self.metadata_file_list.currentRow()
        if row < 0 or row >= len(self.metadata_files):
            return

        audio_file = Path(self.metadata_files[row])
        metadata = {key: edit.text().strip() for key, edit in self.metadata_edits.items()}
        self.save_metadata_btn.setEnabled(False)
        self.metadata_status.setText("\u6b63\u5728\u4fdd\u5b58……")
        try:
            self.converter.ffmpeg.update_metadata(audio_file, metadata)
        except Exception as error:
            self.metadata_status.setText(f"\u4fdd\u5b58\u5931\u8d25：{error}")
            QMessageBox.critical(self, "\u4fdd\u5b58\u5931\u8d25", str(error))
        else:
            self.metadata_status.setText(
                "\u4fdd\u5b58\u6210\u529f，Windows \u8d44\u6e90\u7ba1\u7406\u5668\u53ef\u80fd\u9700\u8981\u5237\u65b0\u540e\u663e\u793a\u65b0\u4fe1\u606f。"
            )
        finally:
            self.update_metadata_controls()

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
        self.worker.cancelled.connect(self.on_cancelled)
        self.worker.failed.connect(self.on_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.cancelled.connect(self.thread.quit)
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
        self.cancel_btn.setEnabled(False)
        self.append_log(f"\u5168\u90e8\u8f6c\u6362\u5b8c\u6210\uff0c\u5171 {len(outputs)} \u4e2a\u6587\u4ef6\u3002")

    def cancel_conversion(self):
        if self.worker is None or not self.cancel_btn.isEnabled():
            return
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("\u6b63\u5728\u53d6\u6d88\u2026")
        self.append_log("\u6b63\u5728\u53d6\u6d88\u8f6c\u6362\uff0c\u8bf7\u7a0d\u5019\u2026")
        self.worker.request_cancel()

    def on_cancelled(self, outputs, total):
        self.cancel_btn.setEnabled(False)
        self.append_log(
            f"\u8f6c\u6362\u5df2\u53d6\u6d88\uff1a\u5df2\u5b8c\u6210 {len(outputs)} \u4e2a\uff0c"
            f"\u672a\u5904\u7406 {total - len(outputs)} \u4e2a\u3002"
        )

    def on_failed(self, error):
        self.cancel_btn.setEnabled(False)
        self.append_log(f"\u8f6c\u6362\u5931\u8d25\uff1a{error}")

    def on_thread_finished(self):
        self.set_controls_enabled(True)
        self.cancel_btn.setText("\u53d6\u6d88")
        self.thread = None
        self.worker = None

    def set_controls_enabled(self, enabled):
        self.output_edit.setEnabled(enabled)
        self.ffmpeg_edit.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.ffmpeg_browse_btn.setEnabled(enabled)
        self.save_settings_btn.setEnabled(enabled)
        self.settings_btn.setEnabled(enabled)
        self.choose_btn.setEnabled(enabled)
        self.add_btn.setEnabled(enabled)
        self.file_list.setEnabled(enabled)
        self.codec_box.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(not enabled)
        self.remove_btn.setEnabled(enabled and self.file_list.currentRow() >= 0)
