"""Entry point for `python -m greyhawk_tools.combat_sim`."""

import argparse
import sys

from .policies import POLICIES
from .sweep import (
    DEFAULT_AC_HIGH,
    DEFAULT_AC_LOW,
    DEFAULT_ROUNDS,
    DEFAULT_TARGET_SAVE_BONUS,
    DEFAULT_TRIALS,
    sweep_acs,
)


def main():
    parser = argparse.ArgumentParser(
        prog="simulate_combat",
        description="AC-sweep DPR comparison across party members' weapon-attack builds.",
    )
    parser.add_argument(
        "-c", "--characters", nargs="+", metavar="ID",
        help=f"character ids to include (default: all with a policy — {sorted(POLICIES)})",
    )
    parser.add_argument("--ac-low", type=int, default=DEFAULT_AC_LOW)
    parser.add_argument("--ac-high", type=int, default=DEFAULT_AC_HIGH)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS, help="Monte Carlo trials per AC value")
    parser.add_argument(
        "--target-save-bonus", type=int, default=DEFAULT_TARGET_SAVE_BONUS,
        help="target's saving throw bonus, held constant across the AC sweep (default: %(default)s)",
    )
    parser.add_argument("--plot", metavar="PATH", help="write a PNG comparison chart to this path")
    args = parser.parse_args()

    if args.characters:
        unknown = [c for c in args.characters if c not in POLICIES]
        if unknown:
            print(
                f"[!] No tactics policy registered for: {unknown}. Available: {sorted(POLICIES)}",
                file=sys.stderr,
            )
            sys.exit(1)

    sweep_acs(
        character_ids=args.characters,
        ac_low=args.ac_low,
        ac_high=args.ac_high,
        n=args.trials,
        rounds=args.rounds,
        target_save_bonus=args.target_save_bonus,
        plot_path=args.plot,
    )


if __name__ == "__main__":
    main()
