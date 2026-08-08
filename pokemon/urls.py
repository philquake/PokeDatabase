from django.urls import path

from pokemon import views

urlpatterns = [
    # Static URLS
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("pokedex/", views.pokedex, name="pokedex"), ##TODO Add to a grid of all pokemon entries
    path("types/", views.types, name="types"),
    path("region/", views.region, name="region"),
    path("abilities/", views.abilities, name="abilities"),
    path("moves/", views.moves, name="moves"),
    path("competitive/", views.competitive, name="competitive"),

    # Dynamic URLS
    
    path("pokedex/<str:name>/", views.pokemon_detail, name="pokemon_detail"),

    
]
