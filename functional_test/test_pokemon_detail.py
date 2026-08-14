from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from django.urls import reverse

class PokemonDetailFunctionalTest(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_pokemon_detail_loads(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        self.assertEqual(self.browser.title, "Pokedex Entry - #94 Gengar")
        image = self.browser.find_element(By.CLASS_NAME, "pokemon-detail-img")
        self.assertTrue(image.is_displayed())

    def test_user_loads_correct_data(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        self.assertIn("Gengar", self.browser.page_source)
        self.assertIn("Ghost", self.browser.page_source)
        self.assertIn("Poison", self.browser.page_source)

    def test_next_pokemon(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        next = self.browser.find_element(By.CLASS_NAME, "next")
        next.click()
        self.assertEqual(self.browser.title, "Pokedex Entry - #131 Lapras")
        
    def test_previous_pokemon(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        next = self.browser.find_element(By.CLASS_NAME, "previous")
        next.click()
        self.assertEqual(self.browser.title, "Pokedex Entry - #59 Arcanine")