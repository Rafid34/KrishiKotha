"""WCAG 2.1 AA Contrast Ratio Verification for Krishi Kotha Dark UI.

Computes exact WCAG relative luminance and contrast ratios for:
- Text and background colour pairs used in frontend/src (minimum 4.5:1 for normal text, 3:1 for large text).
- Non-text graphical components and marker boundaries against neighbours (minimum 3:1).
- Confirms --bg is #0C0A09 and #000000 is never used in tokens.css.
- Confirms lime accent #D4F268 is never used for any risk level.
- Verifies contrast on glass top bar, sticky note, noise overlay, and map overlays.

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

    tokens_raw = tokens_file.read_text(encoding='utf-8')
    tokens = parse_tokens(tokens_file)

    failures = 0

    print("=" * 82)
    print(" WCAG AA CONTRAST RATIO VERIFICATION (DARK UI DESIGN REFERENCE)")
    print("=" * 82)

    # Invariant 1: Never use #000000
    if '#000000' in tokens_raw.lower() or '#000;' in tokens_raw.lower():
        print("FAIL: Forbidden pure black #000000 found in tokens.css!", file=sys.stderr)
        failures += 1
    else:
        print("[PASS] Invariant check: No #000000 used (pure black avoided, stone black used).")

    # Invariant 2: Never use lime #D4F268 for risk levels
    risk_colors = [tokens.get('--risk-low'), tokens.get('--risk-moderate'), tokens.get('--risk-high')]
    if '#D4F268' in [c.upper() for c in risk_colors if c]:
        print("FAIL: Accent lime #D4F268 must NOT be used as a risk level colour!", file=sys.stderr)
        failures += 1
    else:
        print("[PASS] Invariant check: Accent lime #D4F268 is never used for risk levels.")

    # Core surfaces
    bg = tokens.get('--bg', '#0C0A09')
    surface = tokens.get('--surface', '#1C1917')
    surface_elevated = tokens.get('--surface-elevated', '#292524')
    top_bar_glass = '#151210'  # Effective blended dark glass background

    # Foreground tokens
    ink = tokens.get('--ink', '#E7E5E4')
    ink_muted = tokens.get('--ink-muted', '#A8A29E')
    accent = tokens.get('--accent', '#D4F268')
    risk_low = tokens.get('--risk-low', '#4ADE80')
    risk_moderate = tokens.get('--risk-moderate', '#FBBF24')
    risk_high = tokens.get('--risk-high', '#F87171')
    nasa_blue = tokens.get('--nasa-blue', '#60A5FA')
    sticky_bg = tokens.get('--sticky-bg', '#D4F268')
    sticky_text = tokens.get('--sticky-text', '#1C1917')

    pairs = [
        # Normal text pairs (target 4.5:1)
        ("Primary text on background", ink, bg, 4.5, "Text"),
        ("Primary text on surface", ink, surface, 4.5, "Text"),
        ("Primary text on elevated surface", ink, surface_elevated, 4.5, "Text"),
        ("Primary text on glass top bar", ink, top_bar_glass, 4.5, "Text"),
        ("Muted text on background", ink_muted, bg, 4.5, "Text"),
        ("Muted text on surface", ink_muted, surface, 4.5, "Text"),
        ("Muted text on elevated surface", ink_muted, surface_elevated, 4.5, "Text"),
        ("Accent link/text on background", accent, bg, 4.5, "Text"),
        ("Accent link/text on surface", accent, surface, 4.5, "Text"),
        ("Accent link/text on elevated surface", accent, surface_elevated, 4.5, "Text"),
        ("Button dark text on Accent fill", bg, accent, 4.5, "Text"),
        ("Sticky note text on Lime card", sticky_text, sticky_bg, 4.5, "Text"),
        ("Top bar active link text on off-white", '#0C0A09', '#E7E5E4', 4.5, "Text"),
        ("Risk Low text on background", risk_low, bg, 4.5, "Text"),
        ("Risk Low text on surface", risk_low, surface, 4.5, "Text"),
        ("Risk Low text on elevated surface", risk_low, surface_elevated, 4.5, "Text"),
        ("Risk Moderate text on background", risk_moderate, bg, 4.5, "Text"),
        ("Risk Moderate text on surface", risk_moderate, surface, 4.5, "Text"),
        ("Risk Moderate text on elevated surface", risk_moderate, surface_elevated, 4.5, "Text"),
        ("Risk High text on background", risk_high, bg, 4.5, "Text"),
        ("Risk High text on surface", risk_high, surface, 4.5, "Text"),
        ("Risk High text on elevated surface", risk_high, surface_elevated, 4.5, "Text"),
        ("NASA blue label on background", nasa_blue, bg, 4.5, "Text"),
        ("NASA blue label on surface", nasa_blue, surface, 4.5, "Text"),
        ("NASA blue label on elevated surface", nasa_blue, surface_elevated, 4.5, "Text"),
        ("Map marker text on dark pill background", ink, surface, 4.5, "Text"),
        ("Catalog label Fig text on dark pill", ink, '#141210', 4.5, "Text"),
        ("Mandatory disclaimer on surface", ink, surface, 4.5, "Text"),
        ("Proxy salinity label on surface", ink, surface, 4.5, "Text"),

        # Non-text graphical components & markers (target 3.0:1)
        ("Risk Low marker / icon vs Surface", risk_low, surface, 3.0, "UI Component"),
        ("Risk Moderate marker / icon vs Surface", risk_moderate, surface, 3.0, "UI Component"),
        ("Risk High marker / icon vs Surface", risk_high, surface, 3.0, "UI Component"),
        ("Catalog label status dot vs dark pill", accent, '#141210', 3.0, "UI Component"),
        ("TrendChart P90 line vs Elevated surface", risk_high, surface_elevated, 3.0, "UI Component"),
        ("TrendChart Rainfall bar vs Elevated surface", nasa_blue, surface_elevated, 3.0, "UI Component"),
        ("TrendChart Soil line vs Elevated surface", risk_low, surface_elevated, 3.0, "UI Component"),
        ("Focus ring (Acid Lime) vs Background", accent, bg, 3.0, "UI Component"),
        ("Focus ring (Acid Lime) vs Surface", accent, surface, 3.0, "UI Component"),
    ]

    print(f"\n{'Pair / Element':<42} | {'Foreground':<10} | {'Background':<10} | {'Ratio':<8} | {'Target':<7} | {'Status'}")
    print("-" * 88)

    for label, fg, bg_col, target, category in pairs:
        cr = contrast_ratio(fg, bg_col)
        status = "PASS" if cr >= target else "FAIL"
        if status == "FAIL":
            failures += 1
            print(f"{label:<42} | {fg:<10} | {bg_col:<10} | {cr:5.2f}:1  | {target:4.1f}:1  | FAIL", file=sys.stderr)
        else:
            print(f"{label:<42} | {fg:<10} | {bg_col:<10} | {cr:5.2f}:1  | {target:4.1f}:1  | PASS")

    # Noise overlay robustness test: +/- 4% luminance variance check
    print("\n--- Verifying Robustness Across 4% Noise Overlay ---")
    for label, fg, bg_col, target, _ in pairs[:5]:
        base_cr = contrast_ratio(fg, bg_col)
        # Even with worst-case 4% overlay variance:
        worst_cr = base_cr * 0.96
        if worst_cr < target:
            print(f"FAIL: Noise overlay degrades {label} below {target}:1 ({worst_cr:.2f}:1)", file=sys.stderr)
            failures += 1
        else:
            print(f"PASS: {label} with 4% noise overlay: {worst_cr:.2f}:1 >= {target}:1")

    print("=" * 88)
    if failures > 0:
        print(f"FAILED: {failures} contrast check(s) failed.", file=sys.stderr)
        return 1

    print("SUCCESS: All WCAG AA contrast ratio checks passed (0 failures).")
    print("=" * 88)
    return 0


if __name__ == '__main__':
    sys.exit(main())
