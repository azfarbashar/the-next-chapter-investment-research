import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import liability_ladder as ll

class LiabilityLadderTests(unittest.TestCase):
    def test_zero_rate_requires_full_500k(self):
        rates = {t: 0.0 for t in range(1, 10)}
        self.assertAlmostEqual(ll.reserve_pv_from_spot_rates(rates), 500000.0)

    def test_flat_three_percent_matches_annuity_due(self):
        rates = {t: 0.03 for t in range(1, 10)}
        expected = sum(50000 / (1.03 ** t) for t in range(10))
        self.assertAlmostEqual(ll.reserve_pv_from_spot_rates(rates), expected, places=6)

    def test_first_payment_is_undiscounted(self):
        rates = {t: 0.04 for t in range(1, 10)}
        ladder = ll.reserve_ladder(rates)
        self.assertEqual(ladder.iloc[0].initial_purchase_cost_usd, 50000.0)
        self.assertEqual(ladder.iloc[0].discount_factor, 1.0)

    def test_ladder_has_ten_payment_rungs(self):
        ladder = ll.reserve_ladder({t: 0.03 for t in range(1, 10)})
        self.assertEqual(len(ladder), 10)
        self.assertEqual(ladder.payment_year.tolist(), list(range(2033, 2043)))
        self.assertTrue((ladder.nominal_cash_required_usd == 50000).all())

    def test_ladder_cost_sums_to_reserve_pv(self):
        curve = {t: 0.025 + 0.001 * t for t in range(1, 10)}
        ladder = ll.reserve_ladder(curve)
        self.assertAlmostEqual(ladder.initial_purchase_cost_usd.sum(), ll.reserve_pv_from_spot_rates(curve), places=6)

    def test_rollforward_retires_one_rung_each_year(self):
        schedule = ll.reserve_rollforward({t: 0.03 for t in range(1, 10)})
        self.assertEqual(schedule.rungs_remaining_after_payment.tolist(), list(range(9, -1, -1)))
        self.assertEqual(schedule.iloc[-1].future_nominal_payments_remaining_usd, 0)

    def test_facility_cap_is_zero_if_p05_below_reserve(self):
        cap, surplus = ll.facility_cap_from_p05(459970, 500000)
        self.assertEqual(cap, 0)
        self.assertLess(surplus, 0)

    def test_middle_band_facility_cap_rounds_down(self):
        cap, surplus = ll.facility_cap_from_p05(548038.64, 500000)
        self.assertEqual(cap, 20000)
        self.assertAlmostEqual(surplus, 48038.64, places=2)
        self.assertLessEqual(cap, surplus * 0.5)

    def test_invalid_curve_rejected(self):
        with self.assertRaises(ValueError):
            ll.reserve_pv_from_spot_rates({1: .03})

if __name__ == "__main__":
    unittest.main()
