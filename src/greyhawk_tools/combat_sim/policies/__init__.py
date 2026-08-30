"""Registry mapping character id -> its `simulate(ac, n, rounds, seed)` tactic."""

from . import (
    burtha_smith,
    eddwarn_celas,
    finn_barrellor,
    halden_lorithan,
    serethe,
    talon_aldric,
    ulfaerr,
    wimble_scheppen,
)

POLICIES = {
    "burtha_smith": burtha_smith.simulate,
    "eddwarn_celas": eddwarn_celas.simulate,
    "finn_barrellor": finn_barrellor.simulate,
    "halden_lorithan": halden_lorithan.simulate,
    "serethe": serethe.simulate,
    "talon_aldric": talon_aldric.simulate,
    "ulfaerr": ulfaerr.simulate,
    "wimble_scheppen": wimble_scheppen.simulate,
}

__all__ = ["POLICIES"]
