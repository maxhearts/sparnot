"""Consistency checker for narrative schemas."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConsistencyIssue:
    """Represents a consistency issue between schemas."""
    severity: str  # 'warning' or 'suggestion'
    category: str  # 'setting', 'theme', 'tone', 'character', 'scene'
    schema_type: str  # 'character', 'arc', 'scene'
    schema_id: Optional[str]  # Character ID, scene_id, etc.
    field: Optional[str]  # Field name if applicable
    message: str
    suggestion: Optional[str] = None  # Suggested fix


@dataclass
class ConsistencyReport:
    """Report of consistency checks."""
    issues: List[ConsistencyIssue]
    has_issues: bool


class ConsistencyChecker:
    """Checks consistency between narrative_intent and other schemas."""
    
    def check_consistency(self, narrative_intent: Dict[str, Any], characters: List[Dict[str, Any]], arc: Optional[Dict[str, Any]]) -> ConsistencyReport:
        """
        Check consistency between narrative_intent and other schemas.
        
        Args:
            narrative_intent: NarrativeIntent schema data
            characters: List of CharacterSchema data
            arc: ArcSkeleton schema data (optional)
        
        Returns:
            ConsistencyReport with issues and suggestions
        """
        issues = []
        
        if not narrative_intent:
            return ConsistencyReport(issues=[], has_issues=False)
        
        setting = narrative_intent.get("setting", "").lower()
        themes = [t.lower() if isinstance(t, str) else t.get("name", "").lower() if isinstance(t, dict) else "" for t in narrative_intent.get("themes", [])]
        
        # Normalize tone_weights (handle both list and dict formats from raw JSON)
        tone_weights_raw = narrative_intent.get("tone_weights", {})
        tone_weights = {}
        if isinstance(tone_weights_raw, list):
            # Convert list format [{'tone': 'x', 'weight': y}, ...] to dict
            for item in tone_weights_raw:
                if isinstance(item, dict):
                    tone = item.get('tone') or item.get('name')
                    weight = item.get('weight') or item.get('value')
                    if tone and weight is not None:
                        tone_weights[tone] = float(weight)
        elif isinstance(tone_weights_raw, dict):
            tone_weights = tone_weights_raw
        else:
            tone_weights = {}
        
        dominant_tone = max(tone_weights.items(), key=lambda x: x[1])[0] if tone_weights else None
        
        # Check characters against setting/themes
        for char in characters:
            char_id = char.get("id")
            char_name = char.get("name", "")
            beliefs = char.get("beliefs", [])
            personality_tags = char.get("personality_tags", [])
            
            # Extract key terms from setting to check against character beliefs/personality
            setting_keywords = self._extract_setting_keywords(setting)
            
            # Check if character beliefs/personality seem inconsistent with setting
            char_text = " ".join(beliefs + personality_tags).lower()
            
            # Flag obvious mismatches (e.g., "medieval" setting but "cyberpunk" character traits)
            setting_mismatches = self._detect_setting_mismatch(setting, char_text, setting_keywords)
            if setting_mismatches:
                issues.append(ConsistencyIssue(
                    severity="suggestion",
                    category="setting",
                    schema_type="character",
                    schema_id=char_id,
                    field="beliefs/personality_tags",
                    message=f"Character {char_name} ({char_id}) may not fit the current setting",
                    suggestion=setting_mismatches
                ))
        
        # Check scenes against setting/themes
        if arc and arc.get("scenes"):
            for scene in arc["scenes"]:
                scene_id = scene.get("scene_id")
                scene_summary = scene.get("summary", "").lower()
                scene_type = scene.get("scene_type", "")
                
                # Check if scene summary seems inconsistent with setting
                scene_mismatches = self._detect_setting_mismatch(setting, scene_summary, setting_keywords)
                if scene_mismatches:
                    issues.append(ConsistencyIssue(
                        severity="suggestion",
                        category="setting",
                        schema_type="scene",
                        schema_id=scene_id,
                        field="summary",
                        message=f"Scene {scene_id} may not fit the current setting",
                        suggestion=scene_mismatches
                    ))
        
        return ConsistencyReport(issues=issues, has_issues=len(issues) > 0)
    
    def _extract_setting_keywords(self, setting: str) -> List[str]:
        """Extract key setting keywords from setting description."""
        # Common setting types and their keywords
        setting_patterns = {
            "dystopia": ["dystopia", "dystopian", "oppressive", "regime", "totalitarian", "corrupt government", "surveillance", "resistance", "rebellion"],
            "fantasy": ["fantasy", "magic", "medieval", "kingdom", "castle", "dragon", "wizard", "elf", "dwarf", "sword", "quest"],
            "sci-fi": ["science fiction", "sci-fi", "space", "planet", "starship", "alien", "futuristic", "technology", "cyberpunk", "neon"],
            "historical": ["historical", "revolution", "war", "ancient", "empire", "colony", "battle", "army", "king", "queen"],
            "modern": ["modern", "contemporary", "city", "urban", "present day", "current"],
            "post-apocalyptic": ["post-apocalyptic", "wasteland", "ruins", "radiation", "survival", "mutant", "scavenge"],
        }
        
        setting_lower = setting.lower()
        keywords = []
        
        # Match setting patterns
        for pattern_name, pattern_keywords in setting_patterns.items():
            if any(pattern_keyword in setting_lower for pattern_keyword in pattern_keywords):
                keywords.extend(pattern_keywords)
        
        # Also extract any capitalized terms (likely proper nouns or key concepts)
        words = setting.split()
        keywords.extend([w.lower() for w in words if w and w[0].isupper() and len(w) > 2])
        
        return list(set(keywords))  # Deduplicate
    
    def _detect_setting_mismatch(self, setting: str, text: str, setting_keywords: List[str]) -> Optional[str]:
        """Detect if text seems to conflict with setting keywords."""
        text_lower = text.lower()
        setting_lower = setting.lower()
        
        # Common mismatch patterns
        mismatch_patterns = {
            "dystopia": ["medieval", "castle", "kingdom", "fantasy", "magic", "dragon", "sword"],
            "fantasy": ["cyberpunk", "neon", "futuristic", "space", "starship", "computer", "digital"],
            "sci-fi": ["medieval", "castle", "sword", "bow and arrow", "fantasy"],
            "historical": ["cyberpunk", "futuristic", "space", "alien", "robot"],
            "modern": ["medieval", "castle", "dragon", "magic", "space", "alien"],
        }
        
        # Check for obvious mismatches
        for setting_type, conflicting_terms in mismatch_patterns.items():
            if any(keyword in setting_lower for keyword in self._extract_setting_keywords(setting_type)[:3]):
                # This seems to be this setting type
                if any(conflict_term in text_lower for conflict_term in conflicting_terms):
                    return f"Text contains terms that typically conflict with {setting_type} settings. Consider reviewing for consistency."
        
        # If no strong keywords match, it might be a generic setting - no mismatch
        if not setting_keywords:
            return None
        
        # Check if text has NO overlap with setting keywords (might be generic enough)
        # But don't flag this as it's too aggressive
        
        return None
    
    def format_report(self, report: ConsistencyReport) -> str:
        """Format consistency report as human-readable text."""
        if not report.has_issues:
            return "✓ All schemas appear consistent with narrative intent."
        
        lines = []
        lines.append(f"⚠ Found {len(report.issues)} potential consistency issue(s):\n")
        
        # Group by category
        by_category = {}
        for issue in report.issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)
        
        for category, category_issues in by_category.items():
            lines.append(f"{category.upper()} Issues:")
            for issue in category_issues:
                schema_label = issue.schema_type
                if issue.schema_id:
                    schema_label = f"{schema_label} ({issue.schema_id})"
                
                lines.append(f"  • {schema_label}: {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Suggestion: {issue.suggestion}")
            lines.append("")
        
        return "\n".join(lines)

