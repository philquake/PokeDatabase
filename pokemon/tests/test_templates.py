from django.test import TestCase
from django.urls import reverse
from django.test import override_settings
from django.contrib.auth import get_user_model



class HomePageTest(TestCase):
    def test_home_page_template(self):
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, 'home.html')


class PokemonDetailPageTest(TestCase):
    def test_pokemon_detail_page_template(self):
        response = self.client.get("/pokemon/pokedex/Gengar/")
        self.assertTemplateUsed(response, 'pokemon_detail.html')
        
        
class BaseHtmlTest(TestCase):
    def test_home_uses_base_template(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertTemplateUsed(response, "base.html")
        
class PokedexTest(TestCase):
    def test_pokedex_page_template(self):
        response = self.client.get(reverse("pokedex"))
        
        self.assertTemplateUsed(response, "pokedex.html")

class AllTemplatesExtendBaseTest(TestCase):
    def test_all_pokemon_templates_use_base_html(self):
        pages = [
            ("home", {}, "home.html"),
            ("pokedex", {}, "pokedex.html"),
            ("pokemon_detail", {"name": "Gengar"}, "pokemon_detail.html"),
        ]

        # subTest lets Django report all failing pages independently in one run, one failing test would stop the loop
        for url_name, kwargs, template_name in pages:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, kwargs=kwargs))
                self.assertTemplateUsed(response, template_name)
                self.assertTemplateUsed(response, "base.html")                       
                
    @override_settings(DEBUG=False, ALLOWED_HOSTS=["localhost", "testserver"])
    def test_404_template_used(self):
        response = self.client.get("/does-not-exist")
        self.assertTemplateUsed(response, "404.html")

User = get_user_model()

class ApiSync(TestCase):
    def setUp(self):
        self.url = reverse("admin_sync_pokemon")
   
        self.staff_user = User.objects.create_user(
            username="staffer", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="testpass123", is_staff=False
        )
        
    def test_admin_sync_renders_admin_sync_template(self):
        self.client.login(username="staffer", password="testpass123")
        response = self.client.get(reverse("admin_sync_pokemon"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_sync.html")
