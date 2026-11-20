"""Observability: metrics, structured logging, model registry (spec §19)."""
from app.observability.logging import configure_logging, get_logger
from app.observability.metrics import render_metrics
from app.observability.registry import ModelVersion, registry

__all__ = ["configure_logging", "get_logger", "render_metrics", "registry", "ModelVersion"]
