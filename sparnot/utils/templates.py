"""JSON templates for schema creation."""

from typing import Dict, Any


def narrative_intent_template() -> Dict[str, Any]:
    """Generate template for narrative intent."""
    return {
        "logline": "A compelling one-sentence summary of your narrative",
        "tone_weights": {
            "tragic": 0.2,
            "hopeful": 0.2,
            "humor": 0.2,
            "mysterious": 0.2,
            "whimsical": 0.2,
        },
        "themes": [
            "Theme 1",
            "Theme 2",
            "Theme 3",
        ],
        "player_fantasy": "story",
        "player_agency": "medium",
        "setting": "Describe your setting here",
        "invariants": [],
    }


def character_template(char_id: str = "", name: str = "") -> Dict[str, Any]:
    """Generate template for character."""
    return {
        "id": char_id or "character_id",
        "name": name or "Character Name",
        "role": "protagonist",
        "beliefs": [
            "Belief 1",
            "Belief 2",
        ],
        "personality_tags": [
            "trait1",
            "trait2",
        ],
    }


def arc_template() -> Dict[str, Any]:
    """Generate template for arc."""
    return {
        "acts": [
            {
                "act_id": "act_1",
                "act_purpose": "Purpose of Act 1",
                "required_scenes": ["scene_1"],
            },
        ],
        "scenes": [
            {
                "scene_id": "scene_1",
                "scene_type": "inciting_incident",
                "summary": "Summary of the scene",
                "involved_characters": [],
            },
        ],
    }

