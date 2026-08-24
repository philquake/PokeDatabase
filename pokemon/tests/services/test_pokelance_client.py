# pokemon/tests/test_pokelance_client.py

from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock
from pokemon.services.pokelance_client import (
    sync_pokemon_data,
    _walk_evolution_chain,
    _fetch_type_matchups,
    _to_fixture_entry,
    PokelanceAPIError,
)


class WalkEvolutionChainTest(SimpleTestCase):
    def test_flattens_linear_chain(self):
        chain_node = {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [
                        {
                            "species": {"name": "venusaur"},
                            "evolves_to": [],
                        }
                    ],
                }
            ],
        }
        result = _walk_evolution_chain(chain_node)

        self.assertEqual(result, ["Bulbasaur", "Ivysaur", "Venusaur"])
        
    def test_flattens_branching_chain(self):
        chain_node = {
            "species": {"name": "eevee"},
            "evolves_to": [
                {"species": {"name": "vaporeon"}, "evolves_to": []},
                {"species": {"name": "jolteon"}, "evolves_to": []},
                {"species": {"name": "flareon"}, "evolves_to": []},
            ],
        }

        result = _walk_evolution_chain(chain_node)

        self.assertEqual(result, ["Eevee", "Vaporeon", "Jolteon", "Flareon"])


class FetchTypeMatchupsTest(SimpleTestCase):
    @patch("pokemon.services.pokelance_client._get")
    def test_normal_type_matchups(self, mock_get):
        mock_get.return_value = {
            "damage_relations": {
                "double_damage_from": [
                    {"name": "fighting"},
                ],
                "half_damage_from": [],
                "no_damage_from": [
                    {"name": "ghost"},
                ],
            }
        }

        result = _fetch_type_matchups(["normal"], {})

        self.assertIn("fighting", result["weaknesses"])
        self.assertIn("ghost", result["immunities"])
        
    def test_cache_is_reused_across_calls(self):
        ...


class ToFixtureEntryTest(SimpleTestCase):

    def setUp(self):
        self.raw = {
            "id": 132,
            "name": "ditto",
            "base_experience": 101,
            "height": 3,
            "weight": 40,
            "sprites": {
                "other": {
                    "official-artwork": {
                        "front_default": "https://example.com/133.png"
                    }
                }
            },
            "stats": [
                {"stat": {"name": "hp"}, "base_stat": 48},
                {"stat": {"name": "attack"}, "base_stat": 48},
                {"stat": {"name": "defense"}, "base_stat": 48},
                {"stat": {"name": "special-attack"}, "base_stat": 48},
                {"stat": {"name": "special-defense"}, "base_stat": 48},
                {"stat": {"name": "speed"}, "base_stat": 48},
            ],
            "types": [{"type": {"name": "normal"}}],
            "abilities": [
                {"ability": {"name": "limber"}, "is_hidden": False},
                {"ability": {"name": "imposter"}, "is_hidden": True},
            ],
        }

        self.species = {
            "genera": [{"genus": "Transform Pokémon", "language": {"name": "en"}}],
            "generation": {"name": "generation-i"},
            "gender_rate": -1,
            "egg_groups": [{"name": "ditto"}],
            "capture_rate": 35,
            "base_happiness": 70,
        }

        self.evolution_chain = ["Ditto"]

        self.type_matchups = {
            "weaknesses": ["ground", "psychic"],
            "resistances": ["fire", "ice", "steel", "water"],
            "immunities": [],
        }

    def test_builds_correct_shape_from_raw_payload(self):
        entry = _to_fixture_entry(
            self.raw, self.species, self.evolution_chain, self.type_matchups
        )

        required_keys = [
            "pokedex_number", "name", "image", "category", "generation",
            "types", "base_stats", "stat_total", "abilities",
            "height_m", "weight_kg", "gender", "egg_groups",
            "catch_rate", "base_experience", "base_happiness",
            "type_effectiveness", "evolution_chain",
        ]
        for key in required_keys:
            self.assertIn(key, entry)

        self.assertEqual(entry["pokedex_number"], 132)
        self.assertEqual(entry["name"], "Ditto")
        self.assertEqual(entry["types"], ["Normal"])
        self.assertEqual(entry["base_stats"]["HP"], 48)
        self.assertEqual(entry["stat_total"], 288)
        self.assertIsNone(entry["gender"])  # gender_rate -1 -> genderless
        self.assertEqual(entry["type_effectiveness"], self.type_matchups)
        self.assertEqual(entry["evolution_chain"], self.evolution_chain)
        
    def test_raises_pokelance_error_on_malformed_payload(self):
        cases = {
            "missing_key": lambda: self.species.pop("gender_rate"),
            "wrong_type": lambda: self.raw.update(stats=None),
        }
        for label, corrupt in cases.items():
            #the first subTest's mutation (del) leaks into the second case since self.species/self.raw are the same dict objects across both loop iterations within one test method.
            with self.subTest(case=label):  
                self.setUp()  # reset fixtures before each corruption
                corrupt()
                with self.assertRaises(PokelanceAPIError) as cm:
                    _to_fixture_entry(self.raw, self.species, self.evolution_chain, self.type_matchups)
                    #checks if the error passes by PokelanceAPIError is a KeyError
                    self.assertIsInstance(cm.exception.__cause__,KeyError)
                    


class SyncPokemonDataTest(SimpleTestCase):
    @patch("pokemon.services.pokelance_client._save_fixture")
    @patch("pokemon.services.pokelance_client._to_fixture_entry")
    @patch("pokemon.services.pokelance_client._fetch_type_matchups")
    @patch("pokemon.services.pokelance_client._fetch_evolution_chain")
    @patch("pokemon.services.pokelance_client._fetch_species")
    @patch("pokemon.services.pokelance_client._fetch_pokemon")
    @patch("pokemon.services.pokelance_client._load_fixture")
    def test_stops_after_count_reached(
        self,
        mock_load,
        mock_fetch_pokemon,
        mock_fetch_species,
        mock_fetch_evolution_chain,
        mock_fetch_type_matchups,
        mock_to_fixture_entry,
        mock_save,
    ):
        
        mock_load.return_value = [{"pokedex_number": 1, "name": "Bulbasaur"}]
        mock_fetch_pokemon.return_value = {"id": 999, "name": "dummy"}
        mock_fetch_species.return_value = {"name": "dummy-species"}
        mock_fetch_evolution_chain.return_value = ["Dummy"]
        mock_fetch_type_matchups.return_value = {
            "weaknesses": [], "resistances": [], "immunities": []
        }
        mock_to_fixture_entry.return_value = {"pokedex_number": 999, "name": "Dummy"}

        count = 5
        result = sync_pokemon_data(count=count)

        self.assertEqual(len(result), count)
        self.assertEqual(mock_fetch_pokemon.call_count, count)
        self.assertEqual(mock_to_fixture_entry.call_count, count)

        mock_save.assert_called_once()
        
                    
                    