from pathlib import Path
import sys, json, math
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
FIG = OUT / "figures"
EXPORT = Path("/mnt/data")

PITCH = ("Protect Laura’s ten operating payments first; use only surplus capital for her creative residency. "
         "A diversified equity-and-Treasury portfolio de-risks by five percentage points annually. "
         "In 2033, a separately priced Treasury reserve will match each payment; downside tests and a "
         "conditional facility rule keep liabilities ahead of construction.")
SECTIONS = [
("Objective.", "Laura contributes $300,000 at the beginning of 2027 and $150,000 at the beginning of 2028. The portfolio’s first obligation is ten fixed $50,000 payments due at the beginning of each year from 2033 through 2042. No grants or co-sponsors are counted toward these operating payments. Facility funding is secondary."),
("Construction and diversification.", "The initial target is 65% equities and 35% U.S. Treasuries: 47% VTI and 18% VXUS. VTI and VXUS diversify companies and geography but share global equity-market risk. Treasuries add distinct interest-rate and contractual cash-flow exposures; historical correlations are regime-dependent, not constant."),
("Dynamic allocation.", "Equity targets decline by five percentage points of total portfolio value annually: 65%, 60%, 55%, 50%, 45%, and 40% from 2027 through 2032, with annual rebalancing. Each year, we test the probability of reaching the priced reserve. If the five-point path falls below our 95% target, we test an accelerated eight-point path. If neither meets the target, facility spending is zero and all available capital is prioritized to the reserve."),
("Operating reserve.", "At the beginning of 2033, before the first payment or construction spending, we segregate a fully priced operating reserve. The first $50,000 is held in immediately available cash or Treasury bills; the remaining nine $50,000 liabilities are matched to nominal U.S. Treasury STRIPS or dedicated Treasury cash flows available no later than each January due date. Early proceeds stay in cash or Treasury bills. One rung is retired after each payment; reserve assets never fund construction."),
("Funding certainty and inflation.", "We define high funding certainty as at least 95% modeled likelihood that portfolio assets can purchase the complete reserve. The historical bootstrap reaches 96.0% at an illustrative 3% flat-rate reserve valuation but 91.8% at the $500,000 zero-yield stress; neither is a guarantee. The actual 2033 zero-coupon curve sets reserve cost. Payments remain fixed nominally; we separately monitor purchasing-power loss, Taiwan construction inflation, and USD/TWD risk."),
("Facility and flexibility.", "In 2031, co-sponsors receive a conditional $0-$20,000 planning range, recalculated from Laura’s observed balance and updated reserve price. No more than half of positive fifth-percentile surplus after the reserve may fund construction, rounded down to $5,000; otherwise contribution is zero. Unused surplus preserves flexibility.")
]

# Helpers
def shade(cell, fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill); tcPr.append(shd)

def set_cell(cell, text, bold=False, color=None, size=8.3):
    cell.text=''; p=cell.paragraphs[0]
    p.paragraph_format.space_after=Pt(0); p.paragraph_format.space_before=Pt(0); p.paragraph_format.line_spacing=1.0
    r=p.add_run(str(text)); r.bold=bold; r.font.name='Aptos'; r.font.size=Pt(size)
    if color: r.font.color.rgb=RGBColor(*color)
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER

def add_table(doc, headers, rows, widths=None, font=8.2):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    for i,h in enumerate(headers):
        set_cell(t.rows[0].cells[i],h,True,(255,255,255),font); shade(t.rows[0].cells[i],'23384D')
    for ridx,row in enumerate(rows):
        cells=t.add_row().cells
        for i,val in enumerate(row):
            set_cell(cells[i],val,size=font)
            if ridx%2: shade(cells[i],'F2F5F8')
    if widths:
        for row in t.rows:
            for i,w in enumerate(widths): row.cells[i].width=Inches(w)
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(2); p.paragraph_format.space_before=Pt(1)
    return t

def heading(doc, text, level=1, new_page=False):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(6 if level==1 else 4); p.paragraph_format.space_after=Pt(3); p.paragraph_format.keep_with_next=True
    if new_page: p.paragraph_format.page_break_before=True
    r=p.add_run(text); r.bold=True; r.font.name='Aptos Display'; r.font.size=Pt(14 if level==1 else 10.5); r.font.color.rgb=RGBColor(35,56,77)
    return p

def body(doc, text, size=9.2, after=4):
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(after); p.paragraph_format.line_spacing=1.05
    r=p.add_run(text); r.font.name='Aptos'; r.font.size=Pt(size)
    return p

def bullet(doc, text, size=9):
    p=doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after=Pt(2); p.paragraph_format.line_spacing=1.0
    r=p.add_run(text); r.font.name='Aptos'; r.font.size=Pt(size)
    return p

def picture(doc, name, caption, width=6.2):
    path=FIG/name
    if not path.exists(): return
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(1); p.paragraph_format.space_after=Pt(0)
    p.add_run().add_picture(str(path),width=Inches(width))
    cp=doc.add_paragraph(); cp.alignment=WD_ALIGN_PARAGRAPH.CENTER; cp.paragraph_format.space_after=Pt(3); cp.paragraph_format.line_spacing=1.0
    r=cp.add_run(caption); r.italic=True; r.font.name='Aptos'; r.font.size=Pt(7.6); r.font.color.rgb=RGBColor(95,105,115)

def base_doc():
    d=Document(); s=d.sections[0]
    s.top_margin=Inches(.65); s.bottom_margin=Inches(.62); s.left_margin=Inches(.72); s.right_margin=Inches(.72)
    normal=d.styles['Normal']; normal.font.name='Aptos'; normal.font.size=Pt(9.2); normal.paragraph_format.space_after=Pt(4); normal.paragraph_format.line_spacing=1.05
    f=s.footer.paragraphs[0]; f.alignment=WD_ALIGN_PARAGRAPH.CENTER
    rr=f.add_run('THE NEXT CHAPTER  |  LIABILITY-AWARE INVESTMENT RESEARCH'); rr.font.name='Aptos'; rr.font.size=Pt(7); rr.font.color.rgb=RGBColor(115,125,135)
    return d

# -------- IPS --------
ips=Document(); sec=ips.sections[0]
sec.top_margin=Inches(1); sec.bottom_margin=Inches(1); sec.left_margin=Inches(1); sec.right_margin=Inches(1)
normal=ips.styles['Normal']; normal.font.name='Times New Roman'; normal.font.size=Pt(12)
normal.paragraph_format.line_spacing=2.0; normal.paragraph_format.space_after=Pt(0); normal.paragraph_format.space_before=Pt(0)
for _ in range(4): ips.add_paragraph('')
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing=1.5
r=p.add_run('THE NEXT CHAPTER'); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(24)
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing=1.5
r=p.add_run('Protecting the Ending. Investing in the Story.'); r.italic=True; r.font.name='Times New Roman'; r.font.size=Pt(14)
for _ in range(3): ips.add_paragraph('')
for label,val in [('Official Team Name:','[ENTER OFFICIAL TEAM NAME]'),('Team Members:','[First Name, Last Initial for each member]'),('WInS Username:','[ENTER WInS USERNAME]')]:
    p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(label+' '); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
    r=p.add_run(val); r.font.name='Times New Roman'; r.font.size=Pt(12)
ips.add_page_break()
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next=True
r=p.add_run('Investment Strategy Elevator Pitch'); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
p=ips.add_paragraph(PITCH); p.paragraph_format.line_spacing=2.0; p.paragraph_format.keep_together=True
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next=True
r=p.add_run('Investment Policy Statement'); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
for h,txt in SECTIONS:
    p=ips.add_paragraph(); p.paragraph_format.line_spacing=2.0; p.paragraph_format.keep_together=True; p.paragraph_format.widow_control=True
    r=p.add_run(h+' '); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
    r=p.add_run(txt); r.font.name='Times New Roman'; r.font.size=Pt(12)
ips_path=EXPORT/'The_Next_Chapter_Final_IPS.docx'; ips.save(ips_path)

# -------- Research appendix --------
summary=json.loads((OUT/'key_results.json').read_text()); policy=json.loads((OUT/'policy_summary.json').read_text())
roll=pd.read_csv(OUT/'rolling_six_year_summary.csv'); boot=pd.read_csv(OUT/'bootstrap_policy_comparison.csv')
fac=pd.read_csv(OUT/'facility_contribution_scenarios.csv'); funding=pd.read_csv(OUT/'funding_certainty_assessment.csv')
reserve=pd.read_csv(OUT/'reserve_pv_sensitivity.csv'); ladder=pd.read_csv(OUT/'reserve_ladder_illustrative_flat_3pct.csv')
rollforward=pd.read_csv(OUT/'reserve_rollforward_illustrative_flat_3pct.csv')
alloc=pd.read_csv(OUT/'wins_current_allocation.csv'); bridge=pd.read_csv(OUT/'wins_principal_only_liability_bridge.csv')
bonds=pd.read_csv(OUT/'wins_bond_position_audit.csv'); cor=pd.read_csv(OUT/'historical_stock_bond_correlations.csv')
modern_cor=pd.read_csv(OUT/'modern_vti_vxus_treasury_correlations.csv'); recon=pd.read_csv(OUT/'wins_account_reconciliation.csv')
infl=pd.read_csv(OUT/'inflation_sensitivity.csv')

rep=base_doc()
# Page 1
p=rep.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(1)
r=p.add_run('THE NEXT CHAPTER'); r.bold=True; r.font.name='Aptos Display'; r.font.size=Pt(23); r.font.color.rgb=RGBColor(35,56,77)
p=rep.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(6)
r=p.add_run('Liability Funding, Reserve Design, and Facility Recommendation'); r.font.name='Aptos Display'; r.font.size=Pt(14); r.font.color.rgb=RGBColor(71,95,116)
body(rep,'Research supplement supporting the team’s Investment Policy Statement. It separates the client’s required cash flows, the portfolio accumulation model, the future operating reserve, and the team’s StockTrak implementation.',9.4)
heading(rep,'Decision in one minute')
bullet(rep,'Protect the ten $50,000 operating payments before any facility contribution. These payments are fixed nominal obligations due at the beginning of each year from 2033 through 2042.')
bullet(rep,'Use a 65/35 starting portfolio and reduce equities by five percentage points annually, reaching 40% equities by 2032. Reassess funding coverage every year.')
bullet(rep,'Define high funding certainty as a 95% modeled reserve-funding threshold. The five-point path passes at 96.01% under the illustrative 3% reserve sensitivity, but not the zero-yield stress; an eight-point fallback is tested if coverage weakens.')
bullet(rep,'In 2033, segregate immediate cash for the first payment and nine Treasury-matched future rungs. Pay one rung each January through 2042.')
bullet(rep,'Use a conditional $0-$20,000 planning range for the 2031 co-sponsor discussion only in the middle-50% modeled 2031-balance scenario; recalculate from Laura’s actual balance and the then-current Treasury zero curve.')
heading(rep,'Requirement coverage')
req=pd.read_csv(OUT/'requirement_coverage_matrix.csv')
req_rows=[[r.requirement,r.policy_rule,r.evidence_and_limitation] for r in req.itertuples()]
add_table(rep,['Wharton requirement','Our rule','Status / limitation'],req_rows,[1.45,3.15,2.35],7.1)
# Page 2: liabilities
heading(rep,'1. Client obligations and reserve valuation', new_page=True)
body(rep,'The case study specifies $300,000 at the beginning of 2027 and $150,000 at the beginning of 2028, with no other portfolio contributions or withdrawals before 2033. Laura then makes ten $50,000 payments at the beginning of each year from 2033 through 2042. The first payment is immediate at the beginning of 2033; it is not discounted.')
add_table(rep,['Payment date','Nominal cash due','Years from reserve date','PV at illustrative 3%'],[[f'{2033+i}-01-01','$50,000',str(i),f'${50000/(1.03**i):,.0f}'] for i in range(10)],[1.55,1.45,1.35,1.55],8)
body(rep,'The reserve is priced using annual-effective zero-coupon spot rates s(t), not raw par coupon yields: Reserve PV = $50,000 + Σ[$50,000/(1+s(t))^t] for t = 1…9. At a flat 3% sensitivity, reserve PV is $439,305. At 0%, the full $500,000 nominal amount is needed. The 3% rate is a planning sensitivity, not a forecast or promised return.',9)
add_table(rep,['Flat discount-rate sensitivity','Reserve PV on 1 Jan 2033'],[[f'{r.flat_rate:.0%}',f'${r.reserve_pv_usd:,.0f}'] for r in reserve.itertuples()],[2.7,2.6],8.5)
picture(rep,'06_reserve_cost_sensitivity.png','Figure 1. Reserve value changes with the assumed flat discount rate.',5.6)
body(rep,'At the start of 2033, the actual reserve cost must be recalculated from the then-current zero-coupon Treasury curve or STRIPS prices. Treasury par yields are not interchangeable with zero-coupon spot rates unless bootstrapped.',8.6)
# Page 3: reserve composition
heading(rep,'2. Initial reserve composition and annual drawdown', new_page=True)
body(rep,'The reserve is established at the beginning of 2033, before the first $50,000 payment and before any discretionary facility spending. The first payment is held in immediately available cash or Treasury bills. Each of the remaining nine liabilities is matched to a nominal Treasury STRIP or dedicated Treasury cash flow that is available no later than the payment date. If an instrument matures earlier, its proceeds remain in cash or Treasury bills until the payment is due.')
ladder_rows=[]
for r in ladder.itertuples():
    rate='Immediate' if pd.isna(r.zero_coupon_spot_rate) else f'{r.zero_coupon_spot_rate:.1%}'
    ladder_rows.append([str(r.payment_year),r.payment_date,f'${r.nominal_cash_required_usd:,.0f}',rate,f'${r.initial_purchase_cost_usd:,.0f}',
                        'Cash / T-bill' if r.payment_year==2033 else 'Treasury STRIP / matched cash flow'])
add_table(rep,['Payment year','Date','Face cash flow','Rate input','Illustrative cost','Target asset'],ladder_rows,[.75,1.1,1.0,.75,1.1,2.0],7.5)
body(rep,f'Total illustrative reserve cost at a flat 3% zero curve: ${ladder.initial_purchase_cost_usd.sum():,.0f}. This is a worked example, not an executable set of 2033 CUSIPs or a statement that the required securities are currently held.',8.7)
heading(rep,'How the reserve changes from 2033 to 2042',2)
add_table(rep,['Payment date','Payment made','Rungs remaining after payment','Remaining nominal liabilities'],[[r.payment_date,f'${r.payment_made_usd:,.0f}',str(r.rungs_remaining_after_payment),f'${r.future_nominal_payments_remaining_usd:,.0f}'] for r in rollforward.itertuples()],[1.3,1.15,2.2,1.75],7.7)
body(rep,'The reserve becomes shorter and more cash-like as each January payment is made. Its growth assets are not used for the scheduled operating payments after the liability-matched reserve has been purchased. Treasury maturity dates should be selected in 2033 so proceeds are available by the case-study payment dates; the template does not assume an exact January 1 STRIP maturity exists.',8.5)
# Page 4: allocation
heading(rep,'3. Growth portfolio and five-point glide path', new_page=True)
body(rep,'The accumulation projection begins with Laura’s case-study contributions, not the StockTrak account balance: $300,000 at the beginning of 2027 and $150,000 at the beginning of 2028. Six annual return periods represent 2027-2032. The second contribution is added before the 2028 return is applied.')
add_table(rep,['Year','Equity target','Treasury / cash target','Rule'],[[str(y),f'{w:.0%}',f'{1-w:.0%}','Annual rebalance'] for y,w in zip(range(2027,2033),[.65,.60,.55,.50,.45,.40])],[.9,1.2,1.65,1.5],8)
picture(rep,'01_glide_path.png','Figure 2. Five-percentage-point reduction in equity exposure each year.',5.5)
body(rep,'VTI and VXUS diversify the equity sleeve across the United States and other markets. They do not eliminate shared global equity risk. Treasury securities add a distinct interest-rate and sovereign cash-flow exposure, but correlations are regime-dependent. We do not assume stocks and bonds always move in opposite directions.',8.8)
heading(rep,'Reserve-funding override',2)
body(rep,'At each annual review, price the reserve using the latest available zero-curve estimate and calculate the share of paired historical-bootstrap paths that can fund it. Keep the five-point glide if it meets the 95% target. If it fails but the eight-point glide passes, adopt the accelerated eight-point path. If neither passes, set facility spending to zero, direct all available discretionary capital toward the reserve, and disclose that the target remains unmet. This is preventive; it cannot reverse losses already incurred or guarantee sufficiency.',8.45)
# Page 5: empirical and bootstrap
heading(rep,'4. Historical evidence and funding-certainty standard', new_page=True)
body(rep,'The long sample contains 98 annual observations from 1928-2025: S&P 500 total returns including dividends and U.S. 10-year Treasury total returns. These are U.S. asset-class proxies, not literal VTI/VXUS or individual-note histories. Applying the contribution and glide-path rules to all contiguous six-year windows produces 93 overlapping historical windows. The five-point policy’s worst window is 1929-1934 at about $366,263; the median is about $686,880; 88 of 93 windows reached $500,000. Overlapping windows are descriptive scenarios, not independent observations.')
picture(rep,'02_historical_rolling_windows.png','Figure 3. Historical six-year outcomes; windows overlap.',5.4)
boot_rows=[]
labels={'constant_65_35':'Constant 65/35','five_percentage_point_glide':'Five-point glide','eight_percentage_point_glide':'Eight-point glide'}
for r in boot.itertuples():
    boot_rows.append([labels[r.policy],f'${r.median_terminal_value_usd:,.0f}',f'${r.p05_terminal_value_usd:,.0f}',f'{r.share_at_or_above_500k:.1%}',f'${r.cvar95_funding_gap_usd:,.0f}'])
add_table(rep,['Policy','Median 2033 value','5th percentile','Paths ≥ $500k','Worst-5% avg. gap'],boot_rows,[1.45,1.25,1.1,1.1,1.35],7.4)
picture(rep,'03_bootstrap_policy_comparison.png','Figure 4. 100,000 paired three-year moving-block bootstrap paths.',5.0)
body(rep,'The five-point path has a $702,063 median and $459,970 5th percentile. It reaches the illustrative $439,305 reserve in 96.01% of paths, but the $500,000 zero-yield benchmark in 91.82%. The eight-point fallback has a $467,739 5th percentile; its corresponding shares are 96.74% and 92.28%. The five-point path’s average worst-5% funding gap is $111,467 (a liability shortfall, not market-loss CVaR).',8.1)
body(rep,'The reserve cost equals the five-point 5th percentile at a flat-rate equivalent of about 1.90%; the eight-point cutoff is about 1.51%. Each year, keep five points if its modeled funding share is at least 95%; otherwise switch to eight points if it passes. If neither passes, facility spending is zero and the target miss is disclosed. No resampling method guarantees future outcomes.',8.1)
# Page 6: contribution
heading(rep,'5. 2031 co-sponsor contribution recommendation', new_page=True)
body(rep,'The model follows the same six-year paired return paths to observe both the January 1, 2031 balance and the January 1, 2033 value. Paths are grouped by their 2031 balance. For each group, the model estimates the 5th-percentile 2033 value. The conservative benchmark is $500,000, equivalent to funding all ten payments with no return after the reserve is established.')
add_table(rep,['2031 balance band','Median 2031 value','2033 conditional P05','Cap under $500k reserve'],[[r['2031_balance_band'],f"${r['2031_balance_median_usd']:,.0f}",f"${r['2033_p05_value_usd']:,.0f}",f"${r['facility_cap_at_0pct_reserve_yield_usd']:,.0f}"] for _,r in fac.iterrows()],[2.1,1.45,1.45,1.35],7.5)
picture(rep,'04_facility_scenarios.png','Figure 5. Downside-tested contribution cap by 2031 balance band and reserve valuation.',5.6)
body(rep,'In the middle 50% of modeled 2031 balances, the median 2031 value is about $607,879 and the conditional 2033 fifth percentile is about $548,039. Against the $500,000 reserve benchmark, the downside surplus is about $48,039. The rule spends at most half that surplus and rounds down to $5,000, giving a conditional $20,000 cap. Within this middle-50% 2031 band, 96.88% of paths retain at least $520,000 after a $20,000 contribution. This is a conditional model result, not an unconditional confidence level. The lower 10th-25th 2031 band supports $0.',8.3)
body(rep,'Recommended co-sponsor planning range: $0-$20,000, with the upper end conditional on Laura’s observed 2031 portfolio value and a refreshed 2033 Treasury zero curve. The range is not a guarantee. If the actual 2031 balance or updated reserve price does not support the fifth-percentile coverage test, the recommendation is $0. Do not pledge operating-reserve capital to construction.',8.45)
# Page 7: StockTrak audit
heading(rep,'6. StockTrak implementation audit', new_page=True)
body(rep,'The following is the team’s supplied competition account snapshot. It is separate from Laura’s hypothetical long-term account and is not added to the client projection.')
add_table(rep,['Holding','Qty','Face value','Market value','Annual coupon'],[[r.symbol,f'{r.quantity:g}',f'${r.face_value_total_usd:,.0f}' if pd.notna(r.face_value_total_usd) else '-',f'${r.market_value:,.2f}',f'${r.annual_coupon_run_rate_usd:,.0f}' if pd.notna(r.annual_coupon_run_rate_usd) else '-'] for r in bonds.itertuples()],[2.1,.55,1.05,1.35,1.2],7.4)
add_table(rep,['Current allocation','Value incl. accrued','Weight'],[[r.asset,f'${r.value_usd:,.2f}',f'{r.weight:.2%}'] for r in alloc.itertuples()],[2.75,1.8,1.35],8)
body(rep,'The six line-item market values total $295,589.14. Adding $1,073.63 accrued bond interest and $740.31 cash reconstructs $297,403.08, one cent above the reported $297,403.07. The separate summary field “Total Market Value of All Positions” is $297,003.14, $1,414 below the six line-item total; the discrepancy is unresolved. The account reports $90 commissions and -0.87% portfolio return versus -1.29% for the S&P 500, but the short period is not evidence of long-run strategy success.',8.3)
picture(rep,'05_wins_principal_bridge.png','Figure 6. Current WInS principal maturities versus cumulative January payment needs; coupons are excluded because exact dates were not supplied.',5.3)
body(rep,'The four notes represent $105,000 face value and a $5,225 initial annual coupon run-rate. Frequency is shown as 6, interpreted as semiannual for coupon sizing, but actual coupon dates have not been confirmed. The February 2036, February 2037, and May 2038 maturities occur after the corresponding January payments. The 2036 reported yield is anomalous relative to its premium price and coupon and is excluded from return assumptions. These existing notes are not the 2033 reserve ladder.',8.2)
# Page 8: risk, inflation, sources
heading(rep,'7. Diversification, inflation, and limitations', new_page=True)
add_table(rep,['Historical period','Observations','S&P 500 / 10Y Treasury correlation'],[[r.period,str(r.n_years),f'{r.stock_bond_correlation:.3f}'] for r in cor.itertuples()],[2.1,1.1,2.8],8)
body(rep,'The full 1928-2025 stock/Treasury correlation is near zero (+0.018), but it is not stable: +0.323 in 1961-1999 and -0.365 in 2000-2025. In 2011-2025, VTI and VXUS correlation is about +0.77. Geographic stock diversification reduces country concentration, but both equity funds retain common market risk.',8.6)
picture(rep,'07_correlation_regimes.png','Figure 7. Stock-bond correlation changes by historical regime.',4.2)
body(rep,'The ten operating payments remain fixed at $50,000 nominally. Inflation reduces purchasing power: at 3% annually, a 2042 payment is about $31,158 in 2026 dollars. Taiwan facility costs also face local inflation and USD/TWD currency risk, which the model does not forecast.',8.2)
picture(rep,'08_inflation_purchasing_power.png','Figure 8. Real purchasing power of the fixed nominal payments.',4.2)
heading(rep,'Limitations and interpretation',2)
body(rep,'The 1928-2025 sample is U.S.-centric; VTI/VXUS data cover 2011-2025 only. Annual returns omit intra-year paths, fees, and taxes. The bootstrap cannot produce events absent from its sample. The accumulation bond sleeve is a 10-year Treasury proxy, not a repricing of the WInS notes. Actual 2033 zero rates, STRIP instruments, and current note coupon dates remain future or unverified inputs. The 95% result is model-dependent; the zero-yield stress is below target.',7.9)
heading(rep,'Sources',2)
body(rep,'Damodaran (NYU Stern), historical stocks, bonds and bills, 1928-2025: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html',7.0,1)
body(rep,'Total Real Returns, VTI/VXUS total returns, 2011-2025: https://totalrealreturns.com/n/VTI,VXUS',7.0,1)
body(rep,'TreasuryDirect, Treasury Notes and STRIPS: https://treasurydirect.gov/marketable-securities/treasury-notes/ ; https://www.treasurydirect.gov/marketable-securities/strips/',7.0,1)
body(rep,'Wharton 2026-2027 Competition Guide, Laura Gao Case Study, and IPS Requirements (team-supplied documents).',7.0,1)

rep_path=EXPORT/'The_Next_Chapter_Research_Appendix.docx'; rep.save(rep_path)

# Requirements crosswalk is maintained as a standalone reviewed source file in reports/.

print('Created:', ips_path, rep_path)
print('Elevator pitch words:', len(PITCH.split()))
print('IPS words:', sum(len((h+' '+txt).split()) for h,txt in SECTIONS))
