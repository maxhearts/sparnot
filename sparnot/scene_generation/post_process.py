"""Post-processing utilities for generated scenes."""

from typing import Dict, Any, List


def add_line_ids(scene_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process generated scene JSON to add line_id field to each dialogue line.
    
    Format: line_id = "{scene_id}:{node_id}:L{n}" where n is 1..k within that node.
    
    Args:
        scene_data: Generated scene JSON data
        
    Returns:
        Updated scene data with line_id fields added
    """
    scene_id = scene_data.get("scene_id", "generated_scene_1")
    dialogue_tree = scene_data.get("dialogue_tree", {})
    
    # Process each node in the dialogue tree
    for node_id, node in dialogue_tree.items():
        dialogue = node.get("dialogue", [])
        
        # Add line_id to each dialogue line
        for i, line in enumerate(dialogue, 1):
            line_id = f"{scene_id}:{node_id}:L{i}"
            line["line_id"] = line_id
            # Ensure speaker field exists (should already be there)
            if "speaker" not in line:
                line["speaker"] = "NARRATOR"  # Fallback
    
    return scene_data

