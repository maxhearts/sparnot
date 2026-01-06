/**
 * TypeScript type definitions matching backend Pydantic models.
 */

// Project types
export interface Project {
  name: string;
  has_narrative_intent: boolean;
  has_arc: boolean;
  character_count: number;
  has_compiled_bundle: boolean;
}

export interface CompilationStatus {
  compiles: boolean;
  status: "compiles" | "blocking_errors" | "warnings_only";
  errors: string[];
  warnings: string[];
}

export interface CompilationHistoryEntry {
  timestamp: string;
  filename: string;
  path: string;
}

// Schema types
export type SchemaType = "narrative_intent" | "arc" | "character";

export interface NarrativeIntent {
  logline: string;
  tone_weights: Record<string, number>;
  themes: string[];
  player_fantasy: string;
  player_agency: string;
  setting: string;
  invariants: string[];
}

export interface Character {
  id: string;
  name: string;
  role: "protagonist" | "antagonist" | "supporting" | "mentor" | "foil";
  beliefs: string[];
  personality_tags: string[];
}

export interface Act {
  act_id: string;
  act_purpose: string;
  required_scenes: string[];
}

export interface Scene {
  scene_id: string;
  scene_type: string;
  summary: string;
  involved_characters: string[];
}

export interface Arc {
  acts: Act[];
  scenes: Scene[];
}

export interface AllSchemas {
  narrative_intent?: NarrativeIntent;
  arc?: Arc;
  characters: Record<string, Character>;
}

// IR types (from CompiledBundle)
export interface NarrativeIR {
  tone_tokens: string[];
  theme_tokens: string[];
  setting_tokens: string[];
  player_fantasy_canon: string;
  player_agency_canon: string;
  choices_per_point: Record<string, number>;
  choices_per_interaction: Record<string, number>;
  choice_nature_tokens: string[];
  generation_context: Record<string, any>;
}

export interface CharacterIR {
  character_id: string;
  role_canon: string;
  belief_tokens: string[];
  personality_tokens: string[];
  generation_context: Record<string, any>;
}

export interface ArcIR {
  act_order: string[];
  scene_order: string[];
  scene_types: Record<string, string>;
  scene_participants: Record<string, string[]>;
  generation_context: Record<string, any>;
}

export interface LintReport {
  errors: string[];
  warnings: string[];
}

export interface CompiledBundle {
  canonical_schemas: {
    narrative_intent?: NarrativeIntent;
    arc?: Arc;
    characters: Record<string, Character>;
  };
  ir: {
    narrative_ir: NarrativeIR;
    character_irs: Record<string, CharacterIR>;
    arc_ir: ArcIR;
  };
  lint: LintReport;
  hashes: Record<string, string>;
  metadata: {
    compiled_at: string;
    project_name: string;
  };
}

// Diff types
export type ChangeType = "added" | "removed" | "modified";

export interface FieldChange {
  path: string;  // Backend uses 'path'
  change_type: ChangeType;
  old_value?: any;
  new_value?: any;
}

export interface SchemaDiff {
  narrative_intent: FieldChange[];
  characters: Record<string, FieldChange[]>;
  arc: FieldChange[];
}

export interface IRDiff {
  narrative_ir: FieldChange[];
  character_irs: Record<string, FieldChange[]>;
  arc_ir: FieldChange[];
}

export interface PropagationEntry {
  schema_path: string;
  schema_change: FieldChange;
  affected_ir_paths: string[];
  ir_changes: FieldChange[];
}

export interface CompilationDiff {
  schema_diffs: SchemaDiff;
  ir_diffs: IRDiff;
  propagation: PropagationEntry[];
  metadata: Record<string, any>;
}

// Diagnostics types
export interface DiagnosticError {
  category: string;
  message: string;
  schema_type?: string;
  schema_id?: string;
  field_path?: string;
}

export interface DiagnosticsReport {
  errors: DiagnosticError[];
  warnings: string[];
  can_compile: boolean;
}

// Scene types
export interface GeneratedScene {
  scene_id: string;
  scene_type: string;
  dialogue_nodes?: DialogueNode[];  // Array format
  dialogue_tree?: Record<string, DialogueNode>;  // Object format (node_id -> node)
  branching_summary?: string;
  narrative_notes?: string;
  location?: string;
  summary?: string;
}

export interface DialogueNode {
  node_id?: string;
  speaker?: string;
  dialogue?: string | Array<{ speaker: string; text: string; exposition?: string; line_id?: string }>;
  screenplay?: string;
  exposition?: string;
  choices?: Choice[];
}

export interface Choice {
  choice_id: string;
  text: string;
  next_node: string;
  choice_nature?: string;
  convergence_hint?: string;
}

export interface SceneInfo {
  scene_id: string;
  scene_type: string;
  filename: string;
  path: string;
}

// Lock types
export interface Lock {
  lock_id: string;
  scope: "line" | "node" | "branch";
  target: string;
  notes?: string;
  data?: any;
}

export interface SceneLocks {
  scene_id: string;
  locks: Lock[];
  fingerprint?: any;
}

// Assistant types
export interface WorkspaceStatus {
  has_workspace: boolean;
  changes: Array<{
    file: string;
    status: string;
    schema_type?: string;
    schema_id?: string;
  }>;
  diagnostics?: DiagnosticsReport;
}

export interface AssistantMessage {
  message: string;
}

export interface AssistantResponse {
  response: string;
  json_updates?: any[];
  diagnostics?: DiagnosticsReport;
}

