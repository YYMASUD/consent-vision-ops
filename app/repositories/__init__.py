"""Async data-access repositories (spec §15)."""
from app.repositories.base import BaseRepository, as_uuid
from app.repositories.events import (
    AccessEventRepository,
    DetectionRepository,
    LivenessRepository,
    RecognitionRepository,
)
from app.repositories.governance import (
    AlertRepository,
    AlertRuleRepository,
    AuditRepository,
    RetentionRepository,
    ReviewRepository,
)
from app.repositories.ops import (
    CameraRepository,
    HealthRepository,
    OccupancyRepository,
    SessionRepository,
    ZoneRepository,
)
from app.repositories.persons import ConsentRepository, EnrollmentRepository, PersonRepository

__all__ = [
    "BaseRepository",
    "as_uuid",
    "PersonRepository",
    "ConsentRepository",
    "EnrollmentRepository",
    "CameraRepository",
    "ZoneRepository",
    "SessionRepository",
    "OccupancyRepository",
    "HealthRepository",
    "DetectionRepository",
    "RecognitionRepository",
    "AccessEventRepository",
    "LivenessRepository",
    "AlertRuleRepository",
    "AlertRepository",
    "ReviewRepository",
    "RetentionRepository",
    "AuditRepository",
]
