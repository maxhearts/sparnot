"""Projects router - project management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import sys

# Add parent directory to path to import sparnot modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sparnot.storage import ProjectManager
from sparnot.poc_compiler.compiler import compile_project
from sparnot.poc_compiler.models import CompiledBundle

router = APIRouter()

# Use same data directory as CLI
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
manager = ProjectManager(DATA_DIR)


class ProjectInfo(BaseModel):
    """Project information."""
    name: str
    has_narrative_intent: bool
    has_arc: bool
    character_count: int
    has_compiled_bundle: bool


class CompilationStatus(BaseModel):
    """Compilation status for a project."""
    compiles: bool
    status: str  # "compiles", "blocking_errors", "warnings_only"
    errors: List[str]
    warnings: List[str]


@router.get("", response_model=List[str])
async def list_projects():
    """List all projects."""
    return manager.list_projects()


@router.post("")
async def create_project(data: dict):
    """Create a new project."""
    name = data.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")
    
    if manager.project_exists(name):
        raise HTTPException(status_code=400, detail=f"Project '{name}' already exists")
    
    project_path = manager.create_project(name)
    return {"name": name, "path": str(project_path)}


@router.get("/{project}/info", response_model=ProjectInfo)
async def get_project_info(project: str):
    """Get project information."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    narrative_intent = manager.load_narrative_intent(project, strict=False)
    arc = manager.load_arc(project, strict=False)
    characters = manager.list_characters(project)
    bundle_path = manager.get_project_path(project) / "compiled_bundle.json"
    
    return ProjectInfo(
        name=project,
        has_narrative_intent=narrative_intent is not None,
        has_arc=arc is not None,
        character_count=len(characters),
        has_compiled_bundle=bundle_path.exists()
    )


@router.get("/{project}/status", response_model=CompilationStatus)
async def get_compilation_status(project: str):
    """Get compilation status for a project."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    bundle_path = manager.get_project_path(project) / "compiled_bundle.json"
    
    if not bundle_path.exists():
        return CompilationStatus(
            compiles=False,
            status="blocking_errors",
            errors=["No compiled bundle found. Run compilation first."],
            warnings=[]
        )
    
    try:
        with open(bundle_path) as f:
            import json
            bundle_data = json.load(f)
            bundle = CompiledBundle(**bundle_data)
            
            errors = bundle.lint.errors
            warnings = bundle.lint.warnings
            
            if errors:
                status = "blocking_errors"
            elif warnings:
                status = "warnings_only"
            else:
                status = "compiles"
            
            return CompilationStatus(
                compiles=len(errors) == 0,
                status=status,
                errors=errors,
                warnings=warnings
            )
    except Exception as e:
        return CompilationStatus(
            compiles=False,
            status="blocking_errors",
            errors=[f"Error loading bundle: {str(e)}"],
            warnings=[]
        )


@router.get("/{project}/history")
async def get_compilation_history(project: str):
    """List compilation history for a project."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    history_dir = manager.get_project_path(project) / "history"
    if not history_dir.exists():
        return []
    
    history_files = sorted(history_dir.glob("compiled_bundle_*.json"), reverse=True)
    
    history = []
    for hist_file in history_files[:10]:  # Latest 10
        # Extract timestamp from filename: compiled_bundle_20240104_120000.json
        timestamp_str = hist_file.stem.replace("compiled_bundle_", "")
        try:
            # Parse timestamp: 20240104_120000
            date_part = timestamp_str[:8]
            time_part = timestamp_str[9:]
            formatted = f"{date_part}_{time_part}"
            history.append({
                "timestamp": formatted,
                "filename": hist_file.name,
                "path": str(hist_file)
            })
        except Exception:
            continue
    
    return history

