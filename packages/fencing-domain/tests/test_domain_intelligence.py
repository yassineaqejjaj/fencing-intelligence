from fencing_domain.intelligence import (
    MIN_SAMPLES,
    athlete_intelligence,
    bout_momentum,
    bout_reading,
    momentum,
    situation_split,
    tactical_profile,
    trend,
)
from fencing_domain.statistics import AnnotationView, BoutView, TouchView

ME = "me"
OPP = "opp"


def _touch(bout: str, step: int, scorer: str, target: str | None = "chest", **kwargs) -> TouchView:
    defaults = dict(
        id=f"{bout}-{step}",
        scorer_id=scorer,
        receiver_id=OPP if scorer == ME else ME,
        valid=True,
        validated=True,
        target_area=target,
        timestamp_ms=step * 1000,
        bout_id=bout,
        video_id=None,
        weapon="epee",
    )
    defaults.update(kwargs)
    return TouchView(**defaults)


def _sheet(bout: str, sequence: str) -> list[TouchView]:
    """'MMOOM' -> touches: M scored by me, O by the opponent."""
    return [_touch(bout, index + 1, ME if letter == "M" else OPP) for index, letter in enumerate(sequence)]


def _ann(code: str, outcome: str, index: int, **kwargs) -> AnnotationView:
    defaults = dict(
        id=f"a{index}",
        athlete_id=ME,
        opponent_id=OPP,
        action_code=code,
        outcome=outcome,
        target_area=None,
        piste_position=None,
        validated=True,
        video_id="v1",
        bout_id="b1",
        start_ms=index * 500,
        weapon="epee",
    )
    defaults.update(kwargs)
    return AnnotationView(**defaults)


def test_situation_split_uses_score_before_each_touch():
    touches = _sheet("b1", "MMOOO")  # 1-0, 2-0, 2-1, 2-2, 2-3
    split = situation_split(ME, touches)
    states = split["states"]
    # before touch 1: tied, I score. before 2: leading, I score. before 3 and 4: leading, conceded. before 5: tied, conceded.
    assert states["tied"] == {"scored": 1, "conceded": 1, "touch_share": {"value": 0.5, "numerator": 1, "denominator": 2, "reason": None}}
    assert states["leading"]["scored"] == 1 and states["leading"]["conceded"] == 2
    assert states["trailing"]["touch_share"]["value"] is None
    assert states["trailing"]["touch_share"]["reason"] == "no_samples"
    assert split["first_touch_rate"]["value"] == 1.0
    assert split["last_touch_rate"]["value"] == 0.0


def test_unvalidated_and_invalid_touches_are_ignored():
    touches = _sheet("b1", "MMM") + [_touch("b1", 9, OPP, validated=False), _touch("b1", 10, OPP, valid=False)]
    split = situation_split(ME, touches)
    assert sum(state["conceded"] for state in split["states"].values()) == 0


def test_momentum_runs_lead_changes_and_comeback():
    touches = _sheet("b1", "OOMMM")  # 0-2 then 3-2: comeback from a deficit of 2
    bouts = [BoutView("b1", "epee", "2026-09-01", (OPP,))]
    runs = momentum(ME, touches, bouts)
    bout = runs["bouts"][0]
    assert bout["longest_run_against"] == 2
    assert bout["longest_run_for"] == 3
    assert bout["lead_changes"] == 1
    assert bout["max_deficit"] == 2
    assert bout["result"] == "win" and bout["comeback"] is True
    assert runs["win_rate"]["value"] == 1.0
    assert runs["comebacks"] == 1


def test_momentum_without_decided_bouts_has_null_win_rate():
    runs = momentum(ME, _sheet("b1", "MO"), [])
    assert runs["bouts_undecided"] == 1
    assert runs["win_rate"]["value"] is None


def test_trend_requires_minimum_dated_bouts():
    touches = _sheet("b1", "MMO") + _sheet("b2", "MOO") + _sheet("b3", "MMM")
    bouts = [BoutView(f"b{i}", "epee", f"2026-09-0{i}", (OPP,)) for i in (1, 2, 3)]
    block = trend(ME, touches, bouts)
    assert block["direction"] is None
    assert block["reason"] == "insufficient_bouts"
    assert len(block["points"]) == 3


def test_trend_direction_and_undated_bouts():
    touches = _sheet("b1", "MOOO") + _sheet("b2", "MOO") + _sheet("b3", "MMMO") + _sheet("b4", "MMM") + _sheet("b5", "MM")
    bouts = [BoutView(f"b{i}", "epee", f"2026-09-0{i}", (OPP,)) for i in (1, 2, 3, 4)] + [BoutView("b5", "epee", None, (OPP,))]
    block = trend(ME, touches, bouts)
    assert block["direction"] == "improving"
    assert block["delta"] > 0
    assert block["undated_bouts"] == 1
    assert [point["bout_id"] for point in block["points"]] == ["b1", "b2", "b3", "b4"]


def test_tactical_profile_rates_and_thresholds():
    annotations = [_ann("attack", "touch_for" if i % 2 == 0 else "no_touch", i) for i in range(6)]  # 3/6
    annotations += [_ann("riposte", "touch_for", 10 + i) for i in range(2)]  # 2/2 but below MIN_SAMPLES
    annotations += [_ann("parry", "no_touch", 20 + i) for i in range(5)]  # 0/5 defensive
    annotations += [_ann("attack", "touch_for", 99, validated=False)]
    profile = tactical_profile(ME, annotations)
    assert profile["total_actions"] == 13
    assert profile["by_action"]["attack"]["success_rate"]["value"] == 0.5
    assert profile["by_category"]["offensive"]["attempts"] == 8
    assert profile["by_category"]["defensive"]["success_rate"]["value"] == 0.0
    codes = [row["action_code"] for row in profile["strengths"]]
    assert "riposte" not in codes, "two attempts is below the minimum sample"
    assert codes[0] == "attack"
    assert [row["action_code"] for row in profile["weaknesses"]] == ["parry"]


def test_low_success_action_is_not_called_a_strength():
    annotations = [_ann("attack", "touch_for" if i < 1 else "no_touch", i) for i in range(MIN_SAMPLES)]
    profile = tactical_profile(ME, annotations)
    assert profile["strengths"] == []
    assert profile["weaknesses"][0]["action_code"] == "attack"
    cards = athlete_intelligence(ME, annotations, [], [], [])["cards"]
    codes = {card["code"] for card in cards}
    assert "best_action" not in codes
    assert "weak_action" in codes


def test_cards_are_gated_by_sample_size_and_carry_evidence():
    small = athlete_intelligence(ME, [_ann("attack", "touch_for", 1)], _sheet("b1", "MO"), [], [])
    assert small["data_status"] == "ok"
    assert small["cards"] == []

    annotations = [_ann("attack", "touch_for" if i < 1 else "no_touch", i) for i in range(MIN_SAMPLES)]
    touches = _sheet("b1", "OOOOOMM", ) + _sheet("b2", "OOOM")
    touches = [
        _touch(t.bout_id or "", int(t.id.split("-")[1]), t.scorer_id, target="weapon_arm" if t.scorer_id == OPP else "chest")
        for t in touches
    ]
    full = athlete_intelligence(ME, annotations, touches, [], [BoutView("b1", "epee", "2026-09-01", (OPP,)), BoutView("b2", "epee", "2026-09-02", (OPP,))])
    codes = {card["code"] for card in full["cards"]}
    assert "weak_action" in codes
    assert "trailing" in codes
    assert "run_against" in codes
    assert "conceded_target" in codes
    assert "trend" not in codes
    for card in full["cards"]:
        assert card["text_fr"] and card["text_en"]
        assert "denominator" in card["evidence"]
        assert card["tone"] in {"strength", "weakness", "neutral"}
    trailing = next(card for card in full["cards"] if card["code"] == "trailing")
    assert trailing["evidence"]["numerator"] == 3 and trailing["evidence"]["denominator"] == 9
    assert "3 échanges sur 9" in trailing["text_fr"]


def test_no_validated_data_returns_no_blocks():
    result = athlete_intelligence(ME, [_ann("attack", "touch_for", 1, validated=False)], [], [], [])
    assert result["data_status"] == "no_validated_data"
    assert result["cards"] == []
    assert "profile" not in result


def test_weapon_filter_applies():
    touches = _sheet("b1", "MMMMM") + [_touch("b2", 1, OPP, weapon="foil")]
    result = athlete_intelligence(ME, [], touches, [], [], weapon="foil")
    assert result["situations"]["states"]["tied"]["conceded"] == 1
    assert sum(state["scored"] for state in result["situations"]["states"].values()) == 0


def test_bout_momentum_timeline():
    touches = _sheet("b1", "MOOM") + [_touch("b1", 7, "stranger")]
    block = bout_momentum(touches, ME, OPP)
    assert block["data_status"] == "ok"
    assert [(row["left"], row["right"]) for row in block["timeline"]][:4] == [(1, 0), (1, 1), (1, 2), (2, 2)]
    assert block["timeline"][2]["run_length"] == 2
    assert block["left"]["longest_run"] == 1
    assert block["right"]["longest_run"] == 2
    assert block["lead_changes"] == 1
    assert block["timeline"][4]["scorer"] == "unknown"
    assert bout_momentum([], ME, OPP)["data_status"] == "no_validated_data"


def test_bout_reading_names_strengths_and_weaknesses_of_one_fight():
    # Opponent scores twice, then I score five: a comeback and a run of five.
    touches = [
        _touch("b1", 1, OPP, target="weapon_arm"),
        _touch("b1", 2, OPP, target="weapon_arm"),
        *[_touch("b1", 3 + index, ME, target="chest") for index in range(5)],
    ]
    annotations = [_ann("riposte", "touch_for", index) for index in range(5)]
    annotations += [_ann("parry", "no_touch", 10 + index) for index in range(4)]
    reading = bout_reading(ME, OPP, annotations, touches)
    assert reading["data_status"] == "ok"
    assert reading["basis"] == "validated_video"
    mine = reading["left"]
    assert mine["result"] == "win" and mine["comeback"] is True
    codes = {card["code"] for card in mine["cards"]}
    assert {"bout_comeback", "bout_run_for", "bout_best_action", "bout_weak_action"} <= codes
    assert "bout_best_action" not in {card["code"] for card in reading["right"]["cards"]}
    conceded = next(card for card in reading["right"]["cards"] if card["code"] == "bout_conceded_target")
    assert "chest" in conceded["text_en"]
    assert bout_reading(ME, OPP, [], [])["data_status"] == "no_validated_data"
