"""Evidence-grounded coaching suggestions.

Every recommendation is derived from validated statistics. The module never
fills missing rates and never emits a drill when the supporting sample is
below the minimum.
"""

from __future__ import annotations

from typing import Any


MIN_SAMPLES = 5

EXERCISES: tuple[dict[str, Any], ...] = (
    {
        "code": "attack_line_and_finish",
        "name_en": "Attack line and finish",
        "name_fr": "Ligne d'attaque et conclusion",
        "weapons": ["epee", "foil", "sabre"],
        "duration_minutes": 15,
        "description_en": "From a measured advance, hit a hand-sized target on the coach's cue. Record only touches that land in the chosen area.",
        "description_fr": "Depuis une marche mesurée, toucher une cible de la taille d'une main au signal du maître. Ne compter que les touches dans la zone choisie.",
    },
    {
        "code": "parry_riposte_quarte",
        "name_en": "Quarte parry-riposte",
        "name_fr": "Parade-riposte de quarte",
        "weapons": ["epee", "foil", "sabre"],
        "duration_minutes": 12,
        "description_en": "Coach gives a direct attack. Parry quarte and riposte to a named target. Separate successful ripostes from late ones.",
        "description_fr": "Le maître donne une attaque directe. Parer de quarte et riposter vers une cible nommée. Séparer les ripostes réussies des ripostes tardives.",
    },
    {
        "code": "counter_time_choice",
        "name_en": "Counter-attack decision",
        "name_fr": "Choix de contre-attaque",
        "weapons": ["epee", "foil", "sabre"],
        "duration_minutes": 12,
        "description_en": "Alternate between a prepared attack and a counter-attack. Keep the counter-attacks that land before the opponent's hit, and discard the rest.",
        "description_fr": "Alterner attaque préparée et contre-attaque. Garder les contre-attaques qui arrivent avant la touche adverse.",
    },
    {
        "code": "distance_advance_retreat",
        "name_en": "Advance-retreat distance",
        "name_fr": "Distance marche-retraite",
        "weapons": ["epee", "foil", "sabre"],
        "duration_minutes": 10,
        "description_en": "Keep stepping distance for one minute, then attack only from the distance marked on the piste. No scoring claim is made from this drill alone.",
        "description_fr": "Conserver la distance de pas pendant une minute, puis attaquer seulement depuis la distance marquée sur la piste.",
    },
    {
        "code": "target_recovery",
        "name_en": "Target-area recovery",
        "name_fr": "Récupération par zone",
        "weapons": ["epee", "foil", "sabre"],
        "duration_minutes": 10,
        "description_en": "Defend the body area that conceded the most validated touches. The coach names that area before the bout drill starts.",
        "description_fr": "Défendre la zone qui a concédé le plus de touches validées. Le maître nomme la zone avant le thème.",
    },
)


def _level(samples: int) -> str:
    if samples >= 20:
        return "high"
    if samples >= 10:
        return "moderate"
    return "low"


def _exercise(code: str) -> dict[str, Any]:
    for item in EXERCISES:
        if item["code"] == code:
            return item
    raise KeyError(code)


def recommend(stats: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    """Build recommendations from an athlete statistics payload.

    `stats` is the dict returned by `athlete_statistics`. Suggestions use the
    combined block only when weapons are not mixed. Mixed weapons are reported
    per weapon so foil priority results are not blended with épée.
    """
    if stats.get("data_status") != "ok":
        return []

    blocks: list[tuple[str | None, dict[str, Any]]] = []
    if stats.get("mixed_weapons"):
        for weapon, block in stats.get("by_weapon", {}).items():
            blocks.append((weapon, block))
    else:
        weapon = stats.get("weapon_filter")
        present = stats.get("weapons_present") or []
        if weapon is None and len(present) == 1:
            weapon = present[0]
        blocks.append((weapon, stats.get("combined") or {}))

    suggestions: list[dict[str, Any]] = []
    for weapon, block in blocks:
        offensive = block.get("offensive_success_rate") or {}
        riposte = block.get("riposte_success_rate") or {}
        counter = block.get("counter_attack_effectiveness") or {}

        if offensive.get("value") is not None and offensive["denominator"] >= MIN_SAMPLES and offensive["value"] < 0.35:
            exercise = _exercise("attack_line_and_finish")
            samples = int(offensive["denominator"])
            suggestions.append(
                {
                    "observation": "Validated offensive actions are producing few touches.",
                    "observation_fr": "Les actions offensives validées produisent peu de touches.",
                    "evidence": {
                        "metric": "offensive_success_rate",
                        "value": offensive["value"],
                        "numerator": offensive["numerator"],
                        "denominator": samples,
                        "weapon": weapon,
                    },
                    "video_references": [],
                    "exercise_code": exercise["code"],
                    "exercise": exercise,
                    "evidence_level": _level(samples),
                    "weapon": weapon,
                }
            )

        if riposte.get("value") is not None and riposte["denominator"] >= MIN_SAMPLES and riposte["value"] < 0.4:
            exercise = _exercise("parry_riposte_quarte")
            samples = int(riposte["denominator"])
            suggestions.append(
                {
                    "observation": "Validated ripostes are rarely finishing in a touch.",
                    "observation_fr": "Les ripostes validées se concluent rarement par une touche.",
                    "evidence": {
                        "metric": "riposte_success_rate",
                        "value": riposte["value"],
                        "numerator": riposte["numerator"],
                        "denominator": samples,
                        "weapon": weapon,
                    },
                    "video_references": [],
                    "exercise_code": exercise["code"],
                    "exercise": exercise,
                    "evidence_level": _level(samples),
                    "weapon": weapon,
                }
            )

        if counter.get("value") is not None and counter["denominator"] >= MIN_SAMPLES and counter["value"] < 0.3:
            exercise = _exercise("counter_time_choice")
            samples = int(counter["denominator"])
            suggestions.append(
                {
                    "observation": "Validated counter-attacks are seldom the scoring action.",
                    "observation_fr": "Les contre-attaques validées marquent rarement.",
                    "evidence": {
                        "metric": "counter_attack_effectiveness",
                        "value": counter["value"],
                        "numerator": counter["numerator"],
                        "denominator": samples,
                        "weapon": weapon,
                    },
                    "video_references": [],
                    "exercise_code": exercise["code"],
                    "exercise": exercise,
                    "evidence_level": _level(samples),
                    "weapon": weapon,
                }
            )

        conceded_targets = (block.get("conceded_target_distribution") or {}).get("counts") or {}
        conceded_known = sum(conceded_targets.values())
        if conceded_known >= MIN_SAMPLES and conceded_targets:
            top_area, top_count = max(conceded_targets.items(), key=lambda item: item[1])
            if top_count / conceded_known >= 0.4:
                exercise = _exercise("target_recovery")
                suggestions.append(
                    {
                        "observation": "A single target area accounts for many conceded touches.",
                        "observation_fr": "Une seule zone concentre une grande part des touches concédées.",
                        "evidence": {
                            "metric": "conceded_target_distribution",
                            "target_area": top_area,
                            "count": top_count,
                            "denominator": conceded_known,
                            "value": top_count / conceded_known,
                            "numerator": top_count,
                            "weapon": weapon,
                        },
                        "video_references": [],
                        "exercise_code": exercise["code"],
                        "exercise": exercise,
                        "evidence_level": _level(conceded_known),
                        "weapon": weapon,
                    }
                )

    suggestions.sort(key=lambda item: item["evidence"]["denominator"], reverse=True)
    return suggestions[:limit]


def attach_video_references(suggestions: list[dict[str, Any]], annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add video pointers that match the metric. Annotations must already be validated."""
    metric_codes = {
        "offensive_success_rate": {"attack", "attack_simple", "attack_compound", "beat_attack", "disengage", "riposte", "riposte_direct", "riposte_indirect", "remise", "reprise", "flick", "coupe", "prise_de_fer", "attack_on_preparation"},
        "riposte_success_rate": {"riposte", "riposte_direct", "riposte_indirect"},
        "counter_attack_effectiveness": {"counter_attack", "stop_hit", "counter_time", "point_in_line"},
    }
    for suggestion in suggestions:
        metric = suggestion["evidence"]["metric"]
        codes = metric_codes.get(metric, set())
        weapon = suggestion.get("weapon")
        refs = []
        for item in annotations:
            if not item.get("validated"):
                continue
            if item.get("action_code") not in codes:
                continue
            if weapon and item.get("weapon") not in {None, weapon}:
                continue
            if item.get("outcome") == "touch_for":
                continue
            if item.get("video_id"):
                refs.append(
                    {
                        "video_id": item["video_id"],
                        "annotation_id": item.get("id"),
                        "start_ms": item.get("start_ms"),
                    }
                )
            if len(refs) >= 5:
                break
        suggestion["video_references"] = refs
    return suggestions
