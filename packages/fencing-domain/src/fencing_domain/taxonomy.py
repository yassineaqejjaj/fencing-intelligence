"""Versioned fencing terminology.

Descriptions are original short labels for the product taxonomy. Official rule
text is not copied into this repository. Each entry records the public source
used to choose the term.
"""

from __future__ import annotations

from dataclasses import dataclass


RULE_SOURCES: tuple[dict[str, str], ...] = (
    {
        "id": "fie-rules",
        "title": "FIE Rules documents",
        "url": "https://fie.org/documents/rules",
        "version": "public-index",
        "note": "Terminology reference only. Rulebook text is not redistributed.",
    },
    {
        "id": "ffe-regulations",
        "title": "FFE competitor regulations index",
        "url": "https://www.ffescrime.fr/je-suis-en-club/competiteurs/reglements/",
        "version": "public-index",
        "note": "French federation index used as a second terminology reference.",
    },
)


@dataclass(frozen=True)
class ActionType:
    code: str
    category: str
    label_en: str
    label_fr: str
    weapons: tuple[str, ...] = ()
    experimental: bool = False
    counts_as_offensive_attempt: bool = False
    counts_as_defensive: bool = False
    riposte_family: bool = False
    counter_attack_family: bool = False


def _a(
    code: str,
    category: str,
    en: str,
    fr: str,
    *,
    weapons: tuple[str, ...] = (),
    experimental: bool = False,
    offensive: bool = False,
    defensive: bool = False,
    riposte: bool = False,
    counter: bool = False,
) -> ActionType:
    return ActionType(
        code=code,
        category=category,
        label_en=en,
        label_fr=fr,
        weapons=weapons,
        experimental=experimental,
        counts_as_offensive_attempt=offensive,
        counts_as_defensive=defensive,
        riposte_family=riposte,
        counter_attack_family=counter,
    )


ACTION_TYPES: tuple[ActionType, ...] = (
    _a("en_garde", "footwork", "En garde", "En garde"),
    _a("advance", "footwork", "Advance", "Marche"),
    _a("retreat", "footwork", "Retreat", "Retraite"),
    _a("lunge", "footwork", "Lunge", "Fente"),
    _a("fleche", "footwork", "Flèche", "Flèche"),
    _a("step_forward", "footwork", "Step forward", "Pas avant"),
    _a("step_backward", "footwork", "Step backward", "Pas arrière"),
    _a("jump_forward", "footwork", "Jump forward", "Bond avant"),
    _a("jump_back", "footwork", "Jump back", "Bond arrière"),
    _a("ballestra", "footwork", "Balestra", "Balestra"),
    _a("check_step", "footwork", "Check step", "Pas de contrôle"),
    _a("attack", "offensive", "Attack", "Attaque", offensive=True),
    _a("attack_simple", "offensive", "Simple attack", "Attaque simple", offensive=True),
    _a("attack_compound", "offensive", "Compound attack", "Attaque composée", offensive=True),
    _a(
        "attack_on_preparation",
        "offensive",
        "Attack on preparation",
        "Attaque sur la préparation",
        offensive=True,
    ),
    _a("beat_attack", "offensive", "Beat attack", "Attaque au battement", offensive=True),
    _a("disengage", "offensive", "Disengage", "Dégagement", offensive=True),
    _a("coupe", "offensive", "Coupé", "Coupé", offensive=True),
    _a("flick", "offensive", "Flick", "Coup lancé", offensive=True, experimental=True),
    _a("prise_de_fer", "offensive", "Prise de fer", "Prise de fer", offensive=True),
    _a("remise", "offensive", "Remise", "Remise", offensive=True, experimental=True),
    _a("reprise", "offensive", "Reprise", "Reprise", offensive=True, experimental=True),
    _a("riposte", "offensive", "Riposte", "Riposte", offensive=True, riposte=True),
    _a(
        "riposte_direct",
        "offensive",
        "Direct riposte",
        "Riposte directe",
        offensive=True,
        riposte=True,
    ),
    _a(
        "riposte_indirect",
        "offensive",
        "Indirect riposte",
        "Riposte indirecte",
        offensive=True,
        riposte=True,
    ),
    _a("parry", "defensive", "Parry", "Parade", defensive=True),
    _a("parry_prime", "defensive", "Prime", "Prime", defensive=True),
    _a("parry_seconde", "defensive", "Seconde", "Seconde", defensive=True),
    _a("parry_tierce", "defensive", "Tierce", "Tierce", defensive=True),
    _a("parry_quarte", "defensive", "Quarte", "Quarte", defensive=True),
    _a("parry_quinte", "defensive", "Quinte", "Quinte", defensive=True),
    _a("parry_sixte", "defensive", "Sixte", "Sixte", defensive=True),
    _a("parry_septime", "defensive", "Septime", "Septime", defensive=True),
    _a("parry_octave", "defensive", "Octave", "Octave", defensive=True),
    _a("circular_parry", "defensive", "Circular parry", "Parade circulaire", defensive=True),
    _a("opposition", "defensive", "Opposition", "Opposition", defensive=True),
    _a("counter_attack", "counter_offensive", "Counter-attack", "Contre-attaque", counter=True),
    _a("stop_hit", "counter_offensive", "Stop hit", "Coup d'arrêt", counter=True),
    _a(
        "counter_time",
        "counter_offensive",
        "Counter-time",
        "Contre-temps",
        counter=True,
        experimental=True,
    ),
    _a(
        "point_in_line",
        "counter_offensive",
        "Point in line",
        "Pointe en ligne",
        weapons=("foil", "sabre"),
        counter=True,
    ),
    _a("feint", "preparation", "Feint", "Feinte", experimental=True),
    _a("engagement", "preparation", "Engagement", "Engagement"),
    _a("change_engagement", "preparation", "Change of engagement", "Changement d'engagement"),
    _a("invitation", "preparation", "Invitation", "Invitation"),
    _a("beat", "preparation", "Beat", "Battement"),
    _a("preparation", "preparation", "Preparation", "Préparation"),
    _a("attack_priority", "priority", "Attack has priority", "Priorité à l'attaque", weapons=("foil", "sabre")),
    _a("riposte_priority", "priority", "Riposte has priority", "Priorité à la riposte", weapons=("foil", "sabre")),
    _a("simultaneous", "priority", "Simultaneous", "Simultané"),
)

ACTION_BY_CODE: dict[str, ActionType] = {item.code: item for item in ACTION_TYPES}

TARGET_AREAS: tuple[dict[str, str], ...] = (
    {"code": "mask", "label_en": "Mask", "label_fr": "Masque"},
    {"code": "chest", "label_en": "Chest", "label_fr": "Poitrine"},
    {"code": "flank", "label_en": "Flank", "label_fr": "Flanc"},
    {"code": "back", "label_en": "Back", "label_fr": "Dos"},
    {"code": "abdomen", "label_en": "Abdomen", "label_fr": "Abdomen"},
    {"code": "weapon_arm", "label_en": "Weapon arm", "label_fr": "Bras armé"},
    {"code": "rear_arm", "label_en": "Rear arm", "label_fr": "Bras arrière"},
    {"code": "weapon_hand", "label_en": "Weapon hand", "label_fr": "Main armée"},
    {"code": "front_thigh", "label_en": "Front thigh", "label_fr": "Cuisse avant"},
    {"code": "rear_thigh", "label_en": "Rear thigh", "label_fr": "Cuisse arrière"},
    {"code": "foot", "label_en": "Foot", "label_fr": "Pied"},
    {"code": "off_target", "label_en": "Off target", "label_fr": "Non valable"},
)

OUTCOMES: tuple[str, ...] = (
    "touch_for",
    "touch_against",
    "off_target",
    "no_touch",
    "halt",
    "simultaneous",
    "annulled",
)

WEAPONS: tuple[str, ...] = ("epee", "foil", "sabre")

# Areas that are generally valid target for each weapon. This is a coaching aid,
# not a referee decision. Unknown areas return None.
_FOIL_VALID = {"chest", "flank", "back", "abdomen"}
_SABRE_VALID = {"mask", "chest", "flank", "back", "abdomen", "weapon_arm", "rear_arm", "weapon_hand"}
_EPEE_OFF = {"off_target"}


def action_by_code(code: str) -> ActionType | None:
    return ACTION_BY_CODE.get(code)


def target_valid_for_weapon(weapon: str, target_area: str | None) -> bool | None:
    if target_area is None or weapon not in WEAPONS:
        return None
    if target_area == "off_target":
        return False
    if weapon == "epee":
        return target_area not in _EPEE_OFF
    if weapon == "foil":
        return target_area in _FOIL_VALID
    if weapon == "sabre":
        return target_area in _SABRE_VALID
    return None


SUCCESS_OUTCOMES = frozenset({"touch_for"})
