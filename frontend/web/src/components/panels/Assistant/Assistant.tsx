import { useState, useEffect, useRef } from "react";
import "./Assistant.css";
import { assistantApi } from "../../../services/api";
import type { AssistantResponse } from "../../../types/models";

interface AssistantProps {
  project: string | null;
}

interface ReviewFile {
  schema_type: string;
  schema_id?: string;
  status: string;
  file: string;
}

export default function Assistant({ project }: AssistantProps) {
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [input, setInput] = useState("");
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewFiles, setReviewFiles] = useState<ReviewFile[]>([]);
  const [approvedFiles, setApprovedFiles] = useState<Set<string>>(new Set());
  const [viewingFile, setViewingFile] = useState<{ schema_type: string; schema_id?: string; content: any } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (project) {
      // Always reinitialize when project changes
      setMessages([]);
      setInput("");
      setIsInitialized(false);
      setHasChanges(false);
      setIsReviewing(false);
      setReviewFiles([]);
      setApprovedFiles(new Set());
      setViewingFile(null);
      initializeAssistant();
    } else {
      // Reset state when project is cleared
      setMessages([]);
      setInput("");
      setIsInitialized(false);
      setHasChanges(false);
      setIsReviewing(false);
      setReviewFiles([]);
      setApprovedFiles(new Set());
      setViewingFile(null);
    }
  }, [project]);

  // Periodically check for changes (only when not loading)
  useEffect(() => {
    if (!project || !isInitialized || isLoading || isReviewing) return;
    
    const interval = setInterval(async () => {
      try {
        const status = await assistantApi.getWorkspaceStatus(project);
        setHasChanges(status.changes.length > 0);
      } catch (e) {
        // Silently ignore errors to avoid console spam
        console.debug("Workspace status check failed:", e);
      }
    }, 10000); // Check every 10 seconds (less frequent to reduce load)
    
    return () => clearInterval(interval);
  }, [project, isInitialized, isLoading, isReviewing]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const initializeAssistant = async () => {
    if (!project) return;
    try {
      setIsLoading(true);
      const result = await assistantApi.init(project);
      setMessages([{ role: "assistant", content: result.opening_message }]);
      setIsInitialized(true);
    } catch (error) {
      console.error("Failed to initialize assistant:", error);
      setMessages([{ role: "assistant", content: "Failed to initialize assistant." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCommand = async (command: string) => {
    if (!project) return;

    const cmd = command.trim().toLowerCase();
    
    if (cmd === "/help" || cmd === "help") {
      const helpText = `Available commands:
/status - Show current changes and compilation status
/diff   - Show diffs for all changed files
/help   - Show this help message
exit/quit/done - End session and review/commit changes`;
      setMessages((prev) => [...prev, { role: "assistant", content: helpText }]);
      return;
    }
    
    if (cmd === "/status" || cmd === "status") {
      if (!isInitialized) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Error: Assistant not initialized. Please wait for initialization to complete." },
        ]);
        return;
      }
      
      setIsLoading(true);
      try {
        const status = await assistantApi.getWorkspaceStatus(project);
        let statusText = "=== Current Status ===\n\n";
        
        if (!status.has_workspace) {
          statusText += "No workspace active. The assistant may need to be reinitialized.\n";
          statusText += "Try sending a message to the assistant to create a workspace.\n";
        } else if (status.changes.length === 0) {
          statusText += "✓ No changes in workspace\n";
        } else {
          statusText += `Changes (${status.changes.length}):\n`;
          status.changes.forEach((change) => {
            const icon = change.status === "created" ? "➕" : change.status === "modified" ? "✏️" : "➖";
            const label = change.schema_id ? `${change.schema_type} (${change.schema_id})` : change.schema_type;
            statusText += `  ${icon} ${change.status}: ${label}\n`;
          });
        }
        
        if (status.diagnostics) {
          statusText += "\nCompilation Status:\n";
          if (status.diagnostics.can_compile && status.diagnostics.errors.length === 0) {
            statusText += "  ✓ Schemas are compilable!\n";
          } else {
            statusText += `  ✗ ${status.diagnostics.errors.length} compilation error(s)\n`;
            if (status.diagnostics.errors.length > 0) {
              status.diagnostics.errors.slice(0, 3).forEach((err: any) => {
                statusText += `    - ${err.message}\n`;
              });
            }
          }
          if (status.diagnostics.warnings && status.diagnostics.warnings.length > 0) {
            statusText += `  ⚠ ${status.diagnostics.warnings.length} warning(s)\n`;
          }
        } else if (status.has_workspace) {
          statusText += "\nCompilation Status: Not available\n";
        }
        
        setMessages((prev) => [...prev, { role: "assistant", content: statusText }]);
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : "Unknown error";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error getting status: ${errorMsg}\n\nThis might mean:\n- The backend server is not running\n- The assistant needs to be reinitialized\n- There's a network connectivity issue` },
        ]);
      } finally {
        setIsLoading(false);
      }
      return;
    }
    
    if (cmd === "/diff" || cmd === "diff") {
      if (!isInitialized) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Error: Assistant not initialized. Please wait for initialization to complete." },
        ]);
        return;
      }
      
      setIsLoading(true);
      try {
        const status = await assistantApi.getWorkspaceStatus(project) as any;
        
        if (!status.has_workspace) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "No workspace active. The assistant may need to be reinitialized.\nTry sending a message to the assistant to create a workspace." },
          ]);
          return;
        }
        
        if (status.changes.length === 0) {
          setMessages((prev) => [...prev, { role: "assistant", content: "✓ No changes to show" }]);
          return;
        }
        
        let diffText = "=== File Diffs ===\n\n";
        status.changes.forEach((change: any) => {
          const label = change.schema_id ? `${change.schema_type} (${change.schema_id})` : change.schema_type;
          diffText += `\n${change.status.toUpperCase()}: ${label}\n`;
          diffText += "-".repeat(60) + "\n";
          // Construct file key from schema_type and schema_id
          const fileKey = change.schema_id ? `${change.schema_type}:${change.schema_id}` : change.schema_type;
          if (status.diffs && status.diffs[fileKey]) {
            diffText += status.diffs[fileKey] + "\n";
          } else {
            diffText += "(No diff available)\n";
          }
        });
        
        setMessages((prev) => [...prev, { role: "assistant", content: diffText }]);
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : "Unknown error";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error getting diffs: ${errorMsg}\n\nThis might mean:\n- The backend server is not running\n- The assistant needs to be reinitialized\n- There's a network connectivity issue` },
        ]);
      } finally {
        setIsLoading(false);
      }
      return;
    }
    
    if (cmd === "exit" || cmd === "quit" || cmd === "done") {
      // Start review workflow
      startReviewWorkflow();
      return;
    }
  };

  const startReviewWorkflow = async () => {
    if (!project) return;
    
    if (!isInitialized) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Assistant not initialized. Please wait for initialization to complete." },
      ]);
      return;
    }
    
    setIsLoading(true);
    try {
      const status = await assistantApi.getWorkspaceStatus(project);
      
      if (!status.has_workspace) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "No workspace active. The assistant may need to be reinitialized.\nTry sending a message to the assistant to create a workspace." },
        ]);
        setIsLoading(false);
        return;
      }
      
      if (status.changes.length === 0) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "✓ No changes to review. Workspace is empty." },
        ]);
        setIsLoading(false);
        return;
      }
      
      // Set up review files
      const files: ReviewFile[] = status.changes.map((change: any) => ({
        schema_type: change.schema_type,
        schema_id: change.schema_id,
        status: change.status,
        file: change.file,
      }));
      
      setReviewFiles(files);
      setIsReviewing(true);
      
      // Show compilation status
      let reviewText = "=== Review Changes ===\n\n";
      reviewText += `Found ${files.length} file(s) to review:\n\n`;
      
      if (status.diagnostics) {
        reviewText += "Compilation Status:\n";
        if (status.diagnostics.can_compile && status.diagnostics.errors.length === 0) {
          reviewText += "  ✓ Schemas are compilable!\n";
        } else {
          reviewText += `  ✗ ${status.diagnostics.errors.length} compilation error(s)\n`;
          if (status.diagnostics.errors.length > 0) {
            status.diagnostics.errors.slice(0, 3).forEach((err: any) => {
              reviewText += `    - ${err.message}\n`;
            });
          }
        }
        if (status.diagnostics.warnings && status.diagnostics.warnings.length > 0) {
          reviewText += `  ⚠ ${status.diagnostics.warnings.length} warning(s)\n`;
        }
      }
      
      reviewText += "\nUse the review panel below to approve or skip each file.";
      
      setMessages((prev) => [...prev, { role: "assistant", content: reviewText }]);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error starting review: ${errorMsg}\n\nThis might mean:\n- The backend server is not running\n- The assistant needs to be reinitialized\n- There's a network connectivity issue` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewFile = async (file: ReviewFile) => {
    if (!project) return;
    
    try {
      const fileContent = await assistantApi.getWorkspaceFile(
        project,
        file.schema_type,
        file.schema_id
      );
      setViewingFile(fileContent);
    } catch (error) {
      alert(`Error loading file: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  const handleToggleApproval = (file: ReviewFile) => {
    const fileKey = `${file.schema_type}:${file.schema_id || ""}`;
    setApprovedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(fileKey)) {
        next.delete(fileKey);
      } else {
        next.add(fileKey);
      }
      return next;
    });
  };

  const handleCommitSelective = async () => {
    if (!project || approvedFiles.size === 0) {
      alert("Please approve at least one file to commit.");
      return;
    }
    
    setIsCommitting(true);
    try {
      const filesToCommit = reviewFiles
        .filter((file) => {
          const fileKey = `${file.schema_type}:${file.schema_id || ""}`;
          return approvedFiles.has(fileKey);
        })
        .map((file) => ({
          schema_type: file.schema_type,
          schema_id: file.schema_id,
        }));
      
      const result = await assistantApi.commitSelective(project, filesToCommit);
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `✓ Committed ${result.committed} file(s) successfully!` },
      ]);
      
      setHasChanges(false);
      setIsReviewing(false);
      setReviewFiles([]);
      setApprovedFiles(new Set());
      setViewingFile(null);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error committing changes: ${error instanceof Error ? error.message : "Unknown error"}` },
      ]);
    } finally {
      setIsCommitting(false);
    }
  };

  const handleCancelReview = () => {
    setIsReviewing(false);
    setReviewFiles([]);
    setApprovedFiles(new Set());
    setViewingFile(null);
  };

  const handleSend = async () => {
    if (!project || !input.trim() || isLoading) return;

    const userMessage = input.trim();
    const userMessageLower = userMessage.toLowerCase();
    
    // Check for commands first
    if (userMessageLower.startsWith("/") || 
        userMessageLower === "exit" || 
        userMessageLower === "quit" || 
        userMessageLower === "done") {
      setInput("");
      setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
      await handleCommand(userMessage);
      return;
    }

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await assistantApi.sendMessage(project, userMessage);
      setMessages((prev) => [...prev, { role: "assistant", content: response.response }]);
      
      // Show compilation status after update
      if (response.diagnostics) {
        let diagnosticsText = "\n=== Compilation Status ===\n";
        if (response.diagnostics.can_compile && response.diagnostics.errors.length === 0) {
          diagnosticsText += "✓ Schemas are compilable!\n";
        } else {
          diagnosticsText += `✗ ${response.diagnostics.errors.length} compilation error(s)\n`;
          if (response.diagnostics.errors.length > 0) {
            response.diagnostics.errors.slice(0, 3).forEach((err: any) => {
              diagnosticsText += `  - ${err.message}\n`;
            });
          }
        }
        if (response.diagnostics.warnings && response.diagnostics.warnings.length > 0) {
          diagnosticsText += `⚠ ${response.diagnostics.warnings.length} warning(s)\n`;
        }
        setMessages((prev) => [...prev, { role: "assistant", content: diagnosticsText }]);
      }
      
      // Check for changes after message
      try {
        const status = await assistantApi.getWorkspaceStatus(project);
        setHasChanges(status.changes.length > 0);
      } catch (e) {
        // Ignore status check errors
        console.error("Failed to check workspace status:", e);
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errorMessage}\n\nIf this persists, try refreshing the page or reinitializing the assistant.` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!project || isCommitting) return;
    
    setIsCommitting(true);
    try {
      await assistantApi.commit(project);
      setHasChanges(false);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "✓ Changes committed successfully! The schemas have been updated." },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error committing changes: ${error instanceof Error ? error.message : "Unknown error"}` },
      ]);
    } finally {
      setIsCommitting(false);
    }
  };

  const handleDiscard = async () => {
    if (!project || isCommitting) return;
    
    if (!confirm("Are you sure you want to discard all workspace changes? This cannot be undone.")) {
      return;
    }
    
    setIsCommitting(true);
    try {
      await assistantApi.discard(project);
      setHasChanges(false);
      setIsReviewing(false);
      setReviewFiles([]);
      setApprovedFiles(new Set());
      setViewingFile(null);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "✓ Changes discarded. Workspace has been cleared." },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error discarding changes: ${error instanceof Error ? error.message : "Unknown error"}` },
      ]);
    } finally {
      setIsCommitting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!project) {
    return (
      <div className="assistant">
        <div className="assistant-placeholder">Select a project to use the assistant</div>
      </div>
    );
  }

  return (
    <div className="assistant">
      <div className="assistant-header">
        <h3>Elicitation Assistant</h3>
        <div className="assistant-commands">
          <button className="command-btn" onClick={() => handleCommand("/status")}>
            /status
          </button>
          <button className="command-btn" onClick={() => handleCommand("/diff")}>
            /diff
          </button>
          <button className="command-btn" onClick={() => handleCommand("/help")}>
            /help
          </button>
          {hasChanges && !isReviewing && (
            <>
              <button 
                className="command-btn command-btn-commit" 
                onClick={handleCommit}
                disabled={isCommitting}
              >
                {isCommitting ? "Committing..." : "Commit All"}
              </button>
              <button 
                className="command-btn command-btn-discard" 
                onClick={handleDiscard}
                disabled={isCommitting}
              >
                Discard
              </button>
            </>
          )}
        </div>
      </div>
      <div className="assistant-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {isLoading && (
          <div className="message message-assistant">
            <div className="message-content">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {isReviewing && (
        <div className="review-panel">
          <div className="review-header">
            <h4>Review Changes ({approvedFiles.size} approved)</h4>
            <button className="review-cancel-btn" onClick={handleCancelReview}>
              Cancel
            </button>
          </div>
          <div className="review-files">
            {reviewFiles.map((file, idx) => {
              const fileKey = `${file.schema_type}:${file.schema_id || ""}`;
              const isApproved = approvedFiles.has(fileKey);
              const label = file.schema_id ? `${file.schema_type} (${file.schema_id})` : file.schema_type;
              
              return (
                <div key={idx} className={`review-file ${isApproved ? "approved" : ""}`}>
                  <div className="review-file-header">
                    <input
                      type="checkbox"
                      checked={isApproved}
                      onChange={() => handleToggleApproval(file)}
                    />
                    <span className="review-file-label">
                      {file.status === "created" ? "➕" : file.status === "modified" ? "✏️" : "➖"} {label}
                    </span>
                    <button
                      className="review-view-btn"
                      onClick={() => handleViewFile(file)}
                    >
                      View JSON
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="review-actions">
            <button
              className="review-commit-btn"
              onClick={handleCommitSelective}
              disabled={isCommitting || approvedFiles.size === 0}
            >
              {isCommitting ? "Committing..." : `Commit ${approvedFiles.size} File(s)`}
            </button>
          </div>
        </div>
      )}
      
      {viewingFile && (
        <div className="file-viewer-overlay" onClick={() => setViewingFile(null)}>
          <div className="file-viewer" onClick={(e) => e.stopPropagation()}>
            <div className="file-viewer-header">
              <h4>
                {viewingFile.schema_id
                  ? `${viewingFile.schema_type} (${viewingFile.schema_id})`
                  : viewingFile.schema_type}
              </h4>
              <button className="file-viewer-close" onClick={() => setViewingFile(null)}>
                ×
              </button>
            </div>
            <div className="file-viewer-content">
              <pre>{JSON.stringify(viewingFile.content, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
      
      <div className="assistant-input">
        <textarea
          className="input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          rows={3}
          disabled={isLoading || isReviewing}
        />
        <button className="send-button" onClick={handleSend} disabled={isLoading || !input.trim() || isReviewing}>
          Send
        </button>
      </div>
    </div>
  );
}
