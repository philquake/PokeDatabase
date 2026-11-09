from django.db import IntegrityError, transaction
from django.test import TestCase

from pokemon.models import FormMove, Pokemon, PokemonForm
from pokemon.services.data import pokemon_to_dict, save_pokemon_entry


def mega_x(**overrides):
    form = {
        "slug": "mega-x", "pokeapi_id": 10034, "kind": "mega", "label": "Mega Charizard X",
        "image": "https://example.test/mega-x.png", "types": ["Fire", "Dragon"],
        "base_stats": {"HP": 78, "Attack": 130, "Defense": 111, "Special Attack": 130,
                       "Special Defense": 85, "Speed": 100},
        "stat_total": 634,
        "abilities": [{"name": "Tough Claws", "hidden": False}],
        "height_m": 1.7, "weight_kg": 110.5, "base_experience": 285,
        "ev_yield": {"Attack": 3}, "held_items": [],
        "moves": [],
    }
    form.update(overrides)
    return form


def gmax(**overrides):
    return mega_x(slug="gmax", pokeapi_id=10196, kind="gmax", label="Gigantamax Charizard", **overrides)


def charizard(forms=None, **overrides):
    entry = {"pokedex_number": 6, "name": "Charizard", "types": ["Fire", "Flying"], "generation": 1}
    if forms is not None:
        entry["forms"] = forms
    entry.update(overrides)
    return entry


class PokemonFormModelTest(TestCase):

    def setUp(self):
        self.pokemon = Pokemon.objects.create(pokedex_number=6, name="Charizard")

    def make(self, slug="mega-x", pokeapi_id=10034, **kw):
        return PokemonForm.objects.create(
            pokemon=self.pokemon, slug=slug, pokeapi_id=pokeapi_id, kind="mega", label="Mega Charizard X", **kw
        )

    def test_str_is_the_label(self):
        self.assertEqual(str(self.make()), "Mega Charizard X")

    def test_forms_are_ordered_by_pokeapi_id(self):
        self.make("gmax", 10196)
        self.make("mega-x", 10034)
        self.assertEqual(list(self.pokemon.forms.values_list("slug", flat=True)), ["mega-x", "gmax"])

    def test_slug_is_unique_within_a_pokemon(self):
        self.make("mega-x", 10034)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make("mega-x", 10999)

    def test_pokeapi_id_is_unique(self):
        self.make("mega-x", 10034)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make("mega-y", 10034)

    def test_deleting_the_pokemon_deletes_its_forms_and_their_moves(self):
        form = self.make()
        FormMove.objects.create(form=form, name="Tackle", version="red-blue", method="level-up")
        self.pokemon.delete()
        self.assertEqual(PokemonForm.objects.count(), 0)
        self.assertEqual(FormMove.objects.count(), 0)


class SaveFormsTest(TestCase):

    def test_creates_forms_with_their_data(self):
        save_pokemon_entry(charizard([mega_x()]))

        form = PokemonForm.objects.get()
        self.assertEqual(form.pokemon.name, "Charizard")
        self.assertEqual((form.slug, form.kind, form.label), ("mega-x", "mega", "Mega Charizard X"))
        self.assertEqual(form.types, ["Fire", "Dragon"])
        self.assertEqual(form.base_stats["Attack"], 130)
        self.assertEqual(form.stat_total, 634)
        self.assertEqual(form.abilities, [{"name": "Tough Claws", "hidden": False}])
        self.assertEqual(form.ev_yield, {"Attack": 3})

    def test_saves_a_forms_own_moves(self):
        moves = [
            {"name": "Flare Blitz", "version": "sword-shield", "level_learnt": 0, "method": "tutor"},
            {"name": "Ember", "version": "sword-shield", "level_learnt": 1, "method": "level-up"},
        ]
        save_pokemon_entry(charizard([mega_x(moves=moves)]))

        self.assertEqual(
            list(FormMove.objects.values_list("name", "method")),
            [("Flare Blitz", "tutor"), ("Ember", "level-up")],
        )

    def test_forms_key_replaces_the_set(self):
        save_pokemon_entry(charizard([mega_x(), gmax()]))
        save_pokemon_entry(charizard([mega_x()]))

        self.assertEqual(list(PokemonForm.objects.values_list("slug", flat=True)), ["mega-x"])

    def test_an_existing_form_is_updated_in_place_by_slug(self):
        save_pokemon_entry(charizard([mega_x()]))
        pk = PokemonForm.objects.get().pk
        save_pokemon_entry(charizard([mega_x(label="Mega Charizard X (updated)", stat_total=640)]))

        form = PokemonForm.objects.get()
        self.assertEqual(form.pk, pk)
        self.assertEqual((form.label, form.stat_total), ("Mega Charizard X (updated)", 640))

    def test_form_moves_are_replaced_when_the_key_is_present_and_kept_when_not(self):
        move = {"name": "Ember", "version": "red-blue", "level_learnt": 1, "method": "level-up"}
        save_pokemon_entry(charizard([mega_x(moves=[move])]))

        without_moves_key = mega_x()
        del without_moves_key["moves"]
        save_pokemon_entry(charizard([without_moves_key]))
        self.assertEqual(FormMove.objects.count(), 1)

        save_pokemon_entry(charizard([mega_x(moves=[])]))
        self.assertEqual(FormMove.objects.count(), 0)

    def test_entry_without_a_forms_key_leaves_forms_alone(self):
        save_pokemon_entry(charizard([mega_x()]))
        save_pokemon_entry(charizard(types=["Fire", "Flying"]))
        self.assertEqual(PokemonForm.objects.count(), 1)

    def test_an_empty_forms_list_clears_them(self):
        save_pokemon_entry(charizard([mega_x()]))
        save_pokemon_entry(charizard([]))
        self.assertEqual(PokemonForm.objects.count(), 0)


class PokemonToDictFormsTest(TestCase):

    def test_related_dict_includes_forms_with_their_moves(self):
        move = {"name": "Ember", "version": "red-blue", "level_learnt": 1, "method": "level-up"}
        save_pokemon_entry(charizard([mega_x(moves=[move])]))

        data = pokemon_to_dict(Pokemon.objects.get(), include_related=True)

        self.assertEqual(data["forms"], [mega_x(moves=[move])])

    def test_plain_dict_has_no_forms_key(self):
        save_pokemon_entry(charizard([mega_x()]))
        self.assertNotIn("forms", pokemon_to_dict(Pokemon.objects.get()))
