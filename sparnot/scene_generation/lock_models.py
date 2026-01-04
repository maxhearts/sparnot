"""Pydantic models for content locks."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class LineLock(BaseModel):
    """Lock a single dialogue line."""

    lock_id: str = Field(..., description="Unique identifier (e.g., 'lock_001')")
    scope: str = Field("line", description="Lock scope")
    target: Dict[str, str] = Field(..., description="Target node_id and line_id")
    must_preserve: Dict[str, str] = Field(..., description="Speaker and text to preserve")
    notes: Optional[str] = Field(None, description="Optional user note")


class NodeLock(BaseModel):
    """Lock an entire node."""

    lock_id: str = Field(..., description="Unique identifier")
    scope: str = Field("node", description="Lock scope")
    target: Dict[str, str] = Field(..., description="Target node_id")
    must_preserve: Dict[str, Any] = Field(
        ..., description="Screenplay, dialogue, and choices to preserve"
    )
    notes: Optional[str] = Field(None, description="Optional user note")


class BranchLock(BaseModel):
    """Lock a branching path."""

    lock_id: str = Field(..., description="Unique identifier")
    scope: str = Field("branch", description="Lock scope")
    target: Dict[str, Any] = Field(
        ..., description="Entry node, choice IDs, and required nodes"
    )
    must_preserve: Dict[str, str] = Field(..., description="Branch summary to preserve")
    notes: Optional[str] = Field(None, description="Optional user note")


class SceneFingerprint(BaseModel):
    """Scene identity for matching."""

    ir_scene_hash: Optional[str] = Field(None, description="Optional hash of scene IR (future)")
    scene_type: str = Field(..., description="Scene type from arc")
    scene_id: str = Field(..., description="Scene ID from arc")


class SceneLocks(BaseModel):
    """Collection of locks for a scene."""

    scene_fingerprint: SceneFingerprint = Field(..., description="Scene identity")
    locks: List[Union[LineLock, NodeLock, BranchLock]] = Field(
        default_factory=list, description="List of locks"
    )


class LockFile(BaseModel):
    """Root lock file structure."""

    scene_locks: Dict[str, SceneLocks] = Field(
        default_factory=dict, description="Locks keyed by scene_id"
    )

