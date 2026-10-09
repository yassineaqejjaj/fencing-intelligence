"""Poule sheets, standings, and direct-elimination draws.

Original implementations of standard fencing event structures. Ordering and
arithmetic are documented here; no federation rulebook text is copied.

Formulas (formula_version 1):
- Poule groups use snake distribution over the seed order, so the top seeds
  spread across groups instead of stacking in one.
- Round-robin pairs come from the circle method: every pair meets exactly once.
- Standings sort by victories, then indicator (scored minus conceded), then
  touches scored. A remaining tie breaks on athlete id only to stay
  deterministic; it is not an official tie-break and must not decide
  qualification on its own.
- A DE draw seeds the bracket 1v8, 4v5, 2v7, 3v6 (generalized to any
  power-of-two size). Missing seeds become byes, never invented athletes.
"""

from __future__ import annotations

from dataclasses import dataclass

FORMULA_VERSION = 1

CATEGORIES = {"u11", "u13", "u15", "u17", "u20", "senior", "veteran", "unspecified"}


def poule_groups(seed_order: list[str], poule_size: int = 6) -> list[list[str]]:
    """Split athletes into poule groups using snake distribution.

    seed_order is best seed first. poule_size is clamped to 2..8.
    """
    size = min(max(poule_size, 2), 8)
    athletes = [entry for entry in seed_order if entry]
    if not athletes:
        return []
    import math

    group_count = max(1, math.ceil(len(athletes) / size))
    groups: list[list[str]] = [[] for _ in range(group_count)]
    for round_index in range(math.ceil(len(athletes) / group_count)):
        for group_index in range(group_count):
            position = round_index * group_count + group_index
            if position >= len(athletes):
                break
            if round_index % 2 == 0:
                groups[group_index].append(athletes[position])
            else:
                groups[group_count - 1 - group_index].append(athletes[position])
    return [group for group in groups if group]


def round_robin_pairs(group: list[str]) -> list[tuple[str, str]]:
    """Every pair in the group meets exactly once (circle method)."""
    athletes = [entry for entry in group if entry]
    if len(athletes) < 2:
        return []
    rotating = list(athletes)
    if len(rotating) % 2 == 1:
        rotating.append("")
    pairs: list[tuple[str, str]] = []
    rounds = len(rotating) - 1
    half = len(rotating) // 2
    for _ in range(rounds):
        for index in range(half):
            left = rotating[index]
            right = rotating[-(index + 1)]
            if left and right:
                pairs.append((left, right))
        rotating = [rotating[0], rotating[-1], *rotating[1:-1]]
    return pairs


@dataclass(frozen=True)
class StandingRow:
    athlete_id: str
    bouts: int
    victories: int
    scored: int
    conceded: int

    @property
    def indicator(self) -> int:
        return self.scored - self.conceded


def rank_standings(rows: list[StandingRow]) -> list[StandingRow]:
    """Sort by victories, indicator, scored. Id tiebreak is arbitrary."""
    return sorted(rows, key=lambda row: (-row.victories, -row.indicator, -row.scored, row.athlete_id))


def de_seed_positions(size: int) -> list[int]:
    """Bracket slot order for seeds 1..size (size must be a power of two)."""
    if size < 2 or (size & (size - 1)) != 0:
        raise ValueError("DE size must be a power of two of at least 2")
    positions = [1]
    while len(positions) < size:
        doubled = []
        for seed in positions:
            doubled.append(seed)
            doubled.append(len(positions) * 2 + 1 - seed)
        positions = doubled
    return positions


def de_first_round(seed_order: list[str], size: int) -> list[tuple[str | None, str | None, str]]:
    """Pair seeds into first-round DE bouts. Missing seeds are byes (None)."""
    order = de_seed_positions(size)
    seeds: list[str | None] = [seed_order[seed - 1] if seed - 1 < len(seed_order) else None for seed in order]
    bouts = []
    round_name = {2: "Final", 4: "Semi-final", 8: "Quarter-final"}.get(size, f"Table of {size}")
    for index in range(0, len(seeds), 2):
        left, right = seeds[index], seeds[index + 1]
        if left is None and right is None:
            continue
        bouts.append((left, right, f"{round_name} · match {index // 2 + 1}"))
    return bouts
