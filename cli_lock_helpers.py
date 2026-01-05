"""Helper functions for CLI lock commands."""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from sparnot.scene_generation.lock_storage import LockManager
from sparnot.scene_generation.lock_models import (
    LineLock,
    NodeLock,
    BranchLock,
    SceneLocks,
    SceneFingerprint,
)


def find_scene_files(project_path: Path) -> List[Path]:
    """Find all generated scene files in project directory."""
    scene_files = []
    
    # Look in generated_scenes subdirectory first (new location)
    scenes_dir = project_path / "generated_scenes"
    if scenes_dir.exists():
        # Look for all generated scene files in the subdirectory
        for scene_file in scenes_dir.glob("generated_scene*.json"):
            scene_files.append(scene_file)
    
    # Also check project root for legacy files (backward compatibility)
    default_scene = project_path / "generated_scene.json"
    if default_scene.exists():
        scene_files.append(default_scene)
    
    # Look for generated_scene_{scene_id}.json files in project root (legacy)
    for scene_file in project_path.glob("generated_scene_*.json"):
        if scene_file != default_scene:
            scene_files.append(scene_file)
    
    return sorted(scene_files)


def load_scene_data(scene_path: Path) -> Optional[Dict[str, Any]]:
    """Load generated scene data from a specific file path."""
    try:
        with open(scene_path) as f:
            return json.load(f)
    except Exception:
        return None


def create_line_lock(
    scene_data: Dict[str, Any], node_id: str, line_number: int, notes: Optional[str] = None
) -> Optional[LineLock]:
    """Create a line lock from scene data."""
    scene_id = scene_data.get("scene_id", "generated_scene_1")
    dialogue_tree = scene_data.get("dialogue_tree", {})
    
    if node_id not in dialogue_tree:
        return None
    
    node = dialogue_tree[node_id]
    dialogue = node.get("dialogue", [])
    
    if line_number < 1 or line_number > len(dialogue):
        return None
    
    line = dialogue[line_number - 1]  # Convert to 0-based index
    line_id = line.get("line_id") or f"{scene_id}:{node_id}:L{line_number}"
    speaker = line.get("speaker", "NARRATOR")
    text = line.get("text", "")
    
    lock_id = f"lock_{uuid.uuid4().hex[:8]}"
    
    return LineLock(
        lock_id=lock_id,
        scope="line",
        target={"node_id": node_id, "line_id": line_id},
        must_preserve={"speaker": speaker, "text": text},
        notes=notes,
    )


def create_node_lock(
    scene_data: Dict[str, Any], node_id: str, notes: Optional[str] = None
) -> Optional[NodeLock]:
    """Create a node lock from scene data."""
    scene_id = scene_data.get("scene_id", "generated_scene_1")
    dialogue_tree = scene_data.get("dialogue_tree", {})
    
    if node_id not in dialogue_tree:
        return None
    
    node = dialogue_tree[node_id]
    
    lock_id = f"lock_{uuid.uuid4().hex[:8]}"
    
    return NodeLock(
        lock_id=lock_id,
        scope="node",
        target={"node_id": node_id},
        must_preserve={
            "screenplay": node.get("screenplay", ""),
            "dialogue": node.get("dialogue", []),
            "choices": node.get("choices", []),
        },
        notes=notes,
    )


def create_branch_lock(
    scene_data: Dict[str, Any],
    entry_node: str,
    choice_ids: List[str],
    required_nodes: List[str],
    summary: str,
    notes: Optional[str] = None,
) -> Optional[BranchLock]:
    """Create a branch lock from scene data."""
    lock_id = f"lock_{uuid.uuid4().hex[:8]}"
    
    return BranchLock(
        lock_id=lock_id,
        scope="branch",
        target={
            "entry_node": entry_node,
            "choice_ids": choice_ids,
            "required_nodes": required_nodes,
        },
        must_preserve={"summary": summary},
        notes=notes,
    )


def get_scene_fingerprint(scene_data: Dict[str, Any], bundle: Optional[Any] = None) -> SceneFingerprint:
    """Get scene fingerprint from scene data."""
    scene_id = scene_data.get("scene_id", "generated_scene_1")
    scene_type = scene_data.get("scene_type", "unknown")
    
    return SceneFingerprint(
        scene_id=scene_id,
        scene_type=scene_type,
        ir_scene_hash=None,  # Future enhancement
    )


def list_nodes_in_scene(scene_data: Dict[str, Any]) -> List[str]:
    """List all node IDs in a scene."""
    dialogue_tree = scene_data.get("dialogue_tree", {})
    return list(dialogue_tree.keys())


def list_lines_in_node(scene_data: Dict[str, Any], node_id: str) -> List[Dict[str, Any]]:
    """List all dialogue lines in a node."""
    dialogue_tree = scene_data.get("dialogue_tree", {})
    if node_id not in dialogue_tree:
        return []
    
    node = dialogue_tree[node_id]
    dialogue = node.get("dialogue", [])
    
    result = []
    for i, line in enumerate(dialogue, 1):
        line_id = line.get("line_id") or f"{scene_data.get('scene_id', 'scene')}:{node_id}:L{i}"
        result.append(
            {
                "line_number": i,
                "line_id": line_id,
                "speaker": line.get("speaker", "NARRATOR"),
                "text": line.get("text", "")[:60] + "..." if len(line.get("text", "")) > 60 else line.get("text", ""),
            }
        )
    
    return result

