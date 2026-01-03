"""ArcSkeleton schema model (optional, canonical if user-authored)."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field, field_validator, model_validator


class SceneType(str, Enum):
    """Scene types."""

    INCITING_INCIDENT = "inciting_incident"
    FIRST_PLOT_POINT = "first_plot_point"
    MIDPOINT = "midpoint"
    SECOND_PLOT_POINT = "second_plot_point"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    TRANSITION = "transition"
    CHARACTER_DEVELOPMENT = "character_development"
    WORLD_BUILDING = "world_building"
    TENSION_RELEASE = "tension_release"


class Act(BaseModel):
    """Act structure."""

    act_id: str = Field(..., description="Unique act identifier")
    act_purpose: str = Field(..., description="Purpose of this act")
    required_scenes: List[str] = Field(
        ...,
        description="Required scene IDs for this act",
    )


class Scene(BaseModel):
    """Scene structure."""

    scene_id: str = Field(..., description="Unique scene identifier")
    scene_type: SceneType = Field(..., description="Type of scene")
    summary: str = Field(..., description="Summary of the scene")
    involved_characters: List[str] = Field(
        ...,
        description="Character IDs involved in this scene",
    )


class ArcSkeleton(BaseModel):
    """Arc skeleton schema model (optional, canonical if user-authored)."""

    acts: List[Act] = Field(..., description="Act structure")
    scenes: List[Scene] = Field(..., description="Scene structure")

    @field_validator("acts")
    @classmethod
    def validate_acts(cls, v: List[Act]) -> List[Act]:
        """Validate acts have unique IDs."""
        act_ids = [act.act_id for act in v]
        if len(act_ids) != len(set(act_ids)):
            raise ValueError("act_ids must be unique")
        return v

    @field_validator("scenes")
    @classmethod
    def validate_scenes(cls, v: List[Scene]) -> List[Scene]:
        """Validate scenes have unique IDs."""
        scene_ids = [scene.scene_id for scene in v]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene_ids must be unique")
        return v

    @model_validator(mode="after")
    def validate_act_scene_references(self) -> "ArcSkeleton":
        """Validate that act required_scenes reference existing scenes."""
        scene_ids = {scene.scene_id for scene in self.scenes}
        for act in self.acts:
            for scene_id in act.required_scenes:
                if scene_id not in scene_ids:
                    raise ValueError(
                        f"Act {act.act_id} references non-existent scene {scene_id}"
                    )
        return self

