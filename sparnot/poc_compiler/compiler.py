"""Deterministic compiler for Schema → IR."""

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from ..schemas import NarrativeIntent, CharacterSchema, ArcSkeleton
from ..storage import ProjectManager
from .models import (
    NarrativeIR,
    CharacterIR,
    ArcIR,
    Proposed,
    GenerationContext,
    LintReport,
    CompiledBundle,
)
from . import rules_tables


def compile_project(project_name: str, data_dir: Path = Path("data")) -> CompiledBundle:
    """Compile project schemas to IR bundle."""
    manager = ProjectManager(data_dir)
    
    # Load schemas with strict validation (compilation requires valid schemas)
    narrative_intent = manager.load_narrative_intent(project_name, strict=True)
    if not narrative_intent:
        raise ValueError(f"Narrative intent not found or invalid for project '{project_name}'")
    
    characters = []
    for char_id in manager.list_characters(project_name):
        char = manager.load_character(project_name, char_id, strict=True)
        if char:
            characters.append(char)
    
    arc = manager.load_arc(project_name, strict=True)
    
    # Compile
    warnings = []
    errors = []
    proposed = Proposed()
    
    # Normalize player fantasy
    player_fantasy_canon, unknown_fantasy = rules_tables.canonicalize_player_fantasy(
        narrative_intent.player_fantasy.value
    )
    if unknown_fantasy:
        warnings.append(f"Unknown player_fantasy '{unknown_fantasy}', defaulting to 'story'")
        proposed.unknown_player_fantasy = unknown_fantasy
    
    # Normalize player agency
    player_agency_canon = rules_tables.canonicalize_player_agency(
        narrative_intent.player_agency.value
    )
    
    # Extract tone profile
    tone_weights = narrative_intent.tone_weights
    sorted_tones = sorted(tone_weights.items(), key=lambda x: x[1], reverse=True)
    dominant_tone = sorted_tones[0][0] if sorted_tones else "hopeful"
    secondary_tone = sorted_tones[1][0] if len(sorted_tones) > 1 and sorted_tones[1][1] > 0.15 else None
    excluded_tones = [tone for tone, weight in tone_weights.items() if weight == 0.0]
    
    # Generate style tokens
    style_tokens = []
    for tone, weight in tone_weights.items():
        if weight > 0 and tone in rules_tables.TONE_TO_STYLE_TOKENS:
            style_tokens.extend(rules_tables.TONE_TO_STYLE_TOKENS[tone])
    
    # Interaction rules
    if tone_weights.get("tragic", 0) >= 0.35 and tone_weights.get("humor", 0) > 0:
        style_tokens.append("gallows_humor_guardrails")
    if tone_weights.get("mysterious", 0) >= 0.15:
        style_tokens.append("withhold_then_payoff")
    
    style_tokens = list(set(style_tokens))  # Deduplicate
    
    # Extract setting tokens
    setting_tokens = rules_tables.extract_setting_tokens(narrative_intent.setting)
    
    # Parse invariants → constraints
    constraints, unmatched_invariants = rules_tables.parse_invariant_patterns(
        narrative_intent.invariants
    )
    if unmatched_invariants:
        warnings.append(f"Unmatched invariants: {unmatched_invariants}")
        proposed.unknown_invariants = unmatched_invariants
    
    # Normalize themes (equal weights for now, strings only)
    theme_weights = {}
    if narrative_intent.themes:
        weight_per_theme = 1.0 / len(narrative_intent.themes)
        for theme in narrative_intent.themes:
            theme_weights[theme] = weight_per_theme
    
    # Map player agency to choice count ranges
    agency_choice_counts = rules_tables.AGENCY_TO_CHOICE_COUNTS.get(
        player_agency_canon,
        {
            "choices_per_point": {"min": 2, "max": 3},
            "choices_per_interaction": {"min": 1, "max": 3},
        }  # Default to medium
    )
    choices_per_point = agency_choice_counts["choices_per_point"]
    choices_per_interaction = agency_choice_counts["choices_per_interaction"]
    
    # Map player fantasy to choice nature tokens
    choice_nature_tokens = rules_tables.FANTASY_TO_CHOICE_NATURE.get(
        player_fantasy_canon,
        ["narrative_choice", "plot_branch"]  # Default to story
    )
    
    # Build NarrativeIR
    narrative_ir = NarrativeIR(
        dominant_tone=dominant_tone,
        secondary_tone=secondary_tone,
        excluded_tones=excluded_tones,
        style_tokens=style_tokens,
        constraints=constraints,
        theme_weights=theme_weights,
        narrative_obligations=[],  # Placeholder for future
        setting_tokens=setting_tokens,
        player_fantasy=player_fantasy_canon,
        player_agency=player_agency_canon,
        choices_per_point=choices_per_point,
        choices_per_interaction=choices_per_interaction,
        choice_nature_tokens=choice_nature_tokens,
    )
    
    # Compile CharacterIRs
    character_irs = []
    character_ids = {char.id for char in characters}
    
    for char in characters:
        # Normalize personality tags
        voice_tokens = []
        unknown_tags = []
        
        for tag in char.personality_tags:
            normalized = rules_tables.normalize_personality_tag(tag)
            if normalized in rules_tables.PERSONALITY_TAGS_TO_VOICE_TOKENS:
                voice_tokens.extend(rules_tables.PERSONALITY_TAGS_TO_VOICE_TOKENS[normalized])
            else:
                unknown_tags.append(tag)
        
        if unknown_tags:
            warnings.append(f"Unknown personality tags for {char.id}: {unknown_tags}")
            proposed.unknown_personality_tags.extend(unknown_tags)
        
        voice_tokens = list(set(voice_tokens))  # Deduplicate
        
        # Normalize beliefs (equal weights for strings)
        belief_weights = {}
        if char.beliefs:
            weight_per_belief = 1.0 / len(char.beliefs)
            for belief in char.beliefs:
                belief_weights[belief] = weight_per_belief
        
        char_ir = CharacterIR(
            character_id=char.id,
            role=char.role.value,
            voice_tokens=voice_tokens,
            belief_weights=belief_weights,
        )
        character_irs.append(char_ir)
    
    # Compile ArcIR
    arc_ir = None
    if arc:
        scene_order = []
        scene_types = {}
        scene_participants = {}
        unknown_scene_types = []
        act_structure = []
        
        # Canonicalize scene types
        for scene in arc.scenes:
            scene_order.append(scene.scene_id)
            canonical_type, unknown = rules_tables.canonicalize_scene_type(scene.scene_type.value)
            scene_types[scene.scene_id] = canonical_type
            if unknown:
                unknown_scene_types.append(f"{scene.scene_id}:{unknown}")
            
            # Validate character references
            for char_id in scene.involved_characters:
                if char_id not in character_ids:
                    errors.append(f"Scene {scene.scene_id} references unknown character {char_id}")
            
            scene_participants[scene.scene_id] = scene.involved_characters
        
        if unknown_scene_types:
            warnings.append(f"Unknown scene types: {unknown_scene_types}")
            proposed.unknown_scene_types = unknown_scene_types
        
        # Build act structure
        for act in arc.acts:
            act_structure.append({
                "act_id": act.act_id,
                "required_scenes": act.required_scenes,
            })
        
        arc_ir = ArcIR(
            scene_order=scene_order,
            scene_types=scene_types,
            scene_participants=scene_participants,
            act_structure=act_structure,
        )
    
    # Build GenerationContext
    act_purposes = []
    scene_summaries = {}
    
    if arc:
        for act in arc.acts:
            act_purposes.append(act.act_purpose)
        for scene in arc.scenes:
            scene_summaries[scene.scene_id] = scene.summary
    
    generation_context = GenerationContext(
        setting=narrative_intent.setting,
        act_purposes=act_purposes,
        scene_summaries=scene_summaries,
        invariants_text=narrative_intent.invariants,
    )
    
    # Check for hard errors (should stop compilation)
    if errors:
        error_msg = "Compilation failed due to errors:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    
    # Build canonical schemas dict
    canonical_schemas = {
        "narrative_intent": narrative_intent.model_dump(),
        "characters": [char.model_dump() for char in characters],
        "arc": arc.model_dump() if arc else None,
    }
    
    # Build lint report (warnings only at this point, since errors would have stopped compilation)
    lint = LintReport(warnings=warnings, errors=[])
    
    # Build IR dict (hashes computed separately)
    ir_dict = {
        "narrative_ir": narrative_ir.model_dump(),
        "character_irs": [char_ir.model_dump() for char_ir in character_irs],
        "arc_ir": arc_ir.model_dump() if arc_ir else None,
    }
    
    # Create bundle with empty hashes first
    temp_bundle = CompiledBundle(
        canonical_schemas=canonical_schemas,
        ir=ir_dict,
        proposed=proposed,
        generation_context=generation_context,
        lint=lint,
        hashes={},
    )
    
    # Compute hashes and create final bundle
    from .hashing import compute_all_hashes
    hashes = compute_all_hashes(temp_bundle)
    
    bundle = temp_bundle.model_copy(update={"hashes": hashes})
    
    return bundle

