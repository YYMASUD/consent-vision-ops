"""Application configuration via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central typed configuration. Loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "consent-vision-ops"
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"

    # --- Database -----------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./consent_vision_ops.db"
    db_echo: bool = False

    # --- Redis / queues ------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    queue_backend: Literal["asyncio", "redis"] = "asyncio"
    worker_concurrency: int = 4

    # --- Object storage ------------------------------------------------------
    object_storage_endpoint: str | None = None
    object_storage_bucket: str = "cvo-media"
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None

    # --- Security ------------------------------------------------------------
    jwt_secret: str = Field(default="dev-secret-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    api_key_header: str = "X-API-Key"
    static_api_key: str | None = None

    # --- Recognition / consent ------------------------------------------------
    recognition_enabled: bool = False  # OFF by default per spec
    recognition_match_threshold: float = 0.62
    recognition_uncertain_band: float = 0.08
    multiframe_confirm_count: int = 3
    multiframe_confirm_window_s: float = 6.0
    consent_required_for_recognition: bool = True

    # --- Face quality ----------------------------------------------------------
    face_min_confidence: float = 0.70
    face_min_width_px: int = 80
    face_blur_laplacian_threshold: float = 60.0
    face_max_yaw_deg: float = 25.0
    face_max_pitch_deg: float = 20.0
    face_max_roll_deg: float = 25.0

    # --- Liveness ------------------------------------------------------------
    liveness_required: bool = False
    liveness_model_path: str | None = None

    # --- Sessions --------------------------------------------------------------
    session_gap_minutes: int = 3
    session_absence_timeout_s: float = 45.0

    # --- Zones / occupancy -------------------------------------------------------
    default_zone_max_occupancy: int = 50
    occupancy_snapshot_interval_s: float = 5.0

    # --- Camera health ---------------------------------------------------------
    camera_offline_after_s: float = 10.0
    frozen_frame_threshold: float = 0.999
    black_screen_threshold: float = 0.01
    white_screen_threshold: float = 0.99
    lens_obstruction_threshold: float = 0.995
    low_fps_threshold: float = 5.0

    # --- Retention -------------------------------------------------------------
    retention_batch_size: int = 500
    anonymous_retention_hours: float = 72.0
    biometric_retention_days: int = 30

    # --- Alerts ------------------------------------------------------------------
    alert_dedup_window_s: int = 300
    alert_suppression_default_s: int = 600

    # --- Inference -----------------------------------------------------------------
    device: Literal["auto", "cpu", "cuda"] = "auto"
    model_dir: str = "./models"
    frame_stride: int = 2
    max_queue_size: int = 64
    batch_size: int = 8


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()

