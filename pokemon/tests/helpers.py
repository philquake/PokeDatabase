from pathlib import Path

from django.test import TestCase

from pokemon.services.data import import_abilities_json, import_items_json, import_moves_json, import_pokemon_json

SAMPLE_POKEMON_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_pokemon.json"


def load_sample_pokemon():
    """
    Load a small, real slice of the dataset into the test database:
    Bulbasaur–Charizard (#1–6), Gastly–Onix (#92–95), Voltorb (#100) and
    Kangaskhan (#115). Enough for prev/next, evolution chains, genderless
    Pokémon and a full featured grid.
    """
    import_pokemon_json(SAMPLE_POKEMON_PATH)


class PokemonDataTestCase(TestCase):
    """TestCase with the sample Pokémon loaded once per class."""

    @classmethod
    def setUpTestData(cls):
        load_sample_pokemon()
        load_sample_moves()
        load_sample_abilities()


SAMPLE_MOVES_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_moves.json"


SAMPLE_ABILITIES_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_abilities.json"


def load_sample_abilities():
    """Effect text for six of the sample Pokémon's abilities (Blaze, Overgrow, Static ...)."""
    import_abilities_json(SAMPLE_ABILITIES_PATH)


SAMPLE_ITEMS_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_items.json"


def load_sample_items():
    """Six items across three categories, plus one with no cost, effect or sprite."""
    import_items_json(SAMPLE_ITEMS_PATH)


def load_sample_moves():
    """Load a small set of move stats (Tackle, Flamethrower, Growl ... one per category)."""
    import_moves_json(SAMPLE_MOVES_PATH)
