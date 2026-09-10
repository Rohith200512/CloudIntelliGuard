const API_BASE = 'http://127.0.0.1:8001/api/v1';

export function getAuthToken() {
  return localStorage.getItem('cig_token');
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('cig_token', token);
  } else {
    localStorage.removeItem('cig_token');
  }
}

async function request(path, options = {}) {
  const token = getAuthToken();
  const headers = {
    ...(options.headers || {}),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If token invalid, clear it and notify context
    setAuthToken(null);
    window.dispatchEvent(new Event('cig_auth_expired'));
  }

  if (!response.ok) {
    let errDetail = 'Request failed';
    try {
      const errJson = await response.json();
      errDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errDetail = await response.text();
    }
    throw new Error(errDetail);
  }

  return response.json();
}

export const api = {
  // Auth
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await request('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });
    if (res.access_token) {
      setAuthToken(res.access_token);
    }
    return res;
  },

  logout() {
    setAuthToken(null);
  },

  async getMe() {
    return request('/auth/me');
  },

  // Dashboard & Metrics
  async getDashboardSummary() {
    return request('/evaluation/dashboard/summary');
  },

  async getSecurityReport() {
    return request('/reports/security');
  },

  // Datasets
  async listDatasets() {
    return request('/datasets');
  },

  async getDataset(id) {
    return request(`/datasets/${id}`);
  },

  async uploadDataset(file, name, description) {
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    if (description) formData.append('description', description);

    return request('/datasets/upload', {
      method: 'POST',
      body: formData,
    });
  },

  async processDataset(id, windowType = 'fixed', windowHours = 24) {
    return request(`/datasets/${id}/process`, {
      method: 'POST',
      body: JSON.stringify({ window_type: windowType, window_hours: windowHours }),
    });
  },

  // Graph
  async getGraphWindow(id, includeGraph = true) {
    return request(`/graph/${id}?include_graph=${includeGraph}`);
  },

  async getUserSubgraph(cloudUserId, datasetId) {
    return request(`/graph/user/${cloudUserId}?dataset_id=${datasetId}`);
  },

  // Anomalies & Models
  async trainModel(datasetId, modelType = 'baseline', hyperparams = {}) {
    return request('/detection/models/train', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, model_type: modelType, hyperparams }),
    });
  },

  async runInference(graphWindowId, modelType = 'baseline', threshold = 0.5, thresholdType = 'statistical') {
    return request('/detection/models/infer', {
      method: 'POST',
      body: JSON.stringify({
        graph_window_id: graphWindowId,
        model_type: modelType,
        threshold: threshold,
        threshold_type: thresholdType,
      }),
    });
  },

  async listAnomalies(params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/detection/anomalies${query ? `?${query}` : ''}`);
  },

  async getAnomaly(id) {
    return request(`/detection/anomalies/${id}`);
  },

  // Risk Scores
  async listRiskScores() {
    return request('/risk');
  },

  async getUserRiskHistory(cloudUserId) {
    return request(`/risk/user/${cloudUserId}/history`);
  },

  async computeRisk(anomalyId) {
    return request(`/risk/compute/${anomalyId}`, {
      method: 'POST',
    });
  },

  // Incidents & Alerts
  async listIncidents() {
    return request('/incidents');
  },

  async updateIncidentStatus(id, status, note = null) {
    return request(`/incidents/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, note }),
    });
  },

  async listAlerts(activeOnly = true) {
    return request(`/alerts?active_only=${activeOnly}`);
  },

  async acknowledgeAlert(id) {
    return request(`/alerts/${id}/acknowledge`, {
      method: 'PATCH',
    });
  },

  // Automated Response & Enforcements
  async listEnforcements() {
    return request('/response');
  },

  async getPolicySummary() {
    return request('/response/summary');
  },

  async overrideEnforcement(cloudUserId, action, reason) {
    return request('/response/override', {
      method: 'POST',
      body: JSON.stringify({ cloud_user_id: cloudUserId, action, reason }),
    });
  },

  // User Behavior Analytics (UBA)
  async listUBAUsers() {
    return request('/uba/users');
  },

  async getUBAProfile(cloudUserId) {
    return request(`/uba/profile/${encodeURIComponent(cloudUserId)}`);
  },

  // Attack Path Analysis
  async listAttackPaths(userId = null, resource = null) {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (resource) params.append('resource', resource);
    const query = params.toString();
    return request(`/attack-path${query ? `?${query}` : ''}`);
  },

  // What-If Risk Simulator
  async simulateRisk(payload) {
    return request('/risk-simulator/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // AI Copilot
  async queryCopilot(query, contextUserId = null, contextIncidentId = null) {
    return request('/copilot/query', {
      method: 'POST',
      body: JSON.stringify({
        query,
        context_user_id: contextUserId,
        context_incident_id: contextIncidentId,
      }),
    });
  },

  // Audit Logs
  async listAuditLogs(action = null, limit = 100) {
    const params = new URLSearchParams();
    if (action) params.append('action', action);
    if (limit) params.append('limit', limit);
    return request(`/audit?${params.toString()}`);
  },
};

