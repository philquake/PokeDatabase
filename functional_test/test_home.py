from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import Keys
from selenium.webdriver.support import expected_conditions as EC




class HomePageTest(LiveServerTestCase):
    
    def setUp(self):
        super().setUp()
        self.browser = webdriver.Chrome()
    
    def tearDown(self):
        self.browser.quit()
        super().tearDown()
            
    def test_home_page_title(self):
        self.browser.get(self.live_server_url + "/")
        self.assertEqual(self.browser.title, "Home")
                 
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
    
    def test_search_bar_present(self):
        self.browser.get(self.live_server_url + "/")
        search_bar = self.browser.find_element(By.CLASS_NAME, "search-input")
        self.assertIsNotNone(search_bar)
        
    def test_hero_pokemon_content(self):
        self.browser.get(self.live_server_url + "/")

        WebDriverWait(self.browser, 10).until(
            lambda driver: driver.execute_script("""
                const img = document.querySelector('.pokemon-image');
                return img && img.complete && img.naturalWidth > 0;
            """)
        )

        image = self.browser.find_element(By.CLASS_NAME, "pokemon-image")
        type = self.browser.find_element(By.CLASS_NAME, "type-emoji")
        pokedex_num = self.browser.find_element(By.CLASS_NAME, "pokemon-tag-id")
        top_stat = self.browser.find_element(By.CLASS_NAME, "pokemon-tag-stats")
        
        self.assertTrue(image.is_displayed())
        self.assertTrue(type.is_displayed())
        self.assertTrue(pokedex_num.is_displayed())
        self.assertTrue(top_stat.is_displayed())
        
    def test_featured_pokemon_exist(self):
        self.browser.get(self.live_server_url + "/")
        self.browser.find_element(By.TAG_NAME, 'body').send_keys(Keys.END) ##Scroll down to the featured pokemon section that has lazy loading

        cards = self.browser.find_elements(By.CLASS_NAME, "poke-card")
        self.assertEqual(len(cards), 8)
        
    def test_featured_pokemon_img_loads(self):
        self.browser.get(self.live_server_url + "/")

        cards = WebDriverWait(self.browser, 10).until(
            lambda driver: driver.find_elements(
                By.CLASS_NAME, "poke-card"
            )
        )

        for card in cards:
            image = card.find_element(By.TAG_NAME, "img")
            self.browser.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                image
            )

            WebDriverWait(self.browser, 10).until(
                lambda driver: driver.execute_script(
                    "return arguments[0].complete && "
                    "arguments[0].naturalWidth > 0;",
                    image
                )
            )
     
    def test_featured_pokemon_content(self):
        self.browser.get(self.live_server_url + "/")
        types = self.browser.find_element(By. CLASS_NAME, "type-badge")
        name = self.browser.find_element(By. CLASS_NAME, "poke-card-name")
        id = self.browser.find_element(By. CLASS_NAME, "poke-card-id")

        self.assertIsNotNone(types)
        self.assertIsNotNone(name)
        self.assertIsNotNone(id)
        
    def test_featured_pokemon_redirect(self):
        self.browser.get(self.live_server_url + "/")
        card = self.browser.find_element(By.CLASS_NAME, "poke-card")
        link = card.find_element(By.TAG_NAME, "a")
        expected_url = link.get_attribute("href")
        link.click()
        self.assertEqual(self.browser.current_url, expected_url)
    
    def test_browse_card_content(self):
        self.browser.get(self.live_server_url + "/")
        resources = self.browser.find_element(By.CLASS_NAME, "resources")
        links = resources.find_elements(By.TAG_NAME, "a")
        self.assertEqual(
        links[2].get_attribute("href"),"https://github.com/philquake")
        
        # resources = self.browser.find_element(By.CLASS_NAME, "community")
        # links = resources.find_elements(By.TAG_NAME, "a")
        # self.assertEqual(
        # links[2].get_attribute("href"),"https://github.com/philquake")
        
    def test_browse_card_redirects(self):
        self.browser.get(self.live_server_url + "/")
        card = self.browser.find_element(By.CLASS_NAME, "browse-card")
        link = card.find_element(By.TAG_NAME, "a")
        expected_url = link.get_attribute("href")
        link.click()
        self.assertEqual(self.browser.current_url, expected_url)
        
    def test_view_all_button(self):
        self.browser.get(self.live_server_url + "/")
        view_all = self.browser.find_element(By.CLASS_NAME, "view-all")
        self.assertIsNotNone(view_all)
    
    def test_view_all_redirect(self):
        self.browser.get(self.live_server_url + "/")
        view_all = self.browser.find_element(By.CLASS_NAME, "view-all")
        view_all.click()
        self.assertEqual(self.browser.current_url, self.live_server_url + "/pokemon/pokedex/")