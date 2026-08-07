from django.test import SimpleTestCase
from django.urls import resolve, reverse

from pokemon import views


class PokemonURLTests(SimpleTestCase):

    def test_home_url(self):
        resolver = resolve("/")
        self.assertEqual(resolver.func, views.home)

    def test_pokemon_detail_url_resolves(self):
        resolver = resolve("/pokemon/Gengar/")
        self.assertEqual(resolver.func, views.pokemon_detail)

    def test_pokemon_detail_url_name(self):
        resolver = resolve("/pokemon/Gengar/")
        self.assertEqual(resolver.url_name,"pokemon_detail")

    def test_pokemon_detail_captures_name(self):
        resolver = resolve("/pokemon/Gengar/")
        self.assertEqual(resolver.kwargs["name"],"Gengar")

    def test_pokemon_detail_reverse(self):
        url = reverse("pokemon_detail",kwargs={"name": "Gengar"})
        self.assertEqual(url,"/pokemon/Gengar/")