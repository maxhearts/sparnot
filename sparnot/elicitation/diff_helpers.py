"""Helper functions for generating diffs between JSON files."""

import json
from pathlib import Path
from typing import Optional


def format_json_diff(old_data: dict, new_data: dict, depth: int = 0) -> str:
    """
    Format a human-readable diff between two JSON dicts.
    
    Uses simple key-based comparison and shows added/removed/changed fields.
    Shows actual values, not just counts.
    """
    lines = []
    indent = "  " * (depth + 1)
    sub_indent = "  " * (depth + 2)
    
    all_keys = set(old_data.keys()) | set(new_data.keys())
    
    for key in sorted(all_keys):
        old_val = old_data.get(key)
        new_val = new_data.get(key)
        
        if key not in old_data:
            # Added
            lines.append(f"{indent}+ {key}: {_format_value_detailed(new_val, depth)}")
        elif key not in new_data:
            # Removed
            lines.append(f"{indent}- {key}: {_format_value_detailed(old_val, depth)}")
        elif old_val != new_val:
            # Changed
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                lines.append(f"{indent}~ {key}:")
                sub_diff = format_json_diff(old_val, new_val, depth + 1)
                if sub_diff:
                    lines.append(sub_diff)
            elif isinstance(old_val, list) and isinstance(new_val, list):
                lines.append(f"{indent}~ {key}:")
                # Show list differences in detail
                max_show = 5
                for i in range(min(max_show, len(old_val), len(new_val))):
                    if old_val[i] != new_val[i]:
                        old_str = _format_value_detailed(old_val[i], depth + 1)
                        new_str = _format_value_detailed(new_val[i], depth + 1)
                        lines.append(f"{sub_indent}[{i}]: {old_str} → {new_str}")
                
                if len(old_val) != len(new_val):
                    lines.append(f"{sub_indent}Length: {len(old_val)} → {len(new_val)}")
                
                if max(len(old_val), len(new_val)) > max_show:
                    lines.append(f"{sub_indent}... ({len(old_val)} items → {len(new_val)} items total)")
            else:
                # Primitive value change
                old_str = _format_value_detailed(old_val, depth)
                new_str = _format_value_detailed(new_val, depth)
                lines.append(f"{indent}~ {key}: {old_str} → {new_str}")
    
    return "\n".join(lines)


def _format_value_detailed(val, depth: int = 0, max_length: int = 80) -> str:
    """Format a value for display in diff with more detail."""
    if isinstance(val, str):
        if len(val) > max_length:
            return f'"{val[:max_length-3]}..."'
        return f'"{val}"'
    elif isinstance(val, list):
        if len(val) == 0:
            return "[]"
        if depth < 2 and len(val) <= 3:
            # Show small lists inline
            items = [_format_value_detailed(item, depth + 1, max_length=40) for item in val[:3]]
            return f"[{', '.join(items)}]"
        return f"[{len(val)} items]"
    elif isinstance(val, dict):
        if depth < 2 and len(val) <= 3:
            # Show small dicts inline
            items = [f"{k}: {_format_value_detailed(v, depth + 1, max_length=30)}" for k, v in list(val.items())[:3]]
            return f"{{{', '.join(items)}}}"
        return f"{{object with {len(val)} keys}}"
    elif val is None:
        return "null"
    elif isinstance(val, bool):
        return "true" if val else "false"
    else:
        return str(val)


def get_file_diff(workspace_path: Path, canonical_path: Optional[Path]) -> Optional[str]:
    """
    Get diff between workspace and canonical file.
    
    Returns:
        Diff string, or None if files don't exist or are identical
    """
    if not workspace_path.exists():
        return None
    
    if canonical_path and canonical_path.exists():
        try:
            with open(workspace_path) as f:
                workspace_data = json.load(f)
            with open(canonical_path) as f:
                canonical_data = json.load(f)
            
            if workspace_data == canonical_data:
                return None
            
            return format_json_diff(canonical_data, workspace_data)
        except Exception:
            return "[Error reading files for diff]"
    else:
        # File is new
        try:
            with open(workspace_path) as f:
                workspace_data = json.load(f)
            lines = ["  (new file)"]
            for key in sorted(workspace_data.keys()):
                lines.append(f"  + {key}: {_format_value_detailed(workspace_data[key])}")
            return "\n".join(lines)
        except Exception as e:
            # Include error message for debugging
            return f"[Error reading file for diff: {e}]"

