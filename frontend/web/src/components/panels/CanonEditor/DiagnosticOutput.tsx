import "./DiagnosticOutput.css";
import type { DiagnosticsReport } from "../../../types/models";

interface DiagnosticOutputProps {
  diagnostics: DiagnosticsReport;
}

export default function DiagnosticOutput({ diagnostics }: DiagnosticOutputProps) {
  return (
    <div className="diagnostic-output">
      {diagnostics.errors.length > 0 && (
        <div className="diagnostic-block diagnostic-errors">
          <h3>Blocking Errors</h3>
          {diagnostics.errors.map((error, idx) => (
            <div key={idx} className="diagnostic-item">
              <span className="diagnostic-path">
                {error.schema_type}
                {error.schema_id && `/${error.schema_id}`}
                {error.field_path && `.${error.field_path}`}
              </span>
              <span className="diagnostic-message">{error.message}</span>
            </div>
          ))}
        </div>
      )}
      {diagnostics.warnings.length > 0 && (
        <div className="diagnostic-block diagnostic-warnings">
          <h3>Warnings</h3>
          {diagnostics.warnings.map((warning, idx) => (
            <div key={idx} className="diagnostic-item">
              <span className="diagnostic-message">{warning}</span>
            </div>
          ))}
        </div>
      )}
      {diagnostics.errors.length === 0 && diagnostics.warnings.length === 0 && (
        <div className="diagnostic-block diagnostic-ok">
          <h3>✓ No issues found</h3>
        </div>
      )}
    </div>
  );
}

