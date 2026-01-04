"""Build canon pack from locks for LLM injection."""

from typing import Dict, List, Any, Optional

from .lock_storage import LockManager
from .lock_models import SceneLocks
from ..poc_compiler.models import CompiledBundle


def build_canon_pack(
    scene_id: str, lock_manager: LockManager, bundle: Optional[CompiledBundle] = None
) -> Dict[str, Any]:
    """
    Build canon pack from locks for LLM.
    
    Args:
        scene_id: Scene ID to get locks for
        lock_manager: LockManager instance
        bundle: Compiled bundle (optional, for future use)
        
    Returns:
        Structured dict with locked_lines, locked_nodes, locked_branches
    """
    scene_locks = lock_manager.get_scene_locks(scene_id)
    
    if not scene_locks:
        return {
            "locked_lines": [],
            "locked_nodes": {},
            "locked_branches": [],
        }
    
    locked_lines = []
    locked_nodes = {}
    locked_branches = []
    
    for lock in scene_locks.locks:
        if lock.scope == "line":
            locked_lines.append(
                {
                    "line_id": lock.target.get("line_id"),
                    "node_id": lock.target.get("node_id"),
                    "speaker": lock.must_preserve.get("speaker"),
                    "text": lock.must_preserve.get("text"),
                }
            )
        elif lock.scope == "node":
            node_id = lock.target.get("node_id")
            if node_id:
                locked_nodes[node_id] = lock.must_preserve
        elif lock.scope == "branch":
            locked_branches.append(
                {
                    "entry_node": lock.target.get("entry_node"),
                    "choice_ids": lock.target.get("choice_ids", []),
                    "required_nodes": lock.target.get("required_nodes", []),
                    "summary": lock.must_preserve.get("summary"),
                }
            )
    
    return {
        "locked_lines": locked_lines,
        "locked_nodes": locked_nodes,
        "locked_branches": locked_branches,
    }


def format_canon_pack_prompt(canon_pack: Dict[str, Any]) -> str:
    """
    Format canon pack as LLM prompt section.
    
    Args:
        canon_pack: Canon pack dict from build_canon_pack()
        
    Returns:
        Formatted prompt string
    """
    lines = []
    
    locked_lines = canon_pack.get("locked_lines", [])
    locked_nodes = canon_pack.get("locked_nodes", {})
    locked_branches = canon_pack.get("locked_branches", [])
    
    if not (locked_lines or locked_nodes or locked_branches):
        return ""  # No locks, return empty
    
    lines.append("LOCKED CANON CONTENT (for reference and natural incorporation)")
    lines.append("The following content was previously marked as high-quality. It should appear at least once in the regenerated scene, naturally integrated.")
    lines.append("DO NOT repeat it multiple times verbatim. If the same idea needs to be expressed multiple times, vary the wording while keeping the core sentiment/meaning.")
    lines.append("")
    
    if locked_lines:
        lines.append("Previously locked dialogue (must appear at least once, naturally integrated):")
        for line in locked_lines:
            lines.append(f"  - [{line['speaker']}] \"{line['text']}\"")
            lines.append(f"    (Must include this moment/idea from {line['speaker']} at least once, but avoid verbatim repetition)")
        lines.append("")
    
    if locked_nodes:
        lines.append("Previously locked node content (use as inspiration for similar moments):")
        for node_id, node_content in locked_nodes.items():
            if node_content.get("screenplay"):
                lines.append(f"  Screenplay/Stage Direction concept: {node_content['screenplay'][:150]}...")
            dialogue = node_content.get("dialogue", [])
            if dialogue:
                lines.append(f"  Dialogue concepts to incorporate:")
                for d_line in dialogue:
                    speaker = d_line.get("speaker", "NARRATOR")
                    text = d_line.get("text", "")
                    lines.append(f"    - [{speaker}] expressing: \"{text[:80]}...\"")
            choices = node_content.get("choices", [])
            if choices:
                lines.append(f"  Choice concepts to incorporate:")
                for choice in choices:
                    choice_text = choice.get("text", "")
                    lines.append(f"    - Similar choice option: \"{choice_text[:60]}...\"")
            lines.append("")
        lines.append("")
    
    if locked_branches:
        lines.append("Previously locked branch paths (incorporate similar narrative structure):")
        for branch in locked_branches:
            lines.append(f"  Branch concept: {branch['summary']}")
            lines.append(f"    Include a similar narrative path/choice structure if it fits naturally.")
        lines.append("")
    
    return "\n".join(lines)

