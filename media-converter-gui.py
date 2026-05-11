#!/usr/bin/env python3
"""
GUI front-end for media_converter.

Requires: pip install PyQt6

Supports proprietary `.media` files (WiFi camera/speaker format) in addition
to all standard ffmpeg-readable formats. .media files are auto-detected and
extracted transparently.
"""

import re
import sys
from pathlib import Path

import media_converter
from media_converter import T

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QCheckBox, QFileDialog,
    QTextEdit, QGroupBox, QRadioButton, QButtonGroup, QLabel,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFontDatabase

VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm"]
AUDIO_FORMATS = ["mp3", "wav", "flac", "aac", "opus"]


class _LineBuffer:
    """File-like object that emits complete lines via a callback."""
    def __init__(self, emit_fn):
        self._emit = emit_fn
        self._buf = ""

    def write(self, text):
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._emit(line)

    def flush(self):
        if self._buf:
            self._emit(self._buf)
            self._buf = ""


class ConversionWorker(QThread):
    line_ready = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, argv: list[str]):
        super().__init__()
        self.argv = argv

    def run(self):
        old_stdout = sys.stdout
        sys.stdout = _LineBuffer(self.line_ready.emit)
        returncode = 0
        try:
            returncode = media_converter.main(self.argv) or 0
        except Exception as e:
            self.line_ready.emit(f"Error: {e}")
            returncode = 1
        finally:
            sys.stdout.flush()
            sys.stdout = old_stdout
        self.finished.emit(returncode)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T.window_title)
        self.setMinimumWidth(680)
        self.worker: ConversionWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # Folder inputs
        form = QFormLayout()
        form.setSpacing(8)

        self.input_folder = QLineEdit()
        input_browse = QPushButton(T.browse)
        input_browse.clicked.connect(lambda: self._pick_dir(self.input_folder, T.input_hint))
        form.addRow(T.input_folder, self._hbox(self.input_folder, input_browse))

        self.output_path = QLineEdit()
        output_browse = QPushButton(T.browse)
        output_browse.clicked.connect(lambda: self._pick_dir(self.output_path, T.output_hint))
        form.addRow(T.output_folder, self._hbox(self.output_path, output_browse))

        root.addLayout(form)

        # Format selector
        format_group = QGroupBox(T.output_format)
        format_layout = QVBoxLayout(format_group)
        format_layout.setSpacing(6)

        self._format_btn_group = QButtonGroup(self)

        video_row = QHBoxLayout()
        video_row.setSpacing(12)
        for fmt in VIDEO_FORMATS:
            rb = QRadioButton(fmt)
            self._format_btn_group.addButton(rb)
            video_row.addWidget(rb)
            if fmt == "mp4":
                rb.setChecked(True)
        video_row.addStretch()
        format_layout.addLayout(video_row)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(12)
        for fmt in AUDIO_FORMATS:
            rb = QRadioButton(fmt)
            self._format_btn_group.addButton(rb)
            audio_row.addWidget(rb)
        audio_row.addStretch()
        format_layout.addLayout(audio_row)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        self.rb_custom = QRadioButton(T.custom_label)
        self._format_btn_group.addButton(self.rb_custom)
        self.custom_format = QLineEdit()
        self.custom_format.setPlaceholderText(T.custom_hint)
        self.custom_format.setMaximumWidth(120)
        self.custom_format.setEnabled(False)
        self.rb_custom.toggled.connect(self.custom_format.setEnabled)
        custom_row.addWidget(self.rb_custom)
        custom_row.addWidget(self.custom_format)
        custom_row.addStretch()
        format_layout.addLayout(custom_row)

        root.addWidget(format_group)

        # Note about .media support
        media_note = QLabel(T.note_media)
        media_note.setWordWrap(True)
        media_note.setStyleSheet("color: gray; font-size: 11px;")
        media_note.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(media_note)

        # Flags
        flags = QHBoxLayout()
        self.cb_recursive = QCheckBox(T.chk_recursive)
        self.cb_merge     = QCheckBox(T.chk_merge)
        self.cb_dry_run   = QCheckBox(T.chk_dry_run)
        self.cb_all_files = QCheckBox(T.chk_all_files)
        for cb in (self.cb_recursive, self.cb_merge, self.cb_dry_run, self.cb_all_files):
            flags.addWidget(cb)
        flags.addStretch()
        root.addLayout(flags)

        # Run button
        self.run_btn = QPushButton(T.run_btn)
        self.run_btn.setFixedHeight(36)
        self.run_btn.clicked.connect(self._run)
        root.addWidget(self.run_btn)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.log.setMinimumHeight(260)
        root.addWidget(self.log)

    def _hbox(self, *widgets) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        for w in widgets:
            layout.addWidget(w)
        return container

    def _pick_dir(self, target: QLineEdit, title: str):
        path = QFileDialog.getExistingDirectory(self, title)
        if path:
            target.setText(path)

    def _selected_format(self) -> str:
        if self.rb_custom.isChecked():
            return self.custom_format.text().strip()
        btn = self._format_btn_group.checkedButton()
        return btn.text() if btn else ""

    def _run(self):
        if self.worker and self.worker.isRunning():
            return

        input_folder  = self.input_folder.text().strip()
        output_format = self._selected_format()
        output_path   = self.output_path.text().strip()

        if not input_folder or not output_format or not output_path:
            self.log.append(T.err_required)
            return

        if not re.fullmatch(r"[a-z0-9]+", output_format):
            self.log.append(T.err_fmt_invalid.format(fmt=output_format))
            return

        argv = [input_folder, output_format, output_path]
        if self.cb_recursive.isChecked():
            argv.append("-r")
        if self.cb_merge.isChecked():
            argv.append("-m")
        if self.cb_dry_run.isChecked():
            argv.append("-n")
        if self.cb_all_files.isChecked():
            argv.append("-a")

        self.log.clear()
        self.log.append(T.starting)
        self.run_btn.setEnabled(False)
        self.run_btn.setText(T.running_btn)

        self.worker = ConversionWorker(argv)
        self.worker.line_ready.connect(self.log.append)
        self.worker.finished.connect(self._done)
        self.worker.start()

    def _done(self, returncode: int):
        status = T.status_done if returncode == 0 else T.status_failed.format(code=returncode)
        self.log.append(f"\n{status}")
        self.run_btn.setEnabled(True)
        self.run_btn.setText(T.run_btn)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
