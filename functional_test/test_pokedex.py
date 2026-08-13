from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver
from django.urls import reverse
from selenium.webdriver import Keys
from selenium.webdriver.support.ui import WebDriverWait

class Pokedex(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_pokedex_loads(self):
        self.browser.get(self.live_server_url + reverse("pokedex"))

        self.assertEqual(self.browser.title, "Pokédex")

        pokemon_grid = self.browser.find_element(By.CLASS_NAME, "pokemon-grid")
        self.assertTrue(pokemon_grid.is_displayed())

    def test_pokedex_image_loads(self):
        self.browser.get(self.live_server_url + reverse("pokedex"))

        pokemon = self.browser.find_element(By.NAME, "pokemon-image")
        
        WebDriverWait(self.browser, 10).until(
            lambda driver: driver.execute_script(
                "return arguments[0].complete &&"
                "arguments[0].naturalWidth > 0;",
            pokemon
            )
        )
    
    def test_pokedex_card_displays(self):
        self.browser.get(self.live_server_url + reverse("pokedex"))
        
        numbers = self.browser.find_element(By.CLASS_NAME, "pokemon-tag")
        names = self.browser.find_element(By.CLASS_NAME, "pokemon-name")
        types = self.browser.find_element(By.CLASS_NAME, "pokemon-types")
        
        self.assertTrue(numbers.is_displayed())
        self.assertTrue(names.is_displayed())
        self.assertTrue(types.is_displayed())

    