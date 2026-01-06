"""Schemas router - schema CRUD operations."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import sys

# Add parent directory to path to import sparnot modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sparnot.storage import ProjectManager
from sparnot.schemas import NarrativeIntent, CharacterSchema, ArcSkeleton
from sparnot.utils.templates import (
    narrative_intent_template,
    character_template,
    arc_template
)

router = APIRouter()

# Use same data directory as CLI
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
manager = ProjectManager(DATA_DIR)


class SchemaResponse(BaseModel):
    """Schema response."""
    schema_type: str
    data: Dict[str, Any]


@router.get("/{project}/schemas")
async def get_all_schemas(project: str):
    """Get all schemas for a project."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    schemas = {}
    
    # Load narrative_intent
    intent = manager.load_narrative_intent(project, strict=False)
    if intent:
        schemas["narrative_intent"] = intent.model_dump()
    else:
        # Try loading raw JSON
        intent_path = manager.get_project_path(project) / "narrative_intent.json"
        if intent_path.exists():
            with open(intent_path) as f:
                schemas["narrative_intent"] = json.load(f)
    
    # Load arc
    arc = manager.load_arc(project, strict=False)
    if arc:
        schemas["arc"] = arc.model_dump()
    else:
        arc_path = manager.get_project_path(project) / "arc.json"
        if arc_path.exists():
            with open(arc_path) as f:
                schemas["arc"] = json.load(f)
    
    # Load characters
    characters = {}
    for char_id in manager.list_characters(project):
        char = manager.load_character(project, char_id, strict=False)
        if char:
            characters[char_id] = char.model_dump()
        else:
            # Try loading raw JSON
            char_path = manager.get_project_path(project) / "characters" / f"{char_id}.json"
            if char_path.exists():
                with open(char_path) as f:
                    characters[char_id] = json.load(f)
    
    schemas["characters"] = characters
    
    return schemas


@router.get("/{project}/schemas/{schema_type}")
async def get_schema(project: str, schema_type: str, schema_id: Optional[str] = None):
    """Get a specific schema."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    if schema_type == "narrative_intent":
        schema = manager.load_narrative_intent(project, strict=False)
        if not schema:
            raise HTTPException(status_code=404, detail="Narrative intent not found")
        return {"schema_type": "narrative_intent", "data": schema.model_dump()}
    
    elif schema_type == "arc":
        schema = manager.load_arc(project, strict=False)
        if not schema:
            raise HTTPException(status_code=404, detail="Arc not found")
        return {"schema_type": "arc", "data": schema.model_dump()}
    
    elif schema_type == "character":
        if not schema_id:
            raise HTTPException(status_code=400, detail="schema_id required for character")
        schema = manager.load_character(project, schema_id, strict=False)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Character '{schema_id}' not found")
        return {"schema_type": "character", "schema_id": schema_id, "data": schema.model_dump()}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown schema type: {schema_type}")


@router.put("/{project}/schemas/{schema_type}")
async def save_schema(project: str, schema_type: str, data: Dict[str, Any], schema_id: Optional[str] = None):
    """Save a schema."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    try:
        if schema_type == "narrative_intent":
            intent = NarrativeIntent(**data)
            manager.save_narrative_intent(project, intent)
            return {"status": "saved", "schema_type": "narrative_intent"}
        
        elif schema_type == "arc":
            arc = ArcSkeleton(**data)
            manager.save_arc(project, arc)
            return {"status": "saved", "schema_type": "arc"}
        
        elif schema_type == "character":
            if not schema_id:
                raise HTTPException(status_code=400, detail="schema_id required for character")
            char = CharacterSchema(**data)
            manager.save_character(project, char)
            return {"status": "saved", "schema_type": "character", "schema_id": schema_id}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown schema type: {schema_type}")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")


@router.post("/{project}/schemas/{schema_type}")
async def create_schema(project: str, schema_type: str, data: Optional[Dict[str, Any]] = None, schema_id: Optional[str] = None):
    """Create a new schema from template or provided data."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    if data:
        # Use provided data
        return await save_schema(project, schema_type, data, schema_id)
    
    # Generate template
    if schema_type == "narrative_intent":
        template = narrative_intent_template()
        return {"schema_type": "narrative_intent", "data": template.model_dump()}
    
    elif schema_type == "arc":
        template = arc_template()
        return {"schema_type": "arc", "data": template.model_dump()}
    
    elif schema_type == "character":
        if not schema_id:
            raise HTTPException(status_code=400, detail="schema_id required for character")
        template = character_template(schema_id, schema_id)  # Use schema_id as name too
        return {"schema_type": "character", "schema_id": schema_id, "data": template.model_dump()}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown schema type: {schema_type}")


@router.get("/{project}/schemas/{schema_type}/template")
async def get_schema_template(project: str, schema_type: str, schema_id: Optional[str] = None):
    """Get a schema template."""
    return await create_schema(project, schema_type, None, schema_id)

