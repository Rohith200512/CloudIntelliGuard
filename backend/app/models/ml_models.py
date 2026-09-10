"""Pydantic schemas for ML pipeline inputs and outputs."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeFeatures(BaseModel):
    node_id: str
    node_type: str  # user | action | service | resource
    request_frequency: Optional[float] = None
    action_frequency: Optional[float] = None
    service_frequency: Optional[float] = None
    failed_ratio: Optional[float] = None
    affected_resources_count: Optional[int] = None
    recent_intensity: Optional[float] = None
    time_of_day_mean: Optional[float] = None
    day_of_week_entropy: Optional[float] = None
    first_time_service: Optional[bool] = None
    first_time_resource: Optional[bool] = None
    historical_deviation: Optional[float] = None


class EdgeFeatures(BaseModel):
    source: str
    target: str
    edge_type: str  # user_action | action_service | service_resource
    timestamp: Optional[datetime] = None
    weight: float = 1.0
    status: Optional[str] = None
    action: Optional[str] = None


class GraphSnapshot(BaseModel):
    window_id: int
    start_time: datetime
    end_time: datetime
    nodes: List[NodeFeatures]
    edges: List[EdgeFeatures]
    event_count: int


class AnomalyDetectionResult(BaseModel):
    cloud_user_id: str
    anomaly_score: float = Field(ge=0.0)
    is_anomaly: bool
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    threshold_used: float
    threshold_type: str
    embedding: Optional[List[float]] = None
    explanation: Optional[Dict[str, Any]] = None


class RiskComputationInput(BaseModel):
    cloud_user_id: str
    anomaly_score: float
    is_anomaly: bool
    event_count: int
    failed_request_count: int
    unique_services: List[str]
    unique_resources: List[str]
    unusual_services: List[str]
    sensitive_resources: List[str]
    historical_avg_requests: Optional[float] = None
    recent_intensity: Optional[float] = None
    is_coordinated: bool = False
    temporal_anomaly_score: Optional[float] = None


class WindowSelectionResult(BaseModel):
    window_type: str
    window_hours: float
    event_count: int
    selection_rationale: str
    processing_time_ms: Optional[float] = None


class EarlyWarningPrediction(BaseModel):
    cloud_user_id: str
    current_risk: float
    historical_trend: Optional[List[float]] = None
    predicted_next_risk: Optional[float] = None
    trend_direction: Optional[str] = None  # INCREASING | STABLE | DECREASING
    prediction_available: bool
    unavailability_reason: Optional[str] = None
