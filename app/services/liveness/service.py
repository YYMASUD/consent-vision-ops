"""Pluggable liveness / anti-spoofing service (spec §8).

Decisions: live | suspected_presentation_attack | insufficient_evidence | unavailable.
Optional ONNX model when configured; heuristic checks otherwise (repeated identical
crops, low texture, brightness anomalies). Media is never retained — decisions only.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from app.common.enums import LIVE, LIVE_INSUFFICIENT, LIVE_UNAVAILABLE, SPOOF_ATTACK
from app.common.utils import utcnow
from app.config.settings import get_settings
from app.observability.metrics import liveness_total


@dataclass
class LivenessDecision:
    decision: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    model_version: str = "heuristic-v1"

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "model_version": self.model_version,
        }


class LivenessService:
    """Pluggable liveness checks; ONNX model when available, heuristics otherwise."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._session = None
        self._input_name: str | None = None
        self._attempted = False
        self._recent_hashes: dict[str, list[tuple[str, datetime]]] = {}

    # --- pluggable ONNX path -------------------------------------------------

    def _load_onnx(self):
        """Load the configured ONNX liveness model (never downloads)."""
        if self._attempted:
            return self._session
        self._attempted = True
        path = self.settings.liveness_model_path
        if not path:
            return None
        try:
            import onnxruntime as ort  # type: ignore

            self._session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
            self._input_name = self._session.get_inputs()[0].name
        except Exception:
            self._session = None
        return self._session

    def _model_inference(self, crop: np.ndarray) -> LivenessDecision | None:
        session = self._load_onnx()
        if session is None or crop is None or crop.size == 0:
            return None
        try:
            import cv2

            blob = cv2.resize(crop, (128, 128)).astype(np.float32) / 255.0
            blob = blob.transpose(2, 0, 1)[None]
            logits = session.run(None, {self._input_name: blob})[0][0]
            prob_attack = float(logits[1]) if logits.ndim else float(logits)
            if prob_attack >= 0.5:
                return LivenessDecision(SPOOF_ATTACK, prob_attack, ["onnx_model"], "onnx-v1")
            return LivenessDecision(LIVE, 1.0 - prob_attack, ["onnx_model"], "onnx-v1")
        except Exception:
            return None

    # --- heuristic path ---------------------------------------------------------

    def check(
        self,
        crop: np.ndarray | None,
        *,
        camera_id: str = "-",
        track_key: str = "-",
        now: datetime | None = None,
    ) -> LivenessDecision:
        """Assess one face crop for presentation-attack indicators."""
        now = now or utcnow()
        model_result = self._model_inference(crop)
        if model_result is not None:
            self._record(camera_id, track_key, model_result, now)
            return model_result

        if crop is None or crop.size == 0:
            decision = LivenessDecision(LIVE_UNAVAILABLE, 0.0, ["no_face_crop"])
            self._record(camera_id, track_key, decision, now)
            return decision

        import cv2

        reasons: list[str] = []
        digest = hashlib.sha256(crop.tobytes()).hexdigest()
        window_start = now - timedelta(seconds=self.settings.liveness_replay_window_s)
        history = [
            (h, ts)
            for h, ts in self._recent_hashes.get(f"{camera_id}:{track_key}", [])
            if ts >= window_start
        ]
        repeats = sum(1 for h, _ in history if h == digest)
        history.append((digest, now))
        self._recent_hashes[f"{camera_id}:{track_key}"] = history[-32:]

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        texture = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(gray.mean())

        if repeats >= self.settings.liveness_replay_repeat_threshold:
            reasons.append("repeated_identical_face_crops")
        if texture < self.settings.liveness_min_texture:
            reasons.append("low_texture_replay_artifact")
        if brightness < 10.0 or brightness > 245.0:
            reasons.append("abnormal_reflectance_pattern")

        if reasons:
            decision = LivenessDecision(SPOOF_ATTACK, 0.9, reasons, "heuristic-v1")
        elif texture < self.settings.liveness_min_texture * 2.0:
            decision = LivenessDecision(LIVE_INSUFFICIENT, 0.5, ["weak_texture_evidence"], "heuristic-v1")
        else:
            decision = LivenessDecision(LIVE, 0.85, [], "heuristic-v1")
        self._record(camera_id, track_key, decision, now)
        return decision

    def _record(self, camera_id: str, track_key: str, decision: LivenessDecision, now: datetime) -> None:
        liveness_total.labels(decision=decision.decision).inc()
        self.last_decision = decision.to_dict() | {"camera_id": camera_id, "ts": now.isoformat()}

    def permits_matching(self, decision: LivenessDecision) -> bool:
        """Spec §8: spoof denies automatic confirmation; unavailable follows fallback policy."""
        if decision.decision == SPOOF_ATTACK:
            return False
        if decision.decision == LIVE_UNAVAILABLE:
            return not self.settings.liveness_required
        return True

    last_decision: dict | None = None
