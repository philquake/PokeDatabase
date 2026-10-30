"""
pokelance_client.py

Client for syncing new Pokémon from the public PokéAPI (https://pokeapi.co)
into PokeDatabase's database (see pokemon.models / services.data).

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

import requests

from pokemon.models import Move, Pokemon, PokemonMove
from pokemon.services.data import move_to_dict, pokemon_to_dict, save_move_entry, save_pokemon_entry


POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/pokemon"
POKEAPI_MOVE_URL = "https://pokeapi.co/api/v2/move"
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
    "generation-ix": 9,
}

IDENTITY_FIELDS = {"pokedex_number"}

class PokelanceAPIError(Exception):
    """Raised when the Pokelance client can't complete a sync."""


def _existing_numbers():
    return set(Pokemon.objects.values_list("pokedex_number", flat=True))


def _load_entry(pokedex_number):
    """Fixture-shaped dict (incl. moves/locations) for a stored Pokémon."""
    pokemon = Pokemon.objects.get(pokedex_number=pokedex_number)
    return pokemon_to_dict(pokemon, include_related=True)


def _save_entry(entry):
    save_pokemon_entry(entry)


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


def _fetch_moves(raw_pokemon):
    """ Flatten PokéAPI's per-move `version_group_details` into one row per
    (move, version group, method, level) combination:
        {"name": "Thunder Punch", "version": "red-blue", "level": 0, "method": "egg"} """
        
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


def _fetch_evolution_chain(species):
    chain_url = species["evolution_chain"]["url"]
    chain_data = _get(chain_url, f"evolution chain for {species['name']}")
    return _walk_evolution_chain(chain_data["chain"])

def _fetch_locations(pokedex_number):
    """
    Fetch wild encounter locations for a Pokémon from PokéAPI's
    /pokemon/{id}/encounters endpoint and flatten it into a list of
    per-encounter dicts, one per (location area, version, method) combo:
 
        {
            "location": "Route 1",
            "version": "red-blue",
            "method": "Walk",
            "chance": 45,
            "min_level": 2,
            "max_level": 5,
        }
 
    This does the flattening once here rather than
    pushing that logic into the template. A Pokémon with no wild encounters
    (starters, legendaries, evolutions-only, etc.) simply returns [].
    """
    raw = _get(
        f"{POKEAPI_BASE_URL}/{pokedex_number}/encounters",
        f"encounter locations for #{pokedex_number}",
    )
 
    locations = []
    for entry in raw:
        location_name = (
            entry["location_area"]["name"].replace("-", " ").title()
        )
        for version_detail in entry.get("version_details", []):
            version = version_detail["version"]["name"]
            for encounter in version_detail.get("encounter_details", []):
                locations.append({
                    "location": location_name,
                    "version": version,
                    "method": encounter["method"]["name"].replace("-", " ").title(),
                    "chance": encounter["chance"],
                    "min_level": encounter["min_level"],
                    "max_level": encounter["max_level"],
                })
 
    return locations

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
    locations = _fetch_locations(pokedex_number)
    return _to_fixture_entry(raw, species, evolution_chain, type_matchups, locations)

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
    
def _to_fixture_entry(raw, species, evolution_chain, type_matchups, locations):
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
            "ev_yield": {
                STAT_NAME_LOOKUP[stat["stat"]["name"]]: stat["effort"]
                for stat in raw["stats"]
                if stat["stat"]["name"] in STAT_NAME_LOOKUP and stat.get("effort")
            },
            "growth_rate": species.get("growth_rate", {}).get("name", ""),
            "held_items": sorted(
                {
                    item["item"]["name"].replace("-", " ").title()
                    for item in raw.get("held_items", [])
                }
            ),
            "moves": _fetch_moves(raw),
            "locations": locations,
        }
    except (KeyError, TypeError) as exc:
        raise PokelanceAPIError(
            f"Pokelance API returned an unexpected payload shape: {exc}"
        ) from exc


def sync_pokemon_data(count=5, update_existing=True):
    """
    Fetch up to `count` new Pokémon from PokéAPI that aren't already in the
    database and store them; then, if `update_existing`, re-fetch every stored
    Pokémon and patch any fields that are missing or have drifted.

    Each Pokémon is saved as soon as it's fetched, so if the sync fails part
    way through, everything fetched before the failure is kept.

    Returns {"added": [...], "updated": [...]} of fixture-shaped dicts.

    Raises PokelanceAPIError if the external API can't be reached or
    returns something unusable. Callers should catch this and show an
    admin-facing error rather than letting it bubble up as a 500.
    """
    known_numbers = _existing_numbers()
    existing_numbers = sorted(known_numbers)
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

        entry = _fetch_and_build_entry(next_number, type_matchup_cache)
        _save_entry(entry)
        new_entries.append(entry)
        known_numbers.add(next_number)
        next_number += 1

    # --- Pass 2: patch existing Pokémon whose data has drifted ---
    if update_existing:
        for pokedex_number in existing_numbers:
            existing_entry = _load_entry(pokedex_number)
            fresh_entry = _fetch_and_build_entry(pokedex_number, type_matchup_cache)
            diff = _diff_fields(existing_entry, fresh_entry)
            if diff:
                _save_entry({"pokedex_number": pokedex_number, **diff})
                updated_entries.append({**existing_entry, **diff})

    return {"added": new_entries, "updated": updated_entries}



# --- Moves -----------------------------------------------------------------

def _move_display_name(slug):
    """Same transform _fetch_moves uses, so Move names line up with PokemonMove names."""
    return slug.replace("-", " ").title()


def _existing_moves():
    return {m.name: move_to_dict(m) for m in Move.objects.all()}


def _known_move_names():
    """Names of moves that at least one stored Pokémon learns."""
    return set(PokemonMove.objects.values_list("name", flat=True).distinct())


def _save_move(entry):
    save_move_entry(entry)


def _to_move_entry(raw):
    """Flatten a PokéAPI move into the stats dict stored on Move."""
    generation = GENERATIONS.get(raw["generation"]["name"])
    if generation is None:
        raise PokelanceAPIError(f"Unknown generation '{raw['generation']['name']}' for move {raw['name']}")

    effect = next(
        (e.get("short_effect", "") for e in raw.get("effect_entries", [])
         if e["language"]["name"] == "en"),
        "",
    )
    effect = effect.replace("$effect_chance", str(raw.get("effect_chance")))

    return {
        "name": _move_display_name(raw["name"]),
        "type": raw["type"]["name"].capitalize(),
        "damage_class": raw["damage_class"]["name"],
        "power": raw.get("power"),
        "accuracy": raw.get("accuracy"),
        "pp": raw.get("pp"),
        "generation": generation,
        "effect": effect,
    }


def sync_move_data(only_known=False, refresh=False):
    """
    Fetch move stats (type, damage class, power, accuracy, PP, effect text) from
    PokéAPI and store them as Move rows.

    only_known: just the moves some stored Pokémon learns (hundreds, not ~900).
    refresh:    re-fetch moves already stored and patch the ones that changed;
                otherwise stored moves are skipped, so a sync can be resumed.

    Each move is saved as soon as it's fetched, so a failure keeps progress.
    Returns {"added": [...], "updated": [...]} of move dicts. Raises
    PokelanceAPIError if PokéAPI can't be reached or returns something unusable.
    """
    listing = _get(f"{POKEAPI_MOVE_URL}?limit=2000", "move list")["results"]
    existing = _existing_moves()
    known = _known_move_names() if only_known else None

    added, updated = [], []
    for item in listing:
        name = _move_display_name(item["name"])
        if known is not None and name not in known:
            continue
        if name in existing and not refresh:
            continue

        entry = _to_move_entry(_get(item["url"], f"move {name}"))
        if name not in existing:
            _save_move(entry)
            added.append(entry)
        elif entry != existing[name]:
            _save_move(entry)
            updated.append(entry)

    return {"added": added, "updated": updated}
