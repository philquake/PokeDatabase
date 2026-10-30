from django.core.management.base import BaseCommand

from pokemon.services.data import import_moves_json


class Command(BaseCommand):
    help = "Load (or refresh) move stats from a JSON list of move dicts into the database."

    def add_arguments(self, parser):
        parser.add_argument("path", help="JSON file of moves (see pokemon/tests/fixtures/sample_moves.json)")

    def handle(self, *args, **options):
        imported = import_moves_json(options["path"])
        self.stdout.write(self.style.SUCCESS(f"Imported {imported} moves from {options['path']}"))
