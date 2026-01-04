"""Human-readable diff formatting."""

from typing import List
from .diff_models import CompilationDiff, SchemaDiff, IRDiff, FieldChange, PropagationEntry, ChangeType


def format_diff_summary(diff: CompilationDiff) -> str:
    """High-level summary of diff."""
    schema_count = (
        len(diff.schema_diffs.narrative_intent)
        + sum(len(changes) for changes in diff.schema_diffs.characters.values())
        + len(diff.schema_diffs.arc)
    )
    
    ir_count = (
        len(diff.ir_diffs.narrative_ir)
        + sum(len(changes) for changes in diff.ir_diffs.character_irs.values())
        + len(diff.ir_diffs.arc_ir)
    )
    
    propagation_count = len(diff.propagation)
    
    lines = [
        "=== Compilation Diff Summary ===",
        f"Schema Changes: {schema_count} fields",
        f"IR Changes: {ir_count} fields",
        f"Propagations: {propagation_count} schema → IR mappings",
        "",
    ]
    
    if diff.metadata.get("identical"):
        lines.append("Bundles are identical (no changes)")
    
    return "\n".join(lines)


def format_schema_diff(schema_diff: SchemaDiff) -> str:
    """Display schema changes grouped by schema type."""
    lines = ["Schema Changes:"]
    
    if schema_diff.narrative_intent:
        lines.append("  narrative_intent:")
        for change in schema_diff.narrative_intent:
            lines.append(f"    - {_format_field_change(change)}")
    
    if schema_diff.characters:
        lines.append("  characters:")
        for char_id, changes in sorted(schema_diff.characters.items()):
            lines.append(f"    [{char_id}]:")
            for change in changes:
                lines.append(f"      - {_format_field_change(change)}")
    
    if schema_diff.arc:
        lines.append("  arc:")
        for change in schema_diff.arc:
            lines.append(f"    - {_format_field_change(change)}")
    
    if not (schema_diff.narrative_intent or schema_diff.characters or schema_diff.arc):
        lines.append("  (no schema changes)")
    
    return "\n".join(lines)


def format_ir_diff(ir_diff: IRDiff) -> str:
    """Display IR changes grouped by IR type."""
    lines = ["IR Changes:"]
    
    if ir_diff.narrative_ir:
        lines.append("  narrative_ir:")
        for change in ir_diff.narrative_ir:
            lines.append(f"    - {_format_field_change(change)}")
    
    if ir_diff.character_irs:
        lines.append("  character_irs:")
        for char_id, changes in sorted(ir_diff.character_irs.items()):
            lines.append(f"    [{char_id}]:")
            for change in changes:
                lines.append(f"      - {_format_field_change(change)}")
    
    if ir_diff.arc_ir:
        lines.append("  arc_ir:")
        for change in ir_diff.arc_ir:
            lines.append(f"    - {_format_field_change(change)}")
    
    if not (ir_diff.narrative_ir or ir_diff.character_irs or ir_diff.arc_ir):
        lines.append("  (no IR changes)")
    
    return "\n".join(lines)


def format_propagation(propagation: List[PropagationEntry]) -> str:
    """Display propagation mappings with clear causality."""
    lines = ["Propagation:"]
    
    if not propagation:
        lines.append("  (no propagation mappings)")
        return "\n".join(lines)
    
    for entry in propagation:
        lines.append(f"  {entry.schema_path} → {', '.join(entry.affected_ir_paths)}")
        if entry.ir_changes:
            lines.append(f"    IR changed:")
            for change in entry.ir_changes:
                lines.append(f"      - {_format_field_change(change)}")
    
    return "\n".join(lines)


def _format_field_change(change: FieldChange) -> str:
    """Format a single field change for display."""
    path_parts = change.path.split(".")
    field_name = path_parts[-1]
    
    if change.change_type == ChangeType.ADDED:
        old_str = "None"
        new_str = _format_value(change.new_value)
        return f"{field_name}: {old_str} → {new_str} (added)"
    elif change.change_type == ChangeType.REMOVED:
        old_str = _format_value(change.old_value)
        new_str = "None"
        return f"{field_name}: {old_str} → {new_str} (removed)"
    else:  # MODIFIED
        old_str = _format_value(change.old_value)
        new_str = _format_value(change.new_value)
        return f"{field_name}: {old_str} → {new_str}"


def _format_value(value: any) -> str:
    """Format a value for display."""
    if value is None:
        return "None"
    elif isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bool):
        return str(value)
    elif isinstance(value, list):
        if len(value) <= 3:
            return str(value)
        else:
            return f"[{len(value)} items]"
    elif isinstance(value, dict):
        if len(value) <= 2:
            return str(value)
        else:
            return f"{{dict with {len(value)} keys}}"
    else:
        return str(value)[:50]  # Truncate long values


def format_full_diff(diff: CompilationDiff) -> str:
    """Format complete diff with all sections."""
    lines = [
        format_diff_summary(diff),
        "",
        format_schema_diff(diff.schema_diffs),
        "",
        format_ir_diff(diff.ir_diffs),
        "",
        format_propagation(diff.propagation),
    ]
    
    return "\n".join(lines)

