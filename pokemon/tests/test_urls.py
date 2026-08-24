from django.test import SimpleTestCase
from django.urls import resolve, reverse
from pokemon import views
from django.contrib.auth import get_user_model
from pokemon.services.pokelance_client import PokelanceAPIError
from unittest.mock import patch
from django.test import TestCase


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
        resolver = resolve("/pokemon/")
        self.assertEqual(resolver.func, views.home)
        
    def test_root_redirects_to_home(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/pokemon/")
                
class PokedexURLTest(SimpleTestCase):
    def test_pokedex_url_resolves(self):
        resolver = resolve("/pokemon/pokedex/")
        self.assertEqual(resolver.func, views.pokedex)
    
    def test_pokedex_url_name(self):
        self.assertEqual(
            reverse("pokedex"),
            "/pokemon/pokedex/"
        )

User = get_user_model()

class AdminSyncPokemonViewTests(TestCase):

    def setUp(self):
        self.url = reverse("admin_sync_pokemon")

        self.staff_user = User.objects.create_user(
            username="staffer", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="testpass123", is_staff=False
        )

    def test_get_renders_empty_sync_page_for_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_sync.html")
        self.assertNotIn("sync_success", response.context)
        self.assertNotIn("sync_error", response.context)


    def test_non_staff_user_redirected_to_home(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("home"))

    def test_anonymous_user_redirected_to_home(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("home"))
        
    def test_post_as_non_staff_redirected_to_home(self):
        self.client.force_login(self.regular_user)
        with patch("pokemon.views.sync_pokemon_data") as mock_sync:
            response = self.client.post(self.url)
        self.assertRedirects(response, reverse("home"))
        mock_sync.assert_not_called()  # critical: sync must NOT run for non-staff

    def test_post_as_anonymous_redirected(self):
        with patch("pokemon.views.sync_pokemon_data") as mock_sync:
            response = self.client.post(self.url)
        self.assertRedirects(response, reverse("home"))
        mock_sync.assert_not_called()
