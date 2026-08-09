from django.test import LiveServerTestCase, SimpleTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By


class HomePageTest(SimpleTestCase):
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")

class TemplateTest(LiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.driver = webdriver.Chrome()

    def tearDown(self):
        self.driver.quit()
        super().tearDown()

    def test_correct_template(self):
        self.driver.get(self.live_server_url)
        self.assertIn("Home", self.driver.title)
        paragraph = self.driver.find_element(By.CLASS_NAME, "hero-subtitle")
        self.assertIn("Search Pokémon", paragraph.text)

class NavigationBarTest(LiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.driver = webdriver.Chrome()

    def tearDown(self):
        self.driver.quit()
        super().tearDown()

    def test_navigation_bar_links(self):
        self.driver.get(self.live_server_url + "/")
        nav_links = self.driver.find_elements(By.CSS_SELECTOR, "nav a")
        link_texts = [link.text for link in nav_links]
        expected_links = ["PokeDatabase", "Home", "Pokédex", "Types", "Region", "Abilities", "Moves", "Competitive"]
        self.assertEqual(link_texts, expected_links)

class searchBarTest(LiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.driver = webdriver.Chrome()

    def tearDown(self):
        self.driver.quit()
        super().tearDown()

    def test_search_bar_present(self):
        self.driver.get(self.live_server_url + "/")
        search_bar = self.driver.find_element(By.CSS_SELECTOR, "form[method='GET']")
        self.assertIsNotNone(search_bar)

class HomeLinkActive(LiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.driver = webdriver.Chrome()
        
    def tearDown(self):
        self.driver.quit()
        super().tearDown()
        
    def test_active_hmtl(self):
        self.driver.get(self.live_server_url + "/")
        link = self.driver.find_element(By.CSS_SELECTOR, "a")
        assert link.get_attribute("class").find("active") != -1