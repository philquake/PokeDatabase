from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
import json
from pathlib import Path
from django.shortcuts import render

# Create your views here.
def home(request):

    featured = {
        "name": "Charizard",
        "pokedex_number": 6,
        "types": ["Fire", "Flying"],
        "image": {
            "official_artwork": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/6.png"
        },
        "stats": {
            "highest": [
                {"name": "Sp.ATK", "value": 109},
                {"name": "SPD", "value": 100},
            ]
        },
    }

    multiple_featured = [
        {
            "pokedex": 6,
            "name": "Charizard",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/6.png",
            "types": ["Fire", "Flying"],
            "top_stats": {
                "Special Attack": 109,
                "Speed": 100
            }
        },
        {
            "pokedex": 94,
            "name": "Gengar",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/94.png",
            "types": ["Ghost", "Poison"],
            "top_stats": {
                "Special Attack": 130,
                "Speed": 110
            }
        },
        {
            "pokedex": 130,
            "name": "Gyarados",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/130.png",
            "types": ["Water", "Flying"],
            "top_stats": {
                "Attack": 125,
                "Special Defense": 100
            }
        },
        {
            "pokedex": 149,
            "name": "Dragonite",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/149.png",
            "types": ["Dragon", "Flying"],
            "top_stats": {
                "Attack": 134,
                "HP": 91
            }
        },
        {
            "pokedex": 212,
            "name": "Scizor",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/212.png",
            "types": ["Bug", "Steel"],
            "top_stats": {
                "Attack": 130,
                "Defense": 100
            }
        },
        {
            "pokedex": 248,
            "name": "Tyranitar",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/248.png",
            "types": ["Rock", "Dark"],
            "top_stats": {
                "Attack": 134,
                "Defense": 110
            }
        },
        {
            "pokedex": 472,
            "name": "Gliscor",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/472.png",
            "types": ["Ground", "Flying"],
            "top_stats": {
                "Defense": 125,
                "Speed": 95
            }
        },
        {
            "pokedex": 448,
            "name": "Lucario",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/448.png",
            "types": ["Fighting", "Steel"],
            "top_stats": {
                "Special Attack": 115,
                "Attack": 110
            }
        },
        {
            "pokedex": 445,
            "name": "Garchomp",
            "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/445.png",
            "types": ["Dragon", "Ground"],
            "top_stats": {
                "Attack": 130,
                "Speed": 102
            }
        }
    ]
    
    return render(request, "home.html", {"pokemon": featured, "multiple_featured": multiple_featured})

def search(request):
    return render(request, 'search.html')


def pokedex(request):
    return HttpResponse("Pokédex")


def types(request):
    return HttpResponse("Types")


def region(request):
    return HttpResponse("Region")


def abilities(request):
    return HttpResponse("Abilities")


def moves(request):
    return HttpResponse("Moves")


def competitive(request):
    return HttpResponse("Competitive")
    