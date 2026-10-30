from django.db import models


GENERATION_REGIONS = {
    1: "Kanto",
    2: "Johto",
    3: "Hoenn",
    4: "Sinnoh",
    5: "Unova",
    6: "Kalos",
    7: "Alola",
    8: "Galar",
    9: "Paldea",
}


class Pokemon(models.Model):
    """
    One Pokémon species. Small, fixed-shape groups of values (types, stats,
    abilities, matchups...) are kept as JSON columns since they're always read
    together with the Pokémon; moves and encounters are the bulk of the data,
    so they live in their own tables and are only loaded on the detail page.
    """

    pokedex_number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=50, unique=True)
    image = models.URLField(max_length=300, blank=True)
    category = models.CharField(max_length=50, blank=True)
    generation = models.PositiveSmallIntegerField(null=True, blank=True)
    region = models.CharField(max_length=20, blank=True)
    types = models.JSONField(default=list)
    base_stats = models.JSONField(default=dict)
    stat_total = models.PositiveIntegerField(default=0)
    abilities = models.JSONField(default=list)
    height_m = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    gender = models.JSONField(null=True, blank=True)  # None = genderless
    egg_groups = models.JSONField(default=list)
    catch_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    base_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    base_happiness = models.PositiveSmallIntegerField(null=True, blank=True)
    type_effectiveness = models.JSONField(default=dict)
    evolution_chain = models.JSONField(default=list)
    ev_yield = models.JSONField(default=dict)  # {"Special Attack": 3}
    growth_rate = models.CharField(max_length=30, blank=True)  # PokéAPI slug, e.g. "medium-slow"
    held_items = models.JSONField(default=list)  # wild held item names

    class Meta:
        ordering = ["pokedex_number"]
        verbose_name_plural = "pokemon"

    def __str__(self):
        return f"#{self.pokedex_number:03d} {self.name}"

    def save(self, *args, **kwargs):
        self.region = GENERATION_REGIONS.get(self.generation, "")
        super().save(*args, **kwargs)


class PokemonMove(models.Model):
    """One (move, game version, learn method, level) row for a Pokémon."""

    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="moves")
    name = models.CharField(max_length=50)
    version = models.CharField(max_length=50)
    level_learnt = models.PositiveSmallIntegerField(default=0)
    method = models.CharField(max_length=30)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["pokemon", "version"])]

    def __str__(self):
        return f"{self.pokemon.name}: {self.name} ({self.version}, {self.method})"


class PokemonEncounter(models.Model):
    """One wild encounter (location area, game version, method) for a Pokémon."""

    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="locations")
    location = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    method = models.CharField(max_length=50)
    chance = models.PositiveSmallIntegerField(default=0)
    min_level = models.PositiveSmallIntegerField(default=0)
    max_level = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["pokemon", "version"])]

    def __str__(self):
        return f"{self.pokemon.name}: {self.location} ({self.version})"
