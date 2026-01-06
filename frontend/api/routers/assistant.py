"""Assistant router - elicitation assistant endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import sys

# Add parent directory to path to import sparnot modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sparnot.storage import ProjectManager
from sparnot.elicitation.assistant import ElicitationAssistant
from sparnot.elicitation.working_copy import WorkingCopyManager
from sparnot.elicitation.diagnostics import DiagnosticsRunner
from sparnot.elicitation.consistency import ConsistencyChecker

router = APIRouter()

# Use same data directory as CLI
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
manager = ProjectManager(DATA_DIR)


class AssistantMessage(BaseModel):
    """Message to assistant."""
    message: str


class WorkspaceStatus(BaseModel):
    """Working copy status."""
    has_workspace: bool
    changes: List[Dict[str, Any]]
    diagnostics: Optional[Dict[str, Any]] = None


# Store assistant instances per project (in-memory for now)
_assistant_instances: Dict[str, ElicitationAssistant] = {}


def get_assistant(project: str) -> ElicitationAssistant:
    """Get or create assistant instance for project."""
    if project not in _assistant_instances:
        _assistant_instances[project] = ElicitationAssistant(data_dir=DATA_DIR)
    return _assistant_instances[project]


@router.post("/{project}/assistant/init")
async def init_assistant(project: str):
    """Initialize assistant session."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    assistant = get_assistant(project)
    
    # Initialize session (creates workspace, runs diagnostics)
    workspace_path = assistant.initialize_session(project)
    
    # Get diagnostics
    diagnostics = assistant.diagnostics_runner.run_diagnostics(project, workspace_path)
    
    # Get opening message
    opening_message = assistant.conversation_manager.start_conversation(
        project, diagnostics, assistant.working_copy_manager, assistant.consistency_checker
    )
    
    return {
        "status": "initialized",
        "opening_message": opening_message,
        "diagnostics": {
            "can_compile": diagnostics.can_compile,
            "errors": [{"category": e.category, "message": e.message} for e in diagnostics.errors],
            "warnings": diagnostics.warnings
        }
    }


@router.post("/{project}/assistant/message")
async def send_message(project: str, request: AssistantMessage):
    """Send message to assistant (streaming response)."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    try:
        assistant = get_assistant(project)
        
        # Get current diagnostics
        workspace_path = assistant.working_copy_manager.get_workspace_path(project)
        diagnostics = assistant.diagnostics_runner.run_diagnostics(project, workspace_path)
        
        # Process message
        response_text, json_updates = assistant.conversation_manager.process_user_message(
            request.message,
            project,
            diagnostics,
            assistant.working_copy_manager
        )
        
        # Apply JSON updates if any
        if json_updates and "updates" in json_updates:
            assistant.apply_json_updates(project, json_updates["updates"])
        
        return {
            "response": response_text,
            "json_updates": json_updates,
            "diagnostics": {
                "can_compile": diagnostics.can_compile,
                "errors": [{"category": e.category, "message": e.message} for e in diagnostics.errors],
                "warnings": diagnostics.warnings
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.get("/{project}/assistant/workspace")
async def get_workspace_status(project: str):
    """Get working copy status."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    assistant = get_assistant(project)
    workspace_path = assistant.working_copy_manager.get_workspace_path(project)
    
    # Check if workspace exists
    has_workspace = workspace_path.exists()
    
    # Get changes
    changes = assistant.working_copy_manager.list_changes(project)
    
    # Get diagnostics
    diagnostics = None
    if has_workspace:
        diagnostics_result = assistant.diagnostics_runner.run_diagnostics(project, workspace_path)
        diagnostics = {
            "can_compile": diagnostics_result.can_compile,
            "errors": [{"category": e.category, "message": e.message} for e in diagnostics_result.errors],
            "warnings": diagnostics_result.warnings
        }
    
    # Get file diffs
    from sparnot.elicitation.diff_helpers import get_file_diff
    diffs = {}
    for change in changes:
        diff_text = get_file_diff(change.workspace_path, change.canonical_path)
        if diff_text:
            diffs[change.file] = diff_text
    
    # Build response dict directly to include diffs
    response_data = {
        "has_workspace": has_workspace,
        "changes": [{
            "file": change.file,
            "status": change.status,
            "schema_type": change.schema_type,
            "schema_id": change.schema_id
        } for change in changes],
        "diagnostics": diagnostics,
        "diffs": diffs
    }
    
    return response_data


@router.post("/{project}/assistant/commit")
async def commit_workspace(project: str):
    """Commit working copy changes to canonical schemas."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    assistant = get_assistant(project)
    
    # Commit changes
    assistant.working_copy_manager.commit_changes(project)
    
    return {"status": "committed"}


@router.post("/{project}/assistant/discard")
async def discard_workspace(project: str):
    """Discard working copy changes."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    assistant = get_assistant(project)
    
    # Discard changes
    assistant.working_copy_manager.discard_changes(project)
    
    return {"status": "discarded"}

