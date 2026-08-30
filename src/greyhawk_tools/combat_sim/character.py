"""Load a character JSON and expose the mechanical facts the sim engine needs.

Tactics (round-by-round choices, resource spend order) are NOT here — they
live in combat_sim/policies/. This module only surfaces what the sheet says:
attack bonuses, parsed damage dice, mastery tags, resource pools, and spell
slots. It never guesses at a tactic.
"""

import json
import re
from dataclasses import dataclass, field

from ..paths import CHARACTERS_DIR


@dataclass(frozen=True)
class Damage:
    """A parsed damage expression: `count`d`sides` + `flat`."""

    count: int
    sides: int
    flat: int

    @classmethod
    def parse(cls, text: str) -> "Damage":
        # Versatile/alternate-form weapons list a primary expression followed
        # by "(...)" or "/ ..." for the other form, e.g. "1d8+4 (one-handed)
        # / 1d10+4 (two-handed versatile)" — take the primary (first) form.
        text = re.split(r"[(/]", text, maxsplit=1)[0].strip()
        m = re.match(r"^(\d+)d(\d+)\s*([+-]\s*\d+)?$", text)
        if m:
            count, sides, flat = m.groups()
            return cls(int(count), int(sides), int(flat.replace(" ", "")) if flat else 0)
        m = re.match(r"^([+-]?\d+)$", text)
        if m:
            return cls(0, 0, int(m.group(1)))
        raise ValueError(f"Unparseable damage expression: {text!r}")

    def upcast(self, extra_dice: int) -> "Damage":
        """Add `extra_dice` more dice of the same size — the common "+1dX per
        slot level above the spell's base level" upcast rule."""
        return Damage(self.count + extra_dice, self.sides, self.flat)


@dataclass(frozen=True)
class Attack:
    id: str
    attack_bonus: int
    damage: Damage
    mastery: str | None = None
    type: str = "melee_weapon"
    trigger: str | None = None  # e.g. "bonus_action_two_weapon_fighting"


@dataclass(frozen=True)
class Spell:
    """A leveled, save-based damage spell (Thunderwave, Dissonant Whispers, ...).

    Attack-roll spells (Guiding Bolt, Ray of Frost, ...) don't need this —
    they're already loadable via `Character.attack()`, same as a weapon.
    """

    id: str
    min_level: int
    damage: Damage
    save: str
    save_dc: int
    half_on_save: bool = True
    upcast_extra_dice: int = 1  # extra damage dice per slot level above min_level

    def damage_at_slot(self, slot_level: int) -> Damage:
        return self.damage.upcast(self.upcast_extra_dice * max(0, slot_level - self.min_level))


@dataclass(frozen=True)
class Resource:
    id: str
    max: int
    unit: str
    recharge: str
    slot_level: int | None = None


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    short_name: str
    character_level: int
    proficiency_bonus: int
    attacks_per_action: int
    extra_attack: bool
    attacks: dict[str, Attack]
    damage_riders: dict[str, Damage]  # extra damage dice with no attack roll of their own, e.g. Sneak Attack
    spells: dict[str, Spell]  # leveled save-based damage spells
    resources: dict[str, Resource]
    spell_slots: dict[int, int]  # spell level -> max slots

    def attack(self, attack_id: str) -> Attack:
        try:
            return self.attacks[attack_id]
        except KeyError:
            raise KeyError(
                f"{self.name} has no attack {attack_id!r}; available: {sorted(self.attacks)}"
            ) from None

    def spell(self, spell_id: str) -> Spell:
        try:
            return self.spells[spell_id]
        except KeyError:
            raise KeyError(
                f"{self.name} has no spell {spell_id!r}; available: {sorted(self.spells)}"
            ) from None

    def damage_rider(self, rider_id: str) -> Damage:
        try:
            return self.damage_riders[rider_id]
        except KeyError:
            raise KeyError(
                f"{self.name} has no damage rider {rider_id!r}; available: {sorted(self.damage_riders)}"
            ) from None

    def resource(self, resource_id: str) -> Resource:
        try:
            return self.resources[resource_id]
        except KeyError:
            raise KeyError(
                f"{self.name} has no resource {resource_id!r}; available: {sorted(self.resources)}"
            ) from None


def load_character(character_id: str) -> Character:
    """Load `data/characters/<character_id>.json` and parse it for the sim engine."""
    path = CHARACTERS_DIR / f"{character_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No character file at {path}")

    with open(path) as f:
        data = json.load(f)

    identity = data["identity"]
    progression = data["progression"]
    actions = data.get("actions")
    if not actions or not actions.get("attacks"):
        raise ValueError(
            f"{identity.get('name', character_id)} has no actions.attacks — "
            "not a weapon-attack build this engine can drive"
        )

    attacks = {}
    damage_riders = {}
    for a in actions["attacks"]:
        try:
            damage = Damage.parse(a["damage"])
        except ValueError:
            # Spell/utility rows with non-numeric damage (e.g. buffs) aren't attacks.
            continue
        attack_bonus = a.get("attack_bonus")
        if attack_bonus is None:
            # No attack roll of its own (e.g. Sneak Attack, Channel Divinity
            # damage riders) — extra damage a policy adds to a landed hit,
            # not a standalone attack.
            damage_riders[a["id"]] = damage
            continue
        attacks[a["id"]] = Attack(
            id=a["id"],
            attack_bonus=attack_bonus,
            damage=damage,
            mastery=a.get("mastery"),
            type=a.get("type", "melee_weapon"),
            trigger=a.get("trigger"),
        )

    resources = {
        r["id"]: Resource(
            id=r["id"],
            max=r["max"],
            unit=r.get("unit", "uses"),
            recharge=r.get("recharge", "long_rest"),
            slot_level=r.get("slot_level"),
        )
        for r in data.get("resources", [])
    }

    spells = {}
    for s in data.get("spellcasting", {}).get("known_spells", []):
        if "damage" not in s or "save" not in s or "save_dc" not in s:
            # Attack-roll spells (already in actions.attacks) and
            # non-damage/utility spells aren't modeled here.
            continue
        try:
            damage = Damage.parse(s["damage"])
        except ValueError:
            continue
        spells[s["id"]] = Spell(
            id=s["id"],
            min_level=s["level"],
            damage=damage,
            save=s["save"],
            save_dc=s["save_dc"],
            half_on_save=s.get("half_on_save", True),
            upcast_extra_dice=s.get("upcast_extra_dice", 1),
        )

    slots_raw = data.get("spellcasting", {}).get("slots", {}) or {}
    spell_slots = {
        int(level): info["max"]
        for level, info in slots_raw.items()
        if level.isdigit() and isinstance(info, dict) and "max" in info
    }

    return Character(
        id=identity.get("id", character_id),
        name=identity["name"],
        short_name=identity.get("short_name") or identity["name"],
        character_level=progression["character_level"],
        proficiency_bonus=progression["proficiency_bonus"]["value"],
        attacks_per_action=actions.get("attacks_per_action", 1),
        extra_attack=bool(actions.get("extra_attack", False)),
        attacks=attacks,
        damage_riders=damage_riders,
        spells=spells,
        resources=resources,
        spell_slots=spell_slots,
    )
