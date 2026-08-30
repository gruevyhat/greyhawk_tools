"""Finn Barrellor — Wizard 5, Magic Missile nova, Ray of Frost once slots run dry.

Magic Missile auto-hits (no attack roll, no save) for 3 darts of 1d4+1
force damage each, +1 dart per slot level above 1st — fixed PHB-2024 text,
not sheet data, so it's hardcoded here rather than modeled through
Character.spells (which is for save-based spells). Because it never
"wastes" a cast, slot consumption is deterministic and identical across
every trial, so the cast order (highest slot first, same convention as the
Paladins' smite spending) is precomputed once rather than tracked per-trial.

Once every slot (4x1st + 3x2nd + 2x3rd = 9 casts) is spent, Finn falls back
to Ray of Frost every remaining round.
"""

import numpy as np

from ..character import load_character
from ..dice import attack_roll, roll_sum
from ..masteries import roll_damage

CRIT_MIN = 20


def _magic_missile_damage(rng, n, slot_level):
    darts = slot_level + 2  # 3 darts at 1st level, +1 per level above
    return roll_sum(rng, n, 4, darts) + darts  # each dart is 1d4 + 1


def _cast_order(spell_slots):
    order = []
    for level in sorted(spell_slots, reverse=True):
        order.extend([level] * spell_slots[level])
    return order


def simulate(ac, n=100_000, rounds=10, seed=9000, target_save_bonus=None):
    char = load_character("finn_barrellor")
    ray_of_frost = char.attack("ray_of_frost")
    cast_order = _cast_order(char.spell_slots)

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    for rd in range(rounds):
        if rd < len(cast_order):
            total += _magic_missile_damage(rng, n, cast_order[rd])
            continue

        hit, crit, _ = attack_roll(rng, n, bonus=ray_of_frost.attack_bonus, ac=ac, advantage=False, crit_min=CRIT_MIN)
        total += np.where(hit, roll_damage(rng, n, ray_of_frost, crit), 0)

    return total
