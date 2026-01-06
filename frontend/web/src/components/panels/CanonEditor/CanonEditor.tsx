import { useState, useEffect } from "react";
import "./CanonEditor.css";
import DiagnosticOutput from "./DiagnosticOutput";
import { schemasApi, compileApi, assistantApi } from "../../../services/api";
import type { AllSchemas, DiagnosticsReport } from "../../../types/models";

interface CanonEditorProps {
  project: string | null;
  onCompile: () => void;
  onStatusChange: () => void;
}

interface TabInfo {
  id: string;
  label: string;
  isDraft: boolean;
  schemaType: string;
  schemaId?: string;
}

export default function CanonEditor({ project, onCompile, onStatusChange }: CanonEditorProps) {
  const [schemas, setSchemas] = useState<AllSchemas | null>(null);
  const [draftSchemas, setDraftSchemas] = useState<AllSchemas | null>(null);
  const [activeTab, setActiveTab] = useState<string>("narrative_intent");
  const [editorContent, setEditorContent] = useState<string>("");
  const [diagnostics, setDiagnostics] = useState<DiagnosticsReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasWorkspace, setHasWorkspace] = useState(false);

  useEffect(() => {
    if (project) {
      loadSchemas();
      loadDraftSchemas();
      runDiagnostics();
      // Periodically check for draft updates
      const interval = setInterval(() => {
        loadDraftSchemas();
      }, 5000);
      return () => clearInterval(interval);
    } else {
      // Reset state when project is cleared
      setSchemas(null);
      setDraftSchemas(null);
      setEditorContent("");
      setDiagnostics(null);
      setActiveTab("narrative_intent");
      setHasWorkspace(false);
    }
  }, [project]);

  useEffect(() => {
    if ((schemas || draftSchemas) && activeTab) {
      updateEditorContent();
    }
  }, [schemas, draftSchemas, activeTab]);

  const loadSchemas = async () => {
    if (!project) return;
    try {
      setIsLoading(true);
      const data = await schemasApi.getAll(project);
      setSchemas(data);
    } catch (error) {
      console.error("Failed to load schemas:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadDraftSchemas = async () => {
    if (!project) return;
    try {
      const data = await assistantApi.getWorkspaceSchemas(project);
      const hasDrafts = !!(data.narrative_intent || data.arc || Object.keys(data.characters || {}).length > 0);
      setHasWorkspace(hasDrafts);
      setDraftSchemas(data);
    } catch (error) {
      // Workspace might not exist yet, that's okay
      setHasWorkspace(false);
      setDraftSchemas(null);
    }
  };

  const updateEditorContent = () => {
    const isDraft = activeTab.startsWith("draft_");
    const tabId = isDraft ? activeTab.replace("draft_", "") : activeTab;
    const source = isDraft ? draftSchemas : schemas;
    
    if (!source) return;

    let content = "";
    if (tabId === "narrative_intent" && source.narrative_intent) {
      content = JSON.stringify(source.narrative_intent, null, 2);
    } else if (tabId === "arc" && source.arc) {
      content = JSON.stringify(source.arc, null, 2);
    } else if (tabId.startsWith("character_")) {
      const charId = tabId.replace("character_", "");
      const char = source.characters?.[charId];
      if (char) {
        content = JSON.stringify(char, null, 2);
      }
    }

    setEditorContent(content);
  };

  const runDiagnostics = async () => {
    if (!project) return;
    try {
      const result = await compileApi.runDiagnostics(project);
      setDiagnostics(result);
    } catch (error) {
      console.error("Failed to run diagnostics:", error);
    }
  };

  const handleSave = async () => {
    if (!project || !activeTab || !editorContent) return;

    try {
      let data;
      try {
        data = JSON.parse(editorContent);
      } catch (e) {
        alert("Invalid JSON");
        return;
      }

      const isDraft = activeTab.startsWith("draft_");
      const tabId = isDraft ? activeTab.replace("draft_", "") : activeTab;

      if (isDraft) {
        // Save to workspace
        if (tabId === "narrative_intent") {
          await assistantApi.saveWorkspaceSchema(project, "narrative_intent", data);
        } else if (tabId === "arc") {
          await assistantApi.saveWorkspaceSchema(project, "arc", data);
        } else if (tabId.startsWith("character_")) {
          const charId = tabId.replace("character_", "");
          await assistantApi.saveWorkspaceSchema(project, "character", data, charId);
        }
        await loadDraftSchemas();
      } else {
        // Save to canonical
        if (tabId === "narrative_intent") {
          await schemasApi.save(project, "narrative_intent", data);
        } else if (tabId === "arc") {
          await schemasApi.save(project, "arc", data);
        } else if (tabId.startsWith("character_")) {
          const charId = tabId.replace("character_", "");
          await schemasApi.save(project, "character", data, charId);
        }
        await loadSchemas();
      }

      await runDiagnostics();
      onStatusChange();
    } catch (error) {
      console.error("Failed to save:", error);
      alert(`Save failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  const handleCompile = async () => {
    await onCompile();
    await runDiagnostics();
  };

  // Build tabs: canonical first, then drafts
  const tabs: TabInfo[] = [];
  
  // Canonical tabs
  if (schemas) {
    if (schemas.narrative_intent) {
      tabs.push({ id: "narrative_intent", label: "narrative_intent.json", isDraft: false, schemaType: "narrative_intent" });
    }
    if (schemas.arc) {
      tabs.push({ id: "arc", label: "arc.json", isDraft: false, schemaType: "arc" });
    }
    Object.keys(schemas.characters || {}).forEach((id) => {
      tabs.push({ id: `character_${id}`, label: `characters/${id}.json`, isDraft: false, schemaType: "character", schemaId: id });
    });
  }
  
  // Draft tabs (clearly marked)
  if (draftSchemas) {
    if (draftSchemas.narrative_intent) {
      tabs.push({ id: "draft_narrative_intent", label: "📝 narrative_intent.json (DRAFT)", isDraft: true, schemaType: "narrative_intent" });
    }
    if (draftSchemas.arc) {
      tabs.push({ id: "draft_arc", label: "📝 arc.json (DRAFT)", isDraft: true, schemaType: "arc" });
    }
    Object.keys(draftSchemas.characters || {}).forEach((id) => {
      tabs.push({ id: `draft_character_${id}`, label: `📝 characters/${id}.json (DRAFT)`, isDraft: true, schemaType: "character", schemaId: id });
    });
  }

  return (
    <div className="canon-editor">
      <div className="editor-toolbar">
        <div className="editor-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`tab ${activeTab === tab.id ? "active" : ""} ${tab.isDraft ? "draft-tab" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="editor-actions">
          <button className="action-btn" onClick={handleSave}>
            {activeTab.startsWith("draft_") ? "Save Draft" : "Save"}
          </button>
        </div>
      </div>
      {activeTab.startsWith("draft_") && (
        <div className="draft-banner">
          ⚠️ You are editing a DRAFT file. Changes are saved to the workspace and will not affect canonical schemas until committed via the Assistant panel.
        </div>
      )}
      <div className="editor-content">
        <textarea
          className="code-editor"
          value={editorContent}
          onChange={(e) => setEditorContent(e.target.value)}
          spellCheck={false}
        />
      </div>
      {diagnostics && <DiagnosticOutput diagnostics={diagnostics} />}
    </div>
  );
}
