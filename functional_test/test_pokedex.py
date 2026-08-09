from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver

class Pokedex(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_pokedex_loads(self):
        self.browser.get(self.live_server_url + "/pokemon/pokedex/")
        self.assertIn("Gengar", self.browser.page_source)
        self.assertIn("Charizard", self.browser.page_source)

    # def test_pokemon_details_loads_on_click(self):
    #     self.browser.get(self.live_server_url + "/pokemon/pokedex/")
    #     link = self.browser.find_element(By.CLASS_NAME, "pokemon-name")
    #     link.click()
    #     self.assertIn("Poison")