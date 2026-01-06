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
    
    try:
        assistant = get_assistant(project)
        workspace_path = assistant.working_copy_manager.get_workspace_path(project)
        
        # Check if workspace exists
        has_workspace = workspace_path.exists()
        
        # Get changes (handle case where workspace doesn't exist)
        changes = []
        if has_workspace:
            try:
                changes = assistant.working_copy_manager.list_changes(project)
            except Exception as e:
                # If list_changes fails, workspace might be in inconsistent state
                # Return empty changes but still indicate workspace exists
                changes = []
        
        # Get diagnostics
        diagnostics = None
        if has_workspace:
            try:
                diagnostics_result = assistant.diagnostics_runner.run_diagnostics(project, workspace_path)
                diagnostics = {
                    "can_compile": diagnostics_result.can_compile,
                    "errors": [{"category": e.category, "message": e.message} for e in diagnostics_result.errors],
                    "warnings": diagnostics_result.warnings
                }
            except Exception as e:
                # If diagnostics fail, return None
                diagnostics = None
        
        # Get file diffs
        from sparnot.elicitation.diff_helpers import get_file_diff
        diffs = {}
        for change in changes:
            try:
                diff_text = get_file_diff(change.workspace_path, change.canonical_path)
                if diff_text:
                    # Construct file identifier from schema_type and schema_id
                    file_key = change.schema_type
                    if change.schema_id:
                        file_key = f"{change.schema_type}:{change.schema_id}"
                    diffs[file_key] = diff_text
            except Exception:
                # Skip this diff if it fails
                pass
        
        # Build response dict directly to include diffs
        response_data = {
            "has_workspace": has_workspace,
            "changes": [{
                "file": change.workspace_path.name if change.workspace_path else f"{change.schema_type}.json",
                "status": change.status,
                "schema_type": change.schema_type,
                "schema_id": change.schema_id
            } for change in changes],
            "diagnostics": diagnostics,
            "diffs": diffs
        }
        
        return response_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting workspace status: {str(e)}")


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


@router.get("/{project}/assistant/workspace/file")
async def get_workspace_file(
    project: str,
    schema_type: str,
    schema_id: Optional[str] = None
):
    """Get workspace file content for viewing draft JSON."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    assistant = get_assistant(project)
    workspace_path = assistant.working_copy_manager.get_workspace_path(project)
    
    # Determine file path
    if schema_type == "narrative_intent":
        file_path = workspace_path / "narrative_intent.json"
    elif schema_type == "arc":
        file_path = workspace_path / "arc.json"
    elif schema_type == "character" and schema_id:
        file_path = workspace_path / "characters" / f"{schema_id}.json"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid schema_type or missing schema_id for character")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace file not found: {file_path.name}")
    
    try:
        with open(file_path) as f:
            content = json.load(f)
        return {
            "schema_type": schema_type,
            "schema_id": schema_id,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.post("/{project}/assistant/commit-selective")
async def commit_selective(project: str, request: Dict[str, Any]):
    """Commit only selected files from workspace."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    approved_files = request.get("approved_files", [])
    if not approved_files:
        return {"status": "no_changes", "committed": 0}
    
    assistant = get_assistant(project)
    workspace_path = assistant.working_copy_manager.get_workspace_path(project)
    project_path = manager.get_project_path(project)
    
    import shutil
    committed_count = 0
    
    for file_info in approved_files:
        schema_type = file_info.get("schema_type")
        schema_id = file_info.get("schema_id")
        
        try:
            # Determine workspace and canonical paths
            if schema_type == "narrative_intent":
                workspace_file = workspace_path / "narrative_intent.json"
                canonical_file = project_path / "narrative_intent.json"
            elif schema_type == "arc":
                workspace_file = workspace_path / "arc.json"
                canonical_file = project_path / "arc.json"
            elif schema_type == "character" and schema_id:
                workspace_file = workspace_path / "characters" / f"{schema_id}.json"
                canonical_file = project_path / "characters" / f"{schema_id}.json"
                canonical_file.parent.mkdir(exist_ok=True)
            else:
                continue
            
            if workspace_file.exists():
                shutil.copy2(workspace_file, canonical_file)
                committed_count += 1
        except Exception as e:
            # Continue with other files even if one fails
            pass
    
    # If all files were committed, discard workspace
    if committed_count > 0:
        changes = assistant.working_copy_manager.list_changes(project)
        # Check if all changes were committed
        if len(changes) == committed_count:
            assistant.working_copy_manager.discard_changes(project)
    
        return {"status": "committed", "committed": committed_count}


@router.get("/{project}/assistant/workspace/schemas")
async def get_workspace_schemas(project: str):
    """Get all workspace schemas (drafts)."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    try:
        assistant = get_assistant(project)
        workspace_path = assistant.working_copy_manager.get_workspace_path(project)
        
        if not workspace_path.exists():
            return {
                "narrative_intent": None,
                "arc": None,
                "characters": {}
            }
        
        result = {
            "narrative_intent": None,
            "arc": None,
            "characters": {}
        }
        
        # Load narrative_intent
        narrative_intent_path = workspace_path / "narrative_intent.json"
        if narrative_intent_path.exists():
            with open(narrative_intent_path) as f:
                result["narrative_intent"] = json.load(f)
        
        # Load arc
        arc_path = workspace_path / "arc.json"
        if arc_path.exists():
            with open(arc_path) as f:
                result["arc"] = json.load(f)
        
        # Load characters
        characters_dir = workspace_path / "characters"
        if characters_dir.exists():
            for char_file in characters_dir.glob("*.json"):
                char_id = char_file.stem
                with open(char_file) as f:
                    result["characters"][char_id] = json.load(f)
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting workspace schemas: {str(e)}")


@router.put("/{project}/assistant/workspace/schemas/{schema_type}")
async def save_workspace_schema(
    project: str,
    schema_type: str,
    data: Dict[str, Any],
    schema_id: Optional[str] = None
):
    """Save schema to workspace (draft)."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    try:
        assistant = get_assistant(project)
        assistant.working_copy_manager.save_working_copy(project, schema_type, data, schema_id)
        return {"status": "saved"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error saving workspace schema: {str(e)}")

