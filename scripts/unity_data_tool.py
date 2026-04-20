#!/usr/bin/env python3
"""Helpers for inspecting and patching Build/rs.data.unityweb.

This build currently stores gameplay tuning in an uncompressed UnityWebData1.0
container at Build/rs.data.unityweb. The timer value lives in the embedded
UnityFS payload and is easiest to patch with UnityPy.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_PATH = Path("Build/rs.data.unityweb")
DEFAULT_GAMELEVEL_PATH_ID = 4627
DEFAULT_GAMELEVEL_FLOAT_OFFSET = 32


def require_unitypy():
    try:
        import UnityPy  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise SystemExit(
            "UnityPy is required for this command.\n"
            "Install it with:\n"
            "  python3 -m pip install UnityPy\n"
            "or, for an isolated target dir:\n"
            "  python3 -m pip install --target /tmp/unitypy UnityPy\n"
            "  PYTHONPATH=/tmp/unitypy python3 scripts/unity_data_tool.py ..."
        ) from exc
    return UnityPy


@dataclass
class ContainerEntry:
    offset: int
    size: int
    name_len: int
    name_bytes: bytes
    name: str


def parse_container(data: bytes) -> tuple[int, list[ContainerEntry]]:
    magic = b"UnityWebData1.0\x00"
    if not data.startswith(magic):
        raise ValueError("Build/rs.data.unityweb is not an uncompressed UnityWebData1.0 container")

    header_size = struct.unpack_from("<I", data, len(magic))[0]
    entries: list[ContainerEntry] = []
    pos = len(magic) + 4
    while pos < header_size:
        offset, size, name_len = struct.unpack_from("<III", data, pos)
        pos += 12
        name_bytes = data[pos : pos + name_len]
        pos += name_len
        entries.append(
            ContainerEntry(
                offset=offset,
                size=size,
                name_len=name_len,
                name_bytes=name_bytes,
                name=name_bytes.rstrip(b"\x00").decode("utf-8"),
            )
        )
    return header_size, entries


def rebuild_container(
    original_data: bytes,
    header_size: int,
    entries: list[ContainerEntry],
    new_first_payload: bytes,
) -> bytes:
    old_first_size = entries[0].size
    delta = len(new_first_payload) - old_first_size

    updated_entries: list[ContainerEntry] = []
    for index, entry in enumerate(entries):
        if index == 0:
            updated_entries.append(
                ContainerEntry(
                    offset=entry.offset,
                    size=len(new_first_payload),
                    name_len=entry.name_len,
                    name_bytes=entry.name_bytes,
                    name=entry.name,
                )
            )
            continue
        updated_entries.append(
            ContainerEntry(
                offset=entry.offset + delta,
                size=entry.size,
                name_len=entry.name_len,
                name_bytes=entry.name_bytes,
                name=entry.name,
            )
        )

    out = bytearray()
    out += original_data[:16]
    out += struct.pack("<I", header_size)
    for entry in updated_entries:
        out += struct.pack("<III", entry.offset, entry.size, entry.name_len)
        out += entry.name_bytes
    if len(out) != header_size:
        raise ValueError(f"header rebuild mismatch: expected {header_size}, got {len(out)}")

    out += new_first_payload
    out += original_data[header_size + old_first_size :]
    return bytes(out)


def load_env(data_path: Path):
    UnityPy = require_unitypy()
    raw = data_path.read_bytes()
    header_size, entries = parse_container(raw)
    first_entry = entries[0]
    payload = raw[first_entry.offset : first_entry.offset + first_entry.size]
    env = UnityPy.load(payload)
    return raw, header_size, entries, payload, env


def get_game_length(data_path: Path, path_id: int, float_offset: int) -> float:
    _, _, _, _, env = load_env(data_path)
    obj = next(o for o in env.objects if o.path_id == path_id)
    return struct.unpack_from("<f", obj.get_raw_data(), float_offset)[0]


def set_game_length(data_path: Path, seconds: float, path_id: int, float_offset: int) -> tuple[float, float]:
    raw, header_size, entries, _, env = load_env(data_path)
    obj = next(o for o in env.objects if o.path_id == path_id)
    obj_raw = bytearray(obj.get_raw_data())
    before = struct.unpack_from("<f", obj_raw, float_offset)[0]
    struct.pack_into("<f", obj_raw, float_offset, seconds)
    obj.set_raw_data(bytes(obj_raw))

    new_payload = env.file.save("original")
    rebuilt = rebuild_container(raw, header_size, entries, new_payload)
    data_path.write_bytes(rebuilt)

    after = get_game_length(data_path, path_id, float_offset)
    return before, after


def cmd_manifest(args: argparse.Namespace) -> int:
    raw = args.data.read_bytes()
    header_size, entries = parse_container(raw)
    print(f"header_size={header_size}")
    for entry in entries:
        print(f"{entry.offset:>9} {entry.size:>9} {entry.name}")
    return 0


def cmd_get_timer(args: argparse.Namespace) -> int:
    value = get_game_length(args.data, args.path_id, args.float_offset)
    print(value)
    return 0


def cmd_set_timer(args: argparse.Namespace) -> int:
    before, after = set_game_length(args.data, args.seconds, args.path_id, args.float_offset)
    print(f"timer: {before} -> {after}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Path to rs.data.unityweb")

    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest", help="Print UnityWebData1.0 entries")
    manifest.set_defaults(func=cmd_manifest)

    get_timer = subparsers.add_parser("get-timer", help="Read the current game timer")
    get_timer.add_argument("--path-id", type=int, default=DEFAULT_GAMELEVEL_PATH_ID)
    get_timer.add_argument("--float-offset", type=int, default=DEFAULT_GAMELEVEL_FLOAT_OFFSET)
    get_timer.set_defaults(func=cmd_get_timer)

    set_timer = subparsers.add_parser("set-timer", help="Patch the current game timer")
    set_timer.add_argument("seconds", type=float, help="New round length in seconds")
    set_timer.add_argument("--path-id", type=int, default=DEFAULT_GAMELEVEL_PATH_ID)
    set_timer.add_argument("--float-offset", type=int, default=DEFAULT_GAMELEVEL_FLOAT_OFFSET)
    set_timer.set_defaults(func=cmd_set_timer)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
