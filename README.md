# PokeDatabase

A Django-based Pokémon database application that retrieves, organizes, and displays Pokémon information using data from the [PokéAPI](https://pokeapi.co/).

The project is designed as both a practical Pokémon lookup application and a learning project for developing web applications with **Python, Django, databases, API integration, HTML/CSS, and Test-Driven Development (TDD)**.

---

## Overview

**PokeDatabase** provides an organized interface for searching and viewing Pokémon information.

The application is being developed with a focus on:

* Django web development
* API integration
* Database design and management
* Automated testing
* Test-Driven Development
* Responsive web design
* Clean and maintainable application structure

Pokémon data can include information such as:

* Pokédex number
* Pokémon name
* Types
* Abilities
* Height
* Weight
* Base statistics
* Sprites and images
* Evolution information
* Generation information

The project can serve as a foundation for a larger Pokémon information and statistics platform.

---

## Features

### Current Features

* Pokémon search
* Pokémon information display
* Integration with Pokémon data sources
* Structured Django application architecture
* HTML templates for displaying Pokémon information
* Static asset management
* Automated unit testing
* Functional testing
* Responsive interface development

### Planned Features

* Advanced Pokémon search and filtering
* Pokémon type filtering
* Evolution chains
* Move database
* Ability database
* Pokémon comparison
* Favorite Pokémon system
* User authentication
* Trainer/user profiles
* Competitive Pokémon statistics
* Pokémon team builder
* REST API
* Improved mobile interface
* Administrative dashboard
* Expanded database functionality

---

## Technology Stack

| Technology | Purpose                                    |
| ---------- | ------------------------------------------ |
| Python     | Primary programming language               |
| Django     | Web application framework                  |
| SQLite     | Development database                       |
| HTML5      | Page structure                             |
| CSS3       | Styling                                    |
| Bootstrap  | Responsive UI components                   |
| JavaScript | Client-side functionality                  |
| PokéAPI    | Pokémon data source                        |
| Pokébase   | Python interface for Pokémon API resources |
| Selenium   | Functional/browser testing                 |
| lxml       | HTML parsing during testing                |
| Git/GitHub | Version control and project hosting        |

---

## Project Structure

The project follows a Django-based structure.

```text
PokeDatabase/
│
├── functional_tests/       # Functional/Selenium tests
│
├── lists/                  # Main Django application
│   ├── migrations/
│   ├── static/
│   │   ├── bootstrap/
│   │   ├── css/
│   │   └── img/
│   │
│   ├── templates/
│   │   └── lists/
│   │
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
│
├── PokeDatabase/            # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── manage.py
├── requirements.txt
├── .gitignore
├── README.md
└── LICENSE
```

> The structure may change as the application develops.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/philquake/PokeDatabase.git
cd PokeDatabase
```

### 2. Create a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If the project is being developed without a `requirements.txt` file yet, install Django and the required testing/API packages separately.

### 4. Run database migrations

```bash
python manage.py migrate
```

### 5. Start the development server

```bash
python manage.py runserver
```

The application can then be accessed through:

```text
http://127.0.0.1:8000/
```

---

## Pokémon Data

PokeDatabase uses Pokémon data from the [PokéAPI](https://pokeapi.co/).

PokéAPI provides structured Pokémon information that can be used to retrieve resources such as:

* Pokémon
* Abilities
* Moves
* Types
* Species
* Evolution chains
* Items
* Berries
* Locations

The application can retrieve API resources and use the information to populate or display Pokémon data.

Example using Pokébase:

```python
import pokebase as pb

pokemon = pb.pokemon("pikachu")

print(pokemon.name)
print(pokemon.height)
print(pokemon.weight)
```

---

## Example

A user can search for a Pokémon such as:

```text
Pikachu
```

The application can display information such as:

```text
Name: Pikachu
Pokédex Number: 25
Type: Electric
Height: 0.4 m
Weight: 6.0 kg
Ability: Static
```

The exact information displayed depends on the application's current implementation and available data.

---

## Testing

Testing is an important part of the project.

PokeDatabase uses both **unit tests** and **functional tests** to verify application behavior.

### Unit Tests

Unit tests are used to test individual components of the application, such as:

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
* Stat comparisons
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
* Compare Pokémon
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
