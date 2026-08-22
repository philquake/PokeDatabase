from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from django.urls import reverse
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

class PokemonDetailFunctionalTest(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_pokemon_detail_loads(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        self.assertEqual(self.browser.title, "Pokedex Entry - #94 Gengar")
        
        WebDriverWait(self.browser, 10).until(
                    lambda driver: driver.execute_script("""
                        const img = document.querySelector('.pokemon-hero-img');
                        return img && img.complete && img.naturalWidth > 0;
                    """)
                )
        
        image = self.browser.find_element(By.CLASS_NAME, "pokemon-hero-img")
        self.assertTrue(image.is_displayed())

    def test_user_loads_correct_data(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        self.assertIn("Gengar", self.browser.page_source)
        self.assertIn("GHOST", self.browser.page_source)
        self.assertIn("POISON", self.browser.page_source)

    def test_next_pokemon_link(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        next = self.browser.find_element(By.CLASS_NAME, "next")
        next.click()
        
        expected_url = self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Onix"})
        WebDriverWait(self.browser, 5).until(
            lambda browser: browser.current_url == expected_url
                )
        
        self.assertEqual(self.browser.title, "Pokedex Entry - #95 Onix")
        
    def test_previous_pokemon_link(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        next = self.browser.find_element(By.CLASS_NAME, "previous")
        next.click()
        
        expected_url = self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Haunter"})
        WebDriverWait(self.browser, 5).until(
            lambda browser: browser.current_url == expected_url
                )
                
        self.assertEqual(self.browser.title, "Pokedex Entry - #93 Haunter")
        
    def test_first_pokemon_has_no_previous_link(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Charizard"}))
        previous_links = self.browser.find_elements(By.CLASS_NAME, "previous")
        self.assertEqual(len(previous_links), 0)

    def test_next_link_text_is_correct(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        next_link = self.browser.find_element(By.CLASS_NAME, "next")
        self.assertIn("Onix", next_link.text)

    def test_previous_link_text_is_correct(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        previous_link = self.browser.find_element(By.CLASS_NAME, "previous")
        self.assertIn("Haunter", previous_link.text)

    def test_chained_next_navigation(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        self.browser.find_element(By.CLASS_NAME, "next").click()  # -> Onix

        WebDriverWait(self.browser, 5).until(
            lambda driver: driver.title == "Pokedex Entry - #95 Onix"
        )

        self.browser.find_element(By.CLASS_NAME, "next").click()  # -> Drowzee
        WebDriverWait(self.browser, 5).until(
            lambda driver: driver.title == "Pokedex Entry - #96 Drowzee"
        )
        self.assertEqual(self.browser.title, "Pokedex Entry - #96 Drowzee")