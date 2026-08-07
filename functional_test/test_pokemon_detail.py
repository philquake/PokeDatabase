from urllib import response

from django.test import LiveServerTestCase
from pathlib import Path
import json

class ID_Test(LiveServerTestCase):

    def test_valid_pokemon(self):
        response = self.client.get("/pokemon/Gengar/")
        self.assertEqual(response.status_code, 200)
        pokemon = response.context["pokemon"]
        self.assertEqual(pokemon["pokedex_number"], 94)
        self.assertEqual(pokemon["name"], "Gengar")

    def test_invalid_pokemon(self):
        # A name in the URL that shouldn't match
        response = self.client.get("/pokemon/not-a-pokemon/")
        self.assertEqual(response.status_code, 404)

    # if pokemon["name"].lower() == name.lower():