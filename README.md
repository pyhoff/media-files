# media-converter

Scan a folder for media files, inspect their streams, and convert them using ffmpeg.
Includes both a CLI and a PyQt6 GUI.

## Requirements

- Python 3.10+
- ffmpeg + ffprobe on PATH
- GUI only: `pip install PyQt6`

## GUI

```bash
pip install PyQt6
python media-converter-gui.py
```

**Format selector** — radio buttons for common formats, grouped by type:

| Video | Audio |
|-------|-------|
| mp4, mkv, avi, mov, webm | mp3, wav, flac, aac, opus |

A **Custom** option lets you type any format ffmpeg supports.

**Options:**

| Checkbox | Flag | Description |
|----------|------|-------------|
| Recursive | `-r` | Recurse into subfolders |
| Merge | `-m` | Merge output into one file; one file per folder with Recursive |
| Dry Run | `-n` | Analyze only, no conversion |
| All Files | `-a` | Probe every file regardless of extension |

The log area streams output live as conversion runs.

## CLI

```
python media_converter.py <input_folder> <output_format> <output_path> [options]
```

### Options

| Flag | Long | Description |
|------|------|-------------|
| `-r` | `--recursive` | Recurse into subfolders |
| `-m` | `--merge` | Merge all converted files into one; with `-r`, one file per folder |
| `-n` | `--dry-run` | Analyze only, no conversion |
| `-a` | `--all-files` | Probe every file regardless of extension |

### Examples

```bash
# Convert all .media files in a folder to mp4
python media_converter.py ./input mp4 ./output

# Recursively convert and merge each subfolder into one file
python media_converter.py ./input mp4 ./output -r -m

# Preview what would happen without converting
python media_converter.py ./input mp4 ./output -r -n

# Force-probe all files regardless of extension
python media_converter.py ./input mp4 ./output -a
```

## Building an Executable

Use [PyInstaller](https://pyinstaller.org) to package the GUI into a standalone binary.
You must build on the target OS — cross-compilation is not supported.

### Install PyInstaller

```bash
pip install pyinstaller
```

### Linux

```bash
pyinstaller --onefile --windowed media-converter-gui.py
```

Output: `dist/media-converter-gui`

Make it executable if needed:
```bash
chmod +x dist/media-converter-gui
```

### Windows

Run in a Command Prompt or PowerShell:
```bat
pyinstaller --onefile --windowed media-converter-gui.py
```

Output: `dist\media-converter-gui.exe`

To add a custom icon:
```bat
pyinstaller --onefile --windowed --icon=icon.ico media-converter-gui.py
```

### macOS

```bash
pyinstaller --onefile --windowed media-converter-gui.py
```

Output: `dist/media-converter-gui`

To build a proper `.app` bundle:
```bash
pyinstaller --windowed --name "Media Converter" media-converter-gui.py
```

Output: `dist/Media Converter.app`

---

> **Note:** ffmpeg and ffprobe must still be installed separately on the end user's machine and available on PATH. They are not bundled into the executable.

## Notes

- Files with no valid audio or video streams are skipped.
- Cover art embedded as a video stream is not counted as video.
- Audio-only formats (mp3, wav, etc.) automatically drop the video stream.
- `--merge` converts to temp files first, then concatenates with ffmpeg's concat demuxer. Temp files are cleaned up after merging.
