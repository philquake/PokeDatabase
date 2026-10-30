from django.core.management.base import BaseCommand, CommandError

from pokemon.services.pokelance_client import PokelanceAPIError, sync_move_data


class Command(BaseCommand):
    help = (
        "Sync move stats (type, physical/special/status, power, accuracy, PP, effect) "
        "from PokéAPI into the database. Fetches one request per move, so run it "
        "from the command line rather than the admin."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-known", action="store_true",
            help="Only moves that a stored Pokémon learns (much faster than every move)",
        )
        parser.add_argument(
            "--refresh", action="store_true",
            help="Re-fetch moves already stored and patch any that changed",
        )

    def handle(self, *args, **options):
        try:
            result = sync_move_data(only_known=options["only_known"], refresh=options["refresh"])
        except PokelanceAPIError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Added {len(result['added'])} moves, updated {len(result['updated'])}"
        ))
