import { useState, useEffect, useRef } from "react";
import "./SceneViewer.css";
import { scenesApi } from "../../../services/api";
import type { SceneInfo, GeneratedScene } from "../../../types/models";

interface SceneViewerProps {
  project: string | null;
}

export default function SceneViewer({ project }: SceneViewerProps) {
  const [scenes, setScenes] = useState<SceneInfo[]>([]);
  const [selectedScene, setSelectedScene] = useState<GeneratedScene | null>(null);
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const selectedSceneIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (project) {
      loadScenes();
    } else {
      // Reset state when project is cleared
      setScenes([]);
      setSelectedScene(null);
      setSelectedSceneId(null);
    }
  }, [project]);

  // Auto-refresh generated scenes list periodically (but preserve selection)
  useEffect(() => {
    if (!project) return;
    
    const interval = setInterval(() => {
      loadScenes(); // loadScenes uses ref to preserve selection
    }, 5000); // Check every 5 seconds for new scenes
    
    return () => clearInterval(interval);
  }, [project]);

  // Keep ref in sync with state
  useEffect(() => {
    selectedSceneIdRef.current = selectedSceneId;
  }, [selectedSceneId]);

  useEffect(() => {
    if (project && selectedSceneId) {
      loadScene(selectedSceneId);
    }
  }, [project, selectedSceneId]);

  // Listen for scene selection events from header
  useEffect(() => {
    const handleSelectScene = (event: CustomEvent) => {
      if (event.detail.sceneId) {
        setSelectedSceneId(event.detail.sceneId);
      }
    };
    
    window.addEventListener('select-scene', handleSelectScene as EventListener);
    return () => {
      window.removeEventListener('select-scene', handleSelectScene as EventListener);
    };
  }, []);

  const loadScenes = async () => {
    if (!project) return;
    try {
      const sceneList = await scenesApi.list(project);
      const currentSelectedId = selectedSceneIdRef.current; // Use ref to get current selection
      
      setScenes(sceneList);
      
      // Only set default if no scene is selected AND we have scenes
      if (sceneList.length > 0 && !currentSelectedId) {
        setSelectedSceneId(sceneList[0].scene_id);
      }
      // If selected scene no longer exists, reset to first available
      else if (currentSelectedId && !sceneList.find(s => s.scene_id === currentSelectedId)) {
        if (sceneList.length > 0) {
          setSelectedSceneId(sceneList[0].scene_id);
        } else {
          setSelectedSceneId(null);
        }
      }
      // Otherwise, DO NOT change selectedSceneId - preserve user's selection
      // The scene still exists, so keep the current selection
    } catch (error) {
      console.error("Failed to load scenes:", error);
    }
  };

  const loadScene = async (sceneId: string) => {
    if (!project) return;
    try {
      const scene = await scenesApi.get(project, sceneId);
      setSelectedScene(scene);
    } catch (error) {
      console.error("Failed to load scene:", error);
    }
  };

  if (!project) {
    return (
      <div className="scene-viewer">
        <div className="scene-placeholder">Select a project to view scenes</div>
      </div>
    );
  }

  return (
    <div className="scene-viewer">
      <div className="scene-header">
        <h3>Scene Viewer</h3>
        <select
          className="scene-selector"
          value={selectedSceneId || ""}
          onChange={(e) => {
            const newId = e.target.value || null;
            setSelectedSceneId(newId);
            selectedSceneIdRef.current = newId; // Update ref immediately
          }}
        >
          <option value="">Select scene...</option>
          {scenes.map((scene) => (
            <option key={scene.scene_id} value={scene.scene_id}>
              {scene.scene_id} ({scene.scene_type})
            </option>
          ))}
        </select>
      </div>
      <div className="scene-content">
        {selectedScene ? (
          <div className="scene-display">
            <div className="scene-info">
              <h4>{selectedScene.scene_id}</h4>
              <span className="scene-type">{selectedScene.scene_type}</span>
            </div>
            <div className="scene-dialogue">
              {(() => {
                // Handle both dialogue_tree (object) and dialogue_nodes (array) formats
                let nodes: any[] = [];
                if (selectedScene.dialogue_nodes) {
                  nodes = selectedScene.dialogue_nodes;
                } else if ((selectedScene as any).dialogue_tree) {
                  // Convert dialogue_tree object to array
                  const tree = (selectedScene as any).dialogue_tree;
                  nodes = Object.entries(tree).map(([nodeId, nodeData]: [string, any]) => ({
                    node_id: nodeId,
                    ...nodeData,
                  }));
                }
                
                return nodes.map((node, idx) => (
                  <div key={node.node_id || idx} className="dialogue-node">
                    {node.screenplay && (
                      <div className="screenplay">{node.screenplay}</div>
                    )}
                    {node.dialogue && Array.isArray(node.dialogue) ? (
                      // Handle dialogue as array of {speaker, text, exposition}
                      node.dialogue.map((line: any, lineIdx: number) => {
                        return (
                          <div key={lineIdx} className="dialogue-line-container">
                            {line.speaker && line.text && (
                              <div className="dialogue-line">
                                <strong>{line.speaker}:</strong> {line.text}
                              </div>
                            )}
                            {line.exposition && (
                              <div className="exposition">{line.exposition}</div>
                            )}
                          </div>
                        );
                      })
                    ) : node.speaker && node.dialogue ? (
                      // Handle dialogue as single string (legacy format)
                      <div className="dialogue-line">
                        <strong>{node.speaker}:</strong> {node.dialogue}
                      </div>
                    ) : null}
                    {node.exposition && !Array.isArray(node.dialogue) && (
                      <div className="exposition">{node.exposition}</div>
                    )}
                    {node.choices && Array.isArray(node.choices) && node.choices.length > 0 && (
                      <div className="choices">
                        {node.choices.map((choice: any, choiceIdx: number) => (
                          <div key={choice.choice_id || choiceIdx} className="choice">
                            {choice.text}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ));
              })()}
            </div>
            {selectedScene.branching_summary && (
              <div className="branching-summary">
                <h5>Branching Summary</h5>
                <p>{selectedScene.branching_summary}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="scene-placeholder">No scene selected</div>
        )}
      </div>
    </div>
  );
}

