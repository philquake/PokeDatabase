import json
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from pokemon.models import Pokemon
from pokemon.services.data import (
    get_pokemon_by_name,
    import_pokemon_json,
    pokemon_to_dict,
    save_pokemon_entry,
)
from pokemon.services.pokelance_client import PokelanceAPIError
from pokemon.tests.helpers import SAMPLE_POKEMON_PATH


def _entry(**overrides):
    entry = {
        "pokedex_number": 94,
        "name": "Gengar",
        "image": "https://example.com/gengar.png",
        "category": "Shadow Pokémon",
        "generation": 1,
        "types": ["Ghost", "Poison"],
        "base_stats": {"HP": 60, "Special Attack": 130},
        "stat_total": 190,
        "abilities": [{"name": "Cursed Body", "hidden": False}],
        "height_m": 1.5,
        "weight_kg": 40.5,
        "gender": {"female_pct": 50.0, "male_pct": 50.0},
        "egg_groups": ["Amorphous"],
        "catch_rate": 45,
        "base_experience": 250,
        "base_happiness": 50,
        "type_effectiveness": {"weaknesses": ["dark"], "resistances": [], "immunities": ["normal"]},
        "evolution_chain": ["Gastly", "Haunter", "Gengar"],
        "ev_yield": {"Special Attack": 3},
        "growth_rate": "medium-slow",
        "held_items": ["Spell Tag"],
        "moves": [
            {"name": "Lick", "version": "red-blue", "level_learnt": 1, "method": "level-up"},
            {"name": "Thunderbolt", "version": "red-blue", "level_learnt": 0, "method": "machine"},
        ],
        "locations": [
            {"location": "Lavender Town", "version": "red-blue", "method": "Walk",
             "chance": 5, "min_level": 20, "max_level": 22},
        ],
    }
    entry.update(overrides)
    return entry


class SavePokemonEntryTest(TestCase):

    def test_round_trips_through_database(self):
        entry = _entry()
        save_pokemon_entry(entry)

        result = pokemon_to_dict(Pokemon.objects.get(pokedex_number=94), include_related=True)

        # A Pokémon with no alternate forms round-trips with an empty "forms" list.
        self.assertEqual({k: v for k, v in result.items() if k != "region"}, {**entry, "forms": []})

    def test_region_is_derived_from_generation(self):
        save_pokemon_entry(_entry(generation=9))
        self.assertEqual(Pokemon.objects.get(pokedex_number=94).region, "Paldea")

    def test_saving_again_replaces_moves_instead_of_duplicating(self):
        save_pokemon_entry(_entry())
        save_pokemon_entry(_entry(moves=[
            {"name": "Hypnosis", "version": "yellow", "level_learnt": 1, "method": "level-up"},
        ]))

        pokemon = Pokemon.objects.get(pokedex_number=94)
        self.assertEqual(list(pokemon.moves.values_list("name", flat=True)), ["Hypnosis"])
        self.assertEqual(pokemon.locations.count(), 1)

    def test_partial_entry_only_updates_given_fields(self):
        save_pokemon_entry(_entry())
        save_pokemon_entry({"pokedex_number": 94, "catch_rate": 3})

        pokemon = Pokemon.objects.get(pokedex_number=94)
        self.assertEqual(pokemon.catch_rate, 3)
        self.assertEqual(pokemon.name, "Gengar")
        self.assertEqual(pokemon.moves.count(), 2)

    def test_pokemon_to_dict_leaves_out_moves_and_locations_by_default(self):
        save_pokemon_entry(_entry())
        result = pokemon_to_dict(Pokemon.objects.get(pokedex_number=94))

        self.assertNotIn("moves", result)
        self.assertNotIn("locations", result)

    def test_get_pokemon_by_name_is_case_insensitive(self):
        save_pokemon_entry(_entry())
        self.assertEqual(get_pokemon_by_name(" gEnGaR ").pokedex_number, 94)
        self.assertIsNone(get_pokemon_by_name("NotARealPokemon"))


class ImportPokemonJsonTest(TestCase):

    def test_imports_sample_file(self):
        count = import_pokemon_json(SAMPLE_POKEMON_PATH)

        self.assertEqual(count, 12)
        self.assertEqual(Pokemon.objects.count(), 12)
        self.assertEqual(Pokemon.objects.first().name, "Bulbasaur")

    def test_duplicate_entries_are_stored_once(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([_entry(), _entry()], f)

        import_pokemon_json(f.name)

        self.assertEqual(Pokemon.objects.count(), 1)
        self.assertEqual(Pokemon.objects.get().moves.count(), 2)

    def test_import_command(self):
        out = StringIO()
        call_command("import_pokemon_json", str(SAMPLE_POKEMON_PATH), stdout=out)

        self.assertIn("Imported 12 Pokémon", out.getvalue())
        self.assertEqual(Pokemon.objects.count(), 12)


class SyncPokemonCommandTest(TestCase):

    @patch("pokemon.management.commands.sync_pokemon.sync_pokemon_data")
    def test_passes_options_and_reports_result(self, mock_sync):
        mock_sync.return_value = {"added": [{"name": "Chikorita"}], "updated": []}
        out = StringIO()

        call_command("sync_pokemon", "--count", "3", "--no-update", stdout=out)

        mock_sync.assert_called_once_with(count=3, update_existing=False)
        self.assertIn("Added: Chikorita", out.getvalue())
        self.assertIn("Updated: none", out.getvalue())

    @patch("pokemon.management.commands.sync_pokemon.sync_pokemon_data")
    def test_api_error_becomes_command_error(self, mock_sync):
        mock_sync.side_effect = PokelanceAPIError("Pokelance API unreachable")

        with self.assertRaises(CommandError):
            call_command("sync_pokemon", stdout=StringIO())
