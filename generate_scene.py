#!/usr/bin/env python3
"""Generate a sample scene from a compiled IR bundle."""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
import os
from openai import OpenAI

from sparnot.poc_compiler.models import CompiledBundle

# Load environment variables
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")
client = OpenAI(api_key=OPENAI_API_KEY)


def build_scene_prompt(
    bundle: CompiledBundle,
    canon_pack: Optional[Dict[str, Any]] = None,
    forced_participants: Optional[List[str]] = None,
) -> str:
    """Build a comprehensive prompt for scene generation."""
    narrative_ir = bundle.ir["narrative_ir"]
    character_irs = bundle.ir.get("character_irs", [])
    arc_ir = bundle.ir.get("arc_ir")
    gen_context = bundle.generation_context
    
    # Determine scene context
    scene_context = ""
    target_characters = []
    scene_id = None
    
    if arc_ir and arc_ir.get("scene_order"):
        # Use first scene from arc
        scene_id = arc_ir["scene_order"][0]
        scene_type = arc_ir["scene_types"].get(scene_id, "dialogue")
        scene_participants = arc_ir["scene_participants"].get(scene_id, [])
        
        # Add forced participants if provided (for generation only, not IR)
        effective_participants = list(scene_participants)
        if forced_participants:
            for char_id in forced_participants:
                if char_id not in effective_participants:
                    effective_participants.append(char_id)
        
        # Get scene summary if available
        scene_summary = gen_context.scene_summaries.get(scene_id, "")
        
        scene_context = f"""
SCENE CONTEXT:
- Scene ID: {scene_id}
- Scene Type: {scene_type}
- Scene Summary: {scene_summary if scene_summary else "No summary provided"}
"""
        
        # Get characters for this scene
        for char_ir in character_irs:
            if char_ir["character_id"] in effective_participants:
                target_characters.append(char_ir)
        
        # If no characters found but participants listed, try to match by ID
        if not target_characters and effective_participants:
            # Character IRs might not exist, but we have participant IDs
            # We'll use canonical schemas instead
            pass
    else:
        # No arc, create a new scene
        scene_context = """
SCENE CONTEXT:
- Creating a new scene appropriate for the narrative
"""
        
        # Use available characters or create new ones
        if character_irs:
            target_characters = character_irs[:2]  # Use first 2 characters
    
    # Build character descriptions
    character_descriptions = []
    
    # If we have scene participants from arc but no character IRs, try canonical schemas
    if arc_ir and arc_ir.get("scene_order"):
        scene_participants = arc_ir["scene_participants"].get(scene_id, [])
        if scene_participants and not target_characters:
            # Look up characters from canonical schemas
            for char in bundle.canonical_schemas.get("characters", []):
                if char["id"] in scene_participants:
                    # Find matching character IR if it exists
                    char_ir = None
                    for cir in character_irs:
                        if cir["character_id"] == char["id"]:
                            char_ir = cir
                            break
                    
                    desc = f"""
CHARACTER: {char['name']} (ID: {char['id']})
- Role: {char.get('role', 'unknown')}
- Beliefs: {', '.join(char.get('beliefs', []))}
- Personality Tags: {', '.join(char.get('personality_tags', []))}
"""
                    if char_ir:
                        desc += f"- Voice Tokens: {', '.join(char_ir.get('voice_tokens', []))}\n"
                    character_descriptions.append(desc)
    
    # Use target characters from IRs
    if target_characters:
        for char_ir in target_characters:
            char_id = char_ir["character_id"]
            # Get full character data from canonical schemas
            char_data = None
            for char in bundle.canonical_schemas.get("characters", []):
                if char["id"] == char_id:
                    char_data = char
                    break
            
            if char_data:
                desc = f"""
CHARACTER: {char_data['name']} (ID: {char_id})
- Role: {char_ir['role']}
- Beliefs: {', '.join(char_data.get('beliefs', []))}
- Personality Tags: {', '.join(char_data.get('personality_tags', []))}
- Voice Tokens: {', '.join(char_ir.get('voice_tokens', []))}
"""
                character_descriptions.append(desc)
    
    # If still no characters, use available ones or create new
    if not character_descriptions:
        if character_irs:
            # Use first available characters
            for char_ir in character_irs[:2]:
                char_id = char_ir["character_id"]
                char_data = None
                for char in bundle.canonical_schemas.get("characters", []):
                    if char["id"] == char_id:
                        char_data = char
                        break
                
                if char_data:
                    desc = f"""
CHARACTER: {char_data['name']} (ID: {char_id})
- Role: {char_ir['role']}
- Beliefs: {', '.join(char_data.get('beliefs', []))}
- Personality Tags: {', '.join(char_data.get('personality_tags', []))}
- Voice Tokens: {', '.join(char_ir.get('voice_tokens', []))}
"""
                    character_descriptions.append(desc)
        
        if not character_descriptions:
            # Need to create at least 2 characters
            character_descriptions.append("""
CHARACTER CREATION REQUIRED:
- Create at least 2 characters that fit plausibly in this world
- Each character should have a name, role, beliefs, and personality
- Characters should be distinct and have clear voices
- Characters should reflect the setting, themes, and tone
""")
    
    # Build choice information
    choices_per_point = narrative_ir["choices_per_point"]
    choices_per_interaction = narrative_ir["choices_per_interaction"]
    choice_nature = narrative_ir["choice_nature_tokens"]
    
    # Format canon pack if provided
    canon_pack_section = ""
    if canon_pack and (canon_pack.get("locked_lines") or canon_pack.get("locked_nodes") or canon_pack.get("locked_branches")):
        from sparnot.scene_generation.canon_pack import format_canon_pack_prompt
        canon_pack_section = format_canon_pack_prompt(canon_pack)
    
    # Build prompt
    prompt = f"""You are generating a narrative scene for a game based on compiled design schemas.

NARRATIVE INTENT:
- Logline: {bundle.canonical_schemas['narrative_intent']['logline']}
- Setting: {gen_context.setting}
- Dominant Tone: {narrative_ir['dominant_tone']}
- Secondary Tone: {narrative_ir.get('secondary_tone', 'None')}
- Excluded Tones: {', '.join(narrative_ir.get('excluded_tones', []))}
- Style Tokens: {', '.join(narrative_ir.get('style_tokens', []))}
- Themes: {', '.join(bundle.canonical_schemas['narrative_intent'].get('themes', []))}
- Theme Weights: {json.dumps(narrative_ir.get('theme_weights', {}), indent=2)}
- Setting Tokens: {', '.join(narrative_ir.get('setting_tokens', []))}
- Constraints: {json.dumps(narrative_ir.get('constraints', {}), indent=2)}

PLAYER EXPERIENCE:
- Player Fantasy: {narrative_ir['player_fantasy']}
- Player Agency: {narrative_ir['player_agency']}
- Choices Per Point: {choices_per_point['min']}-{choices_per_point['max']} options at each choice point
- Choices Per Interaction: {choices_per_interaction['min']}-{choices_per_interaction['max']} total choice points in this scene
- Choice Nature Tokens: {', '.join(choice_nature)}

{scene_context}

CHARACTERS:
{''.join(character_descriptions)}

INVARIANTS (must be respected):
{chr(10).join(f"- {inv}" for inv in gen_context.invariants_text) if gen_context.invariants_text else "- None specified"}

ACT CONTEXT:
{chr(10).join(f"- Act Purpose: {purpose}" for purpose in gen_context.act_purposes) if gen_context.act_purposes else "- No act context provided"}

{canon_pack_section}

GENERATION REQUIREMENTS:
1. Generate a complete branching dialogue scene
2. CRITICAL: Choice structure limits (HARD MAXIMUMS):
   {f"- If player agency is 'low', create a cutscene with NO player choices (dialogue-only nodes)." if choices_per_interaction['max'] == 0 else f"- Create EXACTLY {choices_per_interaction['min']}-{choices_per_interaction['max']} nodes that have player choices (choice points). NO MORE than {choices_per_interaction['max']} choice points total."}
   {f"- Each choice point must have {choices_per_point['min']}-{choices_per_point['max']} options. NO MORE than {choices_per_point['max']} options per choice point." if choices_per_point['max'] > 0 else ""}
   - You may have additional nodes WITHOUT choices (end nodes, intermediate dialogue-only nodes), but count only nodes WITH choices toward the limit.
   - DO NOT exceed these maximums. If you need to create more narrative beats, use dialogue-only nodes or combine choices.
3. Include screenplay/stage directions in each node describing actions, expressions, and environment
4. Use exposition in dialogue to reveal character personality, internal thoughts, and actions naturally
5. The dialogue should reflect the characters' beliefs, personality, and voice tokens
6. The scene should fit the setting, tone, and themes
7. Choices should reflect the choice nature tokens: {', '.join(choice_nature)}
8. Choices should branch meaningfully based on the player fantasy ({narrative_ir['player_fantasy']})
9. Respect all style tokens and constraints
10. The scene should feel authentic to the narrative intent
11. Use the scene summary and act purpose if provided

BRANCHING DIALOGUE INTELLIGENCE:
- Some choices should CONVERGE: Different initial choices lead to the same choice point later (e.g., different approaches to a problem that all lead to the same decision)
- Some choices should DIVERGE: Choices open completely independent paths that don't reconnect (e.g., joining different factions)
- Use narrative logic to determine which choices converge vs diverge:
  * Convergent choices: Different means to the same end, temporary disagreements that resolve, different perspectives on the same issue
  * Divergent choices: Major plot branches, faction alignment, character relationship changes, irreversible decisions
- Higher agency ({narrative_ir['player_agency']}) should have more divergent paths
- Lower agency should have more convergent paths (choices feel meaningful but don't drastically change outcomes)

OUTPUT FORMAT:
Generate the scene in the following JSON format with branching dialogue structure:
{{
  "scene_id": "{scene_id if scene_id else 'generated_scene_1'}",
  "scene_type": "<scene type from arc if available, or appropriate type>",
  "location": "<brief location description>",
  "summary": "<brief scene summary>",
  "dialogue_tree": {{
    "root": {{
      "screenplay": "<stage directions describing what happens before/around this dialogue - actions, expressions, environment details>",
      "dialogue": [
        {{
          "speaker": "<character name>",
          "text": "<dialogue text>",
          "exposition": "<optional: internal thoughts, actions, or personality-revealing details for this character>"
        }}
      ],
      "choices": [
        {{
          "choice_id": "choice_1",
          "text": "<choice text>",
          "choice_nature": "<which choice_nature_token this reflects>",
          "next_node": "node_1",
          "convergence_hint": "<'converges' if this path will merge with others, 'diverges' if independent, or 'continues' if neither>"
        }}
      ]
    }},
    "node_1": {{
      "screenplay": "<stage directions for this node>",
      "dialogue": [
        {{
          "speaker": "<character name>",
          "text": "<dialogue text>",
          "exposition": "<optional: character exposition>"
        }}
      ],
      "choices": [
        {{
          "choice_id": "choice_2",
          "text": "<choice text>",
          "choice_nature": "<choice nature token>",
          "next_node": "<next node id or 'end' if scene ends>",
          "convergence_hint": "<convergence type>"
        }}
      ]
    }},
    "node_2": {{
      "screenplay": "<stage directions>",
      "dialogue": [...],
      "choices": [...],
      "converges_from": ["node_1", "node_3"],
      "convergence_note": "<explanation of how these paths converged>"
    }}
  }},
  "branching_summary": "<clear explanation of the branching structure: which paths converge, which diverge, and why>",
  "narrative_notes": "<notes on how tone, themes, and style tokens are reflected>"
}}

IMPORTANT FORMATTING:
- Include "screenplay" field in each node with stage directions (actions, expressions, environment)
- Use "exposition" field in dialogue to show character personality, internal thoughts, or actions
- Exposition should be brief and reveal character traits naturally
- Screenplay should describe what's happening visually/physically between dialogue

CRITICAL CONSTRAINTS:
{f"- For LOW agency: Create a cutscene with NO player choices (dialogue-only nodes only)" if choices_per_interaction['max'] == 0 else f"- MAXIMUM {choices_per_interaction['max']} nodes with player choices. Count only nodes that have a 'choices' array with at least 1 option."}
{f"- MAXIMUM {choices_per_point['max']} options per choice point. Each choice point should have {choices_per_point['min']}-{choices_per_point['max']} options." if choices_per_point['max'] > 0 else ""}
- You may include additional nodes without choices (end nodes, intermediate dialogue-only nodes) as needed for narrative flow
- Show convergence by having multiple nodes point to the same "next_node" or use "converges_from" field
- Show divergence by having choices lead to completely separate node paths that don't reconnect
- The tree should have a clear structure that makes sense narratively
- DO NOT exceed the maximum choice point count or options per choice point

Generate the scene now:"""

    return prompt


def generate_scene(
    bundle_path: Path,
    scene_id: Optional[str] = None,
    lock_manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generate a scene from a compiled bundle."""
    # Load bundle
    print(f"Loading compiled bundle: {bundle_path}")
    with open(bundle_path) as f:
        bundle_data = json.load(f)
    
    bundle = CompiledBundle(**bundle_data)
    
    # Handle locks if provided
    canon_pack = None
    forced_participants = None
    
    if lock_manager and scene_id:
        from sparnot.scene_generation.conflict_detection import detect_lock_conflicts
        from sparnot.scene_generation.conflict_resolution import (
            resolve_conflicts,
            apply_resolution,
            get_forced_participants,
        )
        from sparnot.scene_generation.canon_pack import build_canon_pack
        from sparnot.scene_generation.scene_matching import match_scene_to_locks
        import click
        
        # Match scene to locks
        matched_scene_id = match_scene_to_locks(scene_id, bundle, lock_manager)
        if matched_scene_id:
            scene_locks = lock_manager.get_scene_locks(matched_scene_id)
            if scene_locks:
                # BEFORE LLM CALL: Detect conflicts
                conflicts = detect_lock_conflicts(matched_scene_id, scene_locks, bundle)
                
                if conflicts:
                    # Resolve conflicts interactively
                    resolution = resolve_conflicts(conflicts, "current_project")  # TODO: get project name
                    # Apply resolution
                    scene_locks = apply_resolution(scene_locks, resolution)
                    # Get forced participants
                    forced_participants = get_forced_participants(resolution, conflicts)
                    # Save updated locks
                    lock_file = lock_manager.load_locks()
                    lock_file.scene_locks[matched_scene_id] = scene_locks
                    lock_manager.save_locks(lock_file)
                
                # Build canon pack from resolved locks
                canon_pack = build_canon_pack(matched_scene_id, lock_manager, bundle)
    
    # Build prompt
    print("Building generation prompt...")
    prompt = build_scene_prompt(bundle, canon_pack=canon_pack, forced_participants=forced_participants)
    
    # Generate with OpenAI
    print("Generating scene with OpenAI...")
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert narrative designer who creates compelling game scenes based on design schemas. You always output valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        scene_json = json.loads(response.choices[0].message.content)
        
        # Post-process: Add line_ids to dialogue lines
        from sparnot.scene_generation.post_process import add_line_ids
        scene_json = add_line_ids(scene_json)
        
        return scene_json
        
    except Exception as e:
        print(f"Error generating scene: {e}")
        raise


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python generate_scene.py <compiled_bundle.json> [output_path]")
        print("\nExample:")
        print("  python generate_scene.py data/projects/Nimbus/compiled_bundle.json")
        print("  python generate_scene.py sparnot/poc_compiler/fixtures/action_rpg_postapoc_compiled.json output/scene.json")
        sys.exit(1)
    
    bundle_path = Path(sys.argv[1])
    if not bundle_path.exists():
        print(f"✗ Bundle file not found: {bundle_path}")
        sys.exit(1)
    
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else bundle_path.parent / "generated_scene.json"
    
    # Try to detect project name from bundle path (e.g., data/projects/Nimbus/compiled_bundle.json -> Nimbus)
    project_name = None
    lock_manager = None
    scene_id = None
    
    if "projects" in bundle_path.parts:
        # Extract project name from path
        projects_idx = bundle_path.parts.index("projects")
        if projects_idx + 1 < len(bundle_path.parts):
            project_name = bundle_path.parts[projects_idx + 1]
            
            # Initialize lock manager
            from sparnot.scene_generation.lock_storage import LockManager
            lock_manager = LockManager(project_name, data_dir=Path("data"))
            
            # Try to extract scene_id from bundle
            try:
                with open(bundle_path) as f:
                    bundle_data = json.load(f)
                    arc_ir = bundle_data.get("ir", {}).get("arc_ir")
                    if arc_ir and arc_ir.get("scene_order"):
                        scene_id = arc_ir["scene_order"][0]  # Use first scene
            except Exception:
                pass  # If we can't extract scene_id, that's okay
    
    try:
        scene = generate_scene(bundle_path, scene_id=scene_id, lock_manager=lock_manager)
        
        # Save scene
        print(f"\nSaving generated scene to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(scene, f, indent=2)
        
        print(f"\n✓ Scene generated successfully!")
        print(f"\nScene Summary: {scene.get('summary', 'N/A')}")
        print(f"Location: {scene.get('location', 'N/A')}")
        
        # Count dialogue nodes and choices
        dialogue_tree = scene.get('dialogue_tree', {})
        if dialogue_tree:
            node_count = len(dialogue_tree)
            total_choices = sum(len(node.get('choices', [])) for node in dialogue_tree.values())
            print(f"Dialogue Nodes: {node_count}")
            print(f"Total Player Choices: {total_choices}")
        else:
            # Fallback for old format
            print(f"Dialogue Entries: {len(scene.get('dialogue', []))}")
            print(f"Player Choices: {len(scene.get('player_choices', []))}")
        
        if scene.get('branching_notes'):
            print(f"\nBranching Notes: {scene['branching_notes'][:100]}...")
        
    except Exception as e:
        print(f"\n✗ Failed to generate scene: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

