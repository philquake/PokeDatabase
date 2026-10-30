from django.core.management.base import BaseCommand, CommandError

from pokemon.services.pokelance_client import PokelanceAPIError, sync_ability_data


class Command(BaseCommand):
    help = "Sync ability effect text from PokéAPI into the database (one request per ability)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-known", action="store_true",
            help="Only abilities that a stored Pokémon has (much faster than every ability)",
        )
        parser.add_argument(
            "--refresh", action="store_true",
            help="Re-fetch abilities already stored and patch any that changed",
        )

    def handle(self, *args, **options):
        try:
            result = sync_ability_data(only_known=options["only_known"], refresh=options["refresh"])
        except PokelanceAPIError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Added {len(result['added'])} abilities, updated {len(result['updated'])}"
        ))
