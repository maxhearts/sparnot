"""Detect conflicts when locks become incompatible with new IR/schemas."""

from typing import Dict, List, Any, Optional

from .lock_models import SceneLocks
from ..poc_compiler.models import CompiledBundle


def detect_lock_conflicts(
    scene_id: str, locks: SceneLocks, bundle: CompiledBundle
) -> List[Dict[str, Any]]:
    """
    Detect character conflicts in locks.
    
    Only checks for missing characters (not missing nodes/branches).
    Conflicts must be detected BEFORE LLM call.
    
    Args:
        scene_id: Scene ID
        locks: SceneLocks to check
        bundle: Compiled bundle to check against
        
    Returns:
        List of conflicts with lock_id, conflict_type, missing_character, details
    """
    conflicts = []
    
    # Get scene participants from arc_ir
    arc_ir = bundle.ir.get("arc_ir")
    scene_participants = []
    if arc_ir and arc_ir.get("scene_participants"):
        scene_participants = arc_ir["scene_participants"].get(scene_id, [])
    
    # Build character name to ID mapping from canonical schemas
    char_name_to_id = {}
    for char in bundle.canonical_schemas.get("characters", []):
        char_name_to_id[char.get("name", "").lower()] = char.get("id")
    
    # Check each lock for character conflicts
    for lock in locks.locks:
        if lock.scope == "line":
            # Check if speaker exists in scene participants
            speaker = lock.must_preserve.get("speaker", "")
            speaker_lower = speaker.lower()
            
            # Check if speaker name maps to a character ID in participants
            char_id = char_name_to_id.get(speaker_lower)
            if char_id and char_id not in scene_participants:
                conflicts.append(
                    {
                        "lock_id": lock.lock_id,
                        "conflict_type": "missing_character",
                        "missing_character": speaker,
                        "character_id": char_id,
                        "details": f"Locked line requires character '{speaker}' (ID: {char_id}) but they are not in scene participants",
                    }
                )
            elif not char_id:
                # Character name doesn't match any canonical character
                # This might be a generated-only character, check if it's in participants by name
                # For now, we'll only flag if it's a known character name that's missing
                # (Unknown characters might be generated-only and not a conflict)
                pass
        
        elif lock.scope == "node":
            # Check if any dialogue speaker in node exists in scene participants
            dialogue = lock.must_preserve.get("dialogue", [])
            missing_speakers = set()
            
            for line in dialogue:
                speaker = line.get("speaker", "")
                speaker_lower = speaker.lower()
                char_id = char_name_to_id.get(speaker_lower)
                
                if char_id and char_id not in scene_participants:
                    missing_speakers.add((speaker, char_id))
            
            if missing_speakers:
                speakers_str = ", ".join(f"{name} (ID: {cid})" for name, cid in missing_speakers)
                conflicts.append(
                    {
                        "lock_id": lock.lock_id,
                        "conflict_type": "missing_character",
                        "missing_character": ", ".join(name for name, _ in missing_speakers),
                        "character_id": list(set(cid for _, cid in missing_speakers)),
                        "details": f"Locked node requires characters: {speakers_str} but they are not in scene participants",
                    }
                )
        
        # Branch locks: Skip conflict detection (not checking nodes in this scope)
    
    return conflicts

