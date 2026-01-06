import { useState, useEffect } from "react";
import "./App.css";
import Header from "./components/Header/Header";
import CanonEditor from "./components/panels/CanonEditor/CanonEditor";
import Assistant from "./components/panels/Assistant/Assistant";
import DiffViewer from "./components/panels/DiffViewer/DiffViewer";
import SceneViewer from "./components/panels/SceneViewer/SceneViewer";
import ScenePlayer from "./components/panels/ScenePlayer/ScenePlayer";
import { projectsApi, compileApi, scenesApi } from "./services/api";
import type { Project, CompilationStatus } from "./types/models";

function App() {
  const [projects, setProjects] = useState<string[]>([]);
  const [currentProject, setCurrentProject] = useState<string | null>(null);
  const [projectInfo, setProjectInfo] = useState<Project | null>(null);
  const [compilationStatus, setCompilationStatus] = useState<CompilationStatus | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [availableScenes, setAvailableScenes] = useState<Array<{ scene_id: string; scene_type: string }>>([]);
  const [generatedScenes, setGeneratedScenes] = useState<Array<{ scene_id: string; filename: string }>>([]);
  const [isGeneratingScene, setIsGeneratingScene] = useState(false);
  const [playingSceneId, setPlayingSceneId] = useState<string | null>(null);
  const [isScenePlayerOpen, setIsScenePlayerOpen] = useState(false);

  // Load projects on mount
  useEffect(() => {
    loadProjects().catch((err) => {
      console.error("Failed to load projects:", err);
      setError(`Failed to connect to backend: ${err instanceof Error ? err.message : "Unknown error"}`);
    });
  }, []);

  // Load project info when project changes
  useEffect(() => {
    if (currentProject) {
      loadProjectInfo().catch((err) => {
        console.error("Failed to load project info:", err);
      });
      loadCompilationStatus().catch((err) => {
        console.error("Failed to load compilation status:", err);
      });
      loadAvailableScenes().catch((err) => {
        console.error("Failed to load available scenes:", err);
      });
      loadGeneratedScenes().catch((err) => {
        console.error("Failed to load generated scenes:", err);
      });
    } else {
      setAvailableScenes([]);
      setGeneratedScenes([]);
    }
  }, [currentProject]);

  const loadProjects = async () => {
    try {
      const projectList = await projectsApi.list();
      setProjects(projectList);
      if (projectList.length > 0 && !currentProject) {
        setCurrentProject(projectList[0]);
      }
    } catch (error) {
      console.error("Failed to load projects:", error);
      throw error;
    }
  };

  const loadProjectInfo = async () => {
    if (!currentProject) return;
    try {
      const info = await projectsApi.getInfo(currentProject);
      setProjectInfo(info);
    } catch (error) {
      console.error("Failed to load project info:", error);
    }
  };

  const loadCompilationStatus = async () => {
    if (!currentProject) return;
    try {
      const status = await projectsApi.getStatus(currentProject);
      setCompilationStatus(status);
      // Extract run ID from bundle timestamp if available
      // For now, use current time or last compile time
      setRunId(new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19));
    } catch (error) {
      console.error("Failed to load compilation status:", error);
      // Don't throw - status might not exist yet
    }
  };

  const loadAvailableScenes = async () => {
    if (!currentProject) return;
    try {
      const bundle = await compileApi.getBundle(currentProject);
      const arcIr = bundle?.ir?.arc_ir;
      if (arcIr?.scene_order) {
        const scenes = arcIr.scene_order.map((sceneId: string) => ({
          scene_id: sceneId,
          scene_type: arcIr.scene_types?.[sceneId] || "unknown",
        }));
        setAvailableScenes(scenes);
      } else {
        setAvailableScenes([]);
      }
    } catch (error) {
      console.error("Failed to load available scenes:", error);
      setAvailableScenes([]);
    }
  };

  const loadGeneratedScenes = async () => {
    if (!currentProject) return;
    try {
      const scenes = await scenesApi.list(currentProject);
      setGeneratedScenes(scenes);
    } catch (error) {
      console.error("Failed to load generated scenes:", error);
      setGeneratedScenes([]);
    }
  };

  const handleGenerateScene = async (sceneId: string) => {
    if (!currentProject || isGeneratingScene) return;
    
    setIsGeneratingScene(true);
    try {
      await scenesApi.generate(currentProject, sceneId);
      
      // Reload generated scenes
      await loadGeneratedScenes();
      
      // Show success notification
      const notification = document.createElement("div");
      notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #2d5a2d;
        color: #7fff7f;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        font-size: 0.9rem;
        max-width: 300px;
      `;
      notification.textContent = `✓ Scene "${sceneId}" generated! Check Scene Viewer panel.`;
      document.body.appendChild(notification);
      
      setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transition = "opacity 0.3s";
        setTimeout(() => notification.remove(), 300);
      }, 4000);
    } catch (error) {
      console.error("Failed to generate scene:", error);
      alert(`Scene generation failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsGeneratingScene(false);
    }
  };

  const handleProjectChange = (projectName: string) => {
    setCurrentProject(projectName);
    // Reset state when switching projects
    setProjectInfo(null);
    setCompilationStatus(null);
    setRunId(null);
  };

  const handleCompile = async () => {
    if (!currentProject) return;
    try {
      const result = await compileApi.compile(currentProject);
      setRunId(result.timestamp);
      await loadCompilationStatus();
      await loadProjectInfo();
      await loadAvailableScenes(); // Refresh available scenes after compilation
      
      // Trigger diff refresh via custom event
      window.dispatchEvent(new CustomEvent('compile-success', { detail: { project: currentProject } }));
      
      // Show success notification
      const notification = document.createElement("div");
      notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #2d5a2d;
        color: #7fff7f;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        font-size: 0.9rem;
        max-width: 300px;
      `;
      notification.textContent = "✓ Compilation successful! Diffs refreshed automatically.";
      document.body.appendChild(notification);
      
      setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transition = "opacity 0.3s";
        setTimeout(() => notification.remove(), 300);
      }, 3000);
    } catch (error) {
      console.error("Compilation failed:", error);
      alert(`Compilation failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  if (error) {
    return (
      <div className="app">
        <div style={{ padding: "2rem", color: "#ff6b6b", textAlign: "center" }}>
          <h2>Connection Error</h2>
          <p>{error}</p>
          <p style={{ marginTop: "1rem", fontSize: "0.9rem", color: "#888" }}>
            Make sure the FastAPI backend is running on http://localhost:8000
          </p>
          <button
            onClick={() => {
              setError(null);
              loadProjects();
            }}
            style={{
              marginTop: "1rem",
              padding: "0.5rem 1rem",
              background: "#4a9eff",
              border: "none",
              borderRadius: "4px",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Header
        currentProject={currentProject}
        projects={projects}
        runId={runId}
        compilationStatus={compilationStatus}
        availableScenes={availableScenes}
        generatedScenes={generatedScenes}
        isGeneratingScene={isGeneratingScene}
        onProjectChange={handleProjectChange}
        onCompile={handleCompile}
        onCreateProject={loadProjects}
        onGenerateScene={handleGenerateScene}
        onPlayScene={(sceneId) => {
          // Open the interactive scene player
          setPlayingSceneId(sceneId);
          setIsScenePlayerOpen(true);
        }}
      />
      <div className="app-grid">
        <div className="panel panel-1">
          <CanonEditor
            project={currentProject}
            onCompile={handleCompile}
            onStatusChange={loadCompilationStatus}
          />
        </div>
        <div className="panel panel-2">
          <DiffViewer project={currentProject} key={currentProject} />
        </div>
        <div className="panel panel-3">
          <Assistant project={currentProject} key={currentProject} />
        </div>
        <div className="panel panel-4">
          <SceneViewer project={currentProject} key={currentProject} />
        </div>
      </div>
      {currentProject && playingSceneId && (
        <ScenePlayer
          project={currentProject}
          sceneId={playingSceneId}
          isOpen={isScenePlayerOpen}
          onClose={() => {
            setIsScenePlayerOpen(false);
            setPlayingSceneId(null);
          }}
        />
      )}
    </div>
  );
}

export default App;
