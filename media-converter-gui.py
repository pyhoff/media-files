#!/usr/bin/env python3
"""
GUI front-end for media-converter.py.

Requires: pip install PyQt6
"""

import sys
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton, QCheckBox, QFileDialog,
    QTextEdit, QGroupBox, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFontDatabase

VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm"]
AUDIO_FORMATS = ["mp3", "wav", "flac", "aac", "opus"]


class ConversionWorker(QThread):
    line_ready = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, cmd: list[str]):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            proc = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in proc.stdout:
                self.line_ready.emit(line.rstrip())
            proc.wait()
            self.finished.emit(proc.returncode)
        except Exception as e:
            self.line_ready.emit(f"Error: {e}")
            self.finished.emit(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Media Converter")
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
        input_browse = QPushButton("Browse")
        input_browse.clicked.connect(lambda: self._pick_dir(self.input_folder, "Select Input Folder"))
        form.addRow("Input Folder:", self._hbox(self.input_folder, input_browse))

        self.output_path = QLineEdit()
        output_browse = QPushButton("Browse")
        output_browse.clicked.connect(lambda: self._pick_dir(self.output_path, "Select Output Folder"))
        form.addRow("Output Folder:", self._hbox(self.output_path, output_browse))

        root.addLayout(form)

        # Format selector
        format_group = QGroupBox("Output Format")
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
        self.rb_custom = QRadioButton("Custom:")
        self._format_btn_group.addButton(self.rb_custom)
        self.custom_format = QLineEdit()
        self.custom_format.setPlaceholderText("e.g. vob, m4v …")
        self.custom_format.setMaximumWidth(120)
        self.custom_format.setEnabled(False)
        self.rb_custom.toggled.connect(self.custom_format.setEnabled)
        custom_row.addWidget(self.rb_custom)
        custom_row.addWidget(self.custom_format)
        custom_row.addStretch()
        format_layout.addLayout(custom_row)

        root.addWidget(format_group)

        # Flags
        flags = QHBoxLayout()
        self.cb_recursive = QCheckBox("Recursive  -r")
        self.cb_merge     = QCheckBox("Merge  -m")
        self.cb_dry_run   = QCheckBox("Dry Run  -n")
        self.cb_all_files = QCheckBox("All Files  -a")
        for cb in (self.cb_recursive, self.cb_merge, self.cb_dry_run, self.cb_all_files):
            flags.addWidget(cb)
        flags.addStretch()
        root.addLayout(flags)

        # Run button
        self.run_btn = QPushButton("Run Conversion")
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
            self.log.append("Error: input folder, output format, and output folder are all required.")
            return

        script = Path(__file__).with_name("media-converter.py")
        cmd = [sys.executable, str(script), input_folder, output_format, output_path]

        if self.cb_recursive.isChecked():
            cmd.append("-r")
        if self.cb_merge.isChecked():
            cmd.append("-m")
        if self.cb_dry_run.isChecked():
            cmd.append("-n")
        if self.cb_all_files.isChecked():
            cmd.append("-a")

        self.log.clear()
        self.log.append("$ " + " ".join(cmd) + "\n")
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running…")

        self.worker = ConversionWorker(cmd)
        self.worker.line_ready.connect(self.log.append)
        self.worker.finished.connect(self._done)
        self.worker.start()

    def _done(self, returncode: int):
        status = "Completed" if returncode == 0 else f"Failed (exit {returncode})"
        self.log.append(f"\n{status}")
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Conversion")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
