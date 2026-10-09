from fencing_domain.competitions import (
    de_first_round,
    de_seed_positions,
    poule_groups,
    rank_standings,
    round_robin_pairs,
    StandingRow,
)


def test_poule_groups_snake_top_seeds_apart():
    groups = poule_groups([f"a{i}" for i in range(1, 13)], poule_size=6)
    assert len(groups) == 2
    assert all(len(group) == 6 for group in groups)
    assert "a1" in groups[0] and "a2" in groups[1]


def test_poule_groups_reject_empty_and_clamp_size():
    assert poule_groups([]) == []
    groups = poule_groups(["a", "b", "c"], poule_size=99)
    assert groups == [["a", "b", "c"]]


def test_round_robin_pairs_meet_once():
    pairs = round_robin_pairs(["a", "b", "c", "d"])
    assert len(pairs) == 6
    normalized = {tuple(sorted(pair)) for pair in pairs}
    assert len(normalized) == 6


def test_round_robin_pairs_odd_group():
    pairs = round_robin_pairs(["a", "b", "c"])
    assert len(pairs) == 3


def test_rank_standings_victories_then_indicator():
    rows = rank_standings(
        [
            StandingRow("a", 3, 2, 12, 9),
            StandingRow("b", 3, 2, 12, 6),
            StandingRow("c", 3, 3, 9, 9),
        ]
    )
    assert [row.athlete_id for row in rows] == ["c", "b", "a"]


def test_de_seed_positions_standard_table_of_8():
    assert de_seed_positions(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_de_first_round_byes_never_invent_athletes():
    bouts = de_first_round(["s1", "s2", "s3"], 4)
    assert len(bouts) == 2
    assert bouts[0][0] == "s1"
    assert bouts[0][1] is None
    flat = [slot for bout in bouts for slot in bout[:2]]
    assert "s4" not in flat and None in flat
