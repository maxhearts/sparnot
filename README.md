# Sparnot: Simple Schema Management CLI

A simple command-line tool for managing narrative design schemas. Create projects, define schemas (narrative intent, characters, arcs), and edit them with JSON validation.

## Overview

Sparnot helps you organize narrative design schemas into projects. Each project contains:
- **Narrative Intent**: Logline, themes, tone weights, player fantasy, setting, etc.
- **Characters**: Character definitions with roles, beliefs, and personality traits
- **Arc**: Narrative structure with acts and scenes

All schemas are validated with Pydantic before saving, ensuring data integrity.

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

1. Run the CLI:
   ```bash
   python cli.py
   ```

2. Select or create a project from the menu

3. You'll enter the main interactive menu where you can:
   - View all schemas
   - Create new schemas
   - Edit existing schemas
   - Manage characters
   - Switch projects
   - Exit when done

## Interactive CLI

The CLI runs in an interactive menu-driven mode. Once started, you navigate through menus to access all functionality without exiting.

### Main Menu

When you run `python cli.py`, you'll see:

```
==================================================
Project: my_project
==================================================

Main Menu:
  1. Show all schemas
  2. Create schema
  3. Edit schema
  4. List characters
  5. Delete character
  6. Switch project
  0. Exit
```

### Menu Options

**1. Show all schemas** - Displays all schemas in the current project (narrative intent, characters, arc)

**2. Create schema** - Opens a submenu to create:
   - Narrative Intent
   - Character (prompts for ID and name)
   - Arc
   Each opens your editor with a JSON template

**3. Edit schema** - Opens a submenu to edit:
   - Narrative Intent
   - Character (shows list to select from)
   - Arc
   Opens existing schema in editor for modification

**4. List characters** - Shows all characters in the current project

**5. Delete character** - Shows character list, select one to delete (with confirmation)

**6. Switch project** - Returns to project selection menu to choose a different project

**0. Exit** - Exits the CLI

## Schema Types

### Narrative Intent

Required fields:
- `logline`: One-sentence summary
- `tone_weights`: Dict with keys: tragic, hopeful, humor, mysterious, whimsical (must sum to 1.0)
- `themes`: List of 3-5 theme strings
- `player_fantasy`: One of: power, exploration, story, social, creation, challenge
- `player_agency`: One of: high, medium, low
- `setting`: Setting description
- `invariants`: Optional list of 0-4 invariant strings

### Character

Required fields:
- `id`: Unique character identifier
- `name`: Character name
- `role`: One of: protagonist, antagonist, supporting, mentor, foil
- `beliefs`: List of belief statements
- `personality_tags`: List of personality descriptors

### Arc

Required fields:
- `acts`: List of acts, each with:
  - `act_id`: Unique identifier
  - `act_purpose`: Purpose description
  - `required_scenes`: List of scene IDs
- `scenes`: List of scenes, each with:
  - `scene_id`: Unique identifier
  - `scene_type`: One of: inciting_incident, first_plot_point, midpoint, second_plot_point, climax, resolution, transition, character_development, world_building, tension_release
  - `summary`: Scene summary
  - `involved_characters`: List of character IDs

## Project Structure

Projects are stored in `data/projects/{project_name}/`:

```
data/
  projects/
    my_project/
      narrative_intent.json
      characters/
        eli.json
        javi.json
      arc.json
  .current_project  (stores currently selected project)
```

## JSON Editing

When creating or editing schemas:
1. The CLI opens a temporary JSON file in your system editor (`$EDITOR` or falls back to `nano`/`vim`)
2. You edit the JSON directly
3. On save and close, validates against the Pydantic schema
4. If valid, saves to the project and returns to menu
5. If invalid, shows validation errors and offers to retry editing

The editor uses your system's default editor. Set `$EDITOR` environment variable to use a specific editor:
```bash
export EDITOR=vim  # or nano, code, etc.
python cli.py
```

## Example Session

```bash
$ python cli.py

Projects:
  1. my_project
  2. another_project
  3. Create new project

Select project or create new [3]: 1

✓ Selected project: my_project

==================================================
Project: my_project
==================================================

Main Menu:
  1. Show all schemas
  2. Create schema
  3. Edit schema
  4. List characters
  5. Delete character
  6. Switch project
  0. Exit

Choice [0]: 2

What would you like to create?
  1. Narrative Intent
  2. Character
  3. Arc
  0. Cancel
Choice: 1
[Editor opens with template...]
✓ Narrative intent created!

Press Enter to continue...

==================================================
Project: my_project
==================================================

Main Menu:
  ...
Choice [0]: 1

=== Project: my_project ===

NARRATIVE INTENT:
  Logline: A story about...
  Setting: Post-apocalyptic sky cities
  Themes: survival, power, choice
  Player Fantasy: story
  Player Agency: high
  Tone Weights: {'tragic': 0.3, 'hopeful': 0.2, ...}

CHARACTERS: None

ARC: Not created

Press Enter to continue...
```

## Validation

All schemas are validated with Pydantic before saving:
- Required fields must be present
- Types must match (strings, lists, enums, etc.)
- Constraints are enforced (e.g., tone_weights must sum to 1.0, themes must be 3-5 items)
- Validation errors are shown clearly if something is invalid

## License

[Add your license here]

