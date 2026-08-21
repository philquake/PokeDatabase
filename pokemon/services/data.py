import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"


def load_pokemon_data():
    """Load the full Pokémon dataset from the JSON fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_name_lookup(pokemon_data):
    """Build a case-insensitive name -> pokemon dict lookup."""
    return {p["name"].lower(): p for p in pokemon_data}


def get_pokemon_by_name(pokemon_data, name):
    """Case-insensitive lookup of a single pokemon dict by name, or None."""
    return build_name_lookup(pokemon_data).get(name.lower())