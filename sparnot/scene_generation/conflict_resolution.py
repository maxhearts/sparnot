"""Resolve conflicts interactively (force_participant or orphan)."""

import click
from typing import Dict, List, Any

from .lock_models import SceneLocks


def resolve_conflicts(conflicts: List[Dict[str, Any]], project: str) -> Dict[str, str]:
    """
    Interactive conflict resolution (simplified to two options).
    
    Args:
        conflicts: List of conflicts from detect_lock_conflicts()
        project: Project name (for display)
        
    Returns:
        Resolution map: {lock_id: "force_participant" | "orphan"}
    """
    resolution = {}
    
    if not conflicts:
        return resolution
    
    click.echo(f"\n{'='*60}")
    click.echo("CONFLICT DETECTION")
    click.echo(f"{'='*60}")
    click.echo(f"\nFound {len(conflicts)} conflict(s):\n")
    
    for conflict in conflicts:
        lock_id = conflict["lock_id"]
        missing_char = conflict["missing_character"]
        details = conflict["details"]
        
        click.echo(f"Lock: {lock_id}")
        click.echo(f"Conflict: {details}")
        click.echo("\nResolution options:")
        click.echo("  A) Force participant in (include character in generation, doesn't change canonical IR)")
        click.echo("  B) Orphan lock (mark lock as orphaned, skip in generation)")
        
        choice = click.prompt("\nChoose resolution (A/B)", type=click.Choice(["A", "B"], case_sensitive=False), default="A")
        
        if choice.upper() == "A":
            resolution[lock_id] = "force_participant"
            click.echo(f"✓ Lock {lock_id} will force participant '{missing_char}' into generation")
        else:
            resolution[lock_id] = "orphan"
            click.echo(f"✓ Lock {lock_id} will be orphaned")
        click.echo()
    
    return resolution


def apply_resolution(locks: SceneLocks, resolution: Dict[str, str]) -> SceneLocks:
    """
    Apply resolved actions to locks.
    
    Mark orphaned locks (remove from active locks, keep for history).
    Keep forced-participant locks active.
    
    Args:
        locks: SceneLocks to apply resolution to
        resolution: Resolution map from resolve_conflicts()
        
    Returns:
        Updated SceneLocks with orphaned locks removed
    """
    # For PoC, we'll just filter out orphaned locks
    # (In a full implementation, you might want to track orphaned locks separately)
    active_locks = [
        lock for lock in locks.locks if resolution.get(lock.lock_id) != "orphan"
    ]
    
    # Create new SceneLocks with only active locks
    from .lock_models import SceneLocks as SceneLocksModel
    return SceneLocksModel(
        scene_fingerprint=locks.scene_fingerprint,
        locks=active_locks,
    )


def get_forced_participants(resolution: Dict[str, str], conflicts: List[Dict[str, Any]]) -> List[str]:
    """
    Extract character IDs that need to be forced into scene participants for generation.
    
    Args:
        resolution: Resolution map from resolve_conflicts()
        conflicts: List of conflicts from detect_lock_conflicts()
        
    Returns:
        List of character IDs to add to generation context (not IR)
    """
    forced_char_ids = set()
    
    for conflict in conflicts:
        lock_id = conflict["lock_id"]
        if resolution.get(lock_id) == "force_participant":
            # Extract character ID(s) from conflict
            char_id = conflict.get("character_id")
            if isinstance(char_id, list):
                forced_char_ids.update(char_id)
            elif char_id:
                forced_char_ids.add(char_id)
    
    return list(forced_char_ids)

