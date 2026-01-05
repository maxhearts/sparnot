"""Main assistant orchestrator for elicitation sessions."""

import click
import json
import shutil
from pathlib import Path
from typing import Optional

from .working_copy import WorkingCopyManager
from .diagnostics import DiagnosticsRunner
from .conversation import ConversationManager
from .diff_helpers import get_file_diff
from .schema_filter import filter_character_data
from .consistency import ConsistencyChecker


class ElicitationAssistant:
    """Main orchestrator for elicitation assistant sessions."""
    
    def __init__(self, data_dir: Path = Path("data")):
        """Initialize assistant."""
        self.working_copy_manager = WorkingCopyManager(data_dir)
        self.diagnostics_runner = DiagnosticsRunner(data_dir)
        self.conversation_manager = ConversationManager()
        self.consistency_checker = ConsistencyChecker()
    
    def run_assistant_session(self, project: str) -> None:
        """Main entry point for assistant session."""
        try:
            # Initialize session
            workspace_path = self.initialize_session(project)
            
            # Run initial diagnostics
            diagnostics = self.diagnostics_runner.run_diagnostics(project, workspace_path)
            
            # Start conversation
            opening_message = self.conversation_manager.start_conversation(
                project, diagnostics, self.working_copy_manager, self.consistency_checker
            )
            
            click.echo("\n" + "="*60)
            click.echo("Elicitation Assistant")
            click.echo("="*60)
            click.echo("\n" + opening_message)
            click.echo("\n" + "-"*60)
            
            # Conversation loop
            self.conversation_loop(project)
            
            # End session
            self.end_session(project)
            
        except KeyboardInterrupt:
            click.echo("\n\nSession interrupted.")
            self.end_session(project)
        except Exception as e:
            click.echo(f"\n✗ Error in assistant session: {e}", err=True)
            import traceback
            traceback.print_exc()
            self.end_session(project)
    
    def initialize_session(self, project: str) -> Path:
        """Set up workspace and run initial diagnostics."""
        workspace_path = self.working_copy_manager.initialize_workspace(project)
        return workspace_path
    
    def conversation_loop(self, project: str) -> None:
        """Interactive streaming conversation loop."""
        workspace_path = self.working_copy_manager.get_workspace_path(project)
        
        # Show help at start
        self._show_help()
        
        while True:
            # Get user input
            user_message = click.prompt("\nYou", type=str, default="")
            
            if not user_message.strip():
                continue
            
            user_message_lower = user_message.strip().lower()
            
            # Handle CLI commands
            if user_message_lower.startswith("/"):
                self._handle_command(user_message_lower, project, workspace_path)
                continue
            
            if user_message_lower in ["exit", "quit", "done"]:
                break
            
            # Run diagnostics before processing
            diagnostics = self.diagnostics_runner.run_diagnostics(project, workspace_path)
            
            # Process user message
            try:
                response_text, json_updates = self.conversation_manager.process_user_message(
                    user_message,
                    project,
                    diagnostics,
                    self.working_copy_manager,
                )
                
                # If LLM returned JSON updates, apply them to working copies
                if json_updates and "updates" in json_updates:
                    click.echo("\n" + "-"*60)
                    click.echo("Applying schema updates...")
                    self.apply_json_updates(project, json_updates["updates"])
                    
                    # Re-run diagnostics after updates
                    diagnostics = self.diagnostics_runner.run_diagnostics(project, workspace_path)
                    
                    # Show updated diagnostics
                    if diagnostics.can_compile and not diagnostics.errors:
                        click.echo("✓ Schemas are now compilable!")
                    elif diagnostics.errors:
                        click.echo(f"✗ {len(diagnostics.errors)} compilation error(s) remaining")
                    
                    click.echo("-"*60)
                
            except Exception as e:
                click.echo(f"\n✗ Error processing message: {e}", err=True)
                import traceback
                traceback.print_exc()
    
    def apply_json_updates(self, project: str, updates: list) -> None:
        """Apply JSON updates to working copies."""
        narrative_intent_updated = False
        
        for update in updates:
            schema_type = update.get("schema_type")
            schema_id = update.get("schema_id")
            action = update.get("action", "update")
            data = update.get("data")
            
            if not schema_type or not data:
                continue
            
            # Track if narrative_intent was updated
            if schema_type == "narrative_intent":
                narrative_intent_updated = True
            
            try:
                if action == "create" or action == "update":
                    # Filter invalid fields before saving
                    if schema_type == "character":
                        data = filter_character_data(data)
                    
                    self.working_copy_manager.save_working_copy(
                        project, schema_type, data, schema_id
                    )
                    action_label = "Created" if action == "create" else "Updated"
                    schema_label = schema_type
                    if schema_id:
                        schema_label = f"{schema_label} ({schema_id})"
                    click.echo(f"  ✓ {action_label} {schema_label}")
            except Exception as e:
                click.echo(f"  ✗ Error applying update to {schema_type}: {e}", err=True)
        
        # If narrative_intent was updated, run consistency check
        if narrative_intent_updated:
            self._run_consistency_check_and_report(project)
    
    def _run_consistency_check_and_report(self, project: str) -> None:
        """Run consistency check and display results."""
        # Load current schemas from workspace
        narrative_intent = self.working_copy_manager.load_working_copy(project, "narrative_intent")
        if not narrative_intent:
            return
        
        characters = []
        for char_id in self.working_copy_manager.list_working_characters(project):
            char_data = self.working_copy_manager.load_working_copy(project, "character", char_id)
            if char_data:
                characters.append(char_data)
        
        arc = self.working_copy_manager.load_working_copy(project, "arc")
        
        # Run consistency check
        consistency_report = self.consistency_checker.check_consistency(
            narrative_intent, characters, arc
        )
        
        if consistency_report.has_issues:
            from .consistency import ConsistencyChecker
            checker = ConsistencyChecker()
            click.echo("\n" + "=" * 60)
            click.echo("CONSISTENCY CHECK (after narrative_intent update)")
            click.echo("=" * 60)
            click.echo(checker.format_report(consistency_report))
            click.echo("\nI can help you update characters and scenes to align with the new narrative intent.")
            click.echo("=" * 60)
    
    def end_session(self, project: str) -> None:
        """Prompt for commit, apply or discard changes."""
        changes = self.working_copy_manager.list_changes(project)
        
        # Always show the review workflow if there are any workspace files
        # Even if they match canonical, user should be able to review
        workspace_path = self.working_copy_manager.get_workspace_path(project)
        has_workspace_files = False
        if workspace_path.exists():
            # Check if any schema files exist in workspace
            if (workspace_path / "narrative_intent.json").exists() or \
               (workspace_path / "arc.json").exists() or \
               (workspace_path / "characters").exists() and list((workspace_path / "characters").glob("*.json")):
                has_workspace_files = True
        
        if not changes and not has_workspace_files:
            click.echo("\n✓ No changes to commit.")
            self.working_copy_manager.discard_changes(project)
            return
        
        # If we have workspace files but no detected changes, still show review
        # (might be identical to canonical, but user should see them)
        if not changes and has_workspace_files:
            click.echo("\n" + "="*60)
            click.echo("Session Summary")
            click.echo("="*60)
            click.echo("\nWorkspace files exist but appear identical to canonical.")
            click.echo("You can still review and commit if needed.")
            click.echo("\nWhat would you like to do?")
            click.echo("  1. Review workspace files (see diffs and approve/reject)")
            click.echo("  2. Discard workspace")
            click.echo("  3. Keep workspace for later")
            
            choice = click.prompt("\nChoice", type=click.IntRange(1, 3), default=1)
            
            if choice == 1:
                # Force review even if no changes detected
                self._review_workspace_files(project)
            elif choice == 2:
                self.working_copy_manager.discard_changes(project)
                click.echo("\n✓ Discarded workspace")
            else:
                workspace_path = self.working_copy_manager.get_workspace_path(project)
                click.echo("\n✓ Workspace preserved.")
                click.echo(f"  Workspace location: {workspace_path}")
            return
        
        click.echo("\n" + "="*60)
        click.echo("Session Summary")
        click.echo("="*60)
        click.echo(f"\nChanges in workspace ({len(changes)}):")
        
        for change in changes:
            status_icon = {
                "created": "➕",
                "modified": "✏️",
                "deleted": "➖",
            }.get(change.status, "❓")
            schema_label = change.schema_type
            if change.schema_id:
                schema_label = f"{schema_label} ({change.schema_id})"
            click.echo(f"  {status_icon} {change.status}: {schema_label}")
        
        # Run final diagnostics
        workspace_path = self.working_copy_manager.get_workspace_path(project)
        diagnostics = self.diagnostics_runner.run_diagnostics(project, workspace_path)
        
        click.echo("\nCompilation Status:")
        if diagnostics.can_compile and not diagnostics.errors:
            click.echo("  ✓ Schemas are compilable!")
        else:
            click.echo(f"  ✗ {len(diagnostics.errors)} compilation error(s) remain")
            if diagnostics.errors:
                for error in diagnostics.errors[:3]:  # Show first 3
                    click.echo(f"    - {error.message}")
        
        # ALWAYS force review workflow - don't allow skipping
        click.echo("\nReview and commit your changes:")
        self._review_and_commit(project)
    
    def _show_help(self) -> None:
        """Show help for CLI commands."""
        click.echo("\n" + "-"*60)
        click.echo("Available commands (type /command):")
        click.echo("  /status  - Show current changes and compilation status")
        click.echo("  /diff    - Show diffs for all changed files")
        click.echo("  /help    - Show this help message")
        click.echo("  exit/quit/done - End session and commit/discard changes")
        click.echo("-"*60)
    
    def _handle_command(self, command: str, project: str, workspace_path: Path) -> None:
        """Handle CLI commands during conversation."""
        command = command.lstrip("/").split()[0]  # Get first word after /
        
        if command == "help":
            self._show_help()
        elif command == "status":
            self._show_status(project, workspace_path)
        elif command == "diff":
            self._show_diffs(project)
        else:
            click.echo(f"\n✗ Unknown command: /{command}")
            click.echo("  Type /help for available commands")
    
    def _show_status(self, project: str, workspace_path: Path) -> None:
        """Show current status of changes and compilation."""
        changes = self.working_copy_manager.list_changes(project)
        
        click.echo("\n" + "="*60)
        click.echo("Current Status")
        click.echo("="*60)
        
        if not changes:
            click.echo("\n✓ No changes in workspace")
        else:
            click.echo(f"\nChanges ({len(changes)}):")
            for change in changes:
                status_icon = {
                    "created": "➕",
                    "modified": "✏️",
                    "deleted": "➖",
                }.get(change.status, "❓")
                schema_label = change.schema_type
                if change.schema_id:
                    schema_label = f"{schema_label} ({change.schema_id})"
                click.echo(f"  {status_icon} {change.status}: {schema_label}")
        
        # Show compilation status
        diagnostics = self.diagnostics_runner.run_diagnostics(project, workspace_path)
        click.echo("\nCompilation Status:")
        if diagnostics.can_compile and not diagnostics.errors:
            click.echo("  ✓ Schemas are compilable!")
        else:
            click.echo(f"  ✗ {len(diagnostics.errors)} compilation error(s)")
            if diagnostics.errors:
                for error in diagnostics.errors[:5]:
                    click.echo(f"    - {error.message}")
        
        if diagnostics.warnings:
            click.echo(f"\n  ⚠ {len(diagnostics.warnings)} warning(s)")
    
    def _show_diffs(self, project: str) -> None:
        """Show diffs for all changed files."""
        changes = self.working_copy_manager.list_changes(project)
        
        if not changes:
            click.echo("\n✓ No changes to show")
            return
        
        click.echo("\n" + "="*60)
        click.echo("File Diffs")
        click.echo("="*60)
        
        for change in changes:
            schema_label = change.schema_type
            if change.schema_id:
                schema_label = f"{schema_label} ({change.schema_id})"
            
            click.echo(f"\n{change.status.upper()}: {schema_label}")
            click.echo("-" * 60)
            
            diff = get_file_diff(change.workspace_path, change.canonical_path)
            if diff:
                click.echo(diff)
            else:
                click.echo("  (no diff available)")
        
        click.echo("\n" + "="*60)
    
    def _review_and_commit(self, project: str) -> None:
        """Review changes file by file and approve/reject."""
        changes = self.working_copy_manager.list_changes(project)
        
        if not changes:
            click.echo("\n✓ No changes to commit")
            return
        
        click.echo("\n" + "="*60)
        click.echo("Review Changes")
        click.echo("="*60)
        click.echo(f"\n{len(changes)} file(s) to review\n")
        
        approved_changes = []
        
        for i, change in enumerate(changes, 1):
            schema_label = change.schema_type
            if change.schema_id:
                schema_label = f"{schema_label} ({change.schema_id})"
            
            click.echo(f"\n[{i}/{len(changes)}] {change.status.upper()}: {schema_label}")
            click.echo("-" * 60)
            
            # Show diff
            diff = get_file_diff(change.workspace_path, change.canonical_path)
            if diff:
                click.echo(diff)
            else:
                click.echo("  (new file or no diff available)")
            
            click.echo("\nOptions:")
            click.echo("  1. Approve and include")
            click.echo("  2. Skip (don't commit this file)")
            click.echo("  3. Show full file content")
            
            file_choice = click.prompt("\nChoice", type=click.IntRange(1, 3), default=1)
            
            if file_choice == 1:
                approved_changes.append(change)
                click.echo("  ✓ Approved")
            elif file_choice == 2:
                click.echo("  ⊘ Skipped")
            elif file_choice == 3:
                # Show full file
                try:
                    with open(change.workspace_path) as f:
                        file_content = f.read()
                    click.echo("\nFull file content:")
                    click.echo("="*60)
                    click.echo(file_content)
                    click.echo("="*60)
                    # Ask again
                    approve_choice = click.prompt("\nApprove? (y/n)", type=bool, default=True)
                    if approve_choice:
                        approved_changes.append(change)
                        click.echo("  ✓ Approved")
                    else:
                        click.echo("  ⊘ Skipped")
                except Exception as e:
                    click.echo(f"  ✗ Error reading file: {e}")
                    click.echo("  ⊘ Skipped")
        
        if not approved_changes:
            click.echo("\n✗ No changes approved. Nothing committed.")
            return
        
        # Commit approved changes
        click.echo(f"\n\nCommitting {len(approved_changes)} approved file(s)...")
        
        project_path = self.working_copy_manager.project_manager.get_project_path(project)
        committed_count = 0
        
        for change in approved_changes:
            schema_label = change.schema_type
            if change.schema_id:
                schema_label = f"{schema_label} ({change.schema_id})"
            
            try:
                if change.status == "deleted":
                    # Skip deletions for now (would need to delete from canonical)
                    continue
                
                if change.schema_type == "narrative_intent":
                    canonical_path = project_path / "narrative_intent.json"
                    shutil.copy2(change.workspace_path, canonical_path)
                    committed_count += 1
                elif change.schema_type == "arc":
                    canonical_path = project_path / "arc.json"
                    shutil.copy2(change.workspace_path, canonical_path)
                    committed_count += 1
                elif change.schema_type == "character" and change.schema_id:
                    canonical_path = project_path / "characters" / f"{change.schema_id}.json"
                    canonical_path.parent.mkdir(exist_ok=True)
                    shutil.copy2(change.workspace_path, canonical_path)
                    committed_count += 1
            except Exception as e:
                click.echo(f"  ✗ Error committing {schema_label}: {e}")
        
        click.echo(f"\n✓ Committed {committed_count} file(s) to canonical schemas")
        
        # Clean up workspace only if user approved at least one change
        if approved_changes:
            self.working_copy_manager.discard_changes(project)
        else:
            # User skipped all changes - ask if they want to keep workspace
            keep = click.confirm("\nKeep workspace for later?", default=True)
            if not keep:
                self.working_copy_manager.discard_changes(project)
    
    def _review_workspace_files(self, project: str) -> None:
        """Review all workspace files even if no changes detected."""
        from .diff_helpers import get_file_diff
        
        workspace_path = self.working_copy_manager.get_workspace_path(project)
        project_path = self.working_copy_manager.project_manager.get_project_path(project)
        
        files_to_review = []
        
        # Collect all workspace files
        if (workspace_path / "narrative_intent.json").exists():
            files_to_review.append({
                "type": "narrative_intent",
                "id": None,
                "workspace": workspace_path / "narrative_intent.json",
                "canonical": project_path / "narrative_intent.json" if (project_path / "narrative_intent.json").exists() else None,
            })
        
        if (workspace_path / "arc.json").exists():
            files_to_review.append({
                "type": "arc",
                "id": None,
                "workspace": workspace_path / "arc.json",
                "canonical": project_path / "arc.json" if (project_path / "arc.json").exists() else None,
            })
        
        if (workspace_path / "characters").exists():
            for char_file in (workspace_path / "characters").glob("*.json"):
                char_id = char_file.stem
                files_to_review.append({
                    "type": "character",
                    "id": char_id,
                    "workspace": char_file,
                    "canonical": project_path / "characters" / char_file.name if (project_path / "characters" / char_file.name).exists() else None,
                })
        
        if not files_to_review:
            click.echo("\n✓ No workspace files to review")
            return
        
        click.echo("\n" + "="*60)
        click.echo("Review Workspace Files")
        click.echo("="*60)
        click.echo(f"\n{len(files_to_review)} file(s) in workspace\n")
        
        approved_files = []
        
        for i, file_info in enumerate(files_to_review, 1):
            schema_label = file_info["type"]
            if file_info["id"]:
                schema_label = f"{schema_label} ({file_info['id']})"
            
            status = "created" if not file_info["canonical"] else "modified"
            click.echo(f"\n[{i}/{len(files_to_review)}] {status.upper()}: {schema_label}")
            click.echo("-" * 60)
            
            # Show diff
            diff = get_file_diff(file_info["workspace"], file_info["canonical"])
            if diff:
                click.echo(diff)
            else:
                click.echo("  (identical to canonical or new file)")
            
            click.echo("\nOptions:")
            click.echo("  1. Approve and commit")
            click.echo("  2. Skip (don't commit this file)")
            click.echo("  3. Show full file content")
            
            file_choice = click.prompt("\nChoice", type=click.IntRange(1, 3), default=1)
            
            if file_choice == 1:
                approved_files.append(file_info)
                click.echo("  ✓ Approved")
            elif file_choice == 2:
                click.echo("  ⊘ Skipped")
            elif file_choice == 3:
                # Show full file
                try:
                    with open(file_info["workspace"]) as f:
                        file_content = f.read()
                    click.echo("\nFull file content:")
                    click.echo("="*60)
                    click.echo(file_content)
                    click.echo("="*60)
                    # Ask again
                    approve_choice = click.prompt("\nApprove? (y/n)", type=bool, default=True)
                    if approve_choice:
                        approved_files.append(file_info)
                        click.echo("  ✓ Approved")
                    else:
                        click.echo("  ⊘ Skipped")
                except Exception as e:
                    click.echo(f"  ✗ Error reading file: {e}")
                    click.echo("  ⊘ Skipped")
        
        if not approved_files:
            click.echo("\n✗ No files approved. Nothing committed.")
            return
        
        # Commit approved files
        click.echo(f"\n\nCommitting {len(approved_files)} approved file(s)...")
        
        project_path = self.working_copy_manager.project_manager.get_project_path(project)
        committed_count = 0
        
        for file_info in approved_files:
            schema_label = file_info["type"]
            if file_info["id"]:
                schema_label = f"{schema_label} ({file_info['id']})"
            
            try:
                if file_info["type"] == "narrative_intent":
                    canonical_path = project_path / "narrative_intent.json"
                    shutil.copy2(file_info["workspace"], canonical_path)
                    committed_count += 1
                elif file_info["type"] == "arc":
                    canonical_path = project_path / "arc.json"
                    shutil.copy2(file_info["workspace"], canonical_path)
                    committed_count += 1
                elif file_info["type"] == "character" and file_info["id"]:
                    canonical_path = project_path / "characters" / f"{file_info['id']}.json"
                    canonical_path.parent.mkdir(exist_ok=True)
                    shutil.copy2(file_info["workspace"], canonical_path)
                    committed_count += 1
            except Exception as e:
                click.echo(f"  ✗ Error committing {schema_label}: {e}")
        
        click.echo(f"\n✓ Committed {committed_count} file(s) to canonical schemas")
        
        # Clean up workspace
        self.working_copy_manager.discard_changes(project)
