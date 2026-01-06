# Sparnot Architecture

## Overview

Sparnot is a narrative design tool that helps game developers and writers create, manage, and compile narrative schemas into structured Intermediate Representations (IRs) for use in game engines and content generation systems.

## System Architecture

### High-Level Flow

```
User Input (CLI / Web UI)
    ↓
Schema Management (Pydantic Models)
    ↓
Compiler (Deterministic Rules)
    ↓
Intermediate Representation (IR)
    ↓
Scene Generation (LLM)
    ↓
Generated Scenes (JSON)
    ↓
Scene Playback (Interactive CLI / Web Modal)
```

### Core Components

#### 1. Schema Layer (`sparnot/schemas/`)

**Purpose**: Define and validate canonical narrative design schemas.

**Components**:
- `narrative_intent.py`: NarrativeIntent, PlayerFantasy, PlayerAgency enums
- `character.py`: CharacterSchema, CharacterRole enum
- `arc.py`: ArcSkeleton, Act, Scene, SceneType enum

**Key Features**:
- Pydantic validation ensures data integrity
- Enum types enforce canonical values
- Field validators normalize inputs (e.g., tone_weights normalization)
- Supports both strict (compilation) and non-strict (viewing) loading

#### 2. Storage Layer (`sparnot/storage/`)

**Purpose**: Manage project directories and schema persistence.

**Components**:
- `project_manager.py`: ProjectManager class

**Key Features**:
- Project-based organization (`data/projects/{project_name}/`)
- CRUD operations for all schema types
- Compilation history management
- Character file management (one file per character)

#### 3. Compiler Layer (`sparnot/poc_compiler/`)

**Purpose**: Deterministically compile high-level schemas into structured IRs.

**Components**:
- `compiler.py`: Main compilation logic
- `rules_tables.py`: Canonicalization tables and synonym maps
- `models.py`: IR models (NarrativeIR, CharacterIR, ArcIR, CompiledBundle)
- `hashing.py`: Deterministic hashing for change detection
- `diff.py`: Schema and IR diffing logic
- `propagation.py`: Rule-based propagation analysis
- `diff_display.py`: Human-readable diff formatting

**Key Features**:
- **Deterministic**: Same input always produces same output (no LLM calls)
- **Tolerant**: Uses warnings instead of hard errors for unknown inputs
- **Canonicalization**: Expansive synonym tables map variations to canonical values
- **Genre-aware**: Detects setting keywords and applies appropriate tokens
- **Hash-optimized**: Uses hashes to skip unchanged components during diffs

**Compilation Process**:
1. Load schemas (strict validation)
2. Canonicalize enums (map synonyms to canonical values)
3. Normalize weights (themes, beliefs, tone_weights)
4. Generate style tokens from tone weights
5. Extract voice tokens from personality tags
6. Map player_fantasy/agency to choice constraints
7. Separate compiled IR from proposed unknowns
8. Extract generation context (prose, summaries)
9. Compute hashes for change detection
10. Save compiled bundle

#### 4. Scene Generation Layer (`sparnot/scene_generation/`)

**Purpose**: Generate interactive, branching scenes from compiled IRs using LLMs.

**Components**:
- `generate_scene.py`: Main scene generation script
- `post_process.py`: Add stable line_ids to dialogue
- `lock_models.py`: Lock data models (LineLock, NodeLock, BranchLock)
- `lock_storage.py`: LockManager for persistence
- `canon_pack.py`: Build locked content for LLM injection
- `conflict_detection.py`: Detect conflicts between locks and IR
- `conflict_resolution.py`: Interactive conflict resolution
- `scene_matching.py`: Match scenes to locks after recompiles

**Key Features**:
- LLM-powered generation with structured prompts
- Branching dialogue trees with player choices
- Screenplay (stage directions) and exposition (character thoughts)
- Content locking for preserving favorite moments
- Semantic preservation (locked content must appear, structure can change)
- Conflict detection and resolution
- Stable line_ids for persistent locking

**Generation Process**:
1. Load compiled bundle
2. Determine scene context (from arc or create new)
3. Build comprehensive prompt with:
   - Narrative IR attributes
   - Character IRs for participants
   - Scene summary and type
   - Locked content (if any)
   - Choice constraints based on agency
   - Dialogue compensation for low agency (more dialogue when choices are limited)
4. Generate with OpenAI (GPT-5-mini)
5. Post-process: Add line_ids
6. Save to `generated_scenes/` directory

**Agency-Based Generation:**
- **Low Agency**: No player choices, compensated with 4-8 dialogue lines per node, 6-10+ nodes, richer exposition and detailed screenplay
- **Medium Agency**: 2-3 choice points with 2-3 options each, more convergent paths
- **High Agency**: 2-5 choice points with 2-5 options each, more divergent paths

#### 5. Elicitation Assistant Layer (`sparnot/elicitation/`)

**Purpose**: AI-powered assistant for schema refinement and compliance.

**Components**:
- `assistant.py`: Main orchestrator
- `working_copy.py`: Working copy management (`.assistant_workspace/`)
- `diagnostics.py`: Deterministic diagnostics (dry compilation)
- `conversation.py`: Streaming LLM conversation management
- `consistency.py`: Consistency checking between schemas
- `diff_helpers.py`: JSON diff formatting
- `schema_filter.py`: Filter invalid fields from LLM output

**Key Features**:
- Working copy isolation (changes don't affect canonical until commit)
- Deterministic diagnostics (real compilation, not LLM guessing)
- Streaming responses for better UX
- Structured JSON updates from LLM
- Focus shift (narrative → compliance over conversation)
- Consistency checking (narrative_intent vs. characters/arc)
- Empty project support with welcoming experience
- In-chat commands (`/status`, `/diff`, `/help`)
- Compilation status display after each update
- Draft viewing in web UI (Panel 1)
- Review workflow with selective approval (CLI and web)
- File-by-file review with diff viewing

**Workflow**:
1. Initialize workspace (copy schemas or create empty)
2. Run diagnostics (dry compilation)
3. LLM opening statement
4. Interactive conversation loop:
   - User input
   - Diagnostics re-run
   - LLM response with suggestions
   - JSON updates applied to working copy
   - Compilation status displayed
   - Drafts visible in web UI (Panel 1)
5. End session: Review workflow
   - List all changed files
   - View diffs for each file
   - Approve or skip individual files
   - View full file content if needed
   - Commit selected changes

#### 6. CLI Layer (`cli.py`, `cli_lock_helpers.py`)

**Purpose**: Interactive command-line interface for all functionality.

**Key Features**:
- Menu-driven navigation
- Project selection/creation
- Schema CRUD operations
- Compilation and diff viewing
- Scene generation and playback
- Content locking interface
- Elicitation assistant integration

**Menu Structure**:
- Main menu with 13 options
- Sub-menus for schema creation/editing
- Scene selection menus
- Lock management menus

#### 7. Web Frontend Layer (`frontend/web/`)

**Purpose**: React-based web interface for visual editing and interaction.

**Components**:
- `App.tsx`: Main application orchestrator
- `CanonEditor`: Schema editing with draft viewing
- `DiffViewer`: Compilation diff visualization
- `Assistant`: Interactive assistant panel with review workflow
- `SceneViewer`: Static scene viewing
- `ScenePlayer`: Interactive modal scene playback

**Key Features**:
- **Four-Panel Layout**: Canon Editor, Diff Viewer, Assistant, Scene Viewer
- **Draft Management**: View and edit assistant drafts in Canon Editor with clear visual distinction
- **Interactive Assistant**: Full review workflow with selective approval
- **Scene Playback**: Modal player with automatic delays and clickable choices
- **Real-time Updates**: Auto-refresh for compilation status and draft changes
- **Compilation Status**: Display errors/warnings after assistant suggestions

**Panel Functions**:
- **Panel 1 (Canon Editor)**: Edit canonical schemas and workspace drafts
- **Panel 2 (Diff Viewer)**: View compilation differences
- **Panel 3 (Assistant)**: AI-powered schema refinement with review workflow
- **Panel 4 (Scene Viewer)**: Static viewing of generated scenes

#### 8. API Layer (`frontend/api/`)

**Purpose**: FastAPI backend providing REST endpoints for web frontend.

**Components**:
- `main.py`: FastAPI application with CORS configuration
- `routers/projects.py`: Project management endpoints
- `routers/schemas.py`: Schema CRUD endpoints
- `routers/compile.py`: Compilation and diagnostics endpoints
- `routers/diff.py`: Diff viewing endpoints
- `routers/scenes.py`: Scene generation and retrieval endpoints
- `routers/locks.py`: Content locking endpoints
- `routers/assistant.py`: Assistant interaction endpoints

**Key Features**:
- RESTful API design
- CORS enabled for local development
- Error handling and validation
- Workspace management for assistant drafts
- Selective commit workflow support

## Data Flow

### Compilation Flow

```
User Schemas (JSON)
    ↓
Pydantic Validation
    ↓
Canonicalization (rules_tables.py)
    ↓
IR Generation (compiler.py)
    ↓
Hash Computation (hashing.py)
    ↓
CompiledBundle (JSON)
    ↓
History Storage (history/)
```

### Scene Generation Flow

```
CompiledBundle
    ↓
Scene Selection (from arc or generic)
    ↓
Lock Loading (if exists)
    ↓
Conflict Detection
    ↓
Prompt Building (with canon pack)
    ↓
LLM Generation (OpenAI)
    ↓
Post-processing (line_ids)
    ↓
Generated Scene (JSON)
    ↓
generated_scenes/ directory
```

### Elicitation Flow

```
User Input (CLI / Web UI)
    ↓
Working Copy Update
    ↓
Dry Compilation (diagnostics)
    ↓
LLM Analysis
    ↓
JSON Updates
    ↓
Working Copy Update
    ↓
[Display Compilation Status]
    ↓
[Loop until satisfied]
    ↓
Review & Commit (Selective Approval)
    ↓
Canonical Schemas
```

### Web UI Flow

```
User Opens Web UI
    ↓
Load Project Schemas
    ↓
[Panel 1] Display Canonical + Draft Schemas
[Panel 2] Show Latest Compilation Diff
[Panel 3] Initialize Assistant
[Panel 4] List Generated Scenes
    ↓
User Interacts:
  - Edit schemas (canonical or drafts)
  - Chat with assistant
  - View diffs
  - Generate/play scenes
    ↓
Assistant Suggests Changes
    ↓
[Panel 1] Drafts Auto-Refresh
[Panel 3] Show Compilation Status
    ↓
User Says "done"
    ↓
Review Workflow:
  - List all changed files
  - View diffs
  - Approve/Reject per file
  - Commit selected changes
```

## Key Design Decisions

### 1. Deterministic Compilation

**Decision**: Compiler uses no LLM calls, only deterministic rules.

**Rationale**:
- Reproducibility: Same input always produces same output
- Performance: Fast compilation without API costs
- Debuggability: Clear rules, not black-box LLM behavior
- Version control: Diffs are meaningful and stable

### 2. Working Copy Model for Assistant

**Decision**: Assistant uses isolated workspace, requires explicit commit.

**Rationale**:
- Safety: Changes don't affect canonical until reviewed
- Experimentation: Users can try suggestions without risk
- Transparency: Clear diff between working copy and canonical
- Control: User decides what to commit

### 3. Semantic Content Locking

**Decision**: Locks preserve content semantically, not structurally.

**Rationale**:
- Flexibility: LLM can reorganize structure while preserving content
- Natural integration: Locked content flows naturally into new generation
- User intent: Users care about content, not exact node IDs
- Robustness: Survives structural changes in regenerations

### 4. Hash-Optimized Diffing

**Decision**: Use deterministic hashes to skip unchanged components.

**Rationale**:
- Performance: Fast comparison of large bundles
- Scalability: Works well with many historical compilations
- Stability: Hash-based comparison ignores ordering noise
- Provenance: Can trace changes through hash chains

### 5. Project-Based Organization

**Decision**: All data organized by project in `data/projects/{project}/`.

**Rationale**:
- Isolation: Projects don't interfere with each other
- Portability: Easy to backup/restore individual projects
- Clarity: Clear ownership of schemas and generated content
- Scalability: Can handle many projects efficiently

## File Organization

```
sparnot/
├── schemas/           # Pydantic schema models
├── storage/           # Project management
├── poc_compiler/      # Compiler and IR models
├── scene_generation/  # Scene generation and locking
├── elicitation/       # AI assistant
├── utils/             # JSON editing, templates
└── frontend/
    ├── api/           # FastAPI backend
    │   ├── main.py
    │   └── routers/   # API endpoints
    └── web/           # React frontend
        └── src/
            ├── components/
            │   └── panels/
            │       ├── CanonEditor/
            │       ├── DiffViewer/
            │       ├── Assistant/
            │       ├── SceneViewer/
            │       └── ScenePlayer/
            └── services/  # API client

data/
└── projects/
    └── {project}/
        ├── narrative_intent.json
        ├── arc.json
        ├── characters/
        ├── compiled_bundle.json
        ├── history/
        ├── generated_scenes/
        ├── locks.json
        └── .assistant_workspace/
            ├── narrative_intent.json
            ├── arc.json
            └── characters/
```

