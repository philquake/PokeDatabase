from django.test import SimpleTestCase
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch ###Makes you allows you to temporarily replace a target with a mock object
from django.test import RequestFactory
from django.http import Http404
from pokemon.views import pokemon_detail

class PokemonDetailTest(SimpleTestCase):

    def test_pokemon_detail_url_resolves_to_correct_view(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_pokemon_detail_passes_pokemon_to_template(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )
        pokemon = response.context["pokemon"]
  
        self.assertEqual(response.status_code, 200)

        required_keys = [
            "pokedex_number",  
            "name",
            "image",
            "types",
            "base_stats",
        ]

        for key in required_keys:
            self.assertIn(key, pokemon)
            
        self.assertEqual(pokemon["name"], "Gengar")
        self.assertEqual(pokemon["types"], ["Ghost", "Poison"])
        self.assertIsInstance(pokemon["base_stats"], dict)
        self.assertEqual(pokemon["base_stats"]["Special Attack"], 130)
        
    def test_pokemon_detail_next_pokemon_link(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )
        next = response.context["next"]
        
        self.assertEqual(next["name"], "Onix")
        
    def test_pokemon_detail_previous_pokemon_link(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )
        previous = response.context["previous"]
        
        self.assertEqual(previous["name"], "Haunter")
        
    def test_first_pokemon_has_no_previous_link(self):
        response = self.client.get(
            reverse("pokemon_detail",
            args=["Charizard"]
            )
        )
        previous = response.context["previous"]
        
        self.assertIsNone(previous)
        
    def test_last_pokemon_has_no_previous_link(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Flaaffy"]
            )
        )
        next = response.context["next"]
        
        self.assertIsNone(next)
            
    def test_lowercase_pokemon_detail_loads(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["gengar"]
            )
        )
        
        self.assertEqual(response.status_code, 200)
        
        pokemon = response.context["pokemon"]
        self.assertEqual(pokemon["name"], "Gengar")

        self.assertEqual(response.context["next"]["name"], "Onix")
        self.assertEqual(response.context["previous"]["name"], "Haunter")

    def test_pokemon_detail_returns_404_for_unknown_pokemon(self):
        response = self.client.get(
            reverse("pokemon_detail", 
                    args=["NotARealPokemon"]
            )
        )
        
        self.assertEqual(response.status_code, 404)
        
    def test_404_exception_message_contains_searched_name(self):
        #RequestFactory is a Django testing utility used to create an HTTP request object manually,
        # so you can call a view directly without going through Django's normal request/URL/middleware cycle.
        factory = RequestFactory()
        request = factory.get("/pokemon/pokedex/NotARealPokemon/")

        #dont use self.client because it doesn't give you access to the exception's message unless you dig through 
        # the rendered template output(and that only works if DEBUG=False and your custom 404.html actually prints {{ exception }})
        #Testing the exception directly with assertRaises is more precise and doesn't depend on template rendering or 
        # DEBUG state at all.
        with self.assertRaises(Http404) as cm:
            pokemon_detail(request, name="NotARealPokemon")

        self.assertIn("NotARealPokemon", str(cm.exception))
        
    def test_pokemon_detail_returns_404_for_empty_name(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=[" "]
            )
        )
        
        self.assertEqual(response.status_code, 400) 


class HomeViewTest(SimpleTestCase):

    def test_home_view_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        
    def test_home_context_contains_required_data(self):
        response = self.client.get(reverse("home"))
        
        self.assertEqual(response.status_code, 200)

        required_keys = [
            "pokemon_count",
            # "move_count",
            # "ability_count",   
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

    @patch("pokemon.views.json.load")
    def test_home_view_has_empty_featured_grid_when_no_pokemon(self, mock_json_load):
        mock_json_load.return_value = []
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["featured_pokemon"], [])
        self.assertIsNone(response.context["hero"])


class SearchViewTest(SimpleTestCase):

    def test_search_view_redirects(self):
        response = self.client.get(
            reverse("search"),
            {"search": "Gengar"})

        self.assertRedirects(response,reverse("pokemon_detail", args=["Gengar"]))

    def test_search_returns_200_when_pokemon_not_found(self):
        response = self.client.get(
            reverse("search"),
            {"search": "NotARealPokemon"},
            follow=True         ##so it follows the redirect elsewise it will stay at the static url
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("home"))
        self.assertContains(response, "No Pokémon found matching NotARealPokemon")