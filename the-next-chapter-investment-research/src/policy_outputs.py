"""Generate requirement coverage, reserve ladder, and funding-policy outputs."""
from __future__ import annotations
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
import model
from liability_ladder import reserve_ladder, reserve_rollforward, reserve_pv_from_spot_rates

OUT = ROOT / "results"
DATA = ROOT / "data"


def equivalent_flat_rate_for_reserve(target: float) -> float:
    """Solve the flat annual-effective rate whose annuity-due PV is target."""
    lo, hi = -0.5, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if model.reserve_cost_flat(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main() -> None:
    OUT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    key = json.loads((OUT / "key_results.json").read_text())
    thresholds = pd.read_csv(OUT / "bootstrap_reserve_threshold_sensitivity.csv")
    five = thresholds[thresholds.policy == "five_percentage_point_glide"].copy()
    eight = thresholds[thresholds.policy == "eight_percentage_point_glide"].copy()
    five = five.sort_values("illustrative_flat_reserve_rate")
    eight = eight.sort_values("illustrative_flat_reserve_rate")

    # Funding-coverage comparison for both the baseline and the explicit fallback.
    funding_rows = []
    for rate in (0.00, 0.01, 0.02, 0.03, 0.04, 0.05):
        row5 = five[np.isclose(five.illustrative_flat_reserve_rate, rate)].iloc[0]
        row8 = eight[np.isclose(eight.illustrative_flat_reserve_rate, rate)].iloc[0]
        p5 = float(row5.share_paths_meeting_target)
        p8 = float(row8.share_paths_meeting_target)
        action = model.funding_policy_decision(p5, p8, 0.95)
        if action == "maintain_five_point_glide":
            explanation = "Five-point baseline meets the 95% modeled threshold under this reserve valuation."
        elif action == "adopt_eight_point_fallback":
            explanation = "Five-point baseline falls short; eight-point fallback meets the 95% modeled threshold."
        else:
            explanation = "Neither path meets 95%; use eight-point fallback, set facility contribution to zero, and disclose the funding target miss."
        for label, row in (("Five-point baseline", row5), ("Eight-point fallback", row8)):
            funding_rows.append({
                "policy": label,
                "flat_discount_rate_assumption": rate,
                "reserve_cost_usd": float(row.reserve_target_usd),
                "modeled_share_reaching_reserve": float(row.share_paths_meeting_target),
                "policy_threshold": 0.95,
                "meets_95pct_policy_threshold": bool(row.share_paths_meeting_target >= 0.95),
                "selected_response": action,
                "decision_explanation": explanation,
            })
    funding = pd.DataFrame(funding_rows)
    funding.to_csv(OUT / "funding_certainty_assessment.csv", index=False)

    # Compact decision table to translate the simulation into an operating rule.
    decision_rows = []
    for rate in (0.00, 0.01, 0.02, 0.03, 0.04, 0.05):
        row5 = five[np.isclose(five.illustrative_flat_reserve_rate, rate)].iloc[0]
        row8 = eight[np.isclose(eight.illustrative_flat_reserve_rate, rate)].iloc[0]
        p5 = float(row5.share_paths_meeting_target)
        p8 = float(row8.share_paths_meeting_target)
        action = model.funding_policy_decision(p5, p8, 0.95)
        decision_rows.append({
            "flat_discount_rate_sensitivity": rate,
            "reserve_cost_usd": float(row5.reserve_target_usd),
            "five_point_success_share": p5,
            "eight_point_success_share": p8,
            "selected_policy_response": action,
            "facility_spending_rule": "Permitted only after reserve is fully funded and the selected policy meets 95%; otherwise $0",
            "interpretation": (
                "Maintain five-point baseline" if action == "maintain_five_point_glide" else
                "Switch to eight-point fallback" if action == "adopt_eight_point_fallback" else
                "Eight-point fallback is more defensive but target remains unmet; $0 facility contribution"
            ),
        })
    pd.DataFrame(decision_rows).to_csv(OUT / "funding_override_assessment.csv", index=False)

    # Illustrative flat 3% reserve ladder and annual rung roll-forward.
    base_curve = {t: .03 for t in range(1, 10)}
    ladder = reserve_ladder(base_curve)
    ladder["assumption_note"] = "Illustrative flat 3% annual-effective zero curve; not a 2033 forecast or tradable quote"
    ladder.to_csv(OUT / "reserve_ladder_illustrative_flat_3pct.csv", index=False)
    reserve_rollforward(base_curve).to_csv(OUT / "reserve_rollforward_illustrative_flat_3pct.csv", index=False)

    # Conditional facility analysis: use the conservative no-yield $500,000 benchmark.
    facility = pd.read_csv(OUT / "facility_contribution_scenarios.csv")
    middle = facility[facility["2031_balance_band"] == "Middle 50% 2031 balance"].iloc[0]
    lower = facility[facility["2031_balance_band"] == "10th-25th percentile 2031 balance"].iloc[0]
    facility_reco = pd.DataFrame([
        {
            "scenario": "Lower 10th-25th percentile 2031 balance band",
            "median_2031_balance_usd": lower["2031_balance_median_usd"],
            "conditional_2033_p05_usd": lower["2033_p05_value_usd"],
            "reserve_benchmark_usd": 500000,
            "surplus_at_p05_usd": lower["p05_surplus_vs_500k_usd"],
            "conditional_facility_cap_usd": lower["facility_cap_at_0pct_reserve_yield_usd"],
            "share_paths_cover_reserve_plus_cap": lower["share_paths_cover_500k_plus_zero_yield_cap"],
            "recommendation": "No facility contribution",
        },
        {
            "scenario": "Middle 50% 2031 balance band",
            "median_2031_balance_usd": middle["2031_balance_median_usd"],
            "conditional_2033_p05_usd": middle["2033_p05_value_usd"],
            "reserve_benchmark_usd": 500000,
            "surplus_at_p05_usd": middle["p05_surplus_vs_500k_usd"],
            "conditional_facility_cap_usd": middle["facility_cap_at_0pct_reserve_yield_usd"],
            "share_paths_cover_reserve_plus_cap": middle["share_paths_cover_500k_plus_zero_yield_cap"],
            "recommendation": "Planning range $0-$20,000; upper end conditional on observed 2031 balance and updated curve",
        },
    ])
    facility_reco.to_csv(OUT / "facility_recommendation_summary.csv", index=False)

    # Requirement crosswalk is designed to make all requested case-study components explicit.
    crosswalk = pd.DataFrame([
        ["Ten $50,000 operating payments", "Portfolio alone funds ten beginning-of-year payments, 2033-2042; no grants or sponsors counted for operations", "Ten-rung reserve design; payment certainty follows only after the complete ladder is purchased"],
        ["Operating reserve established in 2033", "Price and segregate reserve on 1 Jan 2033 before the first payment or facility spending", "First payment immediate; nine future payments priced from 2033 zero-coupon spot rates"],
        ["Initial reserve asset composition", "$50,000 immediate cash/T-bill plus nine nominal Treasury STRIPS or dedicated cash-flow rungs", "Flat 3% illustrative price $439,305; zero-yield nominal benchmark $500,000"],
        ["Reserve composition through 2042", "Pay $50,000 each 1 Jan; retire one rung; hold remaining rungs in matched Treasuries/cash", "Ten-year roll-forward schedule; proceeds available no later than due date"],
        ["High degree of certainty", "Internal policy target: at least 95% modeled probability of accumulating the priced reserve", "Five-point path: 96.009% at illustrative 3% PV, 91.822% at $500k stress; eight-point fallback: 96.744% at 3%, 92.277% at $500k stress"],
        ["Funding override", "Maintain five points if it meets 95%; switch to eight points if only it meets 95%; otherwise $0 facility and disclose target miss", "Explicit simulation-based fallback rule; does not reverse prior losses or guarantee funding"],
        ["Responsible facility contribution", "Spend at most half positive 5th-percentile surplus after reserve, rounded down to $5k", "Middle 50% 2031 balance band supports conditional $20k cap against $500k benchmark; lower 10th-25% band supports $0"],
        ["2031 co-sponsor range", "Communicate conditional $0-$20k planning range; recalculate using actual balance and then-current curve", "96.883% of middle-50% conditional paths retain at least $520k after $20k; not unconditional confidence"],
        ["Dynamic allocation", "Equity targets 65/60/55/50/45/40% in 2027-2032, annual rebalance and funding override", "Rolling historical tests and 100,000 paired moving-block bootstrap paths"],
        ["Inflation", "Keep payments fixed nominally; assess real purchasing power, Taiwan cost inflation and USD/TWD risk", "2%, 3%, 5% purchasing-power sensitivities; no local cost/FX forecast"],
    ], columns=["requirement", "policy_rule", "evidence_and_limitation"])
    crosswalk.to_csv(OUT / "requirement_coverage_matrix.csv", index=False)

    # Operating decision rules used by the IPS and research report.
    decision_rules = pd.DataFrame([
        ["Annual review, 2027-2032", "Reprice the reserve sensitivity and compare five- and eight-point projected funding shares with 95%", "Keep five points if it meets target"],
        ["Five-point path below 95%, eight-point path at or above 95%", "Switch to accelerated eight-percentage-point annual de-risking and suspend facility spending until reserve is secured", "Fallback meets model target under current assumptions"],
        ["Both paths below 95%", "Use eight-point path as more defensive fallback, set facility contribution to $0, and direct all available discretionary capital toward operating reserve", "Target remains unmet; disclose shortfall risk; no policy can reverse losses already incurred"],
        ["2031 co-sponsor communication", "Provide conditional $0-$20,000 planning range only when observed balance and updated reserve price support fifth-percentile coverage", "Upper bound not a promise; lower 2031 balance bands support $0"],
        ["Beginning of 2033", "Price reserve from actual zero-coupon spot curve; segregate full reserve before first payment or facility contribution", "If assets are below reserve cost, no facility spending; disclose funding gap"],
        ["2033-2042 each January", "Pay $50,000 from immediately available cash or maturing matched rung; retire that rung", "Once full ladder is purchased, market-price movements do not require equity sales for scheduled payments"],
    ], columns=["trigger", "required_action", "interpretation"])
    decision_rules.to_csv(OUT / "funding_policy_decision_rules.csv", index=False)

    p05_five = float(key["bootstrap_five_p05_usd"])
    p05_eight = float(pd.read_csv(OUT / "bootstrap_policy_comparison.csv").query("policy == 'eight_percentage_point_glide'").iloc[0].p05_terminal_value_usd)
    summary = {
        "high_certainty_policy_target": 0.95,
        "base_case_discount_rate_sensitivity": 0.03,
        "base_case_reserve_pv_usd": model.reserve_cost_flat(.03),
        "five_point_base_case_modeled_funding_share": float(five[np.isclose(five.illustrative_flat_reserve_rate,.03)].iloc[0].share_paths_meeting_target),
        "eight_point_base_case_modeled_funding_share": float(eight[np.isclose(eight.illustrative_flat_reserve_rate,.03)].iloc[0].share_paths_meeting_target),
        "zero_yield_reserve_pv_usd": 500000.0,
        "five_point_zero_yield_modeled_funding_share": float(five[np.isclose(five.illustrative_flat_reserve_rate,0)].iloc[0].share_paths_meeting_target),
        "eight_point_zero_yield_modeled_funding_share": float(eight[np.isclose(eight.illustrative_flat_reserve_rate,0)].iloc[0].share_paths_meeting_target),
        "five_point_2033_p05_usd": p05_five,
        "eight_point_2033_p05_usd": p05_eight,
        "five_point_equivalent_flat_rate_at_p05": equivalent_flat_rate_for_reserve(p05_five),
        "eight_point_equivalent_flat_rate_at_p05": equivalent_flat_rate_for_reserve(p05_eight),
        "middle_50pct_2031_median_balance_usd": float(middle["2031_balance_median_usd"]),
        "middle_50pct_conditional_2033_p05_usd": float(middle["2033_p05_value_usd"]),
        "central_facility_cap_usd": float(middle["facility_cap_at_0pct_reserve_yield_usd"]),
        "middle_50pct_paths_cover_500k_plus_20k": float(middle["share_paths_cover_500k_plus_zero_yield_cap"]),
        "ladder_example_3pct_pv_usd": reserve_pv_from_spot_rates(base_curve),
        "automated_tests_expected": 32,
    }
    (OUT / "policy_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
