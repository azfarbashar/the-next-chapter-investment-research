# The Next Chapter: Liability-Aware Portfolio Research

**Purpose:** Reproducible educational analysis supporting a long-term investment strategy for the Wharton Global High School Investment Competition client, Laura Gao.

> Protect the Ending. Invest in the Story.

This repository separates three datasets: (1) Laura's hypothetical case-study cash flows; (2) historical U.S. asset-class proxies and a modern VTI/VXUS diagnostic; and (3) the team's actual StockTrak implementation snapshot. StockTrak gains/losses are never added to Laura's client projection.

## Decision summary

- **Client obligations:** $300,000 at the beginning of 2027, $150,000 at the beginning of 2028, and ten fixed $50,000 payments at the beginning of each year from 2033-2042.
- **Baseline allocation:** 65% equity / 35% Treasury in 2027, with equity targets falling by five percentage points to 40% in 2032. VTI is 47% and VXUS 18% at the initial target.
- **Funding policy:** The team defines high funding certainty as at least 95% modeled chance of accumulating enough to buy the full 2033 reserve. Under the 1928-2025 paired moving-block bootstrap, the five-point policy reaches the illustrative 3% reserve PV ($439,305) in 96.009% of paths, but reaches the $500,000 zero-yield benchmark in only 91.822%. These are model shares, not objective probabilities or guarantees.
- **Fallback:** If the five-point path falls below 95% at the reserve cost being tested, the model checks an eight-point accelerated path. It reaches the 3% reserve PV in 96.744%, but only the $500,000 stress in 92.277%. If neither reaches 95%, the policy sets the facility contribution to $0, directs all available discretionary capital toward the reserve, and reports that the model target remains unmet. A rule cannot reverse losses already incurred.
- **Reserve structure:** On January 1, 2033, the first $50,000 is immediately available in cash/T-bills; the remaining nine $50,000 payments are matched to nominal U.S. Treasury STRIPS or dedicated Treasury cash flows available no later than each January due date. One rung is retired after each annual payment through 2042. The actual ladder is priced using the 2033 zero-coupon spot curve, not a guessed yield.
- **Facility contribution:** In the middle 50% of simulated 2031 balances, the median balance is about $607,879 and the conditional 2033 fifth percentile is about $548,039. Under a $500,000 zero-yield reserve benchmark, the rule caps construction at $20,000, leaving at least $28,000 of modeled downside surplus. Within this middle-50% group, 96.883% of paths retain at least $520,000 after a $20,000 contribution. Lower 2031 balance bands support $0. The $0-$20,000 range is conditional, not a promise.
- **Long historical test:** The 1928-2025 data contain 98 annual S&P 500 total-return and 10-year Treasury total-return observations and 93 overlapping six-year rolling windows. The worst five-point historical window is 1929-1934, ending near $366,263. Windows overlap and are not independent.
- **StockTrak audit:** The supplied positions show about 64.01% equities, 35.74% Treasuries including accrued interest, and 0.25% cash. The four Treasury notes total $105,000 face value and $5,225 initial annual coupon run-rate. Coupon dates were not verified, so coupons are not counted as available for January 1 liabilities.

## Quick start

Use Python 3.10 or later.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/model.py
python src/policy_outputs.py
python -m unittest discover -s tests -v
```

The model regenerates CSV/JSON results and PNG charts under `results/`. `policy_outputs.py` creates the liability ladder, funding override assessment, policy decision rules, and case-study requirement crosswalk.

## Repository map

- `src/model.py`: historical rolling windows, paired moving-block bootstrap, portfolio glide paths, reserve thresholds, conditional facility analysis, inflation, correlation, StockTrak audit, and chart generation.
- `src/liability_ladder.py`: ten-payment present-value calculation, zero-curve reserve ladder, annual roll-forward, and facility cap rule.
- `src/policy_outputs.py`: 95% funding threshold, five-point/eight-point decision rule, requirement coverage matrix, reserve schedule, and facility outputs.
- `data/us_long_history_1928_2025.csv`: annual U.S. large-cap stock and 10-year Treasury total-return proxies.
- `data/modern_asset_returns_2011_2025.csv`: modern annual total returns for VTI, VXUS and a Treasury comparison series.
- `data/wins_snapshot.csv` and `data/wins_account_summary.json`: team-supplied WInS/StockTrak holdings and account snapshot.
- `data/2033_spot_curve_input_template.csv`: blank input for annual-effective zero-coupon spot rates at maturities 1-9, observable at the beginning of 2033.
- `data/2033_reserve_ladder_template.csv`: payment-by-payment implementation worksheet.
- `results/`: all model outputs, tables, and figures.
- `tests/`: 32 unit tests for timing, cash-flow PV, reserve rungs, glide path, policy fallback, data coverage, reproducibility, and StockTrak reconciliation.
- `reports/`: IPS text, requirement crosswalk, methods, sources, chart guide, competition-readiness assessment, strengths/limitations, and document builders.

## Model assumptions and limitations

1. Contributions occur at the beginning of the year: $300,000 on January 1, 2027 and $150,000 on January 1, 2028. The second contribution is added before the 2028 annual return.
2. Six annual return periods represent 2027-2032. The five-point equity glide is 65/60/55/50/45/40%; the fallback is 65/57/49/41/33/25%. The remainder is the Treasury proxy sleeve.
3. The 1928-2025 long sample uses S&P 500 total returns including dividends and 10-year Treasury total returns. It is not a literal 98-year backtest of VTI, VXUS, or the team's four individual notes. No international equity return series is used in the long proxy sample.
4. The modern VTI/VXUS diagnostic covers 2011-2025 only (15 annual observations); correlations are descriptive and unstable.
5. The bootstrap resamples paired three-year contiguous blocks from the 98-year annual dataset to create 100,000 six-year paths. It preserves same-year stock/Treasury pairings and local three-year runs but breaks continuity between blocks; it cannot generate events absent from the sample.
6. The 95% funding threshold is the team's policy definition, not a Wharton-mandated number or a guarantee. Under a flat 0%-1% reserve-cost sensitivity, neither glide path reaches 95%; under a flat 2%-5% sensitivity, the five-point policy does. The actual 2033 reserve cost must be calculated from a complete zero-coupon spot curve or STRIPS prices. Do not use unbootstrapped par yields.
7. The $500,000 benchmark assumes zero return after January 1, 2033. It is a conservative nominal-cash benchmark; the actual priced Treasury ladder may cost less if available zero rates are positive.
8. The reserve ladder is an implementation policy, not a list of currently owned CUSIPs. It requires $50,000 immediate cash/T-bills plus nine Treasury rungs sized to deliver $50,000 by each January date through 2042.
9. The facility rule uses the 2031 account balance distribution and the same six-year paths to obtain conditional 2033 values. It caps facility spending at half of positive fifth-percentile surplus over the $500,000 benchmark, rounded down to $5,000. The $0-$20,000 central range is conditional, and the actual balance and reserve cost must be refreshed.
10. StockTrak holdings are implementation evidence only. Four notes total $105,000 face value and $5,225 initial annual coupon run-rate. Exact coupon dates were not supplied and coupons are excluded from the January cash-availability bridge. The 2036 note's displayed yield is anomalous relative to its premium price/coupon and is not used. The separate StockTrak total-market-value summary field remains $1,414 below the six line-item market values and is not explained.
11. Nominal operating payments are fixed at $50,000. Inflation sensitivities describe purchasing-power loss; Taiwan construction-cost inflation and USD/TWD currency movements are not forecast.
12. Annual data omit intra-year paths, exact trade timing, taxes, and fees. Historical models and bootstrap frequencies are not guarantees. Once the reserve is fully purchased with matched Treasury cash flows, scheduled operating payments do not depend on selling equities.

## Final report guidance

Use four core charts: client cash-flow timeline; five-point glide and eight-point fallback; historical/bootstrap downside results with the reserve threshold; and the conditional 2031 facility cap. A stock-bond correlation chart is optional. The appendix contains diagnostics; do not overwhelm judges with every output.

The IPS must remain text-only and within Wharton's page and word limits. The research appendix is supporting evidence, not a replacement for the official Final Report requirements in the team portal.

**Run result:** 32 automated tests pass. See `results/test_log.txt`.

**Competition AI-policy note:** This is an AI-assisted research and code draft. The team must follow Wharton's AI policy, verify the work, disclose retained assistance accurately, and cite AI-generated material as required. See `reports/ai_use_disclosure_template.md`.
