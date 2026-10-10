"""Public FIE profile facts for a fencer the club chooses to link.

The snapshot keeps identity, ranking, medals, and head-to-head counts.
It does not store biography text, news, or images.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import httpx

from fencing_api.errors import AppError
from fencing_api.security import utcnow

FIE_API = "https://fie.org/api/fie"
FIE_PAGE = "https://fie.org/athletes/{fie_id}"
_HEADERS = {"accept": "application/json", "user-agent": "FencingIntelligence/0.1"}
_WEAPON = {"E": "epee", "F": "foil", "S": "sabre"}
_HAND = {"R": "right", "L": "left"}
_CATEGORY = {"S": "senior", "J": "u20", "C": "u17", "V": "veteran", "GV": "veteran"}
_MAX_BOUTS = 400
_ID_IN_URL = re.compile(r"athletes/(\d+)")


def parse_fie_id(fie_id: int | None, profile_url: str) -> int:
    if fie_id is not None:
        if fie_id < 1 or fie_id > 9_999_999:
            raise AppError("invalid_fie_id", 422, "That FIE id is not usable")
        return fie_id
    match = _ID_IN_URL.search(profile_url.strip())
    if match is None:
        raise AppError("invalid_fie_id", 422, "Paste a FIE athlete id or a fie.org/athletes/… link")
    return int(match.group(1))


def search_fencers(name: str) -> list[dict[str, Any]]:
    query = " ".join(name.split())
    if len(query) < 2:
        raise AppError("invalid_fie_query", 422, "Type at least two letters of the fencer's name")
    body = _get("/fencers-all", {"name": query, "page": 1, "pageSize": 10})
    items = body.get("items") if isinstance(body, dict) else None
    if not isinstance(items, list):
        raise AppError("fie_unavailable", 502, "The FIE profile service returned an unexpected list")
    return [_search_row(item) for item in items if isinstance(item, dict) and item.get("id")]


def fetch_snapshot(fie_id: int) -> dict[str, Any]:
    profile = _get(f"/fencer/{fie_id}")
    if not isinstance(profile, dict) or profile.get("id") != fie_id:
        raise AppError("fie_not_found", 404, "No FIE profile matches that id")
    opponents = _opponents(fie_id)
    return _snapshot(profile, opponents)


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        response = httpx.get(f"{FIE_API}{path}", params=params, headers=_HEADERS, timeout=20.0, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise AppError("fie_unavailable", 502, "The FIE profile service did not respond") from exc
    if response.status_code == 404:
        raise AppError("fie_not_found", 404, "No FIE profile matches that id")
    if response.status_code >= 400:
        raise AppError("fie_unavailable", 502, "The FIE profile service rejected the request")
    try:
        return response.json()
    except ValueError as exc:
        raise AppError("fie_unavailable", 502, "The FIE profile service returned an unexpected payload") from exc


def _opponents(fie_id: int) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    page = 1
    total = None
    while page <= 10:
        body = _get(f"/fencer/{fie_id}/opponents", {"page": page, "pageSize": 100})
        if not isinstance(body, dict):
            break
        items = body.get("items") if isinstance(body.get("items"), list) else []
        collected.extend(item for item in items if isinstance(item, dict))
        total = body.get("totalFound") if isinstance(body.get("totalFound"), int) else len(collected)
        if len(collected) >= total or not items:
            break
        page += 1
    return collected


def _snapshot(profile: dict[str, Any], opponents: list[dict[str, Any]]) -> dict[str, Any]:
    fie_id = int(profile["id"])
    weapon_code = str(profile.get("weapon") or "")
    category_code = str(profile.get("category") or "")
    hand_code = str(profile.get("hand") or "")
    birth = _date(profile.get("date"))
    ranking = [_ranking_row(row) for row in profile.get("ranking") or [] if isinstance(row, dict)]
    medals = [_medal_row(row) for row in profile.get("medals") or [] if isinstance(row, dict)]
    upcoming = [_event_row(row) for row in profile.get("futureCompetitions") or [] if isinstance(row, dict)]
    head_to_head, bouts, truncated = _head_to_head(fie_id, opponents)
    wins = sum(1 for bout in bouts if bout["won"])
    losses = sum(1 for bout in bouts if not bout["won"])
    return {
        "source": "fie",
        "source_url": FIE_PAGE.format(fie_id=fie_id),
        "fetched_at": utcnow().isoformat(),
        "note": "Public FIE record. These figures are not validated marks from this salle.",
        "fie_id": fie_id,
        "first_name": _text(profile.get("firstName")),
        "last_name": _text(profile.get("lastName")),
        "display_name": _person(profile.get("firstName"), profile.get("lastName")) or _text(profile.get("name")),
        "country": _text(profile.get("country")),
        "country_code": _text(profile.get("countryCode")),
        "gender": _text(profile.get("gender")),
        "weapon": _WEAPON.get(weapon_code),
        "weapon_code": weapon_code,
        "hand": _HAND.get(hand_code),
        "birth_date": birth.isoformat() if birth else None,
        "birth_year": birth.year if birth else None,
        "height_cm": profile.get("height") if isinstance(profile.get("height"), int) else None,
        "category": _CATEGORY.get(category_code, "unspecified"),
        "category_code": category_code,
        "license_number": _text(profile.get("licenseNumber"))[:40],
        "license_status": _text(profile.get("licenseStatus")),
        "rank": profile.get("rank") if isinstance(profile.get("rank"), int) else None,
        "points": _points(profile.get("points")),
        "season": profile.get("season") if isinstance(profile.get("season"), int) else None,
        "ranking": ranking,
        "medal_counts": {
            "olympic": _medal_counts(profile.get("olympicMedals")),
            "olympic_team": _medal_counts(profile.get("olympicTeamMedals")),
            "worlds": _medal_counts(profile.get("worldChampionshipMedals")),
            "worlds_team": _medal_counts(profile.get("worldChampionshipTeamMedals")),
        },
        "medals": medals,
        "upcoming": upcoming,
        "record": {"wins": wins, "losses": losses, "bouts": len(bouts), "opponents": len(head_to_head), "truncated": truncated},
        "opponents": head_to_head,
        "bouts": bouts,
    }


def _search_row(item: dict[str, Any]) -> dict[str, Any]:
    weapon_code = str(item.get("weapon") or "")
    return {
        "fie_id": int(item["id"]),
        "name": _person(item.get("firstName"), item.get("lastName")) or _text(item.get("name")),
        "country": _text(item.get("country")),
        "country_code": _text(item.get("countryCode")),
        "weapon": _WEAPON.get(weapon_code),
        "gender": _text(item.get("gender")),
        "rank": item.get("rank") if isinstance(item.get("rank"), int) else None,
        "points": _points(item.get("points")),
        "age": item.get("age") if isinstance(item.get("age"), int) else None,
        "source_url": FIE_PAGE.format(fie_id=int(item["id"])),
    }


def _head_to_head(fie_id: int, opponents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    bouts: list[dict[str, Any]] = []
    truncated = False
    for item in opponents:
        events = item.get("events") if isinstance(item.get("events"), list) else []
        parsed: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            bout = _bout(fie_id, item, event)
            if bout is None:
                continue
            if len(bouts) >= _MAX_BOUTS:
                truncated = True
                continue
            parsed.append(bout)
            bouts.append(bout)
        rows.append(
            {
                "fie_id": item.get("id") if isinstance(item.get("id"), int) else None,
                "name": _text(item.get("name")),
                "country": _text(item.get("nationality")),
                "wins": sum(1 for bout in parsed if bout["won"]),
                "losses": sum(1 for bout in parsed if not bout["won"]),
                "bouts": len(parsed),
            }
        )
    bouts.sort(key=lambda row: row.get("date") or "", reverse=True)
    return rows, bouts, truncated


def _bout(fie_id: int, opponent: dict[str, Any], event: dict[str, Any]) -> dict[str, Any] | None:
    left = event.get("fencer1") if isinstance(event.get("fencer1"), dict) else {}
    right = event.get("fencer2") if isinstance(event.get("fencer2"), dict) else {}
    if left.get("id") == fie_id:
        mine, theirs = left, right
    elif right.get("id") == fie_id:
        mine, theirs = right, left
    else:
        return None
    weapon_code = str(event.get("weapon") or "")
    return {
        "opponent_fie_id": opponent.get("id") if isinstance(opponent.get("id"), int) else None,
        "opponent": _text(opponent.get("name")),
        "opponent_country": _text(opponent.get("nationality")),
        "competition": _text(event.get("name")),
        "date": str(event.get("date") or "")[:10],
        "location": _text(event.get("location")),
        "country": _text(event.get("country")),
        "season": event.get("season") if isinstance(event.get("season"), int) else None,
        "weapon": _WEAPON.get(weapon_code),
        "for_score": mine.get("score") if isinstance(mine.get("score"), int) else None,
        "against_score": theirs.get("score") if isinstance(theirs.get("score"), int) else None,
        "won": bool(mine.get("isWinner")),
    }


def _ranking_row(row: dict[str, Any]) -> dict[str, Any]:
    weapon_code = str(row.get("weapon") or "")
    category_code = str(row.get("category") or "")
    return {
        "season": row.get("season") if isinstance(row.get("season"), int) else None,
        "weapon": _WEAPON.get(weapon_code),
        "category": _CATEGORY.get(category_code, "unspecified"),
        "rank": row.get("rank") if isinstance(row.get("rank"), int) else None,
        "points": _points(row.get("point") if "point" in row else row.get("points")),
    }


def _medal_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _text(row.get("competitionName")),
        "medal": _text(row.get("medal")),
        "location": _text(row.get("location")),
        "country": _text(row.get("country")),
        "date": _date(row.get("date")).isoformat() if _date(row.get("date")) else None,
        "season": row.get("season") if isinstance(row.get("season"), int) else None,
    }


def _event_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _text(row.get("name")),
        "city": _text(row.get("city")),
        "country": _text(row.get("country")),
        "kind": _text(row.get("type")),
        "start_date": _date(row.get("startDate")).isoformat() if _date(row.get("startDate")) else None,
        "end_date": _date(row.get("endDate")).isoformat() if _date(row.get("endDate")) else None,
    }


def _medal_counts(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    return {
        "gold": source.get("gold") if isinstance(source.get("gold"), int) else 0,
        "silver": source.get("silver") if isinstance(source.get("silver"), int) else 0,
        "bronze": source.get("bronze") if isinstance(source.get("bronze"), int) else 0,
    }


def _person(first: Any, last: Any) -> str:
    first_name = _name_part(_text(first))
    last_name = _name_part(_text(last))
    return f"{first_name} {last_name}".strip()


def _name_part(value: str) -> str:
    return " ".join(word[:1].upper() + word[1:].lower() for word in value.split() if word)


def _points(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
