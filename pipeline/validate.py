"""CLI: validation against real NASA data (Section 10.4) and the numbers for `docs/methodology.md`.

Two commands:

    python -m pipeline.validate run-year --db data/cache/validation_2022.db
        Scores all districts for 2022-01-01 to 2022-12-31 from IMERG Final Run and POWER only (no
        SMAP, no NDVI; Section 9 task 12.2) into a scratch database, leaving the application
        database untouched.

    python -m pipeline.validate report --year-db data/cache/validation_2022.db
        Measures the four checks of Section 10.4 and prints the result as Markdown. With
        `--write docs/methodology.md` the text is placed verbatim between the
        `<!-- validation:begin -->` and `<!-- validation:end -->` markers of that file.

Everything the report measures is fixed in this file before any result is looked at: nothing
here adapts to the data, and no threshold is read from the data.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YEAR_DB = REPO_ROOT / "data" / "cache" / "validation_2022.db"

BEGIN_MARK = "<!-- validation:begin -->"
END_MARK = "<!-- validation:end -->"

# Fixed definitions (Section 10.4). Dates are the ones the specification names.
EVENT_START = date(2022, 5, 15)
EVENT_END = date(2022, 6, 30)
FALSE_ALARM_END = date(2022, 9, 30)
REFERENCE_ONSET = date(2022, 6, 16)
LEAD_TIME_TARGET_DAYS = 3
CROSS_START = date(2022, 6, 1)
CROSS_END = date(2022, 6, 30)
CROSS_DISTRICTS = ("sylhet", "rajshahi")
YEAR_START = date(2022, 1, 1)
YEAR_END = date(2022, 12, 31)
RAJSHAHI_SALT_LIMIT = 20.0

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
HAZARDS = (("flood", "Flood"), ("drought", "Drought"), ("salt", "Salinity"))


def _use_database(path: Path) -> None:
    """Point the application at `path`; must run before `backend.app` is imported."""
    os.environ["DATABASE_URL"] = f"sqlite:///{path.resolve().as_posix()}"


# --------------------------------------------------------------------------------------------
# run-year
# --------------------------------------------------------------------------------------------
def run_year(db_path: Path, start: date, end: date) -> int:
    """Score `[start, end]` with IMERG Final Run and POWER only, into the database `db_path`."""
    _use_database(db_path)
    from backend.app.db import SessionLocal, create_all
    from backend.app.models import District
    from backend.app.seed import seed
    from pipeline.run_pipeline import run_pipeline
    from sqlalchemy import select

    def no_soil(day: date, districts: list[dict[str, Any]]) -> Mapping[str, float | None]:
        return {d["id"]: None for d in districts}

    create_all()
    with SessionLocal() as session:
        seed(session)
        ids = [d.id for d in session.scalars(select(District))]
    from backend.app.services.risk.baseline import baseline_path

    if any(not baseline_path(i).exists() for i in ids):
        print("Baselines missing; run `python -m pipeline.build_baseline` first.", file=sys.stderr)
        return 1
    with SessionLocal() as session:
        record = run_pipeline(session, start, end, "final", soil_fetcher=no_soil, ndvi_fetcher=None)
        detail = record.detail
    print(
        f"Validation run {record.status}: {detail['snapshots_written']} snapshots, "
        f"IMERG {detail['sources']['IMERG']['status']}, POWER {detail['sources']['POWER']['status']}, "
        f"skipped {detail['skipped_count']}"
    )
    return 0 if record.status == "ok" else 1


# --------------------------------------------------------------------------------------------
# Measurements (pure functions, unit tested)
# --------------------------------------------------------------------------------------------
def first_day(series: Sequence[tuple[date, str]], levels: set[str]) -> date | None:
    """First date whose level is in `levels`; `series` is sorted by date."""
    for day, level in series:
        if level in levels:
            return day
    return None


def event_metrics(
    series: Sequence[tuple[date, float, str]],
    *,
    onset: date = REFERENCE_ONSET,
    event_end: date = EVENT_END,
    window_end: date = FALSE_ALARM_END,
) -> dict[str, Any]:
    """Lead time and High-level day counts for one flood series of `(date, score, level)`.

    `first_moderate` is the first day at Moderate or High (the first day the score reaches 40).
    Lead time is `onset - first_high` in days (negative when High comes after the onset).
    High days are split into three segments so any other definition of "false alarm" can be
    applied by the reader: before the onset, from the onset to `event_end`, and after
    `event_end` up to `window_end`. The false-alarm count is the last segment.
    """
    ordered = sorted(series)
    pairs = [(d, level) for d, _score, level in ordered]
    first_mod = first_day(pairs, {"moderate", "high"})
    first_high = first_day(pairs, {"high"})
    high_days = [d for d, _s, level in ordered if level == "high" and d <= window_end]
    before = [d for d in high_days if d < onset]
    during = [d for d in high_days if onset <= d <= event_end]
    after = [d for d in high_days if event_end < d <= window_end]
    return {
        "first_moderate": first_mod,
        "first_high": first_high,
        "lead_time_days": (onset - first_high).days if first_high else None,
        "high_days_before_onset": before,
        "high_days_onset_to_event_end": during,
        "high_days_after_event_end": after,
        "false_alarm_days": len(after),
        "days_in_window": sum(1 for d, _s, _l in ordered if d <= window_end),
    }


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson correlation coefficient; None when undefined (fewer than 2 points or no spread)."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def compare_rain(imerg: Mapping[date, float | None], power: Mapping[date, float | None]) -> dict[str, Any]:
    """Correlation, mean absolute difference and mean signed difference (IMERG - POWER)."""
    days = sorted(d for d in imerg if imerg[d] is not None and power.get(d) is not None)
    xs = [float(imerg[d]) for d in days]  # type: ignore[arg-type]
    ys = [float(power[d]) for d in days]  # type: ignore[arg-type]
    n = len(days)
    return {
        "days": n,
        "pearson_r": pearson(xs, ys),
        "mean_abs_diff_mm": sum(abs(x - y) for x, y in zip(xs, ys)) / n if n else None,
        "mean_diff_mm": sum(x - y for x, y in zip(xs, ys)) / n if n else None,
        "imerg_total_mm": sum(xs) if n else None,
        "power_total_mm": sum(ys) if n else None,
    }


def monthly_stats(rows: Sequence[tuple[date, float]]) -> dict[int, dict[str, float]]:
    """Mean and maximum per calendar month (1 to 12) for `(date, score)` rows."""
    by_month: dict[int, list[float]] = {}
    for day, score in rows:
        by_month.setdefault(day.month, []).append(score)
    return {m: {"mean": sum(v) / len(v), "max": max(v), "days": len(v)} for m, v in by_month.items()}


def peak_month(stats: Mapping[int, Mapping[str, float]]) -> int:
    """Month with the highest monthly mean score."""
    return max(stats, key=lambda m: stats[m]["mean"])


def seasonality_checks(stats: Mapping[str, Mapping[str, Mapping[int, Mapping[str, float]]]]) -> list[dict[str, Any]]:
    """The four seasonality checks of Section 10.4 item 3, each with the numbers it used.

    `stats[district][hazard]` is the output of `monthly_stats`. Rules, fixed in advance:
    flood peak month = month with the highest monthly mean, must be June to September;
    "higher in A than in B" compares monthly means, and for "March to May" every one of the
    three months must exceed the comparison month; "stays below 20 in every month" is judged on
    the monthly maximum of the daily scores, the strictest reading.
    """
    checks: list[dict[str, Any]] = []
    for district in ("sylhet", "sunamganj"):
        peak = peak_month(stats[district]["flood"])
        checks.append({
            "name": f"Flood score for {district.title()} peaks between June and September",
            "passed": 6 <= peak <= 9,
            "detail": f"peak month by monthly mean = {MONTHS[peak - 1]} "
                      f"({stats[district]['flood'][peak]['mean']:.1f})",
        })
    d = stats["rajshahi"]["drought"]
    checks.append({
        "name": "Drought score for Rajshahi is higher in March and April than in July",
        "passed": d[3]["mean"] > d[7]["mean"] and d[4]["mean"] > d[7]["mean"],
        "detail": f"monthly means: Mar {d[3]['mean']:.1f}, Apr {d[4]['mean']:.1f}, Jul {d[7]['mean']:.1f}",
    })
    for district in ("satkhira", "khulna"):
        s = stats[district]["salt"]
        checks.append({
            "name": f"Salinity score for {district.title()} is higher in March to May than in August",
            "passed": all(s[m]["mean"] > s[8]["mean"] for m in (3, 4, 5)),
            "detail": f"monthly means: Mar {s[3]['mean']:.1f}, Apr {s[4]['mean']:.1f}, "
                      f"May {s[5]['mean']:.1f}, Aug {s[8]['mean']:.1f}",
        })
    r = stats["rajshahi"]["salt"]
    worst = max(r, key=lambda m: r[m]["max"])
    checks.append({
        "name": f"Salinity score for Rajshahi stays below {RAJSHAHI_SALT_LIMIT:.0f} in every month",
        "passed": all(r[m]["max"] < RAJSHAHI_SALT_LIMIT for m in r),
        "detail": f"highest daily score in any month = {r[worst]['max']:.1f} ({MONTHS[worst - 1]})",
    })
    return checks


# --------------------------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------------------------
def load_flood_series(session: Any, district_id: str, start: date, end: date) -> list[tuple[date, float, str]]:
    """`(date, flood_score, flood_level)` rows for one district between `start` and `end`."""
    from backend.app.models import RiskSnapshot
    from sqlalchemy import select

    rows = session.scalars(
        select(RiskSnapshot)
        .where(RiskSnapshot.district_id == district_id, RiskSnapshot.date >= start, RiskSnapshot.date <= end)
        .order_by(RiskSnapshot.date)
    )
    return [(r.date, float(r.flood_score), r.flood_level) for r in rows]


def load_scores(session: Any, start: date, end: date) -> dict[str, dict[str, list[tuple[date, float]]]]:
    """`scores[district][hazard]` lists of `(date, score)` between `start` and `end`."""
    from backend.app.models import RiskSnapshot
    from sqlalchemy import select

    out: dict[str, dict[str, list[tuple[date, float]]]] = {}
    for r in session.scalars(
        select(RiskSnapshot).where(RiskSnapshot.date >= start, RiskSnapshot.date <= end).order_by(RiskSnapshot.date)
    ):
        per = out.setdefault(r.district_id, {"flood": [], "drought": [], "salt": []})
        per["flood"].append((r.date, float(r.flood_score)))
        per["drought"].append((r.date, float(r.drought_score)))
        per["salt"].append((r.date, float(r.salt_score)))
    return out


def load_imerg_obs(session: Any, district_id: str, start: date, end: date) -> dict[date, float | None]:
    """Stored IMERG Final Run daily district rainfall (`precip_mm`)."""
    from backend.app.models import Observation
    from sqlalchemy import select

    rows = session.scalars(
        select(Observation).where(
            Observation.district_id == district_id,
            Observation.source == "IMERG_FINAL",
            Observation.variable == "precip_mm",
            Observation.date >= start,
            Observation.date <= end,
        )
    )
    return {o.date: o.value for o in rows}


def fetch_power_rain(lat: float, lon: float, start: date, end: date) -> dict[date, float | None]:
    """POWER daily `PRECTOTCORR` (mm/day) at a point."""
    from backend.app.services.nasa.power import fetch_power

    frame = fetch_power(lat, lon, start, end, ("PRECTOTCORR",))
    return {ts.date(): (None if v != v else float(v)) for ts, v in frame["PRECTOTCORR"].items()}


# --------------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------------
def _fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _dates(days: Sequence[date]) -> str:
    return ", ".join(d.isoformat() for d in days) if days else "none"


def _event_block(title: str, metrics: Mapping[str, Any], note: str) -> list[str]:
    lead = metrics["lead_time_days"]
    if lead is None:
        verdict = "no High flood level occurred"
    elif lead >= LEAD_TIME_TARGET_DAYS:
        verdict = f"target of at least {LEAD_TIME_TARGET_DAYS} days MET"
    else:
        verdict = f"target of at least {LEAD_TIME_TARGET_DAYS} days MISSED"
    fm, fh = metrics["first_moderate"], metrics["first_high"]
    return [
        f"**{title}**",
        "",
        note,
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Date of first Moderate-or-higher flood level | {fm.isoformat() if fm else 'none'} |",
        f"| Date of first High flood level | {fh.isoformat() if fh else 'none'} |",
        f"| Reference onset date | {REFERENCE_ONSET.isoformat()} |",
        f"| Lead time (onset minus first High), days | {lead if lead is not None else 'n/a'} ({verdict}) |",
        f"| High days before the onset | {len(metrics['high_days_before_onset'])} |",
        f"| High days from the onset to {EVENT_END.isoformat()} | {len(metrics['high_days_onset_to_event_end'])} |",
        f"| High-level false alarm days, {(EVENT_END + timedelta(days=1)).isoformat()} to "
        f"{FALSE_ALARM_END.isoformat()} | {metrics['false_alarm_days']} |",
        f"| Days scored from {EVENT_START.isoformat()} to {FALSE_ALARM_END.isoformat()} | {metrics['days_in_window']} |",
        "",
        f"High days before the onset: {_dates(metrics['high_days_before_onset'])}.",
        "",
        f"High days after {EVENT_END.isoformat()}: {_dates(metrics['high_days_after_event_end'])}.",
        "",
    ]


def build_report(app_db: Path, year_db: Path) -> str:
    """Run every measurement and return the Markdown text."""
    _use_database(app_db)
    from backend.app.db import SessionLocal
    from backend.app.models import District
    from sqlalchemy import select

    lines: list[str] = []
    with SessionLocal() as session:
        districts = {d.id: (d.lat, d.lon) for d in session.scalars(select(District))}
        app_series = load_flood_series(session, "sylhet", EVENT_START, EVENT_END)
        app_imerg = {did: load_imerg_obs(session, did, CROSS_START, CROSS_END) for did in CROSS_DISTRICTS}

    # Year database: a separate engine, so open it through SQLAlchemy directly.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    year_engine = create_engine(f"sqlite:///{year_db.resolve().as_posix()}")
    with sessionmaker(bind=year_engine)() as ysession:
        year_series = load_flood_series(ysession, "sylhet", EVENT_START, FALSE_ALARM_END)
        scores = load_scores(ysession, YEAR_START, YEAR_END)
        year_imerg = {did: load_imerg_obs(ysession, did, CROSS_START, CROSS_END) for did in CROSS_DISTRICTS}
    year_engine.dispose()

    # 1. Event backtest ----------------------------------------------------------------------
    lines += ["### 1. Event backtest (Sylhet, June 2022)", ""]
    lines += _event_block(
        "A. Pipeline as shipped (SMAP L4 soil input where available, POWER otherwise), "
        f"{EVENT_START.isoformat()} to {EVENT_END.isoformat()}",
        event_metrics(app_series),
        f"Source: application database, {len(app_series)} Sylhet days scored. This run ends on "
        f"{EVENT_END.isoformat()}, so it cannot count High days after that date; the false alarm "
        "row for this run is therefore 0 by construction and is not a measurement.",
    )
    lines += _event_block(
        "B. IMERG Final Run and POWER only (no SMAP, no NDVI), "
        f"{EVENT_START.isoformat()} to {FALSE_ALARM_END.isoformat()}",
        event_metrics(year_series),
        f"Source: validation database, {len(year_series)} Sylhet days scored "
        "(the same run as the seasonality table).",
    )

    # 2. Cross-product consistency ------------------------------------------------------------
    lines += [
        f"### 2. Cross-product consistency, {CROSS_START.isoformat()} to {CROSS_END.isoformat()}",
        "",
        "IMERG Final Run daily district-box mean (from run B) against POWER `PRECTOTCORR` at the "
        "district centroid (mm/day).",
        "",
        "| District | Days | Pearson r | Mean absolute difference (mm/day) | Mean IMERG minus POWER (mm/day) "
        "| IMERG total (mm) | POWER total (mm) |",
        "|---|---|---|---|---|---|---|",
    ]
    for did in CROSS_DISTRICTS:
        lat, lon = districts[did]
        power_rain = fetch_power_rain(lat, lon, CROSS_START, CROSS_END)
        cmp = compare_rain(year_imerg[did], power_rain)
        lines.append(
            f"| {did.title()} | {cmp['days']} | {_fmt(cmp['pearson_r'], 3)} | {_fmt(cmp['mean_abs_diff_mm'])} "
            f"| {_fmt(cmp['mean_diff_mm'])} | {_fmt(cmp['imerg_total_mm'], 1)} | {_fmt(cmp['power_total_mm'], 1)} |"
        )
    lines.append("")

    # 3. Seasonality ---------------------------------------------------------------------------
    stats = {
        did: {hz: monthly_stats(rows) for hz, rows in per.items()} for did, per in scores.items()
    }
    lines += [
        f"### 3. Seasonality checks, {YEAR_START.isoformat()} to {YEAR_END.isoformat()} (all districts)",
        "",
        "| Check | Result | Numbers |",
        "|---|---|---|",
    ]
    for c in seasonality_checks(stats):
        lines.append(f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} | {c['detail']} |")
    lines += ["", "Monthly mean of the daily score (0 to 100):", ""]
    for key, label in HAZARDS:
        lines += [f"**{label}**", "", "| District | " + " | ".join(MONTHS) + " |", "|---|" + "---|" * 12]
        for did in sorted(stats):
            cells = [_fmt(stats[did][key][m]["mean"], 1) if m in stats[did][key] else "n/a" for m in range(1, 13)]
            lines.append(f"| {did.title()} | " + " | ".join(cells) + " |")
        lines.append("")
    days = sorted({len(v["flood"]) for v in scores.values()})
    lines.append(f"Days scored per district: {', '.join(str(n) for n in days)} (of 365).")
    lines.append("")
    return "\n".join(lines)


def write_into(path: Path, text: str) -> None:
    """Replace the text between the two marker lines of `path`."""
    doc = path.read_text(encoding="utf-8")
    if BEGIN_MARK not in doc or END_MARK not in doc:
        raise SystemExit(f"{path} has no {BEGIN_MARK} / {END_MARK} markers")
    head, rest = doc.split(BEGIN_MARK, 1)
    _old, tail = rest.split(END_MARK, 1)
    path.write_text(f"{head}{BEGIN_MARK}\n{text}\n{END_MARK}{tail}", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Krishi Kotha validation (Section 10.4)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run-year", help="score a year with IMERG Final Run and POWER only")
    p_run.add_argument("--db", type=Path, default=DEFAULT_YEAR_DB)
    p_run.add_argument("--start", type=date.fromisoformat, default=YEAR_START)
    p_run.add_argument("--end", type=date.fromisoformat, default=YEAR_END)
    p_rep = sub.add_parser("report", help="measure the Section 10.4 checks and print Markdown")
    p_rep.add_argument("--app-db", type=Path, default=REPO_ROOT / "data" / "krishi_kotha.db")
    p_rep.add_argument("--year-db", type=Path, default=DEFAULT_YEAR_DB)
    p_rep.add_argument("--write", type=Path, help="insert the report between the markers of this file")
    args = parser.parse_args(argv)

    if args.command == "run-year":
        return run_year(args.db, args.start, args.end)
    text = build_report(args.app_db, args.year_db)
    print(text)
    if args.write:
        write_into(args.write, text)
        print(f"written to {args.write}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
