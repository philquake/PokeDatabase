
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from pokemon.models import Pokemon
from pokemon.services.data import get_pokemon_by_name, pokemon_to_dict
from pokemon.services.pokelance_client import sync_pokemon_data, PokelanceAPIError


TYPE_EMOJI = {
    "Fire": "🔥", "Water": "💧", "Grass": "🌿", "Electric": "⚡",
    "Flying": "🌪️", "Psychic": "🔮", "Ice": "❄️", "Dragon": "🐉",
    "Dark": "🌑", "Fairy": "✨", "Normal": "⭐", "Fighting": "🥊",
    "Poison": "☠️", "Ground": "⛰️", "Rock": "🪨", "Bug": "🐛",
    "Ghost": "👻", "Steel": "⚙️",
}

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
        hero["type_emoji"] = TYPE_EMOJI.get(hero["types"][0], "🐾")
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

    return render(request, 'pokemon_detail.html', {
        "pokemon": pokemon,
        "next": pokemon_to_dict(next) if next else None,
        "previous": pokemon_to_dict(previous) if previous else None,
        "evolution_chain": evolution_chain,
        "type_defense_order": TYPE_DEFENSE_ORDER,
        "stat_ranges": calculate_stat_range(pokemon["base_stats"]),
        "learnt_hm": learnt_hm,
        "learnt_tm": learnt_tm,
        "locations": pokemon["locations"],
        })

def group_hm_tm_moves(moves):
    """
    Split moves learned via TM/HM ('machine') from everything else.
    PokéAPI doesn't distinguish HM from TM in move_learn_method — both are
    "machine" — so if HM vs. TM needs to be split further later, that'll
    need its own lookup, not a name-based guess.
    """
    
    HM_NAMES = {
        "Cut", "Fly", "Surf", "Strength", "Flash", "Whirlpool",
        "Waterfall", "Rock Smash", "Dive", "Rock Climb", "Defog",
    }
    
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
    return HttpResponse("Types page is not implemented yet.")

def pokedex(request):
    pokemon_data = Pokemon.objects.all()

    return render(request, "pokedex.html", {"pokemon_data": pokemon_data})

def region(request):
    return HttpResponse("Region page is not implemented yet.")

def abilities(request):
    return HttpResponse("Abilities page is not implemented yet.")

def moves(request):
    return HttpResponse("Moves page is not implemented yet.")

def competitive(request):
    return HttpResponse("Competitive Analysis page is not implemented yet.")

def items(request):
    return HttpResponse("Items page is not implemenets yet")


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