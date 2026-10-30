# PokeDatabase — project memory

Django Pokédex app (learning project, built test-first). Single app `pokemon`, no DB models:
all Pokémon data lives in a JSON fixture synced from PokéAPI. Owner: philquake.
All development so far happened in 2026 (Aug 6 – Sep 9); see "2026 timeline" below.

## Stack
- Python 3.14 (CI pins 3.14.2), Django 6.0.7, SQLite (only used for auth/admin), Bootstrap 5.3.5 (vendored in `assets/static/bootstrap-5.3.5-dist`), vanilla JS (`assets/static/js/main.js`).
- `requests` for PokéAPI; Selenium for functional tests; `coverage` for CI.
- `requirements.txt` is **UTF-16 LE with CRLF** — keep that encoding (or convert deliberately) when editing; also contains unused dev packages (jupyter, matplotlib, pandas, djangorestframework).

## Commands
- Run: `python manage.py runserver` → `/` redirects to `/pokemon/`
- Unit tests (what CI runs): `coverage run manage.py test pokemon.tests && coverage report --fail-under=80`
- Functional (Selenium, needs a browser): `python manage.py test functional_test`

## Layout
- `PokeDatabase/urls.py` — `admin/`, `""` → RedirectView to `/pokemon/`, `pokemon/` → `pokemon.urls`.
- `PokeDatabase/settings.py` — `STATICFILES_DIRS = [BASE_DIR/'assets'/'static']`, `APP_DIRS=True`, `DEBUG=True`.
- `pokemon/urls.py` routes (names): `home` (`""`), `search`, `pokedex`, `pokemon_detail` (`pokedex/<str:name>/`), `admin_sync_pokemon` (`admin/sync/`), plus placeholder `types`, `region`, `abilities`, `moves`, `competitive`, `items` (return plain "not implemented" HttpResponse).
- `pokemon/views.py`
  - `home`: random hero (with `type_emoji` from `TYPE_EMOJI`, `top_stats` = top 2 base stats), 8 random `featured_pokemon`, random `explore_pokemon` name, `pokemon_count`. Handles empty data.
  - `pokemon_detail`: case-insensitive name match; context has `pokemon`, `next`/`previous` (fixture order), `evolution_chain` (resolved dicts), `type_defense_order` (`TYPE_DEFENSE_ORDER` 3-letter abbrevs), `stat_ranges` (`calculate_stat_range`, Lv100 min/max formula), `learnt_hm`/`learnt_tm` (`group_hm_tm_moves` — PokéAPI only says "machine", HMs split by a hardcoded name set), `locations`. Unknown name → `Http404`; blank name → redirect home with status 400 + message.
  - `search`: GET `search` param; exact case-insensitive match → redirect to detail; else `messages.error` + redirect home. (Still opens the fixture directly instead of `services.data.load_pokemon_data`.)
  - `admin_sync_pokemon`: `user_passes_test(_is_staff, login_url="home")` so non-staff go home. POST calls `sync_pokemon_data()`; context `sync_success`, `new_pokemon`, `updated_pokemon`, or `sync_error` on `PokelanceAPIError` (never a 500).
- `pokemon/services/data.py` — `FIXTURE_PATH`, `load_pokemon_data()`, `build_name_lookup()`, `get_pokemon_by_name()`.
- `pokemon/services/pokelance_client.py` — PokéAPI sync ("Pokelance" is the project's name for it).
  - `_get(url, context)` wraps all HTTP/JSON failures in `PokelanceAPIError` (5s timeout).
  - Per Pokémon fetches: pokemon, species, evolution chain, type damage relations (cached per sync), encounters → `_to_fixture_entry`.
  - `sync_pokemon_data(count=5, update_existing=True)`: pass 1 appends up to `count` new Pokémon after the highest known dex number (max `count*3` attempts); pass 2 re-fetches every existing entry and patches drifted/missing fields via `_diff_fields` (ignores `pokedex_number`). Writes fixture only if something changed; returns `{"added": [...], "updated": [...]}`.
  - `GENERATIONS` covers gen I–VIII only; unknown generation raises.
- `pokemon/templatetags/pokemon_extras.py` — `get_item` filter (dict lookup by variable key), `has_moves(moves, version, method=None)` and `has_encounters(locations, version)` simple tags used to hide empty tables.
- Templates (`pokemon/templates/`): `base.html` (navbar/header/footer, messages shown on every page), `home.html`, `pokedex.html`, `pokemon_detail.html` (hero section, stat graph, type defenses, evolution partial, moves cards, locations), `admin_sync.html`, `404.html`, `partials/evolution_chain.html`.
- CSS: `styles.css` (global), `pokedex.css`, `pokemon_detail.css` (per-page "extra" CSS block).
- Fixture `assets/static/fixtures/pokemon.json`: ~205 entries (Bulbasaur … dex #265). Entry keys: `pokedex_number, name, image, category, generation, types, base_stats, stat_total, abilities[{name,hidden}], height_m, weight_kg, gender{female_pct,male_pct}|null, egg_groups, catch_rate, base_experience, base_happiness, type_effectiveness{weaknesses,resistances,immunities}, evolution_chain[names], moves[{name,version,level_learnt,method}], locations[{location,version,method,chance,min_level,max_level}]`. Names are capitalized; base_stats keys are `HP, Attack, Defense, Special Attack, Special Defense, Speed`.

## Tests
- `pokemon/tests/`: `test_views.py`, `test_urls.py`, `test_templates.py` (templates extend base, have titles, 404 via `override_settings(DEBUG=False)`), `services/test_pokelance_client.py` (all HTTP mocked with `@patch("pokemon.services.pokelance_client._get")` / `requests.get`).
- `functional_test/`: Selenium tests for home, navigation, pokedex, pokemon_detail, search, api_sync.
- **Tests must never write the real fixture** — patch `_save_fixture`/`_load_fixture` (this bug happened on 2026-08-23).
- Use `reverse()` for URLs in tests; functional tests need explicit waits after redirects.

## Conventions
- Commit prefixes: `feat:`, `fix:`, `test:`, `style:`, `refactor:`, `chore:`, `remove:`. Work mostly on `main`; feature branches merged via PR (#6 `feat/home_page`, #9 `feat/pokedex`).
- TDD: write failing test → implement → refactor.
- Keep data shaping in `pokelance_client` (flatten once), not in templates.

## Gotchas
- `.gitignore` ignores `__init__.py`, so packages (`pokemon/`, `pokemon/tests/`, `templatetags/`, etc.) have no `__init__.py` in a fresh clone — be aware when test discovery or template tag loading misbehaves.
- `.gitignore` also ignores `db.sqlite3` and personal `outline` notes; README mentions `outline.txt`/`db.sqlite3` that aren't in the repo.

## 2026 timeline
- **Aug 6–7** — Project start: `pokemon_detail` page, dummy JSON data instead of hardcoded, first URL/view/search tests, error-message section.
- **Aug 8** — URL routing moved to `pokemon/pokedex/`, messages moved into base, custom 404, nav tests, logo, home revamp (type emoji, random featured Pokémon), LICENSE, README.
- **Aug 9–10** — Hero + featured Pokémon on home, collapsible search bar + JS, Bootstrap folder fix, browse section, `items` view/url, footer, EOP section.
- **Aug 11–12** — `featured_pokemon` → `hero` rename, many view/test fixes (partial-context render bug → redirect, NULL explore_pokemon), custom 404 exception output, tests use `reverse()`. PR #6 merged.
- **Aug 13** — Pokédex page + `pokedex.css`, per-page extra CSS. PR #9 merged.
- **Aug 14–15** — Prev/next Pokémon tests, case-insensitive & nonexistent search tests, `/` redirects to `/pokemon/`.
- **Aug 19** — Functional tests for detail page, templates-extend-base test, `override_settings` 404 test, views refactor.
- **Aug 21** — Detail hero section + stat graph, admin-panel API sync, admin sync writes JSON fixture, stat template tag, fixture data updated.
- **Aug 22–23** — Code cleanup, new header/navbar (Bootstrap sticky instead of custom JS), fixed tests writing the fixture, non-admin redirect to home.
- **Aug 24** — Moves + locations on detail page, apisync & admin sync URL tests, templatetag redundancy reduction, Pokelance client unit tests.
- **Aug 25–26** — Sync adds missing info + moves for all Pokémon, generation fetch tests, `get_item` tests, encounter locations loaded and displayed.
- **Aug 27** — Sync reports added vs updated, variable renames, GitHub Actions coverage gate (80%), requirements updated, `django.yml` fix.
- **Sep 9** — README restructured for clarity (last commit to date).

## Roadmap (from README, not built)
Types/region/abilities/moves/competitive/items pages; richer per-Pokémon data (forms, growth rates); competitive tools (team builder, coverage, comparisons); user accounts/favorites/teams; REST API (`/api/pokemon/`, `/api/types/`, …).
