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
        header_text = self.driver.find_element(By.TAG_NAME, "h1").text
        self.assertIn("Search Pokemon", header_text)

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
        expected_links = ["Home", "Pokédex", "Types", "Abilities", "Moves", "Regions"]
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
