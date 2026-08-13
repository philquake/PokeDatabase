from django.test import SimpleTestCase
from django.urls import resolve, reverse
from pokemon import views


class PokemonDetailURLTests(SimpleTestCase):

    def test_pokemon_detail_url_resolves(self):
        resolver = resolve("/pokemon/pokedex/Gengar/")
        self.assertEqual(resolver.func, views.pokemon_detail)
        self.assertEqual(resolver.kwargs["name"], "Gengar")

    def test_pokemon_detail_reverse(self):
        url = reverse("pokemon_detail",kwargs={"name": "Gengar"})
        self.assertEqual(url,"/pokemon/pokedex/Gengar/")
        
class HomeURLTest(SimpleTestCase):
    
    def test_home_url_resolves(self):
        resolver = resolve("/")
        self.assertEqual(resolver.func, views.home)
                
class PokedexURLTest(SimpleTestCase):
    def test_pokedex_url_resolves(self):
        resolver = resolve("/pokemon/pokedex/")
        self.assertEqual(resolver.func, views.pokedex)
    
    def test_pokedex_url_name(self):
        self.assertEqual(
            reverse("pokedex"),
            "/pokemon/pokedex/"
        )
