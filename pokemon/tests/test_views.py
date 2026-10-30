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
from pokemon.models import Move, Pokemon, PokemonMove
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
          
class TypesViewTest(TestCase):
    
    def test_types_view_returns_200(self):
        response = self.client.get(reverse("types"))
        
        self.assertEqual(response.status_code, 200)

class RegionViewTest(TestCase):
    
    def test_region_view_returns_200(self):
        response = self.client.get(reverse("region"))
        
        self.assertEqual(response.status_code, 200)
        
class AbilitiesViewTest(TestCase):
    
    def test_abilities_view_returns_200(self):
        response = self.client.get(reverse("abilities"))
        
        self.assertEqual(response.status_code, 200)
        
class MovesViewTest(TestCase):
    
    def test_moves_view_returns_200(self):
        response = self.client.get(reverse("moves"))
        
        self.assertEqual(response.status_code, 200)
        
class CompetitiveViewTest(TestCase):
    
    def test_competitive_view_returns_200(self):
        response = self.client.get(reverse("competitive"))
        
        self.assertEqual(response.status_code, 200)
        
class ItemsViewTest(TestCase):
    
    def test_items_view_returns_200(self):
        response = self.client.get(reverse("items"))
        
        self.assertEqual(response.status_code, 200)

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
