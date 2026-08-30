"""Ulfraerr — Barbarian 1 / Warlock 4 (The Undead), Pact of the Blade halberd
("Llerg's Rage"), Great Weapon Master, Savage Attacker.

Tactic (matches inbox/level5_damage_sim_sorcerer.py's `simulate_barblock`):
  Every round: one Attack-action attack with the halberd. Savage Attacker
  (roll damage twice, keep the better) applies once per turn.
  Great Weapon Master's Heavy Weapon Mastery (+3 damage) is optional and not
  baked into the sheet's listed damage, so it's added explicitly here for
  the Attack-action hit.
  Hew (GWM's bonus action): after a crit, one extra attack — modeled from
  round 2 on, since round 1's bonus action is spent entering Rage.
  Armor of Agathys (bonus action, 2nd-level pact slot): cast round 2, once
  Rage has freed up the bonus action. This is the character's one genuine
  early-round burst — see the note below on why it's modeled as a single
  flat proc rather than a per-round retaliation effect.

Cleave (halberd mastery) is ignored, matching the inbox script's own
convention: the simulation is single-target, and Cleave only ever hits a
*second* creature.

Note on Armor of Agathys: it grants 10 temp HP (2nd-level slot) and deals
10 cold damage to anything that hits Ulfraerr in melee while any of that
temp HP remains. That's retaliation damage — it depends on the *target's*
attacks against the player, which this engine never models (every policy
here only simulates the party's outgoing damage against a stationary
dummy). Modeling the barrier fully would mean inventing an enemy attack
pattern found nowhere else in this codebase. Instead this models exactly
one retaliation proc, added the round after casting (round 3), representing
"the first hit lands and the barrier answers once" — a deliberately
conservative single-shot approximation, not a simulation of the barrier's
full lifetime. Expect Ulfaerr's real early-round output to run a bit ahead
of this if he's actually being hit more than once while the 10 temp HP
lasts.

Note: the sheet's current weapon ("Llerg's Rage", a customized magic pact
weapon) carries a flat damage bonus of +7, one higher than the inbox
script's simplified Str+Rage+GWM static of +8 minus the GWM bonus (i.e. the
character has since picked up a magic weapon the original hand-tuned script
didn't model) — see data/characters/ulfaerr.json's validation.unresolved
for the exact breakdown ambiguity. Expect Ulfaerr's curve here to sit
slightly above the archived inbox numbers as a result, not a bug.
"""

import numpy as np

from ..character import load_character
from ..dice import attack_roll, roll_sum
from ..masteries import roll_damage

GWM_HEAVY_WEAPON_BONUS = 3
CRIT_MIN = 20
ARMOR_OF_AGATHYS_DAMAGE = 10  # 2nd-level slot: 5 base + 5 per slot level above 1st


def _savage_or_plain(rng, n, attack, crit, use_savage):
    plain = roll_damage(rng, n, attack, crit)
    savage = roll_damage(rng, n, attack, crit, savage_attacker=True)
    return np.where(use_savage, savage, plain)


def simulate(ac, n=100_000, rounds=10, seed=3000, target_save_bonus=None):
    char = load_character("ulfaerr")
    halberd = char.attack("llergs_rage")
    max_pact_slots = char.resource("pact_magic_slots").max
    pact_slots = np.full(n, max_pact_slots, dtype=np.int8)

    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    for rd in range(1, rounds + 1):
        savage_available = np.ones(n, dtype=bool)

        hit, crit, _ = attack_roll(rng, n, bonus=halberd.attack_bonus, ac=ac, advantage=False, crit_min=CRIT_MIN)
        use_savage = hit & savage_available
        savage_available &= ~use_savage

        dmg = np.where(hit, _savage_or_plain(rng, n, halberd, crit, use_savage) + GWM_HEAVY_WEAPON_BONUS, 0)
        total += dmg

        hew = crit & (rd > 1)
        if np.any(hew):
            hit2, crit2, _ = attack_roll(rng, n, bonus=halberd.attack_bonus, ac=ac, advantage=False, crit_min=CRIT_MIN)
            hit2 &= hew
            crit2 &= hew

            use_savage2 = hit2 & savage_available
            savage_available &= ~use_savage2

            # Hew is a bonus-action attack, not part of the Attack action,
            # so it doesn't get the optional GWM Heavy Weapon Mastery bonus.
            dmg2 = np.where(hit2, _savage_or_plain(rng, n, halberd, crit2, use_savage2), 0)
            total += dmg2

        if rd == 2:
            cast = pact_slots > 0
            pact_slots[cast] -= 1
        if rd == 3:
            total += np.where(pact_slots < max_pact_slots, ARMOR_OF_AGATHYS_DAMAGE, 0)

    return total
