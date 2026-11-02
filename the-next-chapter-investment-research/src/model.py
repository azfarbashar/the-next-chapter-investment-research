"""The Next Chapter: reproducible liability-aware investment research.

This is an educational strategy model, not investment advice or a guarantee.
It deliberately separates:
  (1) Laura's hypothetical long-term client cash flows;
  (2) long-run proxy tests and modern VTI/VXUS diagnostics; and
  (3) the team's actual StockTrak implementation snapshot.

Main accumulation test: $300,000 at the start of 2027, $150,000 at the
start of 2028, six annual returns for 2027-2032, and a 65/60/55/50/45/40%
equity glide path. A paired 3-year moving-block bootstrap is used for
100,000 six-year paths. The 2031 and 2033 values come from the SAME paths.

The 1928-2025 series is S&P 500 total return + 10-year Treasury total return,
not a literal backtest of VTI, VXUS, or the team's individual bonds. See
reports/sources_and_methodology.md for source and limitation details.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "results"
FIG = OUT / "figures"
INITIAL = 300_000.0
CONTRIBUTION_2028 = 150_000.0
PAYMENT = 50_000.0
PAYMENT_YEARS = list(range(2033, 2043))
YEARS = list(range(2027, 2033))
GLIDE_5PP = np.array([0.65, 0.60, 0.55, 0.50, 0.45, 0.40])
POLICIES = {
    "constant_65_35": np.repeat(0.65, 6),
    "five_percentage_point_glide": GLIDE_5PP,
    "eight_percentage_point_glide": np.array([0.65, 0.57, 0.49, 0.41, 0.33, 0.25]),
}
SEED = 20261101
N_PATHS = 100_000
NO_YIELD_RESERVE = 500_000.0
FACILITY_INCREMENT = 5_000.0


def reserve_cost_flat(rate: float, payment: float = PAYMENT) -> float:
    """PV at 1 Jan 2033 of ten beginning-of-year payments (annuity due)."""
    if rate <= -1:
        raise ValueError("discount rate must be greater than -100%")
    return float(sum(payment / (1.0 + rate) ** t for t in range(10)))


def reserve_cost_spot_curve(spot_rates: dict[int, float], payment: float = PAYMENT) -> float:
    """PV using annual-compounded zero-coupon spot rates for 1..9 years.

    The first payment is immediate and is not discounted. Rates must be zero
    rates/STRIPS-derived spot rates, not unbootstrapped par yields.
    """
    if set(spot_rates) != set(range(1, 10)):
        raise ValueError("spot_rates must contain maturities 1 through 9")
    if any(r <= -1 for r in spot_rates.values()):
        raise ValueError("spot rates must be greater than -100%")
    return float(payment + sum(payment / (1 + spot_rates[t]) ** t for t in range(1, 10)))


def reserve_schedule() -> pd.DataFrame:
    rows = []
    for t, year in enumerate(PAYMENT_YEARS):
        row = {"payment_date": f"{year}-01-01", "years_from_2033": t,
               "nominal_payment_usd": PAYMENT}
        for r in (0.00, 0.01, 0.02, 0.03, 0.04, 0.05):
            row[f"pv_at_{int(r*100)}pct_usd"] = PAYMENT / (1 + r) ** t
        rows.append(row)
    return pd.DataFrame(rows)


def reserve_input_templates() -> tuple[pd.DataFrame, pd.DataFrame]:
    spot = pd.DataFrame({
        "payment_date": [f"{2033+t}-01-01" for t in range(10)],
        "years_from_2033": list(range(10)),
        "nominal_payment_usd": [PAYMENT] * 10,
        "annual_zero_coupon_spot_rate": ["Immediate; no discount"] + [""] * 9,
        "discount_factor": [1.0] + [f"1/(1+s{t})^{t}" for t in range(1, 10)],
        "present_value_usd": [PAYMENT] + [f"50000/(1+s{t})^{t}" for t in range(1, 10)],
    })
    ladder = pd.DataFrame({
        "liability_payment_date": [f"{2033+t}-01-01" for t in range(10)],
        "cash_needed_usd": [PAYMENT] * 10,
        "cash_must_be_available_by": [f"{2033+t}-01-01" for t in range(10)],
        "candidate_asset": ["Cash / Treasury bill / Treasury STRIP or note" for _ in range(10)],
        "target_maturity": [f"No later than prior business day before {2033+t}-01-01" for t in range(10)],
        "face_value_to_price_in_2033": ["To be calculated from 2033 spot curve"] * 10,
        "status": ["Future implementation; not currently funded"] * 10,
    })
    return spot, ladder


def load_us() -> pd.DataFrame:
    df = pd.read_csv(DATA / "us_long_history_1928_2025.csv").sort_values("year").reset_index(drop=True)
    expected = list(range(1928, 2026))
    if df.year.astype(int).tolist() != expected:
        raise ValueError("US proxy data must contain every year 1928-2025")
    for col in ("sp500_total_return", "tbond10_total_return"):
        if df[col].isna().any() or (df[col] <= -1).any():
            raise ValueError(f"invalid return data in {col}")
    return df


def load_modern() -> pd.DataFrame:
    df = pd.read_csv(DATA / "modern_asset_returns_2011_2025.csv").sort_values("year").reset_index(drop=True)
    if df.year.astype(int).tolist() != list(range(2011, 2026)):
        raise ValueError("modern ETF data must contain every year 2011-2025")
    return df


def portfolio_value(stock_returns: np.ndarray, bond_returns: np.ndarray,
                    equity_weights: np.ndarray = GLIDE_5PP) -> np.ndarray:
    """Vectorized six-year accumulation model; 2028 contribution is start-year."""
    s = np.asarray(stock_returns, dtype=float)
    b = np.asarray(bond_returns, dtype=float)
    w = np.asarray(equity_weights, dtype=float)
    if s.ndim != 2 or s.shape[1] != 6 or b.shape != s.shape:
        raise ValueError("stock_returns and bond_returns must have shape (paths, 6)")
    if w.shape != (6,) or np.any((w < 0) | (w > 1)):
        raise ValueError("equity_weights must have six weights between 0 and 1")
    wealth = np.full(s.shape[0], INITIAL, dtype=float)
    for j in range(6):
        if j == 1:  # $150,000 arrives at the beginning of 2028, before 2028 return
            wealth += CONTRIBUTION_2028
        rp = w[j] * s[:, j] + (1 - w[j]) * b[:, j]
        wealth *= (1 + rp)
    return wealth


def rolling_historical(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    years = df.year.to_numpy(int)
    stock = df.sp500_total_return.to_numpy(float)
    bond = df.tbond10_total_return.to_numpy(float)
    for start in range(len(df) - 5):
        for policy, weights in POLICIES.items():
            v = portfolio_value(stock[start:start+6][None, :], bond[start:start+6][None, :], weights)[0]
            rows.append({"period": f"{years[start]}-{years[start+5]}",
                         "start_year": years[start], "policy": policy,
                         "value_before_2033_payment_usd": v})
    return pd.DataFrame(rows)


def sample_moving_blocks(df: pd.DataFrame, n_paths: int = N_PATHS,
                          horizon: int = 6, block: int = 3,
                          seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    """Paired moving-block bootstrap; keeps stock/bond pairs and 3-year runs."""
    if horizon % block:
        raise ValueError("horizon must be divisible by block length")
    rng = np.random.default_rng(seed)
    n_blocks = horizon // block
    starts = rng.integers(0, len(df) - block + 1, size=(n_paths, n_blocks))
    offsets = np.arange(block)
    idx = (starts[:, :, None] + offsets[None, None, :]).reshape(n_paths, horizon)
    return (df.sp500_total_return.to_numpy(float)[idx],
            df.tbond10_total_return.to_numpy(float)[idx])


def sample_contiguous(df: pd.DataFrame, horizon: int, n_paths: int,
                      seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Sample contiguous historical annual pairs with replacement."""
    if horizon > len(df):
        raise ValueError("horizon longer than dataset")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(df) - horizon + 1, size=n_paths)
    idx = starts[:, None] + np.arange(horizon)[None, :]
    return (df.sp500_total_return.to_numpy(float)[idx],
            df.tbond10_total_return.to_numpy(float)[idx])


def simulate_joint_2031_2033(df: pd.DataFrame, n_paths: int = N_PATHS,
                             seed: int = SEED + 1) -> tuple[np.ndarray, np.ndarray]:
    """Simulate 2027-2032 on the same paired six-year return paths.

    Returns (value at 1 Jan 2031, value at 1 Jan 2033). The $150,000
    contribution is added at the beginning of 2028. Returns for 2027-2030
    produce the 2031 balance; returns for 2031-2032 produce the 2033 value.
    Using the same path avoids independently resampling the 2031-2032 stage.
    """
    stock, bond = sample_moving_blocks(df, n_paths, 6, 3, seed)
    wealth = np.full(n_paths, INITIAL, dtype=float)
    value_2031 = None
    for j, w in enumerate(GLIDE_5PP):
        if j == 1:
            wealth += CONTRIBUTION_2028
        rp = w * stock[:, j] + (1 - w) * bond[:, j]
        wealth *= 1 + rp
        if j == 3:
            value_2031 = wealth.copy()
    assert value_2031 is not None
    return value_2031, wealth

def tail_summary(values: np.ndarray, label: str, reserve: float = NO_YIELD_RESERVE) -> dict:
    values = np.asarray(values, dtype=float)
    q05, q10, q25, q50, q75, q90, q95 = np.quantile(values, [.05,.10,.25,.50,.75,.90,.95])
    funding_gap = np.maximum(reserve - values, 0.0)
    tail_n = max(1, int(math.ceil(0.05 * len(values))))
    worst_gaps = np.sort(funding_gap)[-tail_n:]
    worst_wealth = np.sort(values)[:tail_n]
    shortfall = values < reserve
    return {
        "case": label, "paths_or_windows": int(len(values)),
        "mean_terminal_value_usd": float(np.mean(values)),
        "p05_terminal_value_usd": float(q05), "p10_terminal_value_usd": float(q10),
        "p25_terminal_value_usd": float(q25), "median_terminal_value_usd": float(q50),
        "p75_terminal_value_usd": float(q75), "p90_terminal_value_usd": float(q90),
        "p95_terminal_value_usd": float(q95),
        "share_at_or_above_500k": float(np.mean(values >= reserve)),
        "mean_worst_5pct_terminal_value_usd": float(np.mean(worst_wealth)),
        "cvar95_funding_gap_usd": float(np.mean(worst_gaps)),
        "mean_gap_conditional_on_shortfall_usd": float(np.mean(funding_gap[shortfall])) if np.any(shortfall) else 0.0,
    }


def policy_bootstrap_comparison(df: pd.DataFrame, n_paths: int = N_PATHS,
                                seed: int = SEED) -> pd.DataFrame:
    s, b = sample_moving_blocks(df, n_paths, 6, 3, seed)
    rows = []
    for name, weights in POLICIES.items():
        item = tail_summary(portfolio_value(s, b, weights), name)
        item["policy"] = name
        rows.append(item)
    return pd.DataFrame(rows)


def distribution_summary(values: np.ndarray, label: str) -> dict:
    """Descriptive distribution summary without an unrelated liability threshold."""
    values = np.asarray(values, dtype=float)
    q05, q10, q25, q50, q75, q90, q95 = np.quantile(values, [.05, .10, .25, .50, .75, .90, .95])
    return {
        "case": label,
        "paths": int(len(values)),
        "mean_usd": float(np.mean(values)),
        "p05_usd": float(q05),
        "p10_usd": float(q10),
        "p25_usd": float(q25),
        "median_usd": float(q50),
        "p75_usd": float(q75),
        "p90_usd": float(q90),
        "p95_usd": float(q95),
    }


def rolling_summary(rolling: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy, g in rolling.groupby("policy"):
        v = g.value_before_2033_payment_usd.to_numpy(float)
        rows.append({"policy": policy, "overlapping_six_year_windows": len(v),
                     "minimum_usd": float(v.min()),
                     "worst_period": g.loc[g.value_before_2033_payment_usd.idxmin(), "period"],
                     "p05_usd": float(np.quantile(v, .05)),
                     "median_usd": float(np.median(v)),
                     "p95_usd": float(np.quantile(v, .95)),
                     "windows_ge_500k": int(np.sum(v >= 500_000)),
                     "windows_ge_3pct_reserve_pv": int(np.sum(v >= reserve_cost_flat(.03))),
                     "windows_ge_4pct_reserve_pv": int(np.sum(v >= reserve_cost_flat(.04)))} )
    return pd.DataFrame(rows)


def funding_policy_decision(five_point_success: float, eight_point_success: float,
                            threshold: float = 0.95) -> str:
    """Choose the glide-path response to modeled reserve-funding coverage.

    The five-point path is the strategic baseline. If it falls below the
    team's 95% modeled target but the eight-point path meets it, accelerate
    de-risking. If neither meets the target, use the eight-point path as the
    more defensive fallback, prohibit facility spending, and disclose that
    the modeled target remains unmet. This decision rule does not guarantee
    sufficient capital and cannot reverse losses already incurred.
    """
    values = (five_point_success, eight_point_success, threshold)
    if any(not np.isfinite(float(v)) for v in values):
        raise ValueError("funding probabilities and threshold must be finite")
    if not (0 <= five_point_success <= 1 and 0 <= eight_point_success <= 1):
        raise ValueError("funding success rates must be between 0 and 1")
    if not (0 < threshold <= 1):
        raise ValueError("threshold must be in (0, 1]")
    if five_point_success >= threshold:
        return "maintain_five_point_glide"
    if eight_point_success >= threshold:
        return "adopt_eight_point_fallback"
    return "eight_point_fallback_target_unmet_zero_facility"


def facility_cap(p05_2033: float, reserve_cost: float,
                 retain_fraction: float = 0.50,
                 increment: float = FACILITY_INCREMENT) -> tuple[float, float]:
    """At most 50% of positive P05 surplus, rounded down to nearest increment."""
    if not (0 <= retain_fraction <= 1):
        raise ValueError("retain_fraction must be in [0,1]")
    surplus = p05_2033 - reserve_cost
    raw = max(0.0, surplus) * (1 - retain_fraction)
    cap = math.floor((raw + 1e-9) / increment) * increment
    return float(cap), float(surplus)


def facility_scenarios_joint(balance_2031: np.ndarray, value_2033: np.ndarray) -> pd.DataFrame:
    """Conditional 2033 outcomes by 2031 starting-wealth band.

    Bands are formed from the joint simulated paths: bottom decile, 10th-25th,
    middle 50%, 75th-90th, and top decile. They are descriptive conditional
    scenarios, not forecasts or a confidence interval for an individual client.
    """
    if balance_2031.shape != value_2033.shape:
        raise ValueError("2031 and 2033 arrays must have the same length")
    q10, q25, q75, q90 = np.quantile(balance_2031, [.10, .25, .75, .90])
    bands = [
        ("Bottom 10% 2031 balance", balance_2031 <= q10),
        ("10th-25th percentile 2031 balance", (balance_2031 > q10) & (balance_2031 <= q25)),
        ("Middle 50% 2031 balance", (balance_2031 > q25) & (balance_2031 <= q75)),
        ("75th-90th percentile 2031 balance", (balance_2031 > q75) & (balance_2031 <= q90)),
        ("Top 10% 2031 balance", balance_2031 > q90),
    ]
    rows = []
    for label, mask in bands:
        terminal = value_2033[mask]
        starting = balance_2031[mask]
        if len(terminal) == 0:
            continue
        p05 = float(np.quantile(terminal, .05))
        p10 = float(np.quantile(terminal, .10))
        cap0, surplus0 = facility_cap(p05, NO_YIELD_RESERVE)
        pv3 = reserve_cost_flat(.03)
        cap3, surplus3 = facility_cap(p05, pv3)
        rows.append({
            "2031_balance_band": label,
            "path_count": int(mask.sum()),
            "2031_balance_median_usd": float(np.median(starting)),
            "2033_p05_value_usd": p05,
            "2033_p10_value_usd": p10,
            "2033_median_value_usd": float(np.median(terminal)),
            "share_paths_cover_500k_reserve": float(np.mean(terminal >= NO_YIELD_RESERVE)),
            "no_yield_reserve_benchmark_usd": NO_YIELD_RESERVE,
            "p05_surplus_vs_500k_usd": surplus0,
            "facility_cap_at_0pct_reserve_yield_usd": cap0,
            "3pct_flat_pv_benchmark_usd": pv3,
            "p05_surplus_vs_3pct_pv_usd": surplus3,
            "facility_cap_at_3pct_flat_pv_usd": cap3,
            "share_paths_cover_500k_plus_zero_yield_cap": float(np.mean(terminal >= NO_YIELD_RESERVE + cap0)),
        })
    return pd.DataFrame(rows)


def facility_curve_sensitivity(p05_2033: float) -> pd.DataFrame:
    rows = []
    for rate in (0,.01,.02,.03,.04,.05):
        pv = reserve_cost_flat(rate)
        cap, surplus = facility_cap(p05_2033, pv)
        rows.append({"illustrative_flat_spot_rate": rate, "reserve_pv_usd": pv,
                     "conditional_2033_p05_usd": p05_2033,
                     "p05_surplus_usd": surplus, "facility_cap_usd": cap})
    return pd.DataFrame(rows)


def inflation_sensitivity() -> pd.DataFrame:
    rows = []
    for inf in (.02,.03,.05):
        for year in (2033,2042):
            years = year - 2026
            rows.append({"inflation_rate": inf, "payment_year": year,
                         "nominal_payment_usd": PAYMENT,
                         "real_value_2026_usd": PAYMENT / (1+inf)**years,
                         "facility_cost_multiplier_from_2026": (1+inf)**years})
    return pd.DataFrame(rows)


def crisis_shocks(df: pd.DataFrame) -> pd.DataFrame:
    years = [1931, 1974, 2008, 2022]
    chosen = df[df.year.isin(years)].copy()
    chosen["portfolio_return_at_40eq_60bond"] = .40*chosen.sp500_total_return + .60*chosen.tbond10_total_return
    chosen["portfolio_return_at_65eq_35bond"] = .65*chosen.sp500_total_return + .35*chosen.tbond10_total_return
    return chosen[["year","sp500_total_return","tbond10_total_return",
                   "portfolio_return_at_65eq_35bond","portfolio_return_at_40eq_60bond"]]


def correlation_tables(us: pd.DataFrame, modern: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows = []
    for label, lo, hi in [("1928-1960",1928,1960),("1961-1999",1961,1999),
                          ("2000-2025",2000,2025),("1928-2025",1928,2025)]:
        x = us[(us.year>=lo)&(us.year<=hi)]
        rows.append({"period":label,"n_years":len(x),
                     "stock_bond_correlation":x.sp500_total_return.corr(x.tbond10_total_return)})
    m = modern[["vti_total_return","vxus_total_return","tbond10_total_return"]].corr()
    modern_long = m.rename_axis("asset").reset_index().melt(id_vars="asset", var_name="other_asset", value_name="correlation")
    return pd.DataFrame(rows), modern_long


def current_wins_audit() -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    pos = pd.read_csv(DATA / "wins_snapshot.csv")
    summary = json.loads((DATA / "wins_account_summary.json").read_text())
    pos_market = float(pos.market_value.sum())
    bond_rows = pos[pos.security_type=="Bond"].copy()
    bond_rows["face_value_total_usd"] = bond_rows.quantity * bond_rows.face_value_per_unit
    bond_rows["purchase_cost_usd"] = bond_rows.quantity * bond_rows.price_paid
    bond_rows["annual_coupon_run_rate_usd"] = bond_rows.face_value_total_usd * bond_rows.coupon_rate
    bond_rows["semiannual_coupon_amount_usd"] = bond_rows.annual_coupon_run_rate_usd / 2
    bond_rows["accrued_interest_total_usd"] = bond_rows.quantity * bond_rows.accrued_interest_per_unit
    bond_rows["yield_note"] = "StockTrak-reported yield; not used in portfolio return or liability pricing"
    # The 2036 quote is anomalous under ordinary fixed-rate bond conventions.
    bond_rows.loc[bond_rows.symbol.str.contains("15022036"),"yield_note"] = (
        "Anomalous: premium price above par with quoted yield above coupon; verify StockTrak field definition")
    # Account reconciliation: row-level positions + account-level accrued interest + cash.
    accrued = float(summary["accrued_interest_earned_on_bonds"])
    cash = float(summary["cash_balance"])
    reconstructed = pos_market + accrued + cash
    recon = pd.DataFrame([
        {"item":"Sum of six line-item market values","amount_usd":pos_market,"source":"User-provided open-position tables"},
        {"item":"Accrued interest on bonds","amount_usd":accrued,"source":"User-provided account summary"},
        {"item":"Cash balance","amount_usd":cash,"source":"User-provided account summary"},
        {"item":"Reconstructed account value","amount_usd":reconstructed,"source":"Calculated"},
        {"item":"Reported current portfolio value","amount_usd":summary["reported_current_portfolio_value"],"source":"User-provided account summary"},
        {"item":"Reconstruction less reported portfolio value","amount_usd":reconstructed-summary["reported_current_portfolio_value"],"source":"Calculated; rounding difference"},
        {"item":"Reported total market value of all positions","amount_usd":summary["reported_total_market_value_all_positions"],"source":"User-provided account summary"},
        {"item":"Line-item positions less reported total market value field","amount_usd":pos_market-summary["reported_total_market_value_all_positions"],"source":"Unreconciled summary-field difference; not explained"},
    ])
    # Asset allocation includes accrued interest in fixed income.
    vti = float(pos.loc[pos.symbol=="VTI","market_value"].iloc[0])
    vxus = float(pos.loc[pos.symbol=="VXUS","market_value"].iloc[0])
    bonds_market = float(bond_rows.market_value.sum())
    cash_value = cash
    total = reconstructed
    alloc = pd.DataFrame([
        {"asset":"US equities (VTI)","value_usd":vti,"weight":vti/total},
        {"asset":"International equities (VXUS)","value_usd":vxus,"weight":vxus/total},
        {"asset":"Treasuries including accrued interest","value_usd":bonds_market+accrued,"weight":(bonds_market+accrued)/total},
        {"asset":"Cash","value_usd":cash_value,"weight":cash_value/total},
    ])
    return bond_rows, recon, alloc


def wins_principal_maturity_bridge(bond_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    maturities = [(pd.Timestamp(r.maturity_date), float(r.face_value_total_usd)) for r in bond_rows.itertuples()]
    for year in PAYMENT_YEARS:
        due = pd.Timestamp(year,1,1)
        matured = sum(face for maturity, face in maturities if maturity < due)
        due_cumulative = PAYMENT*(year-2032)
        rows.append({"payment_date":due.date().isoformat(),
                     "principal_from_current_WInS_bonds_matured_before_payment_usd":matured,
                     "cumulative_operating_payments_due_usd":due_cumulative,
                     "principal_only_gap_usd":max(0.0,due_cumulative-matured),
                     "coupon_cash_counted":False})
    return pd.DataFrame(rows)


def make_figures(rolling: pd.DataFrame, bootstrap: pd.DataFrame,
                 facility: pd.DataFrame, bridge: pd.DataFrame,
                 reserve: pd.DataFrame, correlations: pd.DataFrame,
                 inflation: pd.DataFrame, wins_alloc: pd.DataFrame,
                 shocks: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    # 1 strategic glide path
    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.plot(YEARS, GLIDE_5PP*100, marker="o", linewidth=2.2, label="Equities")
    ax.plot(YEARS, (1-GLIDE_5PP)*100, marker="o", linewidth=2.2, label="Treasuries/cash")
    ax.set(title="The Next Chapter: five-percentage-point glide path", xlabel="Investment year", ylabel="Target allocation (%)", ylim=(0,100))
    ax.grid(alpha=.25); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG/"01_glide_path.png",dpi=180); plt.close(fig)
    # 2 historical rolling distribution
    g = rolling[rolling.policy=="five_percentage_point_glide"]
    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.hist(g.value_before_2033_payment_usd/1000,bins=20,edgecolor="white",alpha=.86)
    ax.axvline(500,color="#a23b3b",linestyle="--",label="$500k no-yield benchmark")
    ax.set(title="93 overlapping six-year US proxy windows (1928-2025)",xlabel="Value before 2033 payment ($000s)",ylabel="Number of windows")
    ax.legend(frameon=False); ax.grid(axis="y",alpha=.2); fig.tight_layout(); fig.savefig(FIG/"02_historical_rolling_windows.png",dpi=180); plt.close(fig)
    # 3 bootstrap distributions by allocation
    fig, ax = plt.subplots(figsize=(8,4.5))
    x = np.arange(len(bootstrap)); width=.24
    for i,col in enumerate(["p05_terminal_value_usd","median_terminal_value_usd"]):
        ax.bar(x+(i-.5)*width,bootstrap[col]/1000,width,label="5th percentile" if i==0 else "Median")
    ax.axhline(500,color="#a23b3b",linestyle="--",label="$500k benchmark")
    ax.set_xticks(x, ["Constant\n65/35", "Five-point\nglide", "Eight-point\nglide"], fontsize=8)
    ax.set(title="Paired three-year block-bootstrap comparison",ylabel="2033 value ($000s)")
    ax.legend(frameon=False,ncol=3,fontsize=8); ax.grid(axis="y",alpha=.2); fig.tight_layout(); fig.savefig(FIG/"03_bootstrap_policy_comparison.png",dpi=180); plt.close(fig)
    # 4 conditional facility cap
    fig, ax = plt.subplots(figsize=(8,4.5))
    labels = ["Bottom 10%","10-25%","Middle 50%","75-90%","Top 10%"]
    ax.bar(labels,facility.facility_cap_at_0pct_reserve_yield_usd/1000,label="0% reserve yield")
    ax.plot(labels,facility.facility_cap_at_3pct_flat_pv_usd/1000,marker="o",linestyle="--",label="3% flat PV sensitivity")
    ax.tick_params(axis="x", labelrotation=15)
    ax.set(title="Facility cap depends on 2031 balance and reserve price",xlabel="2031 portfolio-value scenario",ylabel="Conditional cap ($000s)")
    ax.legend(frameon=False); ax.grid(axis="y",alpha=.2); fig.tight_layout(); fig.savefig(FIG/"04_facility_scenarios.png",dpi=180); plt.close(fig)
    # 5 current WInS principal maturity bridge
    fig, ax = plt.subplots(figsize=(8,4.5))
    x = pd.to_datetime(bridge.payment_date)
    ax.plot(x,bridge.principal_from_current_WInS_bonds_matured_before_payment_usd/1000,marker="o",label="Matured principal only")
    ax.plot(x,bridge.cumulative_operating_payments_due_usd/1000,marker="o",label="Cumulative payments")
    ax.set(title="Current WInS Treasury principal vs. liabilities",ylabel="Cumulative USD ($000s)")
    ax.legend(frameon=False); ax.grid(alpha=.2); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(FIG/"05_wins_principal_bridge.png",dpi=180); plt.close(fig)
    # 6 reserve cost
    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.plot(reserve.flat_rate*100,reserve.reserve_pv_usd/1000,marker="o",linewidth=2)
    ax.set(title="Cost of ten beginning-of-year payments",xlabel="Illustrative flat discount rate (%)",ylabel="Reserve PV at 1 Jan 2033 ($000s)")
    ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(FIG/"06_reserve_cost_sensitivity.png",dpi=180); plt.close(fig)
    # 7 correlation by regime
    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.bar(correlations.period,correlations.stock_bond_correlation)
    ax.axhline(0,color="black",linewidth=.8)
    ax.set(title="Stock / 10-year Treasury correlation changes by era",ylabel="Annual return correlation",ylim=(-.55,.55))
    ax.grid(axis="y",alpha=.2); fig.tight_layout(); fig.savefig(FIG/"07_correlation_regimes.png",dpi=180); plt.close(fig)
    # 8 inflation
    pivot=inflation.pivot(index="payment_year",columns="inflation_rate",values="real_value_2026_usd")
    fig, ax = plt.subplots(figsize=(8,4.5))
    for rate in pivot.columns: ax.plot(pivot.index,pivot[rate]/1000,marker="o",label=f"{rate:.0%} inflation")
    ax.set(title="Real purchasing power of each fixed $50,000 payment",xlabel="Payment year",ylabel="2026 dollars ($000s)")
    ax.legend(frameon=False); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(FIG/"08_inflation_purchasing_power.png",dpi=180); plt.close(fig)
    # 9 WInS allocation
    fig, ax = plt.subplots(figsize=(7,4.5))
    ax.pie(wins_alloc.value_usd,labels=wins_alloc.asset,autopct="%1.1f%%",startangle=90,textprops={"fontsize":8})
    ax.set_title("Current StockTrak implementation allocation")
    fig.tight_layout(); fig.savefig(FIG/"09_wins_allocation.png",dpi=180); plt.close(fig)
    # 10 stress year returns at the 40/60 late-stage target
    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.bar(shocks.year.astype(str),shocks.portfolio_return_at_40eq_60bond*100)
    ax.axhline(0,color="black",linewidth=.8)
    ax.set(title="Selected historical shock years at a 40/60 allocation",xlabel="Historical shock year",ylabel="Illustrative one-year portfolio return (%)")
    ax.grid(axis="y",alpha=.2); fig.tight_layout(); fig.savefig(FIG/"10_stress_years.png",dpi=180); plt.close(fig)


def run_all() -> dict:
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    us=load_us(); modern=load_modern()
    rolling=rolling_historical(us); rolling_sum=rolling_summary(rolling)
    boot=policy_bootstrap_comparison(us)
    # Compare modeled reserve-threshold coverage across flat-rate sensitivities.
    s_threshold, b_threshold = sample_moving_blocks(us, N_PATHS, 6, 3, SEED)
    threshold_rows = []
    for policy_name, weights in POLICIES.items():
        wealth = portfolio_value(s_threshold, b_threshold, weights)
        for rate in (0.00, 0.01, 0.02, 0.03, 0.04, 0.05):
            target = reserve_cost_flat(rate)
            threshold_rows.append({
                "policy": policy_name,
                "illustrative_flat_reserve_rate": rate,
                "reserve_target_usd": target,
                "share_paths_meeting_target": float(np.mean(wealth >= target)),
                "p05_portfolio_value_usd": float(np.quantile(wealth, .05)),
            })
    reserve_thresholds = pd.DataFrame(threshold_rows)
    # Use the same fixed seed for published results.
    s,b=sample_moving_blocks(us,N_PATHS,6,3,SEED)
    five_values=portfolio_value(s,b,GLIDE_5PP)
    boot_five=tail_summary(five_values,"five percentage point glide")
    balances, terminal_2033=simulate_joint_2031_2033(us)
    facility=facility_scenarios_joint(balances,terminal_2033)
    med_balance=float(np.median(balances))
    median_terminal=terminal_2033[(balances > np.quantile(balances,.25)) & (balances <= np.quantile(balances,.75))]
    reserve=pd.DataFrame([{"flat_rate":r,"reserve_pv_usd":reserve_cost_flat(r)} for r in (0,.01,.02,.03,.04,.05)])
    inflation=pd.DataFrame([{"inflation_rate":rate,"payment_year":year,"nominal_payment_usd":PAYMENT,
                             "real_value_2026_usd":PAYMENT/(1+rate)**(year-2026),
                             "facility_cost_multiplier_2026_to_year":(1+rate)**(year-2026)}
                            for rate in (.02,.03,.05) for year in PAYMENT_YEARS])
    shocks=crisis_shocks(us)
    corr_regimes, modern_corr=correlation_tables(us,modern)
    bond_rows,recon,wins_alloc=current_wins_audit()
    bridge=wins_principal_maturity_bridge(bond_rows)
    modern_rolling=[]
    # Exact ETF-era six-year diagnostic using the actual VTI/VXUS returns.
    for start in range(len(modern)-5):
        win=modern.iloc[start:start+6]
        vti=win.vti_total_return.to_numpy(float); vxus=win.vxus_total_return.to_numpy(float); tb=win.tbond10_total_return.to_numpy(float)
        # Preserve the initial 47:18 equity split within the equity sleeve.
        eq=(47/65)*vti+(18/65)*vxus
        val=INITIAL
        for j,w in enumerate(GLIDE_5PP):
            if j==1: val+=CONTRIBUTION_2028
            val*=1+w*eq[j]+(1-w)*tb[j]
        modern_rolling.append({"period":f"{int(win.year.iloc[0])}-{int(win.year.iloc[-1])}","five_point_ending_value_usd":val})
    modern_roll=pd.DataFrame(modern_rolling)
    # Persist results.
    rolling.to_csv(OUT/"rolling_six_year_results.csv",index=False)
    rolling_sum.to_csv(OUT/"rolling_six_year_summary.csv",index=False)
    boot.to_csv(OUT/"bootstrap_policy_comparison.csv",index=False)
    reserve_thresholds.to_csv(OUT/"bootstrap_reserve_threshold_sensitivity.csv",index=False)
    pd.DataFrame([boot_five]).to_csv(OUT/"bootstrap_five_point_tail_summary.csv",index=False)
    pd.DataFrame([distribution_summary(balances,"2031 portfolio value")]).to_csv(OUT/"2031_balance_distribution.csv",index=False)
    pd.DataFrame([tail_summary(median_terminal,"2033 conditional on middle 50% 2031 balance")]).to_csv(OUT/"2033_conditional_distribution.csv",index=False)
    facility.to_csv(OUT/"facility_contribution_scenarios.csv",index=False)
    reserve.to_csv(OUT/"reserve_pv_sensitivity.csv",index=False)
    inflation.to_csv(OUT/"inflation_sensitivity.csv",index=False)
    shocks.to_csv(OUT/"selected_stress_years.csv",index=False)
    corr_regimes.to_csv(OUT/"historical_stock_bond_correlations.csv",index=False)
    modern_corr.to_csv(OUT/"modern_vti_vxus_treasury_correlations.csv",index=False)
    modern_roll.to_csv(OUT/"modern_vti_vxus_rolling_windows.csv",index=False)
    bond_rows.to_csv(OUT/"wins_bond_position_audit.csv",index=False)
    recon.to_csv(OUT/"wins_account_reconciliation.csv",index=False)
    wins_alloc.to_csv(OUT/"wins_current_allocation.csv",index=False)
    bridge.to_csv(OUT/"wins_principal_only_liability_bridge.csv",index=False)
    reserve_schedule().to_csv(OUT/"liability_payment_schedule.csv",index=False)
    spot,ladder=reserve_input_templates()
    spot.to_csv(DATA/"2033_spot_curve_input_template.csv",index=False)
    ladder.to_csv(DATA/"2033_reserve_ladder_template.csv",index=False)
    curve=[]
    p05=float(np.quantile(median_terminal,.05))
    for rate in (0,.01,.02,.03,.04,.05):
        pv=reserve_cost_flat(rate); cap,surplus=facility_cap(p05,pv)
        curve.append({"flat_rate_sensitivity":rate,"reserve_pv_usd":pv,"2033_p05_usd":p05,"p05_surplus_usd":surplus,"facility_cap_usd":cap})
    curve=pd.DataFrame(curve); curve.to_csv(OUT/"median_facility_cap_rate_sensitivity.csv",index=False)
    make_figures(rolling,boot,facility,bridge,reserve,corr_regimes,inflation.rename(columns={"inflation_rate":"inflation_rate","payment_year":"payment_year"}),wins_alloc,shocks)
    summary={
      "data_years_us": [1928,2025], "n_us_annual_observations":len(us),
      "n_overlapping_six_year_windows":int(len(us)-5),
      "five_point_historical_worst_period":rolling_sum.loc[rolling_sum.policy=="five_percentage_point_glide","worst_period"].iloc[0],
      "five_point_historical_min_usd":float(rolling_sum.loc[rolling_sum.policy=="five_percentage_point_glide","minimum_usd"].iloc[0]),
      "five_point_historical_p05_usd":float(rolling_sum.loc[rolling_sum.policy=="five_percentage_point_glide","p05_usd"].iloc[0]),
      "five_point_historical_median_usd":float(rolling_sum.loc[rolling_sum.policy=="five_percentage_point_glide","median_usd"].iloc[0]),
      "five_point_historical_windows_ge_500k":int(rolling_sum.loc[rolling_sum.policy=="five_percentage_point_glide","windows_ge_500k"].iloc[0]),
      "bootstrap_five_p05_usd":boot_five["p05_terminal_value_usd"],
      "bootstrap_five_median_usd":boot_five["median_terminal_value_usd"],
      "bootstrap_five_share_ge_500k":boot_five["share_at_or_above_500k"],
      "bootstrap_five_cvar95_funding_gap_usd":boot_five["cvar95_funding_gap_usd"],
      "bootstrap_five_share_meeting_3pct_pv":float(reserve_thresholds.loc[(reserve_thresholds.policy=="five_percentage_point_glide")&(reserve_thresholds.illustrative_flat_reserve_rate==.03),"share_paths_meeting_target"].iloc[0]),
      "bootstrap_five_share_meeting_4pct_pv":float(reserve_thresholds.loc[(reserve_thresholds.policy=="five_percentage_point_glide")&(reserve_thresholds.illustrative_flat_reserve_rate==.04),"share_paths_meeting_target"].iloc[0]),
      "2031_median_balance_usd":med_balance,
      "2033_conditional_p05_usd":p05,
      "facility_scenario_method":"Joint six-year paired moving-block paths, grouped by 2031 balance percentile bands",
      "facility_cap_middle_50pct_zero_yield_usd":float(facility.loc[facility["2031_balance_band"]=="Middle 50% 2031 balance","facility_cap_at_0pct_reserve_yield_usd"].iloc[0]),
      "facility_cap_middle_50pct_3pct_reserve_pv_usd":float(facility.loc[facility["2031_balance_band"]=="Middle 50% 2031 balance","facility_cap_at_3pct_flat_pv_usd"].iloc[0]),
      "wins_reconstructed_value_usd":float(recon.loc[recon.item=="Reconstructed account value","amount_usd"].iloc[0]),
      "wins_reported_value_usd":float(recon.loc[recon.item=="Reported current portfolio value","amount_usd"].iloc[0]),
      "wins_line_positions_value_usd":float(bond_rows.market_value.sum()+wins_alloc.loc[wins_alloc.asset.str.contains("VTI|VXUS"),"value_usd"].sum()),
      "wins_bond_face_value_usd":float(bond_rows.face_value_total_usd.sum()),
      "wins_annual_coupon_run_rate_usd":float(bond_rows.annual_coupon_run_rate_usd.sum()),
    }
    (OUT/"key_results.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    print("\nBootstrap comparison:\n",boot.to_string(index=False))
    print("\nFacility scenarios:\n",facility.to_string(index=False))
    print("\nTests should be run with: python -m unittest discover -s tests -v")
    return summary


if __name__ == "__main__":
    run_all()
