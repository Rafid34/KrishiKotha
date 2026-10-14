"""Check that Sylhet mid-June rain30_mean exceeds Rajshahi mid-June rain30_mean."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.risk.baseline import load_baseline  # noqa: E402

MID_JUNE_DOY = date(2021, 6, 15).timetuple().tm_yday


def main() -> int:
    """Print both values and return 0 only if Sylhet is wetter."""
    sylhet = load_baseline("sylhet")[MID_JUNE_DOY]["rain30_mean"]
    rajshahi = load_baseline("rajshahi")[MID_JUNE_DOY]["rain30_mean"]
    print(f"mid-June (doy {MID_JUNE_DOY}) rain30_mean: Sylhet={sylhet} mm, Rajshahi={rajshahi} mm")
    ok = sylhet > rajshahi
    print("PASS: Sylhet > Rajshahi" if ok else "FAIL: expected Sylhet > Rajshahi")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
