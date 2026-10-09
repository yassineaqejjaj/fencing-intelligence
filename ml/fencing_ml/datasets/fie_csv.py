"""Read user-supplied FIE result CSV files.

This reader understands the column names published with the dataset. It does
not include or adapt the GPL-3.0 generator.
"""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path


WEAPON_MAP = {
    "epee": "epee",
    "épée": "epee",
    "epée": "epee",
    "foil": "foil",
    "fleuret": "foil",
    "sabre": "sabre",
    "saber": "sabre",
}


class ImportErrorReport(ValueError):
    pass


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _find(root: Path, needle: str) -> list[Path]:
    return sorted(path for path in root.rglob("*.csv") if needle in path.name.lower())


def _weapon(value: str) -> str:
    return WEAPON_MAP.get(value.strip().lower(), "")


def _date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _int(value: str) -> int | None:
    value = (value or "").strip()
    if value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def import_fie_csv_tree(root: Path) -> dict:
    if not root.is_dir():
        raise ImportErrorReport("FIE CSV directory does not exist")
    tournaments = _find(root, "tournament_data")
    bouts = _find(root, "bout_data")
    bios = _find(root, "fencer_bio") or _find(root, "bio_data")
    rankings = _find(root, "fencer_rankings") or _find(root, "rankings_data")
    if not tournaments and not bouts and not bios:
        raise ImportErrorReport(
            "No FIE CSV files found. Expected names containing tournament_data, bout_data, or fencer_bio."
        )

    competitions: dict[str, dict] = {}
    for path in tournaments:
        for row in _rows(path):
            external = str(row.get("competition_ID") or row.get("competition+ID") or row.get("tournament_ID") or "").strip()
            if not external:
                continue
            competitions[external] = {
                "external_id": external,
                "name": (row.get("name") or "").strip(),
                "country": (row.get("country") or "").strip(),
                "weapon": _weapon(row.get("weapon") or ""),
                "category": (row.get("category") or "").strip(),
                "gender": (row.get("gender") or "").strip(),
                "season": str(row.get("season") or "").strip(),
                "start_date": _date(row.get("start_date") or ""),
                "end_date": _date(row.get("end_date") or ""),
                "source_url": (row.get("url") or "").strip(),
                "source": "fie-csv",
            }

    athletes: dict[str, dict] = {}
    for path in bios:
        for row in _rows(path):
            external = str(row.get("id") or row.get("fencer_ID") or "").strip()
            if not external:
                continue
            athletes[external] = {
                "external_id": external,
                "display_name": (row.get("name") or "").strip(),
                "country": (row.get("country") or "").strip(),
                "dominant_hand": (row.get("hand") or "").strip().lower(),
                "source": "fie-csv",
            }

    historical = []
    seen: set[str] = set()
    duplicates = 0
    rejected = 0
    for path in bouts:
        for row in _rows(path):
            fencer = str(row.get("fencer_ID") or row.get("fencer_id") or "").strip()
            opponent = str(row.get("opp_ID") or row.get("opp_id") or "").strip()
            tournament = str(row.get("tournament_ID") or row.get("tournament_id") or "").strip()
            if not fencer or not opponent:
                rejected += 1
                continue
            fingerprint = hashlib.sha256(
                "|".join(
                    [
                        tournament,
                        fencer,
                        opponent,
                        str(row.get("fencer_score") or ""),
                        str(row.get("opp_score") or ""),
                        str(row.get("date") or ""),
                        str(row.get("pool_ID") or ""),
                    ]
                ).encode()
            ).hexdigest()
            if fingerprint in seen:
                duplicates += 1
                continue
            seen.add(fingerprint)
            historical.append(
                {
                    "fingerprint": fingerprint,
                    "tournament_external_id": tournament,
                    "fencer_external_id": fencer,
                    "opponent_external_id": opponent,
                    "fencer_score": _int(row.get("fencer_score") or ""),
                    "opponent_score": _int(row.get("opp_score") or ""),
                    "winner_external_id": str(row.get("winner_ID") or row.get("winner_id") or "").strip(),
                    "bout_date": _date(row.get("date") or ""),
                    "source": "fie-csv",
                    "payload": {
                        "upset": (row.get("upset") or "").strip(),
                        "pool_id": (row.get("pool_ID") or "").strip(),
                        "fencer_curr_pts": (row.get("fencer_curr_pts") or "").strip(),
                        "opp_curr_pts": (row.get("opp_curr_pts") or "").strip(),
                    },
                }
            )
            for external, score_key in ((fencer, "fencer_score"), (opponent, "opp_score")):
                athletes.setdefault(
                    external,
                    {"external_id": external, "display_name": "", "country": "", "dominant_hand": "", "source": "fie-csv"},
                )

    ranking_rows = 0
    for path in rankings:
        ranking_rows += len(_rows(path))

    return {
        "competitions": list(competitions.values()),
        "athletes": list(athletes.values()),
        "bouts": historical,
        "duplicate_bouts": duplicates,
        "rejected_bouts": rejected,
        "ranking_rows_seen": ranking_rows,
        "provenance": {
            "importer": "fencing-intelligence-fie-csv",
            "importer_license": "Apache-2.0",
            "upstream_repository": "https://github.com/amichaelsen/fie-fencing-dataset",
            "upstream_code_license": "GPL-3.0",
            "code_reused": False,
        },
    }
