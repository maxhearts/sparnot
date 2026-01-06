import { useState, useEffect } from "react";
import "./CanonEditor.css";
import DiagnosticOutput from "./DiagnosticOutput";
import { schemasApi, compileApi } from "../../../services/api";
import type { AllSchemas, DiagnosticsReport } from "../../../types/models";

interface CanonEditorProps {
  project: string | null;
  onCompile: () => void;
  onStatusChange: () => void;
}

export default function CanonEditor({ project, onCompile, onStatusChange }: CanonEditorProps) {
  const [schemas, setSchemas] = useState<AllSchemas | null>(null);
  const [activeTab, setActiveTab] = useState<string>("narrative_intent");
  const [editorContent, setEditorContent] = useState<string>("");
  const [diagnostics, setDiagnostics] = useState<DiagnosticsReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (project) {
      loadSchemas();
      runDiagnostics();
    } else {
      // Reset state when project is cleared
      setSchemas(null);
      setEditorContent("");
      setDiagnostics(null);
      setActiveTab("narrative_intent");
    }
  }, [project]);

  useEffect(() => {
    if (schemas && activeTab) {
      updateEditorContent();
    }
  }, [schemas, activeTab]);

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

  const updateEditorContent = () => {
    if (!schemas) return;

    let content = "";
    if (activeTab === "narrative_intent" && schemas.narrative_intent) {
      content = JSON.stringify(schemas.narrative_intent, null, 2);
    } else if (activeTab === "arc" && schemas.arc) {
      content = JSON.stringify(schemas.arc, null, 2);
    } else if (activeTab.startsWith("character_")) {
      const charId = activeTab.replace("character_", "");
      const char = schemas.characters[charId];
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

      if (activeTab === "narrative_intent") {
        await schemasApi.save(project, "narrative_intent", data);
      } else if (activeTab === "arc") {
        await schemasApi.save(project, "arc", data);
      } else if (activeTab.startsWith("character_")) {
        const charId = activeTab.replace("character_", "");
        await schemasApi.save(project, "character", data, charId);
      }

      await loadSchemas();
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

  const tabs = [
    { id: "narrative_intent", label: "narrative_intent.json" },
    { id: "arc", label: "arc.json" },
    ...Object.keys(schemas?.characters || {}).map((id) => ({
      id: `character_${id}`,
      label: `characters/${id}.json`,
    })),
  ];

  return (
    <div className="canon-editor">
      <div className="editor-toolbar">
        <div className="editor-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="editor-actions">
          <button className="action-btn" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
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

