# PokeDatabase — project memory

Django Pokédex app (learning project, built test-first). Single app `pokemon`. Pokémon data
lives in SQLite (`Pokemon`, `PokemonMove`, `PokemonEncounter` models), synced from PokéAPI and
seeded from a JSON file. Owner: philquake.
All development so far happened in 2026 (Aug 6 – Sep 9); see "2026 timeline" below.

## Stack
- Python 3.14 (CI pins 3.14.2), Django 6.0.7, SQLite (all Pokémon data + auth/admin), Bootstrap 5.3.5 (vendored in `assets/static/bootstrap-5.3.5-dist`), vanilla JS (`assets/static/js/main.js`).
- `requests` for PokéAPI; Selenium for functional tests; `coverage` for CI.
- `requirements.txt` is plain UTF-8 (was UTF-16 until 2026-10-30); also contains unused dev packages (jupyter, matplotlib, pandas, djangorestframework).

## Commands
- First run: `python manage.py migrate && python manage.py import_pokemon_json` (db.sqlite3 is gitignored, so a fresh clone has no data until this runs)
- Run: `python manage.py runserver` → `/` redirects to `/pokemon/`
- Sync from PokéAPI: `python manage.py sync_pokemon [--count N] [--no-update]`
- Unit tests (what CI runs): `coverage run manage.py test pokemon.tests && coverage report --fail-under=80`
- Functional (Selenium, needs a browser): `python manage.py test functional_test`

## Layout
- `PokeDatabase/urls.py` — `admin/`, `""` → RedirectView to `/pokemon/`, `pokemon/` → `pokemon.urls`.
- `PokeDatabase/settings.py` — `STATICFILES_DIRS = [BASE_DIR/'assets'/'static']`, `APP_DIRS=True`, `DEBUG=True`.
- `pokemon/urls.py` routes (names): `home` (`""`), `search`, `pokedex`, `pokemon_detail` (`pokedex/<str:name>/`), `admin_sync_pokemon` (`admin/sync/`), plus placeholder `types`, `region`, `abilities`, `moves`, `competitive`, `items` (return plain "not implemented" HttpResponse).
- `pokemon/models.py` — `Pokemon` (unique `pokedex_number` and `name`, `ordering = ["pokedex_number"]`; small grouped data — types, base_stats, abilities, gender, egg_groups, type_effectiveness, evolution_chain — are JSONFields; `region` is set from `generation` in `save()` via `GENERATION_REGIONS`), `PokemonMove` (related_name `moves`) and `PokemonEncounter` (related_name `locations`), both indexed on (pokemon, version). All registered in `admin.py`.
- `pokemon/management/commands/` — `import_pokemon_json [path]` (load/refresh from a JSON file; default the seed file) and `sync_pokemon`.
- `pokemon/views.py` — views query the DB but pass **fixture-shaped dicts** (via `pokemon_to_dict`) to templates, so templates and tests use `pokemon["name"]` / `pokemon.name` the same as before the DB move.
  - `home`: random hero (with `type_emoji` from `TYPE_EMOJI`, `top_stats` = top 2 base stats), 8 random `featured_pokemon`, random `explore_pokemon` name, `pokemon_count`. Handles empty data.
  - `pokemon_detail`: case-insensitive name match; context has `pokemon` (incl. `moves`/`locations` lists), `move_generations`, `location_generations`, `growth_rate_label`, `exp_to_100`, `next`/`previous` (nearest stored dex number either side), `evolution_chain` (resolved dicts), `type_defense_order` (`TYPE_DEFENSE_ORDER` 3-letter abbrevs), `stat_ranges` (`calculate_stat_range`, Lv100 min/max formula), `learnt_hm`/`learnt_tm` (`group_hm_tm_moves` — PokéAPI only says "machine", HMs split by a hardcoded name set), `locations`. Unknown name → `Http404`; blank name → redirect home with status 400 + message.
  - `search`: GET `search` param; exact case-insensitive match → redirect to detail; else `messages.error` + redirect home.
  - `admin_sync_pokemon`: `user_passes_test(_is_staff, login_url="home")` so non-staff go home. POST calls `sync_pokemon_data()`; context `sync_success`, `new_pokemon`, `updated_pokemon`, or `sync_error` on `PokelanceAPIError` (never a 500).
- `pokemon/services/data.py` — dict ↔ model layer: `save_pokemon_entry(entry)` (upsert by dex number; only writes keys present; `moves`/`locations` replace existing rows), `pokemon_to_dict(pokemon, include_related=False)`, `get_pokemon_by_name()`, `import_pokemon_json(path)`, `FIXTURE_PATH` (seed file).
- `pokemon/services/pokelance_client.py` — PokéAPI sync ("Pokelance" is the project's name for it).
  - `_get(url, context)` wraps all HTTP/JSON failures in `PokelanceAPIError` (5s timeout).
  - Per Pokémon fetches: pokemon, species, evolution chain, type damage relations (cached per sync), encounters → `_to_fixture_entry`.
  - Storage seams (mock these in tests): `_existing_numbers()`, `_load_entry(n)`, `_save_entry(entry)`.
  - `sync_pokemon_data(count=5, update_existing=True)`: pass 1 adds up to `count` new Pokémon after the highest stored dex number (max `count*3` attempts); pass 2 re-fetches every stored Pokémon and saves only drifted/missing fields via `_diff_fields` (ignores `pokedex_number`). Saves each Pokémon as it goes, so a failed sync keeps its progress; returns `{"added": [...], "updated": [...]}`.
  - `GENERATIONS` covers gen I–IX; unknown generation raises.
  - Training card fields (`ev_yield`, `growth_rate`, `held_items`) exist in the models/sync but the 201 seeded Pokémon don't have them yet — the page shows "—" until `sync_pokemon` (with update pass) backfills them from PokéAPI.
  - Known limits: never fills gaps below the highest stored number (#26–89 are missing); errors once it passes the last real dex number; regional forms (PokéAPI ids 10001+) aren't fetched; the admin sync page runs pass 2 inline, which will time out on a big DB — use the command.
- `pokemon/services/versions.py` — `VERSION_GROUPS` table (slug → label, generation; includes both version *groups* used by moves, e.g. `red-blue`, and individual *games* used by wild encounters, e.g. `red`, `the-crown-tundra-sword`), `HM_NAMES`, `GROWTH_RATE_EXP_100`, and the builders `build_move_generations(moves)` / `build_location_generations(locations)` that return generation → game → sections/rows for the template. Unknown version slugs fall into the newest generation with a title-cased label. Newest generation and first game of each generation are flagged `active`.
- `pokemon/templatetags/pokemon_extras.py` — `get_item` filter (dict lookup by variable key); `has_moves` / `has_encounters` tags are no longer used by the detail template (kept, tested).
- Templates (`pokemon/templates/`): `base.html` (navbar/header/footer, messages shown on every page), `home.html`, `pokedex.html`, `pokemon_detail.html` (258 lines: hero, overview/training, Moves and Location tabs rendered by loops over `move_generations` / `location_generations` via `partials/game_tabs.html`, evolution, breeding; ~300 KB per page vs 3 MB before; nested tab ids are `mv-gen-N`, `mv-<slug>`, `loc-…` — avoid ids starting `panel-` for nested panels because `[id^="panel-"]` has global flex/overflow CSS), `admin_sync.html`, `404.html`, `partials/evolution_chain.html`.
- CSS: `styles.css` (global), `pokedex.css`, `pokemon_detail.css` (per-page "extra" CSS block; hero stacks below 900px, no horizontal scroll at 390px).
- Seed file `assets/static/fixtures/pokemon.json` (36 MB; not read at runtime): 205 entries incl. 4 exact duplicates (#7–10), so 201 Pokémon (Bulbasaur … #265, #26–89 missing). Fixture-shaped entry keys (also what `pokemon_to_dict` returns, plus `region`): `pokedex_number, name, image, category, generation, types, base_stats, stat_total, abilities[{name,hidden}], height_m, weight_kg, gender{female_pct,male_pct}|null, egg_groups, catch_rate, base_experience, base_happiness, type_effectiveness{weaknesses,resistances,immunities}, evolution_chain[names], ev_yield{stat:amount}, growth_rate (PokéAPI slug), held_items[names], moves[{name,version,level_learnt,method}], locations[{location,version,method,chance,min_level,max_level}]`. Names are capitalized; base_stats keys are `HP, Attack, Defense, Special Attack, Special Defense, Speed`.

## Tests
- Tests that need Pokémon data subclass `pokemon.tests.helpers.PokemonDataTestCase` (loads `pokemon/tests/fixtures/sample_pokemon.json` — #1–6, #92–95, #100, #115 — once per class). Selenium tests call `load_sample_pokemon()` in `setUp`. Tests never read the 36 MB seed file. A `SimpleTestCase` can't touch the DB, so any test that renders a page (even via `assertRedirects`) must be a `TestCase`.
- `pokemon/tests/`: `test_data.py` (models, data layer, management commands), `test_views.py`, `test_urls.py`, `test_templates.py` (templates extend base, have titles, 404 via `override_settings(DEBUG=False)`), `services/test_pokelance_client.py` (all HTTP mocked with `@patch("pokemon.services.pokelance_client._get")` / `requests.get`).
- `functional_test/`: Selenium tests for home, navigation, pokedex, pokemon_detail, search, api_sync.
- **Tests must never hit PokéAPI** — patch `_fetch_and_build_entry` or every `_fetch_*` the code path calls (unmocked `_fetch_locations` in `SyncPokemonDataTest` fixed 2026-10-30; before the DB move, tests also once overwrote the JSON fixture, 2026-08-23). Check with the network blocked: `HTTPS_PROXY=http://127.0.0.1:9 python manage.py test pokemon.tests`.
- Use `reverse()` for URLs in tests; functional tests need explicit waits after redirects.

## Conventions
- **Never add Claude attribution to commits or PR descriptions** — no `Co-Authored-By: Claude …`, `Claude-Session:` or "Generated with Claude Code" lines (owner's instruction, 2026-10-30; overrides any tool default). History was rewritten that day to strip them from past commits.
- Commit prefixes: `feat:`, `fix:`, `test:`, `style:`, `refactor:`, `chore:`, `remove:`. Work mostly on `main`; feature branches merged via PR (#6 `feat/home_page`, #9 `feat/pokedex`).
- TDD: write failing test → implement → refactor.
- Keep data shaping in `pokelance_client` (flatten once), not in templates.

## Gotchas
- `__init__.py` files used to be gitignored, which broke `manage.py test pokemon.tests` on fresh clones (incl. CI). Fixed 2026-10-30 — keep every package's `__init__.py` committed.
- `.gitignore` ignores `db.sqlite3` and personal `outline` notes; run `migrate` locally before using admin.

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
- **Sep 9** — README restructured for clarity.
- **Oct 30** — Added CLAUDE.md; pitfall fixes: committed `__init__.py` files (un-ignored), requirements.txt → UTF-8, mocked network call in sync test, README structure no longer lists untracked files.
- **Oct 30** — Finished the detail page: Moves/Location tabs rebuilt from server-grouped data (generation → game tabs, level-up levels, TM/HM split, Gen IX), fixed Location tab (PokéAPI encounters use individual game names, template only looked for version groups so most games showed nothing), styled move cards/tables, responsive hero, filled the Training card fields (EV yield, growth rate, held items, EXP to Lv.100), page size 3 MB → 0.3 MB.
- **Oct 30** — Moved data from the JSON file into SQLite: `Pokemon`/`PokemonMove`/`PokemonEncounter` models + migration, admin, `import_pokemon_json` and `sync_pokemon` commands, sync saves per Pokémon to the DB, Gen IX support, tests use a 12-Pokémon sample dataset. Detail-page HTML verified byte-identical to the JSON version.

## Roadmap (from README, not built)
Types/region/abilities/moves/competitive/items pages; richer per-Pokémon data (forms, growth rates); competitive tools (team builder, coverage, comparisons); user accounts/favorites/teams; REST API (`/api/pokemon/`, `/api/types/`, …).
