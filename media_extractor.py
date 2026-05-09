#!/usr/bin/env python3
"""
Extractor for proprietary .media files used by some WiFi camera/speaker devices.

File structure (reverse-engineered):
    [8-byte file header]
    [block 1] [block 2] ... [block N]

Each block is:
    [4 bytes: chunk size, LE uint32]
    [4 bytes: timestamp/sequence]
    [4 bytes: 9d 01 00 00  - block start marker]
    [4 bytes: secondary timestamp]
    [4 bytes: 91 78 23 e1  - block start marker 2]
    [N bytes: payload]

Payload type is determined by the first 4 bytes of the payload:
    - 00 00 00 01  ->  H.265 (HEVC) NAL unit (video)
    - anything else ->  raw 16-bit little-endian PCM audio @ 8kHz mono
"""

import struct
import subprocess  # nosec B404 - used to call ffmpeg with shell=False
import wave
from pathlib import Path

MARKER_1 = b"\x9d\x01\x00\x00"
MARKER_2 = b"\x91\x78\x23\xe1"

AUDIO_SAMPLE_RATE = 8000   # 8 kHz
AUDIO_SAMPLE_WIDTH = 2     # 16-bit
AUDIO_CHANNELS = 1         # mono


def is_media_file(path: Path) -> bool:
    """Check whether path looks like our proprietary .media format."""
    if path.suffix.lower() != ".media":
        return False
    try:
        with path.open("rb") as f:
            head = f.read(32)
        # Header signature: bytes 8..12 should be 9d 01 00 00 right after
        # the first 4-byte size + 4-byte timestamp. Empirically the marker
        # appears at offset 12 in the first block.
        return MARKER_1 in head and MARKER_2 in head
    except OSError:
        return False


def parse_blocks(data: bytes) -> list[tuple[int, int, bytes]]:
    """
    Walk the file, returning a list of (offset, chunk_size, payload) tuples.

    Uses the dual marker (9d 01 00 00 ... 91 78 23 e1) to find block boundaries
    reliably even if individual chunk sizes drift.
    """
    positions: list[int] = []
    start = 0
    while True:
        pos = data.find(MARKER_1, start)
        if pos == -1:
            break
        # Verify the second marker is exactly 4 bytes after the end of the first
        if data[pos + 8 : pos + 12] == MARKER_2:
            positions.append(pos)
        start = pos + 1

    blocks: list[tuple[int, int, bytes]] = []
    for i, pos in enumerate(positions):
        payload_start = pos + 12  # past both markers
        payload_end = positions[i + 1] - 4 if i + 1 < len(positions) else len(data)
        if pos < 4:
            chunk_size = 0
        else:
            chunk_size = struct.unpack_from("<I", data, pos - 4)[0]
        blocks.append((pos, chunk_size, data[payload_start:payload_end]))
    return blocks


# Each audio block ends with an 8-byte trailer (looks like a checksum or
# sequence counter, e.g. `00 00 XX XX XX XX 00 00`). Including these bytes
# in the PCM stream produces a periodic click roughly every 80ms (12.5 Hz).
# Strip them off the end of every audio block.
AUDIO_BLOCK_TRAILER_BYTES = 8


def extract_streams(media_path: Path) -> tuple[bytes, bytes]:
    """
    Extract raw HEVC video and raw PCM audio from a .media file.
    Returns (hevc_bytes, pcm_bytes).
    """
    with media_path.open("rb") as f:
        data = f.read()

    video = bytearray()
    audio = bytearray()

    for _, _, payload in parse_blocks(data):
        if not payload:
            continue
        if payload[:4] == b"\x00\x00\x00\x01":
            video += payload
        else:
            # Drop the per-block trailer that otherwise causes clicks.
            # Keep the block whole if it's smaller than the trailer for safety.
            if len(payload) > AUDIO_BLOCK_TRAILER_BYTES:
                audio += payload[:-AUDIO_BLOCK_TRAILER_BYTES]
            else:
                audio += payload

    return bytes(video), bytes(audio)


def convert_media_to_mkv(
    media_path: Path,
    output_path: Path,
    *,
    overwrite: bool = True,
) -> bool:
    """
    Convert a single .media file to an MKV with H.265 video + AAC audio.

    Returns True on success.
    """
    video_bytes, audio_bytes = extract_streams(media_path)

    if not video_bytes and not audio_bytes:
        return False

    tmp_dir = output_path.parent
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_video = tmp_dir / f"._{output_path.stem}_video.hevc"
    tmp_audio = tmp_dir / f"._{output_path.stem}_audio.wav"

    try:
        if video_bytes:
            tmp_video.write_bytes(video_bytes)

        if audio_bytes:
            with wave.open(str(tmp_audio), "wb") as w:
                w.setnchannels(AUDIO_CHANNELS)
                w.setsampwidth(AUDIO_SAMPLE_WIDTH)
                w.setframerate(AUDIO_SAMPLE_RATE)
                w.writeframes(audio_bytes)

        cmd = ["ffmpeg", "-loglevel", "error"]
        if overwrite:
            cmd.append("-y")

        if video_bytes:
            cmd += ["-i", str(tmp_video)]
        if audio_bytes:
            cmd += ["-i", str(tmp_audio)]

        # Build mappings + codec args based on what we actually have
        if video_bytes and audio_bytes:
            cmd += [
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac",
            ]
        elif video_bytes:
            cmd += ["-map", "0:v", "-c:v", "copy"]
        else:
            cmd += ["-map", "0:a", "-c:a", "aac"]

        cmd.append(str(output_path))

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603
            return True
        except subprocess.CalledProcessError as e:
            tail = e.stderr.strip().splitlines()[-1] if e.stderr else "unknown"
            print(f"    ffmpeg error: {tail}")
            return False

    finally:
        tmp_video.unlink(missing_ok=True)
        tmp_audio.unlink(missing_ok=True)


def get_stream_info(media_path: Path) -> dict:
    """
    Return a dict shaped like ffprobe output so existing analysis code works.
    """
    video_bytes, audio_bytes = extract_streams(media_path)

    streams = []
    if video_bytes:
        streams.append({
            "codec_type": "video",
            "codec_name": "hevc",
            "disposition": {},
        })
    if audio_bytes:
        streams.append({
            "codec_type": "audio",
            "codec_name": "pcm_s16le",
            "disposition": {},
        })

    # Best-effort duration estimate from audio (most reliable)
    duration = None
    if audio_bytes:
        duration = len(audio_bytes) / (AUDIO_SAMPLE_RATE * AUDIO_SAMPLE_WIDTH * AUDIO_CHANNELS)

    return {
        "streams": streams,
        "format": {"duration": str(duration) if duration is not None else ""},
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: media_extractor.py <input.media> <output.mkv>")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    if not is_media_file(src):
        print(f"Not a recognized .media file: {src}")
        sys.exit(1)
    ok = convert_media_to_mkv(src, dst)
    sys.exit(0 if ok else 1)
