"""
The type effectiveness chart (current rules, Gen VI onwards, incl. Fairy) and helpers.

TYPE_CHART[attacker][defender] is 2, 0.5 or 0; any matchup not listed is neutral (1).
The matchups the sync stores per Pokémon come from PokéAPI; a test checks this chart
reproduces all of them, so typos here get caught.
"""

TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison", "ground",
    "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy",
]

TYPE_CHART = {
    "normal":   {"rock": 0.5, "ghost": 0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2, "bug": 2, "rock": 0.5, "dragon": 0.5, "steel": 2},
    "water":    {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5, "ground": 2, "flying": 0.5,
                 "bug": 0.5, "rock": 2, "dragon": 0.5, "steel": 0.5},
    "ice":      {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 0.5, "ground": 2, "flying": 2,
                 "dragon": 2, "steel": 0.5},
    "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5,
                 "rock": 2, "ghost": 0, "dark": 2, "steel": 2, "fairy": 0.5},
    "poison":   {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2},
    "ground":   {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5,
                 "rock": 2, "steel": 2},
    "flying":   {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2, "poison": 2, "psychic": 0.5, "dark": 0, "steel": 0.5},
    "bug":      {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2,
                 "ghost": 0.5, "dark": 2, "steel": 0.5, "fairy": 0.5},
    "rock":     {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2, "steel": 0.5},
    "ghost":    {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
    "dragon":   {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark":     {"fighting": 0.5, "psychic": 2, "ghost": 2, "dark": 0.5, "fairy": 0.5},
    "steel":    {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2, "rock": 2, "steel": 0.5, "fairy": 2},
    "fairy":    {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2, "dark": 2, "steel": 0.5},
}


def effectiveness(attacker, defender):
    """Damage multiplier of an `attacker`-type move on a `defender`-type Pokémon (lowercase names)."""
    return TYPE_CHART[attacker].get(defender, 1)


def type_matchups(type_name):
    """
    What a type does and what it takes (as a single type), each list in the standard
    type order: {"attack": {"super", "not_very", "no_effect"}, "defend": {"weak", "resist", "immune"}}.
    """
    def attacking(multiplier):
        return [d for d in TYPES if effectiveness(type_name, d) == multiplier]

    def defending(multiplier):
        return [a for a in TYPES if effectiveness(a, type_name) == multiplier]

    return {
        "attack": {"super": attacking(2), "not_very": attacking(0.5), "no_effect": attacking(0)},
        "defend": {"weak": defending(2), "resist": defending(0.5), "immune": defending(0)},
    }


# Defence-chart cell states by damage multiplier (a Pokémon has at most two types: 0, 1/4 ... 4).
_DEFENSE_STATES = {4: "x4", 2: "x2", 1: "x1", 0.5: "half", 0.25: "quarter", 0: "immune"}
_DEFENSE_LABELS = {4: "4×", 2: "2×", 1: "1×", 0.5: "½×", 0.25: "¼×", 0: "0×"}


def defense_cells(defending_types):
    """
    One cell per attacking type (standard order) for a Pokémon with these type(s):
    {"slug", "name", "multiplier", "label", "state"}. Multipliers stack across both
    types, so a Fire/Flying Pokémon takes 4x from Rock and 1/4x from Grass. Names that
    aren't real types are ignored.
    """
    defending = [t.lower() for t in defending_types if t.lower() in TYPE_CHART]
    cells = []
    for attacker in TYPES:
        multiplier = 1
        for defender in defending:
            multiplier *= effectiveness(attacker, defender)
        cells.append({
            "slug": attacker,
            "name": attacker.title(),
            "multiplier": multiplier,
            "label": _DEFENSE_LABELS[multiplier],
            "state": _DEFENSE_STATES[multiplier],
        })
    return cells
