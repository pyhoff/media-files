#!/usr/bin/env python3
"""
Diagnose clicking in extracted audio.

Looks at:
1. Are audio block sizes consistent? (irregular sizes might mean missing data)
2. Are there big sample-value jumps at block boundaries? (causes clicks)
3. Is there a header byte at the start of each audio block we should skip?
"""
import struct, sys
from pathlib import Path

MARKER_1 = b'\x9d\x01\x00\x00'
MARKER_2 = b'\x91\x78\x23\xe1'

if len(sys.argv) != 2:
    print("Usage: diagnose_clicks.py <file.media>")
    sys.exit(1)

data = Path(sys.argv[1]).read_bytes()

# Find all blocks
positions = []
start = 0
while True:
    pos = data.find(MARKER_1, start)
    if pos == -1:
        break
    if data[pos+8:pos+12] == MARKER_2:
        positions.append(pos)
    start = pos + 1

audio_blocks = []
for i, pos in enumerate(positions):
    payload_start = pos + 12
    payload_end = positions[i+1] - 4 if i+1 < len(positions) else len(data)
    payload = data[payload_start:payload_end]
    if payload[:4] != b'\x00\x00\x00\x01':  # not video
        audio_blocks.append((pos, payload))

print(f"Found {len(audio_blocks)} audio blocks\n")

# Audio block size distribution
sizes = [len(p) for _, p in audio_blocks]
print(f"Audio block sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)//len(sizes)}")
print(f"Unique sizes: {len(set(sizes))}")

# Show first 16 bytes of first 5 audio blocks - look for a common header pattern
print("\nFirst 16 bytes of first 8 audio blocks:")
for i, (pos, payload) in enumerate(audio_blocks[:8]):
    hex_part = ' '.join(f'{b:02x}' for b in payload[:16])
    print(f"  block {i} (size={len(payload)}): {hex_part}")

# Look at sample values at block boundaries
# If audio is 16-bit LE PCM, parse as int16
print("\n--- Boundary analysis (last 4 samples of block N vs first 4 of block N+1) ---")
for i in range(min(5, len(audio_blocks)-1)):
    cur = audio_blocks[i][1]
    nxt = audio_blocks[i+1][1]
    
    # Last 4 samples of current
    last_samples = struct.unpack(f'<{4}h', cur[-8:]) if len(cur) >= 8 else ()
    # First 4 samples of next
    first_samples = struct.unpack(f'<{4}h', nxt[:8]) if len(nxt) >= 8 else ()
    
    if last_samples and first_samples:
        jump = abs(first_samples[0] - last_samples[-1])
        flag = " <-- BIG JUMP" if jump > 5000 else ""
        print(f"  block {i} end: {last_samples} | block {i+1} start: {first_samples} | jump={jump}{flag}")

# Check if every audio block has same number of samples (suggests fixed framing)
from collections import Counter
size_counter = Counter(sizes)
print(f"\nMost common block sizes (top 10):")
for size, count in size_counter.most_common(10):
    samples = size // 2
    print(f"  {size} bytes ({samples} samples = {samples/8000*1000:.1f}ms @ 8kHz): {count} blocks")
