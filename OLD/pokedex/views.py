from django.shortcuts import render
from .services import get_pokemon


def pokemon_detail(request, name):

    pokemon = get_pokemon(name)

    context = {
        "pokemon": pokemon
    }

    return render(
        request,
        "pokemon/detail.html",
        context
    )