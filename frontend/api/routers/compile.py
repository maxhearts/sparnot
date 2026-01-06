"""Compile router - compilation and diagnostics endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import sys
from datetime import datetime

# Add parent directory to path to import sparnot modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sparnot.storage import ProjectManager
from sparnot.poc_compiler.compiler import compile_project
from sparnot.poc_compiler.models import CompiledBundle
from sparnot.elicitation.diagnostics import DiagnosticsRunner

router = APIRouter()

# Use same data directory as CLI
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
manager = ProjectManager(DATA_DIR)
diagnostics_runner = DiagnosticsRunner(DATA_DIR)


class DiagnosticError(BaseModel):
    """Diagnostic error."""
    category: str
    message: str
    schema_type: Optional[str] = None
    schema_id: Optional[str] = None
    field_path: Optional[str] = None


class DiagnosticsReport(BaseModel):
    """Diagnostics report."""
    errors: List[DiagnosticError]
    warnings: List[str]
    can_compile: bool


@router.post("/{project}/compile")
async def compile_project_endpoint(project: str):
    """Compile project to IR."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    try:
        # Save previous compilation to history if it exists
        bundle_path = manager.get_project_path(project) / "compiled_bundle.json"
        if bundle_path.exists():
            manager.save_compilation_history(project)
        
        # Compile
        bundle = compile_project(project, data_dir=DATA_DIR)
        
        # Save bundle
        with open(bundle_path, 'w') as f:
            json.dump(bundle.model_dump(mode="json"), f, indent=2)
        
        return {
            "status": "success",
            "bundle": bundle.model_dump(mode="json"),
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    
    except ValueError as e:
        # Compilation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")


@router.get("/{project}/bundle")
async def get_bundle(project: str):
    """Get current compiled bundle."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    bundle_path = manager.get_project_path(project) / "compiled_bundle.json"
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail="No compiled bundle found")
    
    try:
        with open(bundle_path) as f:
            bundle_data = json.load(f)
            bundle = CompiledBundle(**bundle_data)
            return bundle.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading bundle: {str(e)}")


@router.get("/{project}/bundle/history/{timestamp}")
async def get_historical_bundle(project: str, timestamp: str):
    """Get historical bundle by timestamp."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    history_dir = manager.get_project_path(project) / "history"
    bundle_path = history_dir / f"compiled_bundle_{timestamp}.json"
    
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail=f"Historical bundle not found: {timestamp}")
    
    try:
        with open(bundle_path) as f:
            bundle_data = json.load(f)
            bundle = CompiledBundle(**bundle_data)
            return bundle.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading historical bundle: {str(e)}")


@router.post("/{project}/diagnostics")
async def run_diagnostics(project: str):
    """Run diagnostics (dry compile) on current schemas."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    project_path = manager.get_project_path(project)
    
    # Run diagnostics on canonical schemas (not workspace)
    diagnostics = diagnostics_runner.run_diagnostics(project, project_path)
    
    # Convert to response model
    errors = [
        DiagnosticError(
            category=err.category,
            message=err.message,
            schema_type=err.schema_type,
            schema_id=err.schema_id,
            field_path=err.field_path
        )
        for err in diagnostics.errors
    ]
    
    return DiagnosticsReport(
        errors=errors,
        warnings=diagnostics.warnings,
        can_compile=diagnostics.can_compile
    )


@router.get("/{project}/diagnostics")
async def get_last_diagnostics(project: str):
    """Get last diagnostics result (cached or re-run)."""
    # For now, just re-run diagnostics
    # In future, could cache results
    return await run_diagnostics(project)

