"""SQLAlchemy model registry (spec §15)."""
from app.models.base import Base, EmbeddingVector, EMBED_DIM, JSONType, UUIDPk
from app.models.events import (
    AccessVerificationEvent,
    FaceDetection,
    LivenessEvent,
    RecognitionEvent,
)
from app.models.governance import Alert, AlertRule, AuditLog, RetainedMedia, ReviewAction, ReviewCase
from app.models.ops import (
    CameraHealthEvent,
    CameraSource,
    CameraZone,
    OccupancySnapshot,
    VisitSession,
)
from app.models.persons import ConsentRecord, FaceEnrollment, PersonProfile

__all__ = [
    "Base",
    "UUIDPk",
    "JSONType",
    "EmbeddingVector",
    "EMBED_DIM",
    "PersonProfile",
    "ConsentRecord",
    "FaceEnrollment",
    "CameraSource",
    "CameraZone",
    "VisitSession",
    "OccupancySnapshot",
    "CameraHealthEvent",
    "FaceDetection",
    "RecognitionEvent",
    "AccessVerificationEvent",
    "LivenessEvent",
    "AlertRule",
    "Alert",
    "ReviewCase",
    "ReviewAction",
    "RetainedMedia",
    "AuditLog",
]


def register_models() -> None:
    """Ensure every model module is imported and mappers are configured."""
    # Imports at module top already register all mappers; kept for explicit call sites.
    return None