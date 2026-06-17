#!/usr/bin/env python3
import math
import sys
from collections import Counter
from pathlib import Path


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def summarize(path: Path, data: bytes) -> None:
    print(f"[+] {path}")
    print(f"  size={len(data)} entropy={shannon_entropy(data):.3f} null_bytes={data.count(0)}")
    print(f"  first64={data[:64].hex()}")
    if b"\x00" in data:
        print("  hint=contains null bytes; do not assume UTF-8/JSON")


def diff_offsets(left: bytes, right: bytes) -> list[int]:
    limit = min(len(left), len(right))
    return [i for i in range(limit) if left[i] != right[i]]


def offset_patterns(offsets: list[int]) -> None:
    if not offsets:
        print("  identical_prefix=yes")
        return
    print(f"  differing_offsets={offsets[:64]}")
    if all(offset % 2 == 0 for offset in offsets):
        print("  hint=all changes land on even offsets; suspect fixed-width fields or struct alignment")
    strides = [b - a for a, b in zip(offsets, offsets[1:])]
    if strides and len(set(strides[:16])) == 1:
        print(f"  hint=constant stride {strides[0]} between changes; suspect repeated fixed-size records")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: binary_sample_triage.py sample1 [sample2 ...]", file=sys.stderr)
        return 2
    blobs = []
    for name in argv[1:]:
        path = Path(name)
        data = path.read_bytes()
        summarize(path, data)
        blobs.append((path, data))
    if len(blobs) >= 2:
        first_path, first = blobs[0]
        for other_path, other in blobs[1:]:
            print(f"[+] diff {first_path} vs {other_path}")
            offsets = diff_offsets(first, other)
            offset_patterns(offsets)
            print(f"  length_delta={len(other) - len(first)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
