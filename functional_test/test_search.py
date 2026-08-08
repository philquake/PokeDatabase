from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By

class SearchLoadsTest (LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()
        
    def test_user_can_search_for_pokemon_via_form(self):
        self.browser.get(self.live_server_url)
        search_box = self.browser.find_element(By.NAME, "search")
        search_box.send_keys("Gengar")
        search_box.submit()

        self.assertEqual(self.browser.current_url, self.live_server_url + "/pokemon/pokedex/Gengar/")

    def test_user_search_not_a_pokemon(self):
        self.browser.get(self.live_server_url)
        search_box = self.browser.find_element(By.NAME, "search")
        search_box.send_keys("NotAPokemon")
        search_box.submit()

        self.assertIn("Pokemon not found", self.browser.page_source )

    def test_user_search_empty(self):
        self.browser.get(self.live_server_url)

        search_box = self.browser.find_element(By.NAME, "search")
        search_box.submit()

        self.assertIn("Pokemon name required", self.browser.page_source)