"""Pydantic v2 request and response schemas for all CloudIntelliGuard API endpoints."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: Optional[str] = None


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    role_name: str = "SECURITY_ANALYST"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    file_type: str
    status: str
    upload_time: datetime
    processed_time: Optional[datetime] = None
    raw_event_count: Optional[int] = None
    processed_event_count: Optional[int] = None
    dropped_event_count: Optional[int] = None
    preprocessing_report: Optional[Dict[str, Any]] = None
    is_demo: bool


class DatasetProcessRequest(BaseModel):
    window_type: str = Field(default="fixed", pattern="^(fixed|adaptive)$")
    window_hours: Optional[float] = None


# ---------------------------------------------------------------------------
# Cloud Events
# ---------------------------------------------------------------------------

class CloudEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dataset_id: int
    event_id: Optional[str] = None
    timestamp: datetime
    cloud_user_id: Optional[str] = None
    action: Optional[str] = None
    service: Optional[str] = None
    resource: Optional[str] = None
    source_ip: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Graph Windows
# ---------------------------------------------------------------------------

class GraphWindowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dataset_id: int
    window_type: str
    window_hours: Optional[float] = None
    start_time: datetime
    end_time: datetime
    event_count: int
    node_count: Optional[int] = None
    edge_count: Optional[int] = None
    created_at: datetime
    processing_time_ms: Optional[float] = None


class GraphWindowWithData(GraphWindowRead):
    graph_json: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Model Runs
# ---------------------------------------------------------------------------

class ModelTrainRequest(BaseModel):
    model_type: str = Field(pattern="^(baseline|enhanced)$")
    dataset_id: int
    graph_window_id: Optional[int] = None
    hyperparams: Optional[Dict[str, Any]] = None


class ModelInferRequest(BaseModel):
    model_type: str = Field(pattern="^(baseline|enhanced)$")
    graph_window_id: int
    threshold: Optional[float] = None
    threshold_type: str = Field(default="statistical", pattern="^(statistical|adaptive|fixed)$")


class ModelRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    model_type: str
    run_type: str
    dataset_id: Optional[int] = None
    graph_window_id: Optional[int] = None
    hyperparams: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    model_checkpoint_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------

class AnomalyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    cloud_user_id: str
    graph_window_id: int
    model_run_id: Optional[int] = None
    anomaly_score: float
    is_anomaly: bool
    confidence: Optional[float] = None
    threshold_used: Optional[float] = None
    threshold_type: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Risk Scores
# ---------------------------------------------------------------------------

class RiskFactor(BaseModel):
    factor: str
    contribution: float
    description: Optional[str] = None


class RiskScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cloud_user_id: str
    graph_window_id: Optional[int] = None
    anomaly_id: Optional[int] = None
    risk_score: float
    risk_level: str
    factors: Optional[List[RiskFactor]] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

class IncidentCreate(BaseModel):
    title: str
    severity: str = Field(pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    cloud_user_ids: Optional[List[str]] = None
    graph_window_id: Optional[int] = None
    anomaly_id: Optional[int] = None
    explanation: Optional[str] = None


class IncidentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(NEW|INVESTIGATING|MITIGATED|RESOLVED)$")
    note: Optional[str] = None


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    severity: str
    action: str
    rationale: str
    priority: int
    is_simulation_only: bool
    created_at: datetime


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    severity: str
    status: str
    cloud_user_ids: Optional[List[str]] = None
    risk_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    explanation: Optional[str] = None
    affected_services: Optional[List[str]] = None
    affected_resources: Optional[List[str]] = None
    is_coordinated: bool
    created_at: datetime
    updated_at: datetime
    recommendations: List[RecommendationRead] = []


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    cloud_user_id: Optional[str] = None
    alert_type: str
    message: str
    severity: str
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Coordinated Events
# ---------------------------------------------------------------------------

class CoordinatedEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    coordination_score: float
    related_cloud_user_ids: List[str]
    related_services: Optional[List[str]] = None
    related_resources: Optional[List[str]] = None
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    evidence: Optional[Dict[str, Any]] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class EvaluationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    model_run_id: int
    experiment_name: Optional[str] = None
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    roc_auc: Optional[float] = None
    false_positive_rate: Optional[float] = None
    detection_latency_ms: Optional[float] = None
    total_runtime_s: Optional[float] = None
    evaluated_on_ground_truth: bool
    notes: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    total_datasets: int
    total_events: int
    total_anomalies: int
    total_incidents: int
    open_incidents: int
    critical_incidents: int
    total_alerts: int
    unacknowledged_alerts: int
    last_model_run: Optional[datetime] = None
    demo_mode: bool


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str
    detail: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Cloud User Enforcements & Automated Response
# ---------------------------------------------------------------------------

class EnforcementRead(BaseModel):
    id: int
    cloud_user_id: str
    status: str
    risk_score: float
    risk_level: str
    restriction_reason: Optional[str] = None
    blocking_reason: Optional[str] = None
    session_revoked: bool = False
    restricted_at: Optional[datetime] = None
    blocked_at: Optional[datetime] = None
    last_evaluated_at: datetime
    history: Optional[List[Dict[str, Any]]] = None

    model_config = {"from_attributes": True}


class EnforcementOverrideRequest(BaseModel):
    cloud_user_id: str
    action: str  # "RESTORE" | "RESTRICT" | "BLOCK"
    reason: Optional[str] = "Manual security analyst action"


class AutomatedPolicySummary(BaseModel):
    total_monitored_users: int
    active_users: int
    restricted_users: int
    blocked_users: int
    policies: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# User Behavior Analytics (UBA)
# ---------------------------------------------------------------------------

class UBAProfile(BaseModel):
    cloud_user_id: str
    current_status: str
    current_risk_score: float
    current_risk_level: str
    deviation_score: float
    baseline: Dict[str, Any]
    current_behavior: Dict[str, Any]
    suspicious_indicators: List[Dict[str, Any]]
    recent_events: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Attack Path Analysis
# ---------------------------------------------------------------------------

class AttackPathStep(BaseModel):
    step_number: int
    source_entity: str
    source_type: str
    target_entity: str
    target_type: str
    action: str
    timestamp: Optional[str] = None
    status: Optional[str] = None
    is_suspicious: bool = False
    details: Optional[str] = None


class AttackPath(BaseModel):
    path_id: str
    cloud_user_id: str
    target_resource: Optional[str] = None
    path_risk_score: float
    severity: str
    steps: List[AttackPathStep]
    summary: str


# ---------------------------------------------------------------------------
# What-If Risk Simulator
# ---------------------------------------------------------------------------

class SimulateRiskRequest(BaseModel):
    cloud_user_id: str
    unusual_login: bool = False
    new_ip_location: bool = False
    privilege_escalation: bool = False
    abnormal_api_activity: bool = False
    sensitive_resource_access: bool = False
    multiple_failed_logins: bool = False
    coordinated_behavior: bool = False
    temporal_anomaly: bool = False


class SimulateRiskResponse(BaseModel):
    cloud_user_id: str
    current_risk_score: float
    current_risk_level: str
    simulated_risk_score: float
    simulated_risk_level: str
    delta: float
    risk_level_changed: bool
    top_contributor: str
    explanation: str
    factor_contributions: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# AI Copilot
# ---------------------------------------------------------------------------

class CopilotQueryRequest(BaseModel):
    query: str
    context_user_id: Optional[str] = None
    context_incident_id: Optional[int] = None


class CopilotQueryResponse(BaseModel):
    query: str
    answer: str
    intent: str
    related_entities: List[Dict[str, Any]] = []
    suggested_actions: List[str] = []
    data_sources_used: List[str] = []


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class AuditLogRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    resource: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}

