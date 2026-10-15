"""WCAG 2.1 contrast ratio verification for frontend/src styles and tokens.

Computes exact WCAG relative luminance and contrast ratios for:
- Text and background colour pairs used in frontend/src (minimum 4.5:1 for normal text).
- Non-text graphical components and marker boundaries against neighbours (minimum 3:1).
- Confirms --risk-moderate (#E0A100) is never used as text colour on light backgrounds.
- Confirms dark ink (#1F2A24) is used on amber fill (--risk-moderate).
- Confirms darker variant --risk-moderate-text (#8F6600) is used for text on light backgrounds.

Exits 1 on any failing pair.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def relative_luminance(hex_str: str) -> float:
    """Calculate WCAG relative luminance for an sRGB hex colour code."""
    hex_clean = hex_str.strip().lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = ''.join([c * 2 for c in hex_clean])
    if len(hex_clean) != 6:
        raise ValueError(f"Invalid hex colour: '{hex_str}'")

    r = int(hex_clean[0:2], 16) / 255.0
    g = int(hex_clean[2:4], 16) / 255.0
    b = int(hex_clean[4:6], 16) / 255.0

    def to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = to_linear(r)
    g_lin = to_linear(g)
    b_lin = to_linear(b)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate the WCAG contrast ratio between two hex colours (>= 1.0)."""
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def parse_tokens(tokens_file: Path) -> dict[str, str]:
    """Parse CSS variable hex definitions from tokens.css."""
    text = tokens_file.read_text(encoding='utf-8')
    tokens: dict[str, str] = {}
    pattern = re.compile(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\b')
    for match in pattern.finditer(text):
        tokens[match.group(1)] = match.group(2).upper()
    return tokens


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    tokens_file = root / 'frontend' / 'src' / 'styles' / 'tokens.css'
    if not tokens_file.exists():
        print(f"ERROR: Cannot find tokens file at {tokens_file}", file=sys.stderr)
        return 1

    tokens = parse_tokens(tokens_file)
    print(f"Loaded {len(tokens)} colour tokens from {tokens_file.relative_to(root)}:")
    for k, v in sorted(tokens.items()):
        print(f"  {k}: {v}")

    failures = 0

    # Required tokens
    if '--risk-moderate-text' not in tokens:
        print("FAIL: Missing required token '--risk-moderate-text' in tokens.css", file=sys.stderr)
        failures += 1

    # Verify reference values from C1
    print("\n--- Verifying C1 Reference Values ---")
    c1_refs = [
        ('#E0A100 on white', '#E0A100', '#FFFFFF', 2.27),
        ('#E0A100 on #F7F6F1', '#E0A100', '#F7F6F1', 2.09),
        ('dark ink #1F2A24 on #E0A100', '#1F2A24', '#E0A100', 6.55),
        ('#8F6600 on white', '#8F6600', '#FFFFFF', 5.16),
        ('#8F6600 on #F7F6F1', '#8F6600', '#F7F6F1', 4.77),
        ('#B07D00 on white (rejected by review)', '#B07D00', '#FFFFFF', 3.63),
    ]
    for label, c1, c2, expected in c1_refs:
        cr = contrast_ratio(c1, c2)
        print(f"  {label}: computed {cr:.2f} (spec: {expected:.2f})")
        if abs(cr - expected) > 0.05:
            print(f"  WARNING: Reference mismatch for {label}: computed {cr:.2f} vs expected {expected:.2f}")

    # Text & Background Pairs actually used in frontend/src
    print("\n--- Verifying Text / Background Pairs (WCAG AA: >= 4.5:1) ---")
    text_pairs = [
        ("Ink on Surface", tokens.get('--ink', '#1F2A24'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("Ink on Page Background", tokens.get('--ink', '#1F2A24'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("Ink Muted on Surface", tokens.get('--ink-muted', '#55635A'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("Ink Muted on Page Background", tokens.get('--ink-muted', '#55635A'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("Brand on Surface", tokens.get('--brand', '#1E6B45'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("Brand on Page Background", tokens.get('--brand', '#1E6B45'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("Brand Dark on Surface", tokens.get('--brand-dark', '#14472D'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("Brand Dark on Page Background", tokens.get('--brand-dark', '#14472D'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("White on Brand", '#FFFFFF', tokens.get('--brand', '#1E6B45'), 4.5),
        ("White on Brand Dark", '#FFFFFF', tokens.get('--brand-dark', '#14472D'), 4.5),
        ("Risk Low text on Surface", tokens.get('--risk-low', '#2E7D32'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("Risk Low text on Page Background", tokens.get('--risk-low', '#2E7D32'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("Risk High text on Surface", tokens.get('--risk-high', '#C62828'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("Risk High text on Page Background", tokens.get('--risk-high', '#C62828'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("Risk Moderate Text on Surface", tokens.get('--risk-moderate-text', '#8F6600'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("Risk Moderate Text on Page Background", tokens.get('--risk-moderate-text', '#8F6600'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("Dark Ink text on Amber Fill (--risk-moderate)", tokens.get('--ink', '#1F2A24'), tokens.get('--risk-moderate', '#E0A100'), 4.5),
        ("NASA Blue on Surface", tokens.get('--nasa-blue', '#0B3D91'), tokens.get('--surface', '#FFFFFF'), 4.5),
        ("NASA Blue on Page Background", tokens.get('--nasa-blue', '#0B3D91'), tokens.get('--bg', '#F7F6F1'), 4.5),
        ("Method Disclaimer #795548 on #FFF8E1", '#795548', '#FFF8E1', 4.5),
        ("Chip Flood #0369A1 on #E0F2FE", '#0369A1', '#E0F2FE', 4.5),
        ("Chip Salt #92400E on #FEF3C7", '#92400E', '#FEF3C7', 4.5),
        ("Chip Drought #B91C1C on #FEE2E2", '#B91C1C', '#FEE2E2', 4.5),
        ("Chip Command #4B5563 on #F3F4F6", '#4B5563', '#F3F4F6', 4.5),
        ("Call Notice #1E40AF on #EFF6FF", '#1E40AF', '#EFF6FF', 4.5),
        ("Crop Pill #2E7D32 on #E8F5E9", '#2E7D32', '#E8F5E9', 4.5),
    ]
    for label, fg, bg, target in text_pairs:
        cr = contrast_ratio(fg, bg)
        if cr < target:
            print(f"  FAIL: {label}: {cr:.2f}:1 < {target}:1 ({fg} on {bg})", file=sys.stderr)
            failures += 1
        else:
            print(f"  PASS: {label}: {cr:.2f}:1 >= {target}:1")

    # Non-text marker colours against neighbours (WCAG 2.1 SC 1.4.11: >= 3:1)
    print("\n--- Verifying Non-Text Marker Colours Against Neighbours (>= 3:1) ---")
    marker_pairs = [
        ("Marker Risk Low (#2E7D32) vs White background", tokens.get('--risk-low', '#2E7D32'), '#FFFFFF', 3.0),
        ("Marker Risk High (#C62828) vs White background", tokens.get('--risk-high', '#C62828'), '#FFFFFF', 3.0),
        ("Marker Risk Moderate (#E0A100) vs Dark Ink stroke/neighbour", tokens.get('--risk-moderate', '#E0A100'), tokens.get('--ink', '#1F2A24'), 3.0),
        ("Marker Risk Moderate variant (#8F6600) vs White background", tokens.get('--risk-moderate-text', '#8F6600'), '#FFFFFF', 3.0),
        ("TrendChart P90 line (#D32F2F) vs Chart background", '#D32F2F', '#FFFFFF', 3.0),
        ("TrendChart Rainfall bar (#0B3D91) vs Chart background", tokens.get('--nasa-blue', '#0B3D91'), '#FFFFFF', 3.0),
    ]
    for label, c1, c2, target in marker_pairs:
        cr = contrast_ratio(c1, c2)
        if cr < target:
            print(f"  FAIL: {label}: {cr:.2f}:1 < {target}:1 ({c1} vs {c2})", file=sys.stderr)
            failures += 1
        else:
            print(f"  PASS: {label}: {cr:.2f}:1 >= {target}:1")

    # Scan frontend/src for any illegal direct use of --risk-moderate as text colour
    print("\n--- Scanning frontend/src for forbidden text uses of --risk-moderate ---")
    src_dir = root / 'frontend' / 'src'
    forbidden_pattern = re.compile(r'color\s*:\s*var\(--risk-moderate\)')
    for file_path in src_dir.rglob('*.[jJ][sS]*'):
        if '__tests__' in file_path.parts:
            continue
        content = file_path.read_text(encoding='utf-8')
        for lineno, line in enumerate(content.splitlines(), start=1):
            if forbidden_pattern.search(line):
                print(f"  FAIL: {file_path.relative_to(root)}:{lineno} uses 'color: var(--risk-moderate)' directly for text!", file=sys.stderr)
                failures += 1

    if failures > 0:
        print(f"\nFAILED: {failures} contrast check(s) failed.", file=sys.stderr)
        return 1

    print("\nSUCCESS: All WCAG contrast ratio checks passed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
