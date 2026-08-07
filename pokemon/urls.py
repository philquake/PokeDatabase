from django.urls import path

from pokemon import views

urlpatterns = [
    path("", views.home, name="home"),
    path("<str:name>/", views.pokemon_detail, name="pokemon_detail"),

    path("pokedex/", views.pokedex, name="pokedex"),
    path("types/", views.types, name="types"),
    path("region/", views.region, name="region"),
    path("abilities/", views.abilities, name="abilities"),
    path("moves/", views.moves, name="moves"),
    path("competitive/", views.competitive, name="competitive"),
    path("search/", views.search, name="search"),
]
