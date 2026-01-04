"""NarrativeIntent schema model (required, canonical)."""

from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, Field, field_validator, model_validator


class PlayerFantasy(str, Enum):
    """Player fantasy types."""

    POWER = "power"
    EXPLORATION = "exploration"
    STORY = "story"
    SOCIAL = "social"
    CREATION = "creation"
    CHALLENGE = "challenge"
    SURVIVAL = "survival"
    MASTERY = "mastery"
    MYSTERY = "mystery"
    BUILDER = "builder"
    COZY = "cozy"
    STRATEGY = "strategy"


class PlayerAgency(str, Enum):
    """Player agency levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NarrativeIntent(BaseModel):
    """Narrative intent schema (required, canonical)."""

    logline: str = Field(..., description="One-sentence summary of the narrative")
    tone_weights: Dict[str, float] = Field(
        ...,
        description="Normalized tone weights for: tragic, hopeful, humor, mysterious, whimsical",
    )
    themes: List[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3-5 theme names (simple strings for PoC)",
    )
    player_fantasy: PlayerFantasy = Field(..., description="Primary player fantasy")
    player_agency: PlayerAgency = Field(..., description="Player agency level")
    setting: str = Field(..., description="Setting description")
    invariants: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="0-5 invariant strings (optional)",
    )

    @field_validator("tone_weights", mode="before")
    @classmethod
    def normalize_tone_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Normalize tone weights to sum to 1.0."""
        if not v:
            raise ValueError("tone_weights cannot be empty")
        total = sum(v.values())
        if total == 0:
            raise ValueError("tone_weights cannot all be zero")
        return {k: v / total for k, v in v.items()}

    @field_validator("themes")
    @classmethod
    def validate_themes(cls, v: List[str]) -> List[str]:
        """Validate themes are non-empty strings."""
        if not all(theme.strip() for theme in v):
            raise ValueError("themes must be non-empty strings")
        return [theme.strip() for theme in v]

    @field_validator("invariants")
    @classmethod
    def validate_invariants(cls, v: List[str]) -> List[str]:
        """Validate invariants are non-empty strings."""
        if v and not all(inv.strip() for inv in v):
            raise ValueError("invariants must be non-empty strings")
        return [inv.strip() for inv in v] if v else []

    @model_validator(mode="after")
    def validate_tone_weights_sum(self) -> "NarrativeIntent":
        """Ensure tone weights sum to 1.0 after normalization."""
        total = sum(self.tone_weights.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(f"tone_weights must sum to 1.0, got {total}")
        return self

