"""Shared, data-driven mechanics for weapon damage and 2024 Weapon Mastery riders.

Only riders that affect single-target DPR are modeled:

  graze  — on a miss, still deal damage equal to the ability modifier used
  vex    — on a hit, gain advantage on your next attack against the same
           target (this one is sequencing, not a damage roll — callers read
           `hit` and feed it as the next attack's `advantage`)

`cleave`, `push`, `slow`, `topple`, `sap`, `nick` don't change the wielder's
own single-target damage output (cleave hits a second creature, push/slow/
topple/sap impose control effects with no direct damage term, nick just
grants an extra attack that the policy already sequences explicitly) — this
mirrors the inbox script's own convention ("Cleave ignored because
simulation is single-target").
"""

import numpy as np

from .character import Attack, Damage
from .dice import great_weapon_fighting, roll_sum


def roll_damage(rng, n, attack: Attack, crit, savage_attacker=False, great_weapon_fighting_style=False):
    """Roll damage for a landed hit: base dice (+ crit extra dice) + flat bonus.

    Great Weapon Fighting and Savage Attacker stack (roll the GWF-adjusted
    dice twice, keep the higher sum) when both flags are set.
    """
    if attack.damage.count == 0:
        return np.full(n, attack.damage.flat, dtype=np.int32)

    def roll_base():
        if great_weapon_fighting_style:
            return great_weapon_fighting(rng, n, attack.damage.sides, attack.damage.count)
        return roll_sum(rng, n, attack.damage.sides, attack.damage.count)

    if savage_attacker:
        base = np.maximum(roll_base(), roll_base())
    else:
        base = roll_base()

    # Crit-extra dice are still weapon dice, so Great Weapon Fighting's
    # "1s and 2s reroll as 3s" applies to them too.
    if great_weapon_fighting_style:
        crit_extra = great_weapon_fighting(rng, n, attack.damage.sides, attack.damage.count)
    else:
        crit_extra = roll_sum(rng, n, attack.damage.sides, attack.damage.count)
    return base + np.where(crit, crit_extra, 0) + attack.damage.flat


def graze_damage_on_miss(n, hit, ability_mod):
    """Graze mastery: even on a miss, deal damage equal to the ability modifier."""
    return np.where(hit, 0, max(ability_mod, 0))


def save_damage(rng, n, damage: Damage, save_dc: int, target_save_bonus: int, half_on_save: bool = True):
    """Roll a target's saving throw against `save_dc` and return the damage dealt.

    No crit concept — saving throws don't crit. A natural 20 still only
    succeeds the save (it isn't an automatic negation of the spell), and a
    natural 1 still only fails it — 2024 saving throws don't have nat-1/20
    auto-fail/succeed rules the way attack rolls do, so this is a plain
    d20 + bonus vs. DC comparison.
    """
    roll = rng.integers(1, 21, size=n) + target_save_bonus
    saved = roll >= save_dc

    full = roll_sum(rng, n, damage.sides, damage.count) + damage.flat
    if half_on_save:
        return np.where(saved, full // 2, full)
    return np.where(saved, 0, full)
