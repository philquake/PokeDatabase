from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
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

        self.assertEqual(
        self.browser.current_url,
        self.live_server_url + "/pokemon/Gengar/")
        