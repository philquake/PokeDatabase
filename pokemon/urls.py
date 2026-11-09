from django.urls import path

from pokemon import views

urlpatterns = [
    # Static URLS
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("pokedex/", views.pokedex, name="pokedex"), 
    path("forms/", views.forms, name="forms"),
    path("types/", views.types, name="types"),
    path("region/", views.region, name="region"),
    path("abilities/", views.abilities, name="abilities"),
    path("moves/", views.moves, name="moves"),
    path("competitive/", views.competitive, name="competitive"),
    path("items/", views.items, name="items"),

    # Dynamic URLS
    
    path("types/<str:name>/", views.type_detail, name="type_detail"),
    path("region/<str:name>/", views.region_detail, name="region_detail"),
    path("abilities/<str:slug>/", views.ability_detail, name="ability_detail"),
    path("pokedex/<str:name>/", views.pokemon_detail, name="pokemon_detail"),
    path("pokedex/<str:name>/moves/<str:version>/", views.pokemon_moves_fragment, name="pokemon_moves_fragment"),
    path("admin/sync/", views.admin_sync_pokemon, name="admin_sync_pokemon"),


    
]
