# Competition Readiness: Strengths, Weaknesses, and Candid Assessment

## Strongest aspects

- **Client-first strategy:** Ten fixed operating payments are the first priority; facility funding is secondary.
- **Specific investment policy:** The five-percentage-point equity glide path is measurable and testable, with an explicit eight-point fallback.
- **Liability implementation:** The reserve is valued by payment date. It begins with immediate cash for 2033 and uses nine nominal Treasury rungs for 2034-2042. One rung is retired after each January payment.
- **Defined funding standard:** The team defines “high degree of funding certainty” as at least 95% modeled probability of accumulating the priced reserve. This is a team policy definition, not a guarantee or Wharton-mandated percentage.
- **Quantitative evidence:** 98 annual U.S. proxy observations, 93 overlapping six-year historical windows, and 100,000 paired three-year moving-block bootstrap paths compare constant 65/35, five-point, and eight-point policies.
- **Transparent fallback:** At an illustrative flat 3% reserve valuation, five-point modeled coverage is 96.009% and eight-point coverage is 96.744%. At the $500,000 zero-yield stress, they are 91.822% and 92.277%; neither meets 95%, so the facility allocation becomes zero and the shortfall risk is disclosed.
- **Facility discipline:** The $0-$20,000 planning range is conditional on the observed 2031 balance and updated 2033 curve; the middle-50% modeled 2031 balance group supports a $20,000 cap, while lower bands support $0.
- **Client narrative:** “The Next Chapter” links the financial hierarchy to Laura's work without replacing the investment analysis with metaphors.

## Weaknesses and trade-offs

- **No guarantee of 2033 accumulation:** The 5-point policy's 5th-percentile terminal value is approximately $459,970. Its $500,000 no-yield reserve success share is 91.822%, below the 95% internal target. The 8-point fallback improves the 5th percentile to approximately $467,739 but still reaches $500,000 in only 92.277% of paths.
- **Reserve-rate dependence:** Both paths meet the 95% threshold at the illustrative flat 3% reserve PV; neither meets it at 0%-1%. Actual 2033 spot rates will materially affect the reserve price.
- **Proxy mismatch:** The 1928-2025 dataset uses U.S. large-cap stocks and 10-year Treasury total returns, not actual VTI/VXUS or the team's individual notes. The modern VTI/VXUS sample covers only 2011-2025.
- **Bootstrap limits:** Annual data and paired three-year blocks cannot capture every regime, monthly path, liquidity event, or event absent from the historical sample. Path frequencies are not real-world probabilities.
- **Accumulation fixed-income approximation:** The simulation uses a 10-year Treasury total-return proxy rather than repricing each actual security from a full simulated yield curve.
- **WInS holdings are not the reserve:** Current notes total $105,000 face value and do not independently cover all ten $50,000 liabilities. Three maturities occur after their corresponding January payment dates. Coupon dates were not supplied and are excluded from the January-liquidity bridge.
- **Future execution variables:** The actual 2033 zero curve, specific STRIPS/CUSIPs, and precise cash availability must be determined in 2033.
- **Facility contribution is conditional:** The $20,000 cap applies to the middle 50% 2031-balance scenario and the $500,000 no-yield reserve benchmark; lower balance scenarios support $0. It must not be communicated as a guaranteed contribution.
- **StockTrak data oddities:** The account value reconciles to the supplied line items plus accrued interest and cash within one cent, but the separate “Total Market Value of All Positions” field is inconsistent. The 2036 bond's displayed yield is also anomalous and unused.

## Candid competition assessment

The project now addresses all major case-study policy components: the ten liabilities, initial reserve, reserve drawdown through 2042, a defined certainty standard, a glide-path baseline and fallback, inflation, a conditional facility rule, and 2031 co-sponsor communication. The supporting model and code provide evidence and make assumptions auditable.

The project's strength is its integrated liability-driven approach, not the number of quantitative terms. The principal vulnerability remains that the 95% funding target is conditional on the assumed reserve cost: under the zero-yield stress, even the eight-point fallback does not meet it. The strategy addresses this transparently with zero facility spending and a reserve-first policy, but cannot guarantee that market assets will reach the reserve price by 2033.

No responsible probability of winning can be assigned without the other teams' submissions and full judging results. The project has the ingredients of a potentially competitive submission if the team understands, independently verifies, and clearly explains the model and its limitations. Technical depth alone does not establish a likely win.
