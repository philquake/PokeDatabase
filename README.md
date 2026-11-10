# PokeDatabase

PokeDatabase is a Django-based Pokémon reference app that catalogs Pokémon data, displays detailed stats, and supports data syncing from the PokéAPI ecosystem. The project blends a searchable Pokédex experience with a lightweight app architecture intended for learning, experimentation, and extension.

## Overview

This project is built around a simple but functional web experience:

- browse a searchable Pokémon catalog
- view detailed Pokémon information pages
- inspect stats, moves, evolution chains, and encounter data
- sync or refresh dataset entries through a staff-only admin flow
- store Pokémon, moves and encounters in a SQLite database, seeded from a JSON file

The app is designed as a practical Django project with an emphasis on data handling, template rendering, and test coverage.

## Features

### Included

- Pokédex listing page
- Individual Pokémon detail views
- Search by Pokémon name
- Featured home page with random Pokémon highlights
- Evolution chain rendering
- Stats and type information
- Shareable comparisons for 2–4 Pokémon, including stats, weaknesses, and stored move overlap
- SQLite-backed data models (Pokémon, moves, encounters) with Django admin
- Staff sync UI for refreshing Pokémon data
- Anonymous, shareable team builder at `/team/` with defensive weaknesses, stored move-type coverage, and coverage suggestions
- Django test suite for application and view-level validation

### Current project status

The app is in active development. Type, region, ability, move, competitive, and item browse pages are implemented. The comparison page accepts two to four stored Pokémon and encodes the selection in repeatable query parameters for sharing.

## Tech Stack

- Python
- Django
- SQLite
- HTML, CSS, and Bootstrap
- JavaScript for front-end interactions
- PokéAPI / Pokélance-style data integration
- Django testing framework

## Project Structure

```text
PokeDatabase/
├── PokeDatabase/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── pokemon/
│   ├── management/commands/
│   │   ├── import_pokemon_json.py
│   │   └── sync_pokemon.py
│   ├── migrations/
│   ├── services/
│   │   ├── data.py
│   │   └── pokelance_client.py
│   ├── templates/
│   │   ├── 404.html
│   │   ├── admin_sync.html
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── pokedex.html
│   │   ├── pokemon_detail.html
│   │   └── partials/
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── pokemon_extras.py
│   ├── tests/
│   │   ├── fixtures/sample_pokemon.json
│   │   ├── services/
│   │   ├── helpers.py
│   │   ├── test_data.py
│   │   ├── test_templates.py
│   │   ├── test_urls.py
│   │   └── test_views.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── assets/
│   └── static/
│       ├── css/
│       ├── fixtures/
│       ├── img/
│       └── js/
├── functional_test/
│   ├── test_api_sync.py
│   ├── test_home.py
│   ├── test_navigation.py
│   ├── test_pokedex.py
│   ├── test_pokemon_detail.py
│   └── test_search.py
├── manage.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/philquake/PokeDatabase.git
cd PokeDatabase
```

### 2. Create a virtual environment

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the database and load the Pokémon data

```bash
python manage.py migrate
python manage.py import_pokemon_json
```

`import_pokemon_json` loads the seed file `assets/static/fixtures/pokemon.json` into `db.sqlite3`. It's safe to run again; existing Pokémon are updated, not duplicated.

### 5. Run the local server

```bash
python manage.py runserver
```

Then visit:

```text
http://127.0.0.1:8000/
```

## App Usage

### Home page

The home page presents a featured Pokémon, a navigation to discovery areas, and a search form.

### Search

Use the search box to find a Pokémon by name. Matching names are resolved to the detail page for the selected Pokémon.

### Pokédex

The Pokédex view lists all catalogued Pokémon and provides direct links to each detail page.

### Pokémon detail

Each detail page includes:

- Pokémon name and Pokédex number
- image and type information
- base stats and stat ranges
- evolution chain
- moves and encounters
- related navigation to previous/next Pokémon

### Team builder

Choose up to six stored Pokémon at `/team/`. The selected team lives in the URL as `?p=bulbasaur,charizard`, so teams can be shared without an account. The analysis summarizes team-wide defensive weaknesses, super-effective coverage from stored damaging move types, and stored Pokémon suggestions that cover gaps. Move coverage depends on move data being present; run `python manage.py sync_moves` to populate it.

### Staff sync

The application includes a staff-only sync page at:

```text
/admin/sync/
```

This page triggers a refresh against the external Pokémon data source and updates the database when new or changed entries are found.

For larger syncs, use the management command instead, since a full refresh takes too long for a web request:

```bash
python manage.py sync_pokemon --count 20             # add 20 new Pokémon, then re-check all stored ones
python manage.py sync_pokemon --count 20 --no-update # only add new Pokémon
```

Each Pokémon is saved as soon as it's fetched, so an interrupted sync keeps its progress.

## Data Source

Pokémon data comes from [PokéAPI](https://pokeapi.co/) and is stored in SQLite through three models in `pokemon/models.py`:

- `Pokemon` — one row per species (stats, types, abilities, matchups, evolution chain, generation and region)
- `PokemonMove` — one row per move / game version / learn method
- `PokemonEncounter` — one row per wild encounter location / game version

`assets/static/fixtures/pokemon.json` is a seed file only; the app never reads it at runtime. The models are also registered in the Django admin (`/admin/`).

## Running Tests

Run the Django test suite with:

```bash
python manage.py test
```

You can also target a specific app or test module if needed.

## Notes

- The project uses SQLite for local development.
- Static assets are served from the `assets/static` directory.
- UI sections such as type, region, abilities, moves, competitive, and items pages are present in the app structure and may be expanded over time.
- This project is suitable for learning Django, API-driven data handling, template logic, and test-driven development.

## License

This project is licensed under the terms of the repository license. See the LICENSE file for details.

* Models
* Views
* Forms
* URL configuration
* Template behavior
* Individual pieces of application logic

Run Django's test suite with:

```bash
python manage.py test
```

### Functional Tests

Functional tests verify application behavior from the user's perspective.

The project uses **Selenium** for browser-based functional testing.

Example:

```bash
python manage.py test functional_tests
```

Functional tests can be used to verify workflows such as:

1. Opening the application
2. Finding the search interface
3. Entering a Pokémon name
4. Submitting the search
5. Verifying the resulting Pokémon information

---

## Test-Driven Development

The project incorporates **Test-Driven Development (TDD)** principles.

The general development cycle is:

```text
Write Test
    ↓
Run Test
    ↓
Test Fails
    ↓
Implement Feature
    ↓
Run Test Again
    ↓
Test Passes
    ↓
Refactor
```

This approach helps ensure that new functionality is supported by automated tests and reduces the likelihood of breaking existing functionality.

---

## Static Files

The application uses Django's static-file system for resources such as:

* CSS
* JavaScript
* Bootstrap
* Images
* Other frontend assets

Static files are organized within the application's `static` directory.

Example:

```django
{% load static %}

<link
    href="{% static 'css/styles.css' %}"
    rel="stylesheet"
>
```

---

## Development Goals

PokeDatabase is intended to evolve beyond a basic Pokémon lookup application.

Potential future development includes building features useful to Pokémon players and developers, including:

### Pokémon Database

Expand the available information for each Pokémon:

* Base stats
* Hidden abilities
* Gender ratios
* Egg groups
* Experience requirements
* Catch rates
* Growth rates
* Forms
* Generational differences

### Competitive Pokémon

A future version could provide tools for competitive players:

* Team building
* Type coverage
* Nature information
* Ability analysis
* Move sets
* Competitive rankings
* Pokémon matchup information

### User Features

Users could eventually:

* Create accounts
* Save favorite Pokémon
* Build Pokémon teams
* Save custom searches
* Track competitive builds

### API

A REST API could eventually allow other applications to access PokeDatabase's processed Pokémon information.

Potential endpoints could include:

```text
/api/pokemon/
/api/pokemon/{id}/
/api/types/
/api/abilities/
/api/moves/
/api/evolutions/
```

---

## Learning Objectives

This project provides practical experience with:

* Python programming
* Django development
* Model-View-Template architecture
* Relational databases
* REST/API integration
* HTML and CSS
* Bootstrap
* JavaScript
* Automated testing
* Selenium
* Test-Driven Development
* Git and GitHub
* Application architecture
* Static file management
* Web application deployment

---

## Future Architecture

The long-term goal is to develop PokeDatabase into a more complete Pokémon information platform.

```text
                    ┌───────────────────┐
                    │     Frontend      │
                    │  HTML/CSS/JS      │
                    │    Bootstrap      │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │      Django       │
                    │ Views / Forms     │
                    │ Application Logic │
                    └─────────┬─────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌─────────────────┐       ┌─────────────────┐
        │    Database     │       │     PokéAPI     │
        │ Pokémon Data    │       │ External Data   │
        └─────────────────┘       └─────────────────┘
```

---

## Contributing

Contributions, suggestions, and improvements are welcome.

A typical development workflow is:

```bash
git pull
```

Create and test your changes:

```bash
python manage.py test
```

Review the changes:

```bash
git diff
```

Commit the changes:

```bash
git add .
git commit -m "Describe your changes"
```

Push the changes:

```bash
git push
```

---

## Disclaimer

Pokémon and all related names, characters, images, and trademarks are the property of their respective owners, including **Nintendo, Game Freak, and Creatures Inc.**

PokeDatabase is an independent educational/development project and is not affiliated with or endorsed by Nintendo, Game Freak, Creatures Inc., or The Pokémon Company.

Pokémon data is sourced or inspired by publicly available resources, including the [PokéAPI](https://pokeapi.co/).

---

## License

See the [`LICENSE`](LICENSE) file for information about the project's licensing terms.
