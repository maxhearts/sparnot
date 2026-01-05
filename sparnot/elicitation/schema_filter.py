"""Filter invalid fields from schema data before saving."""

from typing import Dict, Any, Set

# Valid fields for each schema type
VALID_CHARACTER_FIELDS: Set[str] = {
    "id",
    "name",
    "role",
    "beliefs",
    "personality_tags",
}


def filter_character_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out invalid fields from character data, keeping only valid schema fields.
    
    Args:
        data: Character data dict (may contain invalid fields)
        
    Returns:
        Filtered dict with only valid fields
    """
    filtered = {}
    for key in VALID_CHARACTER_FIELDS:
        if key in data:
            filtered[key] = data[key]
    
    # Warn about removed fields
    removed_fields = set(data.keys()) - VALID_CHARACTER_FIELDS
    if removed_fields:
        import click
        click.echo(f"  ⚠ Removed invalid fields: {', '.join(sorted(removed_fields))}")
    
    return filtered

