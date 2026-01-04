"""CLI entry point for Sparnot."""

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
    """Display all schemas in project."""
    click.echo(f"\n=== Project: {project} ===\n")
    
    # Narrative Intent
    intent = manager.load_narrative_intent(project)
    if intent:
        click.echo("NARRATIVE INTENT:")
        click.echo(f"  Logline: {intent.logline}")
        click.echo(f"  Setting: {intent.setting}")
        click.echo(f"  Themes: {', '.join(intent.themes)}")
        click.echo(f"  Player Fantasy: {intent.player_fantasy.value}")
        click.echo(f"  Player Agency: {intent.player_agency.value}")
        click.echo(f"  Tone Weights: {intent.tone_weights}")
        if intent.invariants:
            click.echo(f"  Invariants: {', '.join(intent.invariants)}")
        click.echo()
    else:
        click.echo("NARRATIVE INTENT: Not created\n")
    
    # Characters
    characters = manager.list_characters(project)
    if characters:
        click.echo(f"CHARACTERS ({len(characters)}):")
        for char_id in characters:
            char = manager.load_character(project, char_id)
            if char:
                click.echo(f"  - {char.name} ({char.id}): {char.role.value}")
                click.echo(f"    Beliefs: {', '.join(char.beliefs)}")
                click.echo(f"    Personality: {', '.join(char.personality_tags)}")
            else:
                click.echo(f"  - ⚠ {char_id} (invalid schema - needs editing)")
        click.echo()
    else:
        click.echo("CHARACTERS: None\n")
    
    # Arc
    arc = manager.load_arc(project)
    if arc:
        click.echo(f"ARC ({len(arc.acts)} acts, {len(arc.scenes)} scenes):")
        for act in arc.acts:
            click.echo(f"  Act {act.act_id}: {act.act_purpose}")
            click.echo(f"    Required scenes: {', '.join(act.required_scenes)}")
        click.echo()
        for scene in arc.scenes:
            click.echo(f"  Scene {scene.scene_id} ({scene.scene_type.value}): {scene.summary}")
            click.echo(f"    Characters: {', '.join(scene.involved_characters)}")
        click.echo()
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
            char = manager.load_character(project, char_id)
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
        arc = manager.load_arc(project)
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
        
        # Save bundle
        manager = ProjectManager()
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
        click.echo("  7. Switch project")
        click.echo("  0. Exit")
        
        choice = click.prompt("\nChoice", type=click.IntRange(0, 7), default=0)
        
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
                for char_id in characters:
                    char = manager.load_character(project, char_id)
                    if char:
                        click.echo(f"  - {char.name} ({char.id}): {char.role.value}")
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

