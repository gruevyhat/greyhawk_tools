"""Burtha Smith — Fighter 4 (Champion) / Ranger 1, dual-wield shortsword + scimitar.

Tactic (matches inbox/level5_damage_sim_sorcerer.py's `simulate_fighter`):
  Round 1:    Bonus Action = Hunter's Mark (kept up via Concentration for the
              rest of the fight). Attack action = shortsword + scimitar
              (Nick folds the scimitar's extra Light attack into the Attack
              action). Action Surge = a second Attack action's shortsword.
  Rounds 2+:  Attack action = shortsword + scimitar (Nick). Bonus action =
              Enhanced Dual Wielding's extra shortsword attack.
  Vex (shortsword): a hit grants advantage on the *next* attack roll against
  the same target — modeled as advantage on the very next attack in sequence.
  Champion's Improved Critical: crit on a natural 19-20.

Fighter 4 has no Extra Attack (Fighter gets it at level 5); the JSON's
`extra_attack: false` confirms this, so every "Attack action" here is one
attack, matching the class table rather than being hardcoded.
"""

import numpy as np

from ..character import load_character
from ..dice import attack_roll, roll_sum
from ..masteries import roll_damage

CRIT_MIN = 19  # Champion: Improved Critical


def simulate(ac, n=100_000, rounds=10, seed=1000, target_save_bonus=None):
    char = load_character("burtha_smith")
    shortsword = char.attack("shortsword")
    scimitar = char.attack("scimitar")

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)
    vex_ready = np.zeros(n, dtype=bool)

    def hunters_mark(crit):
        base = roll_sum(rng, n, 6, 1)
        extra = roll_sum(rng, n, 6, 1)
        return base + np.where(crit, extra, 0)

    for _ in range(rounds):
        # Attack action (shortsword + Nick scimitar) plus either Action
        # Surge's extra Attack action (round 1) or the Enhanced Dual
        # Wielding bonus-action attack (rounds 2+) — both grant one more
        # shortsword swing, so the sequence is identical either way.
        for weapon in (shortsword, scimitar, shortsword):
            advantage = vex_ready.copy()
            vex_ready[:] = False

            hit, crit, _ = attack_roll(rng, n, bonus=weapon.attack_bonus, ac=ac, advantage=advantage, crit_min=CRIT_MIN)
            dmg = roll_damage(rng, n, weapon, crit) + hunters_mark(crit)
            total += np.where(hit, dmg, 0)

            if weapon is shortsword:
                vex_ready |= hit

    return total
