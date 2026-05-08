# media-converter

Scan a folder for media files, inspect their streams, and convert them using ffmpeg.
Includes both a CLI and a PyQt6 GUI.

Also supports a proprietary `.media` container format used by some WiFi camera/speaker
devices — these files are auto-detected and extracted transparently.

## Requirements

- Python 3.10+
- ffmpeg + ffprobe on PATH
- GUI only: `pip install PyQt6`

## Files

| File | Purpose |
|------|---------|
| `media_converter.py` | CLI entry point and pipeline |
| `media_converter_gui.py` | PyQt6 GUI front-end |
| `media_extractor.py` | Helper module for proprietary `.media` files |

All three must live in the same directory.

## GUI

```bash
pip install PyQt6
python media_converter_gui.py
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

## `.media` File Support

Some WiFi camera/speaker devices write recordings to SD card in a proprietary
`.media` container format that standard tools (ffmpeg, VLC) cannot read directly.
This tool detects and extracts them automatically.

### What it does

When a `.media` file is encountered, the converter:

1. Walks the file's block structure using its dual-marker pattern
2. Separates the interleaved video and audio payloads
3. Strips per-block trailer bytes from the audio (otherwise produces a periodic click)
4. Muxes the streams into an intermediate MKV
5. Feeds that MKV through the normal ffmpeg conversion pipeline

The output is a normal `.mp4`, `.mkv`, `.mp3`, etc. — whatever you asked for.

### Format details (reverse-engineered)

For reference, the `.media` container looks like this:

- **File header:** 8 bytes
- **Blocks:** `[4-byte size][4-byte ts][9d 01 00 00][4-byte ts][91 78 23 e1][payload]`
- **Video payload:** raw H.265/HEVC NAL units (begin with `00 00 00 01`)
- **Audio payload:** 16-bit little-endian PCM @ 8 kHz mono, with an 8-byte
  trailer per block that must be stripped before concatenating

### Limitations

- Audio sample rate is hard-coded to 8 kHz mono. If your device records at a
  different rate, edit `AUDIO_SAMPLE_RATE` in `media_extractor.py`.
- The format was reverse-engineered from one device family; other vendors using
  the `.media` extension may use a completely different layout.

## Building an Executable

Use [PyInstaller](https://pyinstaller.org) to package the GUI into a standalone binary.
You must build on the target OS — cross-compilation is not supported.

### Install PyInstaller

```bash
pip install pyinstaller
```

### Linux

```bash
pyinstaller --onefile --windowed media_converter_gui.py
```

Output: `dist/media_converter_gui`

Make it executable if needed:
```bash
chmod +x dist/media_converter_gui
```

### Windows

Run in a Command Prompt or PowerShell:
```bat
pyinstaller --onefile --windowed media_converter_gui.py
```

Output: `dist\media_converter_gui.exe`

To add a custom icon:
```bat
pyinstaller --onefile --windowed --icon=icon.ico media_converter_gui.py
```

### macOS

```bash
pyinstaller --onefile --windowed media_converter_gui.py
```

Output: `dist/media_converter_gui`

To build a proper `.app` bundle:
```bash
pyinstaller --windowed --name "Media Converter" media_converter_gui.py
```

Output: `dist/Media Converter.app`

---

> **Note:** ffmpeg and ffprobe must still be installed separately on the end user's machine and available on PATH. They are not bundled into the executable.

## Notes

- Files with no valid audio or video streams are skipped.
- Cover art embedded as a video stream is not counted as video.
- Audio-only formats (mp3, wav, etc.) automatically drop the video stream.
- `--merge` converts to temp files first, then concatenates with ffmpeg's concat demuxer. Temp files are cleaned up after merging.
- `.media` files are extracted to intermediate MKVs in a temp directory that's cleaned up at the end of each run.
