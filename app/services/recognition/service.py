"""Recognition pipeline orchestration (spec §9).

Gate order: quality -> liveness -> consent/policy -> embedding -> gallery match ->
multi-frame confirmation -> multi-factor correlation -> final decision.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.common.enums import (
    REC_BLOCKED_POLICY,
    REC_BLOCKED_QUALITY,
    REC_CONFIRMED,
    REC_FACE_QUALITY,
    REC_MFA_CONFLICT,
    REC_NO_MATCH,
    REC_SPOOF_SUSPECTED,
    REC_UNCERTAIN,
    REC_UNKNOWN,
    SPOOF_ATTACK,
)
from app.common.utils import utcnow
from app.config.settings import get_settings
from app.observability.metrics import recognition_total
from app.services.access_control.consent_policy import ConsentPolicyService
from app.services.liveness.service import LivenessDecision, LivenessService
from app.services.recognition.embeddings import EmbeddingService
from app.services.recognition.multi_frame import ConfirmationOutcome, MultiFrameConfirmator


@dataclass
class RecognitionContext:
    """Everything the pipeline needs for one face on one frame."""

    camera_id: uuid.UUID
    track_key: str  # scoped per camera (spec §6)
    track_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    quality: dict | None = None
    crop: Any = None
    signals: list = field(default_factory=list)
    now: datetime | None = None


@dataclass
class RecognitionResult:
    """Decision + audit fields persisted as a recognition_event (spec §15)."""

    decision: str
    matched_person_id: uuid.UUID | None = None
    similarity: float | None = None
    policy_status: str = "allowed"
    liveness_status: str | None = None
    mfa_outcome: str | None = None
    review_status: str = "none"
    reasons: list[str] = field(default_factory=list)
    model_version: str = "hashing-v1"

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "matched_person_id": str(self.matched_person_id) if self.matched_person_id else None,
            "similarity": self.similarity,
            "policy_status": self.policy_status,
            "liveness_status": self.liveness_status,
            "mfa_outcome": self.mfa_outcome,
            "review_status": self.review_status,
            "reasons": self.reasons,
            "model_version": self.model_version,
        }


def _blocked(
    decision: str, policy_status: str, reasons: list[str], model_version: str, liveness: LivenessDecision | None = None
) -> RecognitionResult:
    """Build a blocked/terminal result and count it in metrics."""
    result = RecognitionResult(
        decision=decision,
        policy_status=policy_status,
        liveness_status=liveness.decision if liveness else None,
        reasons=reasons,
        model_version=model_version,
    )
    recognition_total.labels(decision=result.decision).inc()
    return result


class RecognitionPipeline:
    """Stateless-per-call orchestrator over the recognition gates."""

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        liveness_service: LivenessService | None = None,
        policy_service: ConsentPolicyService | None = None,
        confirmator: MultiFrameConfirmator | None = None,
        mfa_service=None,
        gallery_search=None,
        person_lookup=None,
        review_opener=None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_service = embedding_service or EmbeddingService()
        self.liveness_service = liveness_service or LivenessService()
        self.policy_service = policy_service or ConsentPolicyService()
        self.confirmator = confirmator or MultiFrameConfirmator()
        self.mfa_service = mfa_service
        self.gallery_search = gallery_search  # async (embedding) -> [(enrollment, score)]
        self.person_lookup = person_lookup  # async (enrollment) -> (person, consents, count)
        self.review_opener = review_opener  # async (result, ctx) -> review case

    async def process(self, ctx: RecognitionContext) -> RecognitionResult:
        """Run one face through the full recognition gate chain."""
        now = ctx.now or utcnow()
        model_version = self.embedding_service.model_version

        # 1. quality gate
        quality = ctx.quality or {}
        if not quality.get("usable", False):
            return _blocked(
                REC_FACE_QUALITY,
                "blocked_quality",
                list(quality.get("rejection_reasons", ["quality_not_evaluated"])),
                model_version,
            )

        # 2. liveness gate
        liveness: LivenessDecision = self.liveness_service.check(
            ctx.crop, track_key=ctx.track_key, now=now
        )
        if liveness.decision == SPOOF_ATTACK:
            result = _blocked(
                REC_SPOOF_SUSPECTED, "blocked_liveness", list(liveness.reasons), model_version, liveness
            )
            if self.review_opener:
                await self.review_opener(result, ctx)
            return result

        # 3. embedding
        embedding = self.embedding_service.embed(ctx.crop)
        if embedding is None:
            return _blocked(
                REC_BLOCKED_POLICY, "no_embedding", ["embedding_generation_failed"], model_version, liveness
            )

        # 4. gallery + policy gates
        if self.gallery_search is None or self.person_lookup is None:
            return _blocked(
                REC_NO_MATCH,
                "gallery_unavailable",
                ["recognition_disabled_or_no_gallery"],
                model_version,
                liveness,
            )

        candidates = [
            (enrollment, score)
            for enrollment, score in await self.gallery_search(embedding)
            if score >= self.settings.recognition_min_similarity
        ]

        # 5. multi-frame accumulation per authorized candidate
        best_outcome: ConfirmationOutcome | None = None
        confirmed_person: uuid.UUID | None = None
        candidate_score = 0.0

        for enrollment, score in candidates:
            person = await self.person_lookup(enrollment)
            if person is None:
                continue
            person_obj, consents, active_enrollments = person
            policy = self.policy_service.recognition_permitted(
                person_active=getattr(person_obj, "active", None),
                active_enrollments=active_enrollments,
                consents=list(consents),
                camera_id=ctx.camera_id,
                zone_id=ctx.zone_id,
                quality_usable=True,
                liveness_permits=True,
            )
            if not policy.allowed:
                continue
            outcome = self.confirmator.add_match(ctx.track_key, person_obj.person_id, score, now=now)
            if outcome.person_id == person_obj.person_id and (
                best_outcome is None or outcome.best_similarity > best_outcome.best_similarity
            ):
                best_outcome = outcome
            if outcome.decision == REC_CONFIRMED and confirmed_person is None:
                confirmed_person = person_obj.person_id

        if confirmed_person is None and best_outcome is None:
            return _blocked(
                REC_UNKNOWN,
                "allowed",
                ["no_authorized_candidate_above_threshold"],
                model_version,
                liveness,
            )

        decision_person = confirmed_person or (best_outcome.person_id if best_outcome else None)
        similarity = best_outcome.best_similarity if best_outcome else candidate_score
        decision = REC_CONFIRMED if confirmed_person else REC_UNCERTAIN

        # 6. multi-factor correlation
        mfa_outcome_str = None
        if self.mfa_service is not None and decision == REC_CONFIRMED:
            mfa = self.mfa_service.verify(decision_person, ctx.signals, now=now)
            mfa_outcome_str = mfa.outcome
            if mfa.outcome == "factor_conflict":
                result = RecognitionResult(
                    decision=REC_MFA_CONFLICT,
                    matched_person_id=decision_person,
                    similarity=similarity,
                    liveness_status=liveness.decision,
                    mfa_outcome=mfa.outcome,
                    review_status="required",
                    reasons=list(mfa.reasons),
                    model_version=model_version,
                )
                recognition_total.labels(decision=result.decision).inc()
                if self.review_opener:
                    await self.review_opener(result, ctx)
                return result
            if mfa.outcome == "manual_review_required":
                decision = REC_UNCERTAIN
                confirmed_person = None

        result = RecognitionResult(
            decision=decision,
            matched_person_id=decision_person,
            similarity=similarity,
            liveness_status=liveness.decision,
            mfa_outcome=mfa_outcome_str,
            review_status="required" if decision == REC_UNCERTAIN else "none",
            reasons=[f"consistent_frames={best_outcome.consistent_frames}"] if best_outcome else [],
            model_version=model_version,
        )
        recognition_total.labels(decision=result.decision).inc()
        if result.review_status == "required" and self.review_opener:
            await self.review_opener(result, ctx)
        return result


