from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from pokemon.models import Item
from pokemon.services.pokelance_client import PokelanceAPIError, _to_item_entry, sync_item_data


def raw_item(slug="potion", **overrides):
    raw = {
        "name": slug,
        "cost": 200,
        "category": {"name": "healing"},
        "sprites": {"default": "https://example.test/potion.png"},
        "effect_entries": [
            {"language": {"name": "de"}, "short_effect": "Auf Deutsch."},
            {"language": {"name": "en"}, "short_effect": "Restores 20 HP."},
        ],
    }
    raw.update(overrides)
    return raw


class ToItemEntryTest(SimpleTestCase):

    def test_flattens_a_pokeapi_item(self):
        self.assertEqual(_to_item_entry(raw_item()), {
            "name": "Potion", "category": "healing", "cost": 200,
            "effect": "Restores 20 HP.", "sprite": "https://example.test/potion.png",
        })

    def test_missing_sprite_and_effect_become_empty(self):
        entry = _to_item_entry(raw_item(sprites={"default": None}, effect_entries=[]))
        self.assertEqual(entry["sprite"], "")
        self.assertEqual(entry["effect"], "")

    def test_hyphenated_names_match_the_display_transform(self):
        self.assertEqual(_to_item_entry(raw_item("master-ball"))["name"], "Master Ball")


ITEM_LIST = {"results": [
    {"name": "master-ball", "url": "https://pokeapi.co/api/v2/item/1/"},
    {"name": "ultra-ball", "url": "https://pokeapi.co/api/v2/item/2/"},
    {"name": "great-ball", "url": "https://pokeapi.co/api/v2/item/3/"},
]}


def fake_get(url, context):
    if "limit=" in url:
        return ITEM_LIST
    slug = {"/1/": "master-ball", "/2/": "ultra-ball", "/3/": "great-ball"}[url[url.rindex("/", 0, -1):]]
    return raw_item(slug, category={"name": "standard-balls"})


@patch("pokemon.services.pokelance_client._get", side_effect=fake_get)
class SyncItemDataTest(TestCase):

    def test_adds_every_item(self, mock_get):
        result = sync_item_data()

        self.assertEqual([i["name"] for i in result["added"]], ["Master Ball", "Ultra Ball", "Great Ball"])
        self.assertEqual(Item.objects.get(name="Ultra Ball").category, "standard-balls")

    def test_max_count_stops_after_that_many(self, mock_get):
        result = sync_item_data(max_count=2)

        self.assertEqual(len(result["added"]), 2)
        self.assertEqual(Item.objects.count(), 2)

    def test_a_second_run_resumes_where_the_first_stopped(self, mock_get):
        sync_item_data(max_count=2)
        result = sync_item_data(max_count=2)

        self.assertEqual([i["name"] for i in result["added"]], ["Great Ball"])
        self.assertEqual(Item.objects.count(), 3)

    def test_refresh_patches_changed_items_only(self, mock_get):
        sync_item_data()
        Item.objects.filter(name="Master Ball").update(cost=999)

        result = sync_item_data(refresh=True)

        self.assertEqual([i["name"] for i in result["updated"]], ["Master Ball"])
        self.assertEqual(Item.objects.get(name="Master Ball").cost, 200)

    def test_a_failure_keeps_the_items_saved_before_it(self, mock_get):
        def flaky(url, context):
            if url.endswith("/2/"):
                raise PokelanceAPIError("boom")
            return fake_get(url, context)
        mock_get.side_effect = flaky

        with self.assertRaises(PokelanceAPIError):
            sync_item_data()

        self.assertEqual(list(Item.objects.values_list("name", flat=True)), ["Master Ball"])
