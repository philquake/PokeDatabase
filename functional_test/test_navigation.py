from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium import webdriver

class Navigation_Links(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def tearDown(self):
        self.browser.quit()

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


