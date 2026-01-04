"""Project manager for schema storage and retrieval."""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from ..schemas import (
    NarrativeIntent,
    CharacterSchema,
    ArcSkeleton,
)


class ProjectManager:
    """Manages projects and their schemas."""

    def __init__(self, data_dir: Path = Path("data")):
        """Initialize project manager."""
        self.data_dir = data_dir
        self.projects_dir = data_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> List[str]:
        """List all project names."""
        if not self.projects_dir.exists():
            return []
        return [
            d.name
            for d in self.projects_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def create_project(self, name: str) -> Path:
        """Create a new project directory."""
        project_path = self.projects_dir / name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "characters").mkdir(exist_ok=True)
        return project_path

    def get_project_path(self, name: str) -> Path:
        """Get path to project directory."""
        return self.projects_dir / name

    def project_exists(self, name: str) -> bool:
        """Check if project exists."""
        return (self.projects_dir / name).exists()

    def load_narrative_intent(self, project: str, strict: bool = False) -> Optional[NarrativeIntent]:
        """Load narrative intent from project.
        
        Args:
            project: Project name
            strict: If True, raise ValidationError on invalid data. If False, return None on validation errors.
        """
        project_path = self.get_project_path(project)
        file_path = project_path / "narrative_intent.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path) as f:
                data = json.load(f)
                return NarrativeIntent(**data)
        except Exception as e:
            if strict:
                raise
            # For non-strict mode, return None and let caller handle it
            return None

    def save_narrative_intent(self, project: str, intent: NarrativeIntent) -> Path:
        """Save narrative intent to project."""
        project_path = self.get_project_path(project)
        file_path = project_path / "narrative_intent.json"
        
        with open(file_path, "w") as f:
            json.dump(intent.model_dump(), f, indent=2)
        
        return file_path

    def list_characters(self, project: str) -> List[str]:
        """List all character IDs in project."""
        project_path = self.get_project_path(project)
        characters_dir = project_path / "characters"
        
        if not characters_dir.exists():
            return []
        
        return [
            f.stem
            for f in characters_dir.glob("*.json")
        ]

    def load_character(self, project: str, char_id: str, strict: bool = False) -> Optional[CharacterSchema]:
        """Load character from project.
        
        Args:
            project: Project name
            char_id: Character ID
            strict: If True, raise ValidationError on invalid data. If False, return None on validation errors.
        """
        project_path = self.get_project_path(project)
        file_path = project_path / "characters" / f"{char_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path) as f:
                data = json.load(f)
                return CharacterSchema(**data)
        except Exception as e:
            if strict:
                raise
            # For non-strict mode, return None (caller can handle warning if needed)
            return None

    def save_character(self, project: str, character: CharacterSchema) -> Path:
        """Save character to project."""
        project_path = self.get_project_path(project)
        characters_dir = project_path / "characters"
        characters_dir.mkdir(exist_ok=True)
        
        file_path = characters_dir / f"{character.id}.json"
        
        with open(file_path, "w") as f:
            json.dump(character.model_dump(), f, indent=2)
        
        return file_path

    def delete_character(self, project: str, char_id: str) -> bool:
        """Delete character from project."""
        project_path = self.get_project_path(project)
        file_path = project_path / "characters" / f"{char_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def load_arc(self, project: str, strict: bool = False) -> Optional[ArcSkeleton]:
        """Load arc from project.
        
        Args:
            project: Project name
            strict: If True, raise ValidationError on invalid data. If False, return None on validation errors.
        """
        project_path = self.get_project_path(project)
        file_path = project_path / "arc.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path) as f:
                data = json.load(f)
                return ArcSkeleton(**data)
        except Exception as e:
            if strict:
                raise
            # For non-strict mode, return None and let caller handle it
            return None

    def save_arc(self, project: str, arc: ArcSkeleton) -> Path:
        """Save arc to project."""
        project_path = self.get_project_path(project)
        file_path = project_path / "arc.json"
        
        with open(file_path, "w") as f:
            json.dump(arc.model_dump(), f, indent=2)
        
        return file_path

