from django.urls import path

from pokemon import views

urlpatterns = [
    # Static URLS
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("pokedex/", views.pokedex, name="pokedex"), 
    path("types/", views.types, name="types"),
    path("region/", views.region, name="region"),
    path("abilities/", views.abilities, name="abilities"),
    path("moves/", views.moves, name="moves"),
    path("competitive/", views.competitive, name="competitive"),
    path("items/", views.items, name="items"),

    # Dynamic URLS
    
    path("pokedex/<str:name>/", views.pokemon_detail, name="pokemon_detail"),
    path("admin/sync/", views.admin_sync_pokemon, name="admin_sync_pokemon"),


    
]
