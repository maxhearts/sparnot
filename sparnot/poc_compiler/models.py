"""IR models for compiled schemas."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class NarrativeIR(BaseModel):
    """Compiled narrative intent IR."""

    dominant_tone: str = Field(..., description="Dominant tone")
    secondary_tone: Optional[str] = Field(None, description="Secondary tone")
    excluded_tones: List[str] = Field(default_factory=list, description="Excluded tones")
    style_tokens: List[str] = Field(default_factory=list, description="Style tokens")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Hard constraints")
    theme_weights: Dict[str, float] = Field(default_factory=dict, description="Theme weights")
    narrative_obligations: List[str] = Field(default_factory=list, description="Narrative obligations")
    setting_tokens: List[str] = Field(default_factory=list, description="Setting tokens")
    player_fantasy: str = Field(..., description="Canonical player fantasy")
    player_agency: str = Field(..., description="Canonical player agency")
    choices_per_point: Dict[str, int] = Field(..., description="Min/max choices at any given choice point")
    choices_per_interaction: Dict[str, int] = Field(..., description="Min/max total choices per interaction/scene")
    choice_nature_tokens: List[str] = Field(default_factory=list, description="Choice nature tokens based on fantasy")


class CharacterIR(BaseModel):
    """Compiled character IR."""

    character_id: str = Field(..., description="Character ID")
    role: str = Field(..., description="Character role")
    voice_tokens: List[str] = Field(default_factory=list, description="Voice tokens")
    belief_weights: Dict[str, float] = Field(default_factory=dict, description="Normalized belief weights")


class ArcIR(BaseModel):
    """Compiled arc IR."""

    scene_order: List[str] = Field(default_factory=list, description="Ordered scene IDs")
    scene_types: Dict[str, str] = Field(default_factory=dict, description="Scene ID to canonical type")
    scene_participants: Dict[str, List[str]] = Field(default_factory=dict, description="Scene ID to participant IDs")
    act_structure: List[Dict[str, Any]] = Field(default_factory=list, description="Act structure")


class Proposed(BaseModel):
    """Proposed/unknown inputs that need review."""

    unknown_player_fantasy: Optional[str] = Field(None, description="Unmapped player fantasy value")
    unknown_scene_types: List[str] = Field(default_factory=list, description="Unmapped scene types")
    unknown_personality_tags: List[str] = Field(default_factory=list, description="Unmapped personality tags")
    unknown_invariants: List[str] = Field(default_factory=list, description="Unmapped invariants")


class GenerationContext(BaseModel):
    """Prose and raw text for LLM generation."""

    setting: str = Field(..., description="Full setting description")
    act_purposes: List[str] = Field(default_factory=list, description="Act purpose descriptions")
    scene_summaries: Dict[str, str] = Field(default_factory=dict, description="Scene ID to summary")
    invariants_text: List[str] = Field(default_factory=list, description="Raw invariant text")


class LintReport(BaseModel):
    """Lint warnings and errors."""

    warnings: List[str] = Field(default_factory=list, description="Warnings")
    errors: List[str] = Field(default_factory=list, description="Errors")


class CompiledBundle(BaseModel):
    """Complete compiled bundle."""

    canonical_schemas: Dict[str, Any] = Field(..., description="Original schemas")
    ir: Dict[str, Any] = Field(..., description="Compiled IRs")
    proposed: Proposed = Field(..., description="Proposed/unknown inputs")
    generation_context: GenerationContext = Field(..., description="Generation context")
    lint: LintReport = Field(..., description="Lint report")
    hashes: Dict[str, Any] = Field(..., description="Hashes for change detection")

