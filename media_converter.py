#!/usr/bin/env python3
"""
Media file analyzer and converter.

Scans a folder for media files, reports whether each has audio/video streams,
then converts them to the requested output format using ffmpeg.

Special handling for proprietary `.media` files (WiFi camera/speaker format):
they are first extracted to an intermediate MKV using media_extractor, then
converted as normal.

Usage:
    python media_converter.py <input_folder> <output_format> <output_path> [-r] [-n] [-m] [-a]

Examples:
    python media_converter.py ./videos mp4 ./converted
    python media_converter.py ./media mp3 ./audio_only -r
    python media_converter.py ./clips mkv ./out -n
    python media_converter.py ./clips mp4 ./out -m
    python media_converter.py ./clips mp4 ./out -m -r
"""

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404 — required to invoke ffmpeg/ffprobe; shell=False used throughout
import sys
import tempfile
import types
from collections import defaultdict
from pathlib import Path

import media_extractor

# ---------------------------------------------------------------------------
# Localisation
# ---------------------------------------------------------------------------

def _detect_lang() -> str:
    """Return the 2-letter BCP-47 language code for the OS UI language."""
    if sys.platform == "win32":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(85)
            ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
            return buf.value.split("-")[0].lower()
        except Exception:
            pass
    elif sys.platform == "darwin":
        # macOS: query System Preferences language list (reliable for GUI locale)
        try:
            import re as _re
            out = subprocess.check_output(
                ["defaults", "read", "-g", "AppleLanguages"],
                stderr=subprocess.DEVNULL, text=True, timeout=2,
            )  # nosec B603
            m = _re.search(r'"([a-z]{2})[-_"]', out.lower())
            if m:
                return m.group(1)
        except Exception:
            pass
    # Linux + macOS fallback: POSIX / GNU locale env vars
    for _v in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(_v, "")
        if val:
            code = val.lower().split("_")[0].split(".")[0].split("@")[0]
            if code in ("c", "posix"):
                return "en"
            if code:
                return code
    # GNU LANGUAGE extension — colon-separated preference list
    for part in os.environ.get("LANGUAGE", "").split(":"):
        code = part.lower().split("_")[0].split(".")[0]
        if code:
            return "en" if code in ("c", "posix") else code
    return "en"


_T_EN = types.SimpleNamespace(
    # GUI
    window_title    = "Media Converter",
    input_folder    = "Input Folder:",
    input_hint      = "Select Input Folder",
    output_folder   = "Output Folder:",
    output_hint     = "Select Output Folder",
    browse          = "Browse",
    output_format   = "Output Format",
    custom_label    = "Custom:",
    custom_hint     = "e.g. vob, m4v …",
    note_media      = ("Note: proprietary .media files (WiFi camera/speaker format) "
                       "are auto-detected and extracted (HEVC video + 8 kHz PCM audio)."),
    chk_recursive   = "Recursive  -r",
    chk_merge       = "Merge  -m",
    chk_dry_run     = "Dry Run  -n",
    chk_all_files   = "All Files  -a",
    run_btn         = "Run Conversion",
    running_btn     = "Running…",
    starting        = "Starting conversion...\n",
    status_done     = "Completed",
    status_failed   = "Failed (exit {code})",
    err_required    = "Error: input folder, output format, and output folder are all required.",
    err_fmt_invalid = "Error: invalid output format '{fmt}'. Use alphanumeric only.",
    # CLI / log
    err_dep         = "Error: '{tool}' was not found on PATH. Please install ffmpeg (https://ffmpeg.org/download.html) and try again.",
    err_not_dir     = "Error: '{folder}' does not exist or is not a directory.",
    err_invalid_fmt = "Error: invalid output format '{fmt}'. Use alphanumeric only (e.g. mp4, mkv, mp3).",
    no_media_found  = "No media files found in '{folder}'{suffix}.",
    no_media_rec    = " (recursive)",
    found_files     = "Found {n} candidate file(s). Analyzing...\n",
    skip_not_media  = "    Skipped: not a recognized media file (ffprobe failed).\n",
    extract_media   = "    Extracting .media -> {name}",
    extract_failed  = "    Failed to extract .media file.",
    probe_line      = "    {prefix}Video: {video}  Audio: {audio}  Streams: {streams}  Duration: {dur}",
    yes             = "yes",
    no              = "no",
    unknown         = "unknown",
    streams_none    = "none",
    ffmpeg_err      = "    ffmpeg error: {msg}",
    skip_no_stream  = "    Skipped: no playable streams.\n",
    skip_audio_only = "    Skipped: target '{fmt}' is audio-only but file has no audio.\n",
    dry_run_convert = "    [dry-run] Would convert -> {out}\n",
    converting      = "    Converting -> {out}",
    conv_done       = "    Done.\n",
    conv_failed     = "    Failed.\n",
    folder_header   = "\nFolder: {label} — {n} file(s)",
    dry_run_conv_tmp= "    [dry-run] Would convert to temp: {name}",
    converting_short= "    Converting...",
    done_short      = "    Done.",
    failed_short    = "    Failed.",
    nothing_merge   = "  Nothing to merge.\n",
    dry_run_merge   = "\n  [dry-run] Would merge {n} file(s) -> {out}\n",
    merging         = "\n  Merging {n} file(s) -> {out}",
    merge_complete  = "  Merge complete.\n",
    merge_failed    = "  Merge failed.\n",
    summary         = "Summary: {successes} converted, {failures} failed, {skipped} skipped{suffix}",
    dry_run_suffix  = " (dry-run)",
)

_T_ES = types.SimpleNamespace(
    # GUI
    window_title    = "Conversor de Medios",
    input_folder    = "Carpeta de entrada:",
    input_hint      = "Seleccionar carpeta de entrada",
    output_folder   = "Carpeta de salida:",
    output_hint     = "Seleccionar carpeta de salida",
    browse          = "Examinar",
    output_format   = "Formato de salida",
    custom_label    = "Personalizado:",
    custom_hint     = "ej. vob, m4v …",
    note_media      = ("Nota: Los archivos .media (formato de cámara/bocina WiFi) "
                       "se detectan automáticamente y se extraen (HEVC + PCM 8 kHz)."),
    chk_recursive   = "Recursivo  -r",
    chk_merge       = "Combinar  -m",
    chk_dry_run     = "Modo prueba  -n",
    chk_all_files   = "Todos los archivos  -a",
    run_btn         = "Iniciar conversión",
    running_btn     = "Ejecutando…",
    starting        = "Iniciando conversión...\n",
    status_done     = "Completado",
    status_failed   = "Error (salida {code})",
    err_required    = "Error: la carpeta de entrada, el formato y la carpeta de salida son obligatorios.",
    err_fmt_invalid = "Error: formato inválido '{fmt}'. Use solo caracteres alfanuméricos.",
    # CLI / log
    err_dep         = "Error: '{tool}' no encontrado en PATH. Instale ffmpeg (https://ffmpeg.org/download.html) e intente de nuevo.",
    err_not_dir     = "Error: '{folder}' no existe o no es un directorio.",
    err_invalid_fmt = "Error: formato de salida inválido '{fmt}'. Use solo caracteres alfanuméricos (ej. mp4, mkv, mp3).",
    no_media_found  = "No se encontraron archivos multimedia en '{folder}'{suffix}.",
    no_media_rec    = " (recursivo)",
    found_files     = "Se encontraron {n} archivo(s) candidato(s). Analizando...\n",
    skip_not_media  = "    Omitido: archivo multimedia no reconocido (ffprobe falló).\n",
    extract_media   = "    Extrayendo .media -> {name}",
    extract_failed  = "    Error al extraer el archivo .media.",
    probe_line      = "    {prefix}Vídeo: {video}  Audio: {audio}  Pistas: {streams}  Duración: {dur}",
    yes             = "sí",
    no              = "no",
    unknown         = "desconocido",
    streams_none    = "ninguna",
    ffmpeg_err      = "    error ffmpeg: {msg}",
    skip_no_stream  = "    Omitido: sin pistas reproducibles.\n",
    skip_audio_only = "    Omitido: el formato '{fmt}' es solo audio pero el archivo no tiene audio.\n",
    dry_run_convert = "    [prueba] Se convertiría -> {out}\n",
    converting      = "    Convirtiendo -> {out}",
    conv_done       = "    Listo.\n",
    conv_failed     = "    Error.\n",
    folder_header   = "\nCarpeta: {label} — {n} archivo(s)",
    dry_run_conv_tmp= "    [prueba] Se convertiría a temporal: {name}",
    converting_short= "    Convirtiendo...",
    done_short      = "    Listo.",
    failed_short    = "    Error.",
    nothing_merge   = "  Nada para combinar.\n",
    dry_run_merge   = "\n  [prueba] Se combinarían {n} archivo(s) -> {out}\n",
    merging         = "\n  Combinando {n} archivo(s) -> {out}",
    merge_complete  = "  Combinación completada.\n",
    merge_failed    = "  Error al combinar.\n",
    summary         = "Resumen: {successes} convertido(s), {failures} fallido(s), {skipped} omitido(s){suffix}",
    dry_run_suffix  = " (prueba)",
)

# Active locale — imported by media-converter-gui.py
T = _T_EN

def _init_locale() -> None:
    global T
    if _detect_lang() == "es":
        T = _T_ES

_init_locale()

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

# Directory used for intermediate files when extracting .media files.
# Created on demand and cleaned up at end of run.
_EXTRACTION_TMP_DIR: Path | None = None


def check_dependencies() -> bool:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(T.err_dep.format(tool=tool))
            return False
    return True


def _get_extraction_tmp_dir() -> Path:
    global _EXTRACTION_TMP_DIR
    if _EXTRACTION_TMP_DIR is None:
        _EXTRACTION_TMP_DIR = Path(tempfile.mkdtemp(prefix="media_extract_"))
    return _EXTRACTION_TMP_DIR


def cleanup_extraction_tmp() -> None:
    global _EXTRACTION_TMP_DIR
    if _EXTRACTION_TMP_DIR is not None and _EXTRACTION_TMP_DIR.exists():
        shutil.rmtree(_EXTRACTION_TMP_DIR, ignore_errors=True)
        _EXTRACTION_TMP_DIR = None


def extract_media_to_intermediate(media_path: Path) -> Path | None:
    """
    Convert a proprietary .media file to an intermediate MKV in the temp dir.
    Returns the intermediate file path on success, or None on failure.
    """
    tmp_dir = _get_extraction_tmp_dir()
    # Use a hash-ish unique name so collisions across folders don't clobber each other
    unique = f"{media_path.stem}_{abs(hash(str(media_path.absolute())))}.mkv"
    intermediate = tmp_dir / unique

    if intermediate.exists():
        return intermediate

    print(T.extract_media.format(name=intermediate.name))
    if media_extractor.convert_media_to_mkv(media_path, intermediate):
        return intermediate
    return None


def probe_file(path: Path) -> dict | None:
    """
    Probe a file with ffprobe and return parsed JSON.
    For .media files, returns synthetic probe data based on extraction.
    """
    if path.suffix.lower() == ".media" and media_extractor.is_media_file(path):
        return media_extractor.get_stream_info(path)

    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # nosec B603
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
    """
    Convert a media file to output_path. For .media files, first extract to
    an intermediate MKV, then convert from there.
    """
    actual_input = input_path
    if input_path.suffix.lower() == ".media" and media_extractor.is_media_file(input_path):
        intermediate = extract_media_to_intermediate(input_path)
        if intermediate is None:
            print(T.extract_failed)
            return False
        actual_input = intermediate

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(actual_input)]
    if output_path.suffix.lower().lstrip(".") in AUDIO_ONLY_FORMATS and has_video:
        cmd.extend(["-vn"])
    cmd.append(str(output_path))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603
        return True
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip().splitlines()[-1] if e.stderr else T.unknown
        print(T.ffmpeg_err.format(msg=msg))
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
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603
        return True
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip().splitlines()[-1] if e.stderr else T.unknown
        print(T.ffmpeg_err.format(msg=msg))
        return False
    finally:
        list_path.unlink(missing_ok=True)


def parse_args(argv=None) -> argparse.Namespace:
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
    return parser.parse_args(argv)


def _probe_and_print(file_path: Path) -> tuple[dict | None, bool, bool]:
    probe_data = probe_file(file_path)
    if probe_data is None:
        print(T.skip_not_media)
        return None, False, False

    has_video, has_audio, codecs = analyze_streams(probe_data)
    duration = probe_data.get("format", {}).get("duration")
    duration_str = f"{float(duration):.1f}s" if duration else T.unknown

    is_proprietary = file_path.suffix.lower() == ".media"
    prefix = "[.media] " if is_proprietary else ""

    print(T.probe_line.format(
        prefix=prefix,
        video=T.yes if has_video else T.no,
        audio=T.yes if has_audio else T.no,
        streams=", ".join(codecs) or T.streams_none,
        dur=duration_str,
    ))

    return probe_data, has_video, has_audio


def main(argv=None) -> int:
    args = parse_args(argv)

    if not check_dependencies():
        return 1

    if not args.input_folder.is_dir():
        print(T.err_not_dir.format(folder=args.input_folder))
        return 1

    output_format = args.output_format.lstrip(".").lower()
    if not re.fullmatch(r"[a-z0-9]+", output_format):
        print(T.err_invalid_fmt.format(fmt=output_format))
        return 1

    args.output_path.mkdir(parents=True, exist_ok=True)

    files = find_media_files(args.input_folder, args.recursive, args.all_files)
    if not files:
        suffix = T.no_media_rec if args.recursive else ""
        print(T.no_media_found.format(folder=args.input_folder, suffix=suffix))
        return 0

    print(T.found_files.format(n=len(files)))

    successes = 0
    failures = 0
    skipped = 0

    try:
        if not args.merge:
            for idx, file_path in enumerate(files, 1):
                rel = file_path.relative_to(args.input_folder)
                print(f"[{idx}/{len(files)}] {rel}")

                probe_data, has_video, has_audio = _probe_and_print(file_path)
                if probe_data is None:
                    skipped += 1
                    continue

                if not has_video and not has_audio:
                    print(T.skip_no_stream)
                    skipped += 1
                    continue

                if output_format in AUDIO_ONLY_FORMATS and not has_audio:
                    print(T.skip_audio_only.format(fmt=output_format))
                    skipped += 1
                    continue

                out_file = args.output_path / file_path.relative_to(args.input_folder).with_suffix(f".{output_format}")
                out_file.parent.mkdir(parents=True, exist_ok=True)

                if args.dry_run:
                    print(T.dry_run_convert.format(out=out_file))
                    continue

                print(T.converting.format(out=out_file))
                if convert_file(file_path, out_file, has_video, has_audio):
                    print(T.conv_done)
                    successes += 1
                else:
                    print(T.conv_failed)
                    failures += 1

        else:
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

                print(T.folder_header.format(label=group_label, n=len(group_files)))

                converted_temps: list[Path] = []

                for idx, file_path in enumerate(group_files, 1):
                    rel = file_path.relative_to(args.input_folder)
                    print(f"  [{idx}/{len(group_files)}] {rel}")

                    probe_data, has_video, has_audio = _probe_and_print(file_path)
                    if probe_data is None:
                        skipped += 1
                        continue

                    if not has_video and not has_audio:
                        print(T.skip_no_stream)
                        skipped += 1
                        continue

                    if output_format in AUDIO_ONLY_FORMATS and not has_audio:
                        print(T.skip_audio_only.format(fmt=output_format))
                        skipped += 1
                        continue

                    tmp_file = tmp_dir / f"{group_name}_{idx:04d}_{file_path.stem}.{output_format}"

                    if args.dry_run:
                        print(T.dry_run_conv_tmp.format(name=tmp_file.name))
                        converted_temps.append(tmp_file)
                        continue

                    print(T.converting_short)
                    if convert_file(file_path, tmp_file, has_video, has_audio):
                        print(T.done_short)
                        converted_temps.append(tmp_file)
                    else:
                        print(T.failed_short)
                        failures += 1

                if not converted_temps:
                    print(T.nothing_merge)
                    continue

                out_file = args.output_path / f"{group_name}.{output_format}"

                if args.dry_run:
                    print(T.dry_run_merge.format(n=len(converted_temps), out=out_file))
                    successes += len(converted_temps)
                    continue

                print(T.merging.format(n=len(converted_temps), out=out_file))
                if merge_files(converted_temps, out_file):
                    print(T.merge_complete)
                    successes += len(converted_temps)
                else:
                    print(T.merge_failed)
                    failures += len(converted_temps)

                for tmp in converted_temps:
                    tmp.unlink(missing_ok=True)

            try:
                tmp_dir.rmdir()
            except OSError:
                pass

    finally:
        cleanup_extraction_tmp()

    print("=" * 50)
    suffix = T.dry_run_suffix if args.dry_run else ""
    print(T.summary.format(successes=successes, failures=failures, skipped=skipped, suffix=suffix))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
