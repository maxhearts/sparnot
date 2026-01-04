"""Pydantic models for compilation diffs."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Type of change in a field."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class FieldChange(BaseModel):
    """Represents a single field change."""

    path: str = Field(..., description="Dot-separated path to the field (e.g., 'narrative_intent.player_fantasy')")
    old_value: Optional[Any] = Field(None, description="Previous value (None for added fields)")
    new_value: Optional[Any] = Field(None, description="New value (None for removed fields)")
    change_type: ChangeType = Field(..., description="Type of change")


class SchemaDiff(BaseModel):
    """Collection of field changes for schemas."""

    narrative_intent: List[FieldChange] = Field(default_factory=list, description="Changes to narrative_intent schema")
    characters: Dict[str, List[FieldChange]] = Field(
        default_factory=dict, description="Changes to character schemas by character_id"
    )
    arc: List[FieldChange] = Field(default_factory=list, description="Changes to arc schema")


class IRDiff(BaseModel):
    """Collection of field changes for IR components."""

    narrative_ir: List[FieldChange] = Field(default_factory=list, description="Changes to narrative IR")
    character_irs: Dict[str, List[FieldChange]] = Field(
        default_factory=dict, description="Changes to character IRs by character_id"
    )
    arc_ir: List[FieldChange] = Field(default_factory=list, description="Changes to arc IR")


class PropagationEntry(BaseModel):
    """Maps a schema change to affected IR changes."""

    schema_path: str = Field(..., description="Path to the changed schema field")
    schema_change: FieldChange = Field(..., description="The schema field change")
    affected_ir_paths: List[str] = Field(..., description="Paths to IR fields affected by this schema change")
    ir_changes: List[FieldChange] = Field(default_factory=list, description="The actual IR field changes")


class CompilationDiff(BaseModel):
    """Complete diff report between two compilations."""

    schema_diffs: SchemaDiff = Field(..., description="Schema changes")
    ir_diffs: IRDiff = Field(..., description="IR changes")
    propagation: List[PropagationEntry] = Field(default_factory=list, description="Propagation mappings")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata (e.g., bundle hashes, timestamp, etc.)"
    )

