from django.contrib import admin

from pokemon.models import Ability, Item, Move, Pokemon, PokemonEncounter, PokemonMove


@admin.register(Pokemon)
class PokemonAdmin(admin.ModelAdmin):
    list_display = ("pokedex_number", "name", "generation", "region", "stat_total")
    list_filter = ("generation", "region")
    search_fields = ("name",)


@admin.register(PokemonMove)
class PokemonMoveAdmin(admin.ModelAdmin):
    list_display = ("pokemon", "name", "version", "method", "level_learnt")
    list_filter = ("method", "version")
    search_fields = ("pokemon__name", "name")
    list_select_related = ("pokemon",)


@admin.register(PokemonEncounter)
class PokemonEncounterAdmin(admin.ModelAdmin):
    list_display = ("pokemon", "location", "version", "method", "chance")
    list_filter = ("version", "method")
    search_fields = ("pokemon__name", "location")
    list_select_related = ("pokemon",)


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "damage_class", "power", "accuracy", "pp", "generation")
    list_filter = ("type", "damage_class", "generation")
    search_fields = ("name", "effect")


@admin.register(Ability)
class AbilityAdmin(admin.ModelAdmin):
    list_display = ("name", "generation")
    list_filter = ("generation",)
    search_fields = ("name", "effect")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "cost")
    list_filter = ("category",)
    search_fields = ("name", "effect")
