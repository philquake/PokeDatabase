# Django templates can't do stat_ranges[stat_name] with a variable key using dot notation,
# since stat_ranges.stat_name would look for a literal key "stat_name",
# not the loop variable's value. Use a custom template filter

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)