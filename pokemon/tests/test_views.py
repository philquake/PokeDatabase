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
          "/pokemon/pokedex/Gengar/"
      )