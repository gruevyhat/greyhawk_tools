import numpy as np

# ============================================================
# CORE DICE / ATTACK FUNCTIONS
# ============================================================

def attack_roll(rng, n, bonus, ac, advantage=False, crit_min=20):
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
    if count == 0:
        return np.zeros(n, dtype=np.int16)

    return rng.integers(
        1, sides + 1, size=(n, count), dtype=np.int16
    ).sum(axis=1)


# ============================================================
# FIGHTER 4 / RANGER 1
#
# Champion
# Dex 18
# Shortsword + Scimitar
# Two-Weapon Fighting
# Dual Wielder
# Hunter's Mark
# Action Surge
# Shortsword = Vex
# Scimitar = Nick
# Crit 19-20
#
# Fighter 4 has NO Extra Attack.
# ============================================================

def fighter_attack_damage(rng, n, hit, crit, static=4):
    # 1d6 weapon + 1d6 Hunter's Mark + Dex
    base = roll_sum(rng, n, 6, 2)
    crit_extra = roll_sum(rng, n, 6, 2)

    dmg = base + np.where(crit, crit_extra, 0) + static
    return np.where(hit, dmg, 0)


def simulate_fighter(
    ac,
    n=100_000,
    rounds=10,
    seed=1,
    dual_wielder_add_mod=True
):
    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    vex_ready = np.zeros(n, dtype=bool)

    for rd in range(1, rounds + 1):
        if rd == 1:
            # Bonus Action = Hunter's Mark.
            #
            # Attack action:
            #   Shortsword
            #   Scimitar via Nick
            #
            # Action Surge:
            #   Shortsword
            #
            # Nick can provide its extra Light attack only once/turn.
            attacks = [
                ("shortsword", False),
                ("scimitar", False),
                ("shortsword", False),
            ]
        else:
            # Attack action:
            #   Shortsword
            #   Scimitar via Nick
            #
            # Bonus Action:
            #   Enhanced Dual Wielding attack
            attacks = [
                ("shortsword", False),
                ("scimitar", False),
                ("shortsword", True),
            ]

        for weapon, dual_wielder_bonus in attacks:
            advantage = vex_ready.copy()
            vex_ready[:] = False

            hit, crit, _ = attack_roll(
                rng,
                n,
                bonus=7,   # Dex +4, PB +3 (character level 5)
                ac=ac,
                advantage=advantage,
                crit_min=19
            )

            static = 4

            if dual_wielder_bonus and not dual_wielder_add_mod:
                static = 0

            total += fighter_attack_damage(
                rng, n, hit, crit, static
            )

            if weapon == "shortsword":
                vex_ready |= hit

    return total


# ============================================================
# PALADIN 4 / SORCERER 1
#
# Oath of Vengeance
# Str 18
# Greatsword
# Great Weapon Fighting
# Greatsword mastery = Graze
# Vow of Enmity
# Divine Smite
# Booming Blade
#
# Paladin 4 has NO Extra Attack.
#
# Multiclass caster level:
#   Paladin 4 -> 2
#   Sorcerer 1 -> 1
#   Total     -> 3
#
# Slots:
#   4 x 1st-level
#   2 x 2nd-level
#
# Plus one free 1st-level Divine Smite.
#
# Default tactic:
#   Round 1: Attack action to establish Vow of Enmity.
#   Rounds 2+: Booming Blade.
# ============================================================

def gwf_greatsword_damage(rng, n, crit):
    rolls = rng.integers(
        1, 7, size=(n, 4), dtype=np.int16
    )

    # 2024 Great Weapon Fighting:
    # weapon damage dice showing 1 or 2 count as 3.
    rolls = np.where(rolls <= 2, 3, rolls)

    base = rolls[:, :2].sum(axis=1)
    crit_extra = rolls[:, 2:].sum(axis=1)

    return base + np.where(crit, crit_extra, 0)


def smite_dice_damage(rng, n, crit, dice_count):
    base = roll_sum(rng, n, 8, dice_count)
    crit_extra = roll_sum(rng, n, 8, dice_count)
    return base + np.where(crit, crit_extra, 0)


def simulate_paladin(
    ac,
    n=100_000,
    rounds=10,
    seed=2,
    booming_blade=True,
    bb_move=False
):
    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    second_slots = np.full(n, 2, dtype=np.int8)
    first_slots = np.full(n, 4, dtype=np.int8)
    free_smite = np.full(n, 1, dtype=np.int8)

    for rd in range(1, rounds + 1):
        use_bb = booming_blade and rd > 1

        # Vow is established with the round-1 Attack action
        # and assumed to remain on this single target.
        hit, crit, _ = attack_roll(
            rng,
            n,
            bonus=7,   # Str +4, PB +3
            ac=ac,
            advantage=True,
            crit_min=20
        )

        weapon_damage = gwf_greatsword_damage(
            rng, n, crit
        ) + 4

        # Graze deals Strength modifier on a miss.
        dmg = np.where(hit, weapon_damage, 4)

        if use_bb:
            # Character level 5:
            # +1d8 thunder on the initial hit.
            initial_bb = roll_sum(rng, n, 8, 1)
            initial_bb += np.where(
                crit,
                roll_sum(rng, n, 8, 1),
                0
            )

            dmg += np.where(hit, initial_bb, 0)

            if bb_move:
                # Level 5+ movement rider = 2d8.
                move_damage = roll_sum(rng, n, 8, 2)
                dmg += np.where(hit, move_damage, 0)

        # One Divine Smite can be cast after the hit.
        # Spend highest-level slots first, preserving the
        # original simulation's resource strategy.
        can_smite = (
            hit
            & (
                (second_slots > 0)
                | (first_slots > 0)
                | (free_smite > 0)
            )
        )

        use_second = can_smite & (second_slots > 0)

        if np.any(use_second):
            smite = smite_dice_damage(
                rng, n, crit, 3
            )
            dmg += np.where(use_second, smite, 0)
            second_slots[use_second] -= 1

        remaining = can_smite & (~use_second)
        use_first = remaining & (first_slots > 0)

        if np.any(use_first):
            smite = smite_dice_damage(
                rng, n, crit, 2
            )
            dmg += np.where(use_first, smite, 0)
            first_slots[use_first] -= 1

        remaining = remaining & (~use_first)
        use_free = remaining & (free_smite > 0)

        if np.any(use_free):
            smite = smite_dice_damage(
                rng, n, crit, 2
            )
            dmg += np.where(use_free, smite, 0)
            free_smite[use_free] -= 1

        total += dmg

    return total


# ============================================================
# BARBARIAN 1 / WARLOCK 4
#
# Str 17
# Rage
# Halberd
# Pact of the Blade
# Great Weapon Master
# Savage Attacker
#
# Warlock 4 does NOT qualify for:
#   Thirsting Blade (Warlock 5+)
#   Eldritch Smite (Warlock 5+)
#
# Therefore:
#   one Attack-action weapon attack per turn
#   no Eldritch Smite damage / Prone setup
#
# Halberd mastery = Cleave
# Cleave ignored because simulation is single-target.
# ============================================================

def savage_d10(rng, n, crit, use_savage):
    a1 = rng.integers(1, 11, size=n)
    a2 = rng.integers(1, 11, size=n)

    b1 = rng.integers(1, 11, size=n)
    b2 = rng.integers(1, 11, size=n)

    bundle_a = a1 + np.where(crit, a2, 0)
    bundle_b = b1 + np.where(crit, b2, 0)

    return np.where(
        use_savage,
        np.maximum(bundle_a, bundle_b),
        bundle_a
    )


def simulate_barblock(
    ac,
    n=100_000,
    rounds=10,
    seed=3,
    strength=17,
    weapon="halberd"
):
    rng = np.random.default_rng(seed)
    total = np.zeros(n, dtype=np.int32)

    str_mod = (strength - 10) // 2
    attack_bonus = str_mod + 3  # character-level PB

    for rd in range(1, rounds + 1):
        savage_available = np.ones(n, dtype=bool)

        # One Attack-action attack.
        hit, crit, _ = attack_roll(
            rng,
            n,
            bonus=attack_bonus,
            ac=ac,
            advantage=False,
            crit_min=20
        )

        use_savage = hit & savage_available

        weapon_die = savage_d10(
            rng, n, crit, use_savage
        )

        savage_available &= ~use_savage

        # Attack-action hit:
        # weapon + Str + Rage + GWM PB.
        dmg = np.where(
            hit,
            weapon_die + str_mod + 2 + 3,
            0
        )

        if weapon == "glaive":
            # Glaive mastery = Graze.
            dmg = np.where(hit, dmg, str_mod)

        total += dmg

        # Great Weapon Master: Hew.
        # Round 1 BA is occupied by Rage.
        # Single-target model uses crit trigger only.
        hew = crit & (rd > 1)

        if np.any(hew):
            hit2, crit2, _ = attack_roll(
                rng,
                n,
                bonus=attack_bonus,
                ac=ac,
                advantage=False,
                crit_min=20
            )

            hit2 &= hew
            crit2 &= hew

            use_savage2 = hit2 & savage_available

            weapon_die2 = savage_d10(
                rng, n, crit2, use_savage2
            )

            # Hew is a Bonus Action attack, not part of
            # the Attack action, so no GWM +PB damage.
            dmg2 = np.where(
                hit2,
                weapon_die2 + str_mod + 2,
                0
            )

            if weapon == "glaive":
                dmg2 = np.where(
                    hew & (~hit2),
                    str_mod,
                    dmg2
                )

            total += dmg2

    return total


# ============================================================
# COMPARISON / AC SWEEP
# ============================================================

def run_comparison(ac, n=100_000, rounds=10):
    fighter = simulate_fighter(
        ac, n=n, rounds=rounds, seed=1000 + ac
    ).mean()

    paladin = simulate_paladin(
        ac, n=n, rounds=rounds, seed=2000 + ac,
        booming_blade=True,
        bb_move=False
    ).mean()

    barblock = simulate_barblock(
        ac, n=n, rounds=rounds, seed=3000 + ac
    ).mean()

    return fighter, paladin, barblock


def sweep_acs(low=12, high=25, n=100_000, rounds=10):
    print(
        f"{'AC':>3} "
        f"{'Fighter/Ranger':>16} "
        f"{'Paladin/Sorcerer':>16} "
        f"{'Barb/Warlock':>16}"
    )
    print("-" * 58)

    for ac in range(low, high + 1):
        fighter, paladin, barblock = run_comparison(
            ac, n=n, rounds=rounds
        )

        print(
            f"{ac:>3} "
            f"{fighter:>16.1f} "
            f"{paladin:>16.1f} "
            f"{barblock:>16.1f}"
        )


if __name__ == "__main__":
    sweep_acs()
