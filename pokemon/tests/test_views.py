from django.test import SimpleTestCase
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch ###Makes you allows you to temporarily replace a target with a mock object
from django.test import RequestFactory
from django.http import Http404
from pokemon.views import pokemon_detail, calculate_stat_range
from pokemon.services.pokelance_client import PokelanceAPIError
from pokemon.templatetags.pokemon_extras import get_item
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.template import Context, Template



class PokemonDetailTest(SimpleTestCase):

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
        
        @patch("pokemon.services.build_name_lookup")
        def test_evolution_chain_unknown_name(self, mock_build_name_lookup):
            mock_build_name_lookup.return_value = {
                "gastly": {"name": "Gastly", "sprite_url": "..."},
                "gengar": {"name": "Gengar", "sprite_url": "..."},
            }
            response = self.client.get(reverse("pokemon_detail", args=["Gengar"]))

            self.assertEqual(response.status_code, 200)
            chain = response.context["evolution_chain"]
            names = [stage["name"] for stage in chain]

            self.assertEqual(names, ["Gastly", "Gengar"])
            self.assertNotIn("Haunter", names)
        
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
 
    def test_filter_renders_empty_string_for_missing_key_in_template(self):
        # Django renders None as an empty string when interpolated in a template
        output = self._render(
            "{% load pokemon_extras %}{{ stat_ranges|get_item:stat_name }}",
            {
                "stat_ranges": {"HP": "200-300"},
                "stat_name": "Speed",
            },
        )
        self.assertEqual(output, "")
 
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
        
class HomeViewTest(SimpleTestCase):

    def test_home_view_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        
    def test_home_context_contains_required_data(self):
        response = self.client.get(reverse("home"))
        
        self.assertEqual(response.status_code, 200)

        required_keys = [
            "pokemon_count",
            # "move_count",
            # "ability_count",   
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
        # self.assertIsInstance(context["move_count"], int)
        # self.assertIsInstance(context["ability_count"], int)
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
        
    def test_home_has_correct_number_of_featured_pokemon(self):
        response = self.client.get(reverse("home"))
        context = response.context

        self.assertEqual(
            len(context["featured_pokemon"]),
            settings.FEATURED_POKEMON_COUNT
        )

    @patch("pokemon.views.json.load")
    def test_home_view_has_empty_featured_grid_when_no_pokemon(self, mock_json_load):
        mock_json_load.return_value = []
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["featured_pokemon"], [])
        self.assertIsNone(response.context["hero"])

class SearchViewTest(SimpleTestCase):

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
        mock_sync.return_value = ["Bulbasaur", "Charmander"]
        self.client.force_login(self.staff_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["sync_success"])
        self.assertEqual(response.context["new_pokemon"], ["Bulbasaur", "Charmander"])
        self.assertNotIn("sync_error", response.context)
        mock_sync.assert_called_once()

    @patch("pokemon.views.sync_pokemon_data")
    def test_post_failure_does_not_500(self, mock_sync):
        mock_sync.side_effect = PokelanceAPIError("upstream API unavailable")
        self.client.force_login(self.staff_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sync_error"], "upstream API unavailable")
        self.assertNotIn("sync_success", response.context)
        