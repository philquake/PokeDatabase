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
