from django.test import SimpleTestCase
from django.urls import reverse
from django.conf import settings

class PokemonViewTest(SimpleTestCase):

    def test_pokemon_detail_url_resolves_to_correct_view(self):
     response = self.client.get(reverse("pokemon_detail" , args=["Gengar"]))

     self.assertTemplateUsed(
        response,
        "pokemon_detail.html"
     )

    def test_pokemon_detail_passes_pokemon_to_template(self):
        response = self.client.get(reverse("pokemon_detail" , args=["Gengar"]))
        pokemon = response.context["pokemon"]

        self.assertEqual(pokemon["name"], "Gengar")
        self.assertEqual(pokemon["types"], ["Ghost", "Poison"])

    def test_home_view_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        

    def test_search_view_returns_302(self):
        response = self.client.get(
            reverse("search"),
            {"search": "Gengar"}
        )

        self.assertRedirects(
            response,
            reverse("pokemon_detail", args=["Gengar"])
        )

    def test_search_result_contains_gengar(self):
        response = self.client.get(
            reverse("search"),
            {"search": "Gengar"},
            follow=True
        )

        self.assertContains(response, "Gengar")
    
    def test_home_context_contains_required_data(self):
        response = self.client.get(reverse("home"))
        
        self.assertEqual(response.status_code, 200)

        required_keys = [
            "pokemon_count",
            # "move_count",
            # "ability_count",   ###TO FIX AFTER DATABASE API IS LINKED
            "explore_pokemon",
            "hero",
            "featured_pokemon",
        ]

        for key in required_keys:
            self.assertIn(key, response.context)
            
    def test_home_context_has_correct_types(self):
        response = self.client.get(reverse("home"))
        context = response.context

        self.assertIsInstance(context["pokemon_count"], int)
        # self.assertIsInstance(context["move_count"], int)
        # self.assertIsInstance(context["ability_count"], int)
        self.assertIsInstance(context["explore_pokemon"], str)
        self.assertIsInstance(context["hero"], dict)
        self.assertIsInstance(context["featured_pokemon"], list)
        
    def test_home_context_has_data(self):
        response = self.client.get(reverse("home"))
        context = response.context

        self.assertIsNotNone(context["hero"])

        self.assertTrue(context["featured_pokemon"])
        self.assertTrue(context["explore_pokemon"])
        self.assertTrue(context["pokemon_count"])
        
    def test_home_has_correct_number_of_featured_pokemon(self):
        response = self.client.get(reverse("home"))
        context = response.context

        self.assertEqual(
            len(context["featured_pokemon"]),
            settings.FEATURED_POKEMON_COUNT
        )
