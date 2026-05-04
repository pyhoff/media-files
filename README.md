# media-converter

Scan a folder for media files, inspect their streams, and convert them using ffmpeg.

## Requirements

- Python 3.10+
- ffmpeg + ffprobe on PATH

## Usage

```
python media-converter.py <input_folder> <output_format> <output_path> [options]
```

## Options

| Flag | Long | Description |
|------|------|-------------|
| `-r` | `--recursive` | Recurse into subfolders |
| `-m` | `--merge` | Merge all converted files into one; with `-r`, one file per folder |
| `-n` | `--dry-run` | Analyze only, no conversion |
| `-a` | `--all-files` | Probe every file regardless of extension |

## Examples

```bash
# Convert all .media files in a folder to mp4
python media-converter.py ./input mp4 ./output

# Recursively convert and merge each subfolder into one file
python media-converter.py ./input mp4 ./output -r -m

# Preview what would happen without converting
python media-converter.py ./input mp4 ./output -r -n

# Force-probe all files regardless of extension
python media-converter.py ./input mp4 ./output -a
```

## Notes

- Files with no valid audio or video streams are skipped.
- Cover art embedded as a video stream is not counted as video.
- Audio-only output formats (mp3, wav, etc.) will drop the video stream automatically.
- `--merge` converts to temp files first, then concatenates with ffmpeg's concat demuxer. Temp files are cleaned up after merging.
