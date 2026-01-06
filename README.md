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

4. Set up OpenAI API key (for scene generation):
   Create a `.env` file in the project root:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   ```

## Quick Start

### CLI

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
   - Compile schemas to IR
   - Compare compilations (diff and propagation)
   - Lock scene content
   - Use the Elicitation Assistant (AI-powered schema refinement)
   - Generate and play scenes
   - Switch projects
   - Exit when done

### Web UI

A FastAPI backend and React frontend provide a visual interface for schema editing, compilation, assistant interaction, and scene playback:

1. Start the backend:
   ```bash
   uvicorn frontend.api.main:app --reload --port 8000
   ```

2. Start the frontend (in `frontend/web/`):
   ```bash
   cd frontend/web
   npm install
   npm run dev
   ```

3. Open `http://localhost:3001` in your browser

**Web UI Features:**
- **Panel 1 (Canon Editor)**: Edit canonical schemas and view/edit assistant drafts
  - Draft files are clearly marked with "📝" and "(DRAFT)" labels
  - Drafts save to workspace, canonical files save to project
  - Auto-refreshes to show assistant changes
- **Panel 2 (Diff Viewer)**: View compilation differences between versions
- **Panel 3 (Assistant)**: Interactive AI assistant with review workflow
  - See compilation status after each assistant suggestion
  - View draft JSON files with selective approval
  - Review and commit changes when ready
- **Panel 4 (Scene Viewer)**: Static viewing of generated scenes
- **Scene Player**: Interactive modal player with automatic text delays and clickable choices

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
  6. Compile project to IR
  7. Compare compilations
  8. Switch project
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

**6. Compile project to IR** - Compiles all schemas to Intermediate Representation (see Compilation section). Automatically saves previous compilation to history.

**7. Compare compilations** - Compare two compilations to see schema changes, IR changes, and propagation (see Compilation Diff section)

**8. Lock scene content** - Lock specific dialogue lines, nodes, or branches in generated scenes to preserve them across regenerations (see Content Locking section)

**9. Elicitation Assistant** - AI-powered assistant that helps refine schemas toward compilable JSONs (see Elicitation Assistant section)

**10. Revert to prior compilation** - Restore project schemas from a previous compilation state

**11. Generate scene** - Generate a scene from the compiled bundle, with selection menu to choose which scene from the arc to generate

**12. Play scene** - Interactively play through a generated scene, with selection menu to choose which scene to play

**13. Switch project** - Returns to project selection menu to choose a different project

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
      compiled_bundle.json  (current compilation, generated by compiler)
      history/  (historical compilations)
        compiled_bundle_20240101_120000.json
        compiled_bundle_20240102_140000.json
      generated_scenes/  (generated scene files)
        generated_scene_scene_1.json
        generated_scene_scene_2.json
      locks.json  (content locks for generated scenes)
      .assistant_workspace/  (temporary workspace for elicitation assistant)
        narrative_intent.json
        arc.json
        characters/
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
  6. Compile project to IR
  7. Compare compilations
  8. Switch project
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
Choice [0]: 6

[Compilation output...]
✓ Compiled bundle saved to: data/projects/my_project/compiled_bundle.json

Press Enter to continue...

==================================================
Project: my_project
==================================================

Main Menu:
  ...
Choice [0]: 7

Comparing:
  Old: compiled_bundle_20240101_120000.json
  New: compiled_bundle.json (current)

[Diff output...]

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

## Compilation

Once your schemas are complete, you can compile them to Intermediate Representations (IRs):

**In the CLI menu:**
- Select option **6. Compile to IR**
- The compiler will:
  - Save previous compilation to `history/` (if exists)
  - Load all schemas from the current project
  - Canonicalize enums and normalize data
  - Generate style tokens, voice tokens, and constraints
  - Separate compiled IR from proposed unknowns and generation context
  - Save `compiled_bundle.json` to the project directory

**Compiled Bundle Structure:**
- `canonical_schemas`: Original schemas
- `ir`: Compiled IRs (NarrativeIR, CharacterIRs, ArcIR)
- `proposed`: Unknown/unmapped inputs that need review
- `generation_context`: Prose and raw text for LLM generation
- `lint`: Warnings and errors
- `hashes`: Deterministic hashes for change detection

**Features:**
- **Deterministic**: Same input always produces same output (no LLM calls)
- **Tolerant**: Uses warnings instead of errors for unknown inputs
- **Canonicalization**: Expansive synonym tables map variations to canonical values
- **Genre-aware**: Detects setting keywords and applies genre-appropriate tokens

## Compilation Diff and Propagation

After compiling your project multiple times, you can compare compilations to understand how schema changes affect the compiled IR.

**In the CLI menu:**
- Select option **7. Compare compilations**
- Select which historical compilation to compare with current `compiled_bundle.json`
- Shows:
  - **Schema Changes**: What fields changed in your schemas
  - **IR Changes**: How the compiled IR changed
  - **Propagation**: Which IR changes were caused by which schema changes

**Features:**
- **Deterministic**: All diffs computed without LLM calls
- **Hash-Optimized**: Uses bundle hashes to skip unchanged components
- **Stable**: Ignores ordering noise (sorted keys, set-like list comparison)
- **Provenance**: Explicit mapping of schema changes to IR changes

**Example Output:**
```
=== Compilation Diff Summary ===
Schema Changes: 2 fields
IR Changes: 3 fields
Propagations: 1 schema → IR mappings

Schema Changes:
  narrative_intent:
    - player_fantasy: "story" → "power"
  
IR Changes:
  narrative_ir:
    - choice_nature_tokens: added ["power_fantasy", "dominance_choice"]
  
Propagation:
  narrative_intent.player_fantasy → narrative_ir.choice_nature_tokens
    IR changed:
      - choice_nature_tokens: added ["power_fantasy", "dominance_choice"]
```

**How it works:**
1. Previous compilations are automatically saved to `history/` when you compile
2. Each compilation includes deterministic hashes for change detection
3. The diff system compares bundles at the schema and IR level
4. Propagation analysis maps schema changes to affected IR fields using rule-based mappings
5. Hash optimization skips unchanged components for fast comparison

## Scene Generation

After compiling your schemas to IR, you can generate sample scenes using the scene generator.

**In the CLI menu:**
- Select option **11. Generate scene**
- Choose which scene from your arc to generate (scenes are grouped by act)
- The scene will be generated and saved to `generated_scenes/generated_scene_{scene_id}.json`

**Command-line usage:**
```bash
# Generate from a project bundle
python generate_scene.py data/projects/Nimbus/compiled_bundle.json

# Generate from a fixture bundle
python generate_scene.py sparnot/poc_compiler/fixtures/action_rpg_postapoc_compiled.json

# Specify custom output path
python generate_scene.py bundle.json output/scene.json
```

**How it works:**
1. Loads the compiled IR bundle (from projects or fixtures)
2. If an arc exists, uses the selected scene with its summary, type, and characters
3. If no arc exists, creates a new scene appropriate for the narrative
4. Uses all IR attributes:
   - NarrativeIR: tone, themes, style tokens, constraints, setting tokens
   - Player fantasy/agency → determines choice count and nature (low: cutscenes, medium: 2-3 options with 1-3 decisions, high: 2-5 options with 1-6 decisions)
   - CharacterIR: voice tokens, beliefs, personality (if characters exist)
   - Generation context: setting, act purposes, scene summaries, invariants
5. Generates branching dialogue with player choices that reflect the game type
6. Includes screenplay (stage directions) and exposition (character internal thoughts)
7. Respects locked content if locks exist for the scene

**Output:**
The generator creates a JSON file with:
- Scene metadata (ID, type, location, summary)
- Dialogue tree with nodes containing:
  - Screenplay (stage directions)
  - Dialogue lines with speaker, text, exposition, and stable line_ids
  - Player choices with convergence hints and branching summaries
- Branching summary and narrative notes explaining how IR attributes were used

**File organization:**
- All generated scenes are saved to `generated_scenes/` subdirectory
- Files are named `generated_scene_{scene_id}.json` to avoid overwriting
- Legacy scenes in project root are still supported

**Requirements:**
- OpenAI API key in `.env` file (see Installation)
- Uses GPT-5-mini model for generation

**Agency-Based Generation:**
- **Low Agency**: Generates cutscenes with no player choices, compensated with significantly more dialogue (4-8 lines per node, 6-10+ nodes, richer exposition)
- **Medium Agency**: 2-3 choice points with 2-3 options each
- **High Agency**: 2-5 choice points with 2-5 options each, more divergent paths

## Scene Playback

You can interactively play through generated scenes to experience the branching dialogue.

**In the CLI menu:**
- Select option **12. Play scene**
- Choose which generated scene to play from the selection menu
- Navigate through dialogue and make choices
- See branching summaries and narrative notes at the end

**In the Web UI:**
- Click "Play Scene" in the header and select a scene
- Interactive modal player opens with:
  - Automatic text delays for dialogue playback
  - Clickable choices (instead of numbered options)
  - Screenplay and exposition displayed with proper formatting
  - Branching summary and narrative notes at the end
- Scene viewer panel remains available for static viewing

**Command-line usage:**
```bash
python play_scene.py data/projects/Nimbus/generated_scenes/generated_scene_scene_1.json
```

**Features:**
- Interactive dialogue tree navigation
- Choice selection (numbered in CLI, clickable in web UI)
- Screenplay and exposition displayed in italics
- Branching summaries shown at the end
- Supports both new dialogue tree format and legacy format

## Content Locking

The content locking system allows you to "lock" specific parts of generated scenes so they persist across regenerations. This is useful for preserving favorite dialogue lines, important character moments, or key narrative beats.

**In the CLI menu:**
- Select option **8. Lock scene content**
- Choose which generated scene to work with
- Select what to lock:
  - **Lock a line**: Preserve a specific dialogue line
  - **Lock a node**: Preserve an entire dialogue node (screenplay + dialogue + choices)
  - **Lock a branch**: Preserve a specific branching path
  - **List locks**: View all locks for the scene

**How it works:**
1. Locks are stored in `locks.json` with stable IDs
2. When regenerating a scene, locked content is included in the "canon pack" sent to the LLM
3. The LLM is instructed to semantically preserve locked content (it can appear anywhere, but must be included)
4. Conflict detection checks for missing characters before generation
5. Scene matching uses scene_id primarily, with fallback to (scene_type + act_id + involved_characters)

**Lock types:**
- **Line locks**: Preserve specific dialogue lines with stable `line_id` format: `{scene_id}:{node_id}:L{n}`
- **Node locks**: Preserve entire dialogue nodes
- **Branch locks**: Preserve branching paths with entry nodes and choice IDs

**Features:**
- Semantic preservation (content must appear, but structure can change)
- Conflict detection (warns if locked content requires characters not in scene)
- Conflict resolution (force participant or orphan lock)
- Stable IDs that survive regeneration

## Elicitation Assistant

The Elicitation Assistant is an AI-powered tool that helps you refine your schemas toward compilable JSONs. It uses a working copy model to make changes safely, runs deterministic diagnostics, and provides streaming LLM-powered conversation.

### Entry Points

1. **CLI Menu**: Select option **9. Elicitation Assistant** from the main menu
2. **Compilation Errors**: When compilation fails, the CLI will offer to use the assistant

### How It Works

1. **Working Copy**: The assistant maintains your schemas in `.assistant_workspace/` - changes are isolated until you commit them
2. **Deterministic Diagnostics**: Runs dry compilation to identify all errors before LLM interaction
3. **AI Conversation**: Uses OpenAI to:
   - Restate understanding of your narrative
   - Suggest improvements for narrative strength
   - Flag compilation concerns in user-understandable terms
   - Propose schema updates as structured JSON
4. **Focus Shift**: Early turns focus on narrative, later turns shift to compliance
5. **Commit Flow**: At session end, review changes and choose to commit, discard, or keep workspace for later

### Workflow

1. Assistant initializes workspace (copies existing schemas or creates empty workspace)
2. Runs diagnostics to identify compilation issues
3. LLM provides opening statement summarizing your project
4. Interactive conversation loop:
   - You provide input
   - Assistant runs diagnostics (deterministic check)
   - LLM responds with suggestions and can propose JSON updates
   - Updates are applied to working copies automatically
   - Diagnostics re-run to show progress
5. End session: Review all changes, then commit to canonical schemas or discard

### Features

- **Safe Editing**: All changes in working copy until explicit commit
- **Deterministic Validation**: Real compilation checks, not just LLM guessing
- **Streaming Responses**: See LLM responses as they're generated
- **JSON Updates**: Assistant can propose schema changes as structured JSON
- **Context-Aware**: Understands CLI navigation, file structure, and schema requirements
- **Consistency Checking**: Performs semantic checks between narrative_intent, characters, and arc schemas
- **Empty Project Support**: Welcomes users with new projects and guides them through initial setup
- **In-Chat Commands**: Use `/status`, `/diff`, and `/help` during conversation
- **Strict Schema Enforcement**: Enforces exact enum values and field formats to prevent validation errors
- **Compilation Status Display**: See compilation errors/warnings after each assistant suggestion
- **Draft Viewing**: View and edit draft schemas in Panel 1 (Canon Editor) with clear visual distinction
- **Review Workflow**: When you say "done", review all changes file-by-file with selective approval
- **Selective Commit**: Approve individual files before committing, matching CLI workflow

### Requirements

- OpenAI API key in `.env` file (same as scene generation)
- Uses GPT-4o-mini model for cost-effective assistance

## Validation

All schemas are validated with Pydantic before saving:
- Required fields must be present
- Types must match (strings, lists, enums, etc.)
- Constraints are enforced (e.g., tone_weights must sum to 1.0, themes must be 3-5 items)
- Validation errors are shown clearly if something is invalid

## Additional Tools

### Compile Fixtures

You can compile fixture JSON files directly:

```bash
# Compile a fixture (saves to fixtures/{name}_compiled.json)
python compile_fixture.py action_rpg_postapoc

# Compile with custom output path
python compile_fixture.py cozy_life_sim /tmp/cozy_bundle.json

# List available fixtures
python compile_fixture.py
```

## Compiler Features

### Canonicalization

The compiler uses expansive rule tables to normalize inputs:

- **Player Fantasy**: Maps synonyms (e.g., "narrative" → "story", "godlike" → "power")
- **Player Agency**: Maps synonyms (e.g., "linear" → "low", "sandbox" → "high")
- **Scene Types**: Maps 20+ scene types with synonyms
- **Personality Tags**: Normalizes tags and maps to voice tokens
- **Invariants**: Uses regex patterns to extract constraints

### Style Tokens

Automatically generates style tokens from:
- Tone weights (tragic, hopeful, humor, mysterious, whimsical)
- Tone interactions (e.g., tragic + humor → "gallows_humor_guardrails")
- Setting keywords (detects genre and applies appropriate tokens)

### Unknown Inputs

Unknown inputs are captured in `proposed`:
- Unmapped enums → defaulted + added to proposed
- Unknown personality tags → added to proposed
- Unmatched invariants → added to proposed + kept in generation_context

## Architecture

For a detailed overview of the system architecture, design decisions, and technical implementation, see [ARCHITECTURE.md](./ARCHITECTURE.md).

