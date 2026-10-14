"""Confirm required environment variables are set. Exits non-zero if any is empty."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REQUIRED = ["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"]
ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overriding existing values."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #")[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def main() -> int:
    """Return 0 when every required key is non-empty, else 1."""
    load_dotenv(ROOT / ".env")
    missing = [k for k in REQUIRED if not os.environ.get(k, "").strip()]
    for key in REQUIRED:
        print(f"{key}: {'MISSING' if key in missing else 'ok'}")
    if missing:
        print(f"ERROR: empty required keys: {', '.join(missing)}", file=sys.stderr)
        return 1
    print("Environment OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
