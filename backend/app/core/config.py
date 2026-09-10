"""Application configuration loaded from environment variables / .env file."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    # App
    app_name: str = "CloudIntelliGuard"
    debug: bool = False
    demo_mode: bool = False
    max_upload_size_mb: int = 1000  # Default 1000 MB (1 GB)

    # Database
    database_url: str = "postgresql+asyncpg://cig_user:cig_password@localhost:5432/cig_db"

    # JWT
    secret_key: str = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_KEY"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Admin seed user
    admin_username: str = "admin"
    admin_email: str = "admin@example.com"
    admin_password: str = "AdminPassword123!"

    # Time Window
    default_window_type: str = "fixed"
    default_window_hours: int = 24
    adaptive_low_threshold: int = 100
    adaptive_high_threshold: int = 1000

    # ML Hyperparameters
    gnn_hidden_dim: int = 64
    gnn_output_dim: int = 32
    gnn_num_layers: int = 2
    gnn_dropout: float = 0.3
    anomaly_threshold: float = 0.5

    # Paths
    data_dir: str = "data"
    model_dir: str = "models/trained"
    checkpoint_dir: str = "models/checkpoints"

    # Logging
    log_level: str = "INFO"

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic migrations."""
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


settings = Settings()
