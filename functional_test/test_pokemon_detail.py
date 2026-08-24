from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from django.urls import reverse
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time

class PokemonDetailFunctionalTest(StaticLiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_pokemon_detail_loads(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        self.assertEqual(self.browser.title, "Pokedex Entry - #94 Gengar")
        
        # Waits until the image loads checking if it returns and loads larger than a px.
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
        next = self.browser.find_element(By.CLASS_NAME, "next") # -> Onix
        next.click()
        
        expected_url = self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Onix"})
        
        #Waits for browser to redirect to expected url
        WebDriverWait(self.browser, 5).until(
            lambda browser: browser.current_url == expected_url
                )
        
        self.assertEqual(self.browser.title, "Pokedex Entry - #95 Onix")
        
    def test_previous_pokemon_link(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        next = self.browser.find_element(By.CLASS_NAME, "previous") # -> Haunter
        next.click()
        
        expected_url = self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Haunter"})
        
        #Waits for browser to redirect to expected url
        WebDriverWait(self.browser, 5).until(
            lambda browser: browser.current_url == expected_url
                )
                
        self.assertEqual(self.browser.title, "Pokedex Entry - #93 Haunter")
        
    def test_first_pokemon_has_no_previous_link(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Bulbasaur"}))
        previous_links = self.browser.find_elements(By.CLASS_NAME, "previous")  # - > Empty
        
        #Checks if previous link is empty
        self.assertEqual(len(previous_links), 0)

    def test_next_link_text_is_correct(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        next_link = self.browser.find_element(By.CLASS_NAME, "next")    # -> Onix
        self.assertIn("Onix", next_link.text)

    def test_previous_link_text_is_correct(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))
        previous_link = self.browser.find_element(By.CLASS_NAME, "previous") # -> Haunter
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
        
    def test_pokemon_gender_is_null(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Voltorb"}))
        self.assertIn("Genderless", self.browser.page_source) # -> null
        
    def test_section_tab_switch(self):
        self.browser.get(self.live_server_url + reverse("pokemon_detail", kwargs={"name": "Gengar"}))

        tab = WebDriverWait(self.browser, 5).until(
            EC.element_to_be_clickable((By.ID, "tab-breeding"))
            )
        tab.click()

        import time
        time.sleep(0.3) #due to bootstap fade immdiately applys active and then adds show shortly after
        
        WebDriverWait(self.browser, 5).until(
            lambda d: d.find_element(By.ID, "tab-breeding").get_attribute("aria-selected") == "true"
        )

        tab = self.browser.find_element(By.ID, "tab-breeding")
        overview_tab = self.browser.find_element(By.ID, "tab-overview")
        breeding_panel = self.browser.find_element(By.ID, "panel-breeding")
        overview_panel = self.browser.find_element(By.ID, "panel-overview")

        # Tab button state
        self.assertEqual(tab.get_attribute("aria-selected"), "true")
        self.assertIn("active", tab.get_attribute("class"))
        self.assertEqual(overview_tab.get_attribute("aria-selected"), "false")
        self.assertNotIn("active", overview_tab.get_attribute("class"))

        # Panel visibility (Bootstrap toggles "show active" together)
        self.assertIn("active", breeding_panel.get_attribute("class"))
        self.assertIn("show", breeding_panel.get_attribute("class"))
        self.assertTrue(breeding_panel.is_displayed())
        self.assertNotIn("active", overview_panel.get_attribute("class"))