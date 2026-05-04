#!/usr/bin/env python3
"""
Media file analyzer and converter.

Scans a folder for media files, reports whether each has audio/video streams,
then converts them to the requested output format using ffmpeg.

Usage:
    python media_converter.py <input_folder> <output_format> <output_path> [-r] [--dry-run] [--merge] [--all-files]

Examples:
    python media_converter.py ./videos mp4 ./converted
    python media_converter.py ./media mp3 ./audio_only -r
    python media_converter.py ./clips mkv ./out --dry-run
    python media_converter.py ./clips mp4 ./out --merge
    python media_converter.py ./clips mp4 ./out --merge -r
"""

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

MEDIA_EXTENSIONS = {
    # Video
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".mpg", ".mpeg",
    ".m4v", ".3gp", ".ts", ".mts", ".m2ts", ".vob", ".ogv",
    # Audio
    ".mp3", ".wav", ".aac", ".flac", ".ogg", ".oga", ".m4a", ".wma", ".opus",
    ".aiff", ".alac", ".ac3", ".amr",
    # Other
    ".media",
}

AUDIO_ONLY_FORMATS = {"mp3", "wav", "aac", "flac", "ogg", "m4a", "opus", "wma", "aiff", "ac3"}


def check_dependencies() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            sys.exit(
                f"Error: '{tool}' was not found on PATH. "
                "Please install ffmpeg (https://ffmpeg.org/download.html) and try again."
            )


def probe_file(path: Path) -> dict | None:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def analyze_streams(probe_data: dict) -> tuple[bool, bool, list[str]]:
    has_video = False
    has_audio = False
    codecs: list[str] = []

    for stream in probe_data.get("streams", []):
        codec_type = stream.get("codec_type")
        codec_name = stream.get("codec_name", "unknown")

        if codec_type == "video":
            disposition = stream.get("disposition", {})
            if disposition.get("attached_pic") == 1:
                codecs.append(f"cover-art:{codec_name}")
                continue
            has_video = True
            codecs.append(f"video:{codec_name}")
        elif codec_type == "audio":
            has_audio = True
            codecs.append(f"audio:{codec_name}")
        elif codec_type == "subtitle":
            codecs.append(f"subtitle:{codec_name}")

    return has_video, has_audio, codecs


def find_media_files(folder: Path, recursive: bool, all_files: bool = False) -> list[Path]:
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(
        p for p in iterator
        if p.is_file() and (all_files or p.suffix.lower() in MEDIA_EXTENSIONS)
    )


def convert_file(input_path: Path, output_path: Path, has_video: bool, has_audio: bool) -> bool:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(input_path)]
    if output_path.suffix.lower().lstrip(".") in AUDIO_ONLY_FORMATS and has_video:
        cmd.extend(["-vn"])
    cmd.append(str(output_path))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ffmpeg error: {e.stderr.strip().splitlines()[-1] if e.stderr else 'unknown'}")
        return False


def merge_files(input_files: list[Path], output_file: Path) -> bool:
    """Concatenate files in order using ffmpeg concat demuxer."""
    list_path = output_file.parent / f"_concatlist_{output_file.stem}.txt"
    list_path.write_text(
        "\n".join(f"file '{p.absolute()}'" for p in input_files) + "\n"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c", "copy", str(output_file),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ffmpeg error: {e.stderr.strip().splitlines()[-1] if e.stderr else 'unknown'}")
        return False
    finally:
        list_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze and convert media files in a folder using ffmpeg.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input_folder", type=Path)
    parser.add_argument("output_format", help="Target format/extension (e.g. mp4, mkv, mp3).")
    parser.add_argument("output_path", type=Path)
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Recurse into subfolders of the input folder.")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Only analyze and report; do not convert anything.")
    parser.add_argument("-m", "--merge", action="store_true",
                        help="Merge converted files into one. With -r, produces one file per folder.")
    parser.add_argument("-a", "--all-files", action="store_true",
                        help="Probe every file regardless of extension.")
    return parser.parse_args()


def _probe_and_print(file_path: Path) -> tuple[dict | None, bool, bool]:
    """Probe a file and print its stream info. Returns (probe_data, has_video, has_audio)."""
    probe_data = probe_file(file_path)
    if probe_data is None:
        print("    Skipped: not a recognized media file (ffprobe failed).\n")
        return None, False, False

    has_video, has_audio, codecs = analyze_streams(probe_data)
    duration = probe_data.get("format", {}).get("duration")
    duration_str = f"{float(duration):.1f}s" if duration else "unknown"

    print(f"    Video: {'yes' if has_video else 'no'}  "
          f"Audio: {'yes' if has_audio else 'no'}  "
          f"Streams: {', '.join(codecs) or 'none'}  "
          f"Duration: {duration_str}")

    return probe_data, has_video, has_audio


def main() -> int:
    args = parse_args()
    check_dependencies()

    if not args.input_folder.is_dir():
        sys.exit(f"Error: '{args.input_folder}' does not exist or is not a directory.")

    output_format = args.output_format.lstrip(".").lower()
    args.output_path.mkdir(parents=True, exist_ok=True)

    files = find_media_files(args.input_folder, args.recursive, args.all_files)
    if not files:
        print(f"No media files found in '{args.input_folder}'"
              f"{' (recursive)' if args.recursive else ''}.")
        return 0

    print(f"Found {len(files)} candidate file(s). Analyzing...\n")

    successes = 0
    failures = 0
    skipped = 0

    if not args.merge:
        for idx, file_path in enumerate(files, 1):
            rel = file_path.relative_to(args.input_folder)
            print(f"[{idx}/{len(files)}] {rel}")

            _, has_video, has_audio = _probe_and_print(file_path)
            if _ is None:
                skipped += 1
                continue

            if not has_video and not has_audio:
                print("    Skipped: no playable audio or video streams.\n")
                skipped += 1
                continue

            if output_format in AUDIO_ONLY_FORMATS and not has_audio:
                print(f"    Skipped: target '{output_format}' is audio-only but file has no audio.\n")
                skipped += 1
                continue

            out_file = args.output_path / file_path.relative_to(args.input_folder).with_suffix(f".{output_format}")
            out_file.parent.mkdir(parents=True, exist_ok=True)

            if args.dry_run:
                print(f"    [dry-run] Would convert -> {out_file}\n")
                continue

            print(f"    Converting -> {out_file}")
            if convert_file(file_path, out_file, has_video, has_audio):
                print("    Done.\n")
                successes += 1
            else:
                print("    Failed.\n")
                failures += 1

    else:
        # Merge mode: group files, convert to temp, then concatenate per group.
        if args.recursive:
            groups: dict[Path, list[Path]] = defaultdict(list)
            for f in files:
                groups[f.parent].append(f)
        else:
            groups = {args.input_folder: list(files)}

        tmp_dir = args.output_path / "_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        for folder, group_files in sorted(groups.items()):
            rel_folder = folder.relative_to(args.input_folder)
            group_label = str(rel_folder) if str(rel_folder) != "." else "(root)"
            group_name = "_".join(rel_folder.parts) if rel_folder.parts else "merged"

            print(f"\nFolder: {group_label} — {len(group_files)} file(s)")

            converted_temps: list[Path] = []

            for idx, file_path in enumerate(group_files, 1):
                rel = file_path.relative_to(args.input_folder)
                print(f"  [{idx}/{len(group_files)}] {rel}")

                probe_data, has_video, has_audio = _probe_and_print(file_path)
                if probe_data is None:
                    skipped += 1
                    continue

                if not has_video and not has_audio:
                    print("    Skipped: no playable streams.\n")
                    skipped += 1
                    continue

                if output_format in AUDIO_ONLY_FORMATS and not has_audio:
                    print(f"    Skipped: target '{output_format}' is audio-only but file has no audio.\n")
                    skipped += 1
                    continue

                tmp_file = tmp_dir / f"{group_name}_{idx:04d}_{file_path.stem}.{output_format}"

                if args.dry_run:
                    print(f"    [dry-run] Would convert to temp: {tmp_file.name}")
                    converted_temps.append(tmp_file)
                    continue

                print(f"    Converting...")
                if convert_file(file_path, tmp_file, has_video, has_audio):
                    print("    Done.")
                    converted_temps.append(tmp_file)
                else:
                    print("    Failed.")
                    failures += 1

            if not converted_temps:
                print(f"  Nothing to merge.\n")
                continue

            out_file = args.output_path / f"{group_name}.{output_format}"

            if args.dry_run:
                print(f"\n  [dry-run] Would merge {len(converted_temps)} file(s) -> {out_file}\n")
                successes += len(converted_temps)
                continue

            print(f"\n  Merging {len(converted_temps)} file(s) -> {out_file}")
            if merge_files(converted_temps, out_file):
                print("  Merge complete.\n")
                successes += len(converted_temps)
            else:
                print("  Merge failed.\n")
                failures += len(converted_temps)

            for tmp in converted_temps:
                tmp.unlink(missing_ok=True)

        try:
            tmp_dir.rmdir()
        except OSError:
            pass

    print("=" * 50)
    print(f"Summary: {successes} converted, {failures} failed, {skipped} skipped"
          f"{' (dry-run)' if args.dry_run else ''}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
