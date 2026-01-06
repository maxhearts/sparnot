import { useState, useEffect, useRef } from "react";
import { scenesApi } from "../../../services/api";
import type { GeneratedScene, DialogueNode } from "../../../types/models";
import "./ScenePlayer.css";

interface ScenePlayerProps {
  project: string;
  sceneId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface PlaybackState {
  currentNodeId: string | null;
  visitedNodes: Set<string>;
  history: Array<{
    type: "screenplay" | "dialogue" | "exposition" | "choice" | "summary";
    content: string;
    speaker?: string;
  }>;
  isWaitingForChoice: boolean;
  currentChoices: Array<{ choice_id: string; text: string; next_node: string }>;
  isComplete: boolean;
}

export default function ScenePlayer({ project, sceneId, isOpen, onClose }: ScenePlayerProps) {
  const [scene, setScene] = useState<GeneratedScene | null>(null);
  const [playbackState, setPlaybackState] = useState<PlaybackState>({
    currentNodeId: "root",
    visitedNodes: new Set(),
    history: [],
    isWaitingForChoice: false,
    currentChoices: [],
    isComplete: false,
  });
  const [isLoading, setIsLoading] = useState(false);
  const historyEndRef = useRef<HTMLDivElement>(null);
  const visitedNodesRef = useRef<Set<string>>(new Set());

  // Load scene when opened
  useEffect(() => {
    if (isOpen && project && sceneId) {
      loadScene();
    }
  }, [isOpen, project, sceneId]);

  // Reset state when closed
  useEffect(() => {
    if (!isOpen) {
      setScene(null);
      visitedNodesRef.current = new Set();
      setPlaybackState({
        currentNodeId: "root",
        visitedNodes: new Set(),
        history: [],
        isWaitingForChoice: false,
        currentChoices: [],
        isComplete: false,
      });
    }
  }, [isOpen]);

  // Auto-scroll to bottom when history updates
  useEffect(() => {
    if (historyEndRef.current) {
      historyEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [playbackState.history]);

  const loadScene = async () => {
    if (!project || !sceneId) return;
    setIsLoading(true);
    try {
      const sceneData = await scenesApi.get(project, sceneId);
      setScene(sceneData);
      // Start playback
      startPlayback(sceneData);
    } catch (error) {
      console.error("Failed to load scene:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const startPlayback = async (sceneData: GeneratedScene) => {
    // Reset state
    visitedNodesRef.current = new Set();
    setPlaybackState({
      currentNodeId: "root",
      visitedNodes: new Set(),
      history: [
        {
          type: "summary",
          content: `Scene: ${sceneData.scene_id} (${sceneData.scene_type})${sceneData.location ? ` - ${sceneData.location}` : ""}${sceneData.summary ? `\n\n${sceneData.summary}` : ""}`,
        },
      ],
      isWaitingForChoice: false,
      currentChoices: [],
      isComplete: false,
    });

    // Wait a moment, then start playing
    await delay(1000);
    // Don't mark root as visited yet - we'll mark it when we actually process it
    await playNode(sceneData, "root");
  };

  const playNode = async (sceneData: GeneratedScene, nodeId: string) => {
    if (!nodeId || nodeId === "end") {
      // End of scene - show summary first, then mark as complete
      if (sceneData.branching_summary || sceneData.narrative_notes) {
        await delay(1000);
        let summaryText = "";
        if (sceneData.branching_summary) {
          summaryText += `Branching Structure:\n${sceneData.branching_summary}`;
        }
        if (sceneData.narrative_notes) {
          summaryText += (summaryText ? "\n\n" : "") + `Narrative Notes:\n${sceneData.narrative_notes}`;
        }
        
        setPlaybackState((prev) => ({
          ...prev,
          history: [...prev.history, { type: "summary", content: summaryText }],
        }));
        await delay(1000);
      }
      
      // Mark as complete AFTER showing summary
      setPlaybackState((prev) => ({
        ...prev,
        isComplete: true,
        isWaitingForChoice: false,
      }));
      return;
    }

    // Get dialogue tree
    const dialogueTree = sceneData.dialogue_tree || {};
    const node = dialogueTree[nodeId];

    if (!node) {
      setPlaybackState((prev) => ({
        ...prev,
        history: [
          ...prev.history,
          { type: "summary", content: `⚠ Error: Node '${nodeId}' not found` },
        ],
        isComplete: true,
      }));
      return;
    }

    // Check for loops - only warn if we've actually visited this node before
    // (silently skip if it's a legitimate revisit, but log for debugging)
    if (visitedNodesRef.current.has(nodeId)) {
      // Don't show warning - just skip to prevent infinite loops
      // This can happen in legitimate branching scenarios
      return;
    }

    // Mark as visited BEFORE processing (to prevent revisiting during processing)
    visitedNodesRef.current.add(nodeId);
    setPlaybackState((prev) => ({
      ...prev,
      visitedNodes: new Set(visitedNodesRef.current),
    }));

    // Show screenplay
    if (node.screenplay) {
      await delay(500);
      setPlaybackState((prev) => ({
        ...prev,
        history: [...prev.history, { type: "screenplay", content: node.screenplay }],
      }));
      await delay(1000);
    }

    // Show dialogue
    const dialogue = node.dialogue;
    if (dialogue) {
      if (Array.isArray(dialogue)) {
        for (const line of dialogue) {
          await delay(500);
          setPlaybackState((prev) => ({
            ...prev,
            history: [
              ...prev.history,
              {
                type: "dialogue",
                content: line.text || "",
                speaker: line.speaker,
              },
            ],
          }));
          
          if (line.exposition) {
            await delay(300);
            setPlaybackState((prev) => ({
              ...prev,
              history: [
                ...prev.history,
                { type: "exposition", content: line.exposition || "" },
              ],
            }));
          }
          
          await delay(1500);
        }
      } else if (typeof dialogue === "string" && node.speaker) {
        await delay(500);
        setPlaybackState((prev) => ({
          ...prev,
          history: [
            ...prev.history,
            {
              type: "dialogue",
              content: dialogue,
              speaker: node.speaker,
            },
          ],
        }));
        await delay(1500);
      }
    }

    // Show exposition if it's not part of dialogue lines
    if (node.exposition && !Array.isArray(dialogue)) {
      await delay(500);
      setPlaybackState((prev) => ({
        ...prev,
        history: [
          ...prev.history,
          { type: "exposition", content: node.exposition || "" },
        ],
      }));
      await delay(1000);
    }

    // Handle choices
    const choices = node.choices || [];
    if (choices.length > 0) {
      await delay(500);
      setPlaybackState((prev) => ({
        ...prev,
        isWaitingForChoice: true,
        currentChoices: choices,
        currentNodeId: nodeId,
      }));
    } else {
      // No choices, check for next_node
      const nextNode = node.next_node;
      if (nextNode) {
        await delay(500);
        await playNode(sceneData, nextNode);
      } else {
        // End of path
        await delay(500);
        await playNode(sceneData, "end");
      }
    }
  };

  const handleChoice = async (choice: { choice_id: string; text: string; next_node: string }) => {
    // Add choice to history
    setPlaybackState((prev) => ({
      ...prev,
      history: [
        ...prev.history,
        { type: "choice", content: `✓ ${choice.text}` },
      ],
      isWaitingForChoice: false,
      currentChoices: [],
    }));

    await delay(500);

    // Continue to next node
    if (scene) {
      await playNode(scene, choice.next_node);
    }
  };

  const delay = (ms: number): Promise<void> => {
    return new Promise((resolve) => setTimeout(resolve, ms));
  };

  if (!isOpen) return null;

  return (
    <div className="scene-player-overlay" onClick={onClose}>
      <div className="scene-player-modal" onClick={(e) => e.stopPropagation()}>
        <div className="scene-player-header">
          <h3>Playing Scene: {sceneId}</h3>
          <button className="scene-player-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="scene-player-content">
          {isLoading ? (
            <div className="scene-player-loading">Loading scene...</div>
          ) : (
            <>
              <div className="scene-player-history">
                {playbackState.history.map((item, idx) => (
                  <div key={idx} className={`history-item history-${item.type}`}>
                    {item.type === "screenplay" && (
                      <div className="screenplay-text">{item.content}</div>
                    )}
                    {item.type === "dialogue" && (
                      <div className="dialogue-line">
                        <strong>{item.speaker}:</strong> {item.content}
                      </div>
                    )}
                    {item.type === "exposition" && (
                      <div className="exposition-text">{item.content}</div>
                    )}
                    {item.type === "choice" && (
                      <div className="choice-selected">{item.content}</div>
                    )}
                    {item.type === "summary" && (
                      <div className="summary-text">{item.content}</div>
                    )}
                  </div>
                ))}
                {playbackState.isWaitingForChoice && (
                  <div className="choices-container">
                    <div className="choices-label">CHOOSE:</div>
                    {playbackState.currentChoices.map((choice, idx) => (
                      <button
                        key={choice.choice_id || idx}
                        className="choice-button"
                        onClick={() => handleChoice(choice)}
                      >
                        {choice.text}
                      </button>
                    ))}
                  </div>
                )}
                {playbackState.isComplete && (
                  <div className="scene-complete">
                    <div className="scene-complete-label">END OF SCENE</div>
                  </div>
                )}
                <div ref={historyEndRef} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

