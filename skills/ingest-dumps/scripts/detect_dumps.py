#!/usr/bin/env python3
"""Detect dump files (Windows minidump, ELF core, Mach-O core) by inspecting file headers.

Usage:
    python detect_dumps.py <path> [<path> ...]

Accepts files or directories. For directories, searches recursively.
Outputs a JSON array of absolute paths to detected dump files.
"""

import json
import os
import struct
import sys


def is_minidump(path: str) -> bool:
    """Check for Windows minidump: magic bytes 'MDMP' at offset 0."""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            return magic == b"MDMP"
    except (OSError, IOError):
        return False


def is_elf_core(path: str) -> bool:
    """Check for ELF core: ELF magic + e_type == ET_CORE (4).

    ELF header:
      0x00: 7f 45 4c 46  (magic)
      0x04: EI_CLASS (1=32bit, 2=64bit)
      0x10: e_type (uint16) — ET_CORE = 4
    e_type is at offset 16 for both 32-bit and 64-bit ELF.
    Endianness is at EI_DATA (offset 5): 1=little, 2=big.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(20)
            if len(header) < 20:
                return False
            if header[:4] != b"\x7fELF":
                return False
            ei_data = header[5]
            if ei_data == 1:
                e_type = struct.unpack_from("<H", header, 16)[0]
            elif ei_data == 2:
                e_type = struct.unpack_from(">H", header, 16)[0]
            else:
                return False
            return e_type == 4  # ET_CORE
    except (OSError, IOError):
        return False


def is_macho_core(path: str) -> bool:
    """Check for Mach-O core dump.

    Mach-O header:
      0x00: magic (uint32)
        MH_MAGIC    = 0xFEEDFACE (32-bit, native endian)
        MH_CIGAM    = 0xCEFAEDFE (32-bit, swapped endian)
        MH_MAGIC_64 = 0xFEEDFACF (64-bit, native endian)
        MH_CIGAM_64 = 0xCFFAEDFE (64-bit, swapped endian)
      0x0C: filetype (uint32) — MH_CORE = 4

    Fat/universal binaries (0xCAFEBABE / 0xBEBAFECA) are not core dumps.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(16)
            if len(header) < 16:
                return False

            magic = struct.unpack_from("<I", header, 0)[0]

            MH_MAGIC = 0xFEEDFACE
            MH_CIGAM = 0xCEFAEDFE
            MH_MAGIC_64 = 0xFEEDFACF
            MH_CIGAM_64 = 0xCFFAEDFE

            if magic in (MH_MAGIC, MH_MAGIC_64):
                filetype = struct.unpack_from("<I", header, 12)[0]
            elif magic in (MH_CIGAM, MH_CIGAM_64):
                filetype = struct.unpack_from(">I", header, 12)[0]
            else:
                return False

            return filetype == 4  # MH_CORE
    except (OSError, IOError):
        return False


def is_dump_file(path: str) -> bool:
    return is_minidump(path) or is_elf_core(path) or is_macho_core(path)


def find_dumps(path: str) -> list[str]:
    """Find dump files at the given path (file or directory)."""
    results = []
    path = os.path.abspath(path)

    if os.path.isfile(path):
        if is_dump_file(path):
            results.append(path)
    elif os.path.isdir(path):
        for root, _dirs, files in os.walk(path):
            for name in sorted(files):
                fpath = os.path.join(root, name)
                if is_dump_file(fpath):
                    results.append(fpath)
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: detect_dumps.py <path> [<path> ...]", file=sys.stderr)
        sys.exit(1)

    all_dumps = []
    for arg in sys.argv[1:]:
        if not os.path.exists(arg):
            print(f"Warning: path does not exist: {arg}", file=sys.stderr)
            continue
        all_dumps.extend(find_dumps(arg))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in all_dumps:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    print(json.dumps(unique, indent=2))


if __name__ == "__main__":
    main()
