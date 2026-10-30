from django.test import SimpleTestCase

from pokemon.services.versions import (
    GROWTH_RATE_EXP_100,
    build_location_generations,
    build_move_generations,
    version_label_and_gen,
)


def _move(name, version="red-blue", method="level-up", level=0):
    return {"name": name, "version": version, "method": method, "level_learnt": level}


def _encounter(location, version="red", method="Walk", chance=10, min_level=5, max_level=5):
    return {
        "location": location, "version": version, "method": method,
        "chance": chance, "min_level": min_level, "max_level": max_level,
    }


class VersionLabelTests(SimpleTestCase):

    def test_known_version_group_and_individual_game(self):
        self.assertEqual(version_label_and_gen("red-blue"), ("Red/Blue", 1))
        self.assertEqual(version_label_and_gen("the-crown-tundra-sword"), ("Sword: Crown Tundra", 8))

    def test_unknown_version_goes_to_newest_generation_with_readable_label(self):
        self.assertEqual(version_label_and_gen("brand-new-game"), ("Brand New Game", 9))

    def test_growth_rates_cover_every_pokeapi_slug(self):
        self.assertEqual(len(GROWTH_RATE_EXP_100), 6)
        self.assertEqual(GROWTH_RATE_EXP_100["medium-slow"], 1_059_860)


class BuildMoveGenerationsTests(SimpleTestCase):

    def test_empty_moves_give_no_generations(self):
        self.assertEqual(build_move_generations([]), [])

    def test_groups_by_generation_in_release_order_and_flags_defaults(self):
        generations = build_move_generations([
            _move("Tackle", "scarlet-violet"),
            _move("Tackle", "yellow"),
            _move("Tackle", "red-blue"),
            _move("Tackle", "gold-silver"),
        ])

        self.assertEqual([g["number"] for g in generations], [1, 2, 9])
        self.assertEqual([v["slug"] for v in generations[0]["versions"]], ["red-blue", "yellow"])
        self.assertEqual(generations[0]["roman"], "I")
        self.assertEqual([g["active"] for g in generations], [False, False, True])
        self.assertEqual([v["active"] for v in generations[0]["versions"]], [True, False])

    def test_sections_are_split_and_ordered(self):
        moves = [
            _move("Surf", method="machine"),
            _move("Thunderbolt", method="machine"),
            _move("Lick", level=9),
            _move("Hypnosis", level=1),
            _move("Zap Cannon", method="tutor"),
            _move("Bite", method="egg"),
            _move("Pikachu Move", method="form-change"),
        ]

        sections = build_move_generations(moves)[0]["versions"][0]["sections"]

        self.assertEqual(
            [s["title"] for s in sections],
            ["Level up", "Egg moves", "Tutor", "TM", "HM", "Other"],
        )
        self.assertEqual([m["name"] for m in sections[0]["moves"]], ["Hypnosis", "Lick"])
        self.assertTrue(sections[0]["show_level"])
        self.assertFalse(sections[3]["show_level"])
        self.assertEqual([m["name"] for m in sections[3]["moves"]], ["Thunderbolt"])
        self.assertEqual([m["name"] for m in sections[4]["moves"]], ["Surf"])

    def test_only_sections_with_moves_are_returned(self):
        sections = build_move_generations([_move("Tackle", method="egg")])[0]["versions"][0]["sections"]
        self.assertEqual([s["title"] for s in sections], ["Egg moves"])


class BuildLocationGenerationsTests(SimpleTestCase):

    def test_groups_individual_games_and_sorts_rows(self):
        generations = build_location_generations([
            _encounter("Route 2", "blue"),
            _encounter("Route 1", "blue"),
            _encounter("Route 1", "red"),
            _encounter("Route 9", "sword"),
        ])

        self.assertEqual([g["number"] for g in generations], [1, 8])
        self.assertEqual([v["slug"] for v in generations[0]["versions"]], ["red", "blue"])
        blue = generations[0]["versions"][1]
        self.assertEqual([e["location"] for e in blue["encounters"]], ["Route 1", "Route 2"])

    def test_exact_duplicate_rows_are_collapsed(self):
        generations = build_location_generations([_encounter("Route 1"), _encounter("Route 1")])
        self.assertEqual(len(generations[0]["versions"][0]["encounters"]), 1)

    def test_no_encounters_gives_no_generations(self):
        self.assertEqual(build_location_generations([]), [])
