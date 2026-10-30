from django.core.management.base import BaseCommand

from pokemon.services.data import FIXTURE_PATH, import_pokemon_json


class Command(BaseCommand):
    help = "Load (or refresh) Pokémon from a fixture-shaped JSON file into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "path", nargs="?", default=str(FIXTURE_PATH),
            help="JSON file to import (default: assets/static/fixtures/pokemon.json)",
        )

    def handle(self, *args, **options):
        imported = import_pokemon_json(options["path"])
        self.stdout.write(self.style.SUCCESS(f"Imported {imported} Pokémon from {options['path']}"))
