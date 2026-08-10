from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By


class HomePageTest(LiveServerTestCase):
    
    def setUp(self):
        super().setUp()
        self.browser = webdriver.Chrome()
    
    def tearDown(self):
        self.browser.quit()
        super().tearDown()
            
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
    
    def test_search_bar_present(self):
        self.browser.get(self.live_server_url + "/")
        search_bar = self.browser.find_element(By.CSS_SELECTOR, "form[method='GET']")
        self.assertIsNotNone(search_bar)
        
    def test_hero_pokemon(self):
        self.browser.get(self.live_server_url + "/")
        image = self.browser.find_element(By.CLASS_NAME, "pokemon-image")
        self.assertEqual(image.is_displayed(), True)
        
    def test_featured_pokemon(self):
        self.browser.get(self.live_server_url + "/")
        images = self.browser.find_elements(By.CLASS_NAME, "poke-card-img")
        self.assertEqual(len(images), 8)
        
    def test_featured_pokemon_clickable(self):
        self.browser.get(self.live_server_url + "/")
        card = self.browser.find_element(By.CLASS_NAME, "poke-card")
        link = card.find_element(By.TAG_NAME, "a")
        expected_url = link.get_attribute("href")
        link.click()
        self.assertEqual(self.browser.current_url, expected_url)
        
    def test_browse_clickable(self):
        self.browser.get(self.live_server_url + "/")
        card = self.browser.find_element(By.CLASS_NAME, "browse-card")
        link = card.find_element(By.TAG_NAME, "a")
        expected_url = link.get_attribute("href")
        link.click()
        self.assertEqual(self.browser.current_url, expected_url)