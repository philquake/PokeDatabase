from django.test import TestCase
import lxml.html

# Create your tests here.
class HomePageTest(TestCase):
    def test_home_page_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')


class PokemonDetailPageTest(TestCase):
    def test_pokemon_detail_page_template(self):
        response = self.client.get("/pokemon/Gengar/")
        self.assertTemplateUsed(response, 'pokemon_detail.html')
        