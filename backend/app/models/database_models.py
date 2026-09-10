"""SQLAlchemy ORM models for all CloudIntelliGuard database tables."""
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, JSON, Enum as SAEnum, BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Roles & Users (system users, NOT cloud IAM users)
# ---------------------------------------------------------------------------

class Role(Base):
    """System roles: ADMIN or SECURITY_ANALYST."""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    permissions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    users: Mapped[List["User"]] = relationship("User", back_populates="role", lazy="selectin")


class User(Base):
    """System users (analysts and admins). NOT cloud IAM users."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    role: Mapped[Optional[Role]] = relationship("Role", back_populates="users", lazy="selectin")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")


# ---------------------------------------------------------------------------
# Datasets & Cloud Events
# ---------------------------------------------------------------------------

class Dataset(Base):
    """Uploaded cloud event dataset (CloudTrail-style CSV/JSON)."""
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # csv | json
    status: Mapped[str] = mapped_column(
        SAEnum("UPLOADED", "PROCESSING", "PROCESSED", "FAILED", name="dataset_status"),
        default="UPLOADED", nullable=False,
    )
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    processed_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_event_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_event_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dropped_event_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preprocessing_report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    cloud_events: Mapped[List["CloudEvent"]] = relationship(
        "CloudEvent", back_populates="dataset", cascade="all, delete-orphan"
    )
    graph_windows: Mapped[List["GraphWindow"]] = relationship(
        "GraphWindow", back_populates="dataset"
    )
    model_runs: Mapped[List["ModelRun"]] = relationship(
        "ModelRun", back_populates="dataset"
    )


class CloudEvent(Base):
    """A single processed cloud API event (CloudTrail-style)."""
    __tablename__ = "cloud_events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id"), nullable=False, index=True
    )
    event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    cloud_user_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    resource: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="cloud_events")

    __table_args__ = (
        Index("ix_cloud_events_dataset_ts", "dataset_id", "timestamp"),
        Index("ix_cloud_events_user_ts", "cloud_user_id", "timestamp"),
    )


# ---------------------------------------------------------------------------
# Graph Windows
# ---------------------------------------------------------------------------

class GraphWindow(Base):
    """Temporal graph snapshot for a time window."""
    __tablename__ = "graph_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id"), nullable=False, index=True
    )
    window_type: Mapped[str] = mapped_column(String(20), nullable=False)  # fixed | adaptive
    window_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    node_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    edge_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    graph_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    graph_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="graph_windows")
    anomalies: Mapped[List["Anomaly"]] = relationship(
        "Anomaly", back_populates="graph_window"
    )
    risk_scores: Mapped[List["RiskScore"]] = relationship(
        "RiskScore", back_populates="graph_window"
    )


# ---------------------------------------------------------------------------
# ML Model Runs
# ---------------------------------------------------------------------------

class ModelRun(Base):
    """Record of a model training or inference run."""
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # baseline | enhanced
    run_type: Mapped[str] = mapped_column(String(20), nullable=False)    # train | infer
    dataset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("datasets.id"), nullable=True
    )
    graph_window_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("graph_windows.id"), nullable=True
    )
    hyperparams: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="run_status"),
        default="PENDING", nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    model_checkpoint_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    dataset: Mapped[Optional[Dataset]] = relationship("Dataset", back_populates="model_runs")
    anomalies: Mapped[List["Anomaly"]] = relationship(
        "Anomaly", back_populates="model_run"
    )
    evaluation_results: Mapped[List["EvaluationResult"]] = relationship(
        "EvaluationResult", back_populates="model_run"
    )


# ---------------------------------------------------------------------------
# Anomaly Detection Results
# ---------------------------------------------------------------------------

class Anomaly(Base):
    """Detected anomaly for a cloud user within a graph window."""
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cloud_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    graph_window_id: Mapped[int] = mapped_column(
        ForeignKey("graph_windows.id"), nullable=False, index=True
    )
    model_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("model_runs.id"), nullable=True
    )
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_used: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    explanation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    graph_window: Mapped[GraphWindow] = relationship(
        "GraphWindow", back_populates="anomalies"
    )
    model_run: Mapped[Optional[ModelRun]] = relationship(
        "ModelRun", back_populates="anomalies"
    )


# ---------------------------------------------------------------------------
# Risk Scores
# ---------------------------------------------------------------------------

class RiskScore(Base):
    """Context-aware risk score (0–100) for a cloud user in a window."""
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cloud_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    graph_window_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("graph_windows.id"), nullable=True
    )
    anomaly_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("anomalies.id"), nullable=True
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        SAEnum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="risk_level_enum"),
        nullable=False,
    )
    factors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    graph_window: Mapped[Optional[GraphWindow]] = relationship(
        "GraphWindow", back_populates="risk_scores"
    )


# ---------------------------------------------------------------------------
# Coordinated Events
# ---------------------------------------------------------------------------

class CoordinatedEvent(Base):
    """Detected coordinated suspicious activity across multiple cloud users."""
    __tablename__ = "coordinated_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    coordination_score: Mapped[float] = mapped_column(Float, nullable=False)
    related_cloud_user_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    related_services: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    related_resources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    time_window_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    time_window_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    threshold_used: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="coordinated_event"
    )


# ---------------------------------------------------------------------------
# Incidents, Alerts, Recommendations
# ---------------------------------------------------------------------------

class Incident(Base):
    """Security incident created from detected anomalies."""
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(
        SAEnum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="incident_severity_enum"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        SAEnum("NEW", "INVESTIGATING", "MITIGATED", "RESOLVED", name="incident_status_enum"),
        default="NEW", nullable=False,
    )
    cloud_user_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affected_services: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    affected_resources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    graph_window_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("graph_windows.id"), nullable=True
    )
    anomaly_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("anomalies.id"), nullable=True
    )
    is_coordinated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coordinated_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("coordinated_events.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="incident", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="incident", cascade="all, delete-orphan"
    )
    coordinated_event: Mapped[Optional[CoordinatedEvent]] = relationship(
        "CoordinatedEvent", back_populates="incidents"
    )


class Alert(Base):
    """Alert generated for a security incident."""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id"), nullable=False, index=True
    )
    cloud_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    incident: Mapped[Incident] = relationship("Incident", back_populates="alerts")


class Recommendation(Base):
    """Preventive-response recommendation (simulation only, not real cloud action)."""
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_simulation_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    incident: Mapped[Incident] = relationship("Incident", back_populates="recommendations")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class EvaluationResult(Base):
    """ML model evaluation metrics for a model run."""
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_run_id: Mapped[int] = mapped_column(
        ForeignKey("model_runs.id"), nullable=False, index=True
    )
    experiment_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roc_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    false_positive_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    detection_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_runtime_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evaluated_on_ground_truth: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    model_run: Mapped[ModelRun] = relationship(
        "ModelRun", back_populates="evaluation_results"
    )


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """Audit trail. Passwords and secrets are NEVER stored here."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    resource: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    user: Mapped[Optional[User]] = relationship("User", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# Cloud IAM User Security Status & Automated Enforcements
# ---------------------------------------------------------------------------

class CloudUserEnforcement(Base):
    """Automated security policy enforcement state for a Cloud IAM identity."""
    __tablename__ = "cloud_user_enforcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cloud_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        SAEnum("ACTIVE", "RESTRICTED", "BLOCKED", name="user_enforcement_status"),
        default="ACTIVE", nullable=False, index=True,
    )
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        SAEnum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="enforcement_risk_level"),
        default="LOW", nullable=False,
    )
    restriction_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocking_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    restricted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    history: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

