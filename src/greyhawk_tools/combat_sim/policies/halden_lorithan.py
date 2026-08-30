"""Halden Lorithan — Cleric 5, Guiding Bolt while slots last, then mace.

Guiding Bolt is an attack-roll spell already captured in `actions.attacks`
(4d6, +7 to hit); the only new part is upcasting it with a higher-level
slot (+1d6 per slot level above 1st, PHB-2024 text). Casting a leveled
spell costs the Action, so this replaces the mace swing entirely on rounds
where a slot is spent — Halden doesn't get both. Slot spend order is
highest-first (same convention as the Paladins' smite spending); since the
decision to cast doesn't depend on a random outcome (only the damage roll
does), the cast order is precomputed once rather than tracked per-trial.

Spiritual Weapon (a bonus-action-cast, then free recurring bonus-action
attacker) would pair naturally with this, but combining two spells'
competing slot economy is more than this "default tactic" pass covers —
left as a documented future addition, not modeled here.
"""

import dataclasses

import numpy as np

from ..character import load_character
from ..dice import attack_roll
from ..masteries import roll_damage

CRIT_MIN = 20


def _cast_order(spell_slots):
    order = []
    for level in sorted(spell_slots, reverse=True):
        order.extend([level] * spell_slots[level])
    return order


def simulate(ac, n=100_000, rounds=10, seed=10000, target_save_bonus=None):
    char = load_character("halden_lorithan")
    mace = char.attack("mace")
    guiding_bolt = char.attack("guiding_bolt")
    cast_order = _cast_order(char.spell_slots)

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    for rd in range(rounds):
        if rd < len(cast_order):
            slot_level = cast_order[rd]
            spell = dataclasses.replace(guiding_bolt, damage=guiding_bolt.damage.upcast(slot_level - 1))
        else:
            spell = mace

        hit, crit, _ = attack_roll(rng, n, bonus=spell.attack_bonus, ac=ac, advantage=False, crit_min=CRIT_MIN)
        total += np.where(hit, roll_damage(rng, n, spell, crit), 0)

    return total
