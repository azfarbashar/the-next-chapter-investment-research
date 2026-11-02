# Project Strengths, Trade-offs, and Limitations

## Strengths

1. **Client-first objective:** The ten mandatory operating payments have priority over the discretionary facility contribution.
2. **Clear allocation rule:** Five-percentage-point annual reduction in equity target from 65% in 2027 to 40% in 2032.
3. **Explicit fallback:** If the five-point path misses the 95% modeled funding target, the model tests an eight-point glide; if neither meets the target, facility spending becomes $0.
4. **Actual liability design:** The reserve starts with immediately available $50,000 and uses nine future Treasury/cash rungs matched to the January payment dates.
5. **Long historical context:** 1928-2025 U.S. proxy data include the Great Depression, high-inflation 1970s, dot-com era, Global Financial Crisis, pandemic period, and 2022 stock-bond decline.
6. **Transparent downside measures:** 5th percentile and average worst-5% one-sided funding gap are reported, with the latter clearly distinguished from investment-loss CVaR.
7. **Conditional facility policy:** The $0-$20,000 central planning range is tied to 2031 balance bands and a $500,000 conservative reserve benchmark.
8. **Inflation treatment:** The nominal payment remains fixed while purchasing-power erosion and Taiwan facility-cost risks are considered separately.
9. **Reproducibility:** Code, source data, fixed seeds, outputs, charts, and 32 automated tests are included.
10. **Client-specific narrative:** “The Next Chapter” is memorable but does not replace financial reasoning.

## Weaknesses and trade-offs

1. **Funding probability is conditional:** Five-point modeled success is 96.009% at a 3% flat reserve valuation but 91.822% at the $500,000 no-yield benchmark. The eight-point fallback produces 96.744% and 92.277%, respectively. The 95% threshold is not met in 0%-1% reserve-rate sensitivities.
2. **Historical worst case:** The five-point glide path's worst overlapping six-year proxy window is 1929-1934 and ends near $366,263.
3. **Proxy mismatch:** Long-run returns represent U.S. equities and 10-year Treasuries, not the actual ETFs or individual notes. Modern international equity data are limited to 2011-2025.
4. **Bootstrap limitations:** Three-year blocks preserve within-block sequence but not all long regimes; 100,000 paths do not create 100,000 independent historical observations.
5. **No exact 2033 ladder instruments yet:** The future Treasury zero curve and available STRIPS/CUSIPs are unknown. The model specifies the rungs and timing rule; securities must be selected when the reserve is established.
6. **Current StockTrak notes are only a starting ladder:** $105,000 face value is not enough to cover all ten payments; some current maturities occur after the corresponding January payment dates. Coupon dates were not provided.
7. **Facility range is conditional:** $20,000 is a conditional cap for the middle-50% 2031 balance group. The lower scenario supports $0; no unconditional promise should be made.
8. **Implementation data limitations:** The account-value reconciliation works to one cent using line-item positions, accrued interest, and cash, but the separate total-market-value field remains unexplained; the 2036 quoted bond yield is anomalous.

## Overall assessment

The work covers the major strategy requirements and is substantially more coherent than a stock-picking presentation. Its most important limitation is also its most important honest finding: no glide path alone guarantees that the portfolio will reach the priced reserve by 2033. The reserve-first override protects against discretionary overcommitment but cannot reverse an already-incurred shortfall. The model is evidence for a policy, not a guarantee or a reliable personal forecast.
