
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, F
from django.http import Http404
from django.shortcuts import redirect, render
from pokemon.models import GENERATION_REGIONS, Ability, Item, Move, Pokemon, PokemonMove
from pokemon.services.data import get_move_info, get_pokemon_by_name, pokemon_to_dict
from pokemon.services.types import TYPES, defense_cells, effectiveness, type_matchups
from pokemon.services.pokelance_client import sync_pokemon_data, PokelanceAPIError
from pokemon.services.versions import (
    GENERATION_DEX_RANGES,
    GENERATION_GAMES,
    GROWTH_RATE_EXP_100,
    HM_NAMES,
    ROMAN,
    build_location_generations,
    build_move_generations,
)


TYPE_DEFENSE_ORDER = [
    ("Normal", "NOR"), ("Fire", "FIR"), ("Water", "WAT"), ("Electric", "ELE"), ("Grass", "GRA"),
    ("Ice", "ICE"), ("Fighting", "FIG"), ("Poison", "POI"), ("Ground", "GRO"),
    ("Flying", "FLY"), ("Psychic", "PSY"), ("Bug", "BUG"), ("Rock", "ROC"), ("Ghost", "GHO"),
    ("Dragon", "DRA"), ("Dark", "DAR"), ("Steel", "STE"), ("Fairy", "FAI"),
]

def home(request):
    pokemon_count = Pokemon.objects.count()

    if pokemon_count:
        random_pokemon = Pokemon.objects.order_by("?")
        hero = pokemon_to_dict(random_pokemon.first())
        hero["top_stats"] = sorted(
            hero["base_stats"].items(), key=lambda stat: stat[1], reverse=True
        )[:2]
        featured_pokemon = [
            pokemon_to_dict(p) for p in random_pokemon[:settings.FEATURED_POKEMON_COUNT]
        ]
        explore_pokemon = random_pokemon.values_list("name", flat=True).first()
    else:
        hero = None
        featured_pokemon = []
        explore_pokemon = ""

    context = {
        "pokemon_count": pokemon_count,
        "move_count": PokemonMove.objects.values("name").distinct().count(),
        "ability_count": len({
            ability["name"]
            for abilities in Pokemon.objects.values_list("abilities", flat=True)
            for ability in abilities
        }),
        "hero": hero,
        "featured_pokemon": featured_pokemon,
        "explore_pokemon": explore_pokemon,
    }
    return render(request, "home.html", context)

def pokemon_detail(request, name):
    if not name.strip():
        messages.error(request, "Pokémon name required")
        response = redirect("home")
        response.status_code = 400
        return response
    
    current = get_pokemon_by_name(name)
    if current is None:
        raise Http404(f"No Pokémon found match '{name}'")

    previous = (
        Pokemon.objects.filter(pokedex_number__lt=current.pokedex_number)
        .order_by("-pokedex_number").first()
    )
    next = Pokemon.objects.filter(pokedex_number__gt=current.pokedex_number).first()

    by_name = {
        p.name.lower(): p
        for p in Pokemon.objects.filter(name__in=current.evolution_chain)
    }
    evolution_chain = [
        pokemon_to_dict(by_name[evo_name.lower()])
        for evo_name in current.evolution_chain
        if evo_name.lower() in by_name
    ]

    pokemon = pokemon_to_dict(current, include_related=True)
    learnt_hm, learnt_tm = group_hm_tm_moves(pokemon["moves"])
    type_defenses = defense_cells(pokemon["types"])

    return render(request, 'pokemon_detail.html', {
        "pokemon": pokemon,
        "next": pokemon_to_dict(next) if next else None,
        "previous": pokemon_to_dict(previous) if previous else None,
        "evolution_chain": evolution_chain,
        "type_defense_order": TYPE_DEFENSE_ORDER,
        "type_defenses": type_defenses,
        "stat_ranges": calculate_stat_range(pokemon["base_stats"]),
        "learnt_hm": learnt_hm,
        "learnt_tm": learnt_tm,
        "locations": pokemon["locations"],
        "move_generations": build_move_generations(
            pokemon["moves"], get_move_info(m["name"] for m in pokemon["moves"])
        ),
        "location_generations": build_location_generations(pokemon["locations"]),
        "growth_rate_label": pokemon["growth_rate"].replace("-", " ").title(),
        "exp_to_100": GROWTH_RATE_EXP_100.get(pokemon["growth_rate"]),
        })

def group_hm_tm_moves(moves):
    """
    Split moves learned via TM/HM ('machine') from everything else.
    PokéAPI doesn't distinguish HM from TM in move_learn_method — both are
    "machine" — so if HM vs. TM needs to be split further later, that'll
    need its own lookup, not a name-based guess.
    """
    
    machine_moves = [m for m in moves if m["method"] == "machine"]
    learnt_hm = [m for m in machine_moves if m["name"] in HM_NAMES]
    learnt_tm = [m for m in machine_moves if m["name"] not in HM_NAMES]
    
    return learnt_hm, learnt_tm

def calculate_stat_range(base_stats):
    """
    Level 100 min/max for each stat, using the standard formula:
    - Min: IV 0, EV 0, hindering nature (×0.9, HP unaffected)
    - Max: IV 31, EV 252, beneficial nature (×1.1, HP unaffected)
    """
    level = 100
    ranges = {}
    for stat_name, base in base_stats.items():
        if stat_name == "HP":
            min_val = ((2 * base) * level) // 100 + level + 10
            max_val = ((2 * base + 31 + 63) * level) // 100 + level + 10
        else:
            min_val = int((((2 * base) * level) // 100 + 5) * 0.9)
            max_val = int((((2 * base + 31 + 63) * level) // 100 + 5) * 1.1)
        ranges[stat_name] = {"min": min_val, "max": max_val}
    return ranges

def search(request):
    pokemon_name = request.GET.get("search", "").strip()

    if not pokemon_name: 
            messages.error(request, "Pokémon name required")
            return redirect("home")

    pokemon = get_pokemon_by_name(pokemon_name)
    if pokemon:
        return redirect("pokemon_detail", name=pokemon.name)

    messages.error(request, f"No Pokémon found matching {pokemon_name}")
    return redirect("home")
    
def types(request):
    """All 18 types with Pokémon / move counts, plus the full effectiveness chart."""
    pokemon_counts = {}
    for type_list in Pokemon.objects.values_list("types", flat=True):
        for type_name in type_list:
            pokemon_counts[type_name.lower()] = pokemon_counts.get(type_name.lower(), 0) + 1
    move_counts = {
        row["type"].lower(): row["n"] for row in Move.objects.values("type").annotate(n=Count("id"))
    }

    tiles = [
        {
            "slug": slug, "name": slug.title(),
            "pokemon_count": pokemon_counts.get(slug, 0),
            "move_count": move_counts.get(slug, 0),
        }
        for slug in TYPES
    ]
    labels = {2: "2", 0.5: "\u00bd", 0: "0", 1: ""}
    chart = [
        {
            "slug": attacker, "name": attacker.title(),
            "cells": [
                {
                    "slug": defender, "multiplier": effectiveness(attacker, defender),
                    "label": labels[effectiveness(attacker, defender)],
                }
                for defender in TYPES
            ],
        }
        for attacker in TYPES
    ]
    return render(request, "types.html", {
        "type_tiles": tiles, "chart": chart, "defenders": [{"slug": t, "abbr": t[:3].upper()} for t in TYPES],
    })


def type_detail(request, name):
    """One type: what it hits / is hit by, the Pokémon with that type, and how many moves it has."""
    slug = name.strip().lower()
    if slug not in TYPES:
        raise Http404(f"No type '{name}'")

    pokemon = [
        row for row in Pokemon.objects.values("pokedex_number", "name", "image", "types")
        if slug in (t.lower() for t in row["types"])
    ]
    return render(request, "type_detail.html", {
        "type_slug": slug,
        "type_name": slug.title(),
        "matchups": type_matchups(slug),
        "pokemon": pokemon,
        "move_count": Move.objects.filter(type=slug.title()).count(),
    })

def pokedex(request):
    pokemon_data = Pokemon.objects.all()

    return render(request, "pokedex.html", {"pokemon_data": pokemon_data})

def _region_info(generation):
    low, high = GENERATION_DEX_RANGES[generation]
    return {
        "name": GENERATION_REGIONS[generation],
        "slug": GENERATION_REGIONS[generation].lower(),
        "generation": generation,
        "roman": ROMAN[generation],
        "games": GENERATION_GAMES[generation],
        "dex_range": f"#{low}\u2013#{high}",
    }


def region(request):
    """The nine regions, each with how many of its Pokémon are stored."""
    counts = dict(Pokemon.objects.values_list("region").annotate(n=Count("id")))
    tiles = [
        {**_region_info(generation), "pokemon_count": counts.get(name, 0)}
        for generation, name in GENERATION_REGIONS.items()
    ]
    return render(request, "regions.html", {"region_tiles": tiles})


def region_detail(request, name):
    """One region: its games, dex range and every stored Pokémon from it."""
    generation = next(
        (g for g, region_name in GENERATION_REGIONS.items() if region_name.lower() == name.strip().lower()),
        None,
    )
    if generation is None:
        raise Http404(f"No region '{name}'")

    info = _region_info(generation)
    pokemon = list(
        Pokemon.objects.filter(region=info["name"]).values("pokedex_number", "name", "image", "types")
    )
    neighbours = [
        _region_info(g) for g in (generation - 1, generation + 1) if g in GENERATION_REGIONS
    ]
    return render(request, "region_detail.html", {
        "region": info, "pokemon": pokemon, "neighbours": neighbours,
        "previous_region": next((n for n in neighbours if n["generation"] < generation), None),
        "next_region": next((n for n in neighbours if n["generation"] > generation), None),
    })

def _slugify(name):
    return name.lower().replace(" ", "-")


def _ability_holders():
    """{ability name: [(pokemon row, is_hidden), ...]} over every stored Pokémon, in dex order."""
    holders = {}
    for row in Pokemon.objects.values("pokedex_number", "name", "image", "types", "abilities"):
        for ability in row["abilities"]:
            holders.setdefault(ability["name"], []).append((row, ability["hidden"]))
    return holders


ABILITY_SORT_FIELDS = {"name": "Name", "pokemon": "Pok\u00e9mon"}


def abilities(request):
    """Every ability with its effect text and how many stored Pokémon can have it."""
    holders = _ability_holders()
    info = {a.name: a for a in Ability.objects.all()}

    rows = [
        {
            "name": name,
            "slug": _slugify(name),
            "pokemon_count": len(holders.get(name, [])),
            "effect": info[name].effect if name in info else "",
            "generation": info[name].generation if name in info else None,
        }
        for name in sorted(set(holders) | set(info))
    ]
    stored_count = len(rows)

    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "")
    direction = "desc" if request.GET.get("dir") == "desc" else "asc"
    if q:
        rows = [r for r in rows if q.lower() in r["name"].lower()]
    if sort == "pokemon":
        rows.sort(key=lambda r: r["pokemon_count"], reverse=direction == "desc")  # stable: ties stay by name
    else:
        sort, direction = "", "asc"

    filters = {"q": q} if q else {}
    columns = [
        {
            "key": key, "label": label,
            "query": urlencode({**filters, "sort": key, "dir": "desc" if sort == key and direction == "asc" else "asc"}),
            "aria_sort": ("ascending" if direction == "asc" else "descending") if sort == key else "none",
        }
        for key, label in ABILITY_SORT_FIELDS.items()
    ]
    page_obj = Paginator(rows, 50).get_page(request.GET.get("page"))
    return render(request, "abilities.html", {
        "page_obj": page_obj,
        "total": len(rows),
        "stored_count": stored_count,
        "q": q,
        "columns": columns,
        "selected_sort": sort,
        "query": urlencode({**filters, **({"sort": sort, "dir": direction} if sort else {})}),
        "filtering": bool(q),
        "effects_missing": bool(stored_count) and not info,
    })


def ability_detail(request, slug):
    """One ability: its effect and the Pokémon that have it, regular and hidden."""
    name = slug.strip().replace("-", " ").title()
    holders = _ability_holders().get(name, [])
    ability = Ability.objects.filter(name=name).first()
    if not holders and ability is None:
        raise Http404(f"No ability '{slug}'")

    return render(request, "ability_detail.html", {
        "ability": {
            "name": name,
            "effect": ability.effect if ability else "",
            "generation": ability.generation if ability else None,
        },
        "regular_pokemon": [row for row, hidden in holders if not hidden],
        "hidden_pokemon": [row for row, hidden in holders if hidden],
    })

def pokemon_moves_fragment(request, name, version):
    """
    HTML fragment with one game's move tables for a Pokémon. The detail page only
    renders the visible game up front and fetches the others when their tab is opened,
    which keeps the page small (a Pokémon has ~25 games and up to ~2,000 move rows).
    """
    pokemon = get_pokemon_by_name(name)
    if pokemon is None:
        raise Http404(f"No Pokémon found match '{name}'")

    rows = list(pokemon.moves.filter(version=version).values("name", "version", "level_learnt", "method"))
    if not rows:
        raise Http404(f"{pokemon.name} has no moves for '{version}'")

    generations = build_move_generations(rows, get_move_info(r["name"] for r in rows))
    return render(request, "partials/moves_version.html", {"version": generations[0]["versions"][0]})


MOVES_PER_PAGE = 50
MOVE_SORT_FIELDS = {
    "name": "Name", "type": "Type", "power": "Pow.", "accuracy": "Acc.", "pp": "PP",
}


def moves(request):
    """All moves with stats, filterable by name / type / category and sortable by column."""
    stored = Move.objects.all()
    results = stored

    q = request.GET.get("q", "").strip()
    type_name = request.GET.get("type", "")
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "")
    direction = "desc" if request.GET.get("dir") == "desc" else "asc"

    if q:
        results = results.filter(name__icontains=q)
    if type_name in {name for name, _ in TYPE_DEFENSE_ORDER}:
        results = results.filter(type=type_name)
    else:
        type_name = ""
    if category in dict(Move.DAMAGE_CLASSES):
        results = results.filter(damage_class=category)
    else:
        category = ""
    if sort not in MOVE_SORT_FIELDS:
        sort = ""

    if sort:
        field = F(sort)
        order = field.desc(nulls_last=True) if direction == "desc" else field.asc(nulls_last=True)
        results = results.order_by(order, "name")
    else:
        direction = "asc"
        results = results.order_by("name")

    filters = {k: v for k, v in (("q", q), ("type", type_name), ("category", category)) if v}

    def columns():
        for key, label in MOVE_SORT_FIELDS.items():
            is_current = sort == key
            next_dir = "desc" if is_current and direction == "asc" else "asc"
            yield {
                "label": label,
                "key": key,
                "query": urlencode({**filters, "sort": key, "dir": next_dir}),
                "aria_sort": (direction == "asc" and "ascending" or "descending") if is_current else "none",
            }

    page_obj = Paginator(results, MOVES_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "moves.html", {
        "page_obj": page_obj,
        "total": page_obj.paginator.count,
        "stored_count": stored.count(),
        "q": q,
        "selected_type": type_name,
        "selected_category": category,
        "type_names": [name for name, _ in TYPE_DEFENSE_ORDER],
        "categories": Move.DAMAGE_CLASSES,
        "columns": list(columns()),
        # Filters + sort, without the page number, for pagination links.
        "query": urlencode({**filters, **({"sort": sort, "dir": direction} if sort else {})}),
        "filtering": bool(filters),
    })


COMPETITIVE_STATS = [
    ("total", "Total", None),
    ("hp", "HP", "HP"),
    ("attack", "Attack", "Attack"),
    ("defense", "Defense", "Defense"),
    ("special-attack", "Sp. Atk", "Special Attack"),
    ("special-defense", "Sp. Def", "Special Defense"),
    ("speed", "Speed", "Speed"),
]


def competitive(request):
    """Rank every stored Pokémon by base stat total, or by any single base stat."""
    stat_slug, stat_label, stat_key = next(
        (s for s in COMPETITIVE_STATS if s[0] == request.GET.get("stat")), COMPETITIVE_STATS[0]
    )
    type_name = request.GET.get("type", "")
    if type_name not in {name for name, _ in TYPE_DEFENSE_ORDER}:
        type_name = ""

    rows = [
        {
            "pokedex_number": p["pokedex_number"], "name": p["name"], "image": p["image"],
            "types": p["types"], "stats": p["base_stats"],
            "total": p["stat_total"],
            "value": p["stat_total"] if stat_key is None else p["base_stats"].get(stat_key, 0),
        }
        for p in Pokemon.objects.values("pokedex_number", "name", "image", "types", "base_stats", "stat_total")
    ]
    stored_count = len(rows)
    if type_name:
        rows = [r for r in rows if type_name in r["types"]]

    rows.sort(key=lambda r: (-r["value"], r["pokedex_number"]))
    top = rows[0]["value"] if rows else 0
    for index, row in enumerate(rows):
        # Competition ranking: ties share a rank and the next rank skips (1, 2, 2, 4).
        row["rank"] = rows[index - 1]["rank"] if index and row["value"] == rows[index - 1]["value"] else index + 1
        row["bar"] = round(row["value"] / top * 100) if top else 0

    filters = {"type": type_name} if type_name else {}
    stat_links = [
        {"slug": slug, "label": label, "active": slug == stat_slug, "query": urlencode({"stat": slug, **filters})}
        for slug, label, _ in COMPETITIVE_STATS
    ]
    page_obj = Paginator(rows, 50).get_page(request.GET.get("page"))
    return render(request, "competitive.html", {
        "page_obj": page_obj,
        "total": len(rows),
        "stored_count": stored_count,
        "stat": {"slug": stat_slug, "label": stat_label},
        "stat_links": stat_links,
        "selected_type": type_name,
        "type_names": [name for name, _ in TYPE_DEFENSE_ORDER],
        "stat_columns": [(label, key) for slug, label, key in COMPETITIVE_STATS if key],
        "query": urlencode({"stat": stat_slug, **filters}),
    })


ITEMS_PER_PAGE = 48


def items(request):
    """Browse bag items: search by name, filter by category."""
    stored = Item.objects.all()
    results = stored

    q = request.GET.get("q", "").strip()
    categories = list(stored.order_by("category").values_list("category", flat=True).distinct())
    category = request.GET.get("category", "")
    if category not in categories:
        category = ""

    if q:
        results = results.filter(name__icontains=q)
    if category:
        results = results.filter(category=category)

    filters = {k: v for k, v in (("q", q), ("category", category)) if v}
    page_obj = Paginator(results, ITEMS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "items.html", {
        "page_obj": page_obj,
        "total": page_obj.paginator.count,
        "stored_count": stored.count(),
        "q": q,
        "selected_category": category,
        "category_choices": [(c, c.replace("-", " ").title()) for c in categories if c],
        "query": urlencode(filters),
        "filtering": bool(filters),
    })


def _is_staff(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(_is_staff, login_url="home", redirect_field_name=None)
def admin_sync_pokemon(request):
    """
    Staff-only page that triggers a sync against the Pokelance client.

    GET just shows the sync page. POST triggers the sync and re-renders
    the same page with either the lists of newly added / updated Pokémon
    or a sensible error message if the external API call fails — a
    failure here should never surface as a 500.

    sync_pokemon_data() returns {"added": [...], "updated": [...]};
    both lists are unwrapped into separate context keys so the template
    can render each independently.
    """
    context = {}

    if request.method == "POST":
        try:
            result = sync_pokemon_data()
            context["sync_success"] = True
            context["new_pokemon"] = result["added"]
            context["updated_pokemon"] = result["updated"]
        except PokelanceAPIError as e:
            context["sync_error"] = str(e)

    return render(request, "admin_sync.html", context)