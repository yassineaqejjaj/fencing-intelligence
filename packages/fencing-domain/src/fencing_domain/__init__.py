"""Fencing domain rules that do not depend on the web framework or a database."""

from fencing_domain.recommendations import recommend
from fencing_domain.statistics import athlete_statistics, bout_statistics
from fencing_domain.taxonomy import ACTION_TYPES, RULE_SOURCES, action_by_code

__all__ = [
    "ACTION_TYPES",
    "RULE_SOURCES",
    "action_by_code",
    "athlete_statistics",
    "bout_statistics",
    "recommend",
]
