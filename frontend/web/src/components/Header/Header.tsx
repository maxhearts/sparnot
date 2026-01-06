import { useState } from "react";
import type { CompilationStatus } from "../../types/models";
import { projectsApi } from "../../services/api";
import "./Header.css";

interface HeaderProps {
  currentProject: string | null;
  projects: string[];
  runId: string | null;
  compilationStatus: CompilationStatus | null;
  availableScenes: Array<{ scene_id: string; scene_type: string }>;
  generatedScenes: Array<{ scene_id: string; filename: string }>;
  isGeneratingScene: boolean;
  onProjectChange: (project: string) => void;
  onCompile: () => void;
  onCreateProject: () => void;
  onGenerateScene: (sceneId: string) => void;
  onPlayScene: (sceneId: string) => void;
}

export default function Header({
  currentProject,
  projects,
  runId,
  compilationStatus,
  availableScenes,
  generatedScenes,
  isGeneratingScene,
  onProjectChange,
  onCompile,
  onCreateProject,
  onGenerateScene,
  onPlayScene,
}: HeaderProps) {
  const [showProjectMenu, setShowProjectMenu] = useState(false);
  const [showGenerateMenu, setShowGenerateMenu] = useState(false);
  const [showPlayMenu, setShowPlayMenu] = useState(false);

  const getStatusIndicator = () => {
    if (!compilationStatus) return null;
    switch (compilationStatus.status) {
      case "compiles":
        return <span className="status-indicator status-ok">✓ Compiles</span>;
      case "blocking_errors":
        return <span className="status-indicator status-error">✗ Blocking errors</span>;
      case "warnings_only":
        return <span className="status-indicator status-warning">⚠ Warnings only</span>;
      default:
        return null;
    }
  };

  return (
    <header className="app-header">
      <div className="header-left">
        <h1 className="app-title">Narrative Orchestrator</h1>
        {runId && <span className="run-id">Run: {runId}</span>}
      </div>
      <div className="header-center">
        <div className="project-selector">
          <button
            className="project-button"
            onClick={() => setShowProjectMenu(!showProjectMenu)}
          >
            {currentProject || "Select Project"} ▼
          </button>
          {showProjectMenu && (
            <div className="dropdown-menu">
              {projects.map((project) => (
                <button
                  key={project}
                  className="dropdown-item"
                  onClick={() => {
                    onProjectChange(project);
                    setShowProjectMenu(false);
                  }}
                >
                  {project}
                </button>
              ))}
              <button
                className="dropdown-item dropdown-item-new"
                onClick={async () => {
                  const name = prompt("Enter project name:");
                  if (name) {
                    try {
                      await projectsApi.create(name);
                      onCreateProject();
                    } catch (error) {
                      alert(`Failed to create project: ${error instanceof Error ? error.message : "Unknown error"}`);
                    }
                  }
                  setShowProjectMenu(false);
                }}
              >
                + New Project
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="header-right">
        {getStatusIndicator()}
        <button className="action-button" onClick={onCompile}>
          Compile
        </button>
        <div className="dropdown-container">
          <button
            className="action-button"
            onClick={() => setShowGenerateMenu(!showGenerateMenu)}
            disabled={isGeneratingScene || availableScenes.length === 0}
          >
            {isGeneratingScene ? "Generating..." : "Generate Scene ▼"}
          </button>
          {showGenerateMenu && availableScenes.length > 0 && (
            <div className="dropdown-menu">
              {availableScenes.map((scene) => (
                <button
                  key={scene.scene_id}
                  className="dropdown-item"
                  onClick={() => {
                    onGenerateScene(scene.scene_id);
                    setShowGenerateMenu(false);
                  }}
                >
                  {scene.scene_id} ({scene.scene_type})
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="dropdown-container">
          <button
            className="action-button"
            onClick={() => setShowPlayMenu(!showPlayMenu)}
            disabled={generatedScenes.length === 0}
          >
            Play Scene ▼
          </button>
          {showPlayMenu && generatedScenes.length > 0 && (
            <div className="dropdown-menu">
              {generatedScenes.map((scene) => (
                <button
                  key={scene.scene_id}
                  className="dropdown-item"
                  onClick={() => {
                    onPlayScene(scene.scene_id);
                    setShowPlayMenu(false);
                  }}
                >
                  {scene.scene_id}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

