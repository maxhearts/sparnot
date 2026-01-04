"""Match scenes to locks after recompiles."""

from typing import Optional

from ..poc_compiler.models import CompiledBundle
from .lock_storage import LockManager


def match_scene_to_locks(
    scene_id: str, bundle: CompiledBundle, lock_manager: LockManager
) -> Optional[str]:
    """
    Match scenes to locks after recompiles.
    
    Primary: Match by scene_id (if scene_id still exists in arc_ir.scene_order)
    Fallback: Match by (scene_type + act_id + involved_characters)
    Future: Match by ir_scene_hash if implemented
    
    Args:
        scene_id: Scene ID to match
        bundle: Compiled bundle
        lock_manager: LockManager instance
        
    Returns:
        Matched scene_id or None if orphaned
    """
    arc_ir = bundle.ir.get("arc_ir")
    
    # Primary: Match by scene_id
    if arc_ir and arc_ir.get("scene_order"):
        if scene_id in arc_ir["scene_order"]:
            return scene_id
    
    # Fallback: Match by scene_type + involved_characters
    # (For PoC, we'll use primary matching only)
    # Future enhancement: implement fallback matching
    
    return None

