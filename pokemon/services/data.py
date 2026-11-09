"""
Conversion between PokeDatabase's fixture-shaped Pokémon dicts (what the
PokéAPI sync builds and what the templates read) and the database models.
"""

import json
from pathlib import Path

from django.db import transaction

from pokemon.models import (
    Ability, FormMove, Item, Move, Pokemon, PokemonEncounter, PokemonForm, PokemonMove,
)

FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"

POKEMON_FIELDS = [
    "pokedex_number", "name", "image", "category", "generation", "types",
    "base_stats", "stat_total", "abilities", "height_m", "weight_kg", "gender",
    "egg_groups", "catch_rate", "base_experience", "base_happiness",
    "type_effectiveness", "evolution_chain", "ev_yield", "growth_rate", "held_items",
]
MOVE_FIELDS = ["name", "version", "level_learnt", "method"]
MOVE_INFO_FIELDS = ["name", "type", "damage_class", "power", "accuracy", "pp", "generation", "effect"]
ABILITY_FIELDS = ["name", "generation", "effect"]
ITEM_FIELDS = ["name", "category", "cost", "effect", "sprite"]
FORM_FIELDS = [
    "slug", "pokeapi_id", "kind", "label", "image", "types", "base_stats", "stat_total",
    "abilities", "height_m", "weight_kg", "base_experience", "ev_yield", "held_items",
]
ENCOUNTER_FIELDS = ["location", "version", "method", "chance", "min_level", "max_level"]


def pokemon_to_dict(pokemon, include_related=False, form_moves=True):
    """
    Fixture-shaped dict for a Pokemon; moves/locations/forms only when asked for. `form_moves=False`
    leaves each form's move rows out (the sync needs them to detect drift, a page render does not).
    """
    data = {field: getattr(pokemon, field) for field in POKEMON_FIELDS}
    data["region"] = pokemon.region
    if include_related:
        data["moves"] = list(pokemon.moves.values(*MOVE_FIELDS))
        data["locations"] = list(pokemon.locations.values(*ENCOUNTER_FIELDS))
        forms = pokemon.forms.prefetch_related("moves") if form_moves else pokemon.forms.all()
        data["forms"] = [form_to_dict(form, include_moves=form_moves) for form in forms]
    return data


def form_to_dict(form, include_moves=False):
    """Dict of one PokemonForm (fixture shape: the same keys the sync builds)."""
    data = {field: getattr(form, field) for field in FORM_FIELDS}
    if include_moves:
        data["moves"] = [{f: getattr(m, f) for f in MOVE_FIELDS} for m in form.moves.all()]
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
    if "forms" in entry:
        _replace_forms(pokemon, entry["forms"])
    return pokemon


def _replace_forms(pokemon, forms):
    """Make `pokemon`'s forms match `forms` (upsert by slug, delete the rest). A form's moves are replaced only if it has a "moves" key."""
    keep = []
    for entry in forms:
        defaults = {k: entry[k] for k in FORM_FIELDS if k in entry and k != "slug"}
        form, _ = PokemonForm.objects.update_or_create(pokemon=pokemon, slug=entry["slug"], defaults=defaults)
        keep.append(form.pk)
        if "moves" in entry:
            form.moves.all().delete()
            FormMove.objects.bulk_create(
                FormMove(form=form, **{k: m[k] for k in MOVE_FIELDS}) for m in entry["moves"]
            )
    pokemon.forms.exclude(pk__in=keep).delete()


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


def ability_to_dict(ability):
    return {field: getattr(ability, field) for field in ABILITY_FIELDS}


def save_ability_entry(entry):
    """Create or update an Ability by name; only the keys present in `entry` are written."""
    defaults = {k: entry[k] for k in ABILITY_FIELDS if k in entry and k != "name"}
    ability, _ = Ability.objects.update_or_create(name=entry["name"], defaults=defaults)
    return ability


def get_ability_info(names):
    """{name: stats dict} for whichever of `names` have effect text stored."""
    return {a.name: ability_to_dict(a) for a in Ability.objects.filter(name__in=set(names))}


def import_abilities_json(path):
    """Load (or refresh) ability effect text from a JSON list of ability dicts."""
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    for entry in entries:
        save_ability_entry(entry)
    return len(entries)


def item_to_dict(item):
    return {field: getattr(item, field) for field in ITEM_FIELDS}


def save_item_entry(entry):
    """Create or update an Item by name; only the keys present in `entry` are written."""
    defaults = {k: entry[k] for k in ITEM_FIELDS if k in entry and k != "name"}
    item, _ = Item.objects.update_or_create(name=entry["name"], defaults=defaults)
    return item


def import_items_json(path):
    """Load (or refresh) items from a JSON list of item dicts."""
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    for entry in entries:
        save_item_entry(entry)
    return len(entries)
