import { useState, useEffect, useRef } from "react";
import "./Assistant.css";
import { assistantApi } from "../../../services/api";
import type { AssistantResponse } from "../../../types/models";

interface AssistantProps {
  project: string | null;
}

export default function Assistant({ project }: AssistantProps) {
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [input, setInput] = useState("");
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (project) {
      // Always reinitialize when project changes
      setMessages([]);
      setInput("");
      setIsInitialized(false);
      setHasChanges(false);
      initializeAssistant();
    } else {
      // Reset state when project is cleared
      setMessages([]);
      setInput("");
      setIsInitialized(false);
      setHasChanges(false);
    }
  }, [project]);

  // Periodically check for changes (only when not loading)
  useEffect(() => {
    if (!project || !isInitialized || isLoading) return;
    
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
  }, [project, isInitialized, isLoading]);

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
exit/quit/done - End session and commit/discard changes`;
      setMessages((prev) => [...prev, { role: "assistant", content: helpText }]);
      return;
    }
    
    if (cmd === "/status" || cmd === "status") {
      try {
        const status = await assistantApi.getWorkspaceStatus(project);
        let statusText = "=== Current Status ===\n\n";
        
        if (!status.has_workspace) {
          statusText += "No workspace active.\n";
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
        }
        
        setMessages((prev) => [...prev, { role: "assistant", content: statusText }]);
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error getting status: ${error instanceof Error ? error.message : "Unknown error"}` },
        ]);
      }
      return;
    }
    
    if (cmd === "/diff" || cmd === "diff") {
      try {
        const status = await assistantApi.getWorkspaceStatus(project) as any;
        if (status.changes.length === 0) {
          setMessages((prev) => [...prev, { role: "assistant", content: "✓ No changes to show" }]);
          return;
        }
        
        let diffText = "=== File Diffs ===\n\n";
        status.changes.forEach((change: any) => {
          const label = change.schema_id ? `${change.schema_type} (${change.schema_id})` : change.schema_type;
          diffText += `\n${change.status.toUpperCase()}: ${label}\n`;
          diffText += "-".repeat(60) + "\n";
          if (status.diffs && status.diffs[change.file]) {
            diffText += status.diffs[change.file] + "\n";
          } else {
            diffText += "(No diff available)\n";
          }
        });
        
        setMessages((prev) => [...prev, { role: "assistant", content: diffText }]);
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error getting diffs: ${error instanceof Error ? error.message : "Unknown error"}` },
        ]);
      }
      return;
    }
    
    if (cmd === "exit" || cmd === "quit" || cmd === "done") {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Session ended. Use the commit/discard buttons in the header to finalize changes." },
      ]);
      return;
    }
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
          {hasChanges && (
            <>
              <button 
                className="command-btn command-btn-commit" 
                onClick={handleCommit}
                disabled={isCommitting}
              >
                {isCommitting ? "Committing..." : "Commit Changes"}
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
      <div className="assistant-input">
        <textarea
          className="input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          rows={3}
          disabled={isLoading}
        />
        <button className="send-button" onClick={handleSend} disabled={isLoading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}

