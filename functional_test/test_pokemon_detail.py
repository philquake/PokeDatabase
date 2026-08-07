from urllib import response

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver



class ID_Test(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

    def test_valid_pokemon(self):
        self.browser.get(self.live_server_url + "/pokemon/Gengar/")
        self.assertIn("Gengar", self.browser.page_source)

    def test_invalid_pokemon(self):
        # A name in the URL that shouldn't match
        self.browser.get(self.live_server_url + "/pokemon/not_a_pokemon/")
        self.assertIn("Not Found", self.browser.page_source)

    def test_user_can_view_img(self):
        self.browser.get(self.live_server_url + "/pokemon/Gengar/")
        image = self.browser.find_element(By.CLASS_NAME, "pokemon-detail-img")
        self.assertTrue(image.is_displayed())

    def test_user_can_view_details(self):
        self.browser.get(self.live_server_url + "/pokemon/Gengar")
        self.assertIn("Ghost", self.browser.page_source)
        self.assertIn("Poison", self.browser.page_source)


    # if pokemon["name"].lower() == name.lower():