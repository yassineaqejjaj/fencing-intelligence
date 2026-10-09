"""Statistics computed only from validated records.

Rates are null when the denominator is zero. A null rate means the metric is
not available; it is not stored or displayed as 0%. Counts of matching events
are real zeros when validated data exists but nothing matched.

If a scope has no validated annotations and no validated touches, data_status
is "no_validated_data". Callers must not draw performance charts in that state.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fencing_domain.taxonomy import SUCCESS_OUTCOMES, action_by_code


@dataclass(frozen=True)
class AnnotationView:
    id: str
    athlete_id: str | None
    opponent_id: str | None
    action_code: str
    outcome: str | None
    target_area: str | None
    piste_position: float | None
    validated: bool
    video_id: str | None
    bout_id: str | None
    start_ms: int
    weapon: str | None = None


@dataclass(frozen=True)
class TouchView:
    id: str
    scorer_id: str
    receiver_id: str
    valid: bool
    validated: bool
    target_area: str | None
    timestamp_ms: int
    bout_id: str | None
    video_id: str | None
    weapon: str | None = None


@dataclass(frozen=True)
class ScoreView:
    timestamp_ms: int
    bout_id: str | None
    left_athlete_id: str | None
    right_athlete_id: str | None
    left_score: int
    right_score: int
    weapon: str | None = None


@dataclass(frozen=True)
class BoutView:
    id: str
    weapon: str | None
    started_on: str | None
    opponent_ids: tuple[str, ...]
    competition_id: str | None = None


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator <= 0:
        return {
            "value": None,
            "numerator": numerator,
            "denominator": 0,
            "reason": "no_samples",
        }
    return {
        "value": numerator / denominator,
        "numerator": numerator,
        "denominator": denominator,
        "reason": None,
    }


def _empty_block() -> dict[str, Any]:
    return {
        "touches_scored": 0,
        "touches_conceded": 0,
        "offensive_attempts": 0,
        "offensive_success_rate": _rate(0, 0),
        "defensive_actions": 0,
        "riposte_success_rate": _rate(0, 0),
        "counter_attack_effectiveness": _rate(0, 0),
        "score_progression": [],
        "action_frequency": {},
        "piste_position_distribution": {"bins": [], "missing_position_count": 0},
        "touch_target_distribution": {"counts": {}, "missing_target_count": 0},
        "conceded_target_distribution": {"counts": {}, "missing_target_count": 0},
        "performance_by_opponent": [],
        "performance_over_time": [],
        "undated_bout_count": 0,
    }


def _piste_bins(values: list[float]) -> list[dict[str, Any]]:
    bins = [{"start": round(i / 10, 1), "end": round((i + 1) / 10, 1), "count": 0} for i in range(10)]
    for value in values:
        if value < 0 or value > 1:
            continue
        index = min(9, int(value * 10))
        bins[index]["count"] += 1
    return bins


def compute_block(
    athlete_id: str,
    annotations: list[AnnotationView],
    touches: list[TouchView],
    scores: list[ScoreView],
    bouts: list[BoutView],
) -> dict[str, Any]:
    validated_annotations = [item for item in annotations if item.validated and item.athlete_id == athlete_id]
    validated_touches = [item for item in touches if item.validated and item.valid]
    scored = [item for item in validated_touches if item.scorer_id == athlete_id]
    conceded = [item for item in validated_touches if item.receiver_id == athlete_id]

    offensive = []
    defensive = 0
    ripostes = []
    counters = []
    frequency: dict[str, int] = defaultdict(int)
    positions: list[float] = []
    missing_positions = 0

    for item in validated_annotations:
        spec = action_by_code(item.action_code)
        frequency[item.action_code] += 1
        if item.piste_position is None:
            missing_positions += 1
        else:
            positions.append(item.piste_position)
        if spec is None:
            continue
        if spec.counts_as_offensive_attempt:
            offensive.append(item)
        if spec.counts_as_defensive:
            defensive += 1
        if spec.riposte_family:
            ripostes.append(item)
        if spec.counter_attack_family:
            counters.append(item)

    offensive_success = sum(1 for item in offensive if item.outcome in SUCCESS_OUTCOMES)
    riposte_success = sum(1 for item in ripostes if item.outcome in SUCCESS_OUTCOMES)
    counter_success = sum(1 for item in counters if item.outcome in SUCCESS_OUTCOMES)

    targets: dict[str, int] = defaultdict(int)
    missing_targets = 0
    for item in scored:
        if item.target_area:
            targets[item.target_area] += 1
        else:
            missing_targets += 1

    conceded_targets: dict[str, int] = defaultdict(int)
    missing_conceded_targets = 0
    for item in conceded:
        if item.target_area:
            conceded_targets[item.target_area] += 1
        else:
            missing_conceded_targets += 1

    bout_by_id = {bout.id: bout for bout in bouts}
    by_opponent: dict[str, dict[str, int]] = defaultdict(lambda: {"touches_scored": 0, "touches_conceded": 0, "bouts": 0})
    seen_bouts: dict[str, set[str]] = defaultdict(set)
    for item in scored:
        by_opponent[item.receiver_id]["touches_scored"] += 1
        if item.bout_id:
            seen_bouts[item.receiver_id].add(item.bout_id)
    for item in conceded:
        by_opponent[item.scorer_id]["touches_conceded"] += 1
        if item.bout_id:
            seen_bouts[item.scorer_id].add(item.bout_id)
    for opponent_id, bout_ids in seen_bouts.items():
        by_opponent[opponent_id]["bouts"] = len(bout_ids)

    over_time: dict[str, dict[str, int]] = defaultdict(lambda: {"touches_scored": 0, "touches_conceded": 0})
    undated = 0
    dated_bouts: set[str] = set()
    undated_bouts: set[str] = set()
    for item in scored + conceded:
        bout = bout_by_id.get(item.bout_id or "")
        day = bout.started_on if bout else None
        if day is None:
            if item.bout_id:
                undated_bouts.add(item.bout_id)
            else:
                undated += 1
            continue
        dated_bouts.add(item.bout_id or day)
        if item.scorer_id == athlete_id:
            over_time[day]["touches_scored"] += 1
        if item.receiver_id == athlete_id:
            over_time[day]["touches_conceded"] += 1

    progression = []
    for score in sorted(scores, key=lambda item: (item.timestamp_ms, item.bout_id or "")):
        if athlete_id not in {score.left_athlete_id, score.right_athlete_id}:
            continue
        own = score.left_score if score.left_athlete_id == athlete_id else score.right_score
        opp = score.right_score if score.left_athlete_id == athlete_id else score.left_score
        progression.append(
            {
                "timestamp_ms": score.timestamp_ms,
                "bout_id": score.bout_id,
                "athlete_score": own,
                "opponent_score": opp,
            }
        )

    block = _empty_block()
    block.update(
        {
            "touches_scored": len(scored),
            "touches_conceded": len(conceded),
            "offensive_attempts": len(offensive),
            "offensive_success_rate": _rate(offensive_success, len(offensive)),
            "defensive_actions": defensive,
            "riposte_success_rate": _rate(riposte_success, len(ripostes)),
            "counter_attack_effectiveness": _rate(counter_success, len(counters)),
            "score_progression": progression,
            "action_frequency": dict(sorted(frequency.items())),
            "piste_position_distribution": {
                "bins": _piste_bins(positions),
                "missing_position_count": missing_positions,
                "observed_count": len(positions),
            },
            "touch_target_distribution": {
                "counts": dict(sorted(targets.items())),
                "missing_target_count": missing_targets,
            },
            "conceded_target_distribution": {
                "counts": dict(sorted(conceded_targets.items())),
                "missing_target_count": missing_conceded_targets,
            },
            "performance_by_opponent": [
                {"opponent_id": opponent_id, **counts}
                for opponent_id, counts in sorted(by_opponent.items())
            ],
            "performance_over_time": [
                {"date": day, **counts} for day, counts in sorted(over_time.items())
            ],
            "undated_bout_count": len(undated_bouts) + (1 if undated and not undated_bouts else 0),
            "validated_annotation_count": len(validated_annotations),
            "validated_touch_count": len(scored) + len(conceded),
        }
    )
    return block


def _filter_weapon(items: list[Any], weapon: str | None) -> list[Any]:
    if weapon is None:
        return items
    return [item for item in items if getattr(item, "weapon", None) == weapon]


def athlete_statistics(
    athlete_id: str,
    annotations: list[AnnotationView],
    touches: list[TouchView],
    scores: list[ScoreView],
    bouts: list[BoutView],
    weapon: str | None = None,
) -> dict[str, Any]:
    def scoped(selected: str | None) -> dict[str, Any]:
        return compute_block(
            athlete_id,
            _filter_weapon(annotations, selected),
            _filter_weapon(touches, selected),
            _filter_weapon(scores, selected),
            _filter_weapon(bouts, selected),
        )

    scope_annotations = _filter_weapon(annotations, weapon)
    scope_touches = _filter_weapon(touches, weapon)
    any_validated = any(
        item.validated and item.athlete_id == athlete_id for item in scope_annotations
    ) or any(
        item.validated and item.valid and athlete_id in {item.scorer_id, item.receiver_id}
        for item in scope_touches
    )
    weapons_present = sorted(
        {
            item.weapon
            for item in list(annotations) + list(touches) + list(bouts)
            if getattr(item, "weapon", None)
            and (
                getattr(item, "athlete_id", None) == athlete_id
                or getattr(item, "opponent_id", None) == athlete_id
                or getattr(item, "scorer_id", None) == athlete_id
                or getattr(item, "receiver_id", None) == athlete_id
                or athlete_id in getattr(item, "opponent_ids", ())
            )
        }
    )
    by_weapon = {name: scoped(name) for name in ([weapon] if weapon else weapons_present)}
    combined = scoped(weapon)
    mixed = weapon is None and len(weapons_present) > 1
    return {
        "athlete_id": athlete_id,
        "data_status": "ok" if any_validated else "no_validated_data",
        "weapon_filter": weapon,
        "mixed_weapons": mixed,
        "weapons_present": weapons_present,
        "combined": combined,
        "by_weapon": by_weapon,
        "formula_version": "1",
    }


def bout_statistics(
    left_athlete_id: str | None,
    right_athlete_id: str | None,
    annotations: list[AnnotationView],
    touches: list[TouchView],
    scores: list[ScoreView],
    bout: BoutView | None,
) -> dict[str, Any]:
    bouts = [bout] if bout else []
    left = (
        compute_block(left_athlete_id, annotations, touches, scores, bouts)
        if left_athlete_id
        else None
    )
    right = (
        compute_block(right_athlete_id, annotations, touches, scores, bouts)
        if right_athlete_id
        else None
    )
    validated = any(item.validated for item in annotations) or any(item.validated and item.valid for item in touches)
    return {
        "bout_id": bout.id if bout else None,
        "data_status": "ok" if validated else "no_validated_data",
        "weapon": bout.weapon if bout else None,
        "left": left,
        "right": right,
        "score_progression": [
            {
                "timestamp_ms": item.timestamp_ms,
                "left_score": item.left_score,
                "right_score": item.right_score,
            }
            for item in sorted(scores, key=lambda row: row.timestamp_ms)
        ],
        "formula_version": "1",
    }
