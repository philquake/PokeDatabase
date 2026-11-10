from math import floor


SPEED_LEVELS = (50, 100)
SPEED_SPREADS = (
    ("max", "Max", 252, 1.1),
    ("neutral", "Neutral", 252, 1.0),
    ("uninvested", "Uninvested", 0, 1.0),
    ("speed-nature", "+Speed nature", 0, 1.1),
    ("choice-scarf", "Choice Scarf", 252, 1.1),
)


def calculate_final_stat(base, level, iv=31, ev=252, nature=1.0, is_hp=False):
    """Calculate a non-HP or HP stat from its base stat, IV, EV, level, and nature."""
    stat = ((2 * base + iv + ev // 4) * level) // 100
    if is_hp:
        return stat + level + 10
    return floor(floor(stat + 5) * nature)


def calculate_stat_range(base_stats):
    """Level 100 min/max ranges: 0 IV/EV with hindering nature to max IV/EV with a boost."""
    ranges = {}
    for stat_name, base in base_stats.items():
        is_hp = stat_name == "HP"
        ranges[stat_name] = {
            "min": calculate_final_stat(
                base, 100, iv=0, ev=0, nature=0.9, is_hp=is_hp
            ),
            "max": calculate_final_stat(
                base, 100, iv=31, ev=252, nature=1.1, is_hp=is_hp
            ),
        }
    return ranges


def calculate_speed_tiers(base_speed):
    """Return final Speed values for the common level 50 and 100 spreads."""
    tiers = {}
    for level in SPEED_LEVELS:
        for slug, _, ev, nature in SPEED_SPREADS:
            speed = calculate_final_stat(
                base_speed, level, iv=31, ev=ev, nature=nature
            )
            if slug == "choice-scarf":
                speed = floor(speed * 1.5)
            tiers[f"{slug}-{level}"] = speed
    return tiers
