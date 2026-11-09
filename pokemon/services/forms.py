"""
Alternate forms (regional variants, Megas, Gigantamax and the rest) of a Pokémon.

PokéAPI lists them as extra "varieties" of a species, each its own pokemon resource with
ids from 10001 (e.g. `rattata-alola`, `charizard-mega-x`, `charizard-gmax`). They are stored
as PokemonForm rows attached to the base Pokémon; this module only works out what kind of
form a slug is and what to call it.
"""

REGIONAL_ADJECTIVES = {"alola": "Alolan", "galar": "Galarian", "hisui": "Hisuian", "paldea": "Paldean"}

# (kind, heading) in display order. "mega" also holds Primal Reversion forms.
FORM_KINDS = [
    ("regional", "Regional"),
    ("mega", "Mega & Primal"),
    ("gmax", "Gigantamax"),
    ("other", "Other forms"),
]
FORM_KIND_LABELS = dict(FORM_KINDS)


def classify_form(base_name, species_slug, pokemon_slug):
    """
    {"slug", "kind", "label"} for a form. `slug` is the part after the species name
    ("mega-x", "alola"), unique within a species. `base_name` is the stored Pokémon name
    ("Charizard", "Mr-mime") so labels match the rest of the site.
    """
    prefix = species_slug + "-"
    suffix = pokemon_slug[len(prefix):] if pokemon_slug.startswith(prefix) else pokemon_slug
    parts = suffix.split("-")
    head, rest = parts[0], parts[1:]
    rest_text = " ".join(rest).title()

    if head in REGIONAL_ADJECTIVES:
        label = f"{REGIONAL_ADJECTIVES[head]} {base_name}" + (f" ({rest_text})" if rest else "")
        return {"slug": suffix, "kind": "regional", "label": label}

    if head == "mega":
        # Mega X / Mega Y: a single trailing letter reads better upper-cased.
        tail = " " + (rest[0].upper() if len(rest) == 1 and len(rest[0]) == 1 else rest_text) if rest else ""
        return {"slug": suffix, "kind": "mega", "label": f"Mega {base_name}{tail}"}

    if head == "primal":
        return {"slug": suffix, "kind": "mega", "label": f"Primal {base_name}"}

    if head == "gmax":
        return {"slug": suffix, "kind": "gmax", "label": f"Gigantamax {base_name}"}
    if head == "eternamax":
        return {"slug": suffix, "kind": "gmax", "label": f"Eternamax {base_name}"}

    return {"slug": suffix, "kind": "other", "label": f"{base_name} ({' '.join(parts).title()})"}
