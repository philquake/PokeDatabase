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

    return render(request, "home.html", {"pokemon": featured})

def pokemon_detail(request, pokedex_number):
    return render(request, 'pokemon_detail.html', {"pokedex_number": pokedex_number})

def search(request):
    return HttpResponse("Search functionality is not implemented yet.")

def types(request):
    return HttpResponse("Types page is not implemented yet.")

def pokedex(request):
    return HttpResponse("Pokedex page is not implemented yet.")

def region(request):
    return HttpResponse("Region page is not implemented yet.")

def abilities(request):
    return HttpResponse("Abilities page is not implemented yet.")

def moves(request):
    return HttpResponse("Moves page is not implemented yet.")

def competitive(request):
    return HttpResponse("Competitive Analysis page is not implemented yet.")
