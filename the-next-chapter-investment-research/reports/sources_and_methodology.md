# Sources and Methodology

## Client cash flows and competition rules

The client's required cash flows and competition instructions come from the 2026-2027 Wharton Global High School Investment Competition materials supplied by the team.

- $300,000 at the beginning of 2027; $150,000 at the beginning of 2028.
- No portfolio additions or withdrawals before 2033 other than those two contributions.
- Ten fixed $50,000 payments at the beginning of each year from 2033 through 2042.
- The first payment is immediate when the reserve is established at the beginning of 2033; the remaining nine payments occur one year apart.
- All ten payments must be funded by the investment portfolio with a high degree of certainty. The facility contribution is discretionary after the operating reserve is established.
- The client begins co-sponsor outreach in 2031 and needs a credible contribution range.
- The case says payments are not inflation-adjusted; inflation must still be considered for real purchasing power and facility costs.

The IPS requirements cap the elevator pitch at 50 words and the policy statement at 500 words. They specify that detailed reserve calculations, full projections, final facility-contribution ranges, and co-sponsor communication belong in the Final Report rather than the IPS. The IPS must not contain charts, external links, footnotes, or formal citations.

## Long historical proxy data: 1928-2025

**Source:** Aswath Damodaran, NYU Stern, Historical Returns on Stocks, Bonds and Bills.

URL: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html

The downloaded/local dataset `data/us_long_history_1928_2025.csv` contains annual observations from 1928 through 2025:

- `sp500_total_return`: S&P 500 annual total return, including dividends.
- `tbond10_total_return`: U.S. 10-year Treasury annual total return, including coupon income and bond-price movements.

The NYU page is labeled “1928-2024” in its title but includes a 2025 row and says it was updated January 5, 2026. The 2025 row reports 17.78% for the S&P 500 including dividends and 7.80% for the 10-year Treasury. The analysis uses these 98 annual rows.

These are broad U.S. asset-class proxies. They are not direct VTI/VXUS data and do not replicate the team's actual individual Treasury-note holdings. There is no international-equity return series in the 1928-2025 proxy test.

## Modern ETF check: 2011-2025

**Source:** Total Real Returns, VTI vs. VXUS annual total returns, dividends reinvested.

URL: https://totalrealreturns.com/n/VTI,VXUS

The dataset `data/modern_asset_returns_2011_2025.csv` uses annual total returns for VTI and VXUS from 2011 through 2025. The Treasury comparison column comes from the long-run 10-year Treasury series. The modern correlation estimates are descriptive and based on 15 annual observations only.

## Historical rolling test

Each contiguous six-year period in 1928-2025 is treated as a historical scenario for the six investment years 2027-2032. The model starts with $300,000, adds $150,000 at the beginning of the second modeled year, and applies each policy's annual equity weights to S&P 500 and 10-year Treasury returns. There are 93 overlapping six-year windows. Because they overlap, they are not independent observations and should not be interpreted as a statistical confidence interval.

## Monte Carlo-style historical moving-block bootstrap

The model creates 100,000 six-year paths by resampling two paired, contiguous 3-year blocks from the 1928-2025 annual series. Pairing means each sampled annual stock return remains matched with that same year's Treasury return. Contiguity preserves observed runs within each three-year block. The boundary between the independently drawn blocks breaks continuity, and no method can resample an extreme event absent from the historical sample.

For each policy, the output reports percentiles of ending wealth before the beginning of the first 2033 payment. The reported path share above $500,000 is the proportion of model paths that reach the no-yield cash benchmark; it is not a forecast probability or guarantee.

### Tail-risk definition

For a 2033 terminal portfolio value `V`, the one-sided funding gap is:

`G = max($500,000 - V, 0)`

`CVaR95 funding gap` is the average of the largest 5% of simulated funding gaps. This is a conditional tail measure of the liability shortfall, not conventional CVaR of market losses or percentage return.

## Glide-path policies

- Constant: 65% equity each year.
- Five-percentage-point glide: 65%, 60%, 55%, 50%, 45%, 40% equity across 2027-2032.
- Eight-percentage-point glide: 65%, 57%, 49%, 41%, 33%, 25% equity.

The remainder is invested in the Treasury total-return proxy. The five-point policy is the baseline because it improves the downside percentile over constant 65/35 while retaining more median wealth than the eight-point path. The eight-point path is the defined fallback if the five-point path falls below the 95% modeled funding target but the eight-point path meets it. If neither meets 95%, facility spending is set to zero and all available discretionary capital is prioritized to the reserve; the model target miss is disclosed.

## 2031 facility-contribution analysis

The model uses the same paired six-year paths for both the January 1, 2031 portfolio value (after 2027-2030 returns) and the January 1, 2033 value (after 2031-2032 returns). This avoids independently sampling the later two years after conditioning on the 2031 balance.

Paths are grouped by their simulated 2031 balance: bottom 10%, 10th-25th percentile, middle 50%, 75th-90th percentile, and top 10%. For each group, the model calculates the 5th-percentile 2033 value. The conservative benchmark assumes $500,000 in cash is needed to fund all ten $50,000 payments with no post-2033 return. The maximum facility cap is half of the positive 5th-percentile surplus above the reserve, rounded down to the nearest $5,000. If the surplus is not positive, the cap is zero.

This is a planning rule and a conditional scenario result, not a promise that the client can contribute that amount in 2031. The cap must be recalculated using the actual 2031 account value and the actual 2033 Treasury spot curve.

## Liability valuation

At the beginning of 2033, the first $50,000 payment is due immediately and is not discounted. The other nine $50,000 payments are discounted using annual-compounded zero-coupon spot rates for maturities one through nine years:

`Reserve PV = $50,000 + sum[$50,000 / (1 + s_t)^t] for t = 1,...,9`

The spot rates must be zero-coupon rates (or derived from Treasury STRIPS prices), not par coupon yields without bootstrapping. The current spot-rate template is a blank input file because the actual 2033 curve is not known today. A flat 0%-5% sensitivity is included for transparency only.

## StockTrak implementation audit

The WInS/StockTrak position snapshot is supplied by the team. Calculations include:

- Six position rows: VTI, VXUS, and four Treasury notes.
- Face value per bond unit: $1,000, as stated in StockTrak detail.
- Coupon rates and maturity dates as supplied.
- Annual coupon run-rate: face value times coupon rate, totaling $5,225 before the 2031 note matures.
- Exact coupon dates are not in the supplied snapshot, so coupon payments are not counted as cash available for January 1 liability dates.
- The 2036 Treasury's displayed yield is flagged as anomalous given its reported premium price and 4.50% coupon; this quote is not used in return projections.
- Sum of six line-item market values ($295,589.14) plus accrued bond interest ($1,073.63) plus cash ($740.31) equals $297,403.08, one cent above the reported current portfolio value ($297,403.07). The separate summary field “Total Market Value of All Positions” ($297,003.14) differs from line-item positions by $1,414 and is left unresolved.

The StockTrak account is implementation evidence only. It is not added to Laura's case-study projection.

## Inflation

The ten payments remain fixed at $50,000 nominal, as required by the case. A separate sensitivity expresses those fixed payments in 2026 purchasing-power dollars under constant 2%, 3%, and 5% inflation scenarios. Facility construction costs in Taiwan may also be affected by local inflation and USD/TWD exchange-rate movements; the model does not forecast those values.

## Sources for security mechanics

- U.S. TreasuryDirect, Treasury Notes: notes pay fixed interest every six months and may be held to maturity or sold before maturity: https://treasurydirect.gov/marketable-securities/treasury-notes/
- U.S. TreasuryDirect, STRIPS: zero-coupon components of Treasury securities can be used to target known future payment dates: https://www.treasurydirect.gov/marketable-securities/strips/
- StockTrak, Available Bonds: security symbols, type, coupon, and maturity: https://www.stocktrak.com/available-bonds/

These public sources describe general security mechanics. Actual StockTrak bond metadata and the user's supplied snapshot are used for the team positions.
