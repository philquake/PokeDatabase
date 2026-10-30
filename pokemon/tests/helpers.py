from pathlib import Path

from django.test import TestCase

from pokemon.services.data import import_pokemon_json

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
