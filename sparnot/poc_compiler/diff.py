"""Deterministic diff computation with hash-based optimization."""

import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .models import CompiledBundle
from .diff_models import CompilationDiff, SchemaDiff, IRDiff, FieldChange, ChangeType, PropagationEntry
from .hashing import compute_all_hashes


def hash_schema_dict(schema_dict: Dict[str, Any]) -> str:
    """Hash a schema dictionary deterministically (matches hashing.py approach)."""
    # Use sorted keys for deterministic JSON
    json_str = json.dumps(schema_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def diff_dicts(old: Dict[str, Any], new: Dict[str, Any], base_path: str = "") -> List[FieldChange]:
    """
    Deep diff of two dictionaries.
    
    Treats lists as sets where order doesn't matter (e.g., style_tokens),
    preserves order where it matters (e.g., scene_order).
    Uses sorted keys for stability.
    """
    changes: List[FieldChange] = []
    all_keys = set(old.keys()) | set(new.keys())
    
    for key in sorted(all_keys):
        path = f"{base_path}.{key}" if base_path else key
        old_val = old.get(key)
        new_val = new.get(key)
        
        if key not in old:
            # Added
            changes.append(FieldChange(path=path, old_value=None, new_value=new_val, change_type=ChangeType.ADDED))
        elif key not in new:
            # Removed
            changes.append(FieldChange(path=path, old_value=old_val, new_value=None, change_type=ChangeType.REMOVED))
        else:
            # Both exist, check if different
            if _values_equal(old_val, new_val):
                continue  # No change
            
            # Check if both are dicts - recurse
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                changes.extend(diff_dicts(old_val, new_val, path))
            elif isinstance(old_val, list) and isinstance(new_val, list):
                # List handling: check if order-sensitive
                if _is_order_sensitive_list(path):
                    # Order matters - compare element by element
                    changes.extend(_diff_ordered_list(old_val, new_val, path))
                else:
                    # Order doesn't matter - compare as sets
                    changes.extend(_diff_unordered_list(old_val, new_val, path))
            else:
                # Primitive or different types
                changes.append(
                    FieldChange(path=path, old_value=old_val, new_value=new_val, change_type=ChangeType.MODIFIED)
                )
    
    return changes


def _is_order_sensitive_list(path: str) -> bool:
    """Check if a list path represents order-sensitive data."""
    # These paths represent ordered sequences
    order_sensitive_paths = [
        "scene_order",
        "act_structure",
        "scenes",
        "acts",
        "dialogue",
    ]
    return any(sensitive in path for sensitive in order_sensitive_paths)


def _diff_ordered_list(old: List[Any], new: List[Any], base_path: str) -> List[FieldChange]:
    """Diff two lists where order matters."""
    changes: List[FieldChange] = []
    max_len = max(len(old), len(new))
    
    for i in range(max_len):
        path = f"{base_path}[{i}]"
        if i >= len(old):
            changes.append(FieldChange(path=path, old_value=None, new_value=new[i], change_type=ChangeType.ADDED))
        elif i >= len(new):
            changes.append(FieldChange(path=path, old_value=old[i], new_value=None, change_type=ChangeType.REMOVED))
        else:
            old_val = old[i]
            new_val = new[i]
            if not _values_equal(old_val, new_val):
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    changes.extend(diff_dicts(old_val, new_val, path))
                else:
                    changes.append(
                        FieldChange(path=path, old_value=old_val, new_value=new_val, change_type=ChangeType.MODIFIED)
                    )
    
    return changes


def _diff_unordered_list(old: List[Any], new: List[Any], base_path: str) -> List[FieldChange]:
    """Diff two lists where order doesn't matter (treat as sets)."""
    changes: List[FieldChange] = []
    
    # Normalize to sorted lists for comparison (convert to JSON for complex types)
    old_set = set(_normalize_list_item(item) for item in old)
    new_set = set(_normalize_list_item(item) for item in new)
    
    added = new_set - old_set
    removed = old_set - new_set
    
    for item in added:
        changes.append(FieldChange(path=f"{base_path}[+]", old_value=None, new_value=item, change_type=ChangeType.ADDED))
    for item in removed:
        changes.append(
            FieldChange(path=f"{base_path}[-]", old_value=item, new_value=None, change_type=ChangeType.REMOVED)
        )
    
    return changes


def _normalize_list_item(item: Any) -> str:
    """Normalize a list item for set comparison."""
    if isinstance(item, (str, int, float, bool)):
        return json.dumps(item)
    elif isinstance(item, dict):
        return json.dumps(item, sort_keys=True)
    else:
        return json.dumps(item, sort_keys=True)


def _values_equal(old: Any, new: Any) -> bool:
    """Check if two values are equal (handles nested structures)."""
    if old == new:
        return True
    
    # For dicts, compare as sorted JSON
    if isinstance(old, dict) and isinstance(new, dict):
        return json.dumps(old, sort_keys=True) == json.dumps(new, sort_keys=True)
    
    # For lists, compare as sorted JSON (will be handled separately for order-sensitive)
    if isinstance(old, list) and isinstance(new, list):
        return json.dumps(old, sort_keys=True) == json.dumps(new, sort_keys=True)
    
    return False


def diff_schemas(old_bundle: CompiledBundle, new_bundle: CompiledBundle) -> SchemaDiff:
    """Compare canonical_schemas sections."""
    old_schemas = old_bundle.canonical_schemas
    new_schemas = new_bundle.canonical_schemas
    
    # Hash optimization: compare schema hashes first
    old_narrative_hash = hash_schema_dict(old_schemas.get("narrative_intent", {}))
    new_narrative_hash = hash_schema_dict(new_schemas.get("narrative_intent", {}))
    
    narrative_changes = []
    if old_narrative_hash != new_narrative_hash:
        narrative_changes = diff_dicts(
            old_schemas.get("narrative_intent", {}), new_schemas.get("narrative_intent", {}), "narrative_intent"
        )
    
    # Character schemas
    old_chars = {char["id"]: char for char in old_schemas.get("characters", [])}
    new_chars = {char["id"]: char for char in new_schemas.get("characters", [])}
    
    character_changes: Dict[str, List[FieldChange]] = {}
    all_char_ids = set(old_chars.keys()) | set(new_chars.keys())
    
    for char_id in sorted(all_char_ids):
        if char_id not in old_chars:
            # New character
            char_hash = hash_schema_dict(new_chars[char_id])
            if char_hash:  # Only add if not empty
                character_changes[char_id] = diff_dicts({}, new_chars[char_id], f"characters[{char_id}]")
        elif char_id not in new_chars:
            # Removed character
            old_char_hash = hash_schema_dict(old_chars[char_id])
            if old_char_hash:
                character_changes[char_id] = diff_dicts(old_chars[char_id], {}, f"characters[{char_id}]")
        else:
            # Existing character - compare hashes
            old_char_hash = hash_schema_dict(old_chars[char_id])
            new_char_hash = hash_schema_dict(new_chars[char_id])
            if old_char_hash != new_char_hash:
                character_changes[char_id] = diff_dicts(old_chars[char_id], new_chars[char_id], f"characters[{char_id}]")
    
    # Arc schema
    old_arc = old_schemas.get("arc")
    new_arc = new_schemas.get("arc")
    
    arc_changes = []
    if old_arc or new_arc:
        old_arc_dict = old_arc if old_arc else {}
        new_arc_dict = new_arc if new_arc else {}
        old_arc_hash = hash_schema_dict(old_arc_dict) if old_arc_dict else ""
        new_arc_hash = hash_schema_dict(new_arc_dict) if new_arc_dict else ""
        
        if old_arc_hash != new_arc_hash:
            arc_changes = diff_dicts(old_arc_dict, new_arc_dict, "arc")
    
    return SchemaDiff(
        narrative_intent=narrative_changes, characters=character_changes, arc=arc_changes
    )


def diff_irs(old_bundle: CompiledBundle, new_bundle: CompiledBundle) -> IRDiff:
    """Compare IR sections with hash optimization."""
    old_ir = old_bundle.ir
    new_ir = new_bundle.ir
    
    # Hash optimization: check narrative_ir hash
    narrative_changes = []
    old_narrative_hash = old_bundle.hashes.get("narrative_ir")
    new_narrative_hash = new_bundle.hashes.get("narrative_ir")
    
    if old_narrative_hash != new_narrative_hash:
        narrative_changes = diff_dicts(
            old_ir.get("narrative_ir", {}), new_ir.get("narrative_ir", {}), "narrative_ir"
        )
    
    # Character IRs
    old_char_irs = {char_ir["character_id"]: char_ir for char_ir in old_ir.get("character_irs", [])}
    new_char_irs = {char_ir["character_id"]: char_ir for char_ir in new_ir.get("character_irs", [])}
    
    character_changes: Dict[str, List[FieldChange]] = {}
    all_char_ids = set(old_char_irs.keys()) | set(new_char_irs.keys())
    
    for char_id in sorted(all_char_ids):
        old_char_hash = old_bundle.hashes.get("character_irs", {}).get(char_id)
        new_char_hash = new_bundle.hashes.get("character_irs", {}).get(char_id)
        
        if old_char_hash != new_char_hash:
            old_char_ir = old_char_irs.get(char_id, {})
            new_char_ir = new_char_irs.get(char_id, {})
            changes = diff_dicts(old_char_ir, new_char_ir, f"character_irs[{char_id}]")
            if changes:
                character_changes[char_id] = changes
    
    # Arc IR
    arc_changes = []
    old_arc_hash = old_bundle.hashes.get("arc_ir")
    new_arc_hash = new_bundle.hashes.get("arc_ir")
    
    if old_arc_hash != new_arc_hash:
        old_arc_ir = old_ir.get("arc_ir") or {}
        new_arc_ir = new_ir.get("arc_ir") or {}
        if old_arc_ir or new_arc_ir:
            arc_changes = diff_dicts(old_arc_ir, new_arc_ir, "arc_ir")
    
    return IRDiff(narrative_ir=narrative_changes, character_irs=character_changes, arc_ir=arc_changes)


def compute_compilation_diff(old_bundle: CompiledBundle, new_bundle: CompiledBundle) -> CompilationDiff:
    """
    Main function to diff two CompiledBundle objects.
    
    Uses hash optimization to skip unchanged components.
    """
    # Quick identity check
    old_bundle_hash = old_bundle.hashes.get("bundle")
    new_bundle_hash = new_bundle.hashes.get("bundle")
    
    if old_bundle_hash == new_bundle_hash:
        # Identical bundles - return empty diff
        return CompilationDiff(
            schema_diffs=SchemaDiff(),
            ir_diffs=IRDiff(),
            propagation=[],
            metadata={
                "old_bundle_hash": old_bundle_hash,
                "new_bundle_hash": new_bundle_hash,
                "identical": True,
            },
        )
    
    # Compute diffs
    schema_diffs = diff_schemas(old_bundle, new_bundle)
    ir_diffs = diff_irs(old_bundle, new_bundle)
    
    # Compute propagation
    from .propagation import analyze_propagation
    propagation = analyze_propagation(schema_diffs, ir_diffs)
    
    return CompilationDiff(
        schema_diffs=schema_diffs,
        ir_diffs=ir_diffs,
        propagation=propagation,
        metadata={
            "old_bundle_hash": old_bundle_hash,
            "new_bundle_hash": new_bundle_hash,
            "identical": False,
        },
    )

