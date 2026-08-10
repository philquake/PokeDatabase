from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



class SearchTest (LiveServerTestCase):

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
        WebDriverWait(self.browser, 5).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "footer"), "Pokemon not found")
        )
        self.assertIn("Pokemon not found", self.browser.page_source )

    def test_user_search_empty(self):
        self.browser.get(self.live_server_url)

        search_box = self.browser.find_element(By.NAME, "search")
        search_box.submit()
        WebDriverWait(self.browser, 5).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "footer"), "Pokemon name required")
        )
        self.assertIn("Pokemon name required", self.browser.page_source)