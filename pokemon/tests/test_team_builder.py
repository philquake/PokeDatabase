from urllib.parse import urlencode

from django.test import TestCase
from django.urls import resolve, reverse

from pokemon import views
from pokemon.models import Move, Pokemon, PokemonMove
from pokemon.services.team_builder import analyze_team
from pokemon.tests.helpers import PokemonDataTestCase


class TeamBuilderAnalysisTests(PokemonDataTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        PokemonMove.objects.all().delete()
        Move.objects.all().delete()

        Move.objects.create(name="Tackle", type="Normal", damage_class="physical")
        Move.objects.create(name="Flamethrower", type="Fire", damage_class="special")
        Move.objects.create(name="Earthquake", type="Ground", damage_class="physical")
        cls.bulbasaur = Pokemon.objects.get(name="Bulbasaur")
        cls.charmander = Pokemon.objects.get(name="Charmander")
        cls.charizard = Pokemon.objects.get(name="Charizard")
        cls.onix = Pokemon.objects.get(name="Onix")
        PokemonMove.objects.create(
            pokemon=cls.bulbasaur, name="Tackle", version="red-blue", method="level-up",
        )
        PokemonMove.objects.create(
            pokemon=cls.charizard, name="Flamethrower", version="red-blue", method="level-up",
        )
        PokemonMove.objects.create(
            pokemon=cls.onix, name="Earthquake", version="red-blue", method="level-up",
        )

    def test_analysis_counts_stacked_defensive_weaknesses_and_move_coverage(self):
        analysis = analyze_team([self.charmander, self.charizard])

        rock = next(row for row in analysis["defensive_weaknesses"] if row["slug"] == "rock")
        self.assertEqual(rock["weak_count"], 2)
        self.assertEqual(
            [(member["name"], member["label"]) for member in rock["weak_members"]],
            [("Charmander", "2×"), ("Charizard", "4×")],
        )
        grass = next(row for row in analysis["offensive_coverage"] if row["slug"] == "grass")
        self.assertTrue(grass["covered"])
        self.assertEqual(grass["move_types"], ["fire"])
        ground = next(row for row in analysis["offensive_coverage"] if row["slug"] == "ground")
        self.assertFalse(ground["covered"])
        self.assertIn("ground", analysis["coverage_gaps"])

    def test_suggestions_cover_uncovered_types_and_exclude_team_members(self):
        analysis = analyze_team([self.bulbasaur, self.charizard])

        suggestion = next(
            row for row in analysis["team_suggestions"] if row["name"] == "Onix"
        )
        self.assertIn("ground", suggestion["move_types"])
        self.assertIn("electric", suggestion["covers"])
        self.assertGreater(suggestion["gap_count"], 0)
        self.assertNotIn(
            self.bulbasaur.name,
            [row["name"] for row in analysis["team_suggestions"]],
        )

    def test_status_move_types_do_not_count_as_offensive_coverage(self):
        Move.objects.create(
            name="Decorative Flame", type="Fire", damage_class="status",
        )
        PokemonMove.objects.create(
            pokemon=self.bulbasaur,
            name="Decorative Flame",
            version="red-blue",
            method="level-up",
        )

        analysis = analyze_team([self.bulbasaur])

        grass = next(row for row in analysis["offensive_coverage"] if row["slug"] == "grass")
        self.assertFalse(grass["covered"])


class TeamBuilderViewTests(PokemonDataTestCase):

    def team_url(self, *names):
        return f"{reverse('team')}?{urlencode({'p': ','.join(names)}, safe=',')}"

    def test_team_url_resolves(self):
        self.assertEqual(resolve(reverse("team")).func, views.team_builder)
        self.assertEqual(reverse("team"), "/team/")

    def test_empty_page_lists_stored_pokemon_and_team_slots(self):
        response = self.client.get(reverse("team"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "team_builder.html")
        self.assertEqual(len(response.context["team_slots"]), 6)
        self.assertContains(response, 'name="p"')
        self.assertFalse(response.context["errors"])

    def test_comma_separated_url_selects_team_and_is_shareable(self):
        response = self.client.get(self.team_url("Bulbasaur", "Charizard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [pokemon["name"] for pokemon in response.context["team_pokemon"]],
            ["Bulbasaur", "Charizard"],
        )
        self.assertEqual(
            response.context["share_url"],
            "/team/?p=Bulbasaur,Charizard",
        )

    def test_repeated_select_values_redirect_to_canonical_comma_url(self):
        response = self.client.get(
            f"{reverse('team')}?p=Bulbasaur&p=&p=Charizard&p=",
        )

        self.assertRedirects(response, self.team_url("Bulbasaur", "Charizard"), fetch_redirect_response=False)

    def test_malformed_blank_team_member_is_rejected(self):
        response = self.client.get(self.team_url("Bulbasaur,,Charizard"))

        self.assertContains(response, "Team members cannot be blank")
        self.assertFalse(response.context["team_pokemon"])

    def test_unknown_member_is_rejected(self):
        response = self.client.get(self.team_url("Bulbasaur", "Missingno"))

        self.assertContains(response, "Unknown Pokémon: Missingno")
        self.assertFalse(response.context["team_pokemon"])

    def test_duplicate_members_are_rejected_case_insensitively(self):
        response = self.client.get(self.team_url("Bulbasaur", "bulbasaur"))

        self.assertContains(response, "Each Pokémon can only be selected once")
        self.assertFalse(response.context["team_pokemon"])

    def test_more_than_six_members_are_rejected(self):
        response = self.client.get(self.team_url(
            "Bulbasaur", "Ivysaur", "Venusaur", "Charmander",
            "Charmeleon", "Charizard", "Gastly",
        ))

        self.assertContains(response, "Choose no more than six Pokémon")
        self.assertFalse(response.context["team_pokemon"])


class TeamBuilderEmptyDatabaseTests(TestCase):

    def test_empty_database_shows_import_guidance(self):
        response = self.client.get(reverse("team"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Pokémon are stored yet")
        self.assertNotContains(response, 'name="p"')
