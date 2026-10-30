from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from pokemon.models import Move
from pokemon.services.data import get_move_info, move_to_dict, save_move_entry
from pokemon.services.pokelance_client import PokelanceAPIError
from pokemon.tests.helpers import SAMPLE_MOVES_PATH, PokemonDataTestCase

FLAMETHROWER = {
    "name": "Flamethrower", "type": "Fire", "damage_class": "special",
    "power": 90, "accuracy": 100, "pp": 15, "generation": 1,
    "effect": "Inflicts regular damage. Has a 10% chance to burn the target.",
}


class MoveModelTest(TestCase):

    def test_str_is_the_move_name(self):
        self.assertEqual(str(Move(name="Tackle")), "Tackle")

    def test_moves_are_ordered_by_name(self):
        Move.objects.create(name="Surf", type="Water", damage_class="special")
        Move.objects.create(name="Cut", type="Normal", damage_class="physical")
        self.assertEqual(list(Move.objects.values_list("name", flat=True)), ["Cut", "Surf"])

    def test_power_accuracy_and_pp_can_be_missing(self):
        move = Move.objects.create(name="Swords Dance", type="Normal", damage_class="status")
        move.refresh_from_db()
        self.assertIsNone(move.power)
        self.assertIsNone(move.accuracy)


class SaveMoveEntryTest(TestCase):

    def test_creates_a_move(self):
        save_move_entry(FLAMETHROWER)
        self.assertEqual(move_to_dict(Move.objects.get(name="Flamethrower")), FLAMETHROWER)

    def test_updates_an_existing_move_by_name(self):
        save_move_entry(FLAMETHROWER)
        save_move_entry({**FLAMETHROWER, "power": 95})
        self.assertEqual(Move.objects.count(), 1)
        self.assertEqual(Move.objects.get().power, 95)

    def test_only_writes_keys_present(self):
        save_move_entry(FLAMETHROWER)
        save_move_entry({"name": "Flamethrower", "pp": 20})
        move = Move.objects.get()
        self.assertEqual(move.pp, 20)
        self.assertEqual(move.type, "Fire")


class GetMoveInfoTest(PokemonDataTestCase):

    def test_returns_a_dict_keyed_by_name_and_skips_unknown_moves(self):
        info = get_move_info(["Flamethrower", "Growl", "Not A Real Move"])
        self.assertEqual(set(info), {"Flamethrower", "Growl"})
        self.assertEqual(info["Flamethrower"]["type"], "Fire")
        self.assertEqual(info["Growl"]["damage_class"], "status")
        self.assertIsNone(info["Growl"]["power"])


class ImportMovesCommandTest(TestCase):

    def test_import_moves_command(self):
        out = StringIO()
        call_command("import_moves_json", str(SAMPLE_MOVES_PATH), stdout=out)

        self.assertIn("Imported 14 moves", out.getvalue())
        self.assertEqual(Move.objects.count(), 14)


class SyncMovesCommandTest(TestCase):

    @patch("pokemon.management.commands.sync_moves.sync_move_data")
    def test_passes_options_and_reports_result(self, mock_sync):
        mock_sync.return_value = {"added": [{"name": "Tackle"}, {"name": "Growl"}], "updated": [{"name": "Cut"}]}
        out = StringIO()

        call_command("sync_moves", "--only-known", "--refresh", stdout=out)

        mock_sync.assert_called_once_with(only_known=True, refresh=True)
        self.assertIn("Added 2 moves", out.getvalue())
        self.assertIn("updated 1", out.getvalue())

    @patch("pokemon.management.commands.sync_moves.sync_move_data")
    def test_defaults_fetch_everything_without_refreshing(self, mock_sync):
        mock_sync.return_value = {"added": [], "updated": []}
        call_command("sync_moves", stdout=StringIO())
        mock_sync.assert_called_once_with(only_known=False, refresh=False)

    @patch("pokemon.management.commands.sync_moves.sync_move_data", side_effect=PokelanceAPIError("down"))
    def test_api_failure_becomes_a_command_error(self, mock_sync):
        with self.assertRaises(CommandError):
            call_command("sync_moves", stdout=StringIO())
