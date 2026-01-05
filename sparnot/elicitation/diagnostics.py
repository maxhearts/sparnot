"""Diagnostic runner for dry compilation."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..storage import ProjectManager
from ..schemas import NarrativeIntent, CharacterSchema, ArcSkeleton
from ..poc_compiler.compiler import compile_project


@dataclass
class DiagnosticError:
    """Represents a compilation error."""
    category: str  # 'validation', 'reference', 'missing', 'structure'
    message: str
    schema_type: Optional[str] = None  # 'narrative_intent', 'character', 'arc'
    schema_id: Optional[str] = None  # Character ID if applicable
    field_path: Optional[str] = None  # JSON path to field (e.g., 'player_fantasy')


@dataclass
class DiagnosticsReport:
    """Diagnostic report with errors and suggestions."""
    errors: List[DiagnosticError]
    warnings: List[str]
    can_compile: bool  # True if no hard errors (only warnings)


class DiagnosticsRunner:
    """Runs deterministic diagnostics via dry compilation."""
    
    def __init__(self, data_dir: Path = Path("data")):
        """Initialize diagnostics runner."""
        self.data_dir = data_dir
    
    def run_diagnostics(self, project: str, workspace_path: Path) -> DiagnosticsReport:
        """
        Try to compile workspace schemas and catch all errors.
        
        Args:
            project: Project name (used for workspace path context)
            workspace_path: Path to .assistant_workspace/ directory
        
        Returns:
            DiagnosticsReport with errors and warnings
        """
        errors = []
        warnings = []
        
        # Create a temporary ProjectManager that loads from workspace
        # We'll patch the ProjectManager to use workspace_path temporarily
        manager = ProjectManager(self.data_dir)
        
        # Try to load and validate schemas manually first
        # Then try compilation
        
        # Check for required schemas
        narrative_intent_path = workspace_path / "narrative_intent.json"
        if not narrative_intent_path.exists():
            errors.append(DiagnosticError(
                category="missing",
                message="narrative_intent.json is required but not found",
                schema_type="narrative_intent",
            ))
            return DiagnosticsReport(errors=errors, warnings=warnings, can_compile=False)
        
        # Try loading and validating narrative_intent
        try:
            with open(narrative_intent_path) as f:
                intent_data = json.load(f)
            NarrativeIntent(**intent_data)
        except json.JSONDecodeError as e:
            errors.append(DiagnosticError(
                category="structure",
                message=f"Invalid JSON in narrative_intent.json: {e}",
                schema_type="narrative_intent",
            ))
            return DiagnosticsReport(errors=errors, warnings=warnings, can_compile=False)
        except Exception as e:
            # Pydantic validation error
            error_msg = str(e)
            errors.append(DiagnosticError(
                category="validation",
                message=f"Validation error in narrative_intent.json: {error_msg}",
                schema_type="narrative_intent",
            ))
            # Try to extract field path from error
            if "field" in error_msg.lower() or "Field" in str(type(e)):
                # Could parse Pydantic error more carefully, but basic parsing for now
                pass
        
        # Try loading characters
        chars_dir = workspace_path / "characters"
        if chars_dir.exists():
            for char_file in chars_dir.glob("*.json"):
                try:
                    with open(char_file) as f:
                        char_data = json.load(f)
                    CharacterSchema(**char_data)
                except json.JSONDecodeError as e:
                    errors.append(DiagnosticError(
                        category="structure",
                        message=f"Invalid JSON in {char_file.name}: {e}",
                        schema_type="character",
                        schema_id=char_file.stem,
                    ))
                except Exception as e:
                    errors.append(DiagnosticError(
                        category="validation",
                        message=f"Validation error in {char_file.name}: {str(e)}",
                        schema_type="character",
                        schema_id=char_file.stem,
                    ))
        
        # Try loading arc if it exists
        arc_path = workspace_path / "arc.json"
        if arc_path.exists():
            try:
                with open(arc_path) as f:
                    arc_data = json.load(f)
                ArcSkeleton(**arc_data)
            except json.JSONDecodeError as e:
                errors.append(DiagnosticError(
                    category="structure",
                    message=f"Invalid JSON in arc.json: {e}",
                    schema_type="arc",
                ))
            except Exception as e:
                errors.append(DiagnosticError(
                    category="validation",
                    message=f"Validation error in arc.json: {str(e)}",
                    schema_type="arc",
                ))
        
        # Now try actual compilation by temporarily switching project paths
        # We need to compile from workspace. Since compile_project uses ProjectManager
        # which loads from canonical paths, we need a different approach.
        # For now, let's create a temporary project manager that loads from workspace
        
        # Actually, a simpler approach: temporarily copy workspace to canonical, compile, then restore
        # But that's complex. Instead, let's create a workspace-aware compile function
        
        # For PoC, let's do a simpler approach: try to compile by temporarily using workspace as canonical
        # We'll use a mock project approach - create temporary project, copy workspace there, compile
        
        # Actually, let's just try compilation with a modified ProjectManager
        # We can create a WorkspaceProjectManager that loads from workspace_path
        
        # For now, let's use a simpler approach: try compilation by temporarily copying
        # But actually, the best approach is to modify compile_project to accept a custom path
        # For PoC, let's implement a simpler version that tries to validate and catch common errors
        
        # Try to compile by creating a temporary project manager wrapper
        # Actually, let's just call compile_project with a temp project name approach
        # For now, let's catch compilation errors directly
        
        # Better approach: Create a workspace-aware compile function
        # For now, let's validate schemas and try a dry compile by actually calling compile_project
        # but catching the exception
        
        # Since compile_project uses ProjectManager which loads from canonical paths,
        # we need to actually copy workspace to canonical temporarily, or modify the approach
        
        # Use a temporary project directory for compilation instead of modifying canonical
        # This prevents any accidental writes to canonical schemas
        import tempfile
        temp_project_dir = Path(tempfile.mkdtemp())
        temp_project_name = f"__temp_diagnostic_{project}"
        
        try:
            # Copy workspace to temp project directory
            if workspace_path.exists():
                if (workspace_path / "narrative_intent.json").exists():
                    temp_project_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(workspace_path / "narrative_intent.json", temp_project_dir / "narrative_intent.json")
                if (workspace_path / "arc.json").exists():
                    shutil.copy2(workspace_path / "arc.json", temp_project_dir / "arc.json")
                if (workspace_path / "characters").exists():
                    (temp_project_dir / "characters").mkdir(exist_ok=True)
                    for char_file in (workspace_path / "characters").glob("*.json"):
                        shutil.copy2(char_file, temp_project_dir / "characters" / char_file.name)
            
            # Create a temporary data directory structure
            temp_data_dir = Path(tempfile.mkdtemp())
            temp_projects_dir = temp_data_dir / "projects" / temp_project_name
            temp_projects_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy workspace files to temp project
            if (temp_project_dir / "narrative_intent.json").exists():
                shutil.copy2(temp_project_dir / "narrative_intent.json", temp_projects_dir / "narrative_intent.json")
            if (temp_project_dir / "arc.json").exists():
                shutil.copy2(temp_project_dir / "arc.json", temp_projects_dir / "arc.json")
            if (temp_project_dir / "characters").exists():
                (temp_projects_dir / "characters").mkdir(exist_ok=True)
                for char_file in (temp_project_dir / "characters").glob("*.json"):
                    shutil.copy2(char_file, temp_projects_dir / "characters" / char_file.name)
            
            # Try compilation using temp data directory
            try:
                bundle = compile_project(temp_project_name, temp_data_dir)
                # Compilation succeeded! Check for warnings
                if bundle.lint.warnings:
                    warnings.extend(bundle.lint.warnings)
            except ValueError as e:
                # Compilation failed with hard error
                error_msg = str(e)
                # Parse error message to extract details
                if "not found or invalid" in error_msg:
                    errors.append(DiagnosticError(
                        category="missing",
                        message=error_msg,
                    ))
                elif "references unknown character" in error_msg:
                    # Extract character ID from error
                    errors.append(DiagnosticError(
                        category="reference",
                        message=error_msg,
                    ))
                else:
                    errors.append(DiagnosticError(
                        category="validation",
                        message=error_msg,
                    ))
        finally:
            # Clean up temp directories
            if temp_project_dir.exists():
                shutil.rmtree(temp_project_dir)
            if temp_data_dir.exists():
                shutil.rmtree(temp_data_dir)
        
        can_compile = len([e for e in errors if e.category != "missing"]) == 0
        
        return DiagnosticsReport(errors=errors, warnings=warnings, can_compile=can_compile)
    
    def categorize_errors(self, errors: List[DiagnosticError]) -> Dict[str, List[DiagnosticError]]:
        """Group errors by category."""
        categorized = {
            "validation": [],
            "reference": [],
            "missing": [],
            "structure": [],
        }
        for error in errors:
            if error.category in categorized:
                categorized[error.category].append(error)
            else:
                categorized["validation"].append(error)  # Default category
        return categorized
    
    def format_diagnostics_report(self, diagnostics: DiagnosticsReport) -> str:
        """Format diagnostics report as human-readable text."""
        lines = []
        
        if diagnostics.can_compile and not diagnostics.errors:
            lines.append("✓ Schemas are compilable!")
            if diagnostics.warnings:
                lines.append(f"\nWarnings ({len(diagnostics.warnings)}):")
                for warning in diagnostics.warnings:
                    lines.append(f"  ⚠ {warning}")
            return "\n".join(lines)
        
        categorized = self.categorize_errors(diagnostics.errors)
        
        lines.append("✗ Compilation errors found:\n")
        
        # Missing schemas
        if categorized["missing"]:
            lines.append("Missing Schemas:")
            for error in categorized["missing"]:
                lines.append(f"  ✗ {error.message}")
            lines.append("")
        
        # Structure errors
        if categorized["structure"]:
            lines.append("JSON Structure Errors:")
            for error in categorized["structure"]:
                schema_label = error.schema_type
                if error.schema_id:
                    schema_label = f"{schema_label} ({error.schema_id})"
                lines.append(f"  ✗ {schema_label}: {error.message}")
            lines.append("")
        
        # Validation errors
        if categorized["validation"]:
            lines.append("Validation Errors:")
            for error in categorized["validation"]:
                schema_label = error.schema_type or "unknown"
                if error.schema_id:
                    schema_label = f"{schema_label} ({error.schema_id})"
                lines.append(f"  ✗ {schema_label}: {error.message}")
            lines.append("")
        
        # Reference errors
        if categorized["reference"]:
            lines.append("Reference Errors:")
            for error in categorized["reference"]:
                lines.append(f"  ✗ {error.message}")
            lines.append("")
        
        # Warnings
        if diagnostics.warnings:
            lines.append(f"Warnings ({len(diagnostics.warnings)}):")
            for warning in diagnostics.warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")
        
        return "\n".join(lines)

