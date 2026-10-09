from fencing_domain.recommendations import attach_video_references, recommend
from fencing_domain.statistics import AnnotationView, athlete_statistics


def _stats_from_attacks(successes: int, attempts: int):
    annotations = []
    for index in range(attempts):
        annotations.append(
            AnnotationView(
                id=f"a{index}",
                athlete_id="left",
                opponent_id="right",
                action_code="attack",
                outcome="touch_for" if index < successes else "no_touch",
                target_area=None,
                piste_position=None,
                validated=True,
                video_id="video-1",
                bout_id="bout-1",
                start_ms=index,
                weapon="epee",
            )
        )
    return athlete_statistics("left", annotations, [], [], []), annotations


def test_no_recommendation_without_validated_data():
    stats = athlete_statistics("left", [], [], [], [])
    assert recommend(stats) == []


def test_no_recommendation_below_sample_minimum():
    stats, _ = _stats_from_attacks(0, 4)
    assert recommend(stats) == []


def test_low_offensive_rate_cites_the_measured_rate():
    stats, annotations = _stats_from_attacks(1, 8)
    suggestions = recommend(stats)
    assert len(suggestions) == 1
    evidence = suggestions[0]["evidence"]
    assert evidence["metric"] == "offensive_success_rate"
    assert evidence["numerator"] == 1
    assert evidence["denominator"] == 8
    assert evidence["value"] == 0.125
    assert suggestions[0]["evidence_level"] == "low"
    payload = [
        {
            "id": item.id,
            "validated": item.validated,
            "action_code": item.action_code,
            "outcome": item.outcome,
            "weapon": item.weapon,
            "video_id": item.video_id,
            "start_ms": item.start_ms,
        }
        for item in annotations
    ]
    attach_video_references(suggestions, payload)
    assert suggestions[0]["video_references"]
    assert all(ref["video_id"] == "video-1" for ref in suggestions[0]["video_references"])


def test_successful_offense_does_not_invent_a_drill():
    stats, _ = _stats_from_attacks(6, 8)
    assert recommend(stats) == []
