"""
Game-version metadata and the builders that turn a Pokémon's flat move /
encounter rows into the generation -> game -> section structure the detail
page renders with simple loops.
"""

ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX"}

# (PokéAPI version / version-group slug, display label, generation).
VERSION_GROUPS = [
    ("red-blue", "Red/Blue", 1),
    ("yellow", "Yellow", 1),
    ("blue-japan", "Blue (Japan)", 1),
    ("red-green-japan", "Red/Green (Japan)", 1),
    ("gold-silver", "Gold/Silver", 2),
    ("crystal", "Crystal", 2),
    ("ruby-sapphire", "Ruby/Sapphire", 3),
    ("emerald", "Emerald", 3),
    ("firered-leafgreen", "FireRed/LeafGreen", 3),
    ("colosseum", "Colosseum", 3),
    ("xd", "XD", 3),
    ("diamond-pearl", "Diamond/Pearl", 4),
    ("platinum", "Platinum", 4),
    ("heartgold-soulsilver", "HeartGold/SoulSilver", 4),
    ("black-white", "Black/White", 5),
    ("black-2-white-2", "Black 2/White 2", 5),
    ("x-y", "X/Y", 6),
    ("omega-ruby-alpha-sapphire", "Omega Ruby/Alpha Sapphire", 6),
    ("sun-moon", "Sun/Moon", 7),
    ("ultra-sun-ultra-moon", "Ultra Sun/Ultra Moon", 7),
    ("lets-go-pikachu-lets-go-eevee", "Let's Go Pikachu/Eevee", 7),
    ("sword-shield", "Sword/Shield", 8),
    ("brilliant-diamond-shining-pearl", "Brilliant Diamond/Shining Pearl", 8),
    ("legends-arceus", "Legends: Arceus", 8),
    ("scarlet-violet", "Scarlet/Violet", 9),
    ("champions", "Champions", 9),
    # Individual games: PokéAPI reports wild encounters per game, not per version group.
    ("red", "Red", 1), ("blue", "Blue", 1),
    ("red-japan", "Red (Japan)", 1), ("green-japan", "Green (Japan)", 1),
    ("gold", "Gold", 2), ("silver", "Silver", 2),
    ("ruby", "Ruby", 3), ("sapphire", "Sapphire", 3),
    ("firered", "FireRed", 3), ("leafgreen", "LeafGreen", 3),
    ("diamond", "Diamond", 4), ("pearl", "Pearl", 4), ("heartgold", "HeartGold", 4), ("soulsilver", "SoulSilver", 4),
    ("black", "Black", 5), ("white", "White", 5), ("black-2", "Black 2", 5), ("white-2", "White 2", 5),
    ("x", "X", 6), ("y", "Y", 6), ("omega-ruby", "Omega Ruby", 6), ("alpha-sapphire", "Alpha Sapphire", 6),
    ("sun", "Sun", 7), ("moon", "Moon", 7), ("ultra-sun", "Ultra Sun", 7), ("ultra-moon", "Ultra Moon", 7),
    ("lets-go-pikachu", "Let's Go Pikachu", 7), ("lets-go-eevee", "Let's Go Eevee", 7),
    ("sword", "Sword", 8), ("shield", "Shield", 8),
    ("the-isle-of-armor-sword", "Sword: Isle of Armor", 8), ("the-isle-of-armor-shield", "Shield: Isle of Armor", 8),
    ("the-crown-tundra-sword", "Sword: Crown Tundra", 8), ("the-crown-tundra-shield", "Shield: Crown Tundra", 8),
    ("brilliant-diamond", "Brilliant Diamond", 8), ("shining-pearl", "Shining Pearl", 8),
    ("scarlet", "Scarlet", 9), ("violet", "Violet", 9),
    ("the-teal-mask", "Scarlet/Violet: Teal Mask", 9), ("the-indigo-disk", "Scarlet/Violet: Indigo Disk", 9),
]
VERSION_INFO = {slug: (label, gen) for slug, label, gen in VERSION_GROUPS}
VERSION_ORDER = {slug: i for i, (slug, _, _) in enumerate(VERSION_GROUPS)}

# PokéAPI only says "machine" for both, so HMs are identified by name.
HM_NAMES = {
    "Cut", "Fly", "Surf", "Strength", "Flash", "Whirlpool",
    "Waterfall", "Rock Smash", "Dive", "Rock Climb", "Defog",
}

# EXP needed to reach level 100 for each PokéAPI growth-rate slug.
GROWTH_RATE_EXP_100 = {
    "slow": 1_250_000,
    "medium-slow": 1_059_860,
    "medium": 1_000_000,
    "fast": 800_000,
    "slow-then-very-fast": 600_000,   # erratic
    "fast-then-very-slow": 1_640_000,  # fluctuating
}


def version_label_and_gen(slug):
    """Known versions use the table above; an unknown slug lands in the newest generation."""
    if slug in VERSION_INFO:
        return VERSION_INFO[slug]
    return slug.replace("-", " ").title(), max(ROMAN)


def _group_by_generation(version_rows, build_version):
    """
    version_rows: {slug: payload}. Returns generations (ascending) each holding
    its versions in release order. The newest generation, and the first game
    in every generation, are flagged `active` so Bootstrap opens them by default.
    """
    generations = {}
    def release_order(slug):
        _, gen = version_label_and_gen(slug)
        return gen, VERSION_ORDER.get(slug, len(VERSION_ORDER)), slug

    for slug in sorted(version_rows, key=release_order):
        label, gen = version_label_and_gen(slug)
        generations.setdefault(gen, []).append(
            {"slug": slug, "label": label, **build_version(version_rows[slug])}
        )

    result = [
        {"number": gen, "roman": ROMAN.get(gen, str(gen)), "versions": versions, "active": False}
        for gen, versions in sorted(generations.items())
    ]
    for generation in result:
        for i, version in enumerate(generation["versions"]):
            version["active"] = i == 0
    if result:
        result[-1]["active"] = True
    return result


MOVE_STAT_FIELDS = ("type", "damage_class", "power", "accuracy", "pp", "effect")


def build_move_generations(moves, move_info=None):
    """
    Moves grouped generation -> game -> Level up / Egg / Tutor / TM / HM / Other.
    `move_info` ({name: stats dict}, see data.get_move_info) adds each move's type,
    damage class, power, accuracy, PP and effect text; moves without stored stats
    are still listed, with those fields None.
    """
    move_info = move_info or {}

    by_version = {}
    for move in moves:
        by_version.setdefault(move["version"], []).append(move)

    def sections_for(version_moves):
        buckets = {"level-up": [], "egg": [], "tutor": [], "tm": [], "hm": [], "other": []}
        for move in version_moves:
            method = move["method"]
            if method == "machine":
                key = "hm" if move["name"] in HM_NAMES else "tm"
            else:
                key = method if method in buckets else "other"
            buckets[key].append(move)

        titles = [
            ("level-up", "Level up"), ("egg", "Egg moves"), ("tutor", "Tutor"),
            ("tm", "TM"), ("hm", "HM"), ("other", "Other"),
        ]
        sections = []
        for key, title in titles:
            rows = buckets[key]
            if not rows:
                continue
            if key == "level-up":
                rows = sorted(rows, key=lambda m: (m["level_learnt"], m["name"]))
            else:
                rows = sorted(rows, key=lambda m: m["name"])
            sections.append({
                "title": title,
                "show_level": key == "level-up",
                "moves": [
                    {
                        "name": m["name"],
                        "level": m["level_learnt"],
                        **{f: move_info.get(m["name"], {}).get(f) for f in MOVE_STAT_FIELDS},
                    }
                    for m in rows
                ],
            })
        return {"sections": sections, "move_count": len(version_moves)}

    return _group_by_generation(by_version, sections_for)


def build_location_generations(locations):
    """Wild encounters grouped generation -> game, rows sorted and de-duplicated."""
    by_version = {}
    for encounter in locations:
        by_version.setdefault(encounter["version"], []).append(encounter)

    def rows_for(version_encounters):
        seen, rows = set(), []
        for e in sorted(version_encounters, key=lambda e: (e["location"], e["method"], e["min_level"])):
            key = (e["location"], e["method"], e["min_level"], e["max_level"], e["chance"])
            if key not in seen:
                seen.add(key)
                rows.append(e)
        return {"encounters": rows}

    return _group_by_generation(by_version, rows_for)
