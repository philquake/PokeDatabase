from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from pokemon.models import Move, Pokemon, PokemonMove
from pokemon.services.pokelance_client import (
    PokelanceAPIError,
    _move_display_name,
    _to_move_entry,
    sync_move_data,
)


def raw_move(slug="flamethrower", **overrides):
    raw = {
        "name": slug,
        "type": {"name": "fire"},
        "damage_class": {"name": "special"},
        "power": 90,
        "accuracy": 100,
        "pp": 15,
        "effect_chance": 10,
        "generation": {"name": "generation-i"},
        "effect_entries": [
            {"language": {"name": "de"}, "short_effect": "Verursacht Schaden."},
            {"language": {"name": "en"},
             "short_effect": "Inflicts regular damage. Has a $effect_chance% chance to burn the target."},
        ],
    }
    raw.update(overrides)
    return raw


class MoveDisplayNameTest(SimpleTestCase):

    def test_matches_the_names_stored_on_pokemon_moves(self):
        self.assertEqual(_move_display_name("solar-beam"), "Solar Beam")
        self.assertEqual(_move_display_name("double-edge"), "Double Edge")


class ToMoveEntryTest(SimpleTestCase):

    def test_flattens_a_pokeapi_move(self):
        self.assertEqual(_to_move_entry(raw_move()), {
            "name": "Flamethrower", "type": "Fire", "damage_class": "special",
            "power": 90, "accuracy": 100, "pp": 15, "generation": 1,
            "effect": "Inflicts regular damage. Has a 10% chance to burn the target.",
        })

    def test_status_move_keeps_missing_power_and_accuracy_as_none(self):
        entry = _to_move_entry(raw_move(
            "swords-dance", damage_class={"name": "status"}, power=None, accuracy=None, effect_chance=None,
            effect_entries=[{"language": {"name": "en"}, "short_effect": "Raises the user's Attack by two stages."}],
        ))
        self.assertIsNone(entry["power"])
        self.assertIsNone(entry["accuracy"])
        self.assertEqual(entry["damage_class"], "status")

    def test_missing_english_effect_gives_empty_text(self):
        self.assertEqual(_to_move_entry(raw_move(effect_entries=[]))["effect"], "")

    def test_unknown_generation_raises(self):
        with self.assertRaises(PokelanceAPIError):
            _to_move_entry(raw_move(generation={"name": "generation-x"}))


MOVE_LIST = {"results": [
    {"name": "tackle", "url": "https://pokeapi.co/api/v2/move/33/"},
    {"name": "flamethrower", "url": "https://pokeapi.co/api/v2/move/53/"},
]}


def fake_get(url, context):
    if "limit=" in url:
        return MOVE_LIST
    if url.endswith("/33/"):
        return raw_move("tackle", type={"name": "normal"}, damage_class={"name": "physical"},
                        power=40, pp=35, effect_chance=None,
                        effect_entries=[{"language": {"name": "en"}, "short_effect": "Inflicts regular damage."}])
    return raw_move()


@patch("pokemon.services.pokelance_client._get", side_effect=fake_get)
class SyncMoveDataTest(TestCase):

    def test_adds_every_move_from_the_list(self, mock_get):
        result = sync_move_data()

        self.assertEqual([m["name"] for m in result["added"]], ["Tackle", "Flamethrower"])
        self.assertEqual(result["updated"], [])
        self.assertEqual(Move.objects.count(), 2)
        self.assertEqual(Move.objects.get(name="Tackle").damage_class, "physical")

    def test_skips_stored_moves_unless_refreshing(self, mock_get):
        Move.objects.create(name="Tackle", type="Normal", damage_class="physical")

        result = sync_move_data()
        self.assertEqual([m["name"] for m in result["added"]], ["Flamethrower"])
        self.assertEqual(Move.objects.get(name="Tackle").power, None)  # untouched

        result = sync_move_data(refresh=True)
        self.assertEqual([m["name"] for m in result["updated"]], ["Tackle"])
        self.assertEqual(Move.objects.get(name="Tackle").power, 40)

    def test_refresh_ignores_moves_that_have_not_changed(self, mock_get):
        sync_move_data()
        self.assertEqual(sync_move_data(refresh=True), {"added": [], "updated": []})

    def test_only_known_fetches_just_moves_some_pokemon_learns(self, mock_get):
        pokemon = Pokemon.objects.create(pokedex_number=4, name="Charmander")
        PokemonMove.objects.create(pokemon=pokemon, name="Flamethrower", version="red-blue", method="machine")

        result = sync_move_data(only_known=True)

        self.assertEqual([m["name"] for m in result["added"]], ["Flamethrower"])
        fetched = [call.args[0] for call in mock_get.call_args_list]
        self.assertNotIn("https://pokeapi.co/api/v2/move/33/", fetched)

    def test_a_failure_keeps_the_moves_saved_before_it(self, mock_get):
        def flaky(url, context):
            if url.endswith("/53/"):
                raise PokelanceAPIError("boom")
            return fake_get(url, context)
        mock_get.side_effect = flaky

        with self.assertRaises(PokelanceAPIError):
            sync_move_data()

        self.assertEqual(list(Move.objects.values_list("name", flat=True)), ["Tackle"])
