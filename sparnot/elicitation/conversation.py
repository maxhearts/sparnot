"""LLM conversation management for elicitation assistant."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv
from openai import OpenAI

from .diagnostics import DiagnosticsReport
from .working_copy import WorkingCopyManager

# Load environment variables
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")
client = OpenAI(api_key=OPENAI_API_KEY)


def load_readme() -> str:
    """Load README.md content for assistant context."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"
    if readme_path.exists():
        try:
            return readme_path.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


class ConversationManager:
    """Manages streaming LLM interactions for schema elicitation."""
    
    def __init__(self):
        """Initialize conversation manager."""
        self.conversation_history: List[Dict[str, str]] = []
        self.turn_count = 0
    
    def build_system_prompt(self, diagnostics: DiagnosticsReport, conversation_turn: int, project_schemas: Dict[str, Any]) -> str:
        """
        Generate system prompt that shifts focus over time.
        
        Args:
            diagnostics: Current diagnostics report
            conversation_turn: Turn number (0 = first turn)
            project_schemas: Current schema data from workspace
        
        Returns:
            System prompt string
        """
        lines = []
        lines.append("You are an expert narrative design assistant. You are currently IN a conversation with the user, helping them refine their schemas so they successfully compile to Intermediate Representation (IR).")
        lines.append("")
        lines.append("IMPORTANT: You ARE the assistant. Do NOT refer to yourself in third person or tell the user to 'use the assistant' or 'fire up the assistant' - you ARE already the assistant in this conversation.")
        lines.append("")
        
        # Include README context (but instruct to use it for reference, not to repeat it)
        readme_content = load_readme()
        if readme_content:
            lines.append("REFERENCE DOCUMENTATION (use to answer questions, do NOT repeat it verbatim):")
            lines.append("The following describes the CLI, file structure, and schema requirements. Reference it when answering questions, but do not regurgitate it:")
            lines.append("")
            lines.append("[Documentation omitted - available for reference when answering specific questions]")
            lines.append("")
        
        # Shift focus based on turn count
        if conversation_turn == 0:
            lines.append("CURRENT FOCUS: Narrative Understanding and Initial Assessment")
            lines.append("- Restate your understanding of the overall narrative")
            lines.append("- Discuss areas that need to be fleshed out for narrative strength")
            lines.append("- Flag compilation concerns in user-understandable terms")
        elif conversation_turn < 3:
            lines.append("CURRENT FOCUS: Balanced Narrative and Compliance")
            lines.append("- Continue refining narrative elements")
            lines.append("- Address compilation errors and compliance issues")
            lines.append("- Suggest improvements for both narrative quality and schema validity")
        else:
            lines.append("CURRENT FOCUS: Compliance and Compilation")
            lines.append("- Prioritize fixing compilation errors")
            lines.append("- Ensure all schemas are valid and compilable")
            lines.append("- Minimize narrative suggestions unless critical")
        
        lines.append("")
        lines.append("SCHEMA UPDATE FORMAT:")
        lines.append("When you propose changes to schemas, output them in a structured JSON format:")
        lines.append('```json')
        lines.append('{')
        lines.append('  "updates": [')
        lines.append('    {')
        lines.append('      "schema_type": "narrative_intent|character|arc",')
        lines.append('      "schema_id": "character_id or null",')
        lines.append('      "action": "create|update",')
        lines.append('      "data": { ... full schema JSON ... }')
        lines.append('    }')
        lines.append('  ]')
        lines.append('}')
        lines.append('```')
        lines.append("")
        lines.append("CRITICAL: When updating schemas, you MUST preserve the exact JSON structure.")
        lines.append("- Use lowercase keys (e.g., 'acts' not 'Acts')")
        lines.append("- Preserve field names exactly as they appear in the schema")
        lines.append("- Only update the fields that need to change")
        lines.append("- The system will merge your updates with existing data")
        lines.append("")
        lines.append("CHARACTER SCHEMA FORMAT (exact fields required):")
        lines.append("Character schemas MUST have EXACTLY these fields (no others):")
        lines.append("- id: string (character ID)")
        lines.append("- name: string (character name)")
        lines.append("- role: string (one of: protagonist, antagonist, supporting, mentor, foil)")
        lines.append("- beliefs: array of strings (belief statements)")
        lines.append("- personality_tags: array of strings (personality descriptors)")
        lines.append("")
        lines.append("EXAMPLE character schema:")
        lines.append('{')
        lines.append('  "id": "001",')
        lines.append('  "name": "Eli",')
        lines.append('  "role": "protagonist",')
        lines.append('  "beliefs": ["I must find my friends", "The system is corrupt"],')
        lines.append('  "personality_tags": ["determined", "brave", "loyal"]')
        lines.append('}')
        lines.append("")
        lines.append("DO NOT add fields like 'background', 'motivations', 'conflict', 'traits', 'description' - these are NOT part of the schema.")
        lines.append("ONLY use the 5 fields listed above: id, name, role, beliefs, personality_tags.")
        lines.append("")
        lines.append("NARRATIVE INTENT SCHEMA FORMAT (exact fields required):")
        lines.append("Narrative intent schemas MUST have EXACTLY these fields:")
        lines.append("- logline: string (required)")
        lines.append("- tone_weights: dict (required) - Format: {\"tragic\": 0.3, \"hopeful\": 0.5, \"humor\": 0.2}")
        lines.append("  CRITICAL: tone_weights MUST be a dictionary/object, NOT a list. Use format: {\"tone_name\": float_weight, ...}")
        lines.append("  Common tones: tragic, hopeful, humor, mysterious, whimsical, dark, suspenseful")
        lines.append("- themes: array of strings (required, 3-5 items)")
        lines.append("- player_fantasy: string (required) - MUST be one of these EXACT values:")
        lines.append("  power, exploration, story, social, creation, challenge, survival, mastery, mystery, builder, cozy, strategy")
        lines.append("  CRITICAL: Do NOT use descriptive text like 'Players can choose...'. Use ONLY the exact enum value.")
        lines.append("- player_agency: string (required) - MUST be one of these EXACT values: low, medium, high")
        lines.append("  CRITICAL: Do NOT use descriptive text. Use ONLY: 'low', 'medium', or 'high'")
        lines.append("- setting: string (required)")
        lines.append("- invariants: array of strings (optional, 0-5 items)")
        lines.append("")
        lines.append("EXAMPLE narrative_intent schema:")
        lines.append('{')
        lines.append('  "logline": "A hero embarks on a quest to save the world",')
        lines.append('  "tone_weights": {"tragic": 0.3, "hopeful": 0.5, "humor": 0.2},')
        lines.append('  "themes": ["friendship", "sacrifice", "hope"],')
        lines.append('  "player_fantasy": "story",')
        lines.append('  "player_agency": "high",')
        lines.append('  "setting": "A fantasy world with magic and dragons"')
        lines.append('}')
        lines.append("")
        lines.append("ARC SCHEMA FORMAT:")
        lines.append("Arc schemas have two top-level arrays:")
        lines.append("- 'acts': array of act objects with: act_id, act_purpose, required_scenes")
        lines.append("- 'scenes': array of scene objects with: scene_id, scene_type, summary, involved_characters")
        lines.append("")
        lines.append("SCENE TYPE VALUES (exact enum values, use EXACTLY as shown):")
        lines.append("scene_type MUST be one of these EXACT values (use underscores, lowercase):")
        lines.append("  inciting_incident, first_plot_point, midpoint, second_plot_point, climax, resolution,")
        lines.append("  transition, character_development, world_building, tension_release")
        lines.append("CRITICAL: Do NOT invent new scene types. Use ONLY the values listed above.")
        lines.append("")
        
        # Include existing scene_ids so LLM knows what's already taken
        if project_schemas.get("arc") and project_schemas["arc"].get("scenes"):
            existing_scene_ids = [s.get("scene_id") for s in project_schemas["arc"]["scenes"] if s.get("scene_id")]
            if existing_scene_ids:
                lines.append(f"CURRENT EXISTING SCENE IDs: {', '.join(sorted(existing_scene_ids))}")
                lines.append("")
        
        lines.append("CRITICAL: Adding NEW scenes vs Updating EXISTING scenes:")
        lines.append("- When the user asks to ADD a new scene, you MUST create a NEW scene_id that does NOT already exist.")
        if project_schemas.get("arc") and project_schemas["arc"].get("scenes"):
            existing_scene_ids = [s.get("scene_id") for s in project_schemas["arc"]["scenes"] if s.get("scene_id")]
            if existing_scene_ids:
                max_num = max([int(sid.split("_")[-1]) for sid in existing_scene_ids if sid and "_" in sid and sid.split("_")[-1].isdigit()], default=0)
                next_id = f"scene_{max_num + 1}"
                lines.append(f"- Example: Since existing scenes are {', '.join(sorted(existing_scene_ids))}, use '{next_id}' for the new scene.")
            else:
                lines.append("- Check the CURRENT EXISTING SCENE IDs listed above to avoid duplicates.")
        else:
            lines.append("- If no scenes exist yet, start with 'scene_1'.")
            lines.append("- If scene_1 exists, use scene_2, scene_3, etc. Check existing scene_ids first.")
        lines.append("- DO NOT update existing scenes when the user asks to ADD a new scene.")
        lines.append("- ONLY update an existing scene if the user explicitly asks to modify/change/update that specific scene.")
        lines.append("")
        lines.append("EXAMPLE: Adding a NEW scene (user says 'add a new scene' or 'create a scene'):")
        lines.append("  Use a scene_id that does NOT exist in CURRENT EXISTING SCENE IDs above.")
        lines.append('  {"scenes": [{"scene_id": "scene_X", "scene_type": "bonding", "summary": "...", "involved_characters": ["001"]}]}')
        lines.append("  (Replace scene_X with an available scene_id like scene_2, scene_3, etc.)")
        lines.append("")
        lines.append("EXAMPLE: Updating an EXISTING scene (user says 'update scene_1' or 'change scene_1'):")
        lines.append("  Use the EXACT scene_id that exists in CURRENT EXISTING SCENE IDs above.")
        lines.append('  {"scenes": [{"scene_id": "scene_1", "scene_type": "midpoint", "summary": "new summary...", "involved_characters": ["001", "004"]}]}')
        lines.append("")
        lines.append("When updating arcs:")
        lines.append("- To ADD a scene: Use a NEW scene_id NOT in CURRENT EXISTING SCENE IDs. Include ONLY the new scene in the 'scenes' array.")
        lines.append("- To UPDATE a scene: Use an EXISTING scene_id from CURRENT EXISTING SCENE IDs. Include ONLY the updated scene in the 'scenes' array.")
        lines.append("- To update an act: Include the full act object. The system will merge by act_id.")
        lines.append("- When adding a scene to a specific act: Include the scene in 'scenes' AND include the act with the scene_id in its 'required_scenes' list.")
        lines.append("  Example: To add scene_2 to act_3, include both:")
        lines.append("    'acts': [{'act_id': 'act_3', 'act_purpose': '...', 'required_scenes': ['scene_2']}]")
        lines.append("    'scenes': [{'scene_id': 'scene_2', 'scene_type': '...', 'summary': '...', 'involved_characters': [...]}]")
        lines.append("- The system automatically merges scenes by scene_id, so you only need to include the scene(s) you're adding or updating.")
        lines.append("- DO NOT nest scenes inside acts. Scenes are a separate top-level array.")
        lines.append("")
        lines.append("DIAGNOSTICS STATUS:")
        if diagnostics.can_compile and not diagnostics.errors:
            lines.append("✓ Schemas are currently compilable!")
        else:
            lines.append("✗ Compilation errors found:")
            for error in diagnostics.errors:
                lines.append(f"  - {error.message}")
        
        if diagnostics.warnings:
            lines.append(f"\nWarnings ({len(diagnostics.warnings)}):")
            for warning in diagnostics.warnings[:5]:  # Limit to first 5
                lines.append(f"  ⚠ {warning}")
        
        return "\n".join(lines)
    
    def build_initial_message(self, project_schemas: Dict[str, Any], diagnostics: DiagnosticsReport, consistency_report: Optional[Any] = None) -> str:
        """Build initial assistant message that restates understanding."""
        lines = []
        
        # Check if project is empty
        has_intent = bool(project_schemas.get("narrative_intent"))
        has_characters = bool(project_schemas.get("characters"))
        has_arc = bool(project_schemas.get("arc"))
        is_empty = not (has_intent or has_characters or has_arc)
        
        if is_empty:
            lines.append("Welcome! I see this is a new project with no schemas yet.")
            lines.append("")
            lines.append("I'm here to help you create your narrative schemas step by step. Let's start by discussing your story idea.")
            lines.append("")
            lines.append("To get started, I'll need:")
            lines.append("  • A narrative intent (logline, setting, themes, player fantasy/agency)")
            lines.append("  • Characters (their roles, beliefs, personalities)")
            lines.append("  • An arc structure (acts and scenes)")
            lines.append("")
            lines.append("Let's begin with your narrative concept. What's your story about?")
            return "\n".join(lines)
        
        # Project has some content - summarize what we have
        lines.append("Let me review your project schemas and provide an assessment.\n")
        
        # Summarize what we have
        if project_schemas.get("narrative_intent"):
            intent = project_schemas["narrative_intent"]
            lines.append("NARRATIVE INTENT:")
            lines.append(f"  Logline: {intent.get('logline', 'N/A')}")
            lines.append(f"  Setting: {intent.get('setting', 'N/A')[:100]}...")
            lines.append(f"  Themes: {', '.join(intent.get('themes', []))}")
            lines.append(f"  Player Fantasy: {intent.get('player_fantasy', 'N/A')}")
            lines.append(f"  Player Agency: {intent.get('player_agency', 'N/A')}")
            lines.append("")
        else:
            lines.append("NARRATIVE INTENT: Not yet created\n")
        
        if project_schemas.get("characters"):
            lines.append(f"CHARACTERS: {len(project_schemas['characters'])} defined")
            # Show all characters, sorted by ID for consistency
            sorted_chars = sorted(project_schemas["characters"], key=lambda c: c.get('id', ''))
            for char in sorted_chars:
                lines.append(f"  - {char.get('name', 'N/A')} ({char.get('id', 'N/A')})")
            lines.append("")
        else:
            lines.append("CHARACTERS: None defined yet\n")
        
        if project_schemas.get("arc"):
            arc = project_schemas["arc"]
            lines.append("ARC:")
            lines.append(f"  Acts: {len(arc.get('acts', []))}")
            lines.append(f"  Scenes: {len(arc.get('scenes', []))}")
            lines.append("")
        else:
            lines.append("ARC: Not yet created\n")
        
        # Add diagnostics
        if not diagnostics.can_compile or diagnostics.errors:
            lines.append("COMPILATION ISSUES:")
            for error in diagnostics.errors[:5]:  # Limit to first 5
                lines.append(f"  ✗ {error.message}")
            lines.append("")
            lines.append("I'll help you resolve these issues and refine your schemas.")
        else:
            lines.append("✓ Your schemas are currently compilable!")
            if diagnostics.warnings:
                lines.append(f"However, there are {len(diagnostics.warnings)} warnings to consider.")
            lines.append("\nI can help you further refine the narrative and ensure everything is optimal.")
        
        # Add consistency check results
        if consistency_report and consistency_report.has_issues:
            from .consistency import ConsistencyChecker
            checker = ConsistencyChecker()
            lines.append("")
            lines.append("=" * 60)
            lines.append("CONSISTENCY CHECK")
            lines.append("=" * 60)
            lines.append(checker.format_report(consistency_report))
            lines.append("I can help you update characters and scenes to better align with your narrative intent.")
        
        return "\n".join(lines)
    
    def stream_llm_response(self, messages: List[Dict[str, str]]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Stream LLM response and parse JSON updates.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        
        Returns:
            Tuple of (full_response_text, parsed_json_updates)
        """
        response_text = ""
        json_updates = None
        
        try:
            stream = client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for assistant
                messages=messages,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_text += content
                    print(content, end="", flush=True)
            
            print()  # New line after streaming
            
            # Try to parse JSON updates from response
            json_updates = self.parse_json_updates(response_text)
            
        except Exception as e:
            print(f"\nError streaming LLM response: {e}")
            raise
        
        return response_text, json_updates
    
    def parse_json_updates(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON schema updates from LLM response.
        
        Looks for JSON code blocks with structure:
        {
          "updates": [
            {
              "schema_type": "narrative_intent|character|arc",
              "schema_id": "...",
              "action": "create|update",
              "data": { ... }
            }
          ]
        }
        
        Returns:
            Dict with "updates" list, or None if no valid JSON found
        """
        # Try to find JSON code block
        json_start = response_text.find("```json")
        if json_start == -1:
            json_start = response_text.find("```")
        if json_start == -1:
            return None
        
        # Find code block end
        code_start = response_text.find("\n", json_start)
        if code_start == -1:
            return None
        
        json_end = response_text.find("```", code_start)
        if json_end == -1:
            return None
        
        json_str = response_text[code_start:json_end].strip()
        
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "updates" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
        
        return None
    
    def start_conversation(self, project: str, diagnostics: DiagnosticsReport, working_copy_manager: WorkingCopyManager, consistency_checker) -> str:
        """
        Initialize conversation and get opening statement.
        
        Returns:
            Opening message from assistant
        """
        self.conversation_history = []
        self.turn_count = 0
        
        # Load current schemas from workspace
        project_schemas = {
            "narrative_intent": working_copy_manager.load_working_copy(project, "narrative_intent"),
            "arc": working_copy_manager.load_working_copy(project, "arc"),
            "characters": [],
        }
        
        for char_id in working_copy_manager.list_working_characters(project):
            char_data = working_copy_manager.load_working_copy(project, "character", char_id)
            if char_data:
                project_schemas["characters"].append(char_data)
        
        # Run consistency check
        consistency_report = None
        if project_schemas.get("narrative_intent"):
            consistency_report = consistency_checker.check_consistency(
                project_schemas["narrative_intent"],
                project_schemas.get("characters", []),
                project_schemas.get("arc")
            )
        
        # Build initial message
        initial_message = self.build_initial_message(project_schemas, diagnostics, consistency_report)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": initial_message,
        })
        
        return initial_message
    
    def process_user_message(self, user_message: str, project: str, diagnostics: DiagnosticsReport, working_copy_manager: WorkingCopyManager) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process user message and get LLM response.
        
        Returns:
            Tuple of (response_text, json_updates)
        """
        self.turn_count += 1
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })
        
        # Build system prompt
        project_schemas = {
            "narrative_intent": working_copy_manager.load_working_copy(project, "narrative_intent"),
            "arc": working_copy_manager.load_working_copy(project, "arc"),
            "characters": [],
        }
        for char_id in working_copy_manager.list_working_characters(project):
            char_data = working_copy_manager.load_working_copy(project, "character", char_id)
            if char_data:
                project_schemas["characters"].append(char_data)
        
        system_prompt = self.build_system_prompt(diagnostics, self.turn_count, project_schemas)
        
        # Build messages list
        messages = [
            {"role": "system", "content": system_prompt},
        ] + self.conversation_history
        
        # Stream response
        response_text, json_updates = self.stream_llm_response(messages)
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response_text,
        })
        
        return response_text, json_updates

