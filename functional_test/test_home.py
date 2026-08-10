from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By


class HomePageTest(LiveServerTestCase):
    
    def setUp(self):
            super().setUp()
            self.driver = webdriver.Chrome()
    
    def tearDown(self):
        self.driver.quit()
        super().tearDown()
            
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
    
    def test_search_bar_present(self):
        self.driver.get(self.live_server_url + "/")
        search_bar = self.driver.find_element(By.CSS_SELECTOR, "form[method='GET']")
        self.assertIsNotNone(search_bar)
        
    def test_hero_pokemon(self):
        self.driver.get(self.live_server_url + "/")
        image = self.driver.find_element(By.CLASS_NAME, "pokemon-image")
        self.assertEqual(image.is_displayed(), True)
        
    # def test_featured_pokemon(self):
    #     self.driver.get(self.live_server_url + "/")
    #     image = self.driver.find_element(By.CLASS_NAME, "poke-card-img")
    #     self.assertEqual(image.is_displayed(), True)
