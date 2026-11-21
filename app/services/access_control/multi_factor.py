"""Multi-factor verification (spec §9).

Correlates face evidence with badge/QR/NFC/PIN/turnstile/door/manual signals.
Outcomes: verified_by_multiple_factors | face_only_match | credential_only |
factor_conflict | credential_denied | manual_review_required.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.common.enums import (
    ACCESS_DENIED,
    CREDENTIAL_TYPES,
    MFA_CONFLICT,
    MFA_CREDENTIAL_DENIED,
    MFA_CREDENTIAL_ONLY,
    MFA_FACE_ONLY,
    MFA_MANUAL_REVIEW,
    MFA_VERIFIED_MULTI,
)
from app.common.utils import utcnow
from app.config.settings import get_settings


@dataclass
class CredentialSignal:
    """One external access-control signal correlated with a face candidate."""

    credential_type: str
    subject_reference: str | None = None
    decision: str = "granted"  # granted | denied
    timestamp: datetime = field(default_factory=utcnow)
    resolved_person_id: uuid.UUID | None = None  # caller-resolved mapping


@dataclass
class MFAOutcome:
    outcome: str
    face_person_id: uuid.UUID | None = None
    credential_person_id: uuid.UUID | None = None
    matched_credentials: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "face_person_id": str(self.face_person_id) if self.face_person_id else None,
            "credential_person_id": str(self.credential_person_id) if self.credential_person_id else None,
            "matched_credentials": self.matched_credentials,
            "reasons": self.reasons,
        }


class MultiFactorVerificationService:
    """Correlates identity evidence across face + credential signals (spec §9)."""

    def __init__(self) -> None:
        s = get_settings()
        self.correlation_window_s = s.mfa_correlation_window_s
        self.allow_credential_only = s.mfa_allow_credential_only

    def verify(
        self,
        face_person_id: uuid.UUID | None,
        signals: list[CredentialSignal],
        *,
        now: datetime | None = None,
    ) -> MFAOutcome:
        now = now or utcnow()
        cutoff = now - timedelta(seconds=self.correlation_window_s)
        recent = [s for s in signals if s.timestamp >= cutoff and s.credential_type in CREDENTIAL_TYPES]

        if not recent:
            if face_person_id is None:
                return MFAOutcome(MFA_MANUAL_REVIEW, reasons=["no_face_no_credentials"])
            return MFAOutcome(MFA_FACE_ONLY, face_person_id=face_person_id, reasons=["face_only"])

        denied = [s for s in recent if s.decision == ACCESS_DENIED]
        if denied:
            return MFAOutcome(
                MFA_CREDENTIAL_DENIED,
                face_person_id=face_person_id,
                matched_credentials=[s.credential_type for s in denied],
                reasons=["credential_denied_by_access_control"],
            )

        resolving = [s for s in recent if s.resolved_person_id is not None]
        conflicting = [s for s in resolving if face_person_id and s.resolved_person_id != face_person_id]
        if conflicting:
            return MFAOutcome(
                MFA_CONFLICT,
                face_person_id=face_person_id,
                credential_person_id=conflicting[0].resolved_person_id,
                matched_credentials=[s.credential_type for s in resolving],
                reasons=["credential_identity_conflicts_with_face_candidate"],
            )

        agreeing = [s for s in resolving if face_person_id and s.resolved_person_id == face_person_id]
        if agreeing and face_person_id:
            return MFAOutcome(
                MFA_VERIFIED_MULTI,
                face_person_id=face_person_id,
                credential_person_id=face_person_id,
                matched_credentials=sorted({s.credential_type for s in agreeing}),
                reasons=["face_and_credentials_agree"],
            )

        # credential present but resolves to a person; no face candidate confirmed
        if resolving and face_person_id is None:
            return MFAOutcome(
                MFA_CREDENTIAL_ONLY,
                credential_person_id=resolving[0].resolved_person_id,
                matched_credentials=[s.credential_type for s in resolving],
                reasons=["credential_only_no_face_match"],
            )

        unmatched = [s for s in recent if s.resolved_person_id is None]
        return MFAOutcome(
            MFA_MANUAL_REVIEW,
            face_person_id=face_person_id,
            matched_credentials=[s.credential_type for s in unmatched],
            reasons=["credentials_unresolvable_to_enrolled_person"],
        )
