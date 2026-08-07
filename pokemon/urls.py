from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("pokedex/", views.pokedex, name="pokedex"),
    path("types/", views.types, name="types"),
    path("region/", views.region, name="region"),
    path("abilities/", views.abilities, name="abilities"),
    path("moves/", views.moves, name="moves"),
    path("competitive/", views.competitive, name="competitive"),
]
