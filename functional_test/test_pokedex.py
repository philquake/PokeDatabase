from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver
from django.urls import reverse

class Pokedex(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_pokedex_loads(self):
        self.browser.get( self.live_server_url + reverse("pokedex")
)
        self.assertIn("Gengar", self.browser.page_source)
        self.assertIn("Charizard", self.browser.page_source)
