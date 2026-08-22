"""
Functional tests for the admin-triggered Pokémon data sync feature.

ASSUMPTIONS (this feature does not exist in the codebase yet — these tests
document the intended contract per Phil's "test gaps vs. feature gaps"
convention, and are written TDD-style so they can drive the implementation):

  - There is a staff-only admin view named "admin_sync_pokemon" at
    /pokemon/admin/sync/ with a button of class "sync-button" that POSTs
    to trigger a sync.
  - The sync itself is performed by a function
    `pokemon.services.pokelance_client.sync_pokemon_data()` which calls
    out to the Pokelance API, and returns the list of newly added Pokémon
    on success or raises `pokemon.services.pokelance_client.PokelanceAPIError`
    on failure.
  - On success, the page re-renders with a success message in an element
    with class "sync-success" and the new Pokémon are persisted so they
    show up on the Pokédex page.
  - On failure, the page re-renders (200, not 500) with an error message
    in an element with class "sync-error", and the rest of the site
    continues to function normally.

Adjust the target patch path / URL name / CSS classes below once the real
implementation lands — the test bodies should not need to change otherwise.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class AdminSyncFunctionalTestBase(LiveServerTestCase):
    """Shared setup: a logged-in staff user with a session cookie in the browser."""

    def setUp(self):
        self.browser = webdriver.Chrome()
        self.admin_user = get_user_model().objects.create_superuser(
            username="poke_admin", email="admin@pokedatabase.test", password="testpass123"
        )
        self._log_admin_into_browser()

    def tearDown(self):
        self.browser.quit()

    def _log_admin_into_browser(self):
        # Log in via the Django test client to get a valid session, then
        # transfer that session cookie into the Selenium browser. The browser
        # must first visit the domain once before cookies can be set on it.
        self.client.login(username="poke_admin", password="testpass123")
        self.browser.get(self.live_server_url + "/does-not-exist/")

        session_cookie = self.client.cookies["sessionid"]
        self.browser.add_cookie({
            "name": "sessionid",
            "value": session_cookie.value,
            "path": "/",
        })
        self.browser.refresh()


class SyncSuccessTest(AdminSyncFunctionalTestBase):

    @patch("pokemon.services.pokelance_client.sync_pokemon_data")
    def test_admin_sync_adds_new_pokemon_to_catalog(self, mock_sync):
        mock_sync.return_value = [
            {
                "pokedex_number": 1000,
                "name": "Testmon",
                "image": "https://example.com/testmon.png",
                "types": ["Normal"],
                "base_stats": {
                    "HP": 50, "Attack": 50, "Defense": 50,
                    "Special Attack": 50, "Special Defense": 50, "Speed": 50,
                },
                "abilities": [{"name": "Placeholder", "hidden": False}],
            }
        ]

        self.browser.get(self.live_server_url + reverse("admin_sync_pokemon"))
        self.browser.find_element(By.CLASS_NAME, "sync-button").click()

        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "sync-success"))
        )

        self.browser.get(self.live_server_url + reverse("pokedex"))
        self.assertIn("Testmon", self.browser.page_source)


class SyncFailureTest(AdminSyncFunctionalTestBase):

    @patch("pokemon.services.pokelance_client.sync_pokemon_data")
    def test_admin_sync_shows_error_when_external_api_is_down(self, mock_sync):
        from pokemon.services.pokelance_client import PokelanceAPIError
        mock_sync.side_effect = PokelanceAPIError("Pokelance API unreachable")

        self.browser.get(self.live_server_url + reverse("admin_sync_pokemon"))
        self.browser.find_element(By.CLASS_NAME, "sync-button").click()

        error_message = WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "sync-error"))
        )
        self.assertIn("Pokelance", error_message.text)

    @patch("pokemon.services.pokelance_client.sync_pokemon_data")
    def test_site_still_works_after_a_failed_sync(self, mock_sync):
        from pokemon.services.pokelance_client import PokelanceAPIError
        mock_sync.side_effect = PokelanceAPIError("Pokelance API unreachable")

        self.browser.get(self.live_server_url + reverse("admin_sync_pokemon"))
        self.browser.find_element(By.CLASS_NAME, "sync-button").click()

        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "sync-error"))
        )

        # The rest of the site should be unaffected by the failed sync.
        self.browser.get(self.live_server_url + reverse("home"))
        body = self.browser.find_element(By.TAG_NAME, "body")
        self.assertTrue(body.is_displayed())