from urllib.parse import urlencode

from django.test import TestCase
from django.urls import resolve, reverse

from pokemon import views
from pokemon.models import Pokemon, PokemonMove
from pokemon.services.stats import calculate_stat_range
from pokemon.tests.helpers import PokemonDataTestCase


class ComparisonViewTests(PokemonDataTestCase):

    def compare_url(self, *names):
        query = urlencode([("p", name) for name in names])
        return f"{reverse('comparison')}?{query}"

    def replace_moves(self, pokemon_name, entries):
        pokemon = Pokemon.objects.get(name=pokemon_name)
        pokemon.moves.all().delete()
        PokemonMove.objects.bulk_create(
            PokemonMove(pokemon=pokemon, name=name, version=version, method="level-up")
            for name, version in entries
        )

    def test_comparison_url_resolves(self):
        resolver = resolve(reverse("comparison"))

        self.assertEqual(resolver.func, views.comparison)

    def test_competitive_tools_are_in_the_main_navigation_dropdown(self):
        response = self.client.get(reverse("competitive"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="competitive active"')
        self.assertContains(response, 'aria-expanded="false" aria-controls="competitiveMenu">Competitive</button>')
        self.assertContains(response, 'href="/pokemon/competitive/" aria-current="page">Rankings</a>')
        self.assertContains(response, 'href="/pokemon/compare/">Compare Pokémon</a>')
        self.assertContains(response, 'href="/team/"')
        self.assertContains(response, 'aria-label="Competitive tools"')
        self.assertNotContains(response, '<nav class="stat-tabs" aria-label="Competitive tools">')

    def test_empty_page_prompts_for_two_to_four_pokemon(self):
        response = self.client.get(reverse("comparison"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "comparison.html")
        self.assertContains(response, "Choose at least two Pokémon")
        self.assertContains(response, 'name="p"')
        self.assertContains(response, 'href="/pokemon/competitive/">Rankings</a>')
        self.assertContains(response, 'href="/pokemon/compare/" aria-current="page">Compare Pokémon</a>')
        self.assertNotContains(response, '<nav class="stat-tabs" aria-label="Competitive tools">')
        self.assertFalse(response.context["errors"])

    def test_compares_stats_types_weaknesses_and_move_overlap(self):
        self.replace_moves("Bulbasaur", [
            ("Tackle", "red-blue"),
            ("Tackle", "yellow"),
            ("Growl", "red-blue"),
        ])
        self.replace_moves("Charizard", [
            ("Tackle", "red-blue"),
            ("Growl", "red-blue"),
            ("Shadow Ball", "scarlet-violet"),
        ])
        self.replace_moves("Gengar", [
            ("Tackle", "red-blue"),
            ("Shadow Ball", "scarlet-violet"),
        ])

        response = self.client.get(self.compare_url("Bulbasaur", "Charizard", "Gengar"))

        self.assertEqual(response.status_code, 200)
        compared = response.context["comparison_pokemon"]
        self.assertEqual([pokemon["name"] for pokemon in compared], [
            "Bulbasaur", "Charizard", "Gengar",
        ])
        self.assertNotEqual(compared[0]["types"], compared[1]["types"])
        charizard = next(p for p in compared if p["name"] == "Charizard")
        rock_weakness = next(w for w in charizard["weaknesses"] if w["slug"] == "rock")
        self.assertEqual(rock_weakness["multiplier"], 4)

        attack_stat = next(stat for stat in charizard["stats"] if stat["label"] == "Attack")
        self.assertEqual(
            (attack_stat["minimum"], attack_stat["maximum"]),
            (
                calculate_stat_range(charizard["base_stats"])["Attack"]["min"],
                calculate_stat_range(charizard["base_stats"])["Attack"]["max"],
            ),
        )
        self.assertEqual(
            [move["name"] for move in response.context["shared_moves"]],
            ["Tackle"],
        )
        self.assertEqual(
            [(move["name"], move["owners"]) for move in response.context["partial_moves"]],
            [
                ("Growl", ["Bulbasaur", "Charizard"]),
                ("Shadow Ball", ["Charizard", "Gengar"]),
            ],
        )
        self.assertIn("p=Bulbasaur&p=Charizard&p=Gengar", response.context["share_url"])
        self.assertContains(response, "Shareable comparison URL")

    def test_missing_move_data_is_reported_without_breaking_comparison(self):
        Pokemon.objects.get(name="Voltorb").moves.all().delete()

        response = self.client.get(self.compare_url("Charizard", "Voltorb"))

        self.assertEqual(response.status_code, 200)
        voltorb = next(
            pokemon for pokemon in response.context["comparison_pokemon"]
            if pokemon["name"] == "Voltorb"
        )
        self.assertEqual(voltorb["moves_known_count"], 0)
        self.assertFalse(response.context["shared_moves"])
        self.assertContains(response, "move data has not been synced")

    def test_missing_selection_is_validated(self):
        response = self.client.get(self.compare_url("Bulbasaur"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose at least two Pokémon")
        self.assertFalse(response.context["comparison_pokemon"])
        self.assertIn("Select a Pokémon.", response.context["comparison_slots"][1]["errors"])

    def test_duplicate_selections_are_rejected_case_insensitively(self):
        response = self.client.get(self.compare_url("Bulbasaur", "bulbasaur"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Each Pokémon can only be selected once")
        self.assertFalse(response.context["comparison_pokemon"])
        self.assertIn(
            "Choose a different Pokémon.",
            response.context["comparison_slots"][1]["errors"],
        )

    def test_unknown_selection_is_reported(self):
        response = self.client.get(self.compare_url("Bulbasaur", "Missingno"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unknown Pokémon: Missingno")
        self.assertFalse(response.context["comparison_pokemon"])
        self.assertIn(
            "This Pokémon was not found.",
            response.context["comparison_slots"][1]["errors"],
        )

    def test_more_than_four_selections_are_rejected(self):
        response = self.client.get(self.compare_url(
            "Bulbasaur", "Ivysaur", "Venusaur", "Charmander", "Charmeleon",
        ))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose no more than four Pokémon")
        self.assertFalse(response.context["comparison_pokemon"])


class ComparisonViewEmptyDatabaseTests(TestCase):

    def test_empty_database_shows_import_guidance(self):
        response = self.client.get(reverse("comparison"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Pokémon are stored yet")
        self.assertNotContains(response, 'name="p"')
