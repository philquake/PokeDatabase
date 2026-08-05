from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By


class NewUserTest(LiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.driver = webdriver.Chrome()

    def tearDown(self):
        self.driver.quit()
        super().tearDown()

    def test_correct_template(self):
        self.driver.get(self.live_server_url + "/")
        self.assertIn("Home", self.driver.title)
        header_text = self.driver.find_element(By.TAG_NAME, "h1").text
        self.assertIn("Search Pokemon", header_text)

    def navigation_bar_links(self):
        self.driver.get(self.live_server_url + "/")
        nav_links = self.driver.find_elements(By.CSS_SELECTOR, "nav a")
        link_texts = [link.text for link in nav_links]
        expected_links = ["Home", "Pokemon", "Types", "Abilities", "Moves", "Regions"]
        self.assertEqual(link_texts, expected_links)
