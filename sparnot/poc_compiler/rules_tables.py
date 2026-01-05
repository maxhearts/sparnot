"""Expansive rule tables for canonicalization."""

from typing import Dict, List, Tuple
import re


# Player Fantasy Canonicalization
PLAYER_FANTASY_CANON = {
    "story",
    "power",
    "survival",
    "mastery",
    "exploration",
    "mystery",
    "builder",
    "cozy",
    "social",
    "strategy",
    "creation",
    "challenge",
}

PLAYER_FANTASY_SYNONYMS: Dict[str, str] = {
    # story
    "narrative": "story",
    "plot": "story",
    "story": "story",
    "rpg_story": "story",
    # power
    "power": "power",
    "godlike": "power",
    "power_fantasy": "power",
    "overpowered": "power",
    "demigod": "power",
    # survival
    "survival": "survival",
    "hardcore": "survival",
    "permadeath": "survival",
    "roguelike_survival": "survival",
    # mastery
    "mastery": "mastery",
    "skill": "mastery",
    "precision": "mastery",
    "soulslike": "mastery",
    "speedrun": "mastery",
    # exploration
    "exploration": "exploration",
    "open_world": "exploration",
    "wander": "exploration",
    "discovery": "exploration",
    "metroidvania": "exploration",
    # mystery
    "mystery": "mystery",
    "detective": "mystery",
    "investigation": "mystery",
    "noir": "mystery",
    # builder
    "builder": "builder",
    "crafting": "builder",
    "factory": "builder",
    "automation": "builder",
    "sandbox": "builder",
    # cozy
    "cozy": "cozy",
    "wholesome": "cozy",
    "slice_of_life": "cozy",
    # social
    "social": "social",
    "dating": "social",
    "party": "social",
    "relationship": "social",
    # strategy
    "strategy": "strategy",
    "tactics": "strategy",
    "4x": "strategy",
    "management": "strategy",
    "rts": "strategy",
    "deckbuilder": "strategy",
    # creation
    "creation": "creation",
    "creative": "creation",
    "artistic": "creation",
    "design": "creation",
    # challenge
    "challenge": "challenge",
    "challenging": "challenge",
    "difficulty": "challenge",
    "hard": "challenge",
}


# Player Agency Canonicalization
PLAYER_AGENCY_CANON = {"low", "medium", "high"}

PLAYER_AGENCY_SYNONYMS: Dict[str, str] = {
    # low
    "low": "low",
    "linear": "low",
    "guided": "low",
    "on_rails": "low",
    "cinematic": "low",
    # medium
    "medium": "medium",
    "hub_and_spoke": "medium",
    "choice_light": "medium",
    "branch_light": "medium",
    # high
    "high": "high",
    "sandbox": "high",
    "systemic": "high",
    "emergent": "high",
    "branching": "high",
    "open_choice": "high",
}


# Scene Type Canonicalization
SCENE_TYPE_CANON = {
    "introduction",
    "inciting_incident",
    "first_test",
    "reveal",
    "twist",
    "setback",
    "betrayal",
    "bonding",
    "midpoint",
    "dark_night",
    "climax",
    "resolution",
    "travel",
    "combat",
    "stealth",
    "puzzle",
    "dialogue",
    "tutorial",
    "economy",
    "base_building",
}

SCENE_TYPE_SYNONYMS: Dict[str, str] = {
    # inciting_incident
    "inciting": "inciting_incident",
    "incident": "inciting_incident",
    "hook": "inciting_incident",
    "catalyst": "inciting_incident",
    "attack": "inciting_incident",
    "disruption": "inciting_incident",
    "call_to_adventure": "inciting_incident",
    "inciting_incident": "inciting_incident",
    # introduction
    "intro": "introduction",
    "introduction": "introduction",
    "opening": "introduction",
    "establishing": "introduction",
    "meet": "introduction",
    "setup": "introduction",
    # reveal
    "reveal": "reveal",
    "discovery": "reveal",
    "uncover": "reveal",
    "expose": "reveal",
    "truth": "reveal",
    # setback
    "setback": "setback",
    "loss": "setback",
    "fail": "setback",
    "defeat": "setback",
    "retreat": "setback",
    # first_test
    "first_test": "first_test",
    "test": "first_test",
    # twist
    "twist": "twist",
    "plot_twist": "twist",
    # betrayal
    "betrayal": "betrayal",
    "betray": "betrayal",
    # bonding
    "bond": "bonding",
    "bonding": "bonding",
    "campfire": "bonding",
    "downtime": "bonding",
    "hangout": "bonding",
    # midpoint
    "midpoint": "midpoint",
    # dark_night
    "dark_night": "dark_night",
    "darkest_hour": "dark_night",
    "crisis": "dark_night",
    # climax
    "climax": "climax",
    "final_battle": "climax",
    "showdown": "climax",
    # resolution
    "resolution": "resolution",
    "ending": "resolution",
    "conclusion": "resolution",
    # first_plot_point
    "first_plot_point": "first_plot_point",
    "plot_point_1": "first_plot_point",
    # second_plot_point
    "second_plot_point": "second_plot_point",
    "plot_point_2": "second_plot_point",
    # puzzle
    "puzzle": "puzzle",
    "riddle": "puzzle",
    "logic": "puzzle",
    "locked_room": "puzzle",
    # base_building
    "base": "base_building",
    "base_building": "base_building",
    "settlement": "base_building",
    "build": "base_building",
    "upgrade": "base_building",
    "home": "base_building",
    # economy
    "economy": "economy",
    "shop": "economy",
    "market": "economy",
    "trade": "economy",
    "crafting": "economy",
    "resources": "economy",
    # combat
    "combat": "combat",
    "fight": "combat",
    "battle": "combat",
    "boss": "combat",
    "skirmish": "combat",
    # stealth
    "stealth": "stealth",
    "infiltration": "stealth",
    "sneak": "stealth",
    "heist": "stealth",
    # travel
    "travel": "travel",
    "journey": "travel",
    "exploration": "travel",
    # tutorial
    "tutorial": "tutorial",
    "tutorial_scene": "tutorial",
    # dialogue (default fallback)
    "dialogue": "dialogue",
}


# Tone → Style Tokens
TONE_TO_STYLE_TOKENS: Dict[str, List[str]] = {
    "tragic": [
        "bittersweet",
        "high_stakes",
        "restraint",
        "cost_and_consequence",
    ],
    "hopeful": [
        "warmth",
        "forward_motion",
        "resilience",
    ],
    "humor": [
        "moments_of_relief",
        "banter_allowed",
        "contrast_tension",
    ],
    "mysterious": [
        "secrets",
        "unreliable_info",
        "foreshadowing",
    ],
    "whimsical": [
        "playful",
        "surreal_edges",
        "lightness",
    ],
}


# Setting Keywords → Tokens
SETTING_KEYWORDS_TO_TOKENS: List[Tuple[List[str], List[str]]] = [
    # Post-apoc
    (["wasteland", "ruins", "radiation", "fallout"], ["scarcity", "dangerous_remnants", "survival_pressure"]),
    # Dystopia
    (["dystopian", "regime", "police state", "oppression"], ["surveillance", "oppression", "moral_tradeoffs"]),
    # Fantasy
    (["kingdom", "castle", "dragon", "magic"], ["mythic_scale", "ancient_power", "court_intrigue_optional"]),
    # Sci-fi
    (["spaceship", "station", "colony", "ai core"], ["systems_dependence", "closed_ecology", "tech_mystery"]),
    # Cozy
    (["town", "farm", "bakery", "cafe", "neighbors"], ["daily_routine", "community", "low_violence_bias"]),
    # Noir
    (["noir", "detective", "case", "suspect"], ["investigation", "hidden_motives", "moral_ambiguity"]),
    # School
    (["school", "academy", "class", "dorm"], ["social_hierarchy", "relationships", "rituals"]),
    # Sky
    (["floating", "sky city", "cloud", "sky cities"], ["verticality", "open_vistas", "class_stratification"]),
]


# Personality Aliases
PERSONALITY_ALIASES: Dict[str, str] = {
    "hot headed": "hot-headed",
    "hot-headed": "hot-headed",
    "level headed": "level-headed",
    "level-headed": "level-headed",
    "laid back": "laid-back",
    "laid-back": "laid-back",
    "quick witted": "quick-witted",
    "quick-witted": "quick-witted",
}


# Personality Tags → Voice Tokens
PERSONALITY_TAGS_TO_VOICE_TOKENS: Dict[str, List[str]] = {
    "reliable": ["grounded", "steady", "plainspoken"],
    "brave": ["direct", "action_oriented", "resolute"],
    "determined": ["focused", "minimal_excuses", "forward"],
    "serene": ["calm", "measured", "low_reactivity"],
    "mysterious": ["elliptical", "withholds_info", "implicature"],
    "ambitious": ["assertive", "status_sensitive", "future_oriented"],
    "competitive": ["challenging", "scorekeeping", "provocative"],
    "hot-headed": ["blunt", "fast_escalation", "emotion_forward"],
    "cautious": ["risk_aware", "asks_questions", "hedges"],
    "cynical": ["dry", "skeptical", "cuts_through"],
    "optimistic": ["bright", "reframes_loss", "encouraging"],
    "charming": ["warm", "socially_fluid", "light_teasing"],
    "awkward": ["hesitant", "overexplains", "self_corrects"],
    "stoic": ["minimal", "controlled", "understated"],
    "level-headed": ["balanced", "rational", "measured"],
    "laid-back": ["relaxed", "casual", "low_pressure"],
    "quick-witted": ["sharp", "banter_ready", "clever"],
}


# Invariant Patterns → Constraints
INVARIANT_PATTERNS: List[Tuple[re.Pattern, str, Any]] = [
    (re.compile(r"not destructible|indestructible|no destruction", re.IGNORECASE), "env_destructible", False),
    (re.compile(r"fully destructible|destructible world", re.IGNORECASE), "env_destructible", True),
    (re.compile(r"death is irreversible|no resurrection|cannot revive|no revive", re.IGNORECASE), "resurrection_allowed", False),
    (re.compile(r"revive|resurrection allowed|resurrection_allowed", re.IGNORECASE), "resurrection_allowed", True),
    (re.compile(r"characters can be killed|permadeath|death possible|death allowed", re.IGNORECASE), "death_allowed", True),
    (re.compile(r"cannot be killed|immortal protagonists|no death", re.IGNORECASE), "death_allowed", False),
    (re.compile(r"downed|knocked|incapacitated briefly|downed state", re.IGNORECASE), "downed_state_allowed", True),
    (re.compile(r"no downed state|no downed", re.IGNORECASE), "downed_state_allowed", False),
    (re.compile(r"friendly fire on|friendly_fire", re.IGNORECASE), "friendly_fire", True),
    (re.compile(r"friendly fire off|no friendly fire", re.IGNORECASE), "friendly_fire", False),
    (re.compile(r"fast travel.*allowed|fast travel.*available", re.IGNORECASE), "fast_travel_allowed", True),
    (re.compile(r"no fast travel", re.IGNORECASE), "fast_travel_allowed", False),
    (re.compile(r"day night|time of day|day/night", re.IGNORECASE), "time_of_day_cycle", True),
]


def canonicalize_player_fantasy(value: str) -> Tuple[str, Optional[str]]:
    """Canonicalize player fantasy value. Returns (canonical, original_if_unknown)."""
    normalized = value.lower().strip()
    canonical = PLAYER_FANTASY_SYNONYMS.get(normalized)
    if canonical:
        return canonical, None
    return "story", value  # Default fallback


def canonicalize_player_agency(value: str) -> str:
    """Canonicalize player agency value. Returns canonical."""
    normalized = value.lower().strip()
    canonical = PLAYER_AGENCY_SYNONYMS.get(normalized)
    if canonical:
        return canonical
    return "medium"  # Default fallback


# Player Agency → Choice Count Ranges
# choices_per_point: number of choices at any given choice point in dialogue
# choices_per_interaction: total number of choice points in an interaction/scene
AGENCY_TO_CHOICE_COUNTS: Dict[str, Dict[str, Dict[str, int]]] = {
    "low": {
        "choices_per_point": {"min": 0, "max": 0},      # Cutscenes only, no choices
        "choices_per_interaction": {"min": 0, "max": 0},  # No choice points
    },
    "medium": {
        "choices_per_point": {"min": 2, "max": 3},      # 2-3 options at each choice
        "choices_per_interaction": {"min": 1, "max": 3},  # 1-3 choice points total
    },
    "high": {
        "choices_per_point": {"min": 2, "max": 5},      # 2-5 options at each choice
        "choices_per_interaction": {"min": 1, "max": 6},  # 1-6 choice points total
    },
}


# Player Fantasy → Choice Nature Tokens
FANTASY_TO_CHOICE_NATURE: Dict[str, List[str]] = {
    "story": [
        "narrative_choice",
        "plot_branch",
        "character_relationship",
        "story_consequence",
    ],
    "power": [
        "dominance_choice",
        "power_expression",
        "overwhelming_option",
        "status_display",
    ],
    "survival": [
        "resource_tradeoff",
        "risk_reward",
        "survival_priority",
        "hard_choice",
    ],
    "mastery": [
        "skill_expression",
        "precision_choice",
        "optimization_path",
        "challenge_selection",
    ],
    "exploration": [
        "discovery_choice",
        "path_selection",
        "hidden_content",
        "world_interaction",
    ],
    "mystery": [
        "investigation_choice",
        "clue_prioritization",
        "deduction_path",
        "information_gathering",
    ],
    "builder": [
        "construction_choice",
        "resource_allocation",
        "design_decision",
        "optimization_choice",
    ],
    "cozy": [
        "comfort_choice",
        "relationship_building",
        "low_stakes_decision",
        "wholesome_option",
    ],
    "social": [
        "relationship_choice",
        "social_interaction",
        "party_dynamics",
        "connection_building",
    ],
    "strategy": [
        "tactical_choice",
        "resource_management",
        "long_term_planning",
        "systemic_decision",
    ],
}


def canonicalize_scene_type(value: str) -> Tuple[str, Optional[str]]:
    """Canonicalize scene type. Returns (canonical, original_if_unknown)."""
    normalized = value.lower().strip()
    canonical = SCENE_TYPE_SYNONYMS.get(normalized)
    if canonical:
        return canonical, None
    return "dialogue", value  # Default fallback


def normalize_personality_tag(tag: str) -> str:
    """Normalize personality tag using aliases."""
    normalized = tag.lower().strip()
    return PERSONALITY_ALIASES.get(normalized, normalized)


def extract_setting_tokens(setting_text: str) -> List[str]:
    """Extract setting tokens from setting text using keyword matching."""
    setting_lower = setting_text.lower()
    tokens = []
    for keywords, token_list in SETTING_KEYWORDS_TO_TOKENS:
        if any(keyword in setting_lower for keyword in keywords):
            tokens.extend(token_list)
    return list(set(tokens))  # Deduplicate


def parse_invariant_patterns(invariants: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """Parse invariants using patterns. Returns (constraints_dict, unmatched_invariants)."""
    constraints = {}
    unmatched = []
    
    for inv in invariants:
        matched = False
        for pattern, key, value in INVARIANT_PATTERNS:
            if pattern.search(inv):
                constraints[key] = value
                matched = True
                break
        if not matched:
            unmatched.append(inv)
    
    return constraints, unmatched

