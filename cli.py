"""CLI entry point for Sparnot."""

import json
import click
import sys
from pathlib import Path
from typing import Optional

import sparnot
from sparnot.storage import ProjectManager
from sparnot.utils import (
    edit_json,
    narrative_intent_template,
    character_template,
    arc_template,
)
from sparnot.schemas import (
    NarrativeIntent,
    CharacterSchema,
    ArcSkeleton,
)


# Global project manager
manager = ProjectManager()
current_project_file = Path("data/.current_project")


def get_current_project() -> Optional[str]:
    """Get current project name."""
    if current_project_file.exists():
        return current_project_file.read_text().strip()
    return None


def set_current_project(name: str):
    """Set current project name."""
    current_project_file.parent.mkdir(parents=True, exist_ok=True)
    current_project_file.write_text(name)


def select_or_create_project() -> str:
    """Show menu to select or create project."""
    projects = manager.list_projects()
    
    click.echo("\nProjects:")
    if projects:
        for i, proj in enumerate(projects, 1):
            click.echo(f"  {i}. {proj}")
        click.echo(f"  {len(projects) + 1}. Create new project")
    else:
        click.echo("  (No projects yet)")
        click.echo("  1. Create new project")
    
    if projects:
        choice = click.prompt(
            "\nSelect project or create new",
            type=click.IntRange(1, len(projects) + 1),
            default=len(projects) + 1,
        )
    else:
        choice = 1
    
    if choice <= len(projects):
        project = projects[choice - 1]
    else:
        name = click.prompt("Project name", type=str)
        manager.create_project(name)
        project = name
    
    set_current_project(project)
    click.echo(f"\n✓ Selected project: {project}\n")
    return project


def show_schemas(project: str):
    """Display all schemas in project (raw JSON, no validation)."""
    click.echo(f"\n=== Project: {project} ===\n")
    
    # Narrative Intent - load raw JSON
    project_path = manager.get_project_path(project)
    intent_file = project_path / "narrative_intent.json"
    if intent_file.exists():
        try:
            with open(intent_file) as f:
                data = json.load(f)
                click.echo("NARRATIVE INTENT:")
                click.echo(f"  Logline: {data.get('logline', 'N/A')}")
                click.echo(f"  Setting: {data.get('setting', 'N/A')}")
                click.echo(f"  Themes: {', '.join(data.get('themes', []))}")
                click.echo(f"  Player Fantasy: {data.get('player_fantasy', 'N/A')}")
                click.echo(f"  Player Agency: {data.get('player_agency', 'N/A')}")
                click.echo(f"  Tone Weights: {data.get('tone_weights', {})}")
                if data.get('invariants'):
                    click.echo(f"  Invariants: {', '.join(data.get('invariants', []))}")
                click.echo()
        except Exception as e:
            click.echo(f"NARRATIVE INTENT: Error loading - {e}\n")
    else:
        click.echo("NARRATIVE INTENT: Not created\n")
    
    # Characters - load raw JSON
    characters = manager.list_characters(project)
    if characters:
        click.echo("CHARACTERS:")
        for char_id in characters:
            char_file = project_path / "characters" / f"{char_id}.json"
            if char_file.exists():
                try:
                    with open(char_file) as f:
                        data = json.load(f)
                        name = data.get('name', char_id)
                        role = data.get('role', 'unknown')
                        click.echo(f"  - {name} ({char_id}): {role}")
                except Exception:
                    click.echo(f"  - {char_id} (error loading)")
        click.echo()
    else:
        click.echo("CHARACTERS: None\n")
    
    # Arc - load raw JSON
    arc_file = project_path / "arc.json"
    if arc_file.exists():
        try:
            with open(arc_file) as f:
                data = json.load(f)
                click.echo("ARC:")
                click.echo(f"  Acts: {len(data.get('acts', []))}")
                click.echo(f"  Scenes: {len(data.get('scenes', []))}")
                click.echo()
        except Exception as e:
            click.echo(f"ARC: Error loading - {e}\n")
    else:
        click.echo("ARC: Not created\n")


def create_schema_menu(project: str):
    """Menu for creating schemas."""
    click.echo("\nWhat would you like to create?")
    click.echo("  1. Narrative Intent")
    click.echo("  2. Character")
    click.echo("  3. Arc")
    click.echo("  0. Cancel")
    
    choice = click.prompt("Choice", type=click.IntRange(0, 3), default=0)
    
    if choice == 0:
                return

    if choice == 1:
        template = narrative_intent_template()
        result = edit_json(template, NarrativeIntent, "narrative intent")
        if result:
            manager.save_narrative_intent(project, result)
            click.echo("✓ Narrative intent created!")
    elif choice == 2:
        char_id = click.prompt("Character ID", type=str)
        name = click.prompt("Character name", type=str, default=char_id)
        template = character_template(char_id, name)
        result = edit_json(template, CharacterSchema, "character")
        if result:
            manager.save_character(project, result)
            click.echo(f"✓ Character '{result.name}' created!")
    elif choice == 3:
        template = arc_template()
        result = edit_json(template, ArcSkeleton, "arc")
        if result:
            manager.save_arc(project, result)
            click.echo("✓ Arc created!")


def edit_schema_menu(project: str):
    """Menu for editing schemas."""
    click.echo("\nWhat would you like to edit?")
    click.echo("  1. Narrative Intent")
    click.echo("  2. Character")
    click.echo("  3. Arc")
    click.echo("  0. Cancel")
    
    choice = click.prompt("Choice", type=click.IntRange(0, 3), default=0)
    
    if choice == 0:
        return
    
    if choice == 1:
        intent = manager.load_narrative_intent(project)
        if not intent:
            click.echo("✗ Narrative intent not found. Create it first.")
            return
        
        updated = edit_json(intent.model_dump(), NarrativeIntent, "narrative intent")
        if updated:
            manager.save_narrative_intent(project, updated)
            click.echo("✓ Narrative intent updated!")
    
    elif choice == 2:
        characters = manager.list_characters(project)
        if not characters:
            click.echo("✗ No characters found. Create one first.")
            return
        
        click.echo("\nSelect character to edit:")
        for i, char_id in enumerate(characters, 1):
            char_file = manager.get_project_path(project) / "characters" / f"{char_id}.json"
            if char_file.exists():
                try:
                    with open(char_file) as f:
                        data = json.load(f)
                        name = data.get('name', char_id)
                        click.echo(f"  {i}. {name} ({char_id})")
                except Exception:
                    click.echo(f"  {i}. {char_id}")
        
        char_choice = click.prompt(
            "\nSelect character",
            type=click.IntRange(1, len(characters)),
            default=1,
        )
        char_id = characters[char_choice - 1]
        
        char = manager.load_character(project, char_id, strict=False)
        if not char:
            click.echo(f"✗ Could not load character '{char_id}'")
            return
        
        updated = edit_json(char.model_dump(), CharacterSchema, "character")
        if updated:
            manager.save_character(project, updated)
            click.echo(f"✓ Character '{updated.name}' updated!")
    
    elif choice == 3:
        arc = manager.load_arc(project, strict=False)
        if not arc:
            click.echo("✗ Arc not found. Create it first.")
            return
        
        updated = edit_json(arc.model_dump(), ArcSkeleton, "arc")
        if updated:
            manager.save_arc(project, updated)
            click.echo("✓ Arc updated!")


def delete_character_menu(project: str):
    """Menu for deleting characters."""
    characters = manager.list_characters(project)
    if not characters:
        click.echo("\n✗ No characters found")
        return
    
    click.echo("\nSelect character to delete:")
    for i, char_id in enumerate(characters, 1):
        char_file = manager.get_project_path(project) / "characters" / f"{char_id}.json"
        if char_file.exists():
            try:
                with open(char_file) as f:
                    data = json.load(f)
                    name = data.get('name', char_id)
                    click.echo(f"  {i}. {name} ({char_id})")
            except Exception:
                click.echo(f"  {i}. {char_id}")
    
    char_choice = click.prompt(
        "\nSelect character",
        type=click.IntRange(1, len(characters)),
        default=1,
    )
    char_id = characters[char_choice - 1]
    
    # Confirm deletion
    confirm = click.confirm(f"\nDelete character '{char_id}'?", default=False)
    if confirm:
        if manager.delete_character(project, char_id):
            click.echo(f"✓ Character '{char_id}' deleted!")
        else:
            click.echo(f"✗ Failed to delete character '{char_id}'")


def compile_project_command(project: str):
    """Compile project to IR bundle."""
    try:
        from sparnot.poc_compiler import compile_project
        import json
        
        click.echo(f"\nCompiling project '{project}'...")
        bundle = compile_project(project)
        
        # Save history before overwriting
        manager = ProjectManager()
        history_path = manager.save_compilation_history(project)
        if history_path:
            click.echo(f"✓ Previous compilation saved to: {history_path}")
        
        # Save bundle
        project_path = manager.get_project_path(project)
        bundle_path = project_path / "compiled_bundle.json"
        
        with open(bundle_path, "w") as f:
            json.dump(bundle.model_dump(mode="json"), f, indent=2)
        
        click.echo(f"✓ Compiled bundle saved to: {bundle_path}")
        
        # Show lint report
        if bundle.lint.warnings:
            click.echo(f"\nWarnings ({len(bundle.lint.warnings)}):")
            for warning in bundle.lint.warnings:
                click.echo(f"  ⚠ {warning}")
        
        if bundle.lint.errors:
            click.echo(f"\nErrors ({len(bundle.lint.errors)}):")
            for error in bundle.lint.errors:
                click.echo(f"  ✗ {error}")
        
        if not bundle.lint.warnings and not bundle.lint.errors:
            click.echo("\n✓ No warnings or errors")
        
        # Show hash
        click.echo(f"\nBundle hash: {bundle.hashes['bundle']}")
        
    except ValueError as e:
        # Compilation error - offer assistant
        click.echo(f"\n✗ Compilation error: {e}", err=True)
        click.echo("\nWould you like to:")
        click.echo("  1. Try fixing manually")
        click.echo("  2. Use elicitation assistant")
        click.echo("  3. Continue")
        
        choice = click.prompt("\nChoice", type=click.IntRange(1, 3), default=2)
        
        if choice == 2:
            elicitation_assistant_command(project)
    except Exception as e:
        click.echo(f"\n✗ Compilation error: {e}", err=True)
        import traceback
        traceback.print_exc()


def elicitation_assistant_command(project: str):
    """Run elicitation assistant for schema refinement."""
    try:
        from sparnot.elicitation.assistant import ElicitationAssistant
        
        assistant = ElicitationAssistant()
        assistant.run_assistant_session(project)
    except Exception as e:
        click.echo(f"\n✗ Error in elicitation assistant: {e}", err=True)
        import traceback
        traceback.print_exc()


def compare_compilations_command(project: str, old_path: Optional[Path] = None, new_path: Optional[Path] = None):
    """Compare two compilation bundles."""
    try:
        from sparnot.poc_compiler.diff import compute_compilation_diff
        from sparnot.poc_compiler.diff_display import format_full_diff
        from sparnot.poc_compiler.models import CompiledBundle
        import json
        
        manager = ProjectManager()
        
        # Load bundles
        if old_path is None and new_path is None:
            # Default: current vs selected from history
            new_data = manager.load_compilation(project)
            if not new_data:
                click.echo(f"\n✗ No current compilation found for project '{project}'")
                click.echo("  Compile the project first (option 6)")
                return
            
            history_files = manager.list_compilation_history(project)
            if not history_files:
                click.echo(f"\n✗ No previous compilation found for project '{project}'")
                click.echo("  Compile the project at least twice to compare")
                return

            # Limit to latest 10
            history_files = history_files[:10]
            
            # Show menu to select historical version
            click.echo("\nSelect historical compilation to compare:")
            click.echo("  (comparing with current compiled_bundle.json)")
            if len(manager.list_compilation_history(project)) > 10:
                click.echo(f"  (showing latest 10 of {len(manager.list_compilation_history(project))} total)")
            click.echo()
            for i, hist_file in enumerate(history_files, 1):
                click.echo(f"  {i}. {hist_file.name}")
            
            choice = click.prompt(
                "\nSelect version (or press Enter for latest)",
                type=click.IntRange(1, len(history_files)),
                default=1,
            )
            
            old_path = history_files[choice - 1]
            old_data = manager.load_compilation(project, old_path)
            
            click.echo(f"\nComparing:")
            click.echo(f"  Old: {old_path.name}")
            click.echo(f"  New: compiled_bundle.json (current)")
        else:
            # Custom paths
            if old_path is None or new_path is None:
                click.echo("\n✗ Both old_path and new_path must be provided for custom comparison")
                return

            old_data = manager.load_compilation(project, old_path)
            new_data = manager.load_compilation(project, new_path)
            
            if not old_data:
                click.echo(f"\n✗ Could not load bundle from: {old_path}")
                return
            if not new_data:
                click.echo(f"\n✗ Could not load bundle from: {new_path}")
                return

        # Create CompiledBundle objects
        old_bundle = CompiledBundle(**old_data)
        new_bundle = CompiledBundle(**new_data)
        
        # Compute diff
        diff = compute_compilation_diff(old_bundle, new_bundle)
        
        # Display diff
        click.echo("\n" + format_full_diff(diff))
        
    except Exception as e:
        click.echo(f"\n✗ Comparison error: {e}", err=True)
        import traceback
        traceback.print_exc()


def revert_to_compilation_command(project: str):
    """Revert schemas to a prior compilation's canonical schemas."""
    try:
        from sparnot.poc_compiler.models import CompiledBundle
        import json
        
        manager = ProjectManager()
        
        # Get historical compilations
        history_files = manager.list_compilation_history(project)
        if not history_files:
            click.echo(f"\n✗ No previous compilation found for project '{project}'")
            click.echo("  Compile the project at least once to have a history")
            return

        # Limit to latest 10
        history_files = history_files[:10]
        
        # Show menu to select historical version
        click.echo("\nSelect compilation to revert to:")
        click.echo("  (This will restore schemas from that compilation)")
        if len(manager.list_compilation_history(project)) > 10:
            click.echo(f"  (showing latest 10 of {len(manager.list_compilation_history(project))} total)")
        click.echo()
        for i, hist_file in enumerate(history_files, 1):
            click.echo(f"  {i}. {hist_file.name}")
        
        choice = click.prompt(
            "\nSelect version",
            type=click.IntRange(1, len(history_files)),
            default=1,
        )
        
        selected_path = history_files[choice - 1]
        bundle_data = manager.load_compilation(project, selected_path)
        
        if not bundle_data:
            click.echo(f"\n✗ Could not load bundle from: {selected_path}")
            return
        
        bundle = CompiledBundle(**bundle_data)
        canonical_schemas = bundle.canonical_schemas
        
        # Confirm revert
        click.echo(f"\nThis will overwrite current schemas with schemas from:")
        click.echo(f"  {selected_path.name}")
        click.echo("\nCurrent schemas will be lost!")
        confirm = click.confirm("\nProceed with revert?", default=False)
        
        if not confirm:
            click.echo("Revert cancelled.")
            return
        
        # Restore schemas
        project_path = manager.get_project_path(project)
        restored_count = 0
        
        # Restore narrative_intent
        if canonical_schemas.get("narrative_intent"):
            intent_file = project_path / "narrative_intent.json"
            with open(intent_file, "w") as f:
                json.dump(canonical_schemas["narrative_intent"], f, indent=2)
            restored_count += 1
            click.echo("  ✓ Restored narrative_intent.json")
        
        # Restore arc
        if canonical_schemas.get("arc"):
            arc_file = project_path / "arc.json"
            with open(arc_file, "w") as f:
                json.dump(canonical_schemas["arc"], f, indent=2)
            restored_count += 1
            click.echo("  ✓ Restored arc.json")
        
        # Restore characters
        if canonical_schemas.get("characters"):
            chars_dir = project_path / "characters"
            chars_dir.mkdir(exist_ok=True)
            
            # Remove existing characters not in the bundle
            existing_chars = set(manager.list_characters(project))
            bundle_char_ids = {char.get("id") for char in canonical_schemas["characters"] if char.get("id")}
            
            for char_id in existing_chars - bundle_char_ids:
                char_file = chars_dir / f"{char_id}.json"
                if char_file.exists():
                    char_file.unlink()
            
            # Restore characters from bundle
            for char_data in canonical_schemas["characters"]:
                char_id = char_data.get("id")
                if char_id:
                    char_file = chars_dir / f"{char_id}.json"
                    with open(char_file, "w") as f:
                        json.dump(char_data, f, indent=2)
                    restored_count += 1
            
            if canonical_schemas["characters"]:
                click.echo(f"  ✓ Restored {len(canonical_schemas['characters'])} character(s)")
        
        click.echo(f"\n✓ Reverted {restored_count} schema file(s) from {selected_path.name}")
        
        # Ask if user wants to recompile
        recompile = click.confirm("\nRecompile with restored schemas?", default=True)
        if recompile:
            compile_project_command(project)
        
    except Exception as e:
        click.echo(f"\n✗ Revert error: {e}", err=True)
        import traceback
        traceback.print_exc()


def lock_content_menu(project: str):
    """Interactive menu for locking scene content."""
    try:
        from sparnot.scene_generation.lock_storage import LockManager
        from sparnot.scene_generation.lock_models import SceneLocks
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from cli_lock_helpers import (
            find_scene_files,
            load_scene_data,
            create_line_lock,
            create_node_lock,
            create_branch_lock,
            get_scene_fingerprint,
            list_nodes_in_scene,
            list_lines_in_node,
        )
        
        manager = ProjectManager()
        project_path = manager.get_project_path(project)
        
        # Find all generated scene files
        scene_files = find_scene_files(project_path)
        if not scene_files:
            click.echo(f"\n✗ No generated scenes found in project '{project}'")
            click.echo("  Generate a scene first using generate_scene.py")
            return
        
        selected_scene_path: Path
        if len(scene_files) == 1:
            selected_scene_path = scene_files[0]
            click.echo(f"\nAutomatically selected scene: {selected_scene_path.name}")
        else:
            click.echo("\nAvailable scenes:")
            for i, scene_file in enumerate(scene_files, 1):
                # Try to load scene_id for display
                temp_scene_data = load_scene_data(scene_file)
                scene_display_name = temp_scene_data.get("scene_id", scene_file.name) if temp_scene_data else scene_file.name
                click.echo(f"  {i}. {scene_display_name} ({scene_file.name})")
            
            choice = click.prompt(
                "\nSelect scene to lock content for",
                type=click.IntRange(1, len(scene_files)),
                default=1,
            )
            selected_scene_path = scene_files[choice - 1]
        
        scene_data = load_scene_data(selected_scene_path)
        if not scene_data:
            click.echo(f"\n✗ Failed to load scene data from {selected_scene_path.name}")
            return
        
        scene_id = scene_data.get("scene_id", selected_scene_path.stem)
        lock_manager = LockManager(project)
        
        click.echo(f"\n=== Working with Scene: {scene_id} ({selected_scene_path.name}) ===")
        click.echo(f"Type: {scene_data.get('scene_type', 'unknown')}")
        
        # Lock menu
        while True:
            click.echo("\nLock Menu:")
            click.echo("  1. Lock a line")
            click.echo("  2. Lock a node")
            click.echo("  3. Lock a branch")
            click.echo("  4. List locks")
            click.echo("  5. Remove lock")
            click.echo("  0. Back to main menu")
            
            choice = click.prompt("\nChoice", type=click.IntRange(0, 5), default=0)
            
            if choice == 0:
                break
            elif choice == 1:
                # Lock a line
                nodes = list_nodes_in_scene(scene_data)
                if not nodes:
                    click.echo("\n✗ No nodes found in scene")
                    continue
                
                click.echo("\nAvailable nodes:")
                for i, node_id in enumerate(nodes, 1):
                    click.echo(f"  {i}. {node_id}")
                
                node_choice = click.prompt("\nSelect node", type=click.IntRange(1, len(nodes)), default=1)
                node_id = nodes[node_choice - 1]
                
                lines = list_lines_in_node(scene_data, node_id)
                if not lines:
                    click.echo(f"\n✗ No lines found in node {node_id}")
                    continue
                
                click.echo(f"\nLines in {node_id}:")
                for line_info in lines:
                    click.echo(f"  {line_info['line_number']}. [{line_info['speaker']}] {line_info['text']}")
                
                line_choice = click.prompt("\nSelect line number", type=click.IntRange(1, len(lines)), default=1)
                notes = click.prompt("Notes (optional)", default="", show_default=False)
                
                lock = create_line_lock(scene_data, node_id, line_choice, notes if notes else None)
                if lock:
                    lock_file = lock_manager.load_locks()
                    if scene_id not in lock_file.scene_locks:
                        fingerprint = get_scene_fingerprint(scene_data)
                        lock_file.scene_locks[scene_id] = SceneLocks(
                            scene_fingerprint=fingerprint, locks=[]
                        )
                    lock_manager.add_lock(scene_id, lock)
                    click.echo(f"\n✓ Locked line {line_choice} in {node_id} (lock_id: {lock.lock_id})")
                else:
                    click.echo("\n✗ Failed to create lock")
            
            elif choice == 2:
                # Lock a node
                nodes = list_nodes_in_scene(scene_data)
                if not nodes:
                    click.echo("\n✗ No nodes found in scene")
                    continue
                
                click.echo("\nAvailable nodes:")
                for i, node_id in enumerate(nodes, 1):
                    click.echo(f"  {i}. {node_id}")
                
                node_choice = click.prompt("\nSelect node to lock", type=click.IntRange(1, len(nodes)), default=1)
                node_id = nodes[node_choice - 1]
                notes = click.prompt("Notes (optional)", default="", show_default=False)
                
                lock = create_node_lock(scene_data, node_id, notes if notes else None)
                if lock:
                    lock_file = lock_manager.load_locks()
                    if scene_id not in lock_file.scene_locks:
                        fingerprint = get_scene_fingerprint(scene_data)
                        lock_file.scene_locks[scene_id] = SceneLocks(
                            scene_fingerprint=fingerprint, locks=[]
                        )
                    lock_manager.add_lock(scene_id, lock)
                    click.echo(f"\n✓ Locked node {node_id} (lock_id: {lock.lock_id})")
                else:
                    click.echo("\n✗ Failed to create lock")
            
            elif choice == 3:
                # Lock a branch (simplified for PoC)
                click.echo("\nBranch locking (simplified):")
                entry_node = click.prompt("Entry node ID", type=str)
                choice_ids_str = click.prompt("Choice IDs (comma-separated)", type=str)
                choice_ids = [cid.strip() for cid in choice_ids_str.split(",")]
                required_nodes_str = click.prompt("Required nodes (comma-separated)", type=str)
                required_nodes = [nid.strip() for nid in required_nodes_str.split(",")]
                summary = click.prompt("Branch summary", type=str)
                notes = click.prompt("Notes (optional)", default="", show_default=False)
                
                lock = create_branch_lock(
                    scene_data, entry_node, choice_ids, required_nodes, summary, notes if notes else None
                )
                if lock:
                    lock_file = lock_manager.load_locks()
                    if scene_id not in lock_file.scene_locks:
                        fingerprint = get_scene_fingerprint(scene_data)
                        lock_file.scene_locks[scene_id] = SceneLocks(
                            scene_fingerprint=fingerprint, locks=[]
                        )
                    lock_manager.add_lock(scene_id, lock)
                    click.echo(f"\n✓ Locked branch (lock_id: {lock.lock_id})")
                else:
                    click.echo("\n✗ Failed to create lock")
            
            elif choice == 4:
                # List locks
                locks = lock_manager.list_locks(scene_id)
                if locks:
                    click.echo(f"\nLocks for {scene_id}:")
                    for lock in locks:
                        click.echo(f"  - {lock['lock_id']} ({lock['scope']}): {lock['target']}")
                        if lock.get('notes'):
                            click.echo(f"    Notes: {lock['notes']}")
                else:
                    click.echo(f"\nNo locks found for {scene_id}")
            
            elif choice == 5:
                # Remove lock
                locks = lock_manager.list_locks(scene_id)
                if not locks:
                    click.echo(f"\nNo locks found for {scene_id}")
                    continue
                
                click.echo("\nLocks:")
                for i, lock in enumerate(locks, 1):
                    click.echo(f"  {i}. {lock['lock_id']} ({lock['scope']})")
                
                lock_choice = click.prompt(
                    "\nSelect lock to remove",
                    type=click.IntRange(1, len(locks)),
                    default=1,
                )
                lock_to_remove = locks[lock_choice - 1]
                lock_manager.remove_lock(scene_id, lock_to_remove["lock_id"])
                click.echo(f"\n✓ Removed lock {lock_to_remove['lock_id']}")
            
            click.prompt("\nPress Enter to continue...", default="", show_default=False)

    except Exception as e:
        click.echo(f"\n✗ Error in lock content menu: {e}", err=True)
        import traceback
        traceback.print_exc()


def main_menu(project: str):
    """Show main menu and handle navigation."""
    while True:
        click.echo(f"\n{'='*50}")
        click.echo(f"Project: {project}")
        click.echo(f"{'='*50}")
        click.echo("\nMain Menu:")
        click.echo("  1. Show all schemas")
        click.echo("  2. Create schema")
        click.echo("  3. Edit schema")
        click.echo("  4. List characters")
        click.echo("  5. Delete character")
        click.echo("  6. Compile to IR")
        click.echo("  7. Compare compilations")
        click.echo("  8. Lock scene content")
        click.echo("  9. Elicitation Assistant")
        click.echo("  10. Revert to prior compilation")
        click.echo("  11. Generate scene")
        click.echo("  12. Play scene")
        click.echo("  13. Switch project")
        click.echo("  0. Exit")
        
        choice = click.prompt("\nChoice", type=click.IntRange(0, 13), default=0)
        
        if choice == 0:
            click.echo("\nGoodbye!")
            break
        elif choice == 1:
            show_schemas(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 2:
            create_schema_menu(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 3:
            edit_schema_menu(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 4:
            characters = manager.list_characters(project)
            if characters:
                click.echo(f"\nCharacters in '{project}':")
                project_path = manager.get_project_path(project)
                for char_id in characters:
                    char_file = project_path / "characters" / f"{char_id}.json"
                    if char_file.exists():
                        try:
                            with open(char_file) as f:
                                data = json.load(f)
                                name = data.get('name', char_id)
                                role = data.get('role', 'unknown')
                                click.echo(f"  - {name} ({char_id}): {role}")
                        except Exception:
                            click.echo(f"  - {char_id} (error loading)")
            else:
                click.echo(f"No characters in '{project}'")
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 5:
            delete_character_menu(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 6:
            compile_project_command(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 7:
            compare_compilations_command(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 8:
            lock_content_menu(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 9:
            elicitation_assistant_command(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 10:
            revert_to_compilation_command(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 11:
            generate_scene_command(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 12:
            play_scene_command(project)
            click.prompt("\nPress Enter to continue...", default="", show_default=False)
        elif choice == 13:
            new_project = select_or_create_project()
            if new_project != project:
                return new_project  # Return new project to update in main loop
        else:
            click.echo("Invalid choice")
    
    return None  # Exit signal


def generate_scene_command(project: str):
    """Generate a scene from compiled bundle."""
    project_path = manager.get_project_path(project)
    bundle_path = project_path / "compiled_bundle.json"
    
    if not bundle_path.exists():
        click.echo(f"\n✗ No compiled bundle found for project '{project}'")
        click.echo("Please compile the project first (option 6)")
        return
    
    try:
        from sparnot.scene_generation.lock_storage import LockManager
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_scene import generate_scene
        
        # Initialize lock manager
        lock_manager = LockManager(project, data_dir=manager.data_dir)
        
        # Load arc to show available scenes
        arc = manager.load_arc(project, strict=False)
        
        scene_id = None
        if arc and arc.scenes:
            # Build a map of scenes to acts
            scene_to_act = {}
            if arc.acts:
                for act in arc.acts:
                    for scene_id_ref in act.required_scenes:
                        scene_to_act[scene_id_ref] = act.act_id
            
            # Show available scenes grouped by act
            click.echo(f"\nAvailable scenes in '{project}':")
            scenes_by_act = {}
            for scene in arc.scenes:
                act_id = scene_to_act.get(scene.scene_id, "unassigned")
                if act_id not in scenes_by_act:
                    scenes_by_act[act_id] = []
                scenes_by_act[act_id].append(scene)
            
            # Display scenes grouped by act
            all_scenes = []
            for act_id in sorted(scenes_by_act.keys()):
                scenes = scenes_by_act[act_id]
                click.echo(f"\n  Act: {act_id}")
                for scene in scenes:
                    scene_idx = len(all_scenes) + 1
                    all_scenes.append(scene)
                    click.echo(f"    {scene_idx}. {scene.scene_id} ({scene.scene_type}) - {scene.summary[:60]}...")
            
            if not all_scenes:
                click.echo("  No scenes found")
                return
            
            # Let user select
            choice = click.prompt(f"\nSelect scene to generate (1-{len(all_scenes)})", type=click.IntRange(1, len(all_scenes)))
            selected_scene = all_scenes[choice - 1]
            scene_id = selected_scene.scene_id
            
            click.echo(f"\nGenerating scene: {scene_id} ({selected_scene.scene_type})")
        else:
            # No arc, can still generate a generic scene
            click.echo(f"\nNo arc structure found. Generating a generic scene...")
        
        # Generate scene
        scene_data = generate_scene(
            bundle_path=bundle_path,
            scene_id=scene_id,
            lock_manager=lock_manager
        )
        
        # Determine output filename based on scene_id
        if scene_id:
            # Use scene_id in filename: generated_scene_{scene_id}.json
            safe_scene_id = scene_id.replace("/", "_").replace("\\", "_")
            output_filename = f"generated_scene_{safe_scene_id}.json"
        else:
            # Fallback for generic scenes
            output_filename = "generated_scene.json"
        
        # Save to generated_scenes subdirectory
        scenes_dir = project_path / "generated_scenes"
        scenes_dir.mkdir(exist_ok=True)
        output_path = scenes_dir / output_filename
        
        # Check if file already exists and warn
        if output_path.exists():
            overwrite = click.confirm(f"\n⚠ File {output_filename} already exists. Overwrite?", default=False)
            if not overwrite:
                click.echo("Generation cancelled.")
                return
        
        # Save to generated_scenes directory
        with open(output_path, 'w') as f:
            json.dump(scene_data, f, indent=2)
        
        click.echo(f"\n✓ Scene generated successfully!")
        click.echo(f"Saved to: {output_path}")
        
    except Exception as e:
        click.echo(f"\n✗ Error generating scene: {e}", err=True)
        import traceback
        traceback.print_exc()


def play_scene_command(project: str):
    """Play a generated scene interactively."""
    project_path = manager.get_project_path(project)
    
    # Find all scene files
    from cli_lock_helpers import find_scene_files, load_scene_data
    
    scene_files = find_scene_files(project_path)
    
    if not scene_files:
        click.echo(f"\n✗ No generated scenes found in project '{project}'")
        click.echo("Please generate a scene first (option 11)")
        return

    # Always show selection menu, even if only one scene
    click.echo(f"\nAvailable generated scenes in '{project}':")
    for i, scene_file in enumerate(scene_files, 1):
        scene_data = load_scene_data(scene_file)
        if scene_data:
            scene_id = scene_data.get("scene_id", scene_file.stem)
            scene_type = scene_data.get("scene_type", "unknown")
            summary = scene_data.get("summary", "")[:60]
            click.echo(f"  {i}. {scene_file.name}")
            click.echo(f"     Scene ID: {scene_id} | Type: {scene_type}")
            if summary:
                click.echo(f"     Summary: {summary}...")
        else:
            click.echo(f"  {i}. {scene_file.name} (error loading)")
    
    choice = click.prompt(f"\nSelect scene to play (1-{len(scene_files)})", type=click.IntRange(1, len(scene_files)))
    selected_scene = scene_files[choice - 1]
    
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from play_scene import play_scene
        
        scene_data = load_scene_data(selected_scene)
        scene_id = scene_data.get("scene_id", selected_scene.stem) if scene_data else selected_scene.stem
        click.echo(f"\nPlaying scene: {scene_id} ({selected_scene.name})")
        play_scene(selected_scene)
        
    except Exception as e:
        click.echo(f"\n✗ Error playing scene: {e}", err=True)
        import traceback
        traceback.print_exc()


@click.command()
@click.version_option(version=sparnot.__version__)
def cli():
    """Sparnot: Simple Schema Management CLI - Interactive Mode"""
    # Initialize data directory
    manager.projects_dir.mkdir(parents=True, exist_ok=True)
    
    # Select or create project
    project = select_or_create_project()
    
    # Enter main menu loop
    while project:
        project = main_menu(project)


if __name__ == "__main__":
    cli()
