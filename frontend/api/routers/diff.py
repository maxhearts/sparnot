"""Diff router - compilation diff and propagation endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Optional
from pathlib import Path
import json
import sys

# Add parent directory to path to import sparnot modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sparnot.storage import ProjectManager
from sparnot.poc_compiler.models import CompiledBundle
from sparnot.poc_compiler.diff import compute_compilation_diff
from sparnot.poc_compiler.propagation import analyze_propagation

router = APIRouter()

# Use same data directory as CLI
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
manager = ProjectManager(DATA_DIR)


def load_bundle_from_path(bundle_path: Path) -> CompiledBundle:
    """Load a CompiledBundle from a file path."""
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail=f"Bundle not found: {bundle_path}")
    
    try:
        with open(bundle_path) as f:
            bundle_data = json.load(f)
            return CompiledBundle(**bundle_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading bundle: {str(e)}")


@router.get("/{project}/diff")
async def get_diff_current_vs_latest(project: str):
    """Compare current bundle with latest historical bundle."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    project_path = manager.get_project_path(project)
    
    # Load current bundle
    current_bundle_path = project_path / "compiled_bundle.json"
    if not current_bundle_path.exists():
        raise HTTPException(status_code=404, detail="No current compiled bundle found")
    
    current_bundle = load_bundle_from_path(current_bundle_path)
    
    # Find latest historical bundle
    history_dir = project_path / "history"
    if not history_dir.exists():
        # No history, return empty diff
        from sparnot.poc_compiler.diff_models import CompilationDiff, SchemaDiff, IRDiff
        return CompilationDiff(
            schema_diffs=SchemaDiff(),
            ir_diffs=IRDiff(),
            propagation=[],
            metadata={"identical": False, "no_history": True}
        ).model_dump(mode="json")
    
    history_files = sorted(history_dir.glob("compiled_bundle_*.json"), reverse=True)
    if not history_files:
        # No history files
        from sparnot.poc_compiler.diff_models import CompilationDiff, SchemaDiff, IRDiff
        return CompilationDiff(
            schema_diffs=SchemaDiff(),
            ir_diffs=IRDiff(),
            propagation=[],
            metadata={"identical": False, "no_history": True}
        ).model_dump(mode="json")
    
    latest_bundle = load_bundle_from_path(history_files[0])
    
    # Compute diff
    diff = compute_compilation_diff(latest_bundle, current_bundle)
    
    return diff.model_dump(mode="json")


@router.get("/{project}/diff/{old_timestamp}/{new_timestamp}")
async def get_diff_between_bundles(project: str, old_timestamp: str, new_timestamp: str):
    """Compare two specific historical bundles."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    project_path = manager.get_project_path(project)
    
    # Load old bundle
    if old_timestamp == "current":
        old_bundle_path = project_path / "compiled_bundle.json"
    else:
        history_dir = project_path / "history"
        old_bundle_path = history_dir / f"compiled_bundle_{old_timestamp}.json"
    
    old_bundle = load_bundle_from_path(old_bundle_path)
    
    # Load new bundle
    if new_timestamp == "current":
        new_bundle_path = project_path / "compiled_bundle.json"
    else:
        history_dir = project_path / "history"
        new_bundle_path = history_dir / f"compiled_bundle_{new_timestamp}.json"
    
    new_bundle = load_bundle_from_path(new_bundle_path)
    
    # Compute diff
    diff = compute_compilation_diff(old_bundle, new_bundle)
    
    return diff.model_dump(mode="json")

