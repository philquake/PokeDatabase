from django.core.management.base import BaseCommand, CommandError

from pokemon.services.pokelance_client import PokelanceAPIError, sync_item_data


class Command(BaseCommand):
    help = (
        "Sync items (name, category, cost, effect, sprite) from PokéAPI into the database. "
        "There are ~2,000 items, one request each; stored items are skipped, so re-running "
        "works through the rest."
    )

    def add_arguments(self, parser):
        parser.add_argument("--max", type=int, default=None, dest="max_count",
                            help="Fetch at most this many new items this run")
        parser.add_argument("--refresh", action="store_true",
                            help="Re-fetch items already stored and patch any that changed")

    def handle(self, *args, **options):
        try:
            result = sync_item_data(max_count=options["max_count"], refresh=options["refresh"])
        except PokelanceAPIError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Added {len(result['added'])} items, updated {len(result['updated'])}"
        ))
