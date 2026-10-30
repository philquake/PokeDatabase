from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from pokemon.models import Ability, Pokemon
from pokemon.services.pokelance_client import PokelanceAPIError, _to_ability_entry, sync_ability_data


def raw_ability(slug="solar-power", **overrides):
    raw = {
        "name": slug,
        "generation": {"name": "generation-iv"},
        "effect_entries": [
            {"language": {"name": "de"}, "short_effect": "Auf Deutsch."},
            {"language": {"name": "en"}, "short_effect": "Boosts Special Attack in sunlight."},
        ],
    }
    raw.update(overrides)
    return raw


class ToAbilityEntryTest(SimpleTestCase):

    def test_flattens_a_pokeapi_ability(self):
        self.assertEqual(_to_ability_entry(raw_ability()), {
            "name": "Solar Power", "generation": 4, "effect": "Boosts Special Attack in sunlight.",
        })

    def test_missing_english_effect_gives_empty_text(self):
        self.assertEqual(_to_ability_entry(raw_ability(effect_entries=[]))["effect"], "")

    def test_unknown_generation_raises(self):
        with self.assertRaises(PokelanceAPIError):
            _to_ability_entry(raw_ability(generation={"name": "generation-x"}))


ABILITY_LIST = {"results": [
    {"name": "stench", "url": "https://pokeapi.co/api/v2/ability/1/"},
    {"name": "solar-power", "url": "https://pokeapi.co/api/v2/ability/94/"},
]}


def fake_get(url, context):
    if "limit=" in url:
        return ABILITY_LIST
    if url.endswith("/1/"):
        return raw_ability("stench", generation={"name": "generation-iii"},
                           effect_entries=[{"language": {"name": "en"}, "short_effect": "May cause flinching."}])
    return raw_ability()


@patch("pokemon.services.pokelance_client._get", side_effect=fake_get)
class SyncAbilityDataTest(TestCase):

    def test_adds_every_ability_from_the_list(self, mock_get):
        result = sync_ability_data()

        self.assertEqual([a["name"] for a in result["added"]], ["Stench", "Solar Power"])
        self.assertEqual(Ability.objects.get(name="Stench").generation, 3)

    def test_skips_stored_abilities_unless_refreshing(self, mock_get):
        Ability.objects.create(name="Stench", generation=3, effect="old")

        self.assertEqual([a["name"] for a in sync_ability_data()["added"]], ["Solar Power"])
        self.assertEqual(Ability.objects.get(name="Stench").effect, "old")

        self.assertEqual([a["name"] for a in sync_ability_data(refresh=True)["updated"]], ["Stench"])
        self.assertEqual(Ability.objects.get(name="Stench").effect, "May cause flinching.")

    def test_only_known_fetches_abilities_some_pokemon_has(self, mock_get):
        Pokemon.objects.create(
            pokedex_number=1, name="Bulbasaur",
            abilities=[{"name": "Solar Power", "hidden": True}],
        )

        result = sync_ability_data(only_known=True)

        self.assertEqual([a["name"] for a in result["added"]], ["Solar Power"])
