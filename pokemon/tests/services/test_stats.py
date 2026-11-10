from django.test import SimpleTestCase

from pokemon.services.stats import calculate_final_stat, calculate_speed_tiers


class FinalStatCalculationTest(SimpleTestCase):

    def test_speed_tiers_at_level_50_and_100(self):
        tiers = calculate_speed_tiers(100)

        self.assertEqual(tiers["max-50"], 167)
        self.assertEqual(tiers["neutral-50"], 152)
        self.assertEqual(tiers["uninvested-50"], 120)
        self.assertEqual(tiers["speed-nature-50"], 132)
        self.assertEqual(tiers["choice-scarf-50"], 250)
        self.assertEqual(tiers["max-100"], 328)
        self.assertEqual(tiers["neutral-100"], 299)
        self.assertEqual(tiers["uninvested-100"], 236)
        self.assertEqual(tiers["speed-nature-100"], 259)
        self.assertEqual(tiers["choice-scarf-100"], 492)

    def test_final_stat_applies_ev_quarters_and_nature_floors(self):
        self.assertEqual(
            calculate_final_stat(base=100, level=50, iv=31, ev=252, nature=1.1),
            167,
        )

    def test_hp_uses_hp_formula_without_nature(self):
        self.assertEqual(
            calculate_final_stat(base=100, level=50, iv=31, ev=252, is_hp=True),
            207,
        )
