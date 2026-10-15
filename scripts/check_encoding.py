"""Encoding verification script for all tracked text files in the repository.

Checks:
1. No UTF-8 BOM (Byte Order Mark) at the beginning of files.
2. File decodes cleanly as UTF-8 without decoding errors or replacement characters (U+FFFD).
3. No corrupted UTF-8 mojibake patterns:
   - 'â€' (e.g. â€”, â€“, â€œ, â€ )
   - 'Ã'  (Latin-1 mojibake)
   - 'à¦' (Bangla 0xE0 0xA6 double-decoded)
   - 'à§' (Bangla 0xE0 0xA7 double-decoded)
   - 'Â'  (e.g. Â§, Â°)
   - U+FFFD (replacement character)

Exits 1 on any hit; 0 if clean.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Known binary extensions to skip
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp',
    '.woff', '.woff2', '.ttf', '.eot',
    '.db', '.sqlite', '.sqlite3', '.pyc', '.pyd',
    '.zip', '.tar', '.gz', '.bz2', '.7z',
    '.mp3', '.wav', '.ogg', '.flac',
    '.pdf',
}

MOJIBAKE_PATTERNS = [
    'â€',
    'Ã',
    'à¦',
    'à§',
    'Â',
    '\ufffd',
]


def is_binary(file_path: Path) -> bool:
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return True
    except OSError:
        return True
    return False


def get_tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ['git', 'ls-files'],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            p = root / line
            if p.is_file():
                files.append(p)
    return files


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    tracked_files = get_tracked_files(root)
    errors = 0

    for file_path in tracked_files:
        if is_binary(file_path):
            continue

        rel_path = file_path.relative_to(root)
        try:
            raw = file_path.read_bytes()
        except OSError as e:
            print(f"ERROR reading {rel_path}: {e}", file=sys.stderr)
            errors += 1
            continue

        # Check BOM
        if raw.startswith(b'\xef\xbb\xbf'):
            print(f"BOM found: {rel_path}", file=sys.stderr)
            errors += 1

        # Check UTF-8 decoding
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as e:
            print(f"UTF-8 decode error in {rel_path}: {e}", file=sys.stderr)
            errors += 1
            continue

        # Check line by line for mojibake patterns
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pat in MOJIBAKE_PATTERNS:
                if pat in line:
                    escaped_pat = pat.encode('unicode_escape').decode('ascii')
                    print(
                        f"Mojibake [{escaped_pat}] at {rel_path}:{lineno} -> {line.strip()}",
                        file=sys.stderr,
                    )
                    errors += 1

    if errors > 0:
        print(f"\nFAILED: {errors} encoding violation(s) found.", file=sys.stderr)
        return 1

    print(f"SUCCESS: Checked {len(tracked_files)} files. All clean UTF-8 without BOM or mojibake.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
