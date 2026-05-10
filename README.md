# media-converter

> Built out of frustration. Couldn't find a single tool that handled the `.media` files cheap cameras dump onto SD cards. ffmpeg, VLC, Handbrake - nothing touched them. So this got vibe-coded into existence.

Scans a folder for media files and converts them using ffmpeg. Comes in two flavours: Python (PyQt6) and Go (Fyne). Both have a GUI and a CLI.

**Take it. Use it. Change it. Ship it.** MIT licensed, no strings attached. See [LICENSE](LICENSE).

## Requirements

- Python 3.10+
- ffmpeg + ffprobe on PATH
- GUI only: `pip install PyQt6`

## Files

| File | Purpose |
|------|---------|
| `media_converter.py` | CLI pipeline |
| `media-converter-gui.py` | PyQt6 GUI |
| `media_extractor.py` | `.media` file extractor |

All three need to be in the same directory.

## GUI

```bash
pip install PyQt6
python media-converter-gui.py
```

Pick a format (mp4, mkv, avi, mov, webm, mp3, wav, flac, aac, opus or custom), tick any options you need, hit Run.

| Checkbox | Flag | What it does |
|----------|------|-------------|
| Recursive | `-r` | Recurse into subfolders |
| Merge | `-m` | Merge output into one file per folder |
| Dry Run | `-n` | Preview only, nothing gets converted |
| All Files | `-a` | Probe every file regardless of extension |

## CLI

```
python media_converter.py <input_folder> <output_format> <output_path> [options]
```

```bash
python media_converter.py ./input mp4 ./output
python media_converter.py ./input mp4 ./output -r -m
python media_converter.py ./input mp4 ./output -r -n
python media_converter.py ./input mp4 ./output -a
```

## .media files

Some cheap cameras write recordings in a proprietary `.media` format that nothing else reads. This tool detects them and extracts them automatically - you just point it at the folder and ask for mp4 (or whatever).

Internally it walks the block structure, splits the interleaved video and audio payloads, strips per-block trailer bytes from the audio (skipping this causes a periodic click), muxes everything into an intermediate MKV, then runs it through the normal ffmpeg pipeline.

**Format (reverse-engineered):**
- 8-byte file header
- Blocks: `[4-byte size][4-byte ts][9d 01 00 00][4-byte ts][91 78 23 e1][payload]`
- Video payload: raw H.265/HEVC NAL units starting with `00 00 00 01`
- Audio payload: 16-bit little-endian PCM at 8 kHz mono, with an 8-byte trailer per block

**Limitations:**
- Audio is hard-coded to 8 kHz mono. Different rate? Edit `AUDIO_SAMPLE_RATE` in `media_extractor.py`.
- Reverse-engineered from one device family. Other vendors using `.media` may be completely different.

## Go version

The Go version lives in `go/` and compiles to a single native binary with no runtime dependencies (beyond ffmpeg on PATH). Launches the GUI by default, CLI is opt-in.

```bash
# GUI (default)
./media-converter

# CLI
./media-converter --cli <input_folder> <output_format> <output_path> [options]
./media-converter --cli ./input mp4 ./output -r -m
```

On Windows the binary is built as a GUI app so double-clicking it opens the GUI with no console window. Running `--cli` from a terminal works normally - it attaches to the existing console automatically.

## Building

Run the script for your OS from the project root. Each one installs dependencies and drops the binary in `dist/`.

**Python (PyInstaller)**
```bash
# Linux
./installers/install-linux.sh

# macOS
./installers/install-macos.sh

# Windows (PowerShell, run as Admin)
.\installers\install-windows.ps1
```

**Go**
```bash
# Linux
./installers/build-go-linux.sh

# macOS
./installers/build-go-macos.sh

# Windows (PowerShell, run as Admin)
.\installers\build-go-windows.ps1
```

Or build the Go version manually if you already have Go 1.21+ installed:
```bash
cd go && go build -o ../dist/media-converter .
```

ffmpeg is not bundled and must be on PATH at runtime.

## Notes

- Files with no audio or video streams are skipped.
- Cover art embedded as a video stream is not counted as video.
- Audio-only formats drop the video stream automatically.
- `--merge` converts to temp files first, then concatenates. Temp files are cleaned up after.

## License

MIT, see [LICENSE](LICENSE). Do whatever you want with it.
