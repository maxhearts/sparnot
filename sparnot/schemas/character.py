"""CharacterSchema model (optional, canonical if user-authored)."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field, field_validator


class CharacterRole(str, Enum):
    """Character roles."""

    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MENTOR = "mentor"
    FOIL = "foil"


class CharacterSchema(BaseModel):
    """Character schema model (optional, canonical if user-authored)."""

    id: str = Field(..., description="Unique character identifier")
    name: str = Field(..., description="Character name")
    role: CharacterRole = Field(..., description="Character role")
    beliefs: List[str] = Field(
        ...,
        description="Belief statements (simple strings for PoC)",
    )
    personality_tags: List[str] = Field(
        ...,
        description="Personality descriptors",
    )

    @field_validator("beliefs")
    @classmethod
    def validate_beliefs(cls, v: List[str]) -> List[str]:
        """Validate beliefs are non-empty strings."""
        if not all(belief.strip() for belief in v):
            raise ValueError("beliefs must be non-empty strings")
        return [belief.strip() for belief in v]

    @field_validator("personality_tags")
    @classmethod
    def validate_personality_tags(cls, v: List[str]) -> List[str]:
        """Validate personality tags are non-empty strings."""
        if not all(tag.strip() for tag in v):
            raise ValueError("personality_tags must be non-empty strings")
        return [tag.strip() for tag in v]

