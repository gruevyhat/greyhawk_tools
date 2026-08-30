"""Serethe "Se" Skarsdotr — Paladin 4 (Oath of Vengeance) / Sorcerer 1, greatsword.

Tactic (matches inbox/level5_damage_sim_sorcerer.py's `simulate_paladin`):
  Round 1:    Attack action establishes Vow of Enmity (advantage on this
              attack) against the target.
  Rounds 2+:  Booming Blade instead of a weapon attack — same attack roll,
              plus 1d8 thunder on the initial hit (character level 5).
  Great Weapon Fighting (feat): 1s and 2s on weapon damage dice reroll as 3.
  Graze (greatsword mastery): even on a miss, deal Strength-modifier damage.
  Every hit: spend one Divine Smite, highest-level slot first (2nd → 1st →
  the free 1st-level smite), consistent with the original script's resource
  strategy.

Paladin 4 has no Extra Attack (Paladin gets it at level 5); multiclass
caster level (Paladin 4 → 2, Sorcerer 1 → 1 → total 3) gives 4×1st + 2×2nd
slots, read from `spellcasting.slots` rather than hardcoded.
"""

import numpy as np

from ..character import load_character
from ..dice import attack_roll, roll_sum
from ..masteries import graze_damage_on_miss, roll_damage

STR_MOD = 4  # Strength +4 (17→18 with the level-4 ASI)
CRIT_MIN = 20


def _smite_damage(rng, n, crit, dice_count):
    base = roll_sum(rng, n, 8, dice_count)
    extra = roll_sum(rng, n, 8, dice_count)
    return base + np.where(crit, extra, 0)


def simulate(ac, n=100_000, rounds=10, seed=2000, target_save_bonus=None):
    char = load_character("serethe")
    greatsword = char.attack("greatsword")

    second_slots = np.full(n, char.spell_slots.get(2, 0), dtype=np.int8)
    first_slots = np.full(n, char.spell_slots.get(1, 0), dtype=np.int8)
    free_smite = np.full(n, char.resource("free_divine_smite").max, dtype=np.int8)

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    for rd in range(1, rounds + 1):
        # Round 1 establishes Vow of Enmity (advantage); it's assumed to
        # persist on this single target for the rest of the fight.
        hit, crit, _ = attack_roll(rng, n, bonus=greatsword.attack_bonus, ac=ac, advantage=True, crit_min=CRIT_MIN)

        weapon_damage = roll_damage(rng, n, greatsword, crit, great_weapon_fighting_style=True)
        dmg = np.where(hit, weapon_damage, graze_damage_on_miss(n, hit, STR_MOD))

        if rd > 1:
            # Booming Blade: +1d8 thunder on the initial hit (level 5 rider).
            bb = roll_sum(rng, n, 8, 1)
            bb += np.where(crit, roll_sum(rng, n, 8, 1), 0)
            dmg += np.where(hit, bb, 0)

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
