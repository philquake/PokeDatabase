
import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from pathlib import Path
from pokemon.services.data import load_pokemon_data, build_name_lookup
from pokemon.services.pokelance_client import sync_pokemon_data, PokelanceAPIError


# Create your views here.
TYPE_EMOJI = {
    "Fire": "🔥", "Water": "💧", "Grass": "🌿", "Electric": "⚡",
    "Flying": "🌪️", "Psychic": "🔮", "Ice": "❄️", "Dragon": "🐉",
    "Dark": "🌑", "Fairy": "✨", "Normal": "⭐", "Fighting": "🥊",
    "Poison": "☠️", "Ground": "⛰️", "Rock": "🪨", "Bug": "🐛",
    "Ghost": "👻", "Steel": "⚙️",
}

def home(request):
    pokemon_data = load_pokemon_data()

    if pokemon_data:
        hero = random.choice(pokemon_data)
        hero["type_emoji"] = TYPE_EMOJI.get(hero["types"][0], "🐾")
        hero["top_stats"] = sorted(
            hero["base_stats"].items(), key=lambda stat: stat[1], reverse=True
        )[:2]
        featured_pokemon = random.sample(pokemon_data, min(8, len(pokemon_data)))
        explore_pokemon = random.choice(pokemon_data)["name"]
    else:
        hero = None
        featured_pokemon = []
        explore_pokemon = ""

    context = {
        "pokemon_count": len(pokemon_data),
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
    
    pokemon_data = load_pokemon_data()
    by_name = build_name_lookup(pokemon_data)
    
    for index, pokemon in enumerate(pokemon_data):
        if pokemon["name"].lower() == name.lower(): 
            current = pokemon
            next = (
                pokemon_data[index +1]
                if index + 1 < len(pokemon_data)
                else None
                )
            previous = (
                pokemon_data[index -1]
                if index > 0
                else None
            )
            
            evolution_chain = [
                by_name[evo_name.lower()]
                for evo_name in current.get("evolution_chain", [])
                if evo_name.lower() in by_name
            ]
            
            return render(request, 'pokemon_detail.html', {
                "pokemon": current, 
                "next": next, 
                "previous": previous,
                "evolution_chain": evolution_chain,
                })
    else:
        raise Http404(f"No Pokémon found match '{name}'")
    
def search(request):
    pokemon_name = request.GET.get("search", "").strip()

    if not pokemon_name: 
            messages.error(request, "Pokémon name required")
            return redirect("home")
        
    # Load the JSON data from the file
    json_file_path = Path(__file__).resolve().parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"

    with open(json_file_path, "r") as f:
        pokemon_data = json.load(f)

    for pokemon in pokemon_data:
        if pokemon["name"].lower() == pokemon_name.lower():
            return redirect("pokemon_detail", name=pokemon["name"])
        
    messages.error(request, f"No Pokémon found matching {pokemon_name}")
    return redirect("home")
    
def types(request):
    return HttpResponse("Types page is not implemented yet.")

def pokedex(request):
    pokemon_data = load_pokemon_data()
            
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

@user_passes_test(_is_staff, login_url="home")
def admin_sync_pokemon(request):
    """
    Staff-only page that triggers a sync against the Pokelance client.
 
    GET just shows the sync page. POST triggers the sync and re-renders
    the same page with either the list of newly added Pokémon or a
    sensible error message if the external API call fails — a failure
    here should never surface as a 500.
    """
    context = {}
 
    if request.method == "POST":
        try:
            new_pokemon = sync_pokemon_data()
            context["sync_success"] = True
            context["new_pokemon"] = new_pokemon
        except PokelanceAPIError as e:
            context["sync_error"] = str(e)
 
    return render(request, "admin_sync.html", context)