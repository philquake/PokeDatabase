"""
Conversion between PokeDatabase's fixture-shaped Pokémon dicts (what the
PokéAPI sync builds and what the templates read) and the database models.
"""

import json
from pathlib import Path

from django.db import transaction

from pokemon.models import Move, Pokemon, PokemonEncounter, PokemonMove

FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"

POKEMON_FIELDS = [
    "pokedex_number", "name", "image", "category", "generation", "types",
    "base_stats", "stat_total", "abilities", "height_m", "weight_kg", "gender",
    "egg_groups", "catch_rate", "base_experience", "base_happiness",
    "type_effectiveness", "evolution_chain", "ev_yield", "growth_rate", "held_items",
]
MOVE_FIELDS = ["name", "version", "level_learnt", "method"]
MOVE_INFO_FIELDS = ["name", "type", "damage_class", "power", "accuracy", "pp", "generation", "effect"]
ENCOUNTER_FIELDS = ["location", "version", "method", "chance", "min_level", "max_level"]


def pokemon_to_dict(pokemon, include_related=False):
    """Fixture-shaped dict for a Pokemon; moves/locations only when asked for."""
    data = {field: getattr(pokemon, field) for field in POKEMON_FIELDS}
    data["region"] = pokemon.region
    if include_related:
        data["moves"] = list(pokemon.moves.values(*MOVE_FIELDS))
        data["locations"] = list(pokemon.locations.values(*ENCOUNTER_FIELDS))
    return data


def get_pokemon_by_name(name):
    """Case-insensitive lookup of a single Pokemon, or None."""
    return Pokemon.objects.filter(name__iexact=name.strip()).first()


@transaction.atomic
def save_pokemon_entry(entry):
    """
    Create or update a Pokemon from a fixture-shaped dict. Only the keys
    present in `entry` are written, so a partial dict (e.g. a sync diff) is
    fine. If "moves" / "locations" are present they replace the existing rows.
    """
    defaults = {k: entry[k] for k in POKEMON_FIELDS if k in entry and k != "pokedex_number"}
    pokemon, _ = Pokemon.objects.update_or_create(
        pokedex_number=entry["pokedex_number"], defaults=defaults
    )

    if "moves" in entry:
        pokemon.moves.all().delete()
        PokemonMove.objects.bulk_create(
            PokemonMove(pokemon=pokemon, **{k: m[k] for k in MOVE_FIELDS})
            for m in entry["moves"]
        )
    if "locations" in entry:
        pokemon.locations.all().delete()
        PokemonEncounter.objects.bulk_create(
            PokemonEncounter(pokemon=pokemon, **{k: e[k] for k in ENCOUNTER_FIELDS})
            for e in entry["locations"]
        )
    return pokemon


def import_pokemon_json(path=FIXTURE_PATH):
    """Load (or refresh) every Pokémon in a fixture-shaped JSON file into the database."""
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    for entry in entries:
        save_pokemon_entry(entry)
    return len(entries)


def move_to_dict(move):
    """Plain dict of a Move's stats (the shape the sync builds and templates read)."""
    return {field: getattr(move, field) for field in MOVE_INFO_FIELDS}


def save_move_entry(entry):
    """Create or update a Move by name; only the keys present in `entry` are written."""
    defaults = {k: entry[k] for k in MOVE_INFO_FIELDS if k in entry and k != "name"}
    move, _ = Move.objects.update_or_create(name=entry["name"], defaults=defaults)
    return move


def get_move_info(names):
    """{name: stats dict} for whichever of `names` have stats stored; unknown names are skipped."""
    return {m.name: move_to_dict(m) for m in Move.objects.filter(name__in=set(names))}


def import_moves_json(path):
    """Load (or refresh) move stats from a JSON list of move dicts."""
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    for entry in entries:
        save_move_entry(entry)
    return len(entries)
