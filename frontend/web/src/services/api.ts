/**
 * API service for communicating with FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = response.statusText;
    try {
      const error = await response.json();
      errorMessage = error.detail || error.message || response.statusText;
    } catch {
      // If JSON parsing fails, use status text
      errorMessage = response.statusText;
    }
    throw new Error(errorMessage || `HTTP ${response.status}`);
  }

  return response.json();
}

// Projects API
export const projectsApi = {
  list: () => apiRequest<string[]>("/api/projects"),
  create: (name: string) => apiRequest<{ name: string; path: string }>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  }),
  getInfo: (project: string) => apiRequest(`/api/projects/${project}/info`),
  getStatus: (project: string) => apiRequest<import("../types/models").CompilationStatus>(`/api/projects/${project}/status`),
  getHistory: (project: string) => apiRequest<import("../types/models").CompilationHistoryEntry[]>(`/api/projects/${project}/history`),
};

// Schemas API
export const schemasApi = {
  getAll: (project: string) => apiRequest<import("../types/models").AllSchemas>(`/api/projects/${project}/schemas`),
  get: (project: string, schemaType: string, schemaId?: string) => {
    const endpoint = schemaId
      ? `/api/projects/${project}/schemas/${schemaType}?schema_id=${schemaId}`
      : `/api/projects/${project}/schemas/${schemaType}`;
    return apiRequest(endpoint);
  },
  save: (project: string, schemaType: string, data: any, schemaId?: string) => {
    const endpoint = schemaId
      ? `/api/projects/${project}/schemas/${schemaType}?schema_id=${schemaId}`
      : `/api/projects/${project}/schemas/${schemaType}`;
    return apiRequest(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
  create: (project: string, schemaType: string, schemaId?: string) => {
    const endpoint = schemaId
      ? `/api/projects/${project}/schemas/${schemaType}?schema_id=${schemaId}`
      : `/api/projects/${project}/schemas/${schemaType}`;
    return apiRequest(endpoint, {
      method: "POST",
    });
  },
  getTemplate: (project: string, schemaType: string, schemaId?: string) => {
    const endpoint = schemaId
      ? `/api/projects/${project}/schemas/${schemaType}/template?schema_id=${schemaId}`
      : `/api/projects/${project}/schemas/${schemaType}/template`;
    return apiRequest(endpoint);
  },
};

// Compile API
export const compileApi = {
  compile: (project: string) => apiRequest<{ status: string; bundle: any; timestamp: string }>(`/api/projects/${project}/compile`, {
    method: "POST",
  }),
  getBundle: (project: string) => apiRequest<import("../types/models").CompiledBundle>(`/api/projects/${project}/bundle`),
  getHistoricalBundle: (project: string, timestamp: string) =>
    apiRequest<import("../types/models").CompiledBundle>(`/api/projects/${project}/bundle/history/${timestamp}`),
  runDiagnostics: (project: string) =>
    apiRequest<import("../types/models").DiagnosticsReport>(`/api/projects/${project}/diagnostics`, {
      method: "POST",
    }),
  getDiagnostics: (project: string) =>
    apiRequest<import("../types/models").DiagnosticsReport>(`/api/projects/${project}/diagnostics`),
};

// Diff API
export const diffApi = {
  getCurrentVsLatest: (project: string) =>
    apiRequest<import("../types/models").CompilationDiff>(`/api/projects/${project}/diff`),
  getBetweenBundles: (project: string, oldTimestamp: string, newTimestamp: string) =>
    apiRequest<import("../types/models").CompilationDiff>(`/api/projects/${project}/diff/${oldTimestamp}/${newTimestamp}`),
};

// Scenes API
export const scenesApi = {
  list: (project: string) => apiRequest<import("../types/models").SceneInfo[]>(`/api/projects/${project}/scenes`),
  get: (project: string, sceneId: string) =>
    apiRequest<import("../types/models").GeneratedScene>(`/api/projects/${project}/scenes/${sceneId}`),
  generate: (project: string, sceneId?: string) =>
    apiRequest<{ status: string; scene: any; filename: string; path: string }>(`/api/projects/${project}/scenes/generate`, {
      method: "POST",
      body: JSON.stringify({ scene_id: sceneId }),
    }),
  getForPlayback: (project: string, sceneId: string) =>
    apiRequest<import("../types/models").GeneratedScene>(`/api/projects/${project}/scenes/${sceneId}/play`),
};

// Locks API
export const locksApi = {
  listAll: (project: string) => apiRequest<import("../types/models").Lock[]>(`/api/projects/${project}/locks`),
  getSceneLocks: (project: string, sceneId: string) =>
    apiRequest<import("../types/models").SceneLocks>(`/api/projects/${project}/locks/${sceneId}`),
  lockLine: (project: string, sceneId: string, nodeId: string, lineNumber: number, notes?: string) =>
    apiRequest<{ status: string; lock_id: string }>(`/api/projects/${project}/locks/${sceneId}/line`, {
      method: "POST",
      body: JSON.stringify({ node_id: nodeId, line_number: lineNumber, notes }),
    }),
  lockNode: (project: string, sceneId: string, nodeId: string, notes?: string) =>
    apiRequest<{ status: string; lock_id: string }>(`/api/projects/${project}/locks/${sceneId}/node`, {
      method: "POST",
      body: JSON.stringify({ node_id: nodeId, notes }),
    }),
  lockBranch: (
    project: string,
    sceneId: string,
    entryNode: string,
    choiceIds: string[],
    requiredNodes?: string[],
    summary?: string,
    notes?: string
  ) =>
    apiRequest<{ status: string; lock_id: string }>(`/api/projects/${project}/locks/${sceneId}/branch`, {
      method: "POST",
      body: JSON.stringify({
        entry_node: entryNode,
        choice_ids: choiceIds,
        required_nodes: requiredNodes,
        summary,
        notes,
      }),
    }),
  removeLock: (project: string, sceneId: string, lockId: string) =>
    apiRequest<{ status: string; lock_id: string }>(`/api/projects/${project}/locks/${sceneId}/${lockId}`, {
      method: "DELETE",
    }),
};

// Assistant API
export const assistantApi = {
  init: (project: string) =>
    apiRequest<{
      status: string;
      opening_message: string;
      diagnostics: any;
    }>(`/api/projects/${project}/assistant/init`, {
      method: "POST",
    }),
  sendMessage: (project: string, message: string) =>
    apiRequest<import("../types/models").AssistantResponse>(`/api/projects/${project}/assistant/message`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getWorkspaceStatus: (project: string) =>
    apiRequest<import("../types/models").WorkspaceStatus>(`/api/projects/${project}/assistant/workspace`),
  commit: (project: string) =>
    apiRequest<{ status: string }>(`/api/projects/${project}/assistant/commit`, {
      method: "POST",
    }),
  discard: (project: string) =>
    apiRequest<{ status: string }>(`/api/projects/${project}/assistant/discard`, {
      method: "POST",
    }),
};

