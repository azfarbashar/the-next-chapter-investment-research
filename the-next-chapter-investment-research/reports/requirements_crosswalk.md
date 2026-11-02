# Wharton case-study requirement crosswalk

| Requirement | Strategy rule | Evidence / limitation |
|---|---|---|
| Ten $50,000 operating payments, 2033-2042 | Laura's portfolio alone is the source for ten beginning-of-year payments; no grants or co-sponsors fund operations. | A ten-rung reserve is specified. Payments are funded only after the entire ladder is purchased in 2033. |
| Operating reserve established in 2033 | Price and segregate the reserve on January 1, 2033 before the first payment or any facility spending. | The first $50,000 is immediate; the other nine payments are priced from zero-coupon spot rates for maturities 1-9. |
| Initial reserve asset composition | $50,000 cash/T-bill plus nine nominal Treasury STRIPS or dedicated Treasury cash-flow rungs. | Illustrative flat 3% cost is $439,305; zero-yield nominal benchmark is $500,000. Actual 2033 curve is unknown. |
| Reserve composition through 2042 | Pay $50,000 every January, retire one rung, and keep remaining assets in matched Treasury/cash instruments. | `results/reserve_rollforward_illustrative_flat_3pct.csv` defines the ten-year drawdown. Actual securities are selected in 2033. |
| High degree of funding certainty | Team-defined internal target: at least 95% modeled chance of accumulating the priced reserve. | Five-point glide: 96.009% at 3% reserve PV, but 91.822% at $500,000 zero-yield stress. This is a model threshold, not a guarantee or Wharton-mandated percentage. |
| Funding override | Keep five-point glide if it reaches 95%; switch to eight-point fallback if only it reaches 95%; if neither passes, set facility contribution to $0 and prioritize all available capital for reserve. | Eight-point fallback: 96.744% at 3% PV, but 92.277% at $500,000 stress; both fall below 95% under the 0%-1% reserve sensitivities. |
| Responsible facility contribution | Spend no more than half of positive fifth-percentile surplus after reserve, rounded down to $5,000. | Middle 50% 2031 balance group supports conditional $20,000 cap under $500,000 benchmark; lower 10th-25th group supports $0. |
| 2031 co-sponsor range | Communicate conditional $0-$20,000 planning range; recalculate from actual 2031 balance and 2033 zero curve. | In the middle-50% conditional group, 96.883% of paths retain at least $520,000 after a $20,000 contribution. This is conditional, not unconditional confidence. |
| Dynamic asset allocation | Equity targets 65/60/55/50/45/40% in 2027-2032; annual rebalance and explicit eight-point fallback. | Rolling historical tests and 100,000 paired three-year moving-block bootstrap paths. |
| Inflation | Keep the ten payments fixed at $50,000 nominal; separately analyze real purchasing power and Taiwan facility/FX exposure. | 2%, 3%, 5% sensitivities; local facility inflation and USD/TWD risk are not forecast. |

## Decision hierarchy

1. The operating reserve is funded before any facility contribution.
2. The five-point glide path is the baseline. If modeled coverage falls below 95%, test the eight-point path.
3. If neither path reaches 95%, facility spending is zero and all available discretionary capital is directed toward the reserve. The target miss is disclosed; an allocation rule cannot reverse losses already incurred.
4. In 2033, actual Treasury zero-coupon spot rates (or STRIPS prices) set the reserve cost. Do not substitute unbootstrapped par yields.
5. After the ladder is fully purchased, make each January payment from cash or the matching Treasury rung through 2042.

The 95% threshold is a team policy definition of “high degree of funding certainty,” not a guarantee and not a percentage mandated by Wharton. A 3% flat reserve rate is an illustrative sensitivity, not a forecast. No facility amount is promised before the actual 2031 portfolio balance and updated reserve cost are known.
