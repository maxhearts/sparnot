"""Working copy management for assistant schemas."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..storage import ProjectManager


@dataclass
class ChangeEntry:
    """Represents a change between workspace and canonical."""
    schema_type: str  # 'narrative_intent', 'character', 'arc'
    schema_id: Optional[str]  # None for narrative_intent/arc, char_id for characters
    status: str  # 'created', 'modified', 'deleted', 'unchanged'
    workspace_path: Path
    canonical_path: Optional[Path]


class WorkingCopyManager:
    """Manages working copies of schemas in .assistant_workspace/"""
    
    def __init__(self, data_dir: Path = Path("data")):
        """Initialize working copy manager."""
        self.data_dir = data_dir
        self.project_manager = ProjectManager(data_dir)
    
    def get_workspace_path(self, project: str) -> Path:
        """Get path to workspace directory for project."""
        project_path = self.project_manager.get_project_path(project)
        return project_path / ".assistant_workspace"
    
    def initialize_workspace(self, project: str) -> Path:
        """
        Initialize workspace by copying existing schemas or creating empty workspace.
        
        Returns:
            Path to workspace directory
        """
        workspace_path = self.get_workspace_path(project)
        project_path = self.project_manager.get_project_path(project)
        
        # Create workspace directory structure
        workspace_path.mkdir(exist_ok=True)
        (workspace_path / "characters").mkdir(exist_ok=True)
        
        # Copy existing schemas if they exist
        if (project_path / "narrative_intent.json").exists():
            shutil.copy2(
                project_path / "narrative_intent.json",
                workspace_path / "narrative_intent.json"
            )
        
        if (project_path / "arc.json").exists():
            shutil.copy2(
                project_path / "arc.json",
                workspace_path / "arc.json"
            )
        
        # Copy characters
        canonical_chars_dir = project_path / "characters"
        workspace_chars_dir = workspace_path / "characters"
        if canonical_chars_dir.exists():
            for char_file in canonical_chars_dir.glob("*.json"):
                shutil.copy2(char_file, workspace_chars_dir / char_file.name)
        
        return workspace_path
    
    def load_working_copy(self, project: str, schema_type: str, schema_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load schema from workspace.
        
        Args:
            project: Project name
            schema_type: 'narrative_intent', 'character', or 'arc'
            schema_id: Character ID if schema_type is 'character'
        
        Returns:
            Schema data as dict, or None if not found
        """
        workspace_path = self.get_workspace_path(project)
        
        if schema_type == "narrative_intent":
            file_path = workspace_path / "narrative_intent.json"
        elif schema_type == "arc":
            file_path = workspace_path / "arc.json"
        elif schema_type == "character":
            if not schema_id:
                return None
            file_path = workspace_path / "characters" / f"{schema_id}.json"
        else:
            return None
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path) as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_working_copy(self, project: str, schema_type: str, data: Dict[str, Any], schema_id: Optional[str] = None) -> Path:
        """
        Save schema to workspace, preserving existing JSON structure.
        
        Args:
            project: Project name
            schema_type: 'narrative_intent', 'character', or 'arc'
            data: Schema data as dict
            schema_id: Character ID if schema_type is 'character'
        
        Returns:
            Path to saved file
        """
        workspace_path = self.get_workspace_path(project)
        workspace_path.mkdir(parents=True, exist_ok=True)
        (workspace_path / "characters").mkdir(exist_ok=True)
        
        if schema_type == "narrative_intent":
            file_path = workspace_path / "narrative_intent.json"
        elif schema_type == "arc":
            file_path = workspace_path / "arc.json"
        elif schema_type == "character":
            if not schema_id:
                schema_id = data.get("id")
            if not schema_id:
                raise ValueError("schema_id required for character schemas")
            file_path = workspace_path / "characters" / f"{schema_id}.json"
        else:
            raise ValueError(f"Unknown schema_type: {schema_type}")
        
        # Preserve existing JSON structure by loading and deep merging
        existing_data = {}
        if file_path.exists():
            try:
                with open(file_path) as f:
                    existing_data = json.load(f)
            except Exception:
                pass  # If we can't load, start fresh
        
        # Special handling for arc schema - merge acts and scenes lists properly
        if schema_type == "arc" and existing_data:
            merged_data = self._merge_arc_data(existing_data, data)
        else:
            # Deep merge: update existing_data with new data
            merged_data = self._deep_merge(existing_data, data)
        
        # Write with consistent formatting (indent=2)
        with open(file_path, "w") as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def _merge_arc_data(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Special merge for arc data that properly handles acts and scenes lists.
        
        - For 'acts': Merge by act_id (update existing, add new)
        - For 'scenes': Merge by scene_id (update existing, add new)
        - For other keys: Use regular deep merge
        """
        result = base.copy()
        
        # Handle scenes list - merge by scene_id
        if "scenes" in updates and isinstance(updates["scenes"], list):
            base_scenes = result.get("scenes", [])
            base_scenes_dict = {s.get("scene_id"): s for s in base_scenes if isinstance(s, dict) and "scene_id" in s}
            
            for update_scene in updates["scenes"]:
                if isinstance(update_scene, dict) and "scene_id" in update_scene:
                    scene_id = update_scene["scene_id"]
                    base_scenes_dict[scene_id] = update_scene  # Update or add
            
            result["scenes"] = list(base_scenes_dict.values())
        
        # Handle acts list - merge by act_id
        if "acts" in updates and isinstance(updates["acts"], list):
            base_acts = result.get("acts", [])
            base_acts_dict = {a.get("act_id"): a for a in base_acts if isinstance(a, dict) and "act_id" in a}
            
            for update_act in updates["acts"]:
                if isinstance(update_act, dict) and "act_id" in update_act:
                    act_id = update_act["act_id"]
                    if act_id in base_acts_dict:
                        # Merge existing act (deep merge for nested fields)
                        base_acts_dict[act_id] = self._deep_merge(base_acts_dict[act_id], update_act)
                    else:
                        # Add new act
                        base_acts_dict[act_id] = update_act
            
            result["acts"] = list(base_acts_dict.values())
        
        # Handle other keys with regular deep merge
        for key, value in updates.items():
            if key not in ("acts", "scenes"):
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(result[key], value)
                elif key not in result:
                    result[key] = value
        
        return result
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge updates into base, preserving base structure.
        
        For lists, replaces entirely (not merging items).
        For dicts, recursively merges.
        """
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Replace (for lists, primitives, or new keys)
                result[key] = value
        
        return result
    
    def list_working_characters(self, project: str) -> List[str]:
        """List character IDs in workspace."""
        workspace_path = self.get_workspace_path(project)
        chars_dir = workspace_path / "characters"
        
        if not chars_dir.exists():
            return []
        
        return [f.stem for f in chars_dir.glob("*.json")]
    
    def list_changes(self, project: str) -> List[ChangeEntry]:
        """
        Get list of changes between workspace and canonical.
        
        Returns:
            List of ChangeEntry objects
        """
        changes = []
        workspace_path = self.get_workspace_path(project)
        project_path = self.project_manager.get_project_path(project)
        
        if not workspace_path.exists():
            return changes
        
        # Check narrative_intent
        workspace_intent = workspace_path / "narrative_intent.json"
        canonical_intent = project_path / "narrative_intent.json"
        if workspace_intent.exists():
            if canonical_intent.exists():
                # Check if different
                try:
                    with open(workspace_intent) as f:
                        ws_data = json.load(f)
                    with open(canonical_intent) as f:
                        can_data = json.load(f)
                    if ws_data != can_data:
                        changes.append(ChangeEntry(
                            schema_type="narrative_intent",
                            schema_id=None,
                            status="modified",
                            workspace_path=workspace_intent,
                            canonical_path=canonical_intent,
                        ))
                except Exception:
                    changes.append(ChangeEntry(
                        schema_type="narrative_intent",
                        schema_id=None,
                        status="modified",
                        workspace_path=workspace_intent,
                        canonical_path=canonical_intent,
                    ))
            else:
                changes.append(ChangeEntry(
                    schema_type="narrative_intent",
                    schema_id=None,
                    status="created",
                    workspace_path=workspace_intent,
                    canonical_path=None,
                ))
        
        # Check arc
        workspace_arc = workspace_path / "arc.json"
        canonical_arc = project_path / "arc.json"
        if workspace_arc.exists():
            if canonical_arc.exists():
                try:
                    with open(workspace_arc) as f:
                        ws_data = json.load(f)
                    with open(canonical_arc) as f:
                        can_data = json.load(f)
                    if ws_data != can_data:
                        changes.append(ChangeEntry(
                            schema_type="arc",
                            schema_id=None,
                            status="modified",
                            workspace_path=workspace_arc,
                            canonical_path=canonical_arc,
                        ))
                except Exception:
                    changes.append(ChangeEntry(
                        schema_type="arc",
                        schema_id=None,
                        status="modified",
                        workspace_path=workspace_arc,
                        canonical_path=canonical_arc,
                    ))
            else:
                changes.append(ChangeEntry(
                    schema_type="arc",
                    schema_id=None,
                    status="created",
                    workspace_path=workspace_arc,
                    canonical_path=None,
                ))
        
        # Check characters
        workspace_chars_dir = workspace_path / "characters"
        canonical_chars_dir = project_path / "characters"
        workspace_char_ids = set(self.list_working_characters(project))
        canonical_char_ids = set(self.project_manager.list_characters(project))
        
        # Modified or created characters
        for char_id in workspace_char_ids:
            workspace_char = workspace_chars_dir / f"{char_id}.json"
            canonical_char = canonical_chars_dir / f"{char_id}.json" if canonical_chars_dir.exists() else None
            
            if canonical_char and canonical_char.exists():
                try:
                    with open(workspace_char) as f:
                        ws_data = json.load(f)
                    with open(canonical_char) as f:
                        can_data = json.load(f)
                    if ws_data != can_data:
                        changes.append(ChangeEntry(
                            schema_type="character",
                            schema_id=char_id,
                            status="modified",
                            workspace_path=workspace_char,
                            canonical_path=canonical_char,
                        ))
                except Exception:
                    changes.append(ChangeEntry(
                        schema_type="character",
                        schema_id=char_id,
                        status="modified",
                        workspace_path=workspace_char,
                        canonical_path=canonical_char,
                    ))
            else:
                changes.append(ChangeEntry(
                    schema_type="character",
                    schema_id=char_id,
                    status="created",
                    workspace_path=workspace_char,
                    canonical_path=None,
                ))
        
        # Deleted characters (in canonical but not in workspace)
        for char_id in canonical_char_ids - workspace_char_ids:
            canonical_char = canonical_chars_dir / f"{char_id}.json"
            changes.append(ChangeEntry(
                schema_type="character",
                schema_id=char_id,
                status="deleted",
                workspace_path=workspace_chars_dir / f"{char_id}.json",  # Doesn't exist, but for consistency
                canonical_path=canonical_char,
            ))
        
        return changes
    
    def commit_changes(self, project: str) -> List[Path]:
        """
        Copy workspace files to canonical location.
        
        Returns:
            List of paths to committed files
        """
        workspace_path = self.get_workspace_path(project)
        project_path = self.project_manager.get_project_path(project)
        
        if not workspace_path.exists():
            return []
        
        committed = []
        
        # Commit narrative_intent
        workspace_intent = workspace_path / "narrative_intent.json"
        if workspace_intent.exists():
            canonical_intent = project_path / "narrative_intent.json"
            shutil.copy2(workspace_intent, canonical_intent)
            committed.append(canonical_intent)
        
        # Commit arc
        workspace_arc = workspace_path / "arc.json"
        if workspace_arc.exists():
            canonical_arc = project_path / "arc.json"
            shutil.copy2(workspace_arc, canonical_arc)
            committed.append(canonical_arc)
        
        # Commit characters
        workspace_chars_dir = workspace_path / "characters"
        canonical_chars_dir = project_path / "characters"
        if workspace_chars_dir.exists():
            canonical_chars_dir.mkdir(exist_ok=True)
            for char_file in workspace_chars_dir.glob("*.json"):
                shutil.copy2(char_file, canonical_chars_dir / char_file.name)
                committed.append(canonical_chars_dir / char_file.name)
        
        return committed
    
    def discard_changes(self, project: str) -> None:
        """Delete workspace directory."""
        workspace_path = self.get_workspace_path(project)
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
