from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver
from django.urls import reverse
from django.test import override_settings



class Navigation_Links(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()
        
    def test_navigation_bar_links(self):
        self.browser.get(self.live_server_url + "/")
        nav_links = self.browser.find_elements(By.CSS_SELECTOR, "nav a")
        link_texts = [link.text for link in nav_links]
        expected_links = ["PokeDatabase", "Home", "Pokédex", "Types", "Region", "Abilities", "Moves", "Competitive"]
        self.assertEqual(link_texts, expected_links)

    def test_navigation_links_redirect(self):

        self.browser.get(self.live_server_url)
        link = self.browser.find_element(By.CLASS_NAME, "pokedex")
        link.click()
        
        self.assertEqual(self.browser.current_url, self.live_server_url + "/pokemon/pokedex/")

    def test_logo_redirect_home(self):

        self.browser.get(self.live_server_url)
        link = self.browser.find_element(By.CLASS_NAME, "logo-icon")
        link.click()

        self.assertEqual(self.browser.current_url, self.live_server_url + "/pokemon/")

    def test_active_navbar_home(self):
        self.browser.get(self.live_server_url + "/")
        link = self.browser.find_element(By.CSS_SELECTOR, "a.home")
        assert "active" in link.get_attribute("class")
        
    def test_active_navbar_pokedex(self):
        self.browser.get(self.live_server_url + "/pokemon/pokedex")
        link = self.browser.find_element(By.CSS_SELECTOR, "a.pokedex")
        assert "active" in link.get_attribute("class")
  
    def test_pokedex_card_redirects_to_pokemon_detail(self):
        self.browser.get(self.live_server_url + reverse("pokedex"))  
        
        pokemon = self.browser.find_element(By.CLASS_NAME, "pokemon-card")
        pokemon_name = pokemon.find_element(By.CLASS_NAME, "pokemon-name").text
        pokemon.click()
        
        self.assertEqual(
        self.browser.current_url,
        self.live_server_url + reverse("pokemon_detail", args=[pokemon_name])
    )
    
    @override_settings(DEBUG=False, ALLOWED_HOSTS=["localhost", "testserver"])
    def test_404_page_navigation_works(self):  
        self.browser.get(self.live_server_url + "/does-not-exist/")

        self.assertIn("Page Not Found", self.browser.title)

        home = self.browser.find_element(By.LINK_TEXT, "Home")
        home.click()

        self.assertEqual(self.browser.current_url, self.live_server_url + reverse("home") )


