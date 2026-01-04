"""Lock storage and management."""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from .lock_models import LockFile, SceneLocks, LineLock, NodeLock, BranchLock


class LockManager:
    """Manage locks per project."""

    def __init__(self, project: str, data_dir: Path = Path("data")):
        """Initialize lock manager for a project."""
        self.project = project
        self.data_dir = data_dir
        self.projects_dir = data_dir / "projects"
        self.project_path = self.projects_dir / project

    def get_lock_path(self) -> Path:
        """Get path to locks.json (in project directory)."""
        return self.project_path / "locks.json"

    def load_locks(self) -> LockFile:
        """Load locks.json (returns empty if doesn't exist)."""
        lock_path = self.get_lock_path()
        if not lock_path.exists():
            return LockFile()
        
        try:
            with open(lock_path) as f:
                data = json.load(f)
                return LockFile(**data)
        except Exception:
            # If loading fails, return empty lock file
            return LockFile()

    def save_locks(self, lock_file: LockFile) -> None:
        """Save locks.json."""
        lock_path = self.get_lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(lock_path, "w") as f:
            json.dump(lock_file.model_dump(mode="json"), f, indent=2)

    def get_scene_locks(self, scene_id: str) -> Optional[SceneLocks]:
        """Get locks for a scene."""
        lock_file = self.load_locks()
        return lock_file.scene_locks.get(scene_id)

    def add_lock(
        self, scene_id: str, lock: Union[LineLock, NodeLock, BranchLock]
    ) -> None:
        """Add a lock to a scene."""
        lock_file = self.load_locks()
        
        if scene_id not in lock_file.scene_locks:
            # Create new SceneLocks entry (will need fingerprint from caller)
            # For now, create with minimal fingerprint
            from .lock_models import SceneFingerprint
            lock_file.scene_locks[scene_id] = SceneLocks(
                scene_fingerprint=SceneFingerprint(
                    scene_id=scene_id, scene_type="unknown"
                ),
                locks=[],
            )
        
        lock_file.scene_locks[scene_id].locks.append(lock)
        self.save_locks(lock_file)

    def remove_lock(self, scene_id: str, lock_id: str) -> bool:
        """Remove a lock from a scene. Returns True if removed, False if not found."""
        lock_file = self.load_locks()
        
        if scene_id not in lock_file.scene_locks:
            return False
        
        scene_locks = lock_file.scene_locks[scene_id]
        original_count = len(scene_locks.locks)
        scene_locks.locks = [
            lock for lock in scene_locks.locks if lock.lock_id != lock_id
        ]
        
        if len(scene_locks.locks) < original_count:
            self.save_locks(lock_file)
            return True
        return False

    def list_locks(self, scene_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all locks for a scene (or all scenes if scene_id is None)."""
        lock_file = self.load_locks()
        
        if scene_id:
            if scene_id not in lock_file.scene_locks:
                return []
            scene_locks = lock_file.scene_locks[scene_id]
            return [
                {
                    "lock_id": lock.lock_id,
                    "scope": lock.scope,
                    "target": lock.target,
                    "notes": lock.notes,
                }
                for lock in scene_locks.locks
            ]
        else:
            # List all locks across all scenes
            all_locks = []
            for sid, scene_locks in lock_file.scene_locks.items():
                for lock in scene_locks.locks:
                    all_locks.append(
                        {
                            "scene_id": sid,
                            "lock_id": lock.lock_id,
                            "scope": lock.scope,
                            "target": lock.target,
                            "notes": lock.notes,
                        }
                    )
            return all_locks

