"""Vectorized Monte Carlo dice primitives.

Every function operates on `n` independent trials at once via numpy arrays,
so a full combat round for `n=100_000` trials is a handful of array ops
rather than a Python loop. No character-specific logic lives here.
"""

import numpy as np


def attack_roll(rng, n, bonus, ac, advantage=False, crit_min=20):
    """Roll `n` attacks at once. Returns (hit, crit, natural_roll) arrays.

    `advantage` may be a scalar bool (applies to all trials) or a bool
    array of length `n` (per-trial, e.g. "advantage only for trials where
    Vex triggered last attack").
    """
    r1 = rng.integers(1, 21, size=n)

    if np.isscalar(advantage):
        if advantage:
            r2 = rng.integers(1, 21, size=n)
            nat = np.maximum(r1, r2)
        else:
            nat = r1
    else:
        advantage = np.asarray(advantage, dtype=bool)
        r2 = rng.integers(1, 21, size=n)
        nat = np.where(advantage, np.maximum(r1, r2), r1)

    crit = nat >= crit_min
    hit = crit | ((nat != 1) & (nat + bonus >= ac))
    return hit, crit, nat


def roll_sum(rng, n, sides, count):
    """Sum `count` dice of `sides` sides, independently for each of `n` trials."""
    if count == 0:
        return np.zeros(n, dtype=np.int16)

    return rng.integers(1, sides + 1, size=(n, count), dtype=np.int16).sum(axis=1)


def roll_best_of_two(rng, n, sides, count):
    """Savage Attacker / similar: roll a damage-dice bundle twice, keep the better sum."""
    a = roll_sum(rng, n, sides, count)
    b = roll_sum(rng, n, sides, count)
    return np.maximum(a, b)


def great_weapon_fighting(rng, n, sides, count):
    """2024 Great Weapon Fighting: any die showing 1 or 2 counts as 3 instead."""
    rolls = rng.integers(1, sides + 1, size=(n, count), dtype=np.int16)
    rolls = np.where(rolls <= 2, 3, rolls)
    return rolls.sum(axis=1)
