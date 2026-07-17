import json
from urllib import request, error

BASE_URL = "https://pokeapi.co/api/v2/"


def get_pokemon(name):
    try:
        with request.urlopen(f"{BASE_URL}pokemon/{name.lower()}") as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except (error.HTTPError, error.URLError):
        return None

    return None

