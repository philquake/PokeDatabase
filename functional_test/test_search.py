from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.urls import reverse

class SearchTest (LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()
        
    def test_user_can_search_for_pokemon_via_form(self):
        self.browser.get(self.live_server_url + reverse("home"))
        search_box = self.browser.find_element(By.NAME, "search")
        search_box.send_keys("Gengar")
        search_button = self.browser.find_element(By.CLASS_NAME,"search-button")
        search_button.click()

        self.assertEqual(
                self.browser.current_url,
                self.live_server_url + reverse(
                    "pokemon_detail",
                    kwargs={"name": "Gengar"}
                )
            )
        
    def test_search_for_nonexistent_pokemon_via_form(self):
        self.browser.get(self.live_server_url + reverse("home"))
        search_box = self.browser.find_element(By.NAME, "search")
        search_box.send_keys("NotaPokemon")
        search_button = self.browser.find_element(By.CLASS_NAME,"search-button")
        search_button.click()

        self.assertEqual(self.browser.current_url, self.live_server_url + reverse("home"))
        self.assertIn("Pokemon not found", self.browser.page_source)