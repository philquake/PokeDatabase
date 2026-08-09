from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver

class Pokemon_Detail(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_valid_pokemon(self):
        self.browser.get(self.live_server_url + "/pokemon/pokedex/Gengar/")
        self.assertIn("Gengar", self.browser.page_source)

    def test_invalid_pokemon(self):
        # A name in the URL that shouldn't match
        self.browser.get(self.live_server_url + "/pokemon/pokedex/not_a_pokemon/")
        self.assertIn("Pokemon not found", self.browser.page_source)

    def test_user_can_view_img(self):
        self.browser.get(self.live_server_url + "/pokemon/pokedex/Gengar/")
        image = self.browser.find_element(By.CLASS_NAME, "pokemon-detail-img")
        self.assertTrue(image.is_displayed())

    def test_user_loads_correct_data(self):
        self.browser.get(self.live_server_url + "/pokemon/pokedex/Gengar")
        self.assertIn("Ghost", self.browser.page_source)
        self.assertIn("Poison", self.browser.page_source)

