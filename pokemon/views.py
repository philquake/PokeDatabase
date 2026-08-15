from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
import json
from pathlib import Path
from django.shortcuts import render
import random
from django.contrib import messages


# Create your views here.
TYPE_EMOJI = {
    "Fire": "🔥", "Water": "💧", "Grass": "🌿", "Electric": "⚡",
    "Flying": "🌪️", "Psychic": "🔮", "Ice": "❄️", "Dragon": "🐉",
    "Dark": "🌑", "Fairy": "✨", "Normal": "⭐", "Fighting": "🥊",
    "Poison": "☠️", "Ground": "⛰️", "Rock": "🪨", "Bug": "🐛",
    "Ghost": "👻", "Steel": "⚙️",
}

def home(request):
    fixture_path = Path(__file__).resolve().parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"
    with open(fixture_path, encoding="utf-8") as f:
        pokemon_data = json.load(f)

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
    
    # Load the JSON data from the file
    json_file_path = Path(__file__).resolve().parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"

    with open(json_file_path, "r") as f:
        pokemon_data = json.load(f)

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
            return render(request, 'pokemon_detail.html', {
                "pokemon": current, "next": next, "previous": previous
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
    # Load the JSON data from the file
    json_file_path = Path(__file__).resolve().parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"
    
    with open(json_file_path, "r") as f:
        pokemon_data = json.load(f)
            
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
