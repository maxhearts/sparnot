"""Scenes router - scene generation and playback endpoints."""

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

router = APIRouter()

# Use same data directory as CLI
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
manager = ProjectManager(DATA_DIR)


class GenerateSceneRequest(BaseModel):
    """Request to generate a scene."""
    scene_id: Optional[str] = None


def find_scene_files(project_path: Path) -> List[Path]:
    """Find all generated scene files in project directory."""
    scene_files = []
    
    # Look in generated_scenes subdirectory first (new location)
    scenes_dir = project_path / "generated_scenes"
    if scenes_dir.exists():
        for scene_file in scenes_dir.glob("generated_scene*.json"):
            scene_files.append(scene_file)
    
    # Also check project root for legacy files
    default_scene = project_path / "generated_scene.json"
    if default_scene.exists():
        scene_files.append(default_scene)
    
    for scene_file in project_path.glob("generated_scene_*.json"):
        if scene_file != default_scene:
            scene_files.append(scene_file)
    
    return sorted(scene_files)


@router.get("/{project}/scenes")
async def list_scenes(project: str):
    """List all generated scenes for a project."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    project_path = manager.get_project_path(project)
    scene_files = find_scene_files(project_path)
    
    scenes = []
    for scene_file in scene_files:
        try:
            with open(scene_file) as f:
                scene_data = json.load(f)
                scenes.append({
                    "scene_id": scene_data.get("scene_id", scene_file.stem),
                    "scene_type": scene_data.get("scene_type", "unknown"),
                    "filename": scene_file.name,
                    "path": str(scene_file.relative_to(project_path))
                })
        except Exception:
            continue
    
    return scenes


@router.get("/{project}/scenes/{scene_id}")
async def get_scene(project: str, scene_id: str):
    """Get a specific generated scene."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    project_path = manager.get_project_path(project)
    scene_files = find_scene_files(project_path)
    
    # Try to find scene by scene_id or filename
    for scene_file in scene_files:
        try:
            with open(scene_file) as f:
                scene_data = json.load(f)
                if scene_data.get("scene_id") == scene_id or scene_file.stem == scene_id:
                    return scene_data
        except Exception:
            continue
    
    raise HTTPException(status_code=404, detail=f"Scene '{scene_id}' not found")


@router.post("/{project}/scenes/generate")
async def generate_scene(project: str, request: GenerateSceneRequest):
    """Generate a scene from compiled bundle."""
    if not manager.project_exists(project):
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
    
    bundle_path = manager.get_project_path(project) / "compiled_bundle.json"
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail="No compiled bundle found. Compile project first.")
    
    try:
        # Import generate_scene function
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from generate_scene import generate_scene
        
        # Initialize lock manager
        lock_manager = LockManager(project, data_dir=DATA_DIR)
        
        # Generate scene
        scene_data = generate_scene(
            bundle_path=bundle_path,
            scene_id=request.scene_id,
            lock_manager=lock_manager
        )
        
        # Determine output filename
        scene_id = request.scene_id or scene_data.get("scene_id", "generated_scene")
        safe_scene_id = scene_id.replace("/", "_").replace("\\", "_")
        output_filename = f"generated_scene_{safe_scene_id}.json"
        
        # Save to generated_scenes directory
        scenes_dir = manager.get_project_path(project) / "generated_scenes"
        scenes_dir.mkdir(exist_ok=True)
        output_path = scenes_dir / output_filename
        
        with open(output_path, 'w') as f:
            json.dump(scene_data, f, indent=2)
        
        return {
            "status": "success",
            "scene": scene_data,
            "filename": output_filename,
            "path": str(output_path.relative_to(manager.get_project_path(project)))
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating scene: {str(e)}")


@router.get("/{project}/scenes/{scene_id}/play")
async def get_scene_for_playback(project: str, scene_id: str):
    """Get scene data formatted for playback."""
    scene_data = await get_scene(project, scene_id)
    return scene_data

