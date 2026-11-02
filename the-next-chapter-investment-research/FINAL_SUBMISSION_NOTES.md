# Final Submission Notes

## Deliverables

- `reports/IPS_text.md` and the IPS DOCX/PDF follow the supplied IPS limits: one title page plus two strategy pages, a 47-word elevator pitch, and a 360-word policy statement. The title page contains placeholders for official team information.
- `reports/` contains the requirements crosswalk, research methodology, chart guide, strengths/limitations assessment, competition-readiness assessment, document builder, and AI-use disclosure template.
- `src/`, `data/`, `results/`, and `tests/` contain the reproducible quantitative analysis.

## Policy completeness

The strategy defines all requested policy elements: the ten operating payments; a 2033 reserve; a ten-rung cash/Treasury reserve structure; annual reserve drawdown through 2042; a 95% internal modeled funding target; a five-point baseline glide path with an eight-point contingency; a conditional 2031 facility range; and nominal-versus-real inflation treatment. The 95% target is a team policy definition, not a guarantee. The five-point path reaches 96.009% at an illustrative 3% reserve-cost sensitivity but only 91.822% at the $500,000 zero-yield stress. The eight-point fallback improves these to 96.744% and 92.277%, respectively. If neither policy reaches 95%, facility contribution is $0 and the model shortfall must be disclosed.

## Important modeling boundaries

- The client projection uses only the case-study contributions: $300,000 at the beginning of 2027 and $150,000 at the beginning of 2028.
- StockTrak holdings are implementation evidence and are audited separately; they are not added to Laura's hypothetical long-term account.
- The 1928-2025 long sample uses S&P 500 and U.S. 10-year Treasury total returns as broad U.S. asset-class proxies, not literal VTI/VXUS or individual-note histories.
- The 100,000-path paired three-year moving-block bootstrap produces model frequencies, not objective real-world probabilities or guarantees.
- The $500,000 reserve benchmark assumes zero return after the beginning of 2033. Actual reserve cost must be recalculated from the 2033 Treasury zero-coupon spot curve or STRIPS prices.
- The reserve design places $50,000 in immediately available cash/T-bills and matches the remaining nine payments to nominal Treasury STRIPS or dedicated cash flows available by each January due date. Actual CUSIPs are selected at the time the reserve is established.
- Exact coupon dates for the StockTrak notes were not provided; their coupon run-rate is reported, but coupons are not treated as available on January 1 liability dates.
- The StockTrak account value reconstructs to within one cent using line-item market values, accrued interest, and cash, but its separate “Total Market Value of All Positions” field is inconsistent and unexplained.
- The middle-50% 2031-balance scenario supports a conditional $20,000 facility cap under the $500,000 no-yield benchmark; lower bands support $0. Recalculate from actual 2031 account value and 2033 curve.

## Run and verify

```bash
pip install -r requirements.txt
python src/model.py
python src/policy_outputs.py
python -m unittest discover -s tests -v
```

The current test suite contains 32 tests. Generated outputs are written to `results/`.

## Competition compliance

Wharton's AI policy must be followed. The team should independently review and understand all retained calculations and code, accurately disclose any AI assistance retained, and cite it as required. The template in `reports/ai_use_disclosure_template.md` must be edited to reflect actual use; do not claim verification that the team has not performed.
