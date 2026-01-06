"""Locks router - content locking endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import sys

# Add parent directory to path to import sparnot modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sparnot.storage import ProjectManager
from sparnot.scene_generation.lock_storage import LockManager
from sparnot.scene_generation.lock_models import LineLock, NodeLock, BranchLock, SceneFingerprint

router = APIRouter()

# Use same data directory as CLI
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
manager = ProjectManager(DATA_DIR)


class LockLineRequest(BaseModel):
    """Request to lock a line."""
    node_id: str
    line_number: int
    notes: Optional[str] = None


class LockNodeRequest(BaseModel):
    """Request to lock a node."""
    node_id: str
    notes: Optional[str] = None


class LockBranchRequest(BaseModel):
    """Request to lock a branch."""
    entry_node: str
    choice_ids: List[str]
    required_nodes: Optional[List[str]] = None
    summary: Optional[str] = None
    notes: Optional[str] = None


@router.get("/{project}/locks")
async def list_all_locks(project: str):
    """List all locks for a project."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    lock_manager = LockManager(project, data_dir=DATA_DIR)
    lock_file = lock_manager.load_locks()
    
    all_locks = []
    for scene_id, scene_locks in lock_file.scene_locks.items():
        for lock in scene_locks.locks:
            all_locks.append({
                "scene_id": scene_id,
                "lock_id": lock.lock_id,
                "scope": lock.__class__.__name__.replace("Lock", "").lower(),  # "line", "node", "branch"
                "target": _format_lock_target(lock),
                "notes": getattr(lock, "notes", None)
            })
    
    return all_locks


@router.get("/{project}/locks/{scene_id}")
async def get_scene_locks(project: str, scene_id: str):
    """Get locks for a specific scene."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    try:
        lock_manager = LockManager(project, data_dir=DATA_DIR)
        scene_locks = lock_manager.get_scene_locks(scene_id)
        
        if not scene_locks:
            return {"scene_id": scene_id, "locks": []}
        
        locks = []
        for lock in scene_locks.locks:
            # Use model_dump for Pydantic v2, or dict() for v1
            try:
                lock_data = lock.model_dump(mode="json") if hasattr(lock, "model_dump") else lock.dict()
            except:
                lock_data = lock.dict() if hasattr(lock, "dict") else {}
            
            locks.append({
                "lock_id": lock.lock_id,
                "scope": lock.__class__.__name__.replace("Lock", "").lower(),
                "target": _format_lock_target(lock),
                "notes": getattr(lock, "notes", None),
                "data": lock_data
            })
        
        # Use model_dump for fingerprint too
        try:
            fingerprint_data = scene_locks.scene_fingerprint.model_dump(mode="json") if hasattr(scene_locks.scene_fingerprint, "model_dump") else scene_locks.scene_fingerprint.dict()
        except:
            fingerprint_data = scene_locks.scene_fingerprint.dict() if hasattr(scene_locks.scene_fingerprint, "dict") else {}
        
        return {
            "scene_id": scene_id,
            "locks": locks,
            "fingerprint": fingerprint_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading locks: {str(e)}")


@router.post("/{project}/locks/{scene_id}/line")
async def lock_line(project: str, scene_id: str, request: LockLineRequest):
    """Lock a dialogue line."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    # Load scene to get line data
    project_path = manager.get_project_path(project)
    scenes_dir = project_path / "generated_scenes"
    
    scene_file = None
    for sf in scenes_dir.glob("generated_scene*.json"):
        try:
            with open(sf) as f:
                scene_data = json.load(f)
                if scene_data.get("scene_id") == scene_id:
                    scene_file = scene_data
                    break
        except Exception:
            continue
    
    if not scene_file:
        # Try project root
        default_scene = project_path / "generated_scene.json"
        if default_scene.exists():
            with open(default_scene) as f:
                scene_file = json.load(f)
    
    if not scene_file:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found")
    
    # Create lock using helper
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from cli_lock_helpers import create_line_lock, get_scene_fingerprint
    
    lock = create_line_lock(scene_file, request.node_id, request.line_number, request.notes)
    if not lock:
        raise HTTPException(status_code=400, detail="Failed to create line lock")
    
    # Save lock
    lock_manager = LockManager(project, data_dir=DATA_DIR)
    lock_file = lock_manager.load_locks()
    
    if scene_id not in lock_file.scene_locks:
        fingerprint = get_scene_fingerprint(scene_file)
        from sparnot.scene_generation.lock_models import SceneLocks
        lock_file.scene_locks[scene_id] = SceneLocks(
            scene_fingerprint=fingerprint,
            locks=[]
        )
    
    lock_manager.add_lock(scene_id, lock)
    
    return {"status": "locked", "lock_id": lock.lock_id}


@router.post("/{project}/locks/{scene_id}/node")
async def lock_node(project: str, scene_id: str, request: LockNodeRequest):
    """Lock a dialogue node."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    # Load scene
    project_path = manager.get_project_path(project)
    scenes_dir = project_path / "generated_scenes"
    
    scene_file = None
    for sf in scenes_dir.glob("generated_scene*.json"):
        try:
            with open(sf) as f:
                scene_data = json.load(f)
                if scene_data.get("scene_id") == scene_id:
                    scene_file = scene_data
                    break
        except Exception:
            continue
    
    if not scene_file:
        default_scene = project_path / "generated_scene.json"
        if default_scene.exists():
            with open(default_scene) as f:
                scene_file = json.load(f)
    
    if not scene_file:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found")
    
    # Create lock
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from cli_lock_helpers import create_node_lock, get_scene_fingerprint
    
    lock = create_node_lock(scene_file, request.node_id, request.notes)
    if not lock:
        raise HTTPException(status_code=400, detail="Failed to create node lock")
    
    # Save lock
    lock_manager = LockManager(project, data_dir=DATA_DIR)
    lock_file = lock_manager.load_locks()
    
    if scene_id not in lock_file.scene_locks:
        fingerprint = get_scene_fingerprint(scene_file)
        from sparnot.scene_generation.lock_models import SceneLocks
        lock_file.scene_locks[scene_id] = SceneLocks(
            scene_fingerprint=fingerprint,
            locks=[]
        )
    
    lock_manager.add_lock(scene_id, lock)
    
    return {"status": "locked", "lock_id": lock.lock_id}


@router.post("/{project}/locks/{scene_id}/branch")
async def lock_branch(project: str, scene_id: str, request: LockBranchRequest):
    """Lock a branch."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    # Load scene
    project_path = manager.get_project_path(project)
    scenes_dir = project_path / "generated_scenes"
    
    scene_file = None
    for sf in scenes_dir.glob("generated_scene*.json"):
        try:
            with open(sf) as f:
                scene_data = json.load(f)
                if scene_data.get("scene_id") == scene_id:
                    scene_file = scene_data
                    break
        except Exception:
            continue
    
    if not scene_file:
        default_scene = project_path / "generated_scene.json"
        if default_scene.exists():
            with open(default_scene) as f:
                scene_file = json.load(f)
    
    if not scene_file:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found")
    
    # Create lock
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from cli_lock_helpers import create_branch_lock, get_scene_fingerprint
    
    lock = create_branch_lock(
        scene_file,
        request.entry_node,
        request.choice_ids,
        request.required_nodes or [],
        request.summary or "",
        request.notes
    )
    if not lock:
        raise HTTPException(status_code=400, detail="Failed to create branch lock")
    
    # Save lock
    lock_manager = LockManager(project, data_dir=DATA_DIR)
    lock_file = lock_manager.load_locks()
    
    if scene_id not in lock_file.scene_locks:
        fingerprint = get_scene_fingerprint(scene_file)
        from sparnot.scene_generation.lock_models import SceneLocks
        lock_file.scene_locks[scene_id] = SceneLocks(
            scene_fingerprint=fingerprint,
            locks=[]
        )
    
    lock_manager.add_lock(scene_id, lock)
    
    return {"status": "locked", "lock_id": lock.lock_id}


@router.delete("/{project}/locks/{scene_id}/{lock_id}")
async def remove_lock(project: str, scene_id: str, lock_id: str):
    """Remove a lock."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    lock_manager = LockManager(project, data_dir=DATA_DIR)
    removed = lock_manager.remove_lock(scene_id, lock_id)
    
    if not removed:
        raise HTTPException(status_code=404, detail=f"Lock '{lock_id}' not found")
    
    return {"status": "removed", "lock_id": lock_id}


def _format_lock_target(lock) -> str:
    """Format lock target for display."""
    if isinstance(lock, LineLock):
        return f"{lock.node_id}:L{lock.line_id.split(':')[-1] if ':' in lock.line_id else '?'}"
    elif isinstance(lock, NodeLock):
        return lock.node_id
    elif isinstance(lock, BranchLock):
        return f"{lock.entry_node} → {','.join(lock.choice_ids)}"
    return "unknown"

