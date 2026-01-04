"""Propagation analysis: map schema changes to IR changes."""

from typing import Dict, List, Optional
from .models import CompiledBundle
from .diff_models import SchemaDiff, IRDiff, FieldChange, PropagationEntry
from . import rules_tables


def analyze_propagation(schema_diff: SchemaDiff, ir_diff: IRDiff) -> List[PropagationEntry]:
    """
    Analyze which IR changes were caused by which schema changes.
    
    Uses rule-based mapping to infer causality.
    """
    propagation: List[PropagationEntry] = []
    
    # Narrative intent → Narrative IR mappings
    for change in schema_diff.narrative_intent:
        affected_ir_paths: List[str] = []
        affected_ir_changes: List[FieldChange] = []
        
        if change.path.startswith("narrative_intent.player_fantasy"):
            # player_fantasy → choice_nature_tokens
            ir_path = "narrative_ir.choice_nature_tokens"
            affected_ir_paths.append(ir_path)
            affected_changes = [c for c in ir_diff.narrative_ir if c.path == ir_path]
            affected_ir_changes.extend(affected_changes)
        
        elif change.path.startswith("narrative_intent.player_agency"):
            # player_agency → choices_per_point, choices_per_interaction
            ir_paths = [
                "narrative_ir.choices_per_point",
                "narrative_ir.choices_per_interaction",
            ]
            affected_ir_paths.extend(ir_paths)
            for ir_path in ir_paths:
                affected_changes = [c for c in ir_diff.narrative_ir if c.path.startswith(ir_path)]
                affected_ir_changes.extend(affected_changes)
        
        elif change.path.startswith("narrative_intent.tone_weights"):
            # tone_weights → dominant_tone, secondary_tone, excluded_tones, style_tokens
            ir_paths = [
                "narrative_ir.dominant_tone",
                "narrative_ir.secondary_tone",
                "narrative_ir.excluded_tones",
                "narrative_ir.style_tokens",
            ]
            affected_ir_paths.extend(ir_paths)
            for ir_path in ir_paths:
                affected_changes = [c for c in ir_diff.narrative_ir if c.path.startswith(ir_path)]
                affected_ir_changes.extend(affected_changes)
        
        elif change.path.startswith("narrative_intent.themes"):
            # themes → theme_weights
            ir_path = "narrative_ir.theme_weights"
            affected_ir_paths.append(ir_path)
            affected_changes = [c for c in ir_diff.narrative_ir if c.path.startswith(ir_path)]
            affected_ir_changes.extend(affected_changes)
        
        elif change.path.startswith("narrative_intent.invariants"):
            # invariants → constraints
            ir_path = "narrative_ir.constraints"
            affected_ir_paths.append(ir_path)
            affected_changes = [c for c in ir_diff.narrative_ir if c.path.startswith(ir_path)]
            affected_ir_changes.extend(affected_changes)
        
        elif change.path.startswith("narrative_intent.setting"):
            # setting → setting_tokens
            ir_path = "narrative_ir.setting_tokens"
            affected_ir_paths.append(ir_path)
            affected_changes = [c for c in ir_diff.narrative_ir if c.path.startswith(ir_path)]
            affected_ir_changes.extend(affected_changes)
        
        if affected_ir_paths:
            propagation.append(
                PropagationEntry(
                    schema_path=change.path,
                    schema_change=change,
                    affected_ir_paths=affected_ir_paths,
                    ir_changes=affected_ir_changes,
                )
            )
    
    # Character schema → Character IR mappings
    for char_id, char_changes in schema_diff.characters.items():
        affected_ir_paths: List[str] = []
        affected_ir_changes: List[FieldChange] = []
        
        for change in char_changes:
            if change.path.endswith(".personality_tags"):
                # personality_tags → voice_tokens
                ir_path = f"character_irs[{char_id}].voice_tokens"
                affected_ir_paths.append(ir_path)
                char_ir_changes = ir_diff.character_irs.get(char_id, [])
                affected_changes = [c for c in char_ir_changes if c.path.endswith(".voice_tokens")]
                affected_ir_changes.extend(affected_changes)
            
            elif change.path.endswith(".beliefs"):
                # beliefs → belief_weights
                ir_path = f"character_irs[{char_id}].belief_weights"
                affected_ir_paths.append(ir_path)
                char_ir_changes = ir_diff.character_irs.get(char_id, [])
                affected_changes = [c for c in char_ir_changes if c.path.endswith(".belief_weights")]
                affected_ir_changes.extend(affected_changes)
            
            elif change.path.endswith(".role"):
                # role → role (direct mapping)
                ir_path = f"character_irs[{char_id}].role"
                affected_ir_paths.append(ir_path)
                char_ir_changes = ir_diff.character_irs.get(char_id, [])
                affected_changes = [c for c in char_ir_changes if c.path.endswith(".role")]
                affected_ir_changes.extend(affected_changes)
        
        if affected_ir_paths:
            # Group all character changes for this character into one propagation entry
            propagation.append(
                PropagationEntry(
                    schema_path=f"characters[{char_id}]",
                    schema_change=char_changes[0],  # Use first change as representative
                    affected_ir_paths=list(set(affected_ir_paths)),  # Deduplicate
                    ir_changes=affected_ir_changes,
                )
            )
    
    # Arc schema → Arc IR mappings
    for change in schema_diff.arc:
        affected_ir_paths: List[str] = []
        affected_ir_changes: List[FieldChange] = []
        
        if change.path.startswith("arc.scenes"):
            # scenes[*].scene_type → arc_ir.scene_types
            # scenes[*].involved_characters → arc_ir.scene_participants
            # scenes order → arc_ir.scene_order
            ir_paths = [
                "arc_ir.scene_types",
                "arc_ir.scene_participants",
                "arc_ir.scene_order",
            ]
            affected_ir_paths.extend(ir_paths)
            for ir_path in ir_paths:
                affected_changes = [c for c in ir_diff.arc_ir if c.path.startswith(ir_path)]
                affected_ir_changes.extend(affected_changes)
        
        elif change.path.startswith("arc.acts"):
            # acts → arc_ir.act_structure
            ir_path = "arc_ir.act_structure"
            affected_ir_paths.append(ir_path)
            affected_changes = [c for c in ir_diff.arc_ir if c.path.startswith(ir_path)]
            affected_ir_changes.extend(affected_changes)
        
        if affected_ir_paths:
            propagation.append(
                PropagationEntry(
                    schema_path=change.path,
                    schema_change=change,
                    affected_ir_paths=list(set(affected_ir_paths)),  # Deduplicate
                    ir_changes=affected_ir_changes,
                )
            )
    
    return propagation

