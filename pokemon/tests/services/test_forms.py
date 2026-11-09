from django.test import SimpleTestCase

from pokemon.services.forms import FORM_KINDS, classify_form


def classify(base, species, pokemon):
    return classify_form(base, species, pokemon)


class ClassifyFormTest(SimpleTestCase):

    def test_regional_forms(self):
        self.assertEqual(classify("Rattata", "rattata", "rattata-alola"),
                         {"slug": "alola", "kind": "regional", "label": "Alolan Rattata"})
        self.assertEqual(classify("Meowth", "meowth", "meowth-galar")["label"], "Galarian Meowth")
        self.assertEqual(classify("Voltorb", "voltorb", "voltorb-hisui")["label"], "Hisuian Voltorb")
        self.assertEqual(classify("Wooper", "wooper", "wooper-paldea")["label"], "Paldean Wooper")

    def test_regional_form_with_a_further_variant_keeps_it_in_brackets(self):
        form = classify("Tauros", "tauros", "tauros-paldea-combat-breed")
        self.assertEqual(form["slug"], "paldea-combat-breed")
        self.assertEqual(form["kind"], "regional")
        self.assertEqual(form["label"], "Paldean Tauros (Combat Breed)")

    def test_mega_forms_including_x_and_y(self):
        self.assertEqual(classify("Venusaur", "venusaur", "venusaur-mega"),
                         {"slug": "mega", "kind": "mega", "label": "Mega Venusaur"})
        self.assertEqual(classify("Charizard", "charizard", "charizard-mega-x")["label"], "Mega Charizard X")
        self.assertEqual(classify("Charizard", "charizard", "charizard-mega-y")["slug"], "mega-y")

    def test_primal_forms_group_with_megas(self):
        form = classify("Groudon", "groudon", "groudon-primal")
        self.assertEqual(form["kind"], "mega")
        self.assertEqual(form["label"], "Primal Groudon")

    def test_gigantamax_and_eternamax(self):
        self.assertEqual(classify("Charizard", "charizard", "charizard-gmax"),
                         {"slug": "gmax", "kind": "gmax", "label": "Gigantamax Charizard"})
        self.assertEqual(classify("Eternatus", "eternatus", "eternatus-eternamax")["kind"], "gmax")

    def test_everything_else_is_other_with_the_variant_in_brackets(self):
        form = classify("Deoxys", "deoxys", "deoxys-attack")
        self.assertEqual(form, {"slug": "attack", "kind": "other", "label": "Deoxys (Attack)"})
        self.assertEqual(classify("Toxtricity", "toxtricity", "toxtricity-low-key")["label"], "Toxtricity (Low Key)")

    def test_base_name_is_used_as_given_so_hyphenated_names_survive(self):
        form = classify("Mr-mime", "mr-mime", "mr-mime-galar")
        self.assertEqual(form["slug"], "galar")
        self.assertEqual(form["label"], "Galarian Mr-mime")

    def test_a_slug_that_does_not_start_with_the_species_still_classifies(self):
        form = classify("Foo", "foo", "bar-mega")
        self.assertEqual(form["slug"], "bar-mega")

    def test_kinds_are_listed_in_display_order(self):
        self.assertEqual([k for k, _ in FORM_KINDS], ["regional", "mega", "gmax", "other"])
