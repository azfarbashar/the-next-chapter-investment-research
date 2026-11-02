import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import model

class ModelTests(unittest.TestCase):
    def test_annuity_due_pv_zero_rate(self):
        self.assertAlmostEqual(model.reserve_cost_flat(0), 500000.0)

    def test_annuity_due_pv_four_percent(self):
        self.assertAlmostEqual(model.reserve_cost_flat(.04), 421766.580526, places=3)

    def test_spot_curve_equals_flat_curve(self):
        curve = {t:.03 for t in range(1,10)}
        self.assertAlmostEqual(model.reserve_cost_spot_curve(curve), model.reserve_cost_flat(.03), places=6)

    def test_spot_curve_requires_all_tenors(self):
        with self.assertRaises(ValueError): model.reserve_cost_spot_curve({1:.03})

    def test_six_year_contribution_timing(self):
        # Six zero-return years leave initial 300k plus 150k beginning-2028 contribution.
        z = np.zeros((1,6))
        self.assertEqual(model.portfolio_value(z,z)[0],450000.0)

    def test_glide_path_five_percentage_points(self):
        np.testing.assert_allclose(model.GLIDE_5PP,[.65,.60,.55,.50,.45,.40])

    def test_historical_data_coverage(self):
        df=model.load_us()
        self.assertEqual(len(df),98)
        self.assertEqual(df.year.iloc[0],1928)
        self.assertEqual(df.year.iloc[-1],2025)

    def test_modern_data_coverage(self):
        df=model.load_modern()
        self.assertEqual(len(df),15)
        self.assertEqual(df.year.iloc[0],2011)
        self.assertEqual(df.year.iloc[-1],2025)

    def test_rolling_windows_count(self):
        self.assertEqual(len(model.rolling_historical(model.load_us())),93*3)

    def test_moving_block_shape_and_pairing(self):
        s,b=model.sample_moving_blocks(model.load_us(),100,6,3,123)
        self.assertEqual(s.shape,(100,6)); self.assertEqual(b.shape,(100,6))
        # Every sampled return is drawn from the paired source columns.
        src=model.load_us()
        for x,y in zip(s[0],b[0]):
            self.assertTrue(((src.sp500_total_return==x)&(src.tbond10_total_return==y)).any())

    def test_bootstrap_reproducibility(self):
        d=model.load_us()
        s1,b1=model.sample_moving_blocks(d,20,6,3,444)
        s2,b2=model.sample_moving_blocks(d,20,6,3,444)
        np.testing.assert_array_equal(s1,s2); np.testing.assert_array_equal(b1,b2)

    def test_joint_path_uses_same_six_year_sequence(self):
        df=model.load_us().copy()
        df["sp500_total_return"] = 0.0
        df["tbond10_total_return"] = 0.0
        v2031, v2033 = model.simulate_joint_2031_2033(df, n_paths=20, seed=1)
        np.testing.assert_allclose(v2031, 450000.0)
        np.testing.assert_allclose(v2033, 450000.0)

    def test_joint_facility_bands_are_complete(self):
        balances=np.arange(1000,11000,dtype=float)
        terminal=balances+100000
        bands=model.facility_scenarios_joint(balances,terminal)
        self.assertEqual(len(bands),5)
        self.assertEqual(int(bands.path_count.sum()),len(balances))
        self.assertTrue((bands.facility_cap_at_0pct_reserve_yield_usd>=0).all())

    def test_funding_policy_keeps_five_point_when_it_passes(self):
        self.assertEqual(model.funding_policy_decision(.96, .97), "maintain_five_point_glide")

    def test_funding_policy_uses_eight_point_if_only_it_passes(self):
        self.assertEqual(model.funding_policy_decision(.94, .96), "adopt_eight_point_fallback")

    def test_funding_policy_discloses_target_miss_and_zero_facility(self):
        self.assertEqual(model.funding_policy_decision(.91, .92), "eight_point_fallback_target_unmet_zero_facility")

    def test_funding_policy_rejects_invalid_probabilities(self):
        with self.assertRaises(ValueError):
            model.funding_policy_decision(1.1, .96)

    def test_reserve_thresholds_order_correctly(self):
        costs=[model.reserve_cost_flat(r) for r in (0,.03,.04,.05)]
        self.assertTrue(all(costs[i] > costs[i+1] for i in range(len(costs)-1)))

    def test_facility_cap_never_spends_reserve(self):
        cap,surplus=model.facility_cap(553069.62,500000)
        self.assertEqual(cap,25000)
        self.assertGreaterEqual(surplus-cap,0)
        cap0,_=model.facility_cap(493958.48,500000)
        self.assertEqual(cap0,0)

    def test_inflation_sensitivity(self):
        df=model.inflation_sensitivity()
        row=df[(df.inflation_rate==.03)&(df.payment_year==2033)].iloc[0]
        self.assertAlmostEqual(row.real_value_2026_usd,50000/(1.03**7),places=6)

    def test_wins_reconciliation_and_face_value(self):
        bonds,recon,alloc=model.current_wins_audit()
        self.assertEqual(float(bonds.face_value_total_usd.sum()),105000)
        self.assertEqual(float(bonds.annual_coupon_run_rate_usd.sum()),5225)
        reconstructed=float(recon.loc[recon.item=="Reconstructed account value","amount_usd"].iloc[0])
        reported=float(recon.loc[recon.item=="Reported current portfolio value","amount_usd"].iloc[0])
        self.assertAlmostEqual(reconstructed,reported,places=1)
        self.assertAlmostEqual(float(alloc.weight.sum()),1.0,places=9)
        gap=float(recon.loc[recon.item=="Line-item positions less reported total market value field","amount_usd"].iloc[0])
        self.assertAlmostEqual(gap,-1414.0,places=2)

    def test_wins_principal_maturities_are_not_early_cash(self):
        bonds,_,_=model.current_wins_audit()
        bridge=model.wins_principal_maturity_bridge(bonds)
        jan2036=bridge.loc[bridge.payment_date=="2036-01-01"].iloc[0]
        jan2037=bridge.loc[bridge.payment_date=="2037-01-01"].iloc[0]
        self.assertEqual(jan2036.principal_from_current_WInS_bonds_matured_before_payment_usd,52000)
        self.assertEqual(jan2037.principal_from_current_WInS_bonds_matured_before_payment_usd,69000)

    def test_cvar_funding_gap_nonnegative(self):
        x=np.array([300000,400000,450000,500000,550000,600000])
        s=model.tail_summary(x,"test")
        self.assertGreaterEqual(s["cvar95_funding_gap_usd"],0)

if __name__ == "__main__":
    unittest.main()
