
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from pokemon.models import GENERATION_REGIONS, Ability, Item, Move, Pokemon, PokemonForm, PokemonMove
from pokemon.services.data import MOVE_FIELDS, form_to_dict, get_move_info, get_pokemon_by_name, pokemon_to_dict
from pokemon.services.forms import FORM_KINDS
from pokemon.services.types import TYPES, defense_cells, effectiveness, type_matchups
from pokemon.services.pokelance_client import sync_pokemon_data, PokelanceAPIError
from pokemon.services.stats import (
    SPEED_LEVELS,
    SPEED_SPREADS,
    calculate_speed_tiers,
    calculate_stat_range,
)
from pokemon.services.team_builder import analyze_team
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

FORM_OVERRIDES = (
    "image", "types", "base_stats", "stat_total", "abilities", "height_m", "weight_kg",
    "base_experience", "ev_yield", "held_items",
)


def _select_form(request, forms):
    """The form named by ?form=<slug> (case-insensitive), None for the base Pokémon; unknown slug -> 404."""
    slug = request.GET.get("form", "").strip().lower()
    if not slug:
        return None
    for form in forms:
        if form.slug == slug:
            return form
    raise Http404(f"No form '{slug}'")


def _apply_form_overrides(pokemon, form):
    """Return a base Pokémon dict with the fields that vary by form replaced."""
    pokemon = pokemon.copy()
    form_data = form_to_dict(form)
    pokemon.update({key: form_data[key] for key in FORM_OVERRIDES})
    return pokemon


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

    pokemon = pokemon_to_dict(current, include_related=True, form_moves=False)
    forms = list(current.forms.all())
    active_form = _select_form(request, forms)
    display_name = current.name
    moves_from_base = False
    form_options = []
    if forms:
        form_options = [{"slug": "", "label": current.name, "image": current.image, "kind": "base",
                         "active": active_form is None}] + [
            {"slug": f.slug, "label": f.label, "image": f.image, "kind": f.kind, "active": f is active_form}
            for f in forms
        ]
    if active_form is not None:
        # Species-level data (category, gender, egg groups, evolution ...) stays the base Pokémon's;
        # what differs per form is overlaid. PokéAPI doesn't give encounters for forms, so none are shown.
        pokemon = _apply_form_overrides(pokemon, active_form)
        pokemon["locations"] = []
        display_name = active_form.label
        own_moves = list(active_form.moves.values(*MOVE_FIELDS))
        if own_moves:
            pokemon["moves"] = own_moves
        else:
            moves_from_base = True    # Megas and the like have no move list of their own
    learnt_hm, learnt_tm = group_hm_tm_moves(pokemon["moves"])
    type_defenses = defense_cells(pokemon["types"])

    return render(request, 'pokemon_detail.html', {
        "pokemon": pokemon,
        "next": pokemon_to_dict(next) if next else None,
        "previous": pokemon_to_dict(previous) if previous else None,
        "evolution_chain": evolution_chain,
        "type_defense_order": TYPE_DEFENSE_ORDER,
        "type_defenses": type_defenses,
        "display_name": display_name,
        "active_form": {"slug": active_form.slug, "label": active_form.label, "kind": active_form.kind}
                       if active_form else None,
        "form_options": form_options,
        "moves_from_base": moves_from_base,
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
    form_counts = {}
    for type_list in PokemonForm.objects.values_list("types", flat=True):
        for type_name in type_list:
            form_counts[type_name.lower()] = form_counts.get(type_name.lower(), 0) + 1
    move_counts = {
        row["type"].lower(): row["n"] for row in Move.objects.values("type").annotate(n=Count("id"))
    }

    tiles = [
        {
            "slug": slug, "name": slug.title(),
            "pokemon_count": pokemon_counts.get(slug, 0),
            "form_count": form_counts.get(slug, 0),
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
    forms = []
    for form in PokemonForm.objects.select_related("pokemon").order_by(
        "pokemon__pokedex_number", "pokeapi_id"
    ):
        base = pokemon_to_dict(form.pokemon)
        data = _apply_form_overrides(base, form)
        if slug in (type_name.lower() for type_name in data["types"]):
            forms.append({
                "name": data["name"],
                "pokedex_number": data["pokedex_number"],
                "slug": form.slug,
                "label": form.label,
                "image": data["image"],
                "types": data["types"],
            })
    return render(request, "type_detail.html", {
        "type_slug": slug,
        "type_name": slug.title(),
        "matchups": type_matchups(slug),
        "pokemon": pokemon,
        "forms": forms,
        "move_count": Move.objects.filter(type=slug.title()).count(),
    })

def pokedex(request):
    stored = list(Pokemon.objects.all())
    stored_count = len(stored)
    regions = list(GENERATION_REGIONS.values())
    selected_region = request.GET.get("region", "")
    if selected_region not in regions:
        selected_region = ""
    selected_type = request.GET.get("type", "").strip().lower()
    if selected_type not in TYPES:
        selected_type = ""

    pokemon_data = [
        pokemon for pokemon in stored
        if (not selected_region or pokemon.region == selected_region)
        and (not selected_type or selected_type in (t.lower() for t in pokemon.types))
    ]
    return render(request, "pokedex.html", {
        "pokemon_data": pokemon_data,
        "pokemon_count": len(pokemon_data),
        "stored_count": stored_count,
        "form_count": PokemonForm.objects.count(),
        "regions": regions,
        "selected_region": selected_region,
        "types": [type_name.title() for type_name in TYPES],
        "selected_type": selected_type,
        "filtering": bool(selected_region or selected_type),
    })


FORMS_PER_PAGE = 48


def forms(request):
    """Every alternate form (regional variants, Megas, Gigantamax ...), filterable by kind and name."""
    stored = PokemonForm.objects.select_related("pokemon")
    kind_counts = {row["kind"]: row["n"] for row in stored.values("kind").annotate(n=Count("id"))}

    kind = request.GET.get("kind", "")
    if kind not in dict(FORM_KINDS):
        kind = ""
    q = request.GET.get("q", "").strip()

    results = stored
    if kind:
        results = results.filter(kind=kind)
    if q:
        results = results.filter(Q(label__icontains=q) | Q(pokemon__name__icontains=q))
    results = results.order_by("pokemon__pokedex_number", "pokeapi_id")

    filters = {k: v for k, v in (("kind", kind), ("q", q)) if v}
    kind_tabs = [
        {
            "slug": slug, "label": label, "active": slug == kind,
            "count": sum(kind_counts.values()) if not slug else kind_counts.get(slug, 0),
            "query": urlencode({**({"q": q} if q else {}), **({"kind": slug} if slug else {})}),
        }
        for slug, label in [("", "All")] + FORM_KINDS
    ]
    page_obj = Paginator(results, FORMS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "forms.html", {
        "page_obj": page_obj,
        "total": page_obj.paginator.count,
        "stored_count": sum(kind_counts.values()),
        "kind_tabs": kind_tabs,
        "kind": kind,
        "q": q,
        "query": urlencode(filters),
        "filtering": bool(filters),
    })

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

    moves = pokemon.moves
    form = _select_form(request, list(pokemon.forms.all()))
    if form is not None and form.moves.exists():
        moves = form.moves          # a form with its own move list; Megas and the like fall back to the base's
    rows = list(moves.filter(version=version).values("name", "version", "level_learnt", "method"))
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


COMPARISON_STATS = (
    ("HP", "HP"),
    ("Attack", "Attack"),
    ("Defense", "Defense"),
    ("Sp. Atk", "Special Attack"),
    ("Sp. Def", "Special Defense"),
    ("Speed", "Speed"),
)


def comparison(request):
    """Compare 2–4 base Pokémon using repeatable ?p=<name> query parameters."""
    pokemon_options = list(Pokemon.objects.order_by("pokedex_number"))
    pokemon_by_name = {pokemon.name.casefold(): pokemon for pokemon in pokemon_options}
    submitted = "p" in request.GET
    selected_values = [value.strip() for value in request.GET.getlist("p")]
    selected_names = [value for value in selected_values if value]
    errors = []
    slot_errors = [[] for _ in range(4)]
    comparison_pokemon = []

    def add_error(message, slot_index):
        errors.append({
            "message": message,
            "field_id": f"compare-pokemon-{slot_index + 1}",
        })

    if submitted:
        if len(selected_names) < 2:
            missing_slots = max(0, 2 - len(selected_names))
            for index in range(4):
                if missing_slots and (
                    index >= len(selected_values) or not selected_values[index]
                ):
                    slot_errors[index].append("Select a Pokémon.")
                    missing_slots -= 1
            add_error("Choose at least two Pokémon.", next(
                (index for index, field_errors in enumerate(slot_errors) if field_errors),
                0,
            ))
        if len(selected_names) > 4:
            slot_errors[3].append("Remove a selection; no more than four are allowed.")
            add_error("Choose no more than four Pokémon.", 3)

        seen_names = set()
        duplicate_index = None
        for index, name in enumerate(selected_values[:4]):
            if name and name.casefold() in seen_names:
                slot_errors[index].append("Choose a different Pokémon.")
                duplicate_index = index
            elif name:
                seen_names.add(name.casefold())
        if duplicate_index is not None:
            add_error("Each Pokémon can only be selected once.", duplicate_index)

        unknown_names = []
        unknown_keys = set()
        unknown_index = None
        for index, name in enumerate(selected_values):
            if not name:
                continue
            if name.casefold() not in pokemon_by_name and name.casefold() not in unknown_keys:
                unknown_names.append(name)
                unknown_keys.add(name.casefold())
                unknown_index = index if index < 4 else 3
                slot_errors[unknown_index].append("This Pokémon was not found.")
        if unknown_names:
            add_error(f"Unknown Pokémon: {', '.join(unknown_names)}.", unknown_index)

        if not errors:
            comparison_pokemon = [
                pokemon_by_name[name.casefold()] for name in selected_names
            ]

    comparison_data = []
    shared_moves = []
    partial_moves = []
    share_url = ""
    if comparison_pokemon:
        move_names_by_pokemon = {pokemon.pk: {} for pokemon in comparison_pokemon}
        move_rows = (
            PokemonMove.objects.filter(
                pokemon_id__in=move_names_by_pokemon,
            )
            .order_by()
            .values_list("pokemon_id", "name")
            .distinct()
        )
        move_owners = {}
        for pokemon_id, move_name in move_rows:
            key = move_name.casefold()
            move_names_by_pokemon[pokemon_id].setdefault(key, move_name)

        for pokemon in comparison_pokemon:
            for key, move_name in move_names_by_pokemon[pokemon.pk].items():
                move_owners.setdefault(key, {"name": move_name, "owners": []})[
                    "owners"
                ].append(pokemon.name)

            data = pokemon_to_dict(pokemon)
            data["stat_ranges"] = calculate_stat_range(data["base_stats"])
            data["type_defenses"] = defense_cells(data["types"])
            data["weaknesses"] = [
                cell for cell in data["type_defenses"] if cell["multiplier"] > 1
            ]
            data["moves_known_count"] = len(move_names_by_pokemon[pokemon.pk])
            data["stats"] = []

            for label, key in COMPARISON_STATS:
                value = data["base_stats"].get(key)
                highest = max(
                    (p.base_stats.get(key, 0) for p in comparison_pokemon),
                    default=0,
                )
                stat_range = data["stat_ranges"].get(key, {})
                data["stats"].append({
                    "label": label,
                    "value": value,
                    "minimum": stat_range.get("min"),
                    "maximum": stat_range.get("max"),
                    "bar": round(value / highest * 100)
                    if value is not None and highest
                    else 0,
                })
            comparison_data.append(data)

        overlap = sorted(move_owners.values(), key=lambda move: move["name"].casefold())
        shared_moves = [
            move for move in overlap if len(move["owners"]) == len(comparison_pokemon)
        ]
        partial_moves = [
            move for move in overlap if 2 <= len(move["owners"]) < len(comparison_pokemon)
        ]
        share_url = f"{reverse('comparison')}?{urlencode([('p', p.name) for p in comparison_pokemon])}"

    slots = []
    for index in range(4):
        value = selected_values[index] if index < len(selected_values) else ""
        known = bool(value and value.casefold() in pokemon_by_name)
        slots.append({
            "value": value,
            "unknown": bool(value and not known),
            "errors": slot_errors[index],
            "options": [
                {
                    "name": pokemon.name,
                    "pokedex_number": pokemon.pokedex_number,
                    "image": pokemon.image,
                    "selected": known and pokemon.name.casefold() == value.casefold(),
                }
                for pokemon in pokemon_options
            ],
        })

    return render(request, "comparison.html", {
        "comparison_pokemon": comparison_data,
        "comparison_slots": slots,
        "errors": errors,
        "shared_moves": shared_moves,
        "partial_moves": partial_moves,
        "share_url": share_url,
        "pokemon_count": len(pokemon_options),
    })


def team_builder(request):
    """Build a six-member team with a canonical comma-separated query-string state."""
    pokemon_options = list(Pokemon.objects.order_by("pokedex_number"))
    pokemon_by_name = {pokemon.name.casefold(): pokemon for pokemon in pokemon_options}
    submitted = "p" in request.GET
    raw_values = request.GET.getlist("p")
    selected_values = []
    malformed = False

    for raw_value in raw_values:
        if not raw_value.strip():
            continue
        parts = raw_value.split(",")
        if any(not part.strip() for part in parts):
            malformed = True
        selected_values.extend(part.strip() for part in parts if part.strip())

    errors = []
    if malformed:
        errors.append("Team members cannot be blank.")
    if len(selected_values) > 6:
        errors.append("Choose no more than six Pokémon.")
    if len({name.casefold() for name in selected_values}) != len(selected_values):
        errors.append("Each Pokémon can only be selected once.")

    unknown_names = []
    unknown_keys = set()
    for name in selected_values:
        if name.casefold() not in pokemon_by_name and name.casefold() not in unknown_keys:
            unknown_names.append(name)
            unknown_keys.add(name.casefold())
    if unknown_names:
        errors.append(f"Unknown Pokémon: {', '.join(unknown_names)}.")

    team = []
    if submitted and not errors and selected_values:
        team = [pokemon_by_name[name.casefold()] for name in selected_values]
        if len(raw_values) > 1:
            canonical_url = (
                f"{reverse('team')}?"
                f"{urlencode({'p': ','.join(pokemon.name for pokemon in team)}, safe=',')}"
            )
            return redirect(canonical_url)

    team_data = [pokemon_to_dict(pokemon) for pokemon in team]
    analysis = analyze_team(team) if team else {}
    share_url = ""
    if team:
        share_url = (
            f"{reverse('team')}?"
            f"{urlencode({'p': ','.join(pokemon.name for pokemon in team)}, safe=',')}"
        )

    slots = []
    for index in range(6):
        value = selected_values[index] if index < len(selected_values) else ""
        known = bool(value and value.casefold() in pokemon_by_name)
        slots.append({
            "value": value,
            "unknown": bool(value and not known),
            "options": [
                {
                    "name": pokemon.name,
                    "pokedex_number": pokemon.pokedex_number,
                    "image": pokemon.image,
                    "selected": known and pokemon.name.casefold() == value.casefold(),
                }
                for pokemon in pokemon_options
            ],
        })

    return render(request, "team_builder.html", {
        "team_pokemon": team_data,
        "team_slots": slots,
        "errors": errors,
        "share_url": share_url,
        "pokemon_count": len(pokemon_options),
        **analysis,
    })


def competitive(request):
    """Rank base Pokémon and alternate forms by base stats or calculated Speed tiers."""
    stat_slug, stat_label, stat_key = next(
        (s for s in COMPETITIVE_STATS if s[0] == request.GET.get("stat")), COMPETITIVE_STATS[0]
    )
    type_name = request.GET.get("type", "")
    if type_name not in {name for name, _ in TYPE_DEFENSE_ORDER}:
        type_name = ""
    speed_sort = request.GET.get("sort", "")
    speed_keys = {
        f"{spread_slug}-{level}"
        for level in SPEED_LEVELS
        for spread_slug, _, _, _ in SPEED_SPREADS
    }
    if speed_sort not in speed_keys:
        speed_sort = ""
    speed_direction = request.GET.get("dir", "desc")
    if speed_direction not in {"asc", "desc"}:
        speed_direction = "desc"

    rows = [
        {
            "pokedex_number": p["pokedex_number"], "name": p["name"], "image": p["image"],
            "display_name": p["name"], "is_form": False, "form_slug": "",
            "form_order": 0,
            "types": p["types"], "stats": p["base_stats"],
            "total": p["stat_total"],
            "value": p["stat_total"] if stat_key is None else p["base_stats"].get(stat_key, 0),
            "speed_tiers": calculate_speed_tiers(p["base_stats"].get("Speed", 0)),
        }
        for p in Pokemon.objects.values("pokedex_number", "name", "image", "types", "base_stats", "stat_total")
    ]
    stored_count = len(rows)
    if type_name:
        rows = [r for r in rows if type_name in r["types"]]
    base_count = len(rows)

    for form in PokemonForm.objects.select_related("pokemon").order_by(
        "pokemon__pokedex_number", "pokeapi_id"
    ):
        base = pokemon_to_dict(form.pokemon)
        data = _apply_form_overrides(base, form)
        if type_name and type_name not in data["types"]:
            continue
        value = data["stat_total"] if stat_key is None else data["base_stats"].get(stat_key, 0)
        rows.append({
            "pokedex_number": data["pokedex_number"],
            "name": data["name"],
            "display_name": form.label,
            "image": data["image"],
            "is_form": True,
            "form_slug": form.slug,
            "form_order": form.pokeapi_id,
            "types": data["types"],
            "stats": data["base_stats"],
            "total": data["stat_total"],
            "value": value,
            "speed_tiers": calculate_speed_tiers(data["base_stats"].get("Speed", 0)),
        })
    form_count = len(rows) - base_count

    speed_labels = {
        f"{spread_slug}-{level}": f"{label} Speed (Lv. {level})"
        for level in SPEED_LEVELS
        for spread_slug, label, _, _ in SPEED_SPREADS
    }
    for row in rows:
        if speed_sort:
            row["value"] = row["speed_tiers"][speed_sort]

    direction = 1 if speed_sort and speed_direction == "asc" else -1
    rows.sort(key=lambda r: (
        direction * r["value"], r["pokedex_number"], r["is_form"], r["form_order"],
    ))
    top = max((row["value"] for row in rows), default=0)
    for index, row in enumerate(rows):
        # Competition ranking: ties share a rank and the next rank skips (1, 2, 2, 4).
        row["rank"] = rows[index - 1]["rank"] if index and row["value"] == rows[index - 1]["value"] else index + 1
        row["bar"] = round(row["value"] / top * 100) if top else 0

    filters = {"type": type_name} if type_name else {}
    stat_links = [
        {
            "slug": slug,
            "label": label,
            "active": not speed_sort and slug == stat_slug,
            "query": urlencode({"stat": slug, **filters}),
        }
        for slug, label, _ in COMPETITIVE_STATS
    ]
    speed_groups = []
    for level in SPEED_LEVELS:
        columns = []
        for spread_slug, label, _, _ in SPEED_SPREADS:
            key = f"{spread_slug}-{level}"
            active = key == speed_sort
            next_direction = "asc" if active and speed_direction == "desc" else "desc"
            columns.append({
                "key": key,
                "label": label,
                "active": active,
                "direction": speed_direction if active else "",
                "query": urlencode({"sort": key, "dir": next_direction, **filters}),
            })
        speed_groups.append({"level": level, "columns": columns})

    query = (
        urlencode({"sort": speed_sort, "dir": speed_direction, **filters})
        if speed_sort else
        urlencode({"stat": stat_slug, **filters})
    )
    page_obj = Paginator(rows, 50).get_page(request.GET.get("page"))
    return render(request, "competitive.html", {
        "page_obj": page_obj,
        "total": len(rows),
        "stored_count": stored_count,
        "base_count": base_count,
        "form_count": form_count,
        "stat": {"slug": stat_slug, "label": stat_label},
        "stat_links": stat_links,
        "speed_mode": bool(speed_sort),
        "speed_sort": speed_sort,
        "speed_direction": speed_direction,
        "speed_label": speed_labels.get(speed_sort, ""),
        "speed_groups": speed_groups,
        "speed_query": urlencode({"sort": "max-50", **filters}),
        "selected_type": type_name,
        "type_names": [name for name, _ in TYPE_DEFENSE_ORDER],
        "stat_columns": [(label, key) for slug, label, key in COMPETITIVE_STATS if key],
        "query": query,
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