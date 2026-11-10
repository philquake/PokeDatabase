from django.test import SimpleTestCase
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch ###Makes you allows you to temporarily replace a target with a mock object
from django.test import RequestFactory
from django.http import Http404
from pokemon.views import pokemon_detail, calculate_stat_range, group_hm_tm_moves
from pokemon.services.pokelance_client import PokelanceAPIError
from pokemon.templatetags.pokemon_extras import get_item
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.template import Context, Template
from pokemon.models import Move, Pokemon, PokemonForm, PokemonMove
from pokemon.tests.helpers import PokemonDataTestCase




class PokemonDetailMovesTest(PokemonDataTestCase):

    def _charizard_rows(self):
        response = self.client.get(reverse("pokemon_detail", args=["Charizard"]))
        rows = [
            move
            for generation in response.context["move_generations"]
            for version in generation["versions"]
            for section in version["sections"]
            for move in section["moves"]
        ]
        return response, rows

    def test_move_rows_include_stored_stats(self):
        _, rows = self._charizard_rows()
        flamethrower = next(r for r in rows if r["name"] == "Flamethrower")

        self.assertEqual(flamethrower["type"], "Fire")
        self.assertEqual(flamethrower["damage_class"], "special")
        self.assertEqual(flamethrower["power"], 90)

    def test_moves_without_stats_are_still_listed(self):
        _, rows = self._charizard_rows()
        unknown = [r for r in rows if r["type"] is None]
        self.assertTrue(unknown)

    def test_moves_tab_shows_type_category_power_and_effect(self):
        response, _ = self._charizard_rows()

        self.assertContains(response, "move-type type-fire")
        self.assertContains(response, "move-cat-special")
        self.assertContains(response, "move-cat-status")
        self.assertContains(response, "Has a 10% chance to burn the target.")

    def test_missing_power_renders_as_a_dash_not_none(self):
        response, _ = self._charizard_rows()
        self.assertNotContains(response, ">None<")


class PokemonMovesFragmentTest(PokemonDataTestCase):

    def url(self, name="Charizard", version="red-blue"):
        return reverse("pokemon_moves_fragment", args=[name, version])

    def test_returns_just_the_move_tables_for_one_game(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Flamethrower")
        self.assertContains(response, "move-type type-fire")
        self.assertContains(response, "Level up")
        self.assertNotContains(response, "<html")

    def test_only_includes_moves_from_that_game(self):
        # Fire Blast is not learnable by Charizard in Red/Blue.
        response = self.client.get(self.url())
        sections = response.context["version"]["sections"]
        self.assertEqual(
            sum(len(s["moves"]) for s in sections),
            response.context["version"]["move_count"],
        )

    def test_name_lookup_is_case_insensitive(self):
        self.assertEqual(self.client.get(self.url("charizard")).status_code, 200)

    def test_unknown_pokemon_is_404(self):
        self.assertEqual(self.client.get(self.url("Missingno")).status_code, 404)

    def test_game_with_no_moves_is_404(self):
        self.assertEqual(self.client.get(self.url(version="not-a-game")).status_code, 404)


class PokemonDetailLazyMovesTest(PokemonDataTestCase):

    def test_only_the_visible_game_is_rendered_up_front(self):
        response = self.client.get(reverse("pokemon_detail", args=["Charizard"]))
        lazy = reverse("pokemon_moves_fragment", args=["Charizard", "red-blue"])
        visible = reverse("pokemon_moves_fragment", args=["Charizard", "scarlet-violet"])

        self.assertContains(response, f'data-src="{lazy}"')
        self.assertNotContains(response, f'data-src="{visible}"')


class PokemonDetailDefensesTest(PokemonDataTestCase):

    def cells(self, name):
        response = self.client.get(reverse("pokemon_detail", args=[name]))
        return response, {c["slug"]: c for c in response.context["type_defenses"]}

    def test_context_has_real_multipliers_including_quad_and_quarter(self):
        _, cells = self.cells("Charizard")

        self.assertEqual(len(cells), 18)
        self.assertEqual(cells["rock"]["multiplier"], 4)
        self.assertEqual(cells["grass"]["multiplier"], 0.25)
        self.assertEqual(cells["ground"]["multiplier"], 0)

    def test_grid_cells_link_to_type_pages_and_name_the_damage(self):
        response, _ = self.cells("Charizard")

        self.assertContains(response, f'href="{reverse("type_detail", args=["rock"])}"')
        self.assertContains(response, 'aria-label="Rock: takes 4\u00d7 damage"')
        self.assertContains(response, 'aria-label="Ground: takes 0\u00d7 damage"')
        self.assertContains(response, "defense-cell state-x4")
        self.assertContains(response, "defense-cell state-quarter")
        self.assertContains(response, "defense-cell state-immune")

    def test_boxes_use_the_same_mult_classes_as_the_types_page_chart(self):
        response, _ = self.cells("Charizard")

        for state in ("x4", "x2", "half", "quarter", "immune"):
            self.assertContains(response, f'class="mult mult-{state}"')

    def test_boxes_show_the_bare_multiplier_and_neutral_cells_are_blank(self):
        response, _ = self.cells("Charizard")
        html = response.content.decode()

        self.assertIn('class="mult mult-x4">4</span>', html)
        self.assertIn('class="mult mult-quarter">\u00bc</span>', html)
        self.assertIn('class="mult mult-immune">0</span>', html)
        self.assertIn('class="mult mult-x1"></span>', html)       # Ice: 1x, no label
        self.assertNotIn(">4\u00d7</span>\n          </a>", html)  # the multiplication sign lives only in aria-label

    def test_neutral_cells_still_say_1x_to_screen_readers(self):
        response, _ = self.cells("Kangaskhan")
        self.assertContains(response, 'aria-label="Fire: takes 1\u00d7 damage"')

    def test_chips_use_the_three_letter_abbreviations_with_full_names_on_hover(self):
        response, _ = self.cells("Charizard")

        self.assertContains(response, ">FIG</span>")
        self.assertContains(response, 'title="Fighting"')

    def test_there_is_no_key_under_the_defense_grid(self):
        response, _ = self.cells("Charizard")

        self.assertNotContains(response, "defense-legend")
        self.assertNotContains(response, "Chart key")

    def test_hero_weakness_chips_mark_quad_weaknesses(self):
        response, _ = self.cells("Charizard")
        self.assertContains(response, "weakness-quad")


class PokemonDetailPagerTest(PokemonDataTestCase):

    def get(self, name):
        return self.client.get(reverse("pokemon_detail", args=[name]))

    def test_both_links_show_image_number_and_name(self):
        response = self.get("Charmeleon")

        self.assertContains(response, 'rel="prev"')
        self.assertContains(response, 'rel="next"')
        self.assertContains(response, "#004")
        self.assertContains(response, "Charmander")
        self.assertContains(response, "#006")
        self.assertContains(response, "Charizard")
        self.assertContains(response, 'aria-label="Previous and next Pok')

    def test_existing_class_hooks_are_kept(self):
        response = self.get("Charmeleon")
        self.assertContains(response, 'class="pager-card previous"')
        self.assertContains(response, 'class="pager-card next"')

    def test_first_pokemon_has_only_a_next_link(self):
        response = self.get("Bulbasaur")

        self.assertNotContains(response, 'rel="prev"')
        self.assertContains(response, 'rel="next"')

    def test_last_pokemon_has_only_a_previous_link(self):
        response = self.get("Kangaskhan")

        self.assertContains(response, 'rel="prev"')
        self.assertNotContains(response, 'rel="next"')


class PokemonDetailFormsTest(PokemonDataTestCase):

    def get(self, name="Charizard", form=None):
        url = reverse("pokemon_detail", args=[name])
        return self.client.get(url, {"form": form} if form else {})

    # --- the switcher
    def test_pokemon_with_forms_get_a_switcher_listing_base_then_forms(self):
        response = self.get()

        options = response.context["form_options"]
        self.assertEqual([o["slug"] for o in options], ["", "mega-x", "mega-y", "gmax"])
        self.assertEqual([o["label"] for o in options],
                         ["Charizard", "Mega Charizard X", "Mega Charizard Y", "Gigantamax Charizard"])
        self.assertEqual([o["active"] for o in options], [True, False, False, False])
        self.assertContains(response, 'class="form-switcher"')
        self.assertContains(response, "?form=mega-x")

    def test_pokemon_without_forms_have_no_switcher(self):
        response = self.get("Bulbasaur")

        self.assertEqual(response.context["form_options"], [])
        self.assertNotContains(response, "form-switcher")

    def test_the_active_option_is_marked_for_assistive_tech(self):
        response = self.get(form="mega-y")
        self.assertContains(response, 'aria-current="page"', count=1)

    # --- viewing a form
    def test_a_form_overrides_types_stats_abilities_and_artwork(self):
        response = self.get(form="mega-x")
        pokemon = response.context["pokemon"]

        self.assertEqual(pokemon["types"], ["Fire", "Dragon"])
        self.assertEqual(pokemon["base_stats"]["Attack"], 130)
        self.assertEqual(pokemon["stat_total"], 634)
        self.assertEqual(pokemon["abilities"], [{"name": "Tough Claws", "hidden": False}])
        self.assertTrue(pokemon["image"].endswith("/10034.png"))
        self.assertEqual(pokemon["height_m"], 1.7)

    def test_species_level_data_stays_the_bases(self):
        pokemon = self.get(form="mega-x").context["pokemon"]

        self.assertEqual(pokemon["name"], "Charizard")
        self.assertEqual(pokemon["pokedex_number"], 6)
        self.assertEqual(pokemon["catch_rate"], 45)
        self.assertEqual(pokemon["egg_groups"], ["Monster", "Dragon"])

    def test_the_page_is_titled_with_the_forms_label(self):
        response = self.get(form="mega-x")

        self.assertEqual(response.context["display_name"], "Mega Charizard X")
        self.assertContains(response, "<title>Pokedex Entry - #6 Mega Charizard X</title>", html=False)
        self.assertContains(response, ">Mega Charizard X</h1>")

    def test_the_base_page_is_unchanged(self):
        response = self.get()

        self.assertEqual(response.context["display_name"], "Charizard")
        self.assertIsNone(response.context["active_form"])
        self.assertEqual(response.context["pokemon"]["types"], ["Fire", "Flying"])

    def test_type_defenses_use_the_forms_types(self):
        cells = {c["slug"]: c for c in self.get(form="mega-x").context["type_defenses"]}

        self.assertEqual(cells["grass"]["multiplier"], 0.25)    # fire and dragon both resist grass
        self.assertEqual(cells["rock"]["multiplier"], 2)         # no longer 4x: dragon is neutral to rock
        self.assertEqual(cells["ground"]["multiplier"], 2)       # no longer immune: not flying

    def test_stat_ranges_follow_the_forms_stats(self):
        base = self.get().context["stat_ranges"]["Attack"]
        mega = self.get(form="mega-x").context["stat_ranges"]["Attack"]
        self.assertGreater(mega["max"], base["max"])

    def test_an_unknown_form_is_404(self):
        self.assertEqual(self.get(form="mega-z").status_code, 404)
        self.assertEqual(self.get("Bulbasaur", form="mega").status_code, 404)

    def test_form_slug_is_case_insensitive(self):
        self.assertEqual(self.get(form="MEGA-X").status_code, 200)

    # --- moves
    def move_names(self, response):
        return {
            move["name"]
            for generation in response.context["move_generations"]
            for version in generation["versions"]
            for section in version["sections"]
            for move in section["moves"]
        }

    def test_a_form_with_its_own_moves_shows_only_those(self):
        response = self.get("Voltorb", form="hisui")

        self.assertFalse(response.context["moves_from_base"])
        self.assertEqual(self.move_names(response), {"Tackle", "Thunder Shock", "Charge", "Chloroblast"})

    def test_a_form_without_moves_falls_back_to_the_bases_and_says_so(self):
        base = self.move_names(self.get())
        response = self.get(form="mega-x")

        self.assertTrue(response.context["moves_from_base"])
        self.assertEqual(self.move_names(response), base)
        self.assertContains(response, "Mega Charizard X uses Charizard")

    def test_lazy_move_tabs_carry_the_form_so_the_right_moves_load(self):
        response = self.get(form="mega-x")
        lazy = reverse("pokemon_moves_fragment", args=["Charizard", "red-blue"])
        self.assertContains(response, f'data-src="{lazy}?form=mega-x"')

    def test_base_lazy_tabs_have_no_form_param(self):
        response = self.get()
        lazy = reverse("pokemon_moves_fragment", args=["Charizard", "red-blue"])
        self.assertContains(response, f'data-src="{lazy}"')

    # --- locations
    def test_forms_hide_the_location_tab_because_encounters_are_not_tracked(self):
        response = self.get(form="mega-x")

        self.assertNotContains(response, 'id="tab-location"')
        self.assertNotContains(response, 'id="panel-location"')
        self.assertContains(self.get(), 'id="tab-location"')

    # --- navigation is by species
    def test_previous_and_next_still_point_at_other_species(self):
        response = self.get("Kangaskhan", form="mega")
        self.assertEqual(response.context["previous"]["name"], "Voltorb")


class PokemonMovesFragmentFormsTest(PokemonDataTestCase):

    def url(self, name, version, form=None):
        url = reverse("pokemon_moves_fragment", args=[name, version])
        return f"{url}?form={form}" if form else url

    def test_a_forms_own_moves_for_a_game(self):
        response = self.client.get(self.url("Voltorb", "legends-arceus", "hisui"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chloroblast")

    def test_a_form_with_its_own_moves_has_none_for_other_games(self):
        self.assertEqual(self.client.get(self.url("Voltorb", "red-blue", "hisui")).status_code, 404)

    def test_a_form_without_moves_serves_the_bases(self):
        response = self.client.get(self.url("Charizard", "red-blue", "mega-x"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Flamethrower")

    def test_unknown_form_is_404(self):
        self.assertEqual(self.client.get(self.url("Charizard", "red-blue", "mega-z")).status_code, 404)


class PokemonDetailTest(PokemonDataTestCase):

    def test_pokemon_detail_url_resolves_to_correct_view(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_pokemon_detail_passes_pokemon_to_template(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )
        pokemon = response.context["pokemon"]
  
        self.assertEqual(response.status_code, 200)

        required_keys = [
            "pokedex_number",  
            "name",
            "image",
            "types",
            "base_stats",
        ]

        for key in required_keys:
            self.assertIn(key, pokemon)
            
        self.assertEqual(pokemon["name"], "Gengar")
        self.assertEqual(pokemon["types"], ["Ghost", "Poison"])
        self.assertIsInstance(pokemon["base_stats"], dict)
        self.assertEqual(pokemon["base_stats"]["Special Attack"], 130)
        
    def test_pokemon_detail_next_pokemon_link(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )
        next = response.context["next"]
        
        self.assertEqual(next["name"], "Onix")
        
    def test_pokemon_detail_previous_pokemon_link(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["Gengar"]
            )
        )
        previous = response.context["previous"]
        
        self.assertEqual(previous["name"], "Haunter")
        
    def test_first_pokemon_has_no_previous_link(self):
        response = self.client.get(
            reverse("pokemon_detail",
            args=["Bulbasaur"]
            )
        )
        previous = response.context["previous"]
        
        self.assertIsNone(previous)
            
    def test_lowercase_pokemon_detail_loads(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=["gengar"]
            )
        )
        
        self.assertEqual(response.status_code, 200)
        
        pokemon = response.context["pokemon"]
        self.assertEqual(pokemon["name"], "Gengar")

        self.assertEqual(response.context["next"]["name"], "Onix")
        self.assertEqual(response.context["previous"]["name"], "Haunter")

    def test_pokemon_detail_returns_404_for_unknown_pokemon(self):
        response = self.client.get(
            reverse("pokemon_detail", 
                    args=["NotARealPokemon"]
            )
        )
        
        self.assertEqual(response.status_code, 404)
        
    def test_404_exception_message_contains_searched_name(self):
        #RequestFactory is a Django testing utility used to create an HTTP request object manually,
        # so you can call a view directly without going through Django's normal request/URL/middleware cycle.
        factory = RequestFactory()
        request = factory.get("/pokemon/pokedex/NotARealPokemon/")

        #dont use self.client because it doesn't give you access to the exception's message unless you dig through 
        # the rendered template output(and that only works if DEBUG=False and your custom 404.html actually prints {{ exception }})
        #Testing the exception directly with assertRaises is more precise and doesn't depend on template rendering or 
        # DEBUG state at all.
        with self.assertRaises(Http404) as cm:
            pokemon_detail(request, name="NotARealPokemon")

        self.assertIn("NotARealPokemon", str(cm.exception))
        
    def test_pokemon_detail_returns_404_for_empty_name(self):
        response = self.client.get(
            reverse("pokemon_detail",
                    args=[" "]
            )
        )
        
        self.assertEqual(response.status_code, 400) 

    def test_calculate_stat_range(self):
        my_test_data = {
            "HP": 60,
            "Attack": 65,
            "Defense": 60,
            "Special Attack": 130,
            "Special Defense": 75,
            "Speed": 110
        }
        result = calculate_stat_range(my_test_data)
        self.assertEqual(result["HP"]["min"], 230)
        self.assertEqual(result["Attack"]["min"], 121)
        self.assertEqual(result["Attack"]["max"], 251)
    
    def test_pokemon_detail_loads_context(self):
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))
        context = response.context
        self.assertIn("pokemon", context)
        self.assertIn("next", context)
        self.assertIn("previous", context)
        self.assertIn("evolution_chain", context)
        self.assertIn("stat_ranges", context)
        self.assertIn("type_defense_order", context)

    def test_evolution_chain(self):
        cases = [
            ("multi_stage", "Gengar", ["Gastly", "Haunter", "Gengar"]),
            ("single_stage", "Kangaskhan", ["Kangaskhan"]),
        ]

        for case_name, name, expected in cases:
            with self.subTest(case=case_name, name=name):
                response = self.client.get(reverse("pokemon_detail", args=[name]))
                chain = response.context["evolution_chain"]
                self.assertEqual([stage["name"] for stage in chain], expected)

    def test_evolution_chain_skips_pokemon_not_in_database(self):
        Pokemon.objects.filter(name="Haunter").delete()
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))

        self.assertEqual(response.status_code, 200)
        names = [stage["name"] for stage in response.context["evolution_chain"]]

        self.assertEqual(names, ["Gastly", "Gengar"])

    def test_pokemon_detail_includes_moves_and_locations(self):
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))
        pokemon = response.context["pokemon"]

        self.assertTrue(pokemon["moves"])
        self.assertEqual(
            set(pokemon["moves"][0]), {"name", "version", "level_learnt", "method"}
        )
        self.assertEqual(response.context["locations"], pokemon["locations"])

    def test_detail_context_has_generation_grouped_moves_and_locations(self):
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))

        move_gens = response.context["move_generations"]
        self.assertTrue(move_gens)
        self.assertEqual(sum(g["active"] for g in move_gens), 1)
        self.assertIn("location_generations", response.context)

    def test_detail_page_renders_move_levels_and_game_tabs(self):
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))

        self.assertContains(response, 'id="tab-mv-gen-1"')
        self.assertContains(response, 'id="mv-red-blue"')
        self.assertContains(response, "Lv. ")
        self.assertContains(response, "Confuse Ray")

    def test_detail_page_with_no_encounters_shows_fallback(self):
        Pokemon.objects.get(name="Gengar").locations.all().delete()
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))

        self.assertContains(response, "can't be found in the wild")

    def test_detail_page_is_not_bloated_by_per_version_copies(self):
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))
        self.assertLess(len(response.content), 600_000)

    def test_training_fields_render_when_data_is_present(self):
        Pokemon.objects.filter(name="Gengar").update(
            ev_yield={"Special Attack": 3}, growth_rate="medium-slow", held_items=["Spell Tag"]
        )
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))

        self.assertContains(response, "3 Special Attack")
        self.assertContains(response, "Medium Slow")
        self.assertContains(response, "Spell Tag")
        self.assertContains(response, "1,059,860")
        self.assertEqual(response.context["exp_to_100"], 1_059_860)

    def test_training_fields_show_dash_when_not_synced_yet(self):
        response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))

        self.assertIsNone(response.context["exp_to_100"])
        self.assertNotContains(response, "Not yet tracked")

    def test_next_and_previous_skip_missing_pokedex_numbers(self):
        # #96–99 aren't in the sample data, so Onix (#95) -> Voltorb (#100)
        response = self.client.get(reverse("pokemon_detail", args=["Onix"]))
        self.assertEqual(response.context["next"]["name"], "Voltorb")

        response = self.client.get(reverse("pokemon_detail", args=["Voltorb"]))
        self.assertEqual(response.context["previous"]["name"], "Onix")
        
    def test_get_pokemon_move_list(self):
        data  = {
            "version": "red-blue",
            "move": "confuse-ray",
            "level_learnt": "1",
            "method": "level-up"
            }
        result = get_item(data, "version")
        
        self.assertEqual(result, "red-blue")
        
    def test_get_generation(self):
        data = {
            "generation": "I",
        }
        result = get_item(data, "generation")
        
        self.assertEqual(result, "I")

class GetItemFilterTest(SimpleTestCase):
    """Direct unit tests against the filter function itself."""
 
    def test_returns_value_for_existing_key(self):
        self.assertEqual(get_item({"HP": 100}, "HP"), 100)
 
    def test_returns_none_for_missing_key(self):
        self.assertIsNone(get_item({"HP": 100}, "Attack"))
 
    def test_returns_none_for_empty_dict(self):
        self.assertIsNone(get_item({}, "HP"))
 
    def test_works_with_variable_keys(self):
        stat_ranges = {
            "HP": {"min": 200, "max": 300},
            "Attack": {"min": 50, "max": 150},
        }
        for stat_name, expected in stat_ranges.items():
            with self.subTest(stat_name=stat_name):
                self.assertEqual(get_item(stat_ranges, stat_name), expected)
 
class GetItemFilterTemplateRenderingTest(SimpleTestCase):
    """
    Confirms the filter is registered under {% load pokemon_extras %} and
    behaves correctly when used from a template. This is the actual scenario
    the filter exists for: a variable key (e.g. a loop variable) that dot
    notation can't resolve, since {{ stat_ranges.stat_name }} would look for
    a literal key "stat_name" rather than the loop variable's value.
    """
 
    def _render(self, template_string, context):
        template = Template(template_string)
        return template.render(Context(context))
 
    def test_filter_resolves_variable_key_in_template(self):
        output = self._render(
            "{% load pokemon_extras %}{{ stat_ranges|get_item:stat_name }}",
            {
                "stat_ranges": {"HP": "200-300"},
                "stat_name": "HP",
            },
        )
        self.assertEqual(output, "200-300")
 
    def test_filter_renders_literal_none_string_for_missing_key_in_template(self):
    # get_item returns None explicitly (not a failed lookup), so Django
    # renders it via force_str(None) -> the literal string "None", not "".
        output = self._render(
            "{% load pokemon_extras %}{{ stat_ranges|get_item:stat_name }}",
            {
                "stat_ranges": {"HP": "200-300"},
                "stat_name": "Speed",
            },
        )
        self.assertEqual(output, "None")
 
    def test_filter_used_in_a_loop_with_dict_access(self):
        # Mirrors the actual usage in pokemon_detail.html: looping over
        # base_stats.items and looking up the matching entry in stat_ranges
        # by the current loop key.
        template_string = (
            "{% load pokemon_extras %}"
            "{% for stat_name, stat_value in base_stats.items %}"
            "{{ stat_name }}:{{ stat_value }}={{ stat_ranges|get_item:stat_name }} "
            "{% endfor %}"
        )
        output = self._render(
            template_string,
            {
                "base_stats": {"HP": 60, "Attack": 65},
                "stat_ranges": {
                    "HP": "180-274",
                    "Attack": "112-207",
                },
            },
        )
        self.assertEqual(output.strip(), "HP:60=180-274 Attack:65=112-207")

class GroupHmTmMovesTests(TestCase):

    def test_group_hm_tm_moves_splits_hm_named_moves_correctly(self):
        moves = [
            {
                "name": "Cut",
                "method": "machine",
            },
            {
                "name": "Fly",
                "method": "machine",
            },
            {
                "name": "Surf",
                "method": "machine",
            },
            {
                "name": "Thunderbolt",
                "method": "machine",
            },
        ]

        hm, tm = group_hm_tm_moves(moves)

        self.assertEqual(
            hm,
            [
                {
                    "name": "Cut",
                    "method": "machine",
                },
                {
                    "name": "Fly",
                    "method": "machine",
                },
                {
                    "name": "Surf",
                    "method": "machine",
                },
            ],
        )

        self.assertEqual(
            tm,
            [
                {
                    "name": "Thunderbolt",
                    "method": "machine",
                },
            ],
        )
        
    def test_group_hm_tm_moves_treats_non_hm_machine_moves_as_tm(self):
        moves = [
            {"name": "Cut", "method": "machine"},
            {"name": "Thunderbolt", "method": "machine"},
            {"name": "Ice Beam", "method": "machine"},
        ]

        expected_hm = [
            {"name": "Cut", "method": "machine"},
        ]

        expected_tm = [
            {"name": "Thunderbolt", "method": "machine"},
            {"name": "Ice Beam", "method": "machine"},
        ]

        hm, tm = group_hm_tm_moves(moves)

        self.assertEqual(hm, expected_hm)
        self.assertEqual(tm, expected_tm)
    
    def test_group_hm_tm_moves_ignores_non_machine_methods(self):
        moves = [
            {
                "name": "Cut",
                "method": "machine",
            },
            {
                "name": "Tackle",
                "method": "level-up",
            },
            {
                "name": "Surf",
                "method": "machine",
            },
        ]
        
        expected_hm = [
                    {"name": "Cut", "method": "machine"},
                    {"name": "Surf", "method": "machine"},
                ]

        hm, tm = group_hm_tm_moves(moves)

        self.assertEqual(hm,expected_hm)
        self.assertEqual(tm, [])
class HomeViewTest(PokemonDataTestCase):

    def test_home_view_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        
    def test_home_context_contains_required_data(self):
        response = self.client.get(reverse("home"))
        
        self.assertEqual(response.status_code, 200)

        required_keys = [
            "pokemon_count",
            "move_count",
            "ability_count",
            "explore_pokemon",
            "hero",
            "featured_pokemon",
        ]

        for key in required_keys:
            self.assertIn(key, response.context)
            
    def test_home_context_has_correct_types(self):
        response = self.client.get(reverse("home"))
        context = response.context

        self.assertIsInstance(context["pokemon_count"], int)
        self.assertIsInstance(context["move_count"], int)
        self.assertIsInstance(context["ability_count"], int)
        self.assertIsInstance(context["explore_pokemon"], str)
        self.assertIsInstance(context["hero"], dict)
        self.assertIsInstance(context["featured_pokemon"], list)
        
    def test_home_context_has_data(self):
        response = self.client.get(reverse("home"))
        context = response.context

        self.assertIsNotNone(context["hero"])

        self.assertTrue(context["featured_pokemon"])
        self.assertTrue(context["explore_pokemon"])
        self.assertTrue(context["pokemon_count"])
        
    def test_home_counts_distinct_moves_and_abilities(self):
        response = self.client.get(reverse("home"))
        context = response.context

        expected_moves = len({m.name for m in PokemonMove.objects.all()})
        expected_abilities = {
            a["name"] for p in Pokemon.objects.all() for a in p.abilities
        }

        self.assertGreater(expected_moves, 0)
        self.assertEqual(context["move_count"], expected_moves)
        self.assertEqual(context["ability_count"], len(expected_abilities))

    def test_home_has_correct_number_of_featured_pokemon(self):
        response = self.client.get(reverse("home"))
        context = response.context

        self.assertEqual(
            len(context["featured_pokemon"]),
            settings.FEATURED_POKEMON_COUNT
        )

class HomeViewEmptyDatabaseTest(TestCase):

    def test_home_view_has_empty_featured_grid_when_no_pokemon(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["featured_pokemon"], [])
        self.assertIsNone(response.context["hero"])

    def test_home_counts_are_zero_when_no_pokemon(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["pokemon_count"], 0)
        self.assertEqual(response.context["move_count"], 0)
        self.assertEqual(response.context["ability_count"], 0)

class SearchViewTest(PokemonDataTestCase):

    def test_search_view_redirects(self):
        response = self.client.get(
            reverse("search"),
            {"search": "Gengar"})

        self.assertRedirects(response,reverse("pokemon_detail", args=["Gengar"]))

    def test_search_returns_200_when_pokemon_not_found(self):
        response = self.client.get(
            reverse("search"),
            {"search": "NotARealPokemon"},
            follow=True         ##so it follows the redirect elsewise it will stay at the static url
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("home"))
        self.assertContains(response, "No Pokémon found matching NotARealPokemon")
        
User = get_user_model()
class AdminSyncViewTest(TestCase):
    
    def setUp(self):
        self.url = reverse("admin_sync_pokemon")
        self.staff_user = User.objects.create_user(
            username="staffer", password="testpass123", is_staff=True
        )
    
    @patch("pokemon.views.sync_pokemon_data")
    def test_post_success_adds_new_pokemon_to_context(self, mock_sync):
        mock_sync.return_value = {
            "added": ["Bulbasaur", "Charmander"],
            "updated": [],
        }
        self.client.force_login(self.staff_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["sync_success"])
        self.assertEqual(response.context["new_pokemon"], ["Bulbasaur", "Charmander"])
        self.assertEqual(response.context["updated_pokemon"], [])
        self.assertNotIn("sync_error", response.context)
        mock_sync.assert_called_once()

    @patch("pokemon.views.sync_pokemon_data")
    def test_post_success_surfaces_updated_pokemon(self, mock_sync):
        mock_sync.return_value = {
            "added": [],
            "updated": ["Gengar"],
        }
        self.client.force_login(self.staff_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["sync_success"])
        self.assertEqual(response.context["new_pokemon"], [])
        self.assertEqual(response.context["updated_pokemon"], ["Gengar"])

    @patch("pokemon.views.sync_pokemon_data")
    def test_post_failure_does_not_500(self, mock_sync):
        mock_sync.side_effect = PokelanceAPIError("upstream API unavailable")
        self.client.force_login(self.staff_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sync_error"], "upstream API unavailable")
        self.assertNotIn("sync_success", response.context)


class PokedexFilterViewTest(PokemonDataTestCase):

    def test_pokedex_filter_controls_are_rendered_and_region_type_can_combine(self):
        response = self.client.get(reverse("pokedex"), {"region": "Kanto", "type": "fire"})

        self.assertEqual(
            [pokemon.name for pokemon in response.context["pokemon_data"]],
            ["Charmander", "Charmeleon", "Charizard"],
        )
        self.assertEqual(response.context["pokemon_count"], 3)
        self.assertEqual(response.context["stored_count"], 12)
        self.assertEqual(response.context["selected_region"], "Kanto")
        self.assertEqual(response.context["selected_type"], "fire")
        self.assertContains(response, 'class="pokedex-filters"')
        self.assertContains(response, 'value="Kanto" selected')
        self.assertContains(response, 'value="fire" selected')

    def test_type_filter_is_case_insensitive(self):
        response = self.client.get(reverse("pokedex"), {"type": "FIRE"})

        self.assertEqual(response.context["selected_type"], "fire")
        self.assertEqual(response.context["pokemon_count"], 3)

    def test_invalid_filters_are_ignored(self):
        response = self.client.get(reverse("pokedex"), {"region": "Unknown", "type": "unknown"})

        self.assertEqual(response.context["pokemon_count"], 12)
        self.assertFalse(response.context["filtering"])

    def test_empty_filter_result_has_clear_guidance(self):
        response = self.client.get(reverse("pokedex"), {"type": "fairy"})

        self.assertEqual(response.context["pokemon_count"], 0)
        self.assertContains(response, "No Pokémon match these filters")
        self.assertContains(response, f'href="{reverse("pokedex")}"')


class TypesViewTest(PokemonDataTestCase):

    def test_types_view_returns_200(self):
        response = self.client.get(reverse("types"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "types.html")

    def test_lists_all_eighteen_types_with_counts(self):
        response = self.client.get(reverse("types"))
        tiles = {t["slug"]: t for t in response.context["type_tiles"]}

        self.assertEqual(len(tiles), 18)
        self.assertEqual(tiles["fire"]["pokemon_count"], 3)   # Charmander, Charmeleon, Charizard
        self.assertEqual(tiles["fire"]["form_count"], 3)
        self.assertEqual(tiles["fire"]["move_count"], 3)      # Ember, Flamethrower, Fire Blast
        self.assertEqual(tiles["fairy"]["pokemon_count"], 0)
        self.assertEqual(tiles["fairy"]["form_count"], 0)
        self.assertContains(response, reverse("type_detail", args=["fire"]))

    def test_chart_has_a_row_per_attacking_type(self):
        response = self.client.get(reverse("types"))
        chart = response.context["chart"]

        self.assertEqual(len(chart), 18)
        fire_row = next(r for r in chart if r["slug"] == "fire")
        grass_cell = next(c for c in fire_row["cells"] if c["slug"] == "grass")
        self.assertEqual(grass_cell["multiplier"], 2)
        self.assertEqual(grass_cell["label"], "2")
        self.assertContains(response, "mult-weak")
        self.assertContains(response, "mult-immune")


class TypesViewEmptyTest(TestCase):

    def test_renders_without_any_pokemon(self):
        response = self.client.get(reverse("types"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["type_tiles"][0]["pokemon_count"], 0)


class TypeDetailViewTest(PokemonDataTestCase):

    def test_shows_matchups_and_pokemon_of_the_type(self):
        response = self.client.get(reverse("type_detail", args=["fire"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "type_detail.html")
        self.assertEqual(response.context["matchups"]["attack"]["super"], ["grass", "ice", "bug", "steel"])
        self.assertEqual(
            [p["name"] for p in response.context["pokemon"]],
            ["Charmander", "Charmeleon", "Charizard"],
        )
        self.assertEqual(response.context["move_count"], 3)

    def test_includes_dual_types(self):
        response = self.client.get(reverse("type_detail", args=["flying"]))
        self.assertEqual([p["name"] for p in response.context["pokemon"]], ["Charizard"])

    def test_lists_matching_forms_separately_from_base_pokemon(self):
        response = self.client.get(reverse("type_detail", args=["dragon"]))

        self.assertEqual(response.context["pokemon"], [])
        form = response.context["forms"][0]
        self.assertEqual(
            (form["name"], form["pokedex_number"], form["slug"], form["label"], form["types"]),
            ("Charizard", 6, "mega-x", "Mega Charizard X", ["Fire", "Dragon"]),
        )
        self.assertTrue(form["image"])
        self.assertContains(response, "Mega Charizard X")
        self.assertContains(response, f'{reverse("pokemon_detail", args=["Charizard"])}?form=mega-x')

    def test_form_cards_follow_pokeapi_order_after_base_species(self):
        response = self.client.get(reverse("type_detail", args=["fire"]))

        self.assertEqual(
            [form["label"] for form in response.context["forms"]],
            ["Mega Charizard X", "Mega Charizard Y", "Gigantamax Charizard"],
        )

    def test_pokemon_without_forms_does_not_get_a_form_entry(self):
        response = self.client.get(reverse("type_detail", args=["grass"]))

        self.assertNotIn("Bulbasaur", [form["name"] for form in response.context["forms"]])

    def test_name_is_case_insensitive(self):
        self.assertEqual(self.client.get(reverse("type_detail", args=["FIRE"])).status_code, 200)

    def test_unknown_type_is_404(self):
        self.assertEqual(self.client.get(reverse("type_detail", args=["banana"])).status_code, 404)

    def test_type_with_no_pokemon_still_renders(self):
        response = self.client.get(reverse("type_detail", args=["fairy"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Fairy-type Pokémon")


class RegionViewTest(PokemonDataTestCase):

    def test_region_view_returns_200(self):
        response = self.client.get(reverse("region"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "regions.html")

    def test_lists_nine_regions_in_order_with_counts(self):
        response = self.client.get(reverse("region"))
        tiles = response.context["region_tiles"]

        self.assertEqual([t["name"] for t in tiles], [
            "Kanto", "Johto", "Hoenn", "Sinnoh", "Unova", "Kalos", "Alola", "Galar", "Paldea",
        ])
        self.assertEqual(tiles[0]["pokemon_count"], 12)
        self.assertEqual(tiles[0]["dex_range"], "#1\u2013#151")
        self.assertEqual(tiles[1]["pokemon_count"], 0)
        self.assertContains(response, reverse("region_detail", args=["kanto"]))


class RegionViewEmptyTest(TestCase):

    def test_renders_without_any_pokemon(self):
        self.assertEqual(self.client.get(reverse("region")).status_code, 200)


class RegionDetailViewTest(PokemonDataTestCase):

    def test_lists_the_regions_pokemon_and_games(self):
        response = self.client.get(reverse("region_detail", args=["kanto"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "region_detail.html")
        self.assertEqual(response.context["region"]["name"], "Kanto")
        self.assertEqual(len(response.context["pokemon"]), 12)
        self.assertEqual(response.context["pokemon"][0]["name"], "Bulbasaur")
        self.assertEqual(response.context["region"]["games"], ["Red/Blue", "Yellow"])
        self.assertContains(response, "Charizard")

    def test_name_is_case_insensitive(self):
        self.assertEqual(self.client.get(reverse("region_detail", args=["KANTO"])).status_code, 200)

    def test_unknown_region_is_404(self):
        self.assertEqual(self.client.get(reverse("region_detail", args=["narnia"])).status_code, 404)

    def test_region_without_pokemon_explains_itself(self):
        response = self.client.get(reverse("region_detail", args=["johto"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Johto Pokémon")

    def test_links_to_neighbouring_regions(self):
        response = self.client.get(reverse("region_detail", args=["johto"]))
        self.assertContains(response, reverse("region_detail", args=["kanto"]))
        self.assertContains(response, reverse("region_detail", args=["hoenn"]))


class AbilitiesViewTest(PokemonDataTestCase):

    def rows(self, response):
        return {r["name"]: r for r in response.context["page_obj"]}

    def test_abilities_view_returns_200(self):
        response = self.client.get(reverse("abilities"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "abilities.html")

    def test_lists_each_ability_once_with_counts_and_effect(self):
        response = self.client.get(reverse("abilities"))
        rows = self.rows(response)

        self.assertEqual(response.context["total"], 15)
        self.assertEqual(rows["Blaze"]["pokemon_count"], 3)
        self.assertEqual(rows["Solar Power"]["pokemon_count"], 3)
        self.assertEqual(rows["Blaze"]["effect"], "Strengthens fire moves to inflict 1.5\u00d7 damage at 1/3 max HP or less.")
        self.assertEqual(rows["Blaze"]["slug"], "blaze")
        self.assertEqual(rows["Rock Head"]["effect"], "")      # no stored effect text
        self.assertContains(response, reverse("ability_detail", args=["solar-power"]))

    def test_default_order_is_by_name(self):
        names = [r["name"] for r in self.client.get(reverse("abilities")).context["page_obj"]]
        self.assertEqual(names, sorted(names))

    def test_search_by_name(self):
        response = self.client.get(reverse("abilities"), {"q": "SOLAR"})
        self.assertEqual(list(self.rows(response)), ["Solar Power"])

    def test_sort_by_pokemon_count(self):
        response = self.client.get(reverse("abilities"), {"sort": "pokemon", "dir": "desc"})
        counts = [r["pokemon_count"] for r in response.context["page_obj"]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_no_matches_message(self):
        self.assertContains(self.client.get(reverse("abilities"), {"q": "zzzz"}), "No abilities match")


class AbilitiesViewWithoutEffectsTest(TestCase):

    def test_missing_effect_text_points_at_sync_abilities(self):
        from pokemon.models import Pokemon
        Pokemon.objects.create(pokedex_number=1, name="Bulbasaur", abilities=[{"name": "Overgrow", "hidden": False}])

        response = self.client.get(reverse("abilities"))

        self.assertContains(response, "Overgrow")
        self.assertContains(response, "sync_abilities")


class AbilitiesViewEmptyTest(TestCase):

    def test_renders_without_any_pokemon(self):
        self.assertEqual(self.client.get(reverse("abilities")).status_code, 200)


class AbilityDetailViewTest(PokemonDataTestCase):

    def test_shows_effect_and_pokemon_split_by_hidden(self):
        response = self.client.get(reverse("ability_detail", args=["chlorophyll"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ability_detail.html")
        self.assertEqual(response.context["ability"]["name"], "Chlorophyll")
        self.assertEqual(response.context["ability"]["effect"], "Doubles Speed during strong sunlight.")
        self.assertEqual(response.context["ability"]["generation"], 3)
        self.assertEqual([p["name"] for p in response.context["hidden_pokemon"]], ["Bulbasaur", "Ivysaur", "Venusaur"])
        self.assertEqual(response.context["regular_pokemon"], [])

    def test_regular_abilities_are_listed_separately(self):
        response = self.client.get(reverse("ability_detail", args=["blaze"]))
        self.assertEqual([p["name"] for p in response.context["regular_pokemon"]], ["Charmander", "Charmeleon", "Charizard"])

    def test_ability_without_effect_text_still_renders(self):
        response = self.client.get(reverse("ability_detail", args=["rock-head"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Onix")

    def test_unknown_ability_is_404(self):
        self.assertEqual(self.client.get(reverse("ability_detail", args=["nope"])).status_code, 404)


class MovesViewTest(TestCase):
    
    def test_moves_view_returns_200(self):
        response = self.client.get(reverse("moves"))
        
        self.assertEqual(response.status_code, 200)
        
class CompetitiveViewTest(PokemonDataTestCase):

    def rows(self, response):
        return list(response.context["page_obj"])

    def test_competitive_view_returns_200(self):
        response = self.client.get(reverse("competitive"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "competitive.html")
        self.assertContains(response, 'data-async-page="competitive"')
        self.assertContains(response, 'aria-live="polite"')

    def test_ranks_base_pokemon_and_forms_by_total_by_default(self):
        response = self.client.get(reverse("competitive"))
        rows = self.rows(response)

        self.assertEqual([r["display_name"] for r in rows[:2]], ["Mega Charizard X", "Mega Charizard Y"])
        self.assertEqual(rows[0]["value"], 634)
        self.assertEqual(response.context["stat"]["slug"], "total")
        self.assertEqual(response.context["stored_count"], 12)
        self.assertEqual(response.context["base_count"], 12)
        self.assertEqual(response.context["form_count"], 5)
        self.assertEqual(response.context["total"], 17)
        self.assertNotContains(response, 'name="forms"')

    def test_tied_pokemon_share_a_rank(self):
        rows = self.rows(self.client.get(reverse("competitive")))
        by_name = {r["name"]: r["rank"] for r in rows}

        self.assertEqual(by_name["Ivysaur"], 9)
        self.assertEqual(by_name["Haunter"], 9)
        self.assertEqual(by_name["Charmeleon"], 9)
        self.assertEqual(by_name["Onix"], 12)    # next rank skips the tie

    def test_ranks_by_a_single_stat(self):
        response = self.client.get(reverse("competitive"), {"stat": "speed"})
        rows = self.rows(response)

        self.assertEqual(rows[0]["name"], "Gengar")
        self.assertEqual(rows[0]["value"], 110)
        self.assertEqual(response.context["stat"]["label"], "Speed")

    def test_rows_carry_every_stat_and_a_bar_width(self):
        response = self.client.get(reverse("competitive"))
        rows = self.rows(response)
        row = next(row for row in rows if row["name"] == "Charizard" and not row["is_form"])

        self.assertEqual(row["stats"]["Attack"], 84)
        self.assertEqual(row["types"], ["Fire", "Flying"])
        self.assertEqual(row["display_name"], "Charizard")
        self.assertFalse(row["is_form"])
        self.assertLess(row["bar"], 100)
        self.assertEqual(rows[0]["bar"], 100)

    def test_forms_are_ranked_by_default_and_keep_base_species_count(self):
        response = self.client.get(reverse("competitive"))
        rows = self.rows(response)
        charizard_forms = [row for row in rows if row["name"] == "Charizard" and row["is_form"]]

        self.assertEqual(response.context["stored_count"], 12)
        self.assertEqual(response.context["base_count"], 12)
        self.assertEqual(response.context["form_count"], 5)
        self.assertEqual(response.context["total"], 17)
        self.assertEqual(
            [(row["display_name"], row["form_slug"], row["types"]) for row in charizard_forms],
            [
                ("Mega Charizard X", "mega-x", ["Fire", "Dragon"]),
                ("Mega Charizard Y", "mega-y", ["Fire", "Flying"]),
                ("Gigantamax Charizard", "gmax", ["Fire", "Flying"]),
            ],
        )
        self.assertEqual(
            [row["display_name"] for row in rows if row["name"] == "Charizard" and row["value"] == 534],
            ["Charizard", "Gigantamax Charizard"],
        )

    def test_form_rankings_sort_by_value_then_species_and_form_order(self):
        rows = self.rows(self.client.get(reverse("competitive")))

        self.assertEqual([row["display_name"] for row in rows[:2]], [
            "Mega Charizard X", "Mega Charizard Y",
        ])
        self.assertEqual([row["rank"] for row in rows[:2]], [1, 1])
        self.assertEqual(
            [row["display_name"] for row in rows if row["name"] == "Bulbasaur"],
            ["Bulbasaur"],
        )

    def test_speed_tiers_include_forms_by_default(self):
        response = self.client.get(reverse("competitive"), {"sort": "max-50"})
        charizard_x = next(
            row for row in self.rows(response)
            if row["name"] == "Charizard" and row["form_slug"] == "mega-x"
        )

        self.assertEqual(charizard_x["speed_tiers"]["max-50"], 167)
        self.assertEqual(response.context["total"], 17)
        self.assertContains(response, "sort=max-100&amp;dir=desc")
        self.assertContains(response, "sort=max-50&amp;dir=asc")

    def test_filters_by_type(self):
        response = self.client.get(reverse("competitive"), {"type": "Ghost"})
        self.assertEqual({r["name"] for r in self.rows(response)}, {"Gastly", "Haunter", "Gengar"})
        self.assertEqual(self.rows(response)[0]["rank"], 1)     # ranks are within the filtered list

    def test_unknown_stat_and_type_are_ignored(self):
        response = self.client.get(reverse("competitive"), {"stat": "luck", "type": "Banana"})

        self.assertEqual(response.context["stat"]["slug"], "total")
        self.assertEqual(response.context["total"], 17)

    def test_every_stat_has_a_link_that_keeps_the_type_filter(self):
        response = self.client.get(reverse("competitive"), {"type": "Fire"})
        self.assertContains(response, "stat=speed&amp;type=Fire")

    def test_no_matches_message(self):
        response = self.client.get(reverse("competitive"), {"type": "Fairy"})
        self.assertContains(response, "No Pok")


class CompetitiveSpeedRankingTest(TestCase):

    @staticmethod
    def create_pokemon(number, name, speed, pokemon_type="Normal"):
        return Pokemon.objects.create(
            pokedex_number=number,
            name=name,
            types=[pokemon_type],
            base_stats={
                "HP": 50, "Attack": 50, "Defense": 50,
                "Special Attack": 50, "Special Defense": 50, "Speed": speed,
            },
            stat_total=300 + speed,
        )

    def rows(self, response):
        return list(response.context["page_obj"])

    def test_selected_speed_column_sorts_rows_by_calculated_speed(self):
        self.create_pokemon(1, "Quick", 100)
        self.create_pokemon(2, "Steady", 90)
        self.create_pokemon(3, "Slow", 50)

        response = self.client.get(reverse("competitive"), {"sort": "max-50"})

        self.assertEqual([row["name"] for row in self.rows(response)], ["Quick", "Steady", "Slow"])
        self.assertEqual(self.rows(response)[0]["value"], 167)
        self.assertTrue(response.context["speed_mode"])

    def test_speed_sort_can_be_ascending_and_keeps_type_filter(self):
        self.create_pokemon(1, "Quick Fire", 100, "Fire")
        self.create_pokemon(2, "Slow Fire", 50, "Fire")
        self.create_pokemon(3, "Quick Water", 100, "Water")

        response = self.client.get(
            reverse("competitive"), {"sort": "neutral-100", "dir": "asc", "type": "Fire"}
        )

        self.assertEqual([row["name"] for row in self.rows(response)], ["Slow Fire", "Quick Fire"])
        self.assertEqual(response.context["query"], "sort=neutral-100&dir=asc&type=Fire")

    def test_tied_speed_values_share_competition_rank(self):
        self.create_pokemon(1, "First", 100)
        self.create_pokemon(2, "Second", 100)
        self.create_pokemon(3, "Third", 90)

        rows = self.rows(self.client.get(reverse("competitive"), {"sort": "choice-scarf-50"}))

        self.assertEqual([(row["name"], row["rank"]) for row in rows], [
            ("First", 1), ("Second", 1), ("Third", 3),
        ])

    def test_speed_column_links_and_assumptions_are_rendered(self):
        self.create_pokemon(1, "Quick", 100)

        response = self.client.get(reverse("competitive"), {"sort": "max-50"})

        self.assertContains(response, "sort=max-100")
        self.assertContains(response, "31 IVs")
        self.assertContains(response, "Choice Scarf")


class CompetitivePaginationTest(TestCase):

    def test_fifty_per_page(self):
        from pokemon.models import Pokemon
        for i in range(1, 61):
            Pokemon.objects.create(
                pokedex_number=i, name=f"Mon{i}", types=["Normal"],
                base_stats={"HP": i, "Attack": 1, "Defense": 1, "Special Attack": 1, "Special Defense": 1, "Speed": 1},
                stat_total=i + 5,
            )
        first = self.client.get(reverse("competitive"))
        second = self.client.get(reverse("competitive"), {"page": 2})

        self.assertEqual(len(first.context["page_obj"]), 50)
        self.assertEqual(len(second.context["page_obj"]), 10)
        self.assertEqual(second.context["page_obj"][0]["rank"], 51)


class CompetitiveEmptyTest(TestCase):

    def test_explains_how_to_load_pokemon(self):
        response = self.client.get(reverse("competitive"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "import_pokemon_json")


class ItemsViewTest(TestCase):

    def setUp(self):
        from pokemon.tests.helpers import load_sample_items
        load_sample_items()

    def names(self, response):
        return [i.name for i in response.context["page_obj"]]

    def test_items_view_returns_200(self):
        response = self.client.get(reverse("items"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "items.html")

    def test_lists_items_with_cost_effect_and_category(self):
        response = self.client.get(reverse("items"))

        self.assertEqual(response.context["total"], 6)
        self.assertEqual(self.names(response), sorted(self.names(response)))
        self.assertContains(response, "Restores 20 HP.")
        self.assertContains(response, "Standard Balls")
        self.assertContains(response, "10,000")

    def test_unsold_or_unpriced_items_show_a_dash_not_a_cost(self):
        response = self.client.get(reverse("items"), {"q": "master"})
        self.assertNotContains(response, ">0<")
        self.assertContains(response, "Not sold")

    def test_filters_by_category(self):
        response = self.client.get(reverse("items"), {"category": "healing"})
        self.assertEqual(self.names(response), ["Potion", "Super Potion"])

    def test_searches_by_name(self):
        response = self.client.get(reverse("items"), {"q": "POTION"})
        self.assertEqual(self.names(response), ["Potion", "Super Potion"])

    def test_filters_combine(self):
        response = self.client.get(reverse("items"), {"category": "healing", "q": "super"})
        self.assertEqual(self.names(response), ["Super Potion"])

    def test_unknown_category_is_ignored(self):
        self.assertEqual(self.client.get(reverse("items"), {"category": "nope"}).context["total"], 6)

    def test_category_choices_come_from_stored_items(self):
        response = self.client.get(reverse("items"))

        self.assertContains(response, '<option value="vitamins"')
        self.assertContains(response, ">Standard Balls<")
        self.assertNotContains(response, '<option value="held-items"')

    def test_items_without_a_sprite_still_render(self):
        response = self.client.get(reverse("items"), {"q": "mystery"})

        self.assertEqual(self.names(response), ["Mystery Item"])
        self.assertContains(response, "Mystery Item")

    def test_no_matches_message(self):
        self.assertContains(self.client.get(reverse("items"), {"q": "zzzz"}), "No items match")


class ItemsPaginationTest(TestCase):

    def test_forty_eight_per_page_and_links_keep_filters(self):
        from pokemon.models import Item
        for i in range(60):
            Item.objects.create(name=f"Item {i:02d}", category="healing")

        first = self.client.get(reverse("items"), {"category": "healing"})
        second = self.client.get(reverse("items"), {"page": 2})

        self.assertEqual(len(first.context["page_obj"]), 48)
        self.assertEqual(len(second.context["page_obj"]), 12)
        self.assertContains(first, "category=healing&amp;page=2")


class ItemsEmptyTest(TestCase):

    def test_explains_how_to_load_items(self):
        response = self.client.get(reverse("items"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sync_items")


class MovesListViewTest(PokemonDataTestCase):

    def names(self, response):
        return [m.name for m in response.context["page_obj"]]

    def test_lists_stored_moves_with_their_stats(self):
        response = self.client.get(reverse("moves"))

        self.assertTemplateUsed(response, "moves.html")
        self.assertEqual(response.context["total"], 14)
        self.assertContains(response, "Flamethrower")
        self.assertContains(response, "move-type type-fire")
        self.assertContains(response, "move-cat-special")
        self.assertContains(response, "Has a 10% chance to burn the target.")

    def test_default_order_is_by_name(self):
        names = self.names(self.client.get(reverse("moves")))
        self.assertEqual(names, sorted(names))

    def test_filters_by_type(self):
        response = self.client.get(reverse("moves"), {"type": "Fire"})
        self.assertEqual(self.names(response), ["Ember", "Fire Blast", "Flamethrower"])

    def test_filters_by_category(self):
        response = self.client.get(reverse("moves"), {"category": "status"})
        self.assertEqual(self.names(response), ["Growl", "Smokescreen", "Swords Dance"])

    def test_searches_by_name_case_insensitively(self):
        response = self.client.get(reverse("moves"), {"q": "FLAME"})
        self.assertEqual(self.names(response), ["Flamethrower"])

    def test_filters_combine(self):
        response = self.client.get(reverse("moves"), {"type": "Fire", "category": "special", "q": "blast"})
        self.assertEqual(self.names(response), ["Fire Blast"])

    def test_unknown_filter_values_are_ignored(self):
        response = self.client.get(reverse("moves"), {"type": "Banana", "category": "nope", "sort": "zzz"})
        self.assertEqual(response.context["total"], 14)

    def test_sorts_by_power_with_unknown_power_last(self):
        desc = self.names(self.client.get(reverse("moves"), {"sort": "power", "dir": "desc"}))
        asc = self.names(self.client.get(reverse("moves"), {"sort": "power", "dir": "asc"}))

        self.assertEqual(desc[0], "Fire Blast")
        self.assertEqual(asc[0], "Ember")
        for names in (asc, desc):
            self.assertEqual(set(names[-4:]), {"Dragon Rage", "Growl", "Smokescreen", "Swords Dance"})

    def test_no_matches_shows_an_empty_message(self):
        response = self.client.get(reverse("moves"), {"q": "zzzz"})
        self.assertContains(response, "No moves match")

    def test_type_and_category_choices_are_offered(self):
        response = self.client.get(reverse("moves"))
        self.assertContains(response, '<option value="Fire"')
        self.assertContains(response, '<option value="physical"')


class MovesListPaginationTest(TestCase):

    def setUp(self):
        for i in range(60):
            Move.objects.create(name=f"Move {i:02d}", type="Normal", damage_class="physical", power=i)

    def test_pages_are_fifty_moves(self):
        first = self.client.get(reverse("moves"))
        second = self.client.get(reverse("moves"), {"page": 2})

        self.assertEqual(len(first.context["page_obj"]), 50)
        self.assertEqual(len(second.context["page_obj"]), 10)

    def test_pagination_links_keep_the_filters(self):
        response = self.client.get(reverse("moves"), {"type": "Normal"})
        self.assertContains(response, "type=Normal&amp;page=2")

    def test_out_of_range_page_shows_the_last_page(self):
        response = self.client.get(reverse("moves"), {"page": 99})
        self.assertEqual(response.context["page_obj"].number, 2)


class MovesListEmptyTest(TestCase):

    def test_explains_how_to_load_move_data(self):
        response = self.client.get(reverse("moves"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sync_moves")


class FormsListViewTest(PokemonDataTestCase):

    def labels(self, response):
        return [f.label for f in response.context["page_obj"]]

    def test_lists_every_form_ordered_by_species_then_id(self):
        response = self.client.get(reverse("forms"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "forms.html")
        self.assertEqual(response.context["total"], 5)
        self.assertEqual(self.labels(response), [
            "Mega Charizard X", "Mega Charizard Y", "Gigantamax Charizard",
            "Hisuian Voltorb", "Mega Kangaskhan",
        ])

    def test_cards_link_to_the_form_on_the_pokemon_page(self):
        response = self.client.get(reverse("forms"))

        self.assertContains(response, f'href="{reverse("pokemon_detail", args=["Charizard"])}?form=mega-x"')
        self.assertContains(response, f'href="{reverse("pokemon_detail", args=["Voltorb"])}?form=hisui"')

    def test_cards_show_types_and_base_stat_total(self):
        response = self.client.get(reverse("forms"), {"q": "mega charizard x"})

        self.assertContains(response, "type-dragon")
        self.assertContains(response, "634")

    def test_kind_tabs_carry_counts(self):
        tabs = {t["slug"]: t for t in self.client.get(reverse("forms")).context["kind_tabs"]}

        self.assertEqual({k: t["count"] for k, t in tabs.items()},
                         {"": 5, "regional": 1, "mega": 3, "gmax": 1, "other": 0})
        self.assertTrue(tabs[""]["active"])

    def test_filters_by_kind(self):
        response = self.client.get(reverse("forms"), {"kind": "mega"})

        self.assertEqual(self.labels(response), ["Mega Charizard X", "Mega Charizard Y", "Mega Kangaskhan"])
        self.assertTrue({t["slug"]: t for t in response.context["kind_tabs"]}["mega"]["active"])

    def test_unknown_kind_is_ignored(self):
        self.assertEqual(self.client.get(reverse("forms"), {"kind": "banana"}).context["total"], 5)

    def test_searches_by_label_or_pokemon_name(self):
        self.assertEqual(self.labels(self.client.get(reverse("forms"), {"q": "HISUI"})), ["Hisuian Voltorb"])
        self.assertEqual(len(self.labels(self.client.get(reverse("forms"), {"q": "charizard"}))), 3)

    def test_search_and_kind_combine(self):
        response = self.client.get(reverse("forms"), {"kind": "mega", "q": "charizard"})
        self.assertEqual(self.labels(response), ["Mega Charizard X", "Mega Charizard Y"])

    def test_no_matches_message(self):
        self.assertContains(self.client.get(reverse("forms"), {"q": "zzzz"}), "No forms match")

    def test_pokedex_page_links_to_the_forms_page_with_a_count(self):
        response = self.client.get(reverse("pokedex"))

        self.assertContains(response, f'href="{reverse("forms")}"')
        self.assertContains(response, "5 alternate forms")


class FormsListPaginationTest(TestCase):

    def test_forty_eight_per_page_and_links_keep_filters(self):
        pokemon = Pokemon.objects.create(pokedex_number=1, name="Mon")
        for i in range(60):
            PokemonForm.objects.create(pokemon=pokemon, slug=f"f{i}", pokeapi_id=10001 + i, kind="other", label=f"Form {i}")

        first = self.client.get(reverse("forms"), {"kind": "other"})
        second = self.client.get(reverse("forms"), {"page": 2})

        self.assertEqual(len(first.context["page_obj"]), 48)
        self.assertEqual(len(second.context["page_obj"]), 12)
        self.assertContains(first, "kind=other&amp;page=2")


class FormsListEmptyTest(TestCase):

    def test_explains_how_to_get_forms(self):
        response = self.client.get(reverse("forms"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sync_pokemon")

    def test_pokedex_page_has_no_forms_link_when_there_are_none(self):
        self.assertNotContains(self.client.get(reverse("pokedex")), "alternate form")
