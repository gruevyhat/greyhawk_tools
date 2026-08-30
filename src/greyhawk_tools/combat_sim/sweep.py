"""AC-sweep DPR comparison harness — the generalized form of the inbox
script's `run_comparison` / `sweep_acs`, driving however many characters
have a registered policy instead of three hardcoded functions.
"""

from .character import load_character
from .policies import POLICIES

DEFAULT_AC_LOW = 12
DEFAULT_AC_HIGH = 25
DEFAULT_TRIALS = 100_000
DEFAULT_ROUNDS = 10
DEFAULT_TARGET_SAVE_BONUS = 3  # held constant across the AC sweep — see run_sweep()


def display_name(character_id: str) -> str:
    return load_character(character_id).short_name


def run_sweep(
    character_ids,
    ac_low=DEFAULT_AC_LOW,
    ac_high=DEFAULT_AC_HIGH,
    n=DEFAULT_TRIALS,
    rounds=DEFAULT_ROUNDS,
    target_save_bonus=DEFAULT_TARGET_SAVE_BONUS,
):
    """Return {ac: {character_id: mean_total_damage_over_rounds}}.

    `target_save_bonus` is the flat bonus assumed for the target's saving
    throws (Thunderwave, Dissonant Whispers, ...) and is held constant
    across the whole AC sweep — AC and save bonus aren't the same stat, and
    deriving one from the other would be a fabricated correlation. A
    character whose damage is entirely save-based will show up as a flat
    line: that's the AC axis genuinely not mattering to that build, not a
    bug in the chart.
    """
    unknown = [c for c in character_ids if c not in POLICIES]
    if unknown:
        raise ValueError(f"No policy registered for: {unknown}. Available: {sorted(POLICIES)}")

    results = {}
    for ac in range(ac_low, ac_high + 1):
        row = {}
        for cid in character_ids:
            simulate = POLICIES[cid]
            total = simulate(ac, n=n, rounds=rounds, seed=hash((cid, ac)) % (2**31), target_save_bonus=target_save_bonus)
            row[cid] = float(total.mean())
        results[ac] = row
    return results


def print_table(results: dict, character_ids):
    names = {cid: display_name(cid) for cid in character_ids}
    headers = [names[cid] for cid in character_ids]
    col_width = max(16, max(len(h) for h in headers) + 2)

    print(f"{'AC':>3} " + " ".join(f"{h:>{col_width}}" for h in headers))
    print("-" * (4 + (col_width + 1) * len(headers)))
    for ac, row in results.items():
        cells = " ".join(f"{row[cid]:>{col_width}.1f}" for cid in character_ids)
        print(f"{ac:>3} {cells}")


def plot(results: dict, character_ids, path):
    import matplotlib.pyplot as plt

    names = {cid: display_name(cid) for cid in character_ids}
    acs = sorted(results)

    fig, ax = plt.subplots(figsize=(10, 6))
    for cid in character_ids:
        ax.plot(acs, [results[ac][cid] for ac in acs], marker="o", label=names[cid])

    ax.set_xlabel("Target AC")
    ax.set_ylabel(f"Mean damage over {DEFAULT_ROUNDS} rounds")
    ax.set_title("Combat sim: expected damage vs. target AC")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def sweep_acs(
    character_ids=None,
    ac_low=DEFAULT_AC_LOW,
    ac_high=DEFAULT_AC_HIGH,
    n=DEFAULT_TRIALS,
    rounds=DEFAULT_ROUNDS,
    target_save_bonus=DEFAULT_TARGET_SAVE_BONUS,
    plot_path=None,
):
    character_ids = character_ids or sorted(POLICIES)
    results = run_sweep(character_ids, ac_low, ac_high, n, rounds, target_save_bonus)
    print_table(results, character_ids)
    if plot_path:
        plot(results, character_ids, plot_path)
        print(f"\nWrote plot to {plot_path}")
    return results


if __name__ == "__main__":
    sweep_acs()
