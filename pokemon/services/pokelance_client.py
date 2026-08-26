"""
pokelance_client.py

Client for syncing new Pokémon from the public PokéAPI (https://pokeapi.co)
into PokeDatabase's JSON-backed fixture file.

    - identity: pokedex_number, name, image, category (genus), generation
    - battle basics: types, base_stats (+ total), abilities
    - physical: height_m, weight_kg
    - breeding: gender, egg_groups
    - meta: catch_rate, base_experience, base_happiness
    - type_effectiveness: weaknesses / resistances / immunities for this Pokémon's type combination
    - evolution_chain: ordered list of species names in its evolutionary line

This means fetching several PokéAPI endpoints per Pokémon (the pokemon
resource, its species, its evolution chain, and its type(s)' damage
relations) instead of just one — sync_pokemon_data() therefore makes more
requests per Pokémon than before. Type-matchup lookups are cached for the
duration of a single sync() call since many Pokémon share types.
"""

import json
from pathlib import Path
import requests


FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "assets" / "static" / "fixtures" / "pokemon.json"
)

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/pokemon"
POKEAPI_POKEMON_SPECIES_URL = "https://pokeapi.co/api/v2/pokemon-species" 
REQUEST_TIMEOUT_SECONDS = 5

# PokéAPI's stat slugs -> the labels PokeDatabase's fixture already uses.
STAT_NAME_LOOKUP = {
    "hp": "HP",
    "attack": "Attack",
    "defense": "Defense",
    "special-attack": "Special Attack",
    "special-defense": "Special Defense",
    "speed": "Speed",
}

ALL_TYPE_NAMES = [
    "normal", "fire", "water", "electric", "grass", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
    "dragon", "dark", "steel", "fairy",
]

GENERATIONS = {
    "generation-i": 1,
    "generation-ii": 2,
    "generation-iii": 3,
    "generation-iv": 4,
    "generation-v": 5,
    "generation-vi": 6,
    "generation-vii": 7,
    "generation-viii": 8,
}

IDENTITY_FIELDS = {"pokedex_number"}

class PokelanceAPIError(Exception):
    """Raised when the Pokelance client can't complete a sync."""


def _load_fixture():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_fixture(pokemon_data):
    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(pokemon_data, f, indent=2)


def _get(url, context):

    """Shared GET-and-decode helper. Wraps any failure in PokelanceAPIError."""
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise PokelanceAPIError(
            f"Pokelance API unreachable while fetching {context}: {exc}"
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise PokelanceAPIError(
            f"Pokelance API returned an unreadable response for {context}"
        ) from exc


def _fetch_pokemon(pokedex_number):
    return _get(f"{POKEAPI_BASE_URL}/{pokedex_number}/", f"#{pokedex_number}")


def _fetch_species(raw_pokemon):
    species_url = raw_pokemon["species"]["url"]
    return _get(species_url, f"species data for {raw_pokemon['name']}")


# Flatten PokéAPI's per-move `version_group_details` into one row per
#     (move, version group, method, level) combination:
 
#         {"name": "Thunder Punch", "version": "red-blue", "level": 0, "method": "egg"}
def _fetch_moves(raw_pokemon):
    moves = []
    for move_entry in raw_pokemon.get("moves", []):
        move_name = move_entry["move"]["name"].replace("-", " ").title()
        for detail in move_entry.get("version_group_details", []):
            moves.append({
                "name": move_name,
                "version": detail["version_group"]["name"],
                "level_learnt": detail["level_learned_at"],
                "method": detail["move_learn_method"]["name"],
            })
    return moves

def _fetch_generation(species):
    gen_name = species["generation"]["name"]  # e.g. "generation-i"
    for gen, gen_num in GENERATIONS.items():
        if gen == gen_name:
            return gen_num
    raise PokelanceAPIError(
        f"Unknown generation '{gen_name}' for {species['name']}"
    )

def _walk_evolution_chain(chain_node, names=None):
    """Flatten PokéAPI's nested evolution chain tree into an ordered name list."""
    if names is None:
        names = []
    names.append(chain_node["species"]["name"].capitalize())
    for next_stage in chain_node.get("evolves_to", []):
        _walk_evolution_chain(next_stage, names)
    return names


def _fetch_evolution_chain(species_data):
    chain_url = species_data["evolution_chain"]["url"]
    chain_data = _get(chain_url, f"evolution chain for {species_data['name']}")
    return _walk_evolution_chain(chain_data["chain"])


def _fetch_type_matchups(type_names, cache):
    """
    Combine damage relations across one or two types into a single
    multiplier per attacking type, then bucket them into weaknesses
    (>1x), resistances (<1x and >0x), and immunities (0x).
    """
    multipliers = {t: 1.0 for t in ALL_TYPE_NAMES}

    for type_name in type_names:
        if type_name not in cache:
            cache[type_name] = _get(
                f"https://pokeapi.co/api/v2/type/{type_name}/",
                f"type data for {type_name}",
            )
        relations = cache[type_name]["damage_relations"]

        for entry in relations["double_damage_from"]:
            multipliers[entry["name"]] *= 2
        for entry in relations["half_damage_from"]:
            multipliers[entry["name"]] *= 0.5
        for entry in relations["no_damage_from"]:
            multipliers[entry["name"]] *= 0

    return {
        "weaknesses": sorted(t for t, m in multipliers.items() if m > 1),
        "resistances": sorted(t for t, m in multipliers.items() if 0 < m < 1),
        "immunities": sorted(t for t, m in multipliers.items() if m == 0),
    }

def _fetch_and_build_entry(pokedex_number, type_matchup_cache):
    """
    Run the full fetch pipeline (pokemon -> species -> evolution chain ->
    type matchups) for a single pokedex number and return a fixture-shaped
    entry. Shared by both the "add new" and "check existing" passes of
    sync_pokemon_data() so there's exactly one definition of what a fresh,
    authoritative fixture entry looks like.
    """
    raw = _fetch_pokemon(pokedex_number)
    species = _fetch_species(raw)
    evolution_chain = _fetch_evolution_chain(species)
    type_matchups = _fetch_type_matchups(
        [t["type"]["name"] for t in raw["types"]], type_matchup_cache
    )
    return _to_fixture_entry(raw, species, evolution_chain, type_matchups)

def _diff_fields(existing_entry, fresh_entry):
    """
    Compare a fixture entry against a freshly-fetched entry and return only
    the fields that are missing from the fixture or no longer match the
    API — never the fields that already agree. An empty dict means the
    fixture is already up to date for this Pokémon.
    """
    return {
        key: fresh_value
        for key, fresh_value in fresh_entry.items()
        if key not in IDENTITY_FIELDS and existing_entry.get(key) != fresh_value
    }
    
def _to_fixture_entry(raw, species, evolution_chain, type_matchups):
    """Convert raw PokéAPI data into PokeDatabase's fixture shape."""
    try:
        base_stats = {
            STAT_NAME_LOOKUP[stat["stat"]["name"]]: stat["base_stat"]
            for stat in raw["stats"]
            if stat["stat"]["name"] in STAT_NAME_LOOKUP
        }

        english_genus = next(
            (g["genus"] for g in species["genera"] if g["language"]["name"] == "en"),
            "",
        )

        gender_rate = species["gender_rate"]  # -1 = genderless, else eighths female
        gender_info = (
            None
            if gender_rate == -1
            else {
                "female_pct": round(gender_rate / 8 * 100, 1),
                "male_pct": round((8 - gender_rate) / 8 * 100, 1),
            }
        )
        
        

        return {
            "pokedex_number": raw["id"],
            "name": raw["name"].capitalize(),
            "image": raw["sprites"]["other"]["official-artwork"]["front_default"],
            "category": english_genus,
            "generation": _fetch_generation(species),
            "types": [t["type"]["name"].capitalize() for t in raw["types"]],
            "base_stats": base_stats,
            "stat_total": sum(base_stats.values()),
            "abilities": [
                {
                    "name": a["ability"]["name"].replace("-", " ").title(),
                    "hidden": a["is_hidden"],
                }
                for a in raw["abilities"]
            ],
            "height_m": raw["height"] / 10,
            "weight_kg": raw["weight"] / 10,
            "gender": gender_info,
            "egg_groups": [
                eg["name"].replace("-", " ").title() for eg in species["egg_groups"]
            ],
            "catch_rate": species["capture_rate"],
            "base_experience": raw["base_experience"],
            "base_happiness": species["base_happiness"],
            "type_effectiveness": type_matchups,
            "evolution_chain": evolution_chain,
            "moves": _fetch_moves(raw),
        }
    except (KeyError, TypeError) as exc:
        raise PokelanceAPIError(
            f"Pokelance API returned an unexpected payload shape: {exc}"
        ) from exc


def sync_pokemon_data(count=5, update_existing=True):
    """
    Fetch up to `count` new Pokémon from PokéAPI that aren't already in the
    local fixture, append them, and return the list of newly added entries.

    Raises PokelanceAPIError if the external API can't be reached or
    returns something unusable. Callers should catch this and show an
    admin-facing error rather than letting it bubble up as a 500.
    """
    existing = _load_fixture()
    existing_by_number = {p["pokedex_number"]: p for p in existing}
    known_numbers = set(existing_by_number)
    highest_known = max(known_numbers, default=0)

    type_matchup_cache = {}
    new_entries = []
    updated_entries = []
    next_number = highest_known + 1
    attempts = 0
    max_attempts = count * 3  # room for skipped/duplicate numbers without looping forever

    while len(new_entries) < count and attempts < max_attempts:
        attempts += 1
        if next_number in known_numbers:
            next_number += 1
            continue

        new_entries.append(_fetch_and_build_entry(next_number, type_matchup_cache))
        known_numbers.add(next_number)
        next_number += 1

    # --- Pass 2: patch existing Pokémon whose data has drifted ---
    if update_existing:
        for pokedex_number, existing_entry in existing_by_number.items():
            fresh_entry = _fetch_and_build_entry(pokedex_number, type_matchup_cache)
            diff = _diff_fields(existing_entry, fresh_entry)
            if diff:
                updated_entries.append({**existing_entry, **diff})

    if new_entries or updated_entries:
        updated_by_number = {e["pokedex_number"]: e for e in updated_entries}
        merged_fixture = [
            updated_by_number.get(entry["pokedex_number"], entry)
            for entry in existing
        ]
        merged_fixture.extend(new_entries)
        _save_fixture(merged_fixture)

    return {"added": new_entries, "updated": updated_entries}