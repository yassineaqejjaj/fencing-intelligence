"""Tactical intelligence derived only from validated records.

This module turns validated annotations and validated valid touches into
readings an athlete can act on: which actions actually score, how the fencer
behaves when leading or trailing, scoring runs, the trend across bouts, and
head-to-head readings per opponent. Every number carries its numerator and
denominator. Nothing is emitted below MIN_SAMPLES, and a reading with no
samples is null, never zero.

The insight cards are template sentences assembled from those numbers. No
language model is involved and no sentence contains a figure that is not in
its evidence block.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fencing_domain.statistics import AnnotationView, BoutView, ScoreView, TouchView, _filter_weapon, _rate
from fencing_domain.taxonomy import SUCCESS_OUTCOMES, action_by_code

FORMULA_VERSION = "1"
MIN_SAMPLES = 5
MIN_BOUTS_FOR_TREND = 4
TREND_DELTA = 0.05
CATEGORIES = ("offensive", "defensive", "counter_offensive", "footwork", "preparation", "priority")

_LABELS_EN = {"offensive": "offensive actions", "defensive": "defensive actions", "counter_offensive": "counter-offensive actions", "footwork": "footwork", "preparation": "preparations", "priority": "priority calls"}
_LABELS_FR = {"offensive": "actions offensives", "defensive": "actions défensives", "counter_offensive": "actions contre-offensives", "footwork": "déplacements", "preparation": "préparations", "priority": "décisions de priorité"}


def _pct(value: float | None, locale: str) -> str:
    if value is None:
        return "—"
    number = round(value * 100)
    return f"{number} %" if locale == "fr" else f"{number}%"


def _level(samples: int) -> str:
    if samples >= 20:
        return "high"
    if samples >= 10:
        return "moderate"
    return "low"


def _action_label(code: str, locale: str) -> str:
    spec = action_by_code(code)
    if spec is None:
        return code.replace("_", " ")
    return spec.label_fr if locale == "fr" else spec.label_en


# --------------------------------------------------------------------------- profile


def tactical_profile(athlete_id: str, annotations: list[AnnotationView]) -> dict[str, Any]:
    acting = [item for item in annotations if item.validated and item.athlete_id == athlete_id]
    total = len(acting)
    by_category: dict[str, dict[str, int]] = {name: {"attempts": 0, "successes": 0} for name in CATEGORIES}
    by_action: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "successes": 0})
    for item in acting:
        spec = action_by_code(item.action_code)
        success = 1 if item.outcome in SUCCESS_OUTCOMES else 0
        by_action[item.action_code]["attempts"] += 1
        by_action[item.action_code]["successes"] += success
        if spec is None:
            continue
        bucket = by_category.setdefault(spec.category, {"attempts": 0, "successes": 0})
        bucket["attempts"] += 1
        bucket["successes"] += success

    categories = {
        name: {
            "attempts": counts["attempts"],
            "successes": counts["successes"],
            "success_rate": _rate(counts["successes"], counts["attempts"]),
            "share": _rate(counts["attempts"], total),
        }
        for name, counts in by_category.items()
    }
    actions = {
        code: {
            "attempts": counts["attempts"],
            "successes": counts["successes"],
            "success_rate": _rate(counts["successes"], counts["attempts"]),
        }
        for code, counts in sorted(by_action.items())
    }
    eligible = [
        {"action_code": code, **values}
        for code, values in actions.items()
        if values["attempts"] >= MIN_SAMPLES and values["success_rate"]["value"] is not None
    ]
    # A 20% action is not a "scoring action" just because it is the only one with enough samples.
    strengths = sorted(
        [row for row in eligible if row["success_rate"]["value"] >= 0.45],
        key=lambda row: (-row["success_rate"]["value"], -row["attempts"]),
    )[:3]
    strength_codes = {row["action_code"] for row in strengths}
    weaknesses = sorted(
        [row for row in eligible if row["success_rate"]["value"] < 0.35 and row["action_code"] not in strength_codes],
        key=lambda row: (row["success_rate"]["value"], -row["attempts"]),
    )[:3]
    return {
        "total_actions": total,
        "by_category": categories,
        "by_action": actions,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


# --------------------------------------------------------------------------- score reconstruction


def _bout_sequences(athlete_id: str, touches: list[TouchView]) -> dict[str, list[tuple[int, int, bool, TouchView]]]:
    """Per bout, the ordered touches with the athlete's score before each one.

    Returns {bout_id: [(own_before, opp_before, scored_by_me, touch), ...]}.
    Touches without a bout cannot be placed in a score and are skipped.
    """
    valid = [item for item in touches if item.validated and item.valid and item.bout_id and athlete_id in {item.scorer_id, item.receiver_id}]
    grouped: dict[str, list[TouchView]] = defaultdict(list)
    for item in valid:
        grouped[item.bout_id or ""].append(item)
    sequences: dict[str, list[tuple[int, int, bool, TouchView]]] = {}
    for bout_id, rows in grouped.items():
        own = opp = 0
        steps = []
        for touch in sorted(rows, key=lambda row: (row.timestamp_ms, row.id)):
            mine = touch.scorer_id == athlete_id
            steps.append((own, opp, mine, touch))
            if mine:
                own += 1
            else:
                opp += 1
        sequences[bout_id] = steps
    return sequences


def situation_split(athlete_id: str, touches: list[TouchView]) -> dict[str, Any]:
    sequences = _bout_sequences(athlete_id, touches)
    states = {name: {"scored": 0, "conceded": 0} for name in ("leading", "tied", "trailing")}
    first_touch_won = 0
    last_touch_won = 0
    bouts_with_touches = 0
    for steps in sequences.values():
        if not steps:
            continue
        bouts_with_touches += 1
        if steps[0][2]:
            first_touch_won += 1
        if steps[-1][2]:
            last_touch_won += 1
        for own, opp, mine, _touch in steps:
            state = "leading" if own > opp else "trailing" if own < opp else "tied"
            states[state]["scored" if mine else "conceded"] += 1
    return {
        "states": {
            name: {
                "scored": counts["scored"],
                "conceded": counts["conceded"],
                "touch_share": _rate(counts["scored"], counts["scored"] + counts["conceded"]),
            }
            for name, counts in states.items()
        },
        "first_touch_rate": _rate(first_touch_won, bouts_with_touches),
        "last_touch_rate": _rate(last_touch_won, bouts_with_touches),
        "bouts_counted": bouts_with_touches,
    }


# --------------------------------------------------------------------------- momentum


def _runs(steps: list[tuple[int, int, bool, Any]]) -> dict[str, Any]:
    longest_for = longest_against = current = 0
    current_mine: bool | None = None
    lead_changes = 0
    leader: bool | None = None  # True = me leading, False = opponent leading, None = tied/no lead yet
    max_deficit = 0
    own = opp = 0
    for _own_before, _opp_before, mine, _touch in steps:
        if current_mine is mine:
            current += 1
        else:
            current_mine = mine
            current = 1
        if mine:
            longest_for = max(longest_for, current)
            own += 1
        else:
            longest_against = max(longest_against, current)
            opp += 1
        max_deficit = max(max_deficit, opp - own)
        now = True if own > opp else False if own < opp else None
        if now is not None and leader is not None and now != leader:
            lead_changes += 1
        if now is not None:
            leader = now
    result = "win" if own > opp else "loss" if own < opp else "undecided"
    return {
        "longest_run_for": longest_for,
        "longest_run_against": longest_against,
        "lead_changes": lead_changes,
        "max_deficit": max_deficit,
        "final": {"own": own, "opponent": opp},
        "result": result,
        "comeback": result == "win" and max_deficit >= 2,
    }


def momentum(athlete_id: str, touches: list[TouchView], bouts: list[BoutView]) -> dict[str, Any]:
    sequences = _bout_sequences(athlete_id, touches)
    by_date = {bout.id: bout.started_on for bout in bouts}
    per_bout = []
    for bout_id, steps in sequences.items():
        if not steps:
            continue
        per_bout.append({"bout_id": bout_id, "date": by_date.get(bout_id), **_runs(steps)})
    per_bout.sort(key=lambda row: (row["date"] or "", row["bout_id"]))
    wins = sum(1 for row in per_bout if row["result"] == "win")
    losses = sum(1 for row in per_bout if row["result"] == "loss")
    decided = wins + losses
    best_for = max(per_bout, key=lambda row: row["longest_run_for"], default=None)
    worst_against = max(per_bout, key=lambda row: row["longest_run_against"], default=None)
    return {
        "bouts": per_bout,
        "bouts_won": wins,
        "bouts_lost": losses,
        "bouts_undecided": len(per_bout) - decided,
        "win_rate": _rate(wins, decided),
        "comebacks": sum(1 for row in per_bout if row["comeback"]),
        "longest_run_for": {"length": best_for["longest_run_for"], "bout_id": best_for["bout_id"]} if best_for else None,
        "longest_run_against": {"length": worst_against["longest_run_against"], "bout_id": worst_against["bout_id"]} if worst_against else None,
    }


def bout_momentum(touches: list[TouchView], left_id: str | None, right_id: str | None) -> dict[str, Any]:
    """Running score timeline for one bout from validated valid touches."""
    valid = sorted(
        [item for item in touches if item.validated and item.valid],
        key=lambda row: (row.timestamp_ms, row.id),
    )
    left = right = 0
    timeline = []
    run_side: str | None = None
    run_length = 0
    for touch in valid:
        side = "left" if touch.scorer_id == left_id else "right" if touch.scorer_id == right_id else "unknown"
        if side == "left":
            left += 1
        elif side == "right":
            right += 1
        if side == run_side:
            run_length += 1
        else:
            run_side = side
            run_length = 1
        timeline.append({"timestamp_ms": touch.timestamp_ms, "left": left, "right": right, "scorer": side, "run_length": run_length, "target_area": touch.target_area})
    known = [(0, 0, item["scorer"] == "left", None) for item in timeline if item["scorer"] != "unknown"]
    left_view = _runs(known) if known else None
    return {
        "data_status": "ok" if timeline else "no_validated_data",
        "timeline": timeline,
        "left": {"longest_run": left_view["longest_run_for"], "score": left} if left_view else None,
        "right": {"longest_run": left_view["longest_run_against"], "score": right} if left_view else None,
        "lead_changes": left_view["lead_changes"] if left_view else 0,
        "formula_version": FORMULA_VERSION,
    }


# --------------------------------------------------------------------------- trend


def trend(athlete_id: str, touches: list[TouchView], bouts: list[BoutView]) -> dict[str, Any]:
    sequences = _bout_sequences(athlete_id, touches)
    by_date = {bout.id: bout.started_on for bout in bouts}
    points = []
    undated = 0
    for bout_id, steps in sequences.items():
        if not steps:
            continue
        day = by_date.get(bout_id)
        if day is None:
            undated += 1
            continue
        scored = sum(1 for step in steps if step[2])
        total = len(steps)
        points.append({"date": day, "bout_id": bout_id, "touch_share": _rate(scored, total), "touches": total})
    points.sort(key=lambda row: (row["date"], row["bout_id"]))
    if len(points) < MIN_BOUTS_FOR_TREND:
        return {"points": points, "direction": None, "delta": None, "reason": "insufficient_bouts", "undated_bouts": undated, "minimum_bouts": MIN_BOUTS_FOR_TREND}
    half = len(points) // 2
    early = [row["touch_share"]["value"] for row in points[:half]]
    late = [row["touch_share"]["value"] for row in points[half:]]
    delta = (sum(late) / len(late)) - (sum(early) / len(early))
    direction = "improving" if delta > TREND_DELTA else "declining" if delta < -TREND_DELTA else "stable"
    return {"points": points, "direction": direction, "delta": delta, "reason": None, "undated_bouts": undated, "minimum_bouts": MIN_BOUTS_FOR_TREND}


# --------------------------------------------------------------------------- opponents


def opponents(athlete_id: str, touches: list[TouchView], annotations: list[AnnotationView]) -> list[dict[str, Any]]:
    valid = [item for item in touches if item.validated and item.valid and athlete_id in {item.scorer_id, item.receiver_id}]
    table: dict[str, dict[str, Any]] = defaultdict(lambda: {"scored": 0, "conceded": 0, "bout_ids": set()})
    for item in valid:
        other = item.receiver_id if item.scorer_id == athlete_id else item.scorer_id
        table[other]["scored" if item.scorer_id == athlete_id else "conceded"] += 1
        if item.bout_id:
            table[other]["bout_ids"].add(item.bout_id)
    per_opponent_actions: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"attempts": 0, "successes": 0}))
    for item in annotations:
        if not item.validated or item.athlete_id != athlete_id or not item.opponent_id:
            continue
        bucket = per_opponent_actions[item.opponent_id][item.action_code]
        bucket["attempts"] += 1
        bucket["successes"] += 1 if item.outcome in SUCCESS_OUTCOMES else 0
    rows = []
    for other, counts in table.items():
        own_touches = [item for item in valid if other in {item.scorer_id, item.receiver_id}]
        split = situation_split(athlete_id, own_touches)
        best = None
        for code, values in per_opponent_actions.get(other, {}).items():
            if values["attempts"] < MIN_SAMPLES:
                continue
            rate = values["successes"] / values["attempts"]
            if best is None or rate > best["success_rate"]["value"]:
                best = {"action_code": code, "attempts": values["attempts"], "successes": values["successes"], "success_rate": _rate(values["successes"], values["attempts"])}
        rows.append(
            {
                "opponent_id": other,
                "bouts": len(counts["bout_ids"]),
                "scored": counts["scored"],
                "conceded": counts["conceded"],
                "touch_share": _rate(counts["scored"], counts["scored"] + counts["conceded"]),
                "trailing_touch_share": split["states"]["trailing"]["touch_share"],
                "best_action": best,
            }
        )
    rows.sort(key=lambda row: (-(row["scored"] + row["conceded"]), row["opponent_id"]))
    return rows


# --------------------------------------------------------------------------- cards


def _card(code: str, tone: str, en: tuple[str, str], fr: tuple[str, str], evidence: dict[str, Any], samples: int) -> dict[str, Any]:
    return {
        "code": code,
        "tone": tone,
        "title_en": en[0],
        "text_en": en[1],
        "title_fr": fr[0],
        "text_fr": fr[1],
        "evidence": evidence,
        "evidence_level": _level(samples),
    }


def insight_cards(profile: dict[str, Any], situations: dict[str, Any], runs: dict[str, Any], trend_block: dict[str, Any], conceded_targets: dict[str, int]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    if profile["strengths"]:
        best = profile["strengths"][0]
        rate = best["success_rate"]
        cards.append(
            _card(
                "best_action",
                "strength",
                ("Your scoring action", f"{_action_label(best['action_code'], 'en')} lands {rate['numerator']} of {rate['denominator']} times ({_pct(rate['value'], 'en')}). Build phrases that end there."),
                ("Votre action qui marque", f"{_action_label(best['action_code'], 'fr')} : {rate['numerator']} touches sur {rate['denominator']} ({_pct(rate['value'], 'fr')}). Construisez vos phrases pour finir dessus."),
                {"metric": "action_success_rate", "action_code": best["action_code"], **rate},
                rate["denominator"],
            )
        )
    if profile["weaknesses"] and (not profile["strengths"] or profile["weaknesses"][0]["action_code"] != profile["strengths"][0]["action_code"]):
        worst = profile["weaknesses"][0]
        rate = worst["success_rate"]
        cards.append(
            _card(
                "weak_action",
                "weakness",
                ("An action that rarely scores", f"{_action_label(worst['action_code'], 'en')} succeeds {rate['numerator']} of {rate['denominator']} times ({_pct(rate['value'], 'en')}). Rehearse the finish or choose it less often."),
                ("Une action qui marque peu", f"{_action_label(worst['action_code'], 'fr')} : {rate['numerator']} réussites sur {rate['denominator']} ({_pct(rate['value'], 'fr')}). Travaillez la conclusion ou choisissez-la moins souvent."),
                {"metric": "action_success_rate", "action_code": worst["action_code"], **rate},
                rate["denominator"],
            )
        )

    trailing = situations["states"]["trailing"]["touch_share"]
    if trailing["denominator"] >= MIN_SAMPLES and trailing["value"] is not None:
        good = trailing["value"] >= 0.5
        cards.append(
            _card(
                "trailing",
                "strength" if good else "weakness",
                (
                    "When you are behind" if good else "Deficits grow",
                    f"Trailing, you win {trailing['numerator']} of {trailing['denominator']} exchanges ({_pct(trailing['value'], 'en')}). " + ("You come back." if good else "Slow the bout down and reset distance before the next action."),
                ),
                (
                    "Quand vous êtes mené" if good else "Les retards se creusent",
                    f"Mené, vous gagnez {trailing['numerator']} échanges sur {trailing['denominator']} ({_pct(trailing['value'], 'fr')}). " + ("Vous revenez." if good else "Ralentissez l'assaut et reprenez la distance avant l'action suivante."),
                ),
                {"metric": "trailing_touch_share", **trailing},
                trailing["denominator"],
            )
        )
    leading = situations["states"]["leading"]["touch_share"]
    if leading["denominator"] >= MIN_SAMPLES and leading["value"] is not None and leading["value"] < 0.45:
        cards.append(
            _card(
                "leading",
                "weakness",
                ("Leads slip away", f"With the lead, you win only {leading['numerator']} of {leading['denominator']} exchanges ({_pct(leading['value'], 'en')}). Keep the same actions that built the lead."),
                ("Les avances s'effritent", f"En tête, vous ne gagnez que {leading['numerator']} échanges sur {leading['denominator']} ({_pct(leading['value'], 'fr')}). Gardez les actions qui ont construit l'avance."),
                {"metric": "leading_touch_share", **leading},
                leading["denominator"],
            )
        )
    first = situations["first_touch_rate"]
    if first["denominator"] >= MIN_SAMPLES and first["value"] is not None:
        cards.append(
            _card(
                "first_touch",
                "strength" if first["value"] >= 0.5 else "neutral",
                ("First touch", f"You take the first touch in {first['numerator']} of {first['denominator']} bouts ({_pct(first['value'], 'en')})."),
                ("Première touche", f"Vous prenez la première touche dans {first['numerator']} assauts sur {first['denominator']} ({_pct(first['value'], 'fr')})."),
                {"metric": "first_touch_rate", **first},
                first["denominator"],
            )
        )

    against = runs.get("longest_run_against")
    if against and against["length"] >= 3:
        cards.append(
            _card(
                "run_against",
                "weakness",
                ("Runs against you", f"Your opponent scored {against['length']} touches in a row in one bout. Call a pause in rhythm after two conceded touches."),
                ("Séries subies", f"Un adversaire a marqué {against['length']} touches d'affilée dans un assaut. Cassez le rythme après deux touches concédées."),
                {"metric": "longest_run_against", "value": against["length"], "bout_id": against["bout_id"], "numerator": against["length"], "denominator": against["length"]},
                MIN_SAMPLES,
            )
        )
    if runs.get("comebacks", 0) >= 1:
        cards.append(
            _card(
                "comeback",
                "strength",
                ("Comebacks", f"You won {runs['comebacks']} bout(s) after trailing by two or more touches."),
                ("Retours", f"Vous avez gagné {runs['comebacks']} assaut(s) après avoir été mené de deux touches ou plus."),
                {"metric": "comebacks", "value": runs["comebacks"], "numerator": runs["comebacks"], "denominator": runs["bouts_won"] + runs["bouts_lost"]},
                runs["bouts_won"] + runs["bouts_lost"],
            )
        )

    known = sum(conceded_targets.values())
    if known >= MIN_SAMPLES and conceded_targets:
        area, count = max(conceded_targets.items(), key=lambda item: item[1])
        share = count / known
        if share >= 0.4:
            cards.append(
                _card(
                    "conceded_target",
                    "weakness",
                    ("Where you get hit", f"{count} of {known} conceded touches ({_pct(share, 'en')}) land on the {area.replace('_', ' ')}. Protect that line first."),
                    ("Où vous êtes touché", f"{count} touches concédées sur {known} ({_pct(share, 'fr')}) arrivent sur la zone « {area.replace('_', ' ')} ». Protégez cette ligne en priorité."),
                    {"metric": "conceded_target_share", "target_area": area, "value": share, "numerator": count, "denominator": known},
                    known,
                )
            )

    if trend_block.get("direction"):
        direction = trend_block["direction"]
        delta = trend_block["delta"]
        points = len(trend_block["points"])
        label_en = {"improving": "Trend: improving", "declining": "Trend: declining", "stable": "Trend: stable"}[direction]
        label_fr = {"improving": "Tendance : en progression", "declining": "Tendance : en recul", "stable": "Tendance : stable"}[direction]
        cards.append(
            _card(
                "trend",
                "strength" if direction == "improving" else "weakness" if direction == "declining" else "neutral",
                (label_en, f"Across {points} dated bouts, your touch share moved by {round(delta * 100):+d} points between the first and second half."),
                (label_fr, f"Sur {points} assauts datés, votre part de touches a bougé de {round(delta * 100):+d} points entre la première et la seconde moitié."),
                {"metric": "trend_delta", "value": delta, "numerator": points, "denominator": points},
                points,
            )
        )

    order = {"weakness": 0, "strength": 1, "neutral": 2}
    cards.sort(key=lambda card: (order[card["tone"]], -card["evidence"].get("denominator", 0)))
    return cards


# --------------------------------------------------------------------------- one bout


BOUT_ACTION_MIN = 3


def bout_reading(
    left_id: str | None,
    right_id: str | None,
    annotations: list[AnnotationView],
    touches: list[TouchView],
) -> dict[str, Any]:
    """Strengths and weaknesses of one bout, from validated marks only.

    A sentence describes this bout. It is not a season rate. Action cards
    wait for BOUT_ACTION_MIN attempts in the bout. Rates below MIN_SAMPLES
    stay phrased as a fraction of this bout, never as a stable tendency.
    """
    valid_touches = [item for item in touches if item.validated and item.valid]
    valid_annotations = [item for item in annotations if item.validated and item.athlete_id]
    if not valid_touches and not valid_annotations:
        return {
            "data_status": "no_validated_data",
            "formula_version": FORMULA_VERSION,
            "minimum_samples": MIN_SAMPLES,
            "left": None,
            "right": None,
        }
    video_ids = sorted({item.video_id for item in [*valid_touches, *valid_annotations] if getattr(item, "video_id", None)})
    return {
        "data_status": "ok",
        "formula_version": FORMULA_VERSION,
        "minimum_samples": MIN_SAMPLES,
        "basis": "validated_video" if video_ids else "validated_records",
        "video_ids": video_ids,
        "left": _fencer_bout(left_id, valid_annotations, valid_touches) if left_id else None,
        "right": _fencer_bout(right_id, valid_annotations, valid_touches) if right_id else None,
    }


def _fencer_bout(athlete_id: str, annotations: list[AnnotationView], touches: list[TouchView]) -> dict[str, Any]:
    mine = [item for item in touches if athlete_id in {item.scorer_id, item.receiver_id}]
    steps = _bout_sequences(athlete_id, mine)
    sequence = next(iter(steps.values()), [])
    runs = _runs(sequence) if sequence else {
        "longest_run_for": 0,
        "longest_run_against": 0,
        "lead_changes": 0,
        "max_deficit": 0,
        "final": {"own": 0, "opponent": 0},
        "result": "undecided",
        "comeback": False,
    }
    scored_targets: dict[str, int] = defaultdict(int)
    conceded_targets: dict[str, int] = defaultdict(int)
    for item in mine:
        if not item.target_area:
            continue
        if item.scorer_id == athlete_id:
            scored_targets[item.target_area] += 1
        elif item.receiver_id == athlete_id:
            conceded_targets[item.target_area] += 1
    actions: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "successes": 0})
    for item in annotations:
        if item.athlete_id != athlete_id:
            continue
        actions[item.action_code]["attempts"] += 1
        if item.outcome in SUCCESS_OUTCOMES:
            actions[item.action_code]["successes"] += 1
    cards = _bout_cards(runs, scored_targets, conceded_targets, actions)
    return {
        "athlete_id": athlete_id,
        "scored": runs["final"]["own"],
        "conceded": runs["final"]["opponent"],
        "result": runs["result"],
        "longest_run_for": runs["longest_run_for"],
        "longest_run_against": runs["longest_run_against"],
        "comeback": runs["comeback"],
        "cards": cards,
    }


def _bout_cards(runs: dict[str, Any], scored_targets: dict[str, int], conceded_targets: dict[str, int], actions: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    if runs["comeback"]:
        cards.append(
            _card(
                "bout_comeback",
                "strength",
                ("Comeback in this bout", f"You won after trailing by {runs['max_deficit']} touches."),
                ("Retour dans ce combat", f"Vous avez gagné après avoir été mené de {runs['max_deficit']} touches."),
                {"metric": "comeback", "value": runs["max_deficit"], "numerator": runs["max_deficit"], "denominator": runs["final"]["own"] + runs["final"]["opponent"]},
                runs["final"]["own"] + runs["final"]["opponent"],
            )
        )
    if runs["longest_run_for"] >= 2:
        length = runs["longest_run_for"]
        cards.append(
            _card(
                "bout_run_for",
                "strength",
                ("Scoring run", f"You scored {length} touches in a row in this bout."),
                ("Série pour vous", f"Vous avez marqué {length} touches d'affilée dans ce combat."),
                {"metric": "longest_run_for", "value": length, "numerator": length, "denominator": length},
                length,
            )
        )
    if runs["longest_run_against"] >= 2:
        length = runs["longest_run_against"]
        cards.append(
            _card(
                "bout_run_against",
                "weakness",
                ("Run against you", f"Your opponent scored {length} touches in a row in this bout."),
                ("Série subie", f"L'adversaire a marqué {length} touches d'affilée dans ce combat."),
                {"metric": "longest_run_against", "value": length, "numerator": length, "denominator": length},
                length,
            )
        )
    cards.extend(_target_card("scored", "strength", scored_targets))
    cards.extend(_target_card("conceded", "weakness", conceded_targets))
    ranked = [
        (code, counts["attempts"], counts["successes"], counts["successes"] / counts["attempts"])
        for code, counts in actions.items()
        if counts["attempts"] >= BOUT_ACTION_MIN
    ]
    strengths = sorted([row for row in ranked if row[3] >= 0.45], key=lambda row: (-row[3], -row[1]))
    weaknesses = sorted([row for row in ranked if row[3] < 0.35], key=lambda row: (row[3], -row[1]))
    if strengths:
        code, attempts, successes, rate = strengths[0]
        cards.append(
            _card(
                "bout_best_action",
                "strength",
                ("Action that scored here", f"In this bout, {_action_label(code, 'en')} landed {successes} of {attempts} times ({_pct(rate, 'en')})."),
                ("L'action qui a marqué ici", f"Dans ce combat, {_action_label(code, 'fr')} a marqué {successes} fois sur {attempts} ({_pct(rate, 'fr')})."),
                {"metric": "action_success_rate", "action_code": code, "value": rate, "numerator": successes, "denominator": attempts},
                attempts,
            )
        )
    if weaknesses and (not strengths or weaknesses[0][0] != strengths[0][0]):
        code, attempts, successes, rate = weaknesses[0]
        cards.append(
            _card(
                "bout_weak_action",
                "weakness",
                ("Action that missed here", f"In this bout, {_action_label(code, 'en')} landed {successes} of {attempts} times ({_pct(rate, 'en')})."),
                ("L'action qui n'a pas marqué ici", f"Dans ce combat, {_action_label(code, 'fr')} a marqué {successes} fois sur {attempts} ({_pct(rate, 'fr')})."),
                {"metric": "action_success_rate", "action_code": code, "value": rate, "numerator": successes, "denominator": attempts},
                attempts,
            )
        )
    order = {"weakness": 0, "strength": 1, "neutral": 2}
    cards.sort(key=lambda card: (order[card["tone"]], -card["evidence"].get("denominator", 0)))
    return cards


def _target_card(kind: str, tone: str, counts: dict[str, int]) -> list[dict[str, Any]]:
    known = sum(counts.values())
    if known < 2 or not counts:
        return []
    area, count = max(counts.items(), key=lambda item: item[1])
    share = count / known
    if share < 0.5:
        return []
    label = area.replace("_", " ")
    if kind == "conceded":
        return [
            _card(
                "bout_conceded_target",
                tone,
                ("Where you were hit in this bout", f"{count} of {known} conceded touches ({_pct(share, 'en')}) landed on the {label}."),
                ("Où vous avez été touché dans ce combat", f"{count} touches concédées sur {known} ({_pct(share, 'fr')}) sont arrivées sur « {label} »."),
                {"metric": "conceded_target_share", "target_area": area, "value": share, "numerator": count, "denominator": known},
                known,
            )
        ]
    return [
        _card(
            "bout_scored_target",
            tone,
            ("Where you scored in this bout", f"{count} of {known} touches you scored ({_pct(share, 'en')}) landed on the {label}."),
            ("Où vous avez marqué dans ce combat", f"{count} de vos touches sur {known} ({_pct(share, 'fr')}) sont arrivées sur « {label} »."),
            {"metric": "scored_target_share", "target_area": area, "value": share, "numerator": count, "denominator": known},
            known,
        )
    ]


# --------------------------------------------------------------------------- entry point


def athlete_intelligence(
    athlete_id: str,
    annotations: list[AnnotationView],
    touches: list[TouchView],
    scores: list[ScoreView],
    bouts: list[BoutView],
    weapon: str | None = None,
) -> dict[str, Any]:
    annotations = _filter_weapon(annotations, weapon)
    touches = _filter_weapon(touches, weapon)
    bouts = _filter_weapon(bouts, weapon)
    _ = scores
    any_validated = any(item.validated and item.athlete_id == athlete_id for item in annotations) or any(
        item.validated and item.valid and athlete_id in {item.scorer_id, item.receiver_id} for item in touches
    )
    if not any_validated:
        return {"athlete_id": athlete_id, "data_status": "no_validated_data", "weapon_filter": weapon, "formula_version": FORMULA_VERSION, "cards": []}
    profile = tactical_profile(athlete_id, annotations)
    situations = situation_split(athlete_id, touches)
    runs = momentum(athlete_id, touches, bouts)
    trend_block = trend(athlete_id, touches, bouts)
    conceded_targets: dict[str, int] = defaultdict(int)
    for item in touches:
        if item.validated and item.valid and item.receiver_id == athlete_id and item.target_area:
            conceded_targets[item.target_area] += 1
    return {
        "athlete_id": athlete_id,
        "data_status": "ok",
        "weapon_filter": weapon,
        "formula_version": FORMULA_VERSION,
        "minimum_samples": MIN_SAMPLES,
        "profile": profile,
        "situations": situations,
        "momentum": runs,
        "trend": trend_block,
        "opponents": opponents(athlete_id, touches, annotations),
        "cards": insight_cards(profile, situations, runs, trend_block, dict(conceded_targets)),
    }
