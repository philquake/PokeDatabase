from django.test import SimpleTestCase

class PokemonViewTest(SimpleTestCase):

    def test_pokemon_detail_url_resolves_to_correct_view(self):
     response = self.client.get("/pokemon/Gengar/")

     self.assertTemplateUsed(
        response,
        "pokemon_detail.html"
     )

    def test_pokemon_detail_passes_pokemon_to_template(self):
        response = self.client.get("/pokemon/Gengar/")

        pokemon = response.context["pokemon"]

        self.assertEqual(pokemon["name"], "Gengar")
        self.assertEqual(pokemon["types"], ["Ghost", "Poison"])

    def test_search_redirects_to_pokemon_detail(self):
       response = self.client.get("/search/?search=Gengar")

       self.assertRedirects(
          response,
          "/pokemon/Gengar"
       )