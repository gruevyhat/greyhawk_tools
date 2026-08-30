"""Talon Aldric — Paladin 5 (Oath of Glory), longsword & shield, Savage Attacker.

No reference implementation exists for this build. Default tactic: Extra
Attack (two longsword swings per Attack action), Savage Attacker applied
once per turn, spend Divine Smite on every landed hit while slots remain
(highest slot first).

The sheet also lists a greatsword, but `armor_class` (plate + shield, see
`data/characters/talon_aldric.json`) confirms a shield is equipped — a
two-handed greatsword can't be wielded alongside it, so the one-handed
longsword (mastery: Sap, no direct-damage rider) is the real weapon here,
not the higher-average-damage two-hander. See the `validation.flags` entry
`greatsword_incompatible_with_shield` on that sheet for the full note.

Slot counts come from `character.json`'s `spellcasting.slots` (derived from
the standard PHB-2024 Paladin table, since they weren't legible on the sheet).
"""

import numpy as np

from ..character import load_character
from ..dice import attack_roll, roll_sum
from ..masteries import roll_damage

CRIT_MIN = 20


def _smite_damage(rng, n, crit, dice_count):
    base = roll_sum(rng, n, 8, dice_count)
    extra = roll_sum(rng, n, 8, dice_count)
    return base + np.where(crit, extra, 0)


def simulate(ac, n=100_000, rounds=10, seed=8000, target_save_bonus=None):
    char = load_character("talon_aldric")
    longsword = char.attack("longsword")

    second_slots = np.full(n, char.spell_slots.get(2, 0), dtype=np.int8)
    first_slots = np.full(n, char.spell_slots.get(1, 0), dtype=np.int8)
    free_smite = np.full(n, char.resource("divine_smite_free_cast").max, dtype=np.int8)

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    for _ in range(rounds):
        savage_available = np.ones(n, dtype=bool)

        for _attack_index in range(2):  # Extra Attack
            hit, crit, _ = attack_roll(rng, n, bonus=longsword.attack_bonus, ac=ac, advantage=False, crit_min=CRIT_MIN)

            use_savage = hit & savage_available
            savage_available &= ~use_savage
            plain = roll_damage(rng, n, longsword, crit)
            savage = roll_damage(rng, n, longsword, crit, savage_attacker=True)
            weapon_damage = np.where(use_savage, savage, plain)

            # Sap (longsword's mastery) imposes disadvantage on the target's
            # next attack — no direct-damage term, so a miss simply deals 0.
            dmg = np.where(hit, weapon_damage, 0)

            can_smite = hit & ((second_slots > 0) | (first_slots > 0) | (free_smite > 0))
            use_second = can_smite & (second_slots > 0)
            if np.any(use_second):
                dmg += np.where(use_second, _smite_damage(rng, n, crit, 3), 0)
                second_slots[use_second] -= 1

            remaining = can_smite & ~use_second
            use_first = remaining & (first_slots > 0)
            if np.any(use_first):
                dmg += np.where(use_first, _smite_damage(rng, n, crit, 2), 0)
                first_slots[use_first] -= 1

            remaining = remaining & ~use_first
            use_free = remaining & (free_smite > 0)
            if np.any(use_free):
                dmg += np.where(use_free, _smite_damage(rng, n, crit, 2), 0)
                free_smite[use_free] -= 1

            total += dmg

    return total
