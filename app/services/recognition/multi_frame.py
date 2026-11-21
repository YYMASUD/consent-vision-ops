"""Multi-frame match confirmation (spec §9).

Only confirms identity when multiple frames within the window match the same
person consistently: minimum count, minimum average, and minimum best similarity.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.common.enums import (
    REC_CONFIRMED,
    REC_NO_MATCH,
    REC_UNCERTAIN,
)
from app.common.utils import utcnow
from app.config.settings import get_settings


@dataclass
class FrameMatch:
    """One frame's candidate match for a track."""

    person_id: uuid.UUID
    similarity: float
    timestamp: datetime = field(default_factory=utcnow)


@dataclass
class ConfirmationOutcome:
    """Aggregated multi-frame decision for a track."""

    decision: str  # confirmed_match | uncertain_match | no_match
    person_id: uuid.UUID | None = None
    best_similarity: float = 0.0
    average_similarity: float = 0.0
    consistent_frames: int = 0

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "person_id": str(self.person_id) if self.person_id else None,
            "best_similarity": round(self.best_similarity, 4),
            "average_similarity": round(self.average_similarity, 4),
            "consistent_frames": self.consistent_frames,
        }


class MultiFrameConfirmator:
    """Accumulates per-track frame matches and emits confirmation decisions."""

    def __init__(self) -> None:
        s = get_settings()
        self.min_frames = s.multiframe_confirm_count
        self.window_s = s.multiframe_confirm_window_s
        self.min_similarity = s.recognition_min_similarity
        self.min_avg_similarity = s.recognition_min_avg_similarity
        self.min_best_similarity = s.recognition_min_best_similarity
        self._history: dict[str, list[FrameMatch]] = {}

    def add_match(
        self,
        track_key: str,
        person_id: uuid.UUID,
        similarity: float,
        *,
        now: datetime | None = None,
    ) -> ConfirmationOutcome:
        """Record one frame match and re-evaluate confirmation for the track."""
        now = now or utcnow()
        history = self._history.setdefault(track_key, [])
        history.append(FrameMatch(person_id=person_id, similarity=float(similarity), timestamp=now))
        return self.evaluate(track_key, now=now)

    def evaluate(self, track_key: str, *, now: datetime | None = None) -> ConfirmationOutcome:
        now = now or utcnow()
        cutoff = now - timedelta(seconds=self.window_s)
        history = [m for m in self._history.get(track_key, []) if m.timestamp >= cutoff]
        self._history[track_key] = history

        if not history:
            return ConfirmationOutcome(decision=REC_NO_MATCH)

        # group by candidate person, keep the largest consistent cluster
        by_person: dict[uuid.UUID, list[FrameMatch]] = {}
        for match in history:
            by_person.setdefault(match.person_id, []).append(match)
        best_person, best_group = max(
            by_person.items(), key=lambda kv: (len(kv[1]), sum(m.similarity for m in kv[1]))
        )

        similarities = [m.similarity for m in best_group]
        best = max(similarities)
        avg = sum(similarities) / len(similarities)
        count = len(similarities)

        if (
            count >= self.min_frames
            and avg >= self.min_avg_similarity
            and best >= self.min_best_similarity
            and min(similarities) >= self.min_similarity
        ):
            return ConfirmationOutcome(
                decision=REC_CONFIRMED,
                person_id=best_person,
                best_similarity=best,
                average_similarity=avg,
                consistent_frames=count,
            )
        if best >= self.min_similarity:
            return ConfirmationOutcome(
                decision=REC_UNCERTAIN,
                person_id=best_person,
                best_similarity=best,
                average_similarity=avg,
                consistent_frames=count,
            )
        return ConfirmationOutcome(
            decision=REC_NO_MATCH,
            person_id=best_person,
            best_similarity=best,
            average_similarity=avg,
            consistent_frames=count,
        )

    def clear(self, track_key: str) -> None:
        self._history.pop(track_key, None)
