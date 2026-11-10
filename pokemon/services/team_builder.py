"""Team-wide defensive and known-move type coverage calculations."""

from pokemon.models import Move, Pokemon, PokemonMove
from pokemon.services.types import TYPES, defense_cells, effectiveness


def analyze_team(team):
    """Analyze base Pokémon and suggest stored candidates that cover current gaps."""
    team = list(team)
    team_ids = [pokemon.pk for pokemon in team]
    move_types_by_pokemon = {pokemon_id: set() for pokemon_id in team_ids}
    known_move_counts = {pokemon_id: 0 for pokemon_id in team_ids}

    learned_moves = (
        PokemonMove.objects.filter(pokemon_id__in=team_ids)
        .order_by()
        .values_list("pokemon_id", "name")
        .distinct()
    )
    learned_names_by_pokemon = {pokemon_id: set() for pokemon_id in team_ids}
    for pokemon_id, move_name in learned_moves:
        learned_names_by_pokemon[pokemon_id].add(move_name)

    move_types_by_name = {
        name.casefold(): move_type.lower()
        for name, move_type in Move.objects.filter(
            name__in={
                name
                for names in learned_names_by_pokemon.values()
                for name in names
            },
            damage_class__in=("physical", "special"),
        ).values_list("name", "type")
    }
    known_moves = {pokemon_id: set() for pokemon_id in team_ids}
    for pokemon_id, names in learned_names_by_pokemon.items():
        for name in names:
            move_type = move_types_by_name.get(name.casefold())
            if move_type in TYPES:
                known_moves[pokemon_id].add(name)
                move_types_by_pokemon[pokemon_id].add(move_type)

    for pokemon_id, names in known_moves.items():
        known_move_counts[pokemon_id] = len(names)

    defenses_by_pokemon = {
        pokemon.pk: {
            cell["slug"]: cell for cell in defense_cells(pokemon.types)
        }
        for pokemon in team
    }
    defensive_weaknesses = []
    for attack_type in TYPES:
        weak_members = []
        resist_members = []
        immune_members = []
        for pokemon in team:
            cell = defenses_by_pokemon[pokemon.pk][attack_type]
            member = {"name": pokemon.name, "label": cell["label"]}
            if cell["multiplier"] > 1:
                weak_members.append({**member, "multiplier": cell["multiplier"]})
            elif cell["multiplier"] == 0:
                immune_members.append(member)
            elif cell["multiplier"] < 1:
                resist_members.append(member)
        if weak_members:
            defensive_weaknesses.append({
                "slug": attack_type,
                "name": attack_type.title(),
                "weak_count": len(weak_members),
                "weak_members": weak_members,
                "resist_members": resist_members,
                "immune_members": immune_members,
                "highest_multiplier": max(member["multiplier"] for member in weak_members),
            })
    defensive_weaknesses.sort(key=lambda row: (
        -row["weak_count"], -row["highest_multiplier"], TYPES.index(row["slug"]),
    ))

    team_move_types = set().union(*move_types_by_pokemon.values())
    offensive_coverage = []
    coverage_gaps = []
    for defender in TYPES:
        effective_move_types = [
            move_type
            for move_type in TYPES
            if move_type in team_move_types and effectiveness(move_type, defender) > 1
        ]
        covered = bool(effective_move_types)
        offensive_coverage.append({
            "slug": defender,
            "name": defender.title(),
            "covered": covered,
            "move_types": effective_move_types,
        })
        if not covered:
            coverage_gaps.append(defender)

    team_without_move_data = [
        pokemon.name for pokemon in team if not move_types_by_pokemon[pokemon.pk]
    ]
    suggestions = []
    if coverage_gaps:
        candidates = list(
            Pokemon.objects.exclude(pk__in=team_ids)
            .order_by("pokedex_number")
            .values("id", "name", "pokedex_number", "image", "types")
        )
        candidate_ids = [candidate["id"] for candidate in candidates]
        useful_move_types = [
            move_type
            for move_type in TYPES
            if any(effectiveness(move_type, gap) > 1 for gap in coverage_gaps)
        ]
        useful_move_rows = [
            (name, move_type.lower())
            for name, move_type in Move.objects.filter(
                damage_class__in=("physical", "special"),
            ).values_list("name", "type")
            if move_type.lower() in useful_move_types
        ]
        candidate_type_by_name = {
            name.casefold(): move_type for name, move_type in useful_move_rows
        }
        candidate_move_types = {pokemon_id: set() for pokemon_id in candidate_ids}
        for pokemon_id, move_name in (
            PokemonMove.objects.filter(
                pokemon_id__in=candidate_ids,
                name__in=[name for name, _ in useful_move_rows],
            )
            .order_by()
            .values_list("pokemon_id", "name")
            .distinct()
        ):
            move_type = candidate_type_by_name.get(move_name.casefold())
            if move_type in TYPES:
                candidate_move_types[pokemon_id].add(move_type)

        for candidate in candidates:
            move_types = candidate_move_types[candidate["id"]]
            covers = [
                gap
                for gap in coverage_gaps
                if any(effectiveness(move_type, gap) > 1 for move_type in move_types)
            ]
            if covers:
                suggestions.append({
                    **candidate,
                    "move_types": [move_type for move_type in TYPES if move_type in move_types],
                    "covers": covers,
                    "gap_count": len(covers),
                })
        suggestions.sort(key=lambda candidate: (
            -candidate["gap_count"], candidate["pokedex_number"], candidate["name"].casefold(),
        ))

    return {
        "defensive_weaknesses": defensive_weaknesses,
        "offensive_coverage": offensive_coverage,
        "coverage_gaps": coverage_gaps,
        "team_suggestions": suggestions[:5],
        "team_without_move_data": team_without_move_data,
        "known_move_count": sum(known_move_counts.values()),
    }
