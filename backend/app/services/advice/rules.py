"""Rule engine for advice selection (Section 7.4)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..risk.scoring import THRESHOLD_HIGH, THRESHOLD_MODERATE


@dataclass(frozen=True)
class RuleEvaluationResult:
    """Result of rule evaluation for a district/crop condition."""

    rule_id: str
    hazard: str | None
    level: str
    effective_score: float
    effective_scores: dict[str, float]
    stage_key: str


def select_advice_rule(
    flood_score: float,
    drought_score: float,
    salt_score: float,
    crop_id: str,
    stage_key: str,
    sensitivities: Mapping[str, float],
) -> RuleEvaluationResult:
    """Evaluate hazards in the order flood, drought, salt.

    Effective value is `score * crop_stage_sensitivity`, capped at 100.
    Chooses the hazard with the highest effective value at or above 40.
    Ties broken by evaluation order (flood, drought, salt).
    If no hazard is at or above 40, returns 'none_low'.
    """
    crop_norm = crop_id.strip().lower()

    # Calculate effective scores capped at 100
    eff_scores = {
        "flood": min(100.0, max(0.0, float(flood_score) * sensitivities.get("flood", 1.0))),
        "drought": min(100.0, max(0.0, float(drought_score) * sensitivities.get("drought", 1.0))),
        "salt": min(100.0, max(0.0, float(salt_score) * sensitivities.get("salt", 1.0))),
    }

    # Evaluate in order: flood, drought, salt
    order = ("flood", "drought", "salt")
    best_hazard: str | None = None
    best_eff = -1.0

    for h in order:
        eff = eff_scores[h]
        # Highest effective value at or above 40 wins.
        # Strict '>' ensures earlier hazard wins in case of tie.
        if eff >= THRESHOLD_MODERATE and eff > best_eff:
            best_eff = eff
            best_hazard = h

    if best_hazard is None:
        return RuleEvaluationResult(
            rule_id="none_low",
            hazard=None,
            level="low",
            effective_score=0.0,
            effective_scores=eff_scores,
            stage_key=stage_key,
        )

    winning_eff = best_eff
    winning_level = "high" if winning_eff >= THRESHOLD_HIGH else "moderate"

    if best_hazard == "flood":
        if winning_level == "high":
            if stage_key == "grain_filling_harvest" or stage_key.endswith("grain_filling_harvest"):
                rule_id = "flood_high_harvest"
            else:
                rule_id = "flood_high_early"
        else:
            rule_id = "flood_moderate_any"

    elif best_hazard == "drought":
        if (
            winning_level == "high"
            and crop_norm == "aman"
            and stage_key in ("nursery", "transplanting")
        ):
            rule_id = "drought_high_transplant"
        else:
            rule_id = "drought_moderate_any"

    elif best_hazard == "salt":
        rule_id = "salt_high_any"

    else:
        rule_id = "none_low"

    return RuleEvaluationResult(
        rule_id=rule_id,
        hazard=best_hazard,
        level=winning_level,
        effective_score=round(winning_eff, 2),
        effective_scores={k: round(v, 2) for k, v in eff_scores.items()},
        stage_key=stage_key,
    )
