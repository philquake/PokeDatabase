from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver

class Navigation_Links(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()
        
    def test_navigation_bar_links(self):
        self.driver.get(self.live_server_url + "/")
        nav_links = self.driver.find_elements(By.CSS_SELECTOR, "nav a")
        link_texts = [link.text for link in nav_links]
        expected_links = ["PokeDatabase", "Home", "Pokédex", "Types", "Region", "Abilities", "Moves", "Competitive"]
        self.assertEqual(link_texts, expected_links)

    def test_navigation_links_redirect(self):

        self.browser.get(self.live_server_url)
        link = self.browser.find_element(By.CLASS_NAME, "pokedex")
        link.click()
        
        self.assertEqual(self.browser.current_url, self.live_server_url + "/pokemon/pokedex/")

    def test_logo_redirect_home(self):

        self.browser.get(self.live_server_url)
        link = self.browser.find_element(By.CLASS_NAME, "logo-icon")
        link.click()

        self.assertEqual(self.browser.current_url, self.live_server_url + "/pokemon/")

    def test_active_hmtl(self):
        self.driver.get(self.live_server_url + "/")
        link = self.driver.find_element(By.CSS_SELECTOR, "a.home")
        assert "active" in link.get_attribute("class")
    
    
    # def test_404_page_navigation_works(self):   ##remember DEBUG = FALSE if testing, need to fix
    #     # Navigate to a page that does not exist
    #     self.browser.get(self.live_server_url + "/does-not-exist/")

    #     # Verify the custom 404 page is displayed
    #     self.assertIn("Page Not Found", self.browser.title)

    #     # Click the navigation link back to the homepage
    #     self.browser.find_element(
    #         By.LINK_TEXT, "Home"
    #     ).click()

    #     # Verify navigation succeeded
    #     self.assertEqual(
    #         self.browser.current_url,
    #         self.live_server_url + "/"
    #     )


