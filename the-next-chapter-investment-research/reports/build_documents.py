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
OUT = ROOT / 'results'
FIG = OUT / 'figures'
EXPORT = Path('/mnt/data')

# ---------- shared helpers ----------
def set_cell_shading(cell, fill='EAF0F6'):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)

def set_cell_text(cell, text, bold=False, color=None, size=9):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(str(text)); r.bold = bold; r.font.name = 'Aptos'; r.font.size = Pt(size)
    if color: r.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def add_table(doc, headers, rows, widths=None, font=8.5):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    for i,h in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], h, bold=True, color=(255,255,255), size=font)
        set_cell_shading(table.rows[0].cells[i], '23384D')
    for ridx,row in enumerate(rows):
        cells = table.add_row().cells
        for i,val in enumerate(row):
            set_cell_text(cells[i], val, size=font)
            if ridx % 2 == 1: set_cell_shading(cells[i], 'F3F6F9')
    if widths:
        for row in table.rows:
            for i,w in enumerate(widths): row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table

def add_bullet(doc, text, level=0):
    p=doc.add_paragraph(style='List Bullet' if level==0 else 'List Bullet 2')
    p.paragraph_format.space_after=Pt(2)
    p.paragraph_format.line_spacing=1.08
    p.add_run(text)
    return p

def add_heading(doc, text, level=1):
    p=doc.add_paragraph()
    p.paragraph_format.space_before=Pt(8 if level==1 else 5)
    p.paragraph_format.space_after=Pt(3)
    p.paragraph_format.keep_with_next=True
    r=p.add_run(text); r.bold=True; r.font.name='Aptos Display'; r.font.size=Pt(15 if level==1 else 11.5); r.font.color.rgb=RGBColor(35,56,77)
    return p

def add_body(doc, text, size=9.5):
    p=doc.add_paragraph()
    p.paragraph_format.space_after=Pt(4)
    p.paragraph_format.line_spacing=1.08
    r=p.add_run(text); r.font.name='Aptos'; r.font.size=Pt(size)
    return p

def add_picture(doc, name, caption, width=6.2):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(1)
    p.add_run().add_picture(str(FIG/name), width=Inches(width))
    cp=doc.add_paragraph(); cp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.space_after=Pt(5); cp.paragraph_format.line_spacing=1.0
    r=cp.add_run(caption); r.italic=True; r.font.name='Aptos'; r.font.size=Pt(8); r.font.color.rgb=RGBColor(90,100,110)

def base_doc():
    d=Document()
    sec=d.sections[0]
    sec.top_margin=Inches(.72); sec.bottom_margin=Inches(.68); sec.left_margin=Inches(.78); sec.right_margin=Inches(.78)
    st=d.styles['Normal']; st.font.name='Aptos'; st.font.size=Pt(9.5)
    st.paragraph_format.space_after=Pt(4); st.paragraph_format.line_spacing=1.08
    # footer
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fr=footer.add_run('THE NEXT CHAPTER  |  LIABILITY-AWARE INVESTMENT RESEARCH')
    fr.font.name='Aptos'; fr.font.size=Pt(7); fr.font.color.rgb=RGBColor(115,125,135)
    return d

# ---------- IPS DOCX ----------
PITCH = ('Every strong story needs a protected ending. We separate Laura\'s mandatory operating payments from discretionary facility capital: '
         'a globally diversified growth portfolio builds assets, while a progressively de-risked Treasury portfolio is structured to match each payment. '
         'Downside testing and funding rules govern risk and contributions.')
SECTIONS = [
('Objective.', "Laura contributes $300,000 at the beginning of 2027 and $150,000 at the beginning of 2028, with no withdrawals before 2033. The portfolio's first priority is ten fixed $50,000 payments at the beginning of each year from 2033 through 2042. Facility funding is secondary and may use only capital remaining after the operating reserve is secured."),
('Construction and diversification.', 'The initial target is 65% equities and 35% U.S. Treasuries: 47% of the total portfolio in VTI and 18% in VXUS. This diversifies equity exposure across U.S. and international markets, but both funds remain exposed to global equity shocks. Treasuries provide a different source of return and contractual cash flows; stock-bond correlations can change across market regimes.'),
('De-risking.', 'The target equity allocation declines by five percentage points of total portfolio value each year, from 65% in 2027 to 40% in 2032, with Treasury and cash exposure rising correspondingly. The portfolio is rebalanced annually, using contributions and maturing assets where practical. Funding coverage is reviewed each year; if projected reserve coverage weakens, protecting the liabilities takes precedence over maintaining the glide path.'),
('Operating reserve.', 'At the beginning of 2033, before the first payment or any facility contribution, the team will segregate enough assets to secure all ten payments. The first $50,000 must be immediately liquid. Remaining liabilities will be matched with cash and nominal U.S. Treasury bills, notes, or STRIPS maturing no later than each payment date. Reserve cost will use the then-current Treasury zero-coupon spot curve, not a fixed assumed return. Cash-flow schedules must make funds available before each January payment.'),
('Risk and purchasing power.', 'The team evaluates downside funding gaps, not volatility alone, using long-run historical stress scenarios, paired stock-bond block resampling, and the fifth-percentile funding outcome. Downside severity is measured by the average funding shortfall in the worst 5% of modeled outcomes (a CVaR-style funding-gap measure). These are model-dependent scenarios, not forecasts or guarantees. Payments remain fixed at $50,000 nominally as specified; separate inflation analysis considers their real purchasing power and the effect of inflation and USD/TWD currency movements on the Taiwan facility.'),
('Facility and flexibility.', 'In 2031, co-sponsors will receive a conditional contribution range based on the then-current portfolio and updated reserve cost. The team will estimate the fifth-percentile 2033 value conditional on the observed 2031 balance. No contribution is made if that downside estimate does not cover the reserve. Otherwise, the contribution is capped at 50% of the positive surplus, rounded down to the nearest $5,000; the balance remains flexible. Operating payments take precedence over construction.')
]

ips=Document()
sec=ips.sections[0]
sec.top_margin=Inches(1); sec.bottom_margin=Inches(1); sec.left_margin=Inches(1); sec.right_margin=Inches(1)
normal=ips.styles['Normal']; normal.font.name='Times New Roman'; normal.font.size=Pt(12)
normal.paragraph_format.line_spacing=2.0; normal.paragraph_format.space_after=Pt(0); normal.paragraph_format.space_before=Pt(0)
# Title page
for _ in range(4): ips.add_paragraph('')
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing=1.5
r=p.add_run('THE NEXT CHAPTER'); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(24)
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing=1.5
r=p.add_run('Protecting the Ending. Investing in the Story.'); r.italic=True; r.font.name='Times New Roman'; r.font.size=Pt(14)
for _ in range(3): ips.add_paragraph('')
for label, value in [
    ('Official Team Name:', '[ENTER OFFICIAL TEAM NAME]'),
    ('Team Members:', '[List all members as First Name, Last Initial]'),
    ('WInS Username:', '[ENTER WInS USERNAME]')]:
    p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(label+' '); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
    r=p.add_run(value); r.font.name='Times New Roman'; r.font.size=Pt(12)
ips.add_page_break()
# Strategy page
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next=True
r=p.add_run('Investment Strategy Elevator Pitch'); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
p=ips.add_paragraph(PITCH); p.paragraph_format.line_spacing=2.0; p.paragraph_format.space_after=Pt(0); p.paragraph_format.keep_together=True
p=ips.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next=True
r=p.add_run('Investment Policy Statement'); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
for h,body in SECTIONS:
    p=ips.add_paragraph(); p.paragraph_format.line_spacing=2.0; p.paragraph_format.space_after=Pt(0)
    p.paragraph_format.widow_control=True
    p.paragraph_format.keep_together=True
    r=p.add_run(h+' '); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
    r=p.add_run(body); r.font.name='Times New Roman'; r.font.size=Pt(12)
ips_path=EXPORT/'The_Next_Chapter_Final_IPS.docx'
ips.save(ips_path)

# ---------- Research Appendix DOCX ----------
summary=json.loads((OUT/'key_results.json').read_text())
roll=pd.read_csv(OUT/'rolling_six_year_summary.csv')
boot=pd.read_csv(OUT/'bootstrap_policy_comparison.csv')
fac=pd.read_csv(OUT/'facility_contribution_scenarios.csv')
reserve=pd.read_csv(OUT/'reserve_pv_sensitivity.csv')
alloc=pd.read_csv(OUT/'wins_current_allocation.csv')
bridge=pd.read_csv(OUT/'wins_principal_only_liability_bridge.csv')
bonds=pd.read_csv(OUT/'wins_bond_position_audit.csv')
cor=pd.read_csv(OUT/'historical_stock_bond_correlations.csv')
modern_cor=pd.read_csv(OUT/'modern_vti_vxus_treasury_correlations.csv')
recon=pd.read_csv(OUT/'wins_account_reconciliation.csv')
infl=pd.read_csv(OUT/'inflation_sensitivity.csv')

rep=base_doc()
p=rep.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(1)
r=p.add_run('THE NEXT CHAPTER'); r.bold=True; r.font.name='Aptos Display'; r.font.size=Pt(23); r.font.color.rgb=RGBColor(35,56,77)
p=rep.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(8)
r=p.add_run('Liability and Facility Funding Analysis'); r.font.name='Aptos Display'; r.font.size=Pt(16); r.font.color.rgb=RGBColor(71,95,116)
add_body(rep,'Research supplement for the team’s investment-policy development. It separates Laura’s case-study projection from the team’s StockTrak implementation and makes assumptions, data limitations, and risk estimates explicit.',10)
add_heading(rep,'Executive findings',1)
add_bullet(rep,'The 5-percentage-point glide path is a defensible compromise: it reduces modeled downside relative to constant 65/35, while preserving more median wealth than the faster 8-point glide path.')
add_bullet(rep,'The reserve is a liability problem, not just a bond-allocation problem. At the start of 2033, the first $50,000 is due immediately; the other nine payments must be matched to cash flows available by each January payment date.')
add_bullet(rep,'In the joint-path middle-50% 2031 balance band, the conservative no-yield reserve benchmark supports a conditional $20,000 facility cap. Lower 2031 balance bands support no facility commitment.')
add_bullet(rep,'Historical and bootstrap results are model-dependent scenario evidence. They are not a guarantee or an objective probability of future funding success.')
add_heading(rep,'Client cash-flow requirements',1)
add_body(rep,'Laura contributes $300,000 at the beginning of 2027 and $150,000 at the beginning of 2028. There are no additional contributions or withdrawals before the operating program begins. Ten fixed $50,000 payments are due at the beginning of each year from 2033 through 2042. The facility contribution is discretionary only after the operating reserve is set aside.')
add_table(rep,['Payment date','Nominal payment','Years from 2033','Discounted at 3% PV'],[[f'{2033+i}-01-01','$50,000',str(i),f'${50000/(1.03**i):,.0f}'] for i in range(10)], [1.55,1.35,1.3,1.7],8.5)
add_body(rep,'The first payment is immediate and is not discounted. At 0% return, the reserve requires $500,000. Illustrative flat-rate present values are $439,305 at 3% and $421,767 at 4%. The actual reserve price should be recalculated using the 2033 Treasury zero-coupon spot curve; these flat-rate values are sensitivity checks, not yield forecasts.')
add_table(rep,['Flat annual discount rate','Reserve present value'],[[f'{int(r.flat_rate*100)}%',f'${r.reserve_pv_usd:,.0f}'] for r in reserve.itertuples()],[2.6,2.4],9)
add_heading(rep,'Strategy and glide path',1)
add_picture(rep,'01_glide_path.png','Figure 1. The annual target reduces equity exposure by five percentage points of total portfolio value.',6.2)
add_body(rep,'The target equity weights are 65%, 60%, 55%, 50%, 45%, and 40% in 2027-2032. The balance is allocated to Treasury securities and cash. The strategy is rebalanced annually; liability coverage is reviewed separately and can take priority over the calendar glide path.')
add_heading(rep,'Historical and simulated portfolio tests',1)
add_body(rep,'The long U.S. proxy dataset contains 98 annual observations from 1928-2025: S&P 500 total returns including dividends and U.S. 10-year Treasury total returns. Applying the six-year contribution and allocation schedule to every contiguous six-year window produces 93 overlapping historical windows. Under the five-point glide path, the worst was 1929-1934 at approximately $366,263; the median was approximately $686,880; 88 of 93 windows reached the $500,000 no-yield reserve benchmark. The windows overlap, so they are not independent trials.')
add_picture(rep,'02_historical_rolling_windows.png','Figure 2. Historical six-year U.S. proxy scenarios; overlapping windows are descriptive, not independent.',6.15)
add_body(rep,'The paired three-year moving-block bootstrap creates 100,000 six-year paths. Each selected stock return remains paired with that year’s Treasury return. Two contiguous three-year blocks create each path. This preserves observed runs inside blocks but not across block boundaries, and cannot produce events absent from the sample.')
policy_names={"constant_65_35":"Constant 65/35","five_percentage_point_glide":"Five-point glide","eight_percentage_point_glide":"Eight-point glide"}
boot_rows=[]
for r in boot.itertuples():
    boot_rows.append([policy_names[r.policy],f'${r.median_terminal_value_usd:,.0f}',f'${r.p05_terminal_value_usd:,.0f}',f'{r.share_at_or_above_500k:.1%}',f'${r.cvar95_funding_gap_usd:,.0f}'])
add_table(rep,['Policy','Median ending value','5th percentile','Paths ≥ $500k','CVaR95 funding gap'],boot_rows,[1.55,1.35,1.2,1.15,1.55],8)
add_picture(rep,'03_bootstrap_policy_comparison.png','Figure 3. Distribution comparison for the three allocation policies.',6.15)
p=add_body(rep,'For the five-point glide path, the bootstrap median is about $702,063, the 5th percentile is about $459,970, and 91.82% of paths reach $500,000. CVaR95 funding gap is about $111,467, defined as the average of the largest 5% of one-sided shortfalls max($500,000 - ending value, 0). It is a liability-shortfall measure, not conventional portfolio-loss CVaR.')
p.paragraph_format.keep_together=True
add_heading(rep,'2031 co-sponsor contribution framework',1)
add_body(rep,'The same six-year simulated paths are used to observe both the January 1, 2031 portfolio balance (after 2027-2030 returns) and the January 1, 2033 value (after 2031-2032 returns). Paths are grouped into 2031 balance bands. The facility cap is at most half of the positive 5th-percentile 2033 surplus above the $500,000 no-yield reserve benchmark, rounded down to the nearest $5,000.')
add_table(rep,['2031 balance band','Median 2031 balance','2033 P05 value','Share at/above $500k','Facility cap'],[[
    r['2031_balance_band'],f"${r['2031_balance_median_usd']:,.0f}",f"${r['2033_p05_value_usd']:,.0f}",f"{r['share_paths_cover_500k_reserve']:.1%}",f"${r['facility_cap_at_0pct_reserve_yield_usd']:,.0f}"
] for _,r in fac.iterrows()],[1.75,1.35,1.25,1.2,1.0],7.6)
add_picture(rep,'04_facility_scenarios.png','Figure 4. Facility cap varies with the 2031 starting-value band and reserve discount-rate sensitivity.',6.15)
add_body(rep,'The middle 50% of modeled 2031 balances has a median balance of approximately $607,879. Within that band, the 2033 5th-percentile portfolio value is approximately $548,039. Against a $500,000 cash reserve benchmark, the fifth-percentile surplus is about $48,039; retaining half and rounding down to $5,000 yields a conditional $20,000 cap. After a $20,000 contribution, 96.88% of paths in this band remain at or above $520,000. This is a model proportion within a conditional band, not a real-world 96.88% probability or guarantee. The lower 10th-25th percentile 2031 band supports no facility contribution.')
rep.add_page_break()
add_heading(rep,'Actual StockTrak holdings audit',1)
add_table(rep,['Holding','Qty','Face value','Market value','Annual coupon run-rate'],[[
    r.symbol,f'{r.quantity:g}',f'${r.face_value_total_usd:,.0f}' if pd.notna(r.face_value_total_usd) else '-',f'${r.market_value:,.2f}',f'${r.annual_coupon_run_rate_usd:,.2f}' if pd.notna(r.annual_coupon_run_rate_usd) else '-'
] for r in bonds.itertuples()],[2.2,.7,1.1,1.35,1.45],8)
add_table(rep,['Asset sleeve','Value incl. accrued interest','Portfolio weight'],[[r.asset,f'${r.value_usd:,.2f}',f'{r.weight:.2%}'] for r in alloc.itertuples()],[2.7,2.0,1.6],8.5)
add_body(rep,'The WInS snapshot contains $105,000 face value of Treasury notes and a $5,225 initial annual coupon run-rate. Exact coupon dates were not supplied, so coupon payments are not counted as available for January 1 liabilities. Principal from the current notes matures on February 15, 2031; February 15, 2036; February 15, 2037; and May 15, 2038. The latter three maturities occur after their corresponding January payment dates. These WInS securities are implementation evidence, not the same as the future reserve ladder and not part of Laura’s case-study projection.')
add_picture(rep,'05_wins_principal_bridge.png','Figure 5. Current WInS bond principal matured by each January 1 date versus cumulative operating payments; coupon cash excluded because exact dates are unverified.',6.15)
add_body(rep,'The position rows plus $1,073.63 accrued interest and $740.31 cash reconstruct the reported account value to $297,403.08, one cent above the stated $297,403.07. The separate “Total Market Value of All Positions” summary field of $297,003.14 remains $1,414 above the sum of the six position rows; this discrepancy is disclosed, not explained. The 2036 note’s displayed yield is also anomalous against its premium price and 4.50% coupon and is excluded from return assumptions.')
rep.add_page_break()
add_heading(rep,'Diversification and inflation',1)
add_table(rep,['Historical period','Years','S&P 500 / 10Y Treasury correlation'],[[r.period,str(r.n_years),f'{r.stock_bond_correlation:.3f}'] for r in cor.itertuples()],[2.2,1.0,2.8],8.5)
add_body(rep,'The full 1928-2025 stock/Treasury correlation is near zero (+0.018), but it is not stable: +0.323 in 1961-1999 and -0.365 in 2000-2025. In the modern 2011-2025 sample, VTI/VXUS correlation is approximately +0.771, demonstrating that two geographically diversified equity funds still share substantial equity-market risk. Diversification reduces concentration; it does not eliminate broad market shocks.')
add_picture(rep,'07_correlation_regimes.png','Figure 6. Historical correlation shifts across U.S. market regimes.',6.15)
add_body(rep,'The case fixes operating payments at $50,000 nominally; inflation does not increase the required dollar payment. It does reduce purchasing power. At an illustrative 3% annual inflation rate, a $50,000 payment in 2042 has about $31,158 of 2026 purchasing power. Taiwan-specific cost inflation and USD/TWD exchange-rate movements can separately affect the facility contribution’s real value.')
rep.add_page_break()
add_heading(rep,'Strengths, limitations, and decision',1)
add_body(rep,'Strengths: the strategy is client-specific, prioritizes required payments, has an explicit glide path, uses direct Treasury cash-flow matching for the reserve, compares alternative de-risking schedules, and publishes reproducible code. Its literary theme is memorable but secondary to the financial logic.',9)
add_body(rep,'Limitations: long-run data are U.S. proxies, not the exact ETFs or individual notes; the 2011-2025 international sample is short; bootstrap proportions are not forecasts; annual returns omit intra-year paths; actual 2033 Treasury spot rates are unknown; current coupon dates are not verified; and the current StockTrak notes do not by themselves secure all ten future payments.',9)
add_body(rep,'Recommendation: retain the five-point glide path as the baseline, but do not describe it as a guarantee. In 2031, recalculate the reserve cost from the actual zero-coupon curve and the then-current portfolio. Under the current middle-50% scenario and no-yield $500,000 benchmark, a conditional facility cap of $20,000 is supportable; lower 2031 balance bands imply $0. The operating reserve always takes priority.',9.2)
add_heading(rep,'Sources',1)
add_body(rep,'Damodaran, NYU Stern, Historical Returns on Stocks, Bonds and Bills (1928-2025; page updated January 5, 2026): https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html',8.2)
add_body(rep,'Total Real Returns, VTI vs. VXUS annual total returns, dividends reinvested (2011-2025): https://totalrealreturns.com/n/VTI,VXUS',8.2)
add_body(rep,'TreasuryDirect, Treasury Notes (semiannual fixed interest): https://treasurydirect.gov/marketable-securities/treasury-notes/; Treasury STRIPS: https://www.treasurydirect.gov/marketable-securities/strips/',8.2)


research_path=EXPORT/'The_Next_Chapter_Research_Appendix.docx'
rep.save(research_path)
print('Created', ips_path, research_path)
print('Pitch words:',len(PITCH.split()))
print('IPS words:',sum(len(v.split()) for _,v in SECTIONS))
