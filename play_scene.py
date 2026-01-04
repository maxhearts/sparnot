#!/usr/bin/env python3
"""Play out a generated scene interactively from JSON."""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


def print_screenplay(screenplay: str, delay: float = 1.0):
    """Print screenplay/stage directions in italics style."""
    if screenplay:
        print(f"\n*{screenplay}*")
        time.sleep(delay)


def print_dialogue(speaker: str, text: str, exposition: str = "", delay: float = 1.5):
    """Print dialogue with formatting, exposition, and delay."""
    print(f"\n[{speaker}]")
    print(f"{text}")
    if exposition:
        print(f"  *{exposition}*")
    print()
    time.sleep(delay)


def show_choices(choices: list, node_id: str = "") -> Optional[str]:
    """Display choices and get user selection. Returns next_node or None."""
    if not choices:
        return None
    
    print("\n" + "="*60)
    print("CHOOSE:")
    print("="*60)
    
    for i, choice in enumerate(choices, 1):
        choice_text = choice.get("text", "")
        print(f"\n{i}. {choice_text}")
    
    print("\n" + "="*60)
    
    while True:
        try:
            selection = input(f"\nEnter choice (1-{len(choices)}) or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                return None
            
            choice_num = int(selection)
            if 1 <= choice_num <= len(choices):
                selected_choice = choices[choice_num - 1]
                next_node = selected_choice.get("next_node")
                
                # Show what was selected (clean, no metadata)
                print(f"\n✓ {selected_choice.get('text', '')}")
                time.sleep(0.5)
                
                return next_node
            else:
                print(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return None


def play_dialogue_tree(dialogue_tree: Dict[str, Any], start_node: str = "root"):
    """Play through the dialogue tree starting from start_node."""
    current_node_id = start_node
    visited_nodes = set()
    
    while current_node_id and current_node_id != "end":
        if current_node_id in visited_nodes:
            print(f"\n⚠ Warning: Revisiting node '{current_node_id}' (possible loop)")
            break
        
        visited_nodes.add(current_node_id)
        node = dialogue_tree.get(current_node_id)
        
        if not node:
            print(f"\n⚠ Error: Node '{current_node_id}' not found in dialogue tree")
            break
        
        # Show screenplay/stage directions
        screenplay = node.get("screenplay", "")
        if screenplay:
            print_screenplay(screenplay)
        
        # Show dialogue
        dialogue_lines = node.get("dialogue", [])
        if dialogue_lines:
            for line in dialogue_lines:
                speaker = line.get("speaker", "Unknown")
                text = line.get("text", "")
                exposition = line.get("exposition", "")
                print_dialogue(speaker, text, exposition)
        
        # Check for convergence note
        if "converges_from" in node:
            convergence_note = node.get("convergence_note", "")
            if convergence_note:
                print(f"\n[Note: {convergence_note}]")
                time.sleep(1)
        
        # Handle choices
        choices = node.get("choices", [])
        if choices:
            next_node = show_choices(choices, current_node_id)
            if next_node is None:  # User quit
                return
            current_node_id = next_node
        else:
            # No choices, check if there's a default next or end
            next_node = node.get("next_node")
            if next_node:
                current_node_id = next_node
            else:
                # End of path
                print("\n" + "="*60)
                print("END OF SCENE")
                print("="*60)
                break


def play_scene(scene_path: Path):
    """Load and play a scene from JSON."""
    print(f"Loading scene: {scene_path}")
    
    try:
        with open(scene_path) as f:
            scene = json.load(f)
    except Exception as e:
        print(f"✗ Error loading scene: {e}")
        return
    
    # Display scene info
    print("\n" + "="*60)
    print("SCENE")
    print("="*60)
    print(f"Scene ID: {scene.get('scene_id', 'N/A')}")
    print(f"Scene Type: {scene.get('scene_type', 'N/A')}")
    print(f"Location: {scene.get('location', 'N/A')}")
    print(f"\nSummary: {scene.get('summary', 'N/A')}")
    print("="*60)
    
    time.sleep(1)
    
    # Check if it's a dialogue tree or old format
    dialogue_tree = scene.get("dialogue_tree")
    
    if dialogue_tree:
        # New format with dialogue tree
        print("\n🎬 Starting scene...\n")
        time.sleep(0.5)
        play_dialogue_tree(dialogue_tree)
    else:
        # Old format - simple dialogue and choices
        dialogue = scene.get("dialogue", [])
        choices = scene.get("player_choices", [])
        
        if dialogue:
            print("\n🎬 Starting scene...\n")
            time.sleep(0.5)
            
            # Show dialogue
            for line in dialogue:
                speaker = line.get("speaker", "Unknown")
                text = line.get("text", "")
                print_dialogue(speaker, text)
            
            # Show choices if present
            if choices:
                next_node = show_choices(choices)
                if next_node:
                    print(f"\n[Would continue to: {next_node}]")
            else:
                print("\n" + "="*60)
                print("END OF SCENE")
                print("="*60)
    
    # Show branching summary and narrative notes at the end
    branching_summary = scene.get("branching_summary")
    narrative_notes = scene.get("narrative_notes")
    
    if branching_summary or narrative_notes:
        print("\n" + "="*60)
        print("SCENE ANALYSIS")
        print("="*60)
        if branching_summary:
            print(f"\nBranching Structure:\n{branching_summary}")
        if narrative_notes:
            print(f"\nNarrative Notes:\n{narrative_notes}")
        print("="*60)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python play_scene.py <generated_scene.json>")
        print("\nExample:")
        print("  python play_scene.py data/projects/Nimbus/generated_scene.json")
        sys.exit(1)
    
    scene_path = Path(sys.argv[1])
    
    if not scene_path.exists():
        print(f"✗ Scene file not found: {scene_path}")
        sys.exit(1)
    
    try:
        play_scene(scene_path)
    except KeyboardInterrupt:
        print("\n\nScene interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error playing scene: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

