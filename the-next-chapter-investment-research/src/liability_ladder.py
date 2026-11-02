"""Liability reserve valuation and ladder schedule for The Next Chapter.

This module is deliberately separate from the StockTrak holdings audit.
It prices ten $50,000 beginning-of-year nominal liabilities at 1 Jan 2033.
The first payment is immediate; the other nine are discounted using annual-
compounded zero-coupon spot rates (or rates derived from Treasury STRIPS).

The generated ladder is an implementation specification, not a list of
currently available security CUSIPs. Exact instrument maturities must be
selected in 2033 so cash is available no later than each January payment date.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import math
import pandas as pd

PAYMENT = 50_000.0
FIRST_YEAR = 2033
LAST_YEAR = 2042


def reserve_pv_from_spot_rates(spot_rates: Mapping[int, float], payment: float = PAYMENT) -> float:
    """Present value on 1 Jan 2033 using zero rates for t=1,...,9.

    The first payment is due immediately and is not discounted. Rates are
    annual-effective zero-coupon spot rates, not raw Treasury par yields.
    """
    required = set(range(1, 10))
    if set(spot_rates.keys()) != required:
        raise ValueError("Provide exactly nine annual zero rates for maturities 1 through 9")
    if payment <= 0:
        raise ValueError("payment must be positive")
    if any(not math.isfinite(float(r)) or float(r) <= -1 for r in spot_rates.values()):
        raise ValueError("All spot rates must be finite and greater than -100%")
    return float(payment + sum(payment / (1.0 + float(spot_rates[t])) ** t for t in range(1, 10)))


def reserve_ladder(spot_rates: Mapping[int, float], payment: float = PAYMENT) -> pd.DataFrame:
    """Build a ten-rung reserve schedule at 1 Jan 2033.

    Rung 2033 is immediate cash. Rungs 2034-2042 target a nominal $50,000
    U.S. Treasury cash flow available by the relevant payment date. For
    simplicity, the price of each future rung is its discounted face value.
    If a STRIP or note matures earlier than the payment date, proceeds should
    be held in cash/Treasury bills until the payment is due.
    """
    reserve_pv_from_spot_rates(spot_rates, payment)
    rows = [{
        "payment_year": FIRST_YEAR,
        "payment_date": f"{FIRST_YEAR}-01-01",
        "years_from_2033": 0,
        "nominal_cash_required_usd": payment,
        "zero_coupon_spot_rate": None,
        "discount_factor": 1.0,
        "initial_purchase_cost_usd": payment,
        "reserve_instrument_target": "Cash or Treasury bill available immediately",
        "timing_rule": "Available at start of 1 Jan 2033 before first payment",
    }]
    for t in range(1, 10):
        year = FIRST_YEAR + t
        rate = float(spot_rates[t])
        df = 1.0 / (1.0 + rate) ** t
        rows.append({
            "payment_year": year,
            "payment_date": f"{year}-01-01",
            "years_from_2033": t,
            "nominal_cash_required_usd": payment,
            "zero_coupon_spot_rate": rate,
            "discount_factor": df,
            "initial_purchase_cost_usd": payment * df,
            "reserve_instrument_target": "U.S. Treasury STRIP or dedicated Treasury cash flow",
            "timing_rule": "Mature/pay no later than payment date; hold early proceeds in cash/T-bills",
        })
    return pd.DataFrame(rows)


def reserve_rollforward(spot_rates: Mapping[int, float], payment: float = PAYMENT) -> pd.DataFrame:
    """Describe the reserve's composition as each January payment is made.

    This table tracks liability rungs, not mark-to-market values after 2033.
    Future market values are unnecessary if each rung is bought and held to
    its matched nominal payment, assuming Treasury obligations are honored.
    """
    ladder = reserve_ladder(spot_rates, payment)
    rows = []
    for i, row in ladder.iterrows():
        remaining = len(ladder) - i - 1
        rows.append({
            "payment_date": row.payment_date,
            "payment_made_usd": payment,
            "rungs_remaining_after_payment": remaining,
            "future_nominal_payments_remaining_usd": remaining * payment,
            "composition_after_payment": (
                "No remaining operating reserve rungs" if remaining == 0 else
                f"{remaining} matched U.S. Treasury/cash rungs for {int(row.payment_year)+1}-2042"
            ),
        })
    return pd.DataFrame(rows)


def facility_cap_from_p05(p05_2033: float, reserve_cost: float,
                          retain_fraction: float = 0.50,
                          increment: float = 5_000.0) -> tuple[float, float]:
    """Cap facility use at a share of the downside surplus, rounded down."""
    if not 0 <= retain_fraction <= 1:
        raise ValueError("retain_fraction must be in [0,1]")
    if reserve_cost < 0 or increment <= 0:
        raise ValueError("reserve_cost must be nonnegative and increment positive")
    surplus = float(p05_2033) - float(reserve_cost)
    spendable = max(0.0, surplus) * (1.0 - retain_fraction)
    cap = math.floor((spendable + 1e-9) / increment) * increment
    return float(cap), float(surplus)


def load_spot_curve_csv(path: str) -> dict[int, float]:
    """Load a CSV with columns years_from_2033, annual_zero_coupon_spot_rate.

    Row t=0 is ignored; every t=1..9 must have a numeric rate. Do not paste
    Treasury par yields into this file without bootstrapping to zero rates.
    """
    df = pd.read_csv(path)
    needed = {"years_from_2033", "annual_zero_coupon_spot_rate"}
    if not needed.issubset(df.columns):
        raise ValueError(f"CSV must contain columns {sorted(needed)}")
    rates = {}
    for r in df.itertuples():
        t = int(r.years_from_2033)
        if 1 <= t <= 9:
            if pd.isna(r.annual_zero_coupon_spot_rate):
                raise ValueError(f"Missing zero spot rate at tenor {t}")
            rates[t] = float(r.annual_zero_coupon_spot_rate)
    if set(rates) != set(range(1, 10)):
        raise ValueError("Need numeric zero rates for tenors 1 through 9")
    return rates


def write_example_outputs(out_dir: str, rate: float = 0.03) -> None:
    """Create an illustrative flat-3% ladder and roll-forward schedule."""
    from pathlib import Path
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    curve = {t: rate for t in range(1, 10)}
    ladder = reserve_ladder(curve)
    ladder.to_csv(out / "reserve_ladder_illustrative_flat_3pct.csv", index=False)
    reserve_rollforward(curve).to_csv(out / "reserve_rollforward_illustrative_flat_3pct.csv", index=False)


if __name__ == "__main__":
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    write_example_outputs(root / "results")
    print(f"Illustrative 3% reserve PV: ${reserve_pv_from_spot_rates({t: .03 for t in range(1,10)}):,.2f}")
