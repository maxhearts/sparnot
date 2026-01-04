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
        click.echo(f"CHARACTERS ({len(characters)}):")
        for char_id in characters:
            char_file = project_path / "characters" / f"{char_id}.json"
            if char_file.exists():
                try:
                    with open(char_file) as f:
                        data = json.load(f)
                        name = data.get('name', char_id)
                        role = data.get('role', 'unknown')
                        beliefs = data.get('beliefs', [])
                        personality = data.get('personality_tags', [])
                        click.echo(f"  - {name} ({char_id}): {role}")
                        if beliefs:
                            click.echo(f"    Beliefs: {', '.join(beliefs)}")
                        if personality:
                            click.echo(f"    Personality: {', '.join(personality)}")
                except Exception as e:
                    click.echo(f"  - ⚠ {char_id} (error loading: {e})")
            else:
                click.echo(f"  - ⚠ {char_id} (file not found)")
        click.echo()
    else:
        click.echo("CHARACTERS: None\n")
    
    # Arc - load raw JSON
    arc_file = project_path / "arc.json"
    if arc_file.exists():
        try:
            with open(arc_file) as f:
                data = json.load(f)
                acts = data.get('acts', [])
                scenes = data.get('scenes', [])
                click.echo(f"ARC ({len(acts)} acts, {len(scenes)} scenes):")
                for act in acts:
                    click.echo(f"  Act {act.get('act_id', 'N/A')}: {act.get('act_purpose', 'N/A')}")
                    click.echo(f"    Required scenes: {', '.join(act.get('required_scenes', []))}")
                click.echo()
                for scene in scenes:
                    click.echo(f"  Scene {scene.get('scene_id', 'N/A')} ({scene.get('scene_type', 'N/A')}): {scene.get('summary', 'N/A')}")
                    click.echo(f"    Characters: {', '.join(scene.get('involved_characters', []))}")
                click.echo()
        except Exception as e:
            click.echo(f"ARC: Error loading - {e}\n")
    else:
        click.echo("ARC: Not created\n")


def create_schema_menu(project: str):
    """Show menu for creating schemas."""
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
    """Show menu for editing schemas."""
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
            click.echo("✗ Narrative intent not found. Use 'Create' first.")
            return
        
        data = intent.model_dump()
        result = edit_json(data, NarrativeIntent, "narrative intent")
        if result:
            manager.save_narrative_intent(project, result)
            click.echo("✓ Narrative intent updated!")
    
    elif choice == 2:
        characters = manager.list_characters(project)
        if not characters:
            click.echo("✗ No characters found. Use 'Create' first.")
            return
        
        click.echo("\nCharacters:")
        for i, char_id in enumerate(characters, 1):
            char = manager.load_character(project, char_id, strict=False)
            if char:
                click.echo(f"  {i}. {char.name} ({char.id})")
        
        char_choice = click.prompt(
            "Select character",
            type=click.IntRange(1, len(characters)),
        )
        char_id = characters[char_choice - 1]
        
        char = manager.load_character(project, char_id)
        if char:
            data = char.model_dump()
            result = edit_json(data, CharacterSchema, f"character '{char_id}'")
            if result:
                manager.save_character(project, result)
                click.echo(f"✓ Character '{result.name}' updated!")
    
    elif choice == 3:
        arc = manager.load_arc(project, strict=False)
        if not arc:
            click.echo("✗ Arc not found. Use 'Create' first.")
            return
        
        data = arc.model_dump()
        result = edit_json(data, ArcSkeleton, "arc")
        if result:
            manager.save_arc(project, result)
            click.echo("✓ Arc updated!")


def delete_character_menu(project: str):
    """Show menu for deleting characters."""
    characters = manager.list_characters(project)
    if not characters:
        click.echo("✗ No characters found.")
        return
    
    click.echo("\nCharacters:")
    for i, char_id in enumerate(characters, 1):
        char = manager.load_character(project, char_id)
        if char:
            click.echo(f"  {i}. {char.name} ({char.id})")
    
    char_choice = click.prompt(
        "Select character to delete",
        type=click.IntRange(1, len(characters)),
    )
    char_id = characters[char_choice - 1]
    
    char = manager.load_character(project, char_id)
    if char:
        confirm = click.confirm(f"Delete character '{char.name}'?", default=False)
        if confirm:
            if manager.delete_character(project, char_id):
                click.echo(f"✓ Character '{char.name}' deleted!")
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
        
    except Exception as e:
        click.echo(f"\n✗ Compilation error: {e}", err=True)
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
        
        # Find all scene files
        scene_files = find_scene_files(project_path)
        if not scene_files:
            click.echo(f"\n✗ No generated scenes found in project '{project}'")
            click.echo("  Generate a scene first using generate_scene.py")
            return
        
        # Select scene file
        if len(scene_files) == 1:
            selected_scene_path = scene_files[0]
            click.echo(f"\nUsing scene: {selected_scene_path.name}")
        else:
            click.echo("\nAvailable scenes:")
            for i, scene_file in enumerate(scene_files, 1):
                # Try to load scene to get scene_id for display
                try:
                    with open(scene_file) as f:
                        scene_temp = json.load(f)
                        scene_id_display = scene_temp.get("scene_id", scene_file.name)
                        click.echo(f"  {i}. {scene_file.name} (scene_id: {scene_id_display})")
                except Exception:
                    click.echo(f"  {i}. {scene_file.name}")
            
            choice = click.prompt("\nSelect scene", type=click.IntRange(1, len(scene_files)), default=1)
            selected_scene_path = scene_files[choice - 1]
        
        # Load selected scene data
        scene_data = load_scene_data(selected_scene_path)
        if not scene_data:
            click.echo(f"\n✗ Failed to load scene from {selected_scene_path.name}")
            return
        
        scene_id = scene_data.get("scene_id", "generated_scene_1")
        lock_manager = LockManager(project)
        
        # Show scene info
        click.echo(f"\nScene: {scene_id}")
        click.echo(f"File: {selected_scene_path.name}")
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
                    # Get or create scene locks
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
                
                lock_choice = click.prompt("\nSelect lock to remove", type=click.IntRange(1, len(locks)), default=1)
                lock_id = locks[lock_choice - 1]["lock_id"]
                
                if lock_manager.remove_lock(scene_id, lock_id):
                    click.echo(f"\n✓ Removed lock {lock_id}")
                else:
                    click.echo(f"\n✗ Failed to remove lock {lock_id}")
        
    except Exception as e:
        click.echo(f"\n✗ Lock menu error: {e}", err=True)
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

            # Show menu to select historical version
            click.echo("\nSelect historical compilation to compare:")
            click.echo("  (comparing with current compiled_bundle.json)")
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
        click.echo(f"\n✗ Compilation error: {e}", err=True)
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
        click.echo("  9. Switch project")
        click.echo("  0. Exit")
        
        choice = click.prompt("\nChoice", type=click.IntRange(0, 9), default=0)
        
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
            new_project = select_or_create_project()
            if new_project != project:
                return new_project  # Return new project to update in main loop
        else:
            click.echo("Invalid choice")
    
    return None  # Exit signal


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

