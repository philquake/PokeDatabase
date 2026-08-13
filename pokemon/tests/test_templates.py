from django.test import TestCase
from django.urls import reverse

# Create your tests here.
class HomePageTest(TestCase):
    def test_home_page_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')


class PokemonDetailPageTest(TestCase):
    def test_pokemon_detail_page_template(self):
        response = self.client.get("/pokemon/pokedex/Gengar/")
        self.assertTemplateUsed(response, 'pokemon_detail.html')
        
        
class BaseHtmlTetst(TestCase):
    def test_home_uses_base_template(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertTemplateUsed(response, "base.html")
        
class Pokedex(TestCase):
    def test_pokedex_page_template(self):
        response = self.client.get(reverse("pokedex"))
        
        self.assertTemplateUsed(response, "pokedex.html")