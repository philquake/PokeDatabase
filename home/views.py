from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
import json
from pathlib import Path
from django.shortcuts import render

# Create your views here.
def home(request):

    pokemon = {
        "name": "Charizard",
        "pokedex_number": 6,
        "types": ["Fire", "Flying"],
        "image": {
            "official_artwork": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/6.png"
        },
        "stats": {
            "highest": [
                {"name": "Special Attack", "value": 109},
                {"name": "Speed", "value": 100},
            ]
        },
    }

    return render(request, "home.html", {"pokemon": pokemon})

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
    