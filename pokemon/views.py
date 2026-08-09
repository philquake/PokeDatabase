from django.http import Http404, HttpResponse, response
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
import json
from pathlib import Path
from django.shortcuts import render
import random

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

    hero = random.choice(pokemon_data)
    hero["type_emoji"] = TYPE_EMOJI.get(hero["types"][0], "🐾")

    # Get the two highest stats
    top_stats = sorted(
        hero["base_stats"].items(),
        key=lambda stat: stat[1],
        reverse=True
    )[:2]

    hero["top_stats"] = top_stats

    featured_pokemon = random.sample(pokemon_data, min(8, len(pokemon_data)))
    explore_pokemon  = random.choice(pokemon_data)["name"] 

    context = {
        "pokemon_count": len(pokemon_data),
        "featured": hero,
        "featured_pokemon": featured_pokemon,
        "explore_pokemon" : explore_pokemon
    }
    return render(request, "home.html", context)

def pokemon_detail(request, name):

    if not name: 
        return render(
            request,
            "home.html",
            {"error": "Pokemon name required"},
            status=400)
    
    # Load the JSON data from the file
    json_file_path = Path(__file__).resolve().parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"

    with open(json_file_path, "r") as f:
        pokemon_data = json.load(f)

    for pokemon in pokemon_data:
        if pokemon["name"] == name:
            return render(request, 'pokemon_detail.html', {"pokemon": pokemon})

    return render(
                request,
                "home.html",
                {"error": "Pokemon not found"},
                status=404)

def search(request):
    pokemon_name = request.GET.get("search")

    if not pokemon_name: 
            return render(
                request,
                "home.html",
                {"error": "Pokemon name required"},
                status=400)
        
    # Load the JSON data from the file
    json_file_path = Path(__file__).resolve().parent.parent / "assets" / "static" / "fixtures" / "pokemon.json"

    with open(json_file_path, "r") as f:
        pokemon_data = json.load(f)

    for pokemon in pokemon_data:
        if pokemon["name"].lower() == pokemon_name.lower():
            return redirect("pokemon_detail", name=pokemon["name"])
        
    return render(
            request,
            "home.html",
            {"error": "Pokemon not found"},
            status=404)
    
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
