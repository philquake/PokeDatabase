# Django templates can't do stat_ranges[stat_name] with a variable key using dot notation,
# since stat_ranges.stat_name would look for a literal key "stat_name",
# not the loop variable's value. Use a custom template filter

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag
def has_moves(moves, version, method=None):
    """
    True if `moves` contains at least one entry matching `version`
    (and `method`, when given). Used to hide a moves-card table
    entirely when that version/method combination has no data,
    instead of rendering an empty table.
    """
    for move in moves:
        if move.get("version") != version:
            continue
        if method is not None and move.get("method") != method:
            continue
        return True
    return False

@register.simple_tag
def has_encounters(locations, version):
    """
    True if `locations` contains at least one wild encounter entry for
    the given `version`. Used to hide a version's encounter table when
    that game has no wild encounters for this Pokémon (evolutions-only,
    starters, event-exclusive, etc.), showing a fallback message instead.
    """
    for encounter in locations:
        if encounter.get("version") == version:
            return True
    return False