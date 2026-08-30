"""Eddwarn Celas — Druid 4 / Rogue 1, Thunderwave while slots last, then Starry Wisp.

Thunderwave is Constitution-save damage (2d8, half on a success, +1d8 per
slot level above 1st — PHB-2024 text, filled into the JSON since it wasn't
on the sheet). Casting it costs the Action, so it replaces Starry Wisp
entirely on rounds where a slot is spent, spent highest-level first (same
convention as the Paladins' smite spending); the cast order is precomputed
since the decision to cast doesn't depend on the save roll.

`target_save_bonus` is the flat bonus assumed for the target's saving
throw — see sweep.py's DEFAULT_TARGET_SAVE_BONUS for why this is a fixed
parameter rather than derived from AC.
"""

import numpy as np

from ..character import load_character
from ..dice import attack_roll
from ..masteries import roll_damage, save_damage

CRIT_MIN = 20


def _cast_order(spell_slots):
    order = []
    for level in sorted(spell_slots, reverse=True):
        order.extend([level] * spell_slots[level])
    return order


def simulate(ac, n=100_000, rounds=10, seed=11000, target_save_bonus=3):
    char = load_character("eddwarn_celas")
    starry_wisp = char.attack("starry_wisp")
    thunderwave = char.spell("thunderwave")
    cast_order = _cast_order(char.spell_slots)

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    for rd in range(rounds):
        if rd < len(cast_order):
            slot_level = cast_order[rd]
            damage = thunderwave.damage_at_slot(slot_level)
            total += save_damage(rng, n, damage, thunderwave.save_dc, target_save_bonus, thunderwave.half_on_save)
            continue

        hit, crit, _ = attack_roll(rng, n, bonus=starry_wisp.attack_bonus, ac=ac, advantage=False, crit_min=CRIT_MIN)
        total += np.where(hit, roll_damage(rng, n, starry_wisp, crit), 0)

    return total
