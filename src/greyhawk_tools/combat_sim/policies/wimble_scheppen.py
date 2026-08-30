"""Wimble Scheppen — Rogue 1 / Bard 4, Dissonant Whispers while slots last,
then "Whisper" (homebrew magic shortbow).

Dissonant Whispers is Wisdom-save damage (3d6 psychic, half on a success,
+1d6 per slot level above 1st). Casting it costs the Action, so it replaces
the weapon routine entirely on rounds where a slot is spent — no Vex
advantage and no Sneak Attack that round, since neither triggers off a
spell. Slots are spent highest-level first (same convention as the
Paladins' smite spending), precomputed since the decision to cast doesn't
depend on the save roll.

Once slots run dry, falls back to Whisper every round — the highest attack
bonus of Wimble's captured weapons (+7, vs. the rapier's +5). Vex grants
advantage on the *next* attack against the same target after a hit,
chained round to round the same way as the other Vex-mastery builds.
Sneak Attack (1d6 at Rogue 1) triggers once per turn on a hit made with
advantage, matching its actual condition ("Once per turn, added to a hit
with Advantage using a Finesse or Ranged weapon") — Whisper qualifies as
Ranged.

`target_save_bonus` is the flat bonus assumed for the target's saving
throw — see sweep.py's DEFAULT_TARGET_SAVE_BONUS for why this is a fixed
parameter rather than derived from AC.
"""

import numpy as np

from ..character import load_character
from ..dice import attack_roll, roll_sum
from ..masteries import roll_damage, save_damage

CRIT_MIN = 20


def _cast_order(spell_slots):
    order = []
    for level in sorted(spell_slots, reverse=True):
        order.extend([level] * spell_slots[level])
    return order


def simulate(ac, n=100_000, rounds=10, seed=12000, target_save_bonus=3):
    char = load_character("wimble_scheppen")
    whisper = char.attack("whisper")
    sneak_attack = char.damage_rider("sneak_attack")
    dissonant_whispers = char.spell("dissonant_whispers")
    cast_order = _cast_order(char.spell_slots)

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)
    vex_ready = np.zeros(n, dtype=bool)

    for rd in range(rounds):
        if rd < len(cast_order):
            slot_level = cast_order[rd]
            damage = dissonant_whispers.damage_at_slot(slot_level)
            total += save_damage(rng, n, damage, dissonant_whispers.save_dc, target_save_bonus, dissonant_whispers.half_on_save)
            continue

        advantage = vex_ready.copy()
        vex_ready[:] = False

        hit, crit, _ = attack_roll(rng, n, bonus=whisper.attack_bonus, ac=ac, advantage=advantage, crit_min=CRIT_MIN)
        dmg = roll_damage(rng, n, whisper, crit)

        sneak = hit & advantage
        sa = roll_sum(rng, n, sneak_attack.sides, sneak_attack.count)
        sa += np.where(crit, roll_sum(rng, n, sneak_attack.sides, sneak_attack.count), 0)
        dmg = dmg + np.where(sneak, sa, 0)

        total += np.where(hit, dmg, 0)
        vex_ready |= hit

    return total
