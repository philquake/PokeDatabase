import json

from django.test import SimpleTestCase

from pokemon.services.types import TYPE_CHART, TYPES, effectiveness, type_matchups
from pokemon.tests.helpers import SAMPLE_POKEMON_PATH


class TypeChartTest(SimpleTestCase):

    def test_there_are_eighteen_types_and_every_one_has_a_row(self):
        self.assertEqual(len(TYPES), 18)
        self.assertEqual(set(TYPE_CHART), set(TYPES))

    def test_every_chart_entry_names_real_types_and_odd_multipliers_only(self):
        for attacker, row in TYPE_CHART.items():
            for defender, multiplier in row.items():
                self.assertIn(defender, TYPES)
                self.assertIn(multiplier, (0, 0.5, 2), f"{attacker} -> {defender}")

    def test_known_matchups(self):
        self.assertEqual(effectiveness("fire", "grass"), 2)
        self.assertEqual(effectiveness("water", "water"), 0.5)
        self.assertEqual(effectiveness("normal", "ghost"), 0)
        self.assertEqual(effectiveness("electric", "ground"), 0)
        self.assertEqual(effectiveness("dragon", "fairy"), 0)
        self.assertEqual(effectiveness("steel", "fairy"), 2)

    def test_unlisted_matchups_are_neutral(self):
        self.assertEqual(effectiveness("normal", "fire"), 1)

    def test_chart_agrees_with_every_stored_pokemon_matchup(self):
        """The sample Pokémon carry PokéAPI's own weaknesses/resistances/immunities."""
        with open(SAMPLE_POKEMON_PATH, encoding="utf-8") as f:
            sample = json.load(f)

        for pokemon in sample:
            defending = [t.lower() for t in pokemon["types"]]
            weak, resist, immune = set(), set(), set()
            for attacker in TYPES:
                multiplier = 1
                for defender in defending:
                    multiplier *= effectiveness(attacker, defender)
                if multiplier == 0:
                    immune.add(attacker)
                elif multiplier > 1:
                    weak.add(attacker)
                elif multiplier < 1:
                    resist.add(attacker)

            stored = pokemon["type_effectiveness"]
            self.assertEqual(weak, set(stored["weaknesses"]), pokemon["name"])
            self.assertEqual(resist, set(stored["resistances"]), pokemon["name"])
            self.assertEqual(immune, set(stored["immunities"]), pokemon["name"])


class TypeMatchupsTest(SimpleTestCase):

    def test_fire_matchups(self):
        matchups = type_matchups("fire")

        self.assertEqual(matchups["attack"]["super"], ["grass", "ice", "bug", "steel"])
        self.assertEqual(matchups["attack"]["not_very"], ["fire", "water", "rock", "dragon"])
        self.assertEqual(matchups["attack"]["no_effect"], [])
        self.assertEqual(matchups["defend"]["weak"], ["water", "ground", "rock"])
        self.assertEqual(matchups["defend"]["resist"], ["fire", "grass", "ice", "bug", "steel", "fairy"])
        self.assertEqual(matchups["defend"]["immune"], [])

    def test_ghost_is_immune_to_normal_and_fighting(self):
        self.assertEqual(type_matchups("ghost")["defend"]["immune"], ["normal", "fighting"])

    def test_results_follow_the_standard_type_order(self):
        order = {t: i for i, t in enumerate(TYPES)}
        for key in ("super", "not_very", "no_effect"):
            names = type_matchups("normal")["attack"][key]
            self.assertEqual(names, sorted(names, key=order.get))


class DefenseCellsTest(SimpleTestCase):

    def cells(self, *types):
        from pokemon.services.types import defense_cells
        return {c["slug"]: c for c in defense_cells(types)}

    def test_one_cell_per_type_in_standard_order(self):
        from pokemon.services.types import defense_cells
        self.assertEqual([c["slug"] for c in defense_cells(["normal"])], TYPES)

    def test_dual_type_stacks_multipliers(self):
        cells = self.cells("fire", "flying")

        self.assertEqual(cells["rock"]["multiplier"], 4)        # weak to rock twice over
        self.assertEqual(cells["rock"]["label"], "4×")
        self.assertEqual(cells["rock"]["state"], "x4")
        self.assertEqual(cells["water"]["multiplier"], 2)
        self.assertEqual(cells["grass"]["multiplier"], 0.25)    # resisted by both types
        self.assertEqual(cells["grass"]["label"], "¼×")
        self.assertEqual(cells["grass"]["state"], "quarter")
        self.assertEqual(cells["fire"]["multiplier"], 0.5)
        self.assertEqual(cells["fire"]["state"], "half")
        self.assertEqual(cells["ground"]["multiplier"], 0)      # flying is immune to ground
        self.assertEqual(cells["ground"]["state"], "immune")
        self.assertEqual(cells["ice"]["multiplier"], 1)         # 1/2 x 2
        self.assertEqual(cells["ice"]["state"], "x1")
        self.assertEqual(cells["ice"]["label"], "1×")

    def test_single_type(self):
        cells = self.cells("normal")
        self.assertEqual(cells["fighting"]["multiplier"], 2)
        self.assertEqual(cells["ghost"]["multiplier"], 0)
        self.assertEqual(cells["fire"]["multiplier"], 1)

    def test_names_are_title_case_and_unknown_types_are_ignored(self):
        cells = self.cells("Fire", "Shadow")
        self.assertEqual(cells["water"]["name"], "Water")
        self.assertEqual(cells["water"]["multiplier"], 2)
