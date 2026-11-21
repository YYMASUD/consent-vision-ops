"""Consent & policy validation service (spec §9, §18).

Recognition is disabled by default and requires every check to pass:
active enrollment, valid unexpired/unrevoked consent, camera and zone
authorization, quality approval, and liveness policy.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.common.utils import utcnow
from app.config.settings import get_settings


@dataclass
class PolicyDecision:
    """Outcome of a consent/policy gate evaluation."""

    allowed: bool
    reason: str
    checks: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason, "checks": self.checks}


class ConsentPolicyService:
    """Evaluates the full recognition-permission checklist (spec §9)."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def recognition_permitted(
        self,
        *,
        person_active: bool | None,
        active_enrollments: int,
        consents: list,
        camera_id: uuid.UUID | None,
        zone_id: uuid.UUID | None = None,
        quality_usable: bool | None = None,
        liveness_permits: bool | None = None,
        requester_authorized: bool = True,
    ) -> PolicyDecision:
        """All checks must pass; recognition stays blocked otherwise."""
        s = self.settings
        checks: dict[str, object] = {}

        if not s.recognition_enabled:
            return PolicyDecision(False, "recognition_disabled", {"recognition_enabled": False})

        checks["recognition_enabled"] = True
        checks["requester_authorized"] = requester_authorized
        if not requester_authorized:
            return PolicyDecision(False, "requester_not_authorized", checks)

        checks["person_active"] = person_active
        if person_active is not True:
            return PolicyDecision(False, "person_not_active", checks)

        checks["active_enrollments"] = active_enrollments
        if active_enrollments < 1:
            return PolicyDecision(False, "no_active_enrollment", checks)

        now = utcnow()
        valid = [
            c
            for c in consents
            if getattr(c, "revoked_at", None) is None
            and getattr(c, "valid_from", now) <= now
            and (getattr(c, "valid_until", None) is None or getattr(c, "valid_until") > now)
        ]
        checks["valid_consent"] = bool(valid)
        if not valid:
            return PolicyDecision(False, "no_valid_consent", checks)

        if s.consent_required_for_recognition:
            camera_ok = any(
                camera_id is None
                or not getattr(c, "allowed_camera_ids", None)
                or str(camera_id) in [str(x) for x in c.allowed_camera_ids]
                for c in valid
            )
            checks["camera_authorized"] = camera_ok
            if not camera_ok:
                return PolicyDecision(False, "camera_not_authorized", checks)

            zone_ok = any(
                zone_id is None
                or not getattr(c, "allowed_zone_ids", None)
                or str(zone_id) in [str(x) for x in c.allowed_zone_ids]
                for c in valid
            )
            checks["zone_authorized"] = zone_ok
            if not zone_ok:
                return PolicyDecision(False, "zone_not_authorized", checks)

        if quality_usable is not None:
            checks["quality_usable"] = quality_usable
            if not quality_usable:
                return PolicyDecision(False, "face_quality_insufficient", checks)

        if liveness_permits is not None:
            checks["liveness_permits"] = liveness_permits
            if not liveness_permits:
                return PolicyDecision(False, "liveness_blocked", checks)

        return PolicyDecision(True, "allowed", checks)

    def revoked_or_expired(self, consent) -> bool:
        """True when a consent record is revoked or expired (blocks matching)."""
        if consent is None:
            return True
        now = utcnow()
        if getattr(consent, "revoked_at", None) is not None:
            return True
        valid_until = getattr(consent, "valid_until", None)
        if valid_until is not None and valid_until <= now:
            return True
        return False
