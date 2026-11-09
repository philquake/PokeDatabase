from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from pokemon.models import FormMove, Pokemon, PokemonForm
from pokemon.services.pokelance_client import (
    PokelanceAPIError,
    _fetch_forms,
    _to_fixture_entry,
    _to_form_entry,
    sync_pokemon_data,
)


def raw_form(slug="charizard-mega-x", pokeapi_id=10034, **overrides):
    """A PokéAPI pokemon resource for a form, trimmed to the fields the sync reads."""
    raw = {
        "id": pokeapi_id,
        "name": slug,
        "base_experience": 285,
        "height": 17,
        "weight": 1105,
        "sprites": {
            "front_default": "https://example.test/front.png",
            "other": {"official-artwork": {"front_default": "https://example.test/art.png"}},
        },
        "stats": [
            {"stat": {"name": "hp"}, "base_stat": 78, "effort": 0},
            {"stat": {"name": "attack"}, "base_stat": 130, "effort": 3},
            {"stat": {"name": "defense"}, "base_stat": 111, "effort": 0},
            {"stat": {"name": "special-attack"}, "base_stat": 130, "effort": 0},
            {"stat": {"name": "special-defense"}, "base_stat": 85, "effort": 0},
            {"stat": {"name": "speed"}, "base_stat": 100, "effort": 0},
        ],
        "types": [{"type": {"name": "fire"}}, {"type": {"name": "dragon"}}],
        "abilities": [{"ability": {"name": "tough-claws"}, "is_hidden": False}],
        "held_items": [],
        "moves": [],
    }
    raw.update(overrides)
    return raw


class ToFormEntryTest(SimpleTestCase):

    def test_builds_a_form_entry_from_a_pokemon_resource(self):
        entry = _to_form_entry("Charizard", "charizard", raw_form())

        self.assertEqual(entry, {
            "slug": "mega-x", "kind": "mega", "label": "Mega Charizard X", "pokeapi_id": 10034,
            "image": "https://example.test/art.png",
            "types": ["Fire", "Dragon"],
            "base_stats": {"HP": 78, "Attack": 130, "Defense": 111, "Special Attack": 130,
                           "Special Defense": 85, "Speed": 100},
            "stat_total": 634,
            "abilities": [{"name": "Tough Claws", "hidden": False}],
            "height_m": 1.7, "weight_kg": 110.5, "base_experience": 285,
            "ev_yield": {"Attack": 3}, "held_items": [], "moves": [],
        })

    def test_falls_back_to_the_plain_sprite_when_there_is_no_official_artwork(self):
        raw = raw_form(sprites={"front_default": "https://example.test/front.png",
                                "other": {"official-artwork": {"front_default": None}}})
        self.assertEqual(_to_form_entry("Charizard", "charizard", raw)["image"], "https://example.test/front.png")

    def test_image_is_empty_when_nothing_is_available(self):
        raw = raw_form(sprites={"front_default": None, "other": {}})
        self.assertEqual(_to_form_entry("Charizard", "charizard", raw)["image"], "")

    def test_flattens_the_forms_own_moves(self):
        raw = raw_form("rattata-alola", 10091, moves=[{
            "move": {"name": "quick-attack"},
            "version_group_details": [{
                "version_group": {"name": "sun-moon"}, "level_learned_at": 1,
                "move_learn_method": {"name": "level-up"},
            }],
        }])
        entry = _to_form_entry("Rattata", "rattata", raw)

        self.assertEqual(entry["moves"], [
            {"name": "Quick Attack", "version": "sun-moon", "level_learnt": 1, "method": "level-up"},
        ])

    def test_malformed_payload_is_a_pokelance_error(self):
        with self.assertRaises(PokelanceAPIError):
            _to_form_entry("Charizard", "charizard", raw_form(stats=None))


VARIETIES = {
    "name": "charizard",
    "varieties": [
        {"is_default": True, "pokemon": {"name": "charizard", "url": "https://pokeapi.co/api/v2/pokemon/6/"}},
        {"is_default": False, "pokemon": {"name": "charizard-gmax", "url": "https://pokeapi.co/api/v2/pokemon/10196/"}},
        {"is_default": False, "pokemon": {"name": "charizard-mega-x", "url": "https://pokeapi.co/api/v2/pokemon/10034/"}},
    ],
}


def fake_get(url, context):
    if url.endswith("/10034/"):
        return raw_form()
    if url.endswith("/10196/"):
        return raw_form("charizard-gmax", 10196, types=[{"type": {"name": "fire"}}, {"type": {"name": "flying"}}])
    raise AssertionError(f"unexpected fetch {url}")


class FetchFormsTest(SimpleTestCase):

    @patch("pokemon.services.pokelance_client._get", side_effect=fake_get)
    def test_fetches_every_non_default_variety_ordered_by_id(self, mock_get):
        forms = _fetch_forms(VARIETIES, "Charizard")

        self.assertEqual([f["slug"] for f in forms], ["mega-x", "gmax"])
        self.assertEqual([f["kind"] for f in forms], ["mega", "gmax"])
        self.assertEqual(forms[1]["types"], ["Fire", "Flying"])
        fetched = sorted(call.args[0] for call in mock_get.call_args_list)
        self.assertEqual(len(fetched), 2)          # the default form is not fetched again

    @patch("pokemon.services.pokelance_client._get")
    def test_a_species_with_one_variety_makes_no_requests(self, mock_get):
        species = {"name": "ditto", "varieties": [
            {"is_default": True, "pokemon": {"name": "ditto", "url": "https://pokeapi.co/api/v2/pokemon/132/"}},
        ]}
        self.assertEqual(_fetch_forms(species, "Ditto"), [])
        mock_get.assert_not_called()

    @patch("pokemon.services.pokelance_client._get")
    def test_a_payload_without_varieties_is_fine(self, mock_get):
        self.assertEqual(_fetch_forms({"name": "dummy-species"}, "Dummy"), [])
        mock_get.assert_not_called()

    @patch("pokemon.services.pokelance_client._get", side_effect=PokelanceAPIError("down"))
    def test_an_api_failure_propagates(self, mock_get):
        with self.assertRaises(PokelanceAPIError):
            _fetch_forms(VARIETIES, "Charizard")


class FixtureEntryFormsTest(SimpleTestCase):

    RAW = {
        "id": 6, "name": "charizard", "base_experience": 240, "height": 17, "weight": 905,
        "sprites": {"other": {"official-artwork": {"front_default": "https://example.test/6.png"}}},
        "stats": [{"stat": {"name": "hp"}, "base_stat": 78}],
        "types": [{"type": {"name": "fire"}}], "abilities": [], "moves": [],
    }
    SPECIES = {"genera": [], "generation": {"name": "generation-i"}, "gender_rate": 1,
               "egg_groups": [], "capture_rate": 45, "base_happiness": 70}

    def entry(self, **kw):
        return _to_fixture_entry(self.RAW, self.SPECIES, ["Charizard"], {}, [], **kw)

    def test_forms_are_included(self):
        forms = [{"slug": "gmax"}]
        self.assertEqual(self.entry(forms=forms)["forms"], forms)

    def test_forms_default_to_an_empty_list(self):
        self.assertEqual(self.entry()["forms"], [])


class SyncFormsEndToEndTest(TestCase):
    """The whole pipeline with only the HTTP-level fetches mocked: forms arrive in the database."""

    def run_sync(self, **kw):
        base = raw_form("charizard", 6, types=[{"type": {"name": "fire"}}, {"type": {"name": "flying"}}])
        with patch("pokemon.services.pokelance_client._fetch_pokemon", return_value=base), \
             patch("pokemon.services.pokelance_client._fetch_species", return_value={
                 **FixtureEntryFormsTest.SPECIES, **VARIETIES}), \
             patch("pokemon.services.pokelance_client._fetch_evolution_chain", return_value=["Charizard"]), \
             patch("pokemon.services.pokelance_client._fetch_type_matchups", return_value={}), \
             patch("pokemon.services.pokelance_client._fetch_locations", return_value=[]), \
             patch("pokemon.services.pokelance_client._get", side_effect=fake_get):
            return sync_pokemon_data(**kw)

    def test_new_pokemon_are_saved_with_their_forms(self):
        result = self.run_sync(count=1, update_existing=False)

        self.assertEqual(len(result["added"]), 1)
        pokemon = Pokemon.objects.get()
        self.assertEqual(list(pokemon.forms.values_list("slug", flat=True)), ["mega-x", "gmax"])
        self.assertEqual(pokemon.forms.get(slug="mega-x").stat_total, 634)

    def test_the_update_pass_backfills_forms_for_pokemon_stored_before_forms_existed(self):
        self.run_sync(count=1, update_existing=False)
        PokemonForm.objects.all().delete()                 # as if stored by an older sync

        result = self.run_sync(count=0, update_existing=True)

        self.assertEqual([p["name"] for p in result["updated"]], ["Charizard"])
        self.assertEqual(PokemonForm.objects.count(), 2)

    def test_a_second_update_pass_changes_nothing(self):
        self.run_sync(count=1, update_existing=False)
        result = self.run_sync(count=0, update_existing=True)
        self.assertEqual(result["updated"], [])
