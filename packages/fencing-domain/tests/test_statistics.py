from fencing_domain.statistics import (
    AnnotationView,
    BoutView,
    ScoreView,
    TouchView,
    athlete_statistics,
    bout_statistics,
)


def _ann(**kwargs) -> AnnotationView:
    defaults = dict(
        id="a1",
        athlete_id="left",
        opponent_id="right",
        action_code="attack",
        outcome="no_touch",
        target_area=None,
        piste_position=0.4,
        validated=True,
        video_id="v1",
        bout_id="b1",
        start_ms=1000,
        weapon="epee",
    )
    defaults.update(kwargs)
    return AnnotationView(**defaults)


def _touch(**kwargs) -> TouchView:
    defaults = dict(
        id="t1",
        scorer_id="left",
        receiver_id="right",
        valid=True,
        validated=True,
        target_area="weapon_arm",
        timestamp_ms=2000,
        bout_id="b1",
        video_id="v1",
        weapon="epee",
    )
    defaults.update(kwargs)
    return TouchView(**defaults)


def test_empty_scope_is_not_a_zero_performance():
    stats = athlete_statistics("left", [], [], [], [])
    assert stats["data_status"] == "no_validated_data"
    assert stats["combined"]["offensive_success_rate"]["value"] is None
    assert stats["combined"]["offensive_success_rate"]["reason"] == "no_samples"
    assert stats["combined"]["touches_scored"] == 0


def test_rates_ignore_drafts_and_invalid_touches():
    stats = athlete_statistics(
        "left",
        [
            _ann(id="draft", validated=False, outcome="touch_for"),
            _ann(id="ok", outcome="touch_for"),
            _ann(id="miss", outcome="no_touch", start_ms=1500),
        ],
        [
            _touch(id="bad", valid=False),
            _touch(id="draft", validated=False),
            _touch(id="good"),
        ],
        [],
        [BoutView("b1", "epee", "2026-01-02", ("right",))],
    )
    block = stats["combined"]
    assert stats["data_status"] == "ok"
    assert block["offensive_attempts"] == 2
    assert block["offensive_success_rate"]["numerator"] == 1
    assert block["offensive_success_rate"]["value"] == 0.5
    assert block["touches_scored"] == 1
    assert block["touches_conceded"] == 0


def test_missing_rate_when_no_ripostes():
    stats = athlete_statistics("left", [_ann()], [_touch()], [], [])
    assert stats["combined"]["riposte_success_rate"]["value"] is None
    assert stats["combined"]["defensive_actions"] == 0


def test_riposte_and_counter_rates():
    annotations = [
        _ann(id=f"r{i}", action_code="riposte", outcome="touch_for" if i < 2 else "no_touch")
        for i in range(5)
    ]
    annotations.append(_ann(id="c1", action_code="counter_attack", outcome="touch_for"))
    stats = athlete_statistics("left", annotations, [], [], [])
    riposte = stats["combined"]["riposte_success_rate"]
    assert riposte["value"] == 0.4
    assert stats["combined"]["counter_attack_effectiveness"]["denominator"] == 1
    assert stats["combined"]["counter_attack_effectiveness"]["value"] == 1


def test_position_bins_and_missing_positions():
    annotations = [
        _ann(id="p1", piste_position=0.05),
        _ann(id="p2", piste_position=0.95, start_ms=2),
        _ann(id="p3", piste_position=None, start_ms=3),
    ]
    stats = athlete_statistics("left", annotations, [], [], [])
    bins = stats["combined"]["piste_position_distribution"]["bins"]
    assert bins[0]["count"] == 1
    assert bins[9]["count"] == 1
    assert stats["combined"]["piste_position_distribution"]["missing_position_count"] == 1


def test_opponent_and_time_do_not_invent_dates():
    touches = [
        _touch(id="s", scorer_id="left", receiver_id="right"),
        _touch(id="c", scorer_id="right", receiver_id="left", timestamp_ms=3000),
    ]
    bouts = [BoutView("b1", "epee", None, ("right",))]
    stats = athlete_statistics("left", [], touches, [], bouts)
    opponents = stats["combined"]["performance_by_opponent"]
    assert opponents == [
        {"opponent_id": "right", "touches_scored": 1, "touches_conceded": 1, "bouts": 1}
    ]
    assert stats["combined"]["performance_over_time"] == []
    assert stats["combined"]["undated_bout_count"] == 1


def test_weapons_are_not_silently_blended_in_by_weapon():
    annotations = [
        _ann(id="e", weapon="epee", outcome="touch_for"),
        _ann(id="f", weapon="foil", outcome="no_touch", start_ms=2),
    ]
    stats = athlete_statistics("left", annotations, [], [], [])
    assert stats["mixed_weapons"] is True
    assert stats["by_weapon"]["epee"]["offensive_success_rate"]["value"] == 1
    assert stats["by_weapon"]["foil"]["offensive_success_rate"]["value"] == 0


def test_bout_score_progression_uses_recorded_events_only():
    scores = [
        ScoreView(1000, "b1", "left", "right", 1, 0, "epee"),
        ScoreView(2000, "b1", "left", "right", 1, 1, "epee"),
    ]
    bout = BoutView("b1", "epee", "2026-04-01", ("right",))
    result = bout_statistics("left", "right", [], [_touch()], scores, bout)
    assert [item["left_score"] for item in result["score_progression"]] == [1, 1]
    assert result["left"]["touches_scored"] == 1
    assert result["right"]["touches_conceded"] == 1


def test_unknown_action_is_counted_in_frequency_but_not_as_an_attempt():
    stats = athlete_statistics("left", [_ann(action_code="not_a_real_action")], [], [], [])
    assert stats["combined"]["action_frequency"]["not_a_real_action"] == 1
    assert stats["combined"]["offensive_attempts"] == 0
    assert stats["combined"]["offensive_success_rate"]["value"] is None
