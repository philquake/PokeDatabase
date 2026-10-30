from django.core.management.base import BaseCommand, CommandError

from pokemon.services.pokelance_client import PokelanceAPIError, sync_pokemon_data


class Command(BaseCommand):
    help = (
        "Sync Pokémon from PokéAPI into the database. Use this instead of the "
        "admin sync page for big syncs, which would time out in a web request."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=5, help="How many new Pokémon to add (default: 5)")
        parser.add_argument(
            "--no-update", action="store_true",
            help="Only add new Pokémon; skip re-checking the ones already stored",
        )

    def handle(self, *args, **options):
        try:
            result = sync_pokemon_data(
                count=options["count"], update_existing=not options["no_update"]
            )
        except PokelanceAPIError as exc:
            raise CommandError(str(exc)) from exc

        added = ", ".join(p["name"] for p in result["added"]) or "none"
        updated = ", ".join(p["name"] for p in result["updated"]) or "none"
        self.stdout.write(self.style.SUCCESS(f"Added: {added}\nUpdated: {updated}"))
