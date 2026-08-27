# pokemon/tests/test_pokelance_client.py

from django.test import SimpleTestCase
import requests
from unittest.mock import patch, MagicMock
from pokemon.services.pokelance_client import (
    _get,
    sync_pokemon_data,
    _walk_evolution_chain,
    _fetch_evolution_chain,
    _fetch_type_matchups,
    _fetch_locations,
    _fetch_generation,
    _fetch_pokemon,
    _fetch_moves,
    _fetch_species,
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
        
    @patch("pokemon.services.pokelance_client._get")
    def test_type_matchup_cache_is_reused_across_calls(self, mock_get):
        cache = {}

        mock_get.return_value = {
            "damage_relations": {
                "double_damage_from": [],
                "half_damage_from": [],
                "no_damage_from": [],
            }
        }

        first_result = _fetch_type_matchups(
            ["fire"],
            cache,
        )

        second_result = _fetch_type_matchups(
            ["fire"],
            cache,
        )

        self.assertEqual(first_result, second_result)
        mock_get.assert_called_once()
        
    @patch("pokemon.services.pokelance_client._get")
    def test_type_matchup_combines_two_types_correctly(self, mock_get):
        cache = {}

        def fake_get(url, context):
            if "fire" in url:
                return {
                    "damage_relations": {
                        "double_damage_from": [{"name": "rock"}],
                        "half_damage_from": [],
                        "no_damage_from": [],
                    }
                }

            if "flying" in url:
                return {
                    "damage_relations": {
                        "double_damage_from": [{"name": "rock"}],
                        "half_damage_from": [],
                        "no_damage_from": [],
                    }
                }

        mock_get.side_effect = fake_get

        result = _fetch_type_matchups(
            ["fire", "flying"],
            cache,
        )

        self.assertEqual(result,{
            "weaknesses": sorted(
                [
                    "rock",
                ]
            ),
            "resistances": [],
            "immunities": [],
        },
)

class FetchPokemonTest(SimpleTestCase):
    
    @patch("pokemon.services.pokelance_client._get")
    def test_fetch_pokemon_calls_correct_url(self, mock_get):
        _fetch_pokemon(94)

        #call_args.args[0] → inspect specifically the first argument meaning the url
        called_url = mock_get.call_args.args[0]

        self.assertEqual(called_url,"https://pokeapi.co/api/v2/pokemon/94/")
        
    @patch("pokemon.services.pokelance_client._get")
    def test_fetch_species(self, mock_get):
        raw_pokemon = {
            "name": "Gengar",
            "species": {
                "url": "https://pokeapi.co/api/v2/pokemon-species/94/"
            },
        }

        _fetch_species(raw_pokemon)

        mock_get.assert_called_once_with("https://pokeapi.co/api/v2/pokemon-species/94/","species data for Gengar")
        
class FetchEvolutionChainTests(SimpleTestCase):

    @patch("pokemon.services.pokelance_client._walk_evolution_chain")
    @patch("pokemon.services.pokelance_client._get")
    def test_fetch_evolution_chain_calls_get_and_walks_result(
        self,
        mock_get,
        mock_walk,
    ):
        species_data = {
            "name": "charizard",
            "evolution_chain": {
                "url": "https://pokeapi.co/api/v2/evolution-chain/94/"
            },
        }

        chain_data = {
            "chain": {
                "species": {
                    "name": "charmander"
                }
            }
        }

        expected = [
            {
                "name": "charmander",
            }
        ]

        mock_get.return_value = chain_data
        mock_walk.return_value = expected

        result = _fetch_evolution_chain(species_data)

        mock_get.assert_called_once_with(
            "https://pokeapi.co/api/v2/evolution-chain/94/",
            "evolution chain for charizard",
        )

        mock_walk.assert_called_once_with(chain_data["chain"])

        self.assertEqual(result, expected)
        
class FetchGenerationTests(SimpleTestCase):

    def test_fetch_generation_raises_on_unknown_generation_name(self):
        raw_pokemon = {
            "species": {
                "generation": {
                    "name": "generation-999",
                }
            }
        }

        with self.assertRaises(KeyError):
            _fetch_generation(raw_pokemon)
    
    def test_fetch_generation_maps_known_generation_name(self):
        species = {
                    "generation": {"name": "generation-i"}
                    }
                
        result = _fetch_generation(species)
        expected_result = 1
        self.assertEqual(result, expected_result)
        
class FetchLocationsTests(SimpleTestCase):

    @patch("pokemon.services.pokelance_client._get")
    def test_fetch_locations_flattens_nested_encounter_data(self, mock_get):

        mock_get.return_value = [
            {
                "location_area": {
                    "name": "viridian-forest",
                },
                "version_details": [
                    {
                        "version": {
                            "name": "red-blue",
                        },
                        "encounter_details": [
                            {
                                "method": {
                                    "name": "walk",
                                },
                                "chance": 20,
                                "min_level": 22,
                                "max_level": 23,
                            },
                            {
                                "method": {
                                    "name": "old-rod",
                                },
                                "chance": 10,
                                "min_level": 22,
                                "max_level": 23,
                            },
                        ],
                    }
                ],
            }
        ]

        result = _fetch_locations(25)

        expected = [
    {
        "location": "Viridian Forest",
        "version": "red-blue",
        "method": "Walk",
        "chance": 20,
        "min_level": 22,
        "max_level": 23,
    },
    {
        "location": "Viridian Forest",
        "version": "red-blue",
        "method": "Old Rod",
        "chance": 10,
        "min_level": 22,
        "max_level": 23,
    },
]

        self.assertEqual(result, expected)
        
    @patch("pokemon.services.pokelance_client._get")
    def test_fetch_locations_formats_location_and_method_names(self, mock_get):
        raw_pokemon = {
            "location_area_encounters": "https://pokeapi.co/api/v2/pokemon/25/encounters"
        }

        mock_get.return_value = [
            {
                "location_area": {
                    "name": "viridian-forest",
                },
                "version_details": [
                    {
                        "version": {
                            "name": "red-blue",
                        },
                        "encounter_details": [
                            {
                                "method": {
                                    "name": "old-rod",
                                },
                                "chance": 20,
                                "min_level": 1,
                                "max_level": 5,
                            }
                        ],
                    }
                ],
            }
        ]

        result = _fetch_locations(raw_pokemon)

        self.assertEqual(result[0]["location"], "Viridian Forest")
        self.assertEqual(result[0]["method"], "Old Rod")
        
    @patch("pokemon.services.pokelance_client._get")
    def test_fetch_locations_formats_location_and_method_names(self, mock_get):
        raw_pokemon = {
            "location_area_encounters": "https://pokeapi.co/api/v2/pokemon/25/encounters"
        }

        mock_get.return_value = [
            {
                "location_area": {
                    "name": "viridian-forest",
                },
                "version_details": [
                    {
                        "version": {
                            "name": "red-blue",
                        },
                        "encounter_details": [
                            {
                                "method": {
                                    "name": "old-rod",
                                },
                                "chance": 20,
                                "min_level": 1,
                                "max_level": 5,
                            }
                        ],
                    }
                ],
            }
        ]

        result = _fetch_locations(raw_pokemon)

        self.assertEqual(result[0]["location"], "Viridian Forest")
        self.assertEqual(result[0]["method"], "Old Rod")
        
    @patch("pokemon.services.pokelance_client._get")
    def test_fetch_locations_returns_empty_list_for_no_encounters(self, mock_get):
        raw_pokemon = {
            "location_area_encounters": "https://pokeapi.co/api/v2/pokemon/25/encounters"
        }

        mock_get.return_value = []

        result = _fetch_locations(raw_pokemon)

        self.assertEqual(result, [])
            
class FetchMovesTests(SimpleTestCase):

    def test_fetch_moves_formats_name_from_slug(self):
        raw_pokemon = {
            "moves": [
                {
                    "move": {
                        "name": "thunder-punch",
                    },
                    "version_group_details": [
                        {
                            "version_group": {
                                "name": "red-blue",
                            },
                            "level_learned_at": {
                                "name": "level-up",
                            },
                            "move_learn_method": {
                                "name": "level-up",
                            },
                        }
                    ],
                }
            ]
        }

        result = _fetch_moves(raw_pokemon)

        self.assertEqual(result[0]["name"], "Thunder Punch")

    def test_fetch_moves_returns_empty_list_when_no_moves_key(self):
        raw_pokemon = {}

        result = _fetch_moves(raw_pokemon)

        self.assertEqual(result, [])
        
    def test_fetch_moves_flattens_multiple_version_group_details(self):
            raw_pokemon = {
                "moves": [
                    {
                        "move": {
                            "name": "shadow-ball"
                        },
                        "version_group_details": [
                            {
                                "version_group": {
                                    "name": "gold-silver"
                                },
                                "level_learned_at": 30,
                                "move_learn_method": {
                                    "name": "level-up"
                                },
                            },
                            {
                                "version_group": {
                                    "name": "ruby-sapphire"
                                },
                                "level_learned_at": 32,
                                "move_learn_method": {
                                    "name": "level-up"
                                },
                            },
                        ],
                    }
                ]
            }
    
            result = _fetch_moves(raw_pokemon)
    
            expected = [
                {
                    "name": "Shadow Ball",
                    "version": "gold-silver",
                    "level_learnt": 30,
                    "method": "level-up",
                },
                {
                    "name": "Shadow Ball",
                    "version": "ruby-sapphire",
                    "level_learnt": 32,
                    "method": "level-up",
                },
            ]
    
            self.assertEqual(result, expected)


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
        
        self.locations = []

    def test_builds_correct_shape_from_raw_payload(self):
        entry = _to_fixture_entry(
            self.raw, self.species, self.evolution_chain, self.type_matchups, self.locations
        )

        required_keys = [
            "pokedex_number", "name", "image", "category", "generation",
            "types", "base_stats", "stat_total", "abilities",
            "height_m", "weight_kg", "gender", "egg_groups",
            "catch_rate", "base_experience", "base_happiness",
            "type_effectiveness", "evolution_chain", "moves", "locations"
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
        self.assertEqual(entry["locations"], self.locations)
        
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
                    _to_fixture_entry(self.raw, self.species, self.evolution_chain, self.type_matchups, self.locations)
                    #checks if the error passes by PokelanceAPIError is a KeyError
                    self.assertIsInstance(cm.exception.__cause__,KeyError)
        
    @patch("pokemon.services.pokelance_client.requests.get")
    def test_get_raises_pokelance_error_on_connection_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.HTTPError("Connection failed")
        
        with self.assertRaises(PokelanceAPIError) as cm:
            _get("https://pokeapi.co/api/v2/pokemon/12", "#12")
            
        self.assertIsInstance(cm.exception.__cause__, requests.exceptions.HTTPError)
            
    @patch("pokemon.services.pokelance_client.requests.get")
    def test_get_raises_pokelance_error_on_http_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.HTTPError("An HTTP error occurred.")
        
        with self.assertRaises(PokelanceAPIError) as cm:
            _get("https://pokeapi.co/api/v2/pokemon/12", "#12")
            
        self.assertIsInstance(cm.exception.__cause__, requests.exceptions.HTTPError)
        
    @patch("pokemon.services.pokelance_client.requests.get")
    def test_get_raises_pokelance_error_on_unparseable_json(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.json.side_effect = ValueError("A JSON error occurred.")
        
        with self.assertRaises(PokelanceAPIError) as cm:
            _get("https://pokeapi.co/api/v2/pokemon/12", "#12")
            
        self.assertIsInstance(cm.exception.__cause__, ValueError)   
        
    @patch("pokemon.services.pokelance_client.requests.get")
    def test_get_returns_parsed_json_on_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("A JSON error occurred.")

        with self.assertRaises(PokelanceAPIError) as cm:
            _get("https://pokeapi.co/api/v2/pokemon/12", "#12")
            
        self.assertIsInstance(cm.exception.__cause__,ValueError)
            
class ToFixtureEntryMovesTest(SimpleTestCase):
    
    @patch("pokemon.services.pokelance_client._fetch_moves")
    def test_moves_are_included_in_fixture_entry(self, mock_fetch_moves):
        mock_fetch_moves.return_value = [
            {"name": "Tackle", "version": "red-blue", "level_learnt": 1, "method": "level-up"}
        ]

        raw = {
            "id": 1, "name": "bulbasaur",
            "sprites": {"other": {"official-artwork": {"front_default": "img.png"}}},
            "types": [{"type": {"name": "grass"}}],
            "stats": [{"stat": {"name": "hp"}, "base_stat": 45}],
            "abilities": [], "height": 7, "weight": 69,
            "base_experience": 64,
        }
        species = {
            "genera": [{"genus": "Seed Pokémon", "language": {"name": "en"}}],
            "generation": {"name": "generation-i"},
            "gender_rate": 1, "egg_groups": [],
            "capture_rate": 45, "base_happiness": 70,
        }

        entry = _to_fixture_entry(
            raw, species, ["Bulbasaur"],
            {"weaknesses": [], "resistances": [], "immunities": []},
            [],
        )

        self.assertEqual(entry["moves"], mock_fetch_moves.return_value)
        mock_fetch_moves.assert_called_once_with(raw)
        
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
        
        mock_load.return_value = [{"pokedex_number": 1, "name": "Bulbasaur"}, ]
        mock_fetch_pokemon.return_value = {"id": 999, "name": "dummy", "types": [{"type": {"name": "normal"}}],}
        mock_fetch_species.return_value = {"name": "dummy-species"}
        mock_fetch_evolution_chain.return_value = ["Dummy"]
        mock_fetch_type_matchups.return_value = {
            "weaknesses": [], "resistances": [], "immunities": []
        }
        mock_to_fixture_entry.return_value = {"pokedex_number": 999, "name": "Dummy"}

        count = 5
        result = sync_pokemon_data(count=count, update_existing=False)

        self.assertEqual(len((result["added"])), count)
        self.assertEqual(mock_fetch_pokemon.call_count, count)
        self.assertEqual(mock_to_fixture_entry.call_count, count)

        mock_save.assert_called_once()
        