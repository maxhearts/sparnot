import { useState, useEffect } from "react";
import "./DiffViewer.css";
import { diffApi } from "../../../services/api";
import type { CompilationDiff } from "../../../types/models";

interface DiffViewerProps {
  project: string | null;
}

export default function DiffViewer({ project }: DiffViewerProps) {
  const [diff, setDiff] = useState<CompilationDiff | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (project) {
      loadDiff();
    } else {
      // Reset state when project is cleared
      setDiff(null);
    }
  }, [project]);

  // Listen for compile success events to auto-refresh
  useEffect(() => {
    if (!project) return;
    
    const handleCompileSuccess = (event: CustomEvent) => {
      if (event.detail.project === project) {
        // Small delay to ensure bundle is saved
        setTimeout(() => {
          loadDiff();
        }, 500);
      }
    };
    
    window.addEventListener('compile-success', handleCompileSuccess as EventListener);
    return () => {
      window.removeEventListener('compile-success', handleCompileSuccess as EventListener);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  const loadDiff = async () => {
    if (!project) return;
    try {
      setIsLoading(true);
      const result = await diffApi.getCurrentVsLatest(project);
      setDiff(result);
    } catch (error) {
      console.error("Failed to load diff:", error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!project) {
    return (
      <div className="diff-viewer">
        <div className="diff-placeholder">Select a project to view diffs</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="diff-viewer">
        <div className="diff-placeholder">Loading diff...</div>
      </div>
    );
  }

  if (!diff) {
    return (
      <div className="diff-viewer">
        <div className="diff-placeholder">No diff available</div>
      </div>
    );
  }

  if (diff.metadata.identical) {
    return (
      <div className="diff-viewer">
        <div className="diff-header">
          <h3>Compilation Diff</h3>
          <button className="refresh-btn" onClick={loadDiff}>
            Refresh
          </button>
        </div>
        <div className="diff-content">
          <div className="diff-summary">Bundles are identical (no changes)</div>
        </div>
      </div>
    );
  }

  return (
    <div className="diff-viewer">
      <div className="diff-header">
        <h3>Compilation Diff</h3>
        <button className="refresh-btn" onClick={loadDiff}>
          Refresh
        </button>
      </div>
      <div className="diff-content">
        <div className="diff-section">
          <h4>Schema Changes</h4>
          {diff.schema_diffs.narrative_intent.length > 0 && (
            <div className="diff-group">
              <strong>narrative_intent:</strong>
              {diff.schema_diffs.narrative_intent.map((change, idx) => (
                <div key={idx} className="diff-item">
                  <span className={`change-type change-${change.change_type}`}>
                    {change.change_type}
                  </span>
                  <span className="change-path">{change.path}</span>
                </div>
              ))}
            </div>
          )}
          {Object.keys(diff.schema_diffs.characters).length > 0 && (
            <div className="diff-group">
              <strong>characters:</strong>
              {Object.entries(diff.schema_diffs.characters).map(([charId, changes]) => (
                <div key={charId}>
                  <strong>[{charId}]:</strong>
                  {changes.map((change, idx) => (
                    <div key={idx} className="diff-item">
                      <span className={`change-type change-${change.change_type}`}>
                        {change.change_type}
                      </span>
                      <span className="change-path">{change.path}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
          {diff.schema_diffs.arc.length > 0 && (
            <div className="diff-group">
              <strong>arc:</strong>
              {diff.schema_diffs.arc.map((change, idx) => (
                <div key={idx} className="diff-item">
                  <span className={`change-type change-${change.change_type}`}>
                    {change.change_type}
                  </span>
                  <span className="change-path">{change.path}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="diff-section">
          <h4>IR Changes</h4>
          {diff.ir_diffs.narrative_ir.length > 0 && (
            <div className="diff-group">
              <strong>narrative_ir:</strong>
              {diff.ir_diffs.narrative_ir.map((change, idx) => (
                <div key={idx} className="diff-item">
                  <span className={`change-type change-${change.change_type}`}>
                    {change.change_type}
                  </span>
                  <span className="change-path">{change.path}</span>
                </div>
              ))}
            </div>
          )}
          {Object.keys(diff.ir_diffs.character_irs).length > 0 && (
            <div className="diff-group">
              <strong>character_irs:</strong>
              {Object.entries(diff.ir_diffs.character_irs).map(([charId, changes]) => (
                <div key={charId}>
                  <strong>[{charId}]:</strong>
                  {changes.map((change, idx) => (
                    <div key={idx} className="diff-item">
                      <span className={`change-type change-${change.change_type}`}>
                        {change.change_type}
                      </span>
                      <span className="change-path">{change.path}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
          {diff.ir_diffs.arc_ir.length > 0 && (
            <div className="diff-group">
              <strong>arc_ir:</strong>
              {diff.ir_diffs.arc_ir.map((change, idx) => (
                <div key={idx} className="diff-item">
                  <span className={`change-type change-${change.change_type}`}>
                    {change.change_type}
                  </span>
                  <span className="change-path">{change.path}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="diff-section">
          <h4>Propagation</h4>
          {diff.propagation && diff.propagation.length > 0 ? (
            diff.propagation.map((entry, idx) => (
              <div key={idx} className="propagation-item">
                <div className="propagation-schema">
                  {entry.schema_path || entry.schema_change?.path || "Unknown"}
                </div>
                <div className="propagation-arrow">→</div>
                <div className="propagation-ir">
                  {(entry.affected_ir_paths || []).length > 0
                    ? entry.affected_ir_paths.join(", ")
                    : "No IR changes"}
                </div>
              </div>
            ))
          ) : (
            <div className="diff-summary">No propagation data available</div>
          )}
        </div>
      </div>
    </div>
  );
}

